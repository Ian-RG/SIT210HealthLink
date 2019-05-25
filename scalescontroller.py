import RPi.GPIO as GPIO
import statistics as stat
import time

#Based on HX711 library from https://github.com/gandalf15/HX711


class Scales:
    def __init__(self):
        self.offset = 0
        self.scaleRatio = 1
        self.clckPin = 6
        self.dataPin = 5

        GPIO.setup(self.clckPin, GPIO.OUT)
        GPIO.setup(self.dataPin, GPIO.IN)
        # set channel and gain
        self.read()
        time.sleep(0.5)

        print("Ensure scales are clear and press enter.")
        input()
        self.zero()
        print("Place dish on scales and press enter.")
        input()
        reading = self.getDataMean()
        self.setScaleRatio(reading/27.18)
        print("Scales calibrated")
        self.zero()

    def zero(self):
        self.offset = self.getRawDataMean()

    def setScaleRatio(self, ratio):
        self.ratio = ratio

    def ready(self):
        if GPIO.input(self.dataPin) == 0:
            return True
        return False

    def read(self):
        GPIO.output(self.clckPin, False)
        while(not self.ready()):
            pass

        data = 0
        for _ in range(24):
            GPIO.output(self.clckPin, True)
            GPIO.output(self.clckPin, False)
            data = (data << 1) | GPIO.input(self.dataPin)
        # Set channel and gain for next reading
        GPIO.output(self.clckPin, True)
        GPIO.output(self.clckPin, False)

        signedData = 0
        if (data & 0x800000):
            signedData = -((data ^ 0xffffff)+1)  # convert from 2s complement
        else:
            signedData = data
        return signedData

    def getRawDataMean(self):
        dataList = []
        for _ in range(30):
            dataList.append(self.read())
        return stat.mean(dataList)

    def getDataMean(self):
        return self.getRawDataMean()-self.offset

    def getWeightMean(self):
        return (self.getRawDataMean()-self.offset)/self.ratio
