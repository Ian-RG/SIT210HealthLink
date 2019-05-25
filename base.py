import RPi.GPIO as GPIO
from urllib import request, parse
import json
from tkinter import *
import tkinter.font
from mfrc522 import SimpleMFRC522
from time import localtime, strftime, strptime, mktime, asctime
from datetime import datetime
import authenticator
from scalescontroller import Scales


def updateResidentStats():
    def isPulseSafe(r, pulse):
        return pulse > r["minPulse"] and pulse < r["maxPulse"]

    def getDeviceData(url):
        response = request.urlopen(url)
        data = json.loads(response.read().decode(
            response.info().get_param('charset') or 'utf-8'))
        return data['result']

    global residents
    for r in residents:
        if (r["timeout"] > 0):
            r["timeout"] -= 1
        if r["statusUrl"] == "none":
            r["pulseLabel"]["text"] = "No device assigned"
            r["fallLabel"]["text"] = "No device assigned"
        else:
            try:
                data = getDeviceData(r["statusUrl"])
                r["pulseLabel"]["text"] = "Pulse: " + data[2:]
                r["fallLabel"]["text"] = "Fall Status: " + \
                    ("OK" if data[0] == "0" else "Fall Detected")
                if (r["fallLabel"]["text"] != "Fall Status: OK" and not alertActive):
                    resetFall(r)
                    displayAlert(r, "fall")
                #if (not isPulseSafe(r, float(data[2:])) and not alertActive and r["timeout"] == 0):
                    #r["timeout"] = 6
                    #displayAlert(r, "heart")
            except:
                r["pulseLabel"]["text"] = "Connection Error"
                r["fallLabel"]["text"] = "Connection Error"

    window.after(10000, updateResidentStats)


def checkMedicationSchedule():
    for m in medicationSchedule:
        if m["time"] <= mktime(localtime()) and not m["reminderSent"]:
            res = {}
            for r in residents:
                if (r["name"] == m["name"]):
                    res = r
                    break
            message = "Medication reminder"
            data = parse.urlencode({"Message": message}).encode()
            req = request.Request(res["messageUrl"], data=data)
            resp = request.urlopen(req)
            m["reminderSent"] = True
            with open("medicationSchedule.json", "w") as scheduleFile:
                json.dump(medicationSchedule, scheduleFile)

    window.after(60000, checkMedicationSchedule)


def resetFall(resident):
    data = parse.urlencode({"Message": "Reset"}).encode()
    req = request.Request(resident["resetFallUrl"], data=data)
    resp = request.urlopen(req)


def openMedicationWindow():
    def getNames(arr):
        names = []
        for e in arr:
            names.append(e["name"])
        return names

    rNames = getNames(residents)
    mNames = getNames(medications)
    dosageLabels = range(1, 11)

    medicationWindow = Tk()
    medicationWindow.title("Resident Medication")
    medicationWindow["bg"] = "white"
    centreWindow(medicationWindow, 800, 100)
    
    header = Label(medicationWindow, text="Medication", font=headerFont)
    header.grid(row=0, column=0, columnspan=7)

    nameLabel = Label(medicationWindow, text="Name", bg="white")
    nameLabel.grid(row=1, column=0)
    medLabel = Label(medicationWindow, text="Medication", bg="white")
    medLabel.grid(row=1, column=1)
    dosLabel = Label(medicationWindow, text="Dosage", bg="white")
    dosLabel.grid(row=1, column=2)
    dateLabel = Label(medicationWindow, text="Date (DD/MM/YYYY)", bg="white")
    dateLabel.grid(row=1, column=3)
    hourLabel = Label(medicationWindow, text="Hour (0-23)", bg="white")
    hourLabel.grid(row=1, column=4)
    minLabel = Label(medicationWindow, text="Minute (0-59)", bg="white")
    minLabel.grid(row=1, column=5)

    namesVar = StringVar(medicationWindow)
    namesVar.set(rNames[0])
    nameOptionList = OptionMenu(medicationWindow, namesVar, *rNames)
    nameOptionList.grid(row=2, column=0)

    medsVar = StringVar(medicationWindow)
    medsVar.set(mNames[0])
    medicationOptionList = OptionMenu(medicationWindow, medsVar, *mNames)
    medicationOptionList.grid(row=2, column=1)

    dosageVar = StringVar(medicationWindow)
    dosageVar.set(dosageLabels[0])
    dosageOptionList = OptionMenu(medicationWindow, dosageVar, *dosageLabels)
    dosageOptionList.grid(row=2, column=2)

    dateEntry = Entry(medicationWindow, bg="white", width=20)
    dateEntry.grid(row=2, column=3)

    hoursEntry = Entry(medicationWindow, bg="white", width=10)
    hoursEntry.grid(row=2, column=4)

    minutesEntry = Entry(medicationWindow, bg="white", width=10)
    minutesEntry.grid(row=2, column=5)

    def verifyAndSubmit():
        dt = dateEntry.get()+" "+hoursEntry.get()+":" + \
            minutesEntry.get()
        if (authenticator.isAuthenticationValid(rfidReader)):
            try:
                e = {}
                e["time"] = mktime(strptime(dt, "%d/%m/%Y %H:%M"))
                e["name"] = namesVar.get()
                e["medication"] = medsVar.get()
                e["dosage"] = dosageVar.get()
                e["reminderSent"] = False

                medicationSchedule.append(e)

                with open("medicationSchedule.json", "w") as scheduleFile:
                    json.dump(medicationSchedule, scheduleFile)
                medicationWindow.destroy()
            except Exception as e:
                print(e)
        else:
            print("Invalid Authentication")
    button = Button(medicationWindow, text="Authenticate and Submit",
                    command=verifyAndSubmit)
    button.grid(row=2, column=6)

    medicationWindow.protocol("WM_DELETE_WINDOW", medicationWindow.destroy)

    medicationWindow.mainloop()


