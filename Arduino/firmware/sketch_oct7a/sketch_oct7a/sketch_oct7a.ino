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

// EEPROM addresses for each setting
const int addrFanSwitchState = 0;
const int addrFanPWMValue = 1;
const int addrWinderMotorSwitchState = 2;
const int addrWinderMotorPWMValue = 3;
const int addrSetTemperature = 4;       // Address to store set temperature

int setTemperature = 10;                // Default temperature (°C)

thermistor therm1(thermistorPin, 0);      // Initialize thermistor

#define HYSTERESIS 1                    // °C hysteresis to prevent rapid toggling
#define UPDATE_INTERVAL 100             // Update interval in milliseconds

// Shutdown Timer Variables
unsigned long shutoffTime = 0;          // In milliseconds
unsigned long shutoffStartTime = 0;
bool shutdownScheduled = false;

// Cooling Mode Variables
bool cooling = false;
unsigned long coolingStartTime = 0;     // Used to delay turning the fan off

// New global flag to block further commands once shutdown is active
bool shutdownActive = false;

const float SHUTOFF_TEMP_THRESHOLD = 35.0; // Temperature threshold in °C

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

// --- Helper functions for fan control ---
// For your wiring, setting fanSwitch_Pin HIGH turns the fan on.
// The PWM output on fanPWM_Pin controls the fan speed.
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
  pinMode(inductiveSwitchPin, INPUT);  // Set inductive switch as input

  Serial.begin(9600);  // Start serial communication for debugging

  // Uncomment the following line to clear EEPROM if needed
  // clearEEPROM();

  // Restore saved settings and play startup chime
  restoreSettings();
  playChime();
}

void loop() {
  // Check emergency stop button (inductive switch)
  if (digitalRead(inductiveSwitchPin) == HIGH) {
    Serial.println("Inductive Switch Pressed: Emergency Stop Activated!");
    emergencyStop();
    // Wait until the switch is released to prevent multiple triggers.
    while (digitalRead(inductiveSwitchPin) == HIGH) {
      delay(100);
    }
  }

  static unsigned long lastUpdate = 0;
  unsigned long currentMillis = millis();

  // Update temperature and control SSR every UPDATE_INTERVAL milliseconds
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

  // Check if shutdown timer has elapsed (print countdown once per second)
  if (shutdownScheduled) {
    unsigned long elapsed = currentMillis - shutoffStartTime;
    static unsigned long lastPrintTime = 0;
    if (currentMillis - lastPrintTime >= 1000) {  // Print once per second
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

  // Cooling Mode: When cooling mode is active, the fan remains on (PWM = 1)
  // until the temperature remains below the threshold for 10 continuous seconds.
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
        beep();  // Indicate cooling complete
        // Allow new commands after cooldown is complete.
        shutdownActive = false;
      }
    } else {
      coolingStartTime = 0;  // Reset the timer if temperature rises
    }
  }

  // Process incoming serial commands only if shutdown is not active.
  if (!shutdownActive && Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    // Beep immediately for every received command
    beep();
    handleCommands(command);
  }
}

void controlTemperature(float currentTemp) {
  static bool ssrEnabled = false;
  if (currentTemp < setTemperature - HYSTERESIS && !ssrEnabled) {
    digitalWrite(ssrPin, HIGH);
    ssrEnabled = true;
    Serial.println("SSR turned ON");
  } else if (currentTemp > setTemperature + HYSTERESIS && ssrEnabled) {
    digitalWrite(ssrPin, LOW);
    ssrEnabled = false;
    Serial.println("SSR turned OFF");
  }
}

