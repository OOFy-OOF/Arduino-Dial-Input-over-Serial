# Arduino-Dial-Input-over-Serial
Code for a simple scrolling input method using potentiometer and a few buttons. Given that the Arduino UNO R3 I am using cannot communicate with PC as an HID device unless the user decides to flash custom firmware, I have decided to make an implementation based on reading the serial output instead.

The switches used in my example are Omron B3WNs and the potentiometer is a common 10k ohm one (306E). A few 4,7k resistors are used as well.

<img width="1272" height="601" alt="circuit" src="https://github.com/user-attachments/assets/03855a34-4778-40aa-a04d-c2036dd9fc1b" />

<img width="696" height="453" alt="image" src="https://github.com/user-attachments/assets/3c154c02-0140-45f7-8d87-53a98468e5f9" />

Only Windows support so far, executable builds are made using Auto py to exe.

## Troubleshooting:
### Executable related:

