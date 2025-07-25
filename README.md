# Arduino-Dial-Input-over-Serial
Fun little project for a simple scrolling input method using a potentiometer and a few buttons. Given that the Arduino Uno R3 I am using cannot communicate with the PC as an HID device unless the user decides to flash custom firmware, I have decided to implement a solution based on reading the serial output instead.

The switches used in my example are Omron B3WNs, and the potentiometer is a common 10k ohm one (306E).

<img width="1272" height="577" alt="Ingenious Maimu-Hillar" src="https://github.com/user-attachments/assets/8c8105c4-b208-4480-bcf9-43ddcfb9c58d" />

Only Windows support for now, executable builds are made using [Auto-py-to-exe](https://github.com/brentvollebregt/auto-py-to-exe).

### Simulate on Tinkercad here: [link](https://www.tinkercad.com/things/fv0Ro02MSqS-arduino-dial-input-over-serial?sharecode=JySeBymt0gb-Ecbg5eRF3zyH4_SAuhMBrEvMna6M8d8)

<br>

## Installation:
### 1. Download the .zip from Releases

<img width="1323" height="364" alt="image" src="https://github.com/user-attachments/assets/1b0d386e-fed3-4f9d-81d4-ec2456391a6b" />

### 2. Unzip on your PC, you should find these files inside the folder:

<img width="656" height="122" alt="image" src="https://github.com/user-attachments/assets/284212c5-e7a5-4128-89b3-05610174bf64" />

### 3. Upload the .ino file to the Arduino using Arduino IDE

<img width="635" height="60" alt="image" src="https://github.com/user-attachments/assets/eb78ec93-98eb-428c-b4d9-50efd589c72c" />

Close the IDE when complete.
### 4. Run the .exe

<img width="1037" height="93" alt="image" src="https://github.com/user-attachments/assets/4b22ff44-4318-4237-a39b-01c891b3d08e" />

### DONE!!!


<br>

## Troubleshooting:
### Executable related:
On first launch, if you receive the following error:

<img width="228" height="172" alt="image" src="https://github.com/user-attachments/assets/603e99b2-4295-4e1e-9c62-d414f4ed4c34" />

Please make sure you are using the correct COM port for your connection by changing it in the settings, then click restart. 

<img width="609" height="415" alt="image" src="https://github.com/user-attachments/assets/ed3442b7-263a-4b28-8f7a-2eb8a01102fe" />

You can check the COM port your Arduino is using in Arduino IDE.

### Set-up related:
If you are unable to input the full range of characters (a-z), note that in the sketch (.ino) file for the Arduino, the potentiometer range is set from 0 to 670 for my particular setup. If you are using a different potentiometer, please change the range to something appropriate for your components. (Refer [here](https://github.com/OOFy-OOF/Arduino-Dial-Input-over-Serial/wiki#%EF%B8%8F-configuration-constants))

### Still not working?
Make sure no other program (for example, Arduino IDE) is accessing your COM port while attempting to run this program; this will prevent it from receiving data. Also, make sure you don't already have an instance running. If the window is hidden, just force close it in Task Manager.

## Known Issues:
* ~~Closing the settings menu without saving and restarting causes the UI to never time out.~~ (fixed, now the main window hides itself anyways)
* ~~Button gestures with MODE are jank because too many variations.~~ (Maybe fixed???)
* buggy behaviour with window when waking from background
* You tell me :D

## More Documentation:
Refer to [Wiki](https://github.com/OOFy-OOF/Arduino-Dial-Input-over-Serial/wiki)

