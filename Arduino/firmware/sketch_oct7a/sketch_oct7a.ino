#include <Arduino.h>
#include <EEPROM.h>

// Define pin assignments
const int fanPWM_Pin = 3;
const int fanSwitch_Pin = 9;
const int winderMotorPWM_Pin = 5;
const int winderMotorSwitch_Pin = 7;
const int ssrPin = 15;

// Define EEPROM addresses for each setting
const int addrFanSwitchState = 0;
const int addrFanPWMValue = 1;
const int addrWinderMotorSwitchState = 2;
const int addrWinderMotorPWMValue = 3;

void setup() {
  pinMode(fanPWM_Pin, OUTPUT);
  pinMode(fanSwitch_Pin, OUTPUT);
  pinMode(winderMotorPWM_Pin, OUTPUT);
  pinMode(winderMotorSwitch_Pin, OUTPUT);
  pinMode(ssrPin, OUTPUT);
  Serial.begin(9600);

  // Restore saved settings
  restoreSettings();
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    
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

    // Add similar handling for winder motor
  }
}

void restoreSettings() {
  // Restore fan state and PWM value
  int fanState = EEPROM.read(addrFanSwitchState);
  digitalWrite(fanSwitch_Pin, fanState);

  int fanPWM = EEPROM.read(addrFanPWMValue);
  analogWrite(fanPWM_Pin, fanPWM);

  // Restore winder motor state and PWM value
  int winderMotorState = EEPROM.read(addrWinderMotorSwitchState);
  digitalWrite(winderMotorSwitch_Pin, winderMotorState);

  int winderMotorPWM = EEPROM.read(addrWinderMotorPWMValue);
  analogWrite(winderMotorPWM_Pin, winderMotorPWM);

  Serial.println("Settings restored.");
}

// Optional: Function to reset EEPROM for debugging
void resetEEPROM() {
  for (int i = 0; i < 512; i++) { // Adjust the size depending on your Arduino model
    EEPROM.write(i, 0);
  }
}
