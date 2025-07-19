const int potPin = A0;           // Potentiometer for character selection
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

int currentMode = 0;              // Start in lowercase letters (mode 0)
bool capsLock = false;            // Track uppercase state for letters
int selectedCharIndex = 0;        
int lastPrintedCharIndex = -1;    // Track last displayed character
int lastPrintedMode = -1;         // Track last displayed mode

// Variables for double press detection (now for mode button)
unsigned long lastModePressTime = 0;
bool modeSinglePress = false;

void setup() {
  Serial.begin(9600);
  pinMode(modeButtonPin, INPUT_PULLUP);
  pinMode(confirmButtonPin, INPUT_PULLUP);
  pinMode(escButtonPin, INPUT_PULLUP);
  Serial.println("Dial Keyboard Ready. Mode: Lowercase Letters");
}

void loop() {
  // Read potentiometer and map to current mode's character range
  int potValue = analogRead(potPin);
  selectedCharIndex = map(potValue, 0, 670, strlen(modes[currentMode]) - 1, 0);
  
  // Only update display if selection or mode changed
  if (selectedCharIndex != lastPrintedCharIndex || currentMode != lastPrintedMode) {
    char selectedChar = modes[currentMode][selectedCharIndex];
    
    Serial.print("Selected: ["); 
    Serial.print(selectedChar); 
    Serial.print("] | Mode: "); 
    Serial.println(getModeName(currentMode));
    
    lastPrintedCharIndex = selectedCharIndex;
    lastPrintedMode = currentMode;
  }

  // Handle button presses
  handleModeButton();
  handleConfirmButton();
  handleEscButton();

  // Check for double press timeout (mode button)
  if (modeSinglePress && (millis() - lastModePressTime > doublePressDelay)) {
    modeSinglePress = false;
  }

  delay(100);
}

// --- Button Handlers ---
void handleModeButton() {
  static unsigned long pressStart = 0;
  static bool wasPressed = false;
  bool isPressed = digitalRead(modeButtonPin) == LOW;

  if (isPressed && !wasPressed) {
    pressStart = millis();
    wasPressed = true;
  }

  if (!isPressed && wasPressed) {
    unsigned long pressDuration = millis() - pressStart;
    
    if (pressDuration < holdDelay) {
      // First check if this is a double press
      if (millis() - lastModePressTime < doublePressDelay && modeSinglePress) {
        // Double press detected - ENTER
        Serial.println("Enter");
        modeSinglePress = false;
        lastModePressTime = 0; // Reset to prevent accidental triple-press detection
      } else {
        // Not a double press (yet) - just record the press time
        modeSinglePress = true;
        lastModePressTime = millis();
      }
    } else {
      // Handle long press (caps lock toggle)
      if (currentMode == 0 || currentMode == 1) {
        capsLock = !capsLock;
        currentMode = capsLock ? 1 : 0;
        Serial.print("Caps Lock: ");
        Serial.println(capsLock ? "ON" : "OFF");
      }
      modeSinglePress = false; // Cancel any pending double press
    }
    wasPressed = false;
  }

  // Handle single press mode change after double-press window expires
  if (modeSinglePress && (millis() - lastModePressTime > doublePressDelay)) {
    currentMode = (currentMode + 1) % 4;
    Serial.print("Mode switched to: ");
    Serial.println(getModeName(currentMode));
    modeSinglePress = false;
  }
}

void handleConfirmButton() {
  static unsigned long pressStart = 0;
  static bool wasPressed = false;
  bool isPressed = digitalRead(confirmButtonPin) == LOW;

  if (isPressed && !wasPressed) {
    pressStart = millis();
    wasPressed = true;
  }

  if (!isPressed && wasPressed) {
    if (millis() - pressStart < holdDelay) {
      // Tap: Confirm selected character
      Serial.print("Confirmed: ");
      Serial.println(modes[currentMode][selectedCharIndex]);
    } else {
      // Hold: Insert space
      Serial.println("Space inserted");
    }
    wasPressed = false;
  }
}

void handleEscButton() {
  static unsigned long pressStart = 0;
  static bool wasPressed = false;
  bool isPressed = digitalRead(escButtonPin) == LOW;

  if (isPressed && !wasPressed) {
    pressStart = millis();
    wasPressed = true;
  }

  if (!isPressed && wasPressed) {
    if (millis() - pressStart < holdDelay) {
      // Tap: Cancel/ESC action
      Serial.println("ESC pressed");
    } else {
      // Hold: Backspace
      Serial.println("Backspace");
    }
    wasPressed = false;
  }
}

const char* getModeName(int mode) {
  switch (mode) {
    case 0: return "Lowercase Letters";
    case 1: return "Uppercase Letters";
    case 2: return "Numbers/Symbols";
    case 3: return "Punctuation";
    default: return "Unknown";
  }
}