def openDispenseWindow():
    dispenseWindow = Tk()
    dispenseWindow.title("Dispense Medication")
    dispenseWindow["bg"] = "white"
    centreWindow(dispenseWindow, 600, 100)
    
    header = Label(dispenseWindow, text="Medication", font=headerFont)
    header.grid(row=0, column=0, columnspan=4)

    itemLabel = Label(dispenseWindow, text="Schedule Item", bg="white")
    itemLabel.grid(row=1, column=0)
    scaleLabel = Label(dispenseWindow, text="On Scales", bg="white")
    scaleLabel.grid(row=1, column=1)

    def getScheduleOptions():
        options = []
        for m in medicationSchedule:
            if m["time"] <= mktime(localtime()):
                options.append(asctime(localtime(
                    m["time"]))+": "+m["name"]+" "+m["dosage"]+" "+m["medication"])
        return options

    validSchedule = getScheduleOptions()
    scheduleVar = StringVar(dispenseWindow)
    scheduleVar.set(validSchedule[0])
    scheduleOptionList = OptionMenu(
        dispenseWindow, scheduleVar, *validSchedule)
    scheduleOptionList.grid(row=2, column=0)

    def getScalesValue():
        activeScheduleItem = {}
        for m in medicationSchedule:
            for m in medicationSchedule:
                if asctime(localtime(m["time"]))+": "+m["name"]+" "+m["dosage"]+" "+m["medication"] == scheduleVar.get():
                    activeScheduleItem = m
        activeMedication = {}
        for m in medications:
            if (m["name"] == activeScheduleItem["medication"]):
                activeMedication = m

        val = round(scales.getWeightMean(), 1)
        target = int(activeScheduleItem["dosage"]) * \
            int(activeMedication["weight"])

        if (val > target*.93 and val < target*1.07):
            button["bg"] = "green"
        else:
            button["bg"] = "red"
        scalesLabel["text"] = val
        dispenseWindow.after(500, getScalesValue)

    scalesLabel = Label(dispenseWindow, text="0", bg="white")
    scalesLabel.grid(row=2, column=1)

    def verifyAndSubmit():
        if (button["bg"] == "green"):
            if (authenticator.isAuthenticationValid(rfidReader)):
                try:
                    for m in medicationSchedule:
                        if asctime(localtime(m["time"]))+": "+m["name"]+" "+m["dosage"]+" "+m["medication"] == scheduleVar.get():
                            medicationSchedule.remove(m)
                            with open("medicationSchedule.json", "w") as scheduleFile:
                                json.dump(medicationSchedule, scheduleFile)
                            dispenseWindow.destroy()

                except Exception as e:
                    print(e)
            else:
                print("Invalid Authentication")

    button = Button(dispenseWindow, text="Authenticate and Submit", bg="red",
                    command=verifyAndSubmit)
    button.grid(row=2, column=2)

    getScalesValue()
    dispenseWindow.protocol("WM_DELETE_WINDOW", dispenseWindow.destroy)
    dispenseWindow.mainloop()


