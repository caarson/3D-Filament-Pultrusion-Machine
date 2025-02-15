#include <Arduino.h>
#include <EEPROM.h>
#include <thermistor.h>  // Include the thermistor library

// Pin assignments
const int fanPWM_Pin = 3;               // PWM output pin for fan speed control
const int fanSwitch_Pin = 9;            // Switch control pin (HIGH = on, LOW = off)
const int winderMotorPWM_Pin = 5;       // PWM output pin for winder motor speed control
const int winderMotorSwitch_Pin = 7;    // Switch control pin for winder motor on/off
const int ssrPin = 15;                  // Solid State Relay pin for heater control
const int speakerPin = 2;               // Speaker pin for auditory feedback
const int thermistorPin = A0;           // Thermistor connected to analog pin A0
const int inductiveSwitchPin = 6;       // Inductive switch for emergency stop

// USB-detect pin (optional; for now, not used with the EJECT command)
const int usbDetectPin = A1;

// EEPROM addresses for each setting
const int addrFanSwitchState = 0;
const int addrFanPWMValue    = 1;
const int addrWinderMotorSwitchState = 2;
const int addrWinderMotorPWMValue    = 3;
const int addrSetTemperature         = 4; // Address to store set temperature

int setTemperature;   // Read from EEPROM in restoreSettings()

thermistor therm1(thermistorPin, 0);   // Initialize thermistor

#define UPDATE_INTERVAL 100            // Update interval in milliseconds

// Shutdown Timer Variables
unsigned long shutoffTime       = 0;
unsigned long shutoffStartTime  = 0;
bool shutdownScheduled          = false;

// Cooling Mode Variables
bool cooling                    = false;
unsigned long coolingStartTime  = 0;   // Delay turning fan off

// Global flag to block further commands once shutdown is active
bool shutdownActive             = false;

// Temperature threshold for cooling mode; when temperature drops below this value (30°C), fan will eventually turn off.
const float SHUTOFF_TEMP_THRESHOLD = 30.0;

// Variable to track USB connection state for debug prints
bool usbWasPlugged = true;

// Function Prototypes
void controlTemperature(float currentTemp);
void handleCommands(String command);
void initiateShutdown();
void emergencyStop();
void beep();
void playChime();
void playShutdownChime();
void restoreSettings();
void clearEEPROM();
void checkUSBState();


// --- Helper functions for fan control ---
void turnFanOn(uint8_t pwmValue) {
  digitalWrite(fanSwitch_Pin, HIGH);
  analogWrite(fanPWM_Pin, pwmValue);
  EEPROM.update(addrFanSwitchState, HIGH);
  EEPROM.update(addrFanPWMValue, pwmValue);
  Serial.print("turnFanOn(): FanSwitch set HIGH, PWM = ");
  Serial.println(pwmValue);
}

void turnFanOff() {
  digitalWrite(fanSwitch_Pin, LOW);
  analogWrite(fanPWM_Pin, 0);
  EEPROM.update(addrFanSwitchState, LOW);
  EEPROM.update(addrFanPWMValue, 0);
  Serial.println("turnFanOff(): FanSwitch set LOW, PWM = 0");
}

void setup() {
  // Set pin modes
  pinMode(fanPWM_Pin, OUTPUT);
  pinMode(fanSwitch_Pin, OUTPUT);
  pinMode(winderMotorPWM_Pin, OUTPUT);
  pinMode(winderMotorSwitch_Pin, OUTPUT);
  pinMode(ssrPin, OUTPUT);
  pinMode(speakerPin, OUTPUT);
  pinMode(thermistorPin, INPUT);
  pinMode(inductiveSwitchPin, INPUT);
  pinMode(usbDetectPin, INPUT);  // USB detect input (optional)

  Serial.begin(9600);
  delay(500);  // Allow some time for Serial to start

  Serial.println("\n=== System (Re)Started! ===");

  // Uncomment this if you need to clear EEPROM once:
  // clearEEPROM();

  // Restore saved settings
  restoreSettings();

  // Immediately check the temperature so that SSR is set appropriately
  float startTemp = therm1.analog2temp();
  Serial.print("Startup Temperature Reading: ");
  Serial.print(startTemp);
  Serial.println(" °C");
  controlTemperature(startTemp);

  playChime();
}

