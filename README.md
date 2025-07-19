# Arduino-Dial-Input-over-Serial
Fun little project for a simple scrolling input method using a potentiometer and a few buttons. Given that the Arduino Uno R3 I am using cannot communicate with the PC as an HID device unless the user decides to flash custom firmware, I have decided to implement a solution based on reading the serial output instead.

The switches used in my example are Omron B3WNs, and the potentiometer is a common 10k ohm one (306E). A few 4,7k resistors are used as well.

<img width="1272" height="601" alt="circuit" src="https://github.com/user-attachments/assets/03855a34-4778-40aa-a04d-c2036dd9fc1b" />

<img width="696" height="453" alt="image" src="https://github.com/user-attachments/assets/3c154c02-0140-45f7-8d87-53a98468e5f9" />

Only Windows support for now, executable builds are made using Auto-py-to-exe.


<br>

## Installation:
### 1. Upload the .ino file to the Arduino using Arduino IDE

<img width="635" height="60" alt="image" src="https://github.com/user-attachments/assets/eb78ec93-98eb-428c-b4d9-50efd589c72c" />

Close the IDE when complete.
### 2. Run the .exe

<img width="1037" height="93" alt="image" src="https://github.com/user-attachments/assets/4b22ff44-4318-4237-a39b-01c891b3d08e" />

### DONE!!!


<br>

## Troubleshooting:
### Executable related:
On first launch, if you receive the following error:

<img width="323" height="201" alt="image" src="https://github.com/user-attachments/assets/1d38e424-69ac-4e34-940c-a5ff55e3184d" />

Please make sure you are using the correct COM port for your connection by changing it in the settings, then click restart. 

<img width="609" height="415" alt="image" src="https://github.com/user-attachments/assets/ed3442b7-263a-4b28-8f7a-2eb8a01102fe" />

You can check the COM port your Arduino is using in Arduino IDE.

### Set-up related:
If you are unable to input the full range of characters (a-z), note that in the sketch (.ino) file for the Arduino, the potentiometer range is set from 0 to 670 for my particular setup. If you are using a different potentiometer, please change the range to something appropriate for your components. 

<img width="935" height="120" alt="image" src="https://github.com/user-attachments/assets/4e2cce98-64a9-480f-8893-aa8f51043c65" />

### Still not working?
Make sure no other program (for example, Arduino IDE) is accessing your COM port while trying to run the program; this will prevent it from receiving data.



