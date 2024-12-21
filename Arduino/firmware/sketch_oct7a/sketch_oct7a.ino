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

int setTemperature = 10;  // Default temperature in degrees Celsius

// Initialize the thermistor object
thermistor therm1(A0, 0); // A0 is the pin, and 0 is the sensor number

#define HYSTERESIS 1  // Degrees Celsius to prevent rapid toggling of SSR state
#define UPDATE_INTERVAL 100  // Update interval in milliseconds

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
  playChime();  // Play a chime on startup
}

void loop() {
  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate >= UPDATE_INTERVAL) {
    lastUpdate = millis();
    float currentTemperature = therm1.analog2temp();  // Read temperature from thermistor

    // Print real-time temperature data to the Serial Monitor
    Serial.print("Current Temperature: ");
    Serial.print(currentTemperature);
    Serial.print(" °C | Set Temperature: ");
    Serial.print(setTemperature);
    Serial.print(" °C | SSR State: ");
    Serial.println(digitalRead(ssrPin) ? "ON" : "OFF");

    // Control temperature using the SSR
    controlTemperature(currentTemperature);
  }

  // Check for incoming serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    handleCommands(command);
  }
}

void controlTemperature(float currentTemp) {
  static bool ssrEnabled = false;

  if (currentTemp < setTemperature - HYSTERESIS && !ssrEnabled) {
    digitalWrite(ssrPin, HIGH);  // Turn on SSR
    ssrEnabled = true;
    Serial.println("SSR turned ON");
  } else if (currentTemp > setTemperature + HYSTERESIS && ssrEnabled) {
    digitalWrite(ssrPin, LOW);  // Turn off SSR
    ssrEnabled = false;
    Serial.println("SSR turned OFF");
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
    int guiPWMValue = command.substring(12).toInt();
    int arduinoPWMValue = 255 - map(guiPWMValue, 0, 100, 0, 255);
    analogWrite(fanPWM_Pin, arduinoPWMValue);
    EEPROM.update(addrFanPWMValue, arduinoPWMValue);
    Serial.print("Fan PWM set to ");
    Serial.println(arduinoPWMValue);
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
    int guiPWMValue = command.substring(15).toInt();
    int arduinoPWMValue = 255 - map(guiPWMValue, 0, 100, 0, 255);
    analogWrite(winderMotorPWM_Pin, arduinoPWMValue);
    EEPROM.update(addrWinderMotorPWMValue, arduinoPWMValue);
    Serial.print("Winder Motor PWM set to ");
    Serial.println(arduinoPWMValue);
  }

  if (command.startsWith("SET_TEMP:")) {
    setTemperature = command.substring(9).toInt();
    EEPROM.update(addrSetTemperature, setTemperature);
    Serial.print("Set Temperature updated to ");
    Serial.print(setTemperature);
    Serial.println(" °C");
  }
}

void playChime() {
  for (int i = 0; i < 100; i++) {
    digitalWrite(speakerPin, HIGH);
    delayMicroseconds(500);
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