void loop() {
  // Optional: Check USB state (if you have a proper USB detect circuit)
  checkUSBState();

  // Check emergency stop button
  if (digitalRead(inductiveSwitchPin) == HIGH) {
    Serial.println("Inductive Switch Pressed: Emergency Stop Activated!");
    emergencyStop();
    while (digitalRead(inductiveSwitchPin) == HIGH) {
      delay(100);
    }
  }

  static unsigned long lastUpdate = 0;
  unsigned long currentMillis = millis();

  // Temperature update every UPDATE_INTERVAL ms
  if (currentMillis - lastUpdate >= UPDATE_INTERVAL) {
    lastUpdate = currentMillis;
    float currentTemperature = therm1.analog2temp();
    Serial.print("Current Temperature: ");
    Serial.print(currentTemperature);
    Serial.print(" °C | Set Temperature: ");
    Serial.print(setTemperature);
    Serial.print(" °C | SSR State: ");
    Serial.println(digitalRead(ssrPin) ? "ON" : "OFF");

    controlTemperature(currentTemperature);
  }

  // Shutdown timer (if set via command)
  if (shutdownScheduled) {
    unsigned long elapsed = currentMillis - shutoffStartTime;
    static unsigned long lastPrintTime = 0;
    if (currentMillis - lastPrintTime >= 1000) {
      Serial.print("Shutdown countdown: ");
      Serial.print(elapsed);
      Serial.print(" ms elapsed (target: ");
      Serial.print(shutoffTime);
      Serial.println(" ms)");
      lastPrintTime = currentMillis;
    }
    if (elapsed >= shutoffTime) {
      shutdownScheduled = false;
      float currentTemperature = therm1.analog2temp();
      Serial.print("Shutdown Timer Elapsed. Current Temperature: ");
      Serial.print(currentTemperature);
      Serial.println(" °C");
      initiateShutdown();
    }
  }

  // Cooling Mode: if active, wait until temperature is below threshold for 10 seconds before turning off the fan
  if (cooling) {
    float currentTemperature = therm1.analog2temp();
    if (currentTemperature < SHUTOFF_TEMP_THRESHOLD) {
      if (coolingStartTime == 0) {
        coolingStartTime = millis();
      }
      if (millis() - coolingStartTime > 10000) {
        Serial.println("Cooling complete. Turning off fan.");
        turnFanOff();
        cooling = false;
        coolingStartTime = 0;
        beep();
        shutdownActive = false;
      }
    } else {
      coolingStartTime = 0; // reset timer if temperature rises
    }
  }

  // Process serial commands (if any)
  if (!shutdownActive && Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    // Beep every time a command is received
    beep();
    command.trim();
    // Debug: print received command
    Serial.print("Received command: ");
    Serial.println(command);
    // Handle the command (including EJECT below)
    handleCommands(command);
  }
}

/**
 * Checks the state of the USB detect pin.
 * (If you have proper hardware, this could auto-adjust on disconnect.)
 */
void checkUSBState() {
  // This function is left here for completeness.
  // Without a dedicated USB detection circuit, its output might not be reliable.
  bool usbNow = (digitalRead(usbDetectPin) == HIGH);
  // (We don't adjust setTemperature automatically here if not using EJECT command.)
  usbWasPlugged = usbNow;
}

/**
 * Controls the heater (SSR) based on current temperature vs. setTemperature.
 * No hysteresis is used so that even a 1°C difference causes a change.
 */
void controlTemperature(float currentTemp) {
  bool heaterOn;
  if (currentTemp < setTemperature) {
    heaterOn = true;
  } else {
    heaterOn = false;
  }
  digitalWrite(ssrPin, heaterOn ? HIGH : LOW);
}

/**
 * Handles incoming Serial commands.
 */