def openSendMessageWindow():
    def getNames():
        n = []
        for r in residents:
            if (r["messageUrl"] != "none"):
                n.append(r["name"])
        print(n)
        return n
    global messageWindow    
    messageWindow = Tk()
    messageWindow.title("Send Message")
    messageWindow["bg"] = "white"
    centreWindow(messageWindow, 500, 80)
    
    header = Label(messageWindow, text="Send Message", font=headerFont)
    header.grid(row=0, column=0, columnspan=3)
    rNames = getNames()
    namesVar = StringVar(messageWindow)
    namesVar.set(rNames[0])
    nameOptionList = OptionMenu(messageWindow, namesVar, *rNames)
    nameOptionList.grid(row=1, column=0)
    entry = Entry(messageWindow, bg="white", fg="black", width=36)
    entry.grid(row=1, column=1)
    submissionMessage = Label(messageWindow, text="Authentication required before message submission")
    submissionMessage.grid(row=2, column=0, columnspan=3)

    def verifyAndSendMessage(message, name):
        url = ""
        for r in residents:
            if (r["name"] == name):
                url = r["messageUrl"]
                break
        if (authenticator.isAuthenticationValid(rfidReader)):
            data = parse.urlencode({"Message": message}).encode()
            req = request.Request(sendMessageUrl, data=data)
            resp = request.urlopen(req)
        messageWindow.destroy()

    sendButton = Button(messageWindow, text="Send", font=labelFont,
                        command=lambda: verifyAndSendMessage(entry.get(), namesVar.get()), bg="green")
    sendButton.grid(row=1, column=2)
    messageWindow.protocol("WM_DELETE_WINDOW", messageWindow.destroy)
    messageWindow.mainloop()


def displayAlert(resident, category):
    global alertActive
    alertActive = True

    message = resident["name"] + ": "
    resident["nameLabel"]["bg"] = "red"
    if (category == "fall"):
        resident["fallLabel"]["bg"] = "red"
        message += "Fall detected at "
    elif (category == "heart"):
        resident["pulseLabel"]["bg"] = "red"
        message += "Heart rate problem detected at "
    message += strftime("%d/%m/%Y %H:%M:%S", localtime())

    addToAlerts(message)
    writeToLogs(message)
    flashAlert()
    openAuthenticationWindow(message)


def writeToLogs(message):
    with open("logs.txt", "a") as logsFile:
        logsFile.write(message + "\n")


def addToAlerts(message):
    global alertRow
    alert = Label(window, text=message, bg="white")
    alert.grid(row=alertRow, column=3)
    alertRow += 1


def dismissAlert():
    global alertActive
    alertActive = False
    for r in residents:
        r["nameLabel"]["bg"] = "white"
        r["fallLabel"]["bg"] = "white"
        r["pulseLabel"]["bg"] = "white"
    alertLabel["bg"] = "white"
    global authenticationValid
    authenticationValid = False
    authenticationWindow.destroy()
    updateResidentStats()


def openAuthenticationWindow(message):
    global authenticationWindow
    authenticationWindow = Tk()
    authenticationWindow.title("Authentication Required")
    authenticationWindow["bg"] = "white"
    centreWindow(authenticationWindow, 500, 50)
    
    header = Label(authenticationWindow,
                   text="Authentication Required", font=headerFont)
    header.grid(row=0, column=0)
    message = Label(authenticationWindow, text=message)
    message.grid(row=1, column=0)
    authenticationWindow.protocol(
        "WM_DELETE_WINDOW", closeAuthenticationWindow)
    monitorRFID()
    authenticationWindow.mainloop()


def flashAlert():
    if (alertActive):
        alertLabel["bg"] = "white" if alertLabel["bg"] == "red" else "red"
        window.after(500, flashAlert)


def closeAuthenticationWindow():
    global authenticationWindow
    if authenticationValid:
        authenticationWindow.destroy()


