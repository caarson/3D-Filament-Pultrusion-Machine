#include <Arduino.h>
#include <EEPROM.h>
#include <thermistor.h>  // Include the thermistor library

// Define pin assignments
const int fanPWM_Pin = 3;
const int fanSwitch_Pin = 9;
const int winderMotorPWM_Pin = 5;
const int winderMotorSwitch_Pin = 7;
const int ssrPin = 15;
const int speakerPin = 2;  // Speaker pin for auditory feedback
const int thermistorPin = A0;  // Thermistor connected to analog pin A0

// Define EEPROM addresses for each setting
const int addrFanSwitchState = 0;
const int addrFanPWMValue = 1;
const int addrWinderMotorSwitchState = 2;
const int addrWinderMotorPWMValue = 3;
const int addrSetTemperature = 4;  // Address to store set temperature

int setTemperature = 25;  // Default temperature in degrees Celsius

// Initialize the thermistor object
thermistor therm(thermistorPin, 10000, 3950, 25, 10000);  // Parameters must match your thermistor's specifications

void setup() {
  pinMode(fanPWM_Pin, OUTPUT);
  pinMode(fanSwitch_Pin, OUTPUT);
  pinMode(winderMotorPWM_Pin, OUTPUT);
  pinMode(winderMotorSwitch_Pin, OUTPUT);
  pinMode(ssrPin, OUTPUT);
  pinMode(speakerPin, OUTPUT);
  pinMode(thermistorPin, INPUT);
  Serial.begin(9600);

  // Restore saved settings
  restoreSettings();
  setTemperature = EEPROM.read(addrSetTemperature);
  playChime();  // Play a chime on startup to indicate power on
}

void loop() {
  static unsigned long lastTempCheck = 0;
  if (millis() - lastTempCheck > 1000) {  // Check temperature every second
    lastTempCheck = millis();
    float currentTemperature = therm.analog2temp();  // Read temperature from thermistor
    controlTemperature(currentTemperature);
    Serial.println("Current Temp: " + String(currentTemperature) + "C, Set Temp: " + String(setTemperature) + "C");
  }

  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    handleCommands(command);
  }
}

void controlTemperature(float currentTemp) {
  if (currentTemp < setTemperature) {
    digitalWrite(ssrPin, HIGH);
  } else {
    digitalWrite(ssrPin, LOW);
  }
}

void handleCommands(String command) {
  if (command == "FAN_ON") {
    digitalWrite(fanSwitch_Pin, HIGH);
    EEPROM.update(addrFanSwitchState, HIGH);
    Serial.println("Fan is ON");
  } else if (command == "FAN_OFF") {
    digitalWrite(fanSwitch_Pin, LOW);
    EEPROM.update(addrFanSwitchState, LOW);
    Serial.println("Fan is OFF");
  }

  if (command.startsWith("SET_FAN_PWM:")) {
    int pwmValue = command.substring(12).toInt();
    analogWrite(fanPWM_Pin, pwmValue);
    EEPROM.update(addrFanPWMValue, pwmValue);
    Serial.println("Fan PWM set to " + String(pwmValue));
  }

  if (command == "WINDER_ON") {
    digitalWrite(winderMotorSwitch_Pin, HIGH);
    EEPROM.update(addrWinderMotorSwitchState, HIGH);
    Serial.println("Winder Motor is ON");
  } else if (command == "WINDER_OFF") {
    digitalWrite(winderMotorSwitch_Pin, LOW);
    EEPROM.update(addrWinderMotorSwitchState, LOW);
    Serial.println("Winder Motor is OFF");
  }

  if (command.startsWith("SET_WINDER_PWM:")) {
    int pwmValue = command.substring(15).toInt();
    analogWrite(winderMotorPWM_Pin, pwmValue);
    EEPROM.update(addrWinderMotorPWMValue, pwmValue);
    Serial.println("Winder Motor PWM set to " + String(pwmValue));
  }

  if (command.startsWith("SET_TEMP:")) {
    setTemperature = command.substring(9).toInt();
    EEPROM.update(addrSetTemperature, setTemperature);
    Serial.println("Set Temperature updated to " + String(setTemperature) + "C");
  }
}

void playChime() {
  for (int i = 0; i < 100; i++) {
    digitalWrite(speakerPin, HIGH);
    delayMicroseconds(500);  // 1 kHz tone
    digitalWrite(speakerPin, LOW);
    delayMicroseconds(500);
  }
}

void restoreSettings() {
  int fanState = EEPROM.read(addrFanSwitchState);
  digitalWrite(fanSwitch_Pin, fanState);
  int fanPWM = EEPROM.read(addrFanPWMValue);
  analogWrite(fanPWM_Pin, fanPWM);

  int winderMotorState = EEPROM.read(addrWinderMotorSwitchState);
  digitalWrite(winderMotorSwitch_Pin, winderMotorState);
  int winderMotorPWM = EEPROM.read(addrWinderMotorPWMValue);
  analogWrite(winderMotorPWM_Pin, winderMotorPWM);

  Serial.println("Settings restored.");
}