void handleCommands(String command) {
  command.trim();
  if (shutdownActive) {
    Serial.println("Shutdown in progress: Command ignored.");
    return;
  }

  // EJECT command: adjust the temperature target before disconnecting USB.
  if (command.equalsIgnoreCase("EJECT")) {
    Serial.println("DEBUG: EJECT command branch entered.");
    int oldSetTemp = setTemperature;
    // Adjust setTemperature 30° lower (so 60 becomes 30, for example)
    if (setTemperature >= 30)
      setTemperature -= 30;
    else
      setTemperature = 0;
    Serial.print("EJECT command received. Adjusted setTemperature from ");
    Serial.print(oldSetTemp);
    Serial.print(" to ");
    Serial.println(setTemperature);
    EEPROM.update(addrSetTemperature, setTemperature);
    beep();
    return; // Exit after processing EJECT
  }

  if (command == "FAN_ON") {
    turnFanOn(255);
    Serial.println("FAN_ON command executed.");
  } else if (command == "FAN_OFF") {
    turnFanOff();
    Serial.println("FAN_OFF command executed.");
  }

  if (command.startsWith("SET_FAN_PWM:")) {
    int pwmValue = command.substring(12).toInt();
    pwmValue = constrain(pwmValue, 0, 255);
    digitalWrite(fanSwitch_Pin, (pwmValue > 0) ? HIGH : LOW);
    analogWrite(fanPWM_Pin, pwmValue);
    EEPROM.update(addrFanPWMValue, pwmValue);
    Serial.print("Fan PWM set to ");
    Serial.println(pwmValue);
  }

  if (command.startsWith("SET_WINDER_PWM:")) {
    int pwmValue = command.substring(15).toInt();
    pwmValue = constrain(pwmValue, 0, 255);
    digitalWrite(winderMotorSwitch_Pin, (pwmValue > 0) ? HIGH : LOW);
    analogWrite(winderMotorPWM_Pin, pwmValue);
    EEPROM.update(addrWinderMotorPWMValue, pwmValue);
    Serial.print("Winder PWM set to ");
    Serial.println(pwmValue);
  }

  if (command == "WINDER_ON") {
    digitalWrite(winderMotorSwitch_Pin, HIGH);
    analogWrite(winderMotorPWM_Pin, 255);
    EEPROM.update(addrWinderMotorSwitchState, HIGH);
    Serial.println("Winder Motor is ON");
  } else if (command == "WINDER_OFF") {
    digitalWrite(winderMotorSwitch_Pin, LOW);
    analogWrite(winderMotorPWM_Pin, 0);
    EEPROM.update(addrWinderMotorSwitchState, LOW);
    Serial.println("Winder Motor is OFF");
  }

  if (command.startsWith("SET_SHUTDOWN_TIME:")) {
    Serial.println("Received SET_SHUTDOWN_TIME");
    int colonIndex = command.indexOf(':');
    if (colonIndex != -1) {
      unsigned long userShutdownTime = command.substring(colonIndex + 1).toInt();
      if (userShutdownTime > 0) {
        shutoffTime = userShutdownTime * 1000UL;
        shutoffStartTime = millis();
        shutdownScheduled = true;
        Serial.print("Shutdown scheduled in ");
        Serial.print(userShutdownTime);
        Serial.println(" seconds.");
      } else {
        Serial.println("Invalid shutdown time received.");
      }
    } else {
      Serial.println("Invalid SET_SHUTDOWN_TIME command format.");
    }
  }

  if (command.startsWith("SET_TEMP:")) {
    int tempValue = command.substring(9).toInt();
    if (tempValue >= 0) {
      setTemperature = tempValue;
      EEPROM.update(addrSetTemperature, setTemperature);
      Serial.print("Set Temperature updated to ");
      Serial.print(setTemperature);
      Serial.println(" °C");
    } else {
      Serial.println("Invalid temperature value received.");
    }
  }
}

/**
 * Initiates the shutdown sequence.
 * In addition to turning off the winder and activating cooling mode,
 * this function also sets the setTemperature to 0 so that heating is turned off.
 */
void initiateShutdown() {
  Serial.println("Initiating shutdown sequence.");
  
  // Set target temperature to 0 (turn heater off)
  setTemperature = 0;
  EEPROM.update(addrSetTemperature, setTemperature);
  Serial.println("Set Temperature set to 0 °C.");
  
  shutdownActive = true;
  digitalWrite(winderMotorSwitch_Pin, LOW);
  analogWrite(winderMotorPWM_Pin, 0);
  Serial.println("Winder Motor turned OFF.");
  
  // Turn on the fan at low speed for cooling mode
  digitalWrite(fanSwitch_Pin, HIGH);
  analogWrite(fanPWM_Pin, 1);
  EEPROM.update(addrFanSwitchState, HIGH);
  EEPROM.update(addrFanPWMValue, 1);
  Serial.println("Fan turned ON in cooling mode (PWM=1).");
  
  cooling = true;
  playShutdownChime();
}

/**
 * Performs an immediate emergency stop.
 */
void emergencyStop() {
  Serial.println("Emergency Stop Activated!");
  turnFanOff();
  digitalWrite(ssrPin, LOW);
  digitalWrite(winderMotorSwitch_Pin, LOW);
  analogWrite(winderMotorPWM_Pin, 0);
  EEPROM.update(addrWinderMotorPWMValue, 0);
  shutdownScheduled = false;
  cooling = false;
  for (int i = 0; i < 3; i++) {
    for (int j = 0; j < 100; j++) {
      digitalWrite(speakerPin, HIGH);
      delayMicroseconds(500);
      digitalWrite(speakerPin, LOW);
      delayMicroseconds(500);
    }
    delay(100);
  }
}

/**
 * Beep sound for feedback.
 */
void beep() {
  for (int i = 0; i < 2; i++) {
    for (int j = 0; j < 100; j++) {
      digitalWrite(speakerPin, HIGH);
      delayMicroseconds(500);
      digitalWrite(speakerPin, LOW);
      delayMicroseconds(500);
    }
    delay(200);
  }
}

/**
 * Short startup chime.
 */
void playChime() {
  for (int i = 0; i < 100; i++) {
    digitalWrite(speakerPin, HIGH);
    delayMicroseconds(500);
    digitalWrite(speakerPin, LOW);
    delayMicroseconds(500);
  }
}

/**
 * Longer shutdown chime.
 */
void playShutdownChime() {
  for (int i = 0; i < 200; i++) {
    digitalWrite(speakerPin, HIGH);
    delayMicroseconds(500);
    digitalWrite(speakerPin, LOW);
    delayMicroseconds(500);
  }
}

/**
 * Restores settings from EEPROM.
 */
void restoreSettings() {
  int fanState = EEPROM.read(addrFanSwitchState);
  digitalWrite(fanSwitch_Pin, fanState);
  int fanPWM = EEPROM.read(addrFanPWMValue);
  analogWrite(fanPWM_Pin, fanPWM);

  int winderMotorState = EEPROM.read(addrWinderMotorSwitchState);
  digitalWrite(winderMotorSwitch_Pin, winderMotorState);
  int winderMotorPWM = EEPROM.read(addrWinderMotorPWMValue);
  analogWrite(winderMotorPWM_Pin, winderMotorPWM);

  int readTemp = EEPROM.read(addrSetTemperature);
  if (readTemp == 0xFF) { 
    readTemp = 10;
  }
  setTemperature = readTemp;

  Serial.println("Settings restored from EEPROM.");
}

/**
 * Clears EEPROM (only call once if needed).
 */
void clearEEPROM() {
  EEPROM.write(addrFanSwitchState, LOW);
  EEPROM.write(addrFanPWMValue, 0);
  EEPROM.write(addrWinderMotorSwitchState, LOW);
  EEPROM.write(addrWinderMotorPWMValue, 0);
  EEPROM.write(addrSetTemperature, 10);
  Serial.println("EEPROM cleared and settings reset to default.");
}