def monitorRFID():
    id = rfidReader.read_id_no_block()
    if (authenticator.authenticateUser(id)):
        global authenticationValid
        authenticationValid = True
        dismissAlert()
        return
    authenticationWindow.after(50, monitorRFID)


def close():
    window.destroy()
    GPIO.cleanup()
    
def centreWindow(window, width, height):
    screenWidth = window.winfo_screenwidth()
    screenHeight = window.winfo_screenheight()
    
    x = (screenWidth/2) - (width/2)
    y = (screenHeight/2) - (height/2)
    window.geometry("%dx%d+%d+%d" % (width, height, x, y))


GPIO.setmode(GPIO.BCM)
scales = Scales()
rfidReader = SimpleMFRC522()

alertActive = False
authenticationValid = False

sendMessageUrl = "https://api.particle.io/v1/devices/2f001f000b47373336323230/ttsMessage?access_token=42cc36c073be42ed74ede6dddde8e5c7bd9de7e6"
alertRow = 2  # row to insert next alert message

# Read in residents, medication, and medication schedule data
with open("residents.json", "r") as residentsFile:
    residentsData = residentsFile.read()
residents = json.loads(residentsData)
with open("medication.json", "r") as medicationFile:
    medicationData = medicationFile.read()
medications = json.loads(medicationData)
with open("medicationSchedule.json", "r") as scheduleFile:
    scheduleData = scheduleFile.read()
medicationSchedule = sorted(json.loads(scheduleData), key=lambda k: k["time"])


# Main Window
window = Tk()
window.title("HealthLink Control Panel")
window["bg"] = "white"
centreWindow(window, 1200, 200)

# Fonts
headerFont = tkinter.font.Font(family="Helvetica", size=18, weight="bold")
labelFont = tkinter.font.Font(family="Helvetica", size=14, weight="bold")

# Header
header = Label(text="HealthLink", font=headerFont)
header.grid(row=0, column=0, columnspan=4)

# Button list
medButton = Button(window, text="Edit Meds", font=labelFont,
                   command=openMedicationWindow, justify=LEFT)
medButton.grid(row=1, column=0)
dispenseButton = Button(window, text="Dispense Meds",
                        font=labelFont, command=openDispenseWindow, justify=LEFT)
dispenseButton.grid(row=2, column=0)
messageButton = Button(window, text="Send Message", font=labelFont,
                       command=openSendMessageWindow, justify=LEFT)
messageButton.grid(row=3, column=0)
exitButton = Button(window, text="Exit", font=labelFont,
                    command=close, bg="red", justify=LEFT)
exitButton.grid(row=5, column=0)

# Resident labels
for i, r in enumerate(residents):
    baseRow = 2*i+1
    r["nameLabel"] = Label(window, text=r["name"], font=labelFont, bg="white")
    r["nameLabel"].grid(row=baseRow, column=1, rowspan=2)
    r["pulseLabel"] = Label(window, text="Pulse: INITIALISING", bg="white")
    r["pulseLabel"].grid(row=baseRow, column=2, sticky=W)
    r["fallLabel"] = Label(
        window, text="Fall Status: INITIALISING", bg="white")
    r["fallLabel"].grid(row=baseRow+1, column=2, sticky=W)

# Alert Indicator
alertLabel = Label(text="Alert", font=labelFont, borderwidth=1,
                   bg="white", relief="solid", width=32)
alertLabel.grid(row=1, column=3)

# Medication Schedule
scheduleLabel = Label(text="Upcoming Meds", font=labelFont, bg="white")
scheduleLabel.grid(row=1, column=4)
sLabels = []
for i, m in enumerate(medicationSchedule):
    if (i > 4):
        break

    l = Label(text=asctime(localtime(
        m["time"]))+": "+m["name"]+" "+m["dosage"]+" "+m["medication"], bg="white")
    l.grid(row=2+i, column=4)
    sLabels.append(l)

window.grid_columnconfigure(0, weight=1)
window.grid_columnconfigure(1, weight=1)
window.grid_columnconfigure(2, weight=1)
window.grid_columnconfigure(3, weight=3)

window.protocol("WM_DELETE_WINDOW", close)

window.after(5000, updateResidentStats)
window.after(10000, checkMedicationSchedule)
window.mainloop()
