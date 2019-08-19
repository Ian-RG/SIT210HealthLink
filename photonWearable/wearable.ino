#include <spark_wiring_i2c.h>
#include <deque>

//Device adxl345 address
#define ADXL345 0x53

//Register addresses for ADXL345
#define THRESH_ACT 0x24 //Activity threshold 
#define THRESH_INACT 0x25 //Inactivity threshold 
#define TIME_INACT 0x26 //Time inactivity
#define ACT_INACT_CTL 0x27//Activity/inactivity detection
#define THRESH_FF 0x28 //Free-fall threshold
#define TIME_FF 0x29 //Free-fall time
#define ACT_TAP_STATUS 0x2B //Source of single/double tap
#define BW_RATE 0x2C//Sample rate
#define POWER_CTL 0x2D//Power mode
#define INT_ENABLE 0x2E //Enable interrupts
#define INT_MAP 0x2F //Interrupt mapping control
#define INT_SOURCE 0x30 //Interrupt source
#define DATA_FORMAT 0x31 //Data format control

//Define pins
#define INTERRUPT_PIN D6
#define PULSE_PIN 0

byte adxlBuffer[6];
long activityTimeStamps[3];

int pulseSensorVal;
std::deque<unsigned long int> pulseTimeStamps;
bool isPulseOverThreshold = false;

String outData = "0 0";

void setup() {
    Wire.begin();
    Serial.begin(9600);
    
    //Initialise EMIC tts module
    Serial1.begin(9600);
    Serial1.print('\n');
    while (Serial1.read() != ':');
    delay(10);
    Serial1.flush();
    setTTSParameter('N', 3);    //Set voice
    setTTSParameter('W', 180);  //Set words per minute
    
    
    //Set parameters for accelerometer
    writeToADXL(THRESH_ACT, 0x20); //2g
    writeToADXL(THRESH_INACT, 0x03); //.1875g
    writeToADXL(TIME_INACT, 0x02); //2 seconds
    writeToADXL(ACT_INACT_CTL, 0x7F);
    writeToADXL(THRESH_FF, 0x0c); //0.75g
    writeToADXL(TIME_FF, 0x06); //30ms
    writeToADXL(BW_RATE, 0x0A); //100hz sample rate
    writeToADXL(POWER_CTL, 0x08); //Measure mode
    writeToADXL(INT_ENABLE, 0x1C); //Enable activity, inactivity, free-fall interrupts
    writeToADXL(INT_MAP, 0x1C);  // Map interrupts to pin 1 on adxl
    writeToADXL(DATA_FORMAT, 0x0B); //+-16g range, i2c interface
    
    //Cloud functions and variables
    Particle.variable("residentStatus", outData);
    Particle.function("ttsMessage", playMessage);
    Particle.function("resetFall", resetFall);
    
    attachInterrupt(INTERRUPT_PIN, interrupt, RISING);
}


void loop() {
    readPulse();
    delay(10);
}

int playMessage(String s) {
    sayTTS(s);
}

void sayTTS (const String &string) {
    Serial1.print('S');
    Serial1.print(string);
    Serial1.print('\n');
    while (Serial1.read() != ':') {
        readPulse();
        delay(10);
    }
}

void setTTSParameter(char command, int val) {
    Serial1.print(command);
    Serial1.print(val);
    Serial1.print('\n');
}

int resetFall(String s) {
    outData = outData.substring(1);
    outData = "0"+outData;
    Serial.println("Fall Reset");
}

void readPulse() {
    pulseSensorVal = analogRead(PULSE_PIN);
    
    if (pulseSensorVal > 2900 && !isPulseOverThreshold) {
        isPulseOverThreshold = true;
        pulseTimeStamps.push_back(millis());
        if (pulseTimeStamps.size() > 10)
            pulseTimeStamps.pop_front();
        
        if (pulseTimeStamps.size() > 1) {    
            double avgPulse = calculateAvgPulse()/1000; //Convert from ms to s
            outData = outData.substring(0, 2);
            outData += String(round(60/avgPulse));
            Serial.println(60/avgPulse);
        }
    }
    //If 3 seconds has passed with no value read, set pulse to zero.
    else if (pulseTimeStamps.size() > 1 && millis() - pulseTimeStamps.back() > 3000) {
        outData = outData.substring(0, 2);
        outData += "0";
    }
    else if (pulseSensorVal <= 3000)
        isPulseOverThreshold = false;
}

double calculateAvgPulse() {
    int i = pulseTimeStamps.size()-1;
    int total = 0;
    while (i > 0) {
        total += pulseTimeStamps[i] - pulseTimeStamps[i-1];
        i--;
    }
    return total / (pulseTimeStamps.size()-1);
}

void interrupt() {
    readFromADXL(INT_SOURCE, 1);
    if ((adxlBuffer[0] & 4) == 4) {
        Serial.println("Freefall");
        activityTimeStamps[0] = millis();
    }
    if (adxlBuffer[0] & 16) {
        activityTimeStamps[1] = millis();
        Serial.println("Activity");
    }
    if ((adxlBuffer[0] & 8) == 8) {
        activityTimeStamps[2] = millis();
        Serial.println("Inactivity");
        detectFall();
    }
}

void detectFall() {
    if (activityTimeStamps[1] - activityTimeStamps[0] < 200 &&
        activityTimeStamps[1] - activityTimeStamps[0] > 0 &&
        activityTimeStamps[2] - activityTimeStamps[1] < 2500 &&
        activityTimeStamps[2] - activityTimeStamps[1] > 0) {
            
        outData = outData.substring(1);
        outData = "1"+outData;
        Serial.println("Fall Detected");
            activityTimeStamps[0] = 0; // Reset free-fall timestamp to avoid repeated detection of same fall
        }
}

void writeToADXL(byte address, byte val) {
    Wire.beginTransmission(ADXL345);
    Wire.write(address);
    Wire.write(val);
    Wire.endTransmission();
}

void readFromADXL(byte address, int num) {
    Wire.beginTransmission(ADXL345);
    Wire.write(address);
    Wire.endTransmission();
    
    Wire.beginTransmission(ADXL345);
    Wire.requestFrom(ADXL345, num);
    
    int i = 0;
    while (Wire.available()) {
        adxlBuffer[i] = Wire.read();
        i++;
    }
    Wire.endTransmission();
}
