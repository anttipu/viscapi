# Viscapi

Viscapi is a python program used with Raspberry Pi to control a PTZ camera with Visca protocol.

## Needed hardware

To use Viscapi, you will need the following pieces of hardware:
* Raspberry Pi
* USB to Serial converter
* Any kind of controller that is supported by pygame library
** For example Logitech Extreme 3D PRO joystick or Playstation controller
* Telycam PTZ camera (in theory should work with any PTZ camera with serial Visca support)

## Needed software

Modified version of Pysca Python library which can be found from https://github.com/anttipu/pysca-telycam

## Usage

Use joystick to control PTZ camera

[joystick]: joystick.jpg "Joystick"
![Joystick](https://github.com/anttipu/viscapi/blob/master/joystick.jpg)

* Use joystick X and Y axis to control camera Pan and Tilt
* Twist joystick to control zoom ("TWIST ZOOM" is disabled by default)
* Use joystick hat up or down to control zoom
* Use joystick hat left or right to set camera to manual focus and control manual focus
* Press "FOCUS TRIG" to set focus to auto and trigger auto focus
* Use "SPEED ADJ" to control movement sensitivity
* Press and hold "SET" and press joystick button labeled 3, 4, 5 or 6 to store PTZ position
* Press joystick button labeled 3, 4, 5 or 6 to recall a stored position
* Pess and hold "MAN WB" and use hat up/down left/right to set camera to manual white balance and control blue and red channel
* Press "AUTO WB" to set camera to auto white balance
* Press "YES" or "NO" for TWIST ZOOM to enable or disable twist zoom (disabled by default on every power up)
* Press "YES" or "NO" for TILT INVERT to invert tilt (disabled by default on every power up)

## Installation instructions

Read misc/readme.txt