void handleCommands(String command) {
  command.trim();  // Remove any extraneous whitespace
  
  // If shutdown is active, ignore further commands.
  if (shutdownActive) {
    Serial.println("Shutdown in progress: Command ignored.");
    return;
  }
  
  if (command == "FAN_ON") {
    turnFanOn(255);  // Full speed when manually commanded.
    Serial.println("FAN_ON command executed.");
  }
  else if (command == "FAN_OFF") {
    turnFanOff();
    Serial.println("FAN_OFF command executed.");
  }

  if (command.startsWith("SET_FAN_PWM:")) {
    int pwmValue = command.substring(12).toInt();
    pwmValue = constrain(pwmValue, 0, 255);
    if (pwmValue > 0) {
      digitalWrite(fanSwitch_Pin, HIGH);
    } else {
      digitalWrite(fanSwitch_Pin, LOW);
    }
    analogWrite(fanPWM_Pin, pwmValue);
    EEPROM.update(addrFanPWMValue, pwmValue);
    Serial.print("Fan PWM set to ");
    Serial.println(pwmValue);
  }

  // New command for setting winder PWM.
  if (command.startsWith("SET_WINDER_PWM:")) {
    int pwmValue = command.substring(15).toInt();
    pwmValue = constrain(pwmValue, 0, 255);
    if (pwmValue > 0) {
      digitalWrite(winderMotorSwitch_Pin, HIGH);
    } else {
      digitalWrite(winderMotorSwitch_Pin, LOW);
    }
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
  }
  else if (command == "WINDER_OFF") {
    digitalWrite(winderMotorSwitch_Pin, LOW);
    analogWrite(winderMotorPWM_Pin, 0);
    EEPROM.update(addrWinderMotorSwitchState, LOW);
    Serial.println("Winder Motor is OFF");
  }

  // The shutdown command now only sets the timer.
  if (command.startsWith("SET_SHUTDOWN_TIME:")) {
    Serial.println("Received SET_SHUTDOWN_TIME");
    int colonIndex = command.indexOf(':');
    if (colonIndex != -1) {
      unsigned long userShutdownTime = command.substring(colonIndex + 1).toInt();
      if (userShutdownTime > 0) {
        shutoffTime = userShutdownTime * 1000; // Convert seconds to milliseconds
        shutoffStartTime = millis();
        shutdownScheduled = true;
        Serial.print("SET_SHUTDOWN_TIME command executed: Shutdown scheduled in ");
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

void initiateShutdown() {
  Serial.println("Initiating shutdown sequence.");
  // Block further commands.
  shutdownActive = true;

  // Set temperature to 0°C to turn off the heater.
  setTemperature = 0;
  EEPROM.update(addrSetTemperature, setTemperature);
  Serial.println("Set Temperature set to 0°C to turn off heater.");

  // Turn off the spool motor.
  digitalWrite(winderMotorSwitch_Pin, LOW);
  analogWrite(winderMotorPWM_Pin, 0);
  Serial.println("Winder Motor turned OFF.");

  // Turn off the heater.
  digitalWrite(ssrPin, LOW);
  Serial.println("Heater (SSR) turned OFF.");

  // Turn on the fan in cooling mode: switch HIGH and PWM set to 1.
  digitalWrite(fanSwitch_Pin, HIGH);
  analogWrite(fanPWM_Pin, 1);
  EEPROM.update(addrFanSwitchState, HIGH);
  EEPROM.update(addrFanPWMValue, 1);
  Serial.println("Fan turned ON in cooling mode with PWM set to 1.");

  // Enter cooling mode.
  cooling = true;
  playShutdownChime();
}

void emergencyStop() {
  Serial.println("Emergency Stop Activated!");
  // Immediately shut down all outputs.
  turnFanOff();
  digitalWrite(ssrPin, LOW);
  digitalWrite(winderMotorSwitch_Pin, LOW);
  analogWrite(winderMotorPWM_Pin, 0);
  EEPROM.update(addrWinderMotorPWMValue, 0);
  // Cancel any scheduled shutdown or cooling mode.
  shutdownScheduled = false;
  cooling = false;
  // Provide an audible alert for emergency stop.
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

void playChime() {
  for (int i = 0; i < 100; i++) {
    digitalWrite(speakerPin, HIGH);
    delayMicroseconds(500);
    digitalWrite(speakerPin, LOW);
    delayMicroseconds(500);
  }
}

void playShutdownChime() {
  for (int i = 0; i < 200; i++) {
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

  setTemperature = EEPROM.read(addrSetTemperature);
  if (setTemperature == 0xFF) {  // If EEPROM not set, default to 10°C
    setTemperature = 10;
  }

  Serial.println("Settings restored from EEPROM.");
}

void clearEEPROM() {
  EEPROM.write(addrFanSwitchState, LOW);
  EEPROM.write(addrFanPWMValue, 0);
  EEPROM.write(addrWinderMotorSwitchState, LOW);
  EEPROM.write(addrWinderMotorPWMValue, 0);
  EEPROM.write(addrSetTemperature, 10);
  Serial.println("EEPROM cleared and settings reset to default.");
}
