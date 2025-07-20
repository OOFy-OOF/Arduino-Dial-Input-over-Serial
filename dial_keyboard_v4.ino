const int potPin = A0;           // Potentiometer for character selection
const int potRange = 670;        // Potentiometer range (0-potRange)
const int modeButtonPin = 10;    // Button to switch modes (Letters/Numbers/Punctuation)
const int confirmButtonPin = 11; // Button to confirm selection
const int escButtonPin = 12;     // Button for ESC/Backspace
const int holdDelay = 300;       // Time to register a "hold" action
const int doublePressDelay = 500; // Max time between presses to count as double press

// Character sets for each mode (lowercase default)
const char* modes[] = {
  "abcdefghijklmnopqrstuvwxyz",  // Lowercase letters (default)
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ",  // Uppercase letters (activated via hold)
  "0123456789$%#@&",             // Numbers/Symbols
  ".,!?;:'\"-()/\\ "             // Punctuation/Space
};

int currentMode = 0;
bool capsLock = false;
int selectedCharIndex = 0;
int lastPrintedCharIndex = -1;
int lastPrintedMode = -1;

// Double press tracking
unsigned long lastModePressTime = 0;
bool modeSinglePress = false;

enum ButtonAction {
  NONE,
  TAP,
  HOLD
};

// --- Setup ---
void setup() {
  Serial.begin(9600);
  pinMode(modeButtonPin, INPUT_PULLUP);
  pinMode(confirmButtonPin, INPUT_PULLUP);
  pinMode(escButtonPin, INPUT_PULLUP);
  Serial.println("Dial Keyboard Ready. Mode: Lowercase Letters");
}

// --- Main Loop ---
void loop() {
  int potValue = analogRead(potPin);
  selectedCharIndex = map(potValue, 0, potRange, strlen(modes[currentMode]) - 1, 0);

  if (selectedCharIndex != lastPrintedCharIndex || currentMode != lastPrintedMode) {
    char selectedChar = modes[currentMode][selectedCharIndex];

    Serial.print("Selected: [");
    Serial.print(selectedChar);
    Serial.print("] | Mode: ");
    Serial.println(getModeName(currentMode));

    lastPrintedCharIndex = selectedCharIndex;
    lastPrintedMode = currentMode;
  }

  handleModeButton();
  handleConfirmButton();
  handleEscButton();

  // Timeout check for single press on mode button
  if (modeSinglePress && (millis() - lastModePressTime > doublePressDelay)) {
    currentMode = (currentMode + 1) % 4;
    Serial.print("Mode switched to: ");
    Serial.println(getModeName(currentMode));
    modeSinglePress = false;
  }
  //removed delay as it was causing double press to be inconsistent
}

// --- Button State Checker ---
ButtonAction checkButtonPress(int pin, unsigned long& pressStart, bool& wasPressed, int holdThreshold = holdDelay) {
  bool isPressed = digitalRead(pin) == LOW;

  if (isPressed && !wasPressed) {
    pressStart = millis();
    wasPressed = true;
  }

  if (!isPressed && wasPressed) {
    wasPressed = false;
    if (millis() - pressStart < holdThreshold) return TAP;
    else return HOLD;
  }

  return NONE;
}

// --- Button Handlers ---

void handleModeButton() {
  static unsigned long pressStart = 0;
  static bool wasPressed = false;
  static bool firstTapWaiting = false;

  ButtonAction action = checkButtonPress(modeButtonPin, pressStart, wasPressed);

  if (action == TAP) {
    if (firstTapWaiting) {
      // Second tap within window → Double press detected
      Serial.println("Enter");
      firstTapWaiting = false;
    } else {
      // First tap → start timer and wait for second
      firstTapWaiting = true;
      lastModePressTime = millis();
    }
  } else if (action == HOLD) {
    // Hold → Caps lock toggle (only in letter modes)
    if (currentMode == 0 || currentMode == 1) {
      capsLock = !capsLock;
      currentMode = capsLock ? 1 : 0;
      Serial.print("Caps Lock: ");
      Serial.println(capsLock ? "ON" : "OFF");
    }
    firstTapWaiting = false; // Cancel pending double press
  }

  // Check if first tap timeout passed → single press mode switch
  if (firstTapWaiting && (millis() - lastModePressTime > doublePressDelay)) {
    currentMode = (currentMode + 1) % 4;
    Serial.print("Mode switched to: ");
    Serial.println(getModeName(currentMode));
    firstTapWaiting = false;
  }
}


void handleConfirmButton() {
  static unsigned long pressStart = 0;
  static bool wasPressed = false;

  ButtonAction action = checkButtonPress(confirmButtonPin, pressStart, wasPressed);

  if (action == TAP) {
    Serial.print("Confirmed: ");
    Serial.println(modes[currentMode][selectedCharIndex]);
  } else if (action == HOLD) {
    Serial.println("Space inserted");
  }
}

void handleEscButton() {
  static unsigned long pressStart = 0;
  static bool wasPressed = false;

  ButtonAction action = checkButtonPress(escButtonPin, pressStart, wasPressed);

  if (action == TAP) {
    Serial.println("ESC pressed");
  } else if (action == HOLD) {
    Serial.println("Backspace");
  }
}

// --- Mode Name Helper ---
const char* getModeName(int mode) {
  switch (mode) {
    case 0: return "Lowercase";
    case 1: return "Uppercase";
    case 2: return "Num/Sym";
    case 3: return "Punctuation";
    default: return "Unknown";
  }
}
