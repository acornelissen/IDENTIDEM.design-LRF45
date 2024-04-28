# LRF45 4x5 Rangefinder Source Code

This is the Circuitpython 8.x code that powers the LRF45: a (mostly) 3D-printed, LiDAR powered, electronically-coupled large format rangefinder. It also has a built-in light-meter!

[The build guide and 3D-printer files are all on Printables](https://www.printables.com/model/718784-lrf45-a-large-format-4x5-rangefinder).

## Hardware
- 1 x Adafruit Feather RP2040
- 1 x Adafruit MiniBoost 5V @ 1A (this is to power the TF-LUNA, which requires 5v operating voltage)
- 1 x TF-LUNA LiDAR sensor
- 1 x Adafruit VCNL4040 Proximity and Lux Sensor
- 1 x Adafruit BH1750 Light Sensor
- 1 x Adafruit Monochrome 1.12" 128x128 OLED Graphic Display
- 2 x 8mm Momentary Push Button Switch
- 1 x 3-Position SPDT Slide Switch 10x5x5mm
- 2 x 10k Ohm resistor
- 2 x 100mm STEMMA QT cable
- 1 x 400mm STEMMA QT cable
- 1 x 3.7V 820mAh 653042 Lipo (30.5 x 44 x 6.8mm)
- 1 x Custom LRF45 PCB

## Required CircuitPython 8.x Libraries
- adafruit_bh1750
- adafruit_vcnl4040
- adafruit_tfmini
- adafruit_displayio_sh1107
- adafruit_display_text
- adafruit_display_shapes
- asyncio

## Set things up for your own use

### Light meter constants
In `code.py:62-63` you can add or remove ISOs and Apertures as desired for the light meter.

### Rangefinder constants
The following values will need to be adjusted for your lens and helicoid.
Sensor readings are from the lens sensor and because of the nature of 3D printing and plastic, your values may vary.

These values are for a Fujinon-W 105mm f/5.6 lens in a 17-31mm M65 helicoid in `code.py:75-82`:
```
CLOSE_FOCUS_CM = 85 # Close focus distance in cm
CLOSE_FOCUS = 68 # Close focus sensor reading
INF_FOCUS_CM = 560 # Infinity focus distance in cm
INF_FOCUS = 875 # Infinity focus sensor reading

# Lomograflok rangefinder constants and variables
CLOSE_FOCUS_CM_LG = 50 # Close focus distance in cm
INF_FOCUS_CM_LG = 60 # Infinity focus distance in cm
```

How do you get these values? A little bit of leg-work is required.

USE A TRIPOD AND A FOCUS TARGET like https://www.squit.co.uk/photo/focuschart.html
1. Using ground glass, focus to target at its closest and infinity, lens wide open, and take note of the LiDAR reading where the target is in focus - see `code.py:388`
2. Take note of the lens sensor reading the helicoid's minimum extension (infinity) and maximum extension (close focus)
3. Set `CLOSE_FOCUS` and `INF_FOCUS` to those values 
4. Set `CLOSE_FOCUS_CM` and `INF_FOCUS_CM` to the distance in cm measured from LiDAR
7. Test your new values by checking focus at infinity and close focus, as well as a few points in between
8. Repeat until you get it right - tedious, but worth it once you dial it in!

Feel free to use this code in your own projects, fork it, whatever.