import asyncio
import board
import keypad
import time
import os
import math
import terminalio
import displayio
import digitalio
import analogio
import adafruit_bh1750
import adafruit_vcnl4040
import adafruit_tfmini
import json
import storage
from adafruit_displayio_sh1107 import SH1107, DISPLAY_OFFSET_ADAFRUIT_128x128_OLED_5297
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.rect import Rect
from ulab import numpy

# Hardware init
# =============================================================================
# Battery monitor pin (ADC3)
adc_batt = analogio.AnalogIn(board.A3)

# Create the I2C and UART interface.
i2c = board.STEMMA_I2C()
uart = board.UART()

# Light sensor init
lsen = adafruit_bh1750.BH1750(i2c)
K = 20  # constant for lightmeter

# LiDAR and ToF init
tfluna = adafruit_tfmini.TFmini(uart)
lr = adafruit_vcnl4040.VCNL4040(i2c)

# Set low power mode for LiDAR
samp_rate_packet = bytes([0x5a,0x06,0x03,35,00,00])
uart.write(samp_rate_packet)

# Create the SSD1306 OLED class and mirror display
displayio.release_displays()
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 128
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D)
display = SH1107(
    display_bus,
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    display_offset=DISPLAY_OFFSET_ADAFRUIT_128x128_OLED_5297,
    rotation=0,
)
display.root_group.hidden = True
display_bus.send(0xC9, b"")  # Bus command to mirror display
# =============================================================================

# Constants
# =============================================================================
# Aperture and ISO constants - change this to match your lens and film stocks
APERTURES = [1.8, 2, 2.8, 4.5, 5.6, 8, 11, 16, 22, 32, 45, 64]
ISOS = [100, 125, 400, 800, 1600, 3200]

# Rangefinder constants and variables
"""
For a Fujinon-W 105mm f/5.6 lens in a 17-31mm M65 helicoid - these values will need to be adjusted for your lens and helicoid.
Sensor readings are from the lens sensor and because of the nature of 3D printing and plastic, your values may vary.

CLOSE_FOCUS_CM = 85 # Close focus distance in cm
CLOSE_FOCUS = 68 # Close focus sensor reading
INF_FOCUS_CM = 560 # Infinity focus distance in cm
INF_FOCUS = 875 # Infinity focus sensor reading
"""
CLOSE_FOCUS_CM = 85 # Close focus distance in cm
CLOSE_FOCUS = 27 # Close focus sensor reading
INF_FOCUS = 181 # Infinity focus sensor reading
CLOSE_FOCUS_CM = 85  # Close focus distance in cm
CLOSE_FOCUS = 71 # Close focus sensor reading
INF_FOCUS_CM = 780 # Infinity focus distance in cm
INF_FOCUS = 860 # Infinity focus sensor reading

# Lomograflok rangefinder constants and variables
CLOSE_FOCUS_CM_LG = 50 # Close focus distance in cm
INF_FOCUS_CM_LG = 60 # Infinity focus distance in cm

# Interface constants
FRAME_LENGTH = 128
FRAME_HEIGHT = 99
FRAME_OFFSET_X = 0
FRAME_OFFSET_Y = 28
LENS_OFFSET = 1035 # For parallax correction
LENS_DIVISOR = 1375 # For parallax correction
CIRCLE_X = 68
CIRCLE_Y = 80
CIRCLE_X_MAX = 85
CIRCLE_Y_MAX = 60
# =============================================================================



# Helper functions
# =============================================================================
def load_config(state):
    try:
        with open("config.json", "r") as f:
            loaded_config = json.load(f)

            state.iso = loaded_config.get('iso')
            state.iso_pos = loaded_config.get('iso_pos')
            state.aperture = loaded_config.get('aperture')
            state.aperture_pos = loaded_config.get('aperture_pos')
            state.rf_mode = loaded_config.get('rf_mode')
    except Exception as e:
        print("Could not load config")
        print(e)

def save_config(state):
    try:
        config_data = {
            "iso": state.iso,
            "iso_pos": state.iso_pos,
            "aperture": state.aperture,
            "aperture_pos": state.aperture_pos,
            "rf_mode": state.rf_mode
        }
        with open("config.json", "w") as f:
            json.dump(config_data, f)
    except Exception as e:
        print("Could not write config")
        print(e)


# Calculate the radius of the circle with a formula that will make it converge as two numbers (object distance and lens focus distance) get closer together
def calculate_radius(object_distance, lens_focus_distance, max_radius, min_radius):
    # Calculate the absolute difference between the object distance and the lens focus distance
    difference = abs(object_distance - lens_focus_distance)

    # Calculate the radius as a linear interpolation between min_radius and max_radius
    # based on the difference. If difference is 0, radius is min_radius. If difference is max_radius, radius is max_radius.
    radius = ((max_radius - min_radius) * difference) / max_radius + min_radius

    # Ensure the radius doesn't exceed max_radius
    radius = min(radius, max_radius)

    # Ensure the radius doesn't fall below min_radius
    radius = max(radius, min_radius)

    return radius

# Generic function to return distance in mm, cm, and m
def format_distance(distance):
    if distance:
        cm = round(distance)
        if cm <= 0:
            return "Err."
        if cm < 1:
            return "<1 cm"
        elif cm < 100:
            return f"{cm} cm"
        elif cm > 799:
            return ">8 m"
        else:
            m = cm / 100
            return f"{m} m"
    else:
        return None

# Moves reticle relative to distance to object
# This is needed as the LiDAR isn't true LiDAR, but a very bright IR LED focused by a lens, which means the reticle will move as the distance gets further away, so we need to compensate for that
def interpolate_reticle(start, end, start_x, end_x, start_y, end_y):
    def get_position(val):
        x = start_x + (end_x - start_x) * ((val - start) / (end - start))
        y = start_y + (end_y - start_y) * ((val - start) / (end - start))
        return round(x), round(y)

    return get_position
# =============================================================================

# Classes
class State:
    def __init__(self):
        self.button_duration = 0

        self.iso = 400  # Initial ISO value
        self.iso_pos = 2  # Initial ISO value position in list
        self.aperture = 2.8 # Initial aperture value
        self.aperture_pos = 2  # Initial aperture value in list
        self.current_lens = None
        self.current_distance = None
        self.current_lens_cm = 0
        self.current_distance_cm = 0
        self.prev_mag = 1  # Magnification placeholder
        self.prev_rad = 1  # Radius placeholder
        self.lomog_offset = 19  # Offset in mm for Lomograflok
        self.rf_mode = "normal"  # RF Mode placeholder (normal/lomograflok)

class Interface:
    def __init__(self, splash):

        # Frame and reticle
        self.rect = Rect(FRAME_OFFSET_X, FRAME_OFFSET_Y, FRAME_LENGTH, FRAME_HEIGHT, fill=None, outline=0XFFFFFF)
        self.circle = Circle(CIRCLE_X, CIRCLE_Y, 2, fill=0x000000, outline=0xFFFFFF)
        self.circle_inner = Circle(CIRCLE_X, CIRCLE_Y, 2, fill=0xFFFFFF)
        splash.append(self.rect)
        splash.append(self.circle)
        splash.append(self.circle_inner)

        # Top bar for text
        rect_top = Rect(0, 0, 128, 25, fill=0xFFFFFF)
        line_sep = Rect(0, 12, 128, 1, fill=0x000000)
        splash.append(rect_top)
        splash.append(line_sep)

        # Data text labels
        self.lm_text_iso = label.Label(
            terminalio.FONT, color=0x000000, x=5, y=6, padding_left=2, padding_right=2, text=f"ISO{state.iso}"
        )
        self.lm_text_apt = label.Label(
            terminalio.FONT, color=0x000000, x=60, y=6, padding_left=2, padding_right=2, text=f"f{state.aperture}"
        )
        self.shutter_text = label.Label(
            terminalio.FONT, color=0x000000, x=95, y=6, padding_left=2, padding_right=2
        )
        self.distance_text = label.Label(
            terminalio.FONT, color=0x000000, x=6, y=19, padding_left=2, padding_right=2
        )
        self.ext_text = label.Label(
            terminalio.FONT, color=0x000000, x=62, y=19, padding_left=2, padding_right=2
        )
        self.bat_text = label.Label(
            terminalio.FONT, color=0x000000, background_color=0XFFFFFF, x=5, y=122, padding_left=2, padding_right=2
        )

        splash.append(self.lm_text_iso)
        splash.append(self.lm_text_apt)
        splash.append(self.shutter_text)
        splash.append(self.distance_text)
        splash.append(self.ext_text)
        splash.append(self.bat_text)


    # Async function to update the interface depending on state
    async def update(self, state, splash):
        while True:
            if state.current_lens and state.current_distance:
                mag = (state.current_lens_cm + LENS_OFFSET) / LENS_DIVISOR

                new_frame_l = round(FRAME_LENGTH * mag)
                new_frame_h = round(FRAME_HEIGHT * mag)

                if new_frame_l > FRAME_LENGTH:
                    new_frame_l = FRAME_LENGTH
                if new_frame_h > FRAME_HEIGHT:
                    new_frame_h = FRAME_HEIGHT

                # Focus reticle / indicator
                radius = round(calculate_radius(state.current_distance_cm, state.current_lens_cm, ((new_frame_h/2) - 4), 1))
                if radius != state.prev_rad:
                    state.prev_rad = radius

                    if radius <= 1 or state.current_lens == "Inf.":
                        radius = 1

                    move_pixel = interpolate_reticle(CLOSE_FOCUS_CM, INF_FOCUS_CM, CIRCLE_X, CIRCLE_X_MAX, CIRCLE_Y, CIRCLE_Y_MAX)
                    new_circle_x, new_circle_y = move_pixel(state.current_distance_cm)


                    splash.remove(self.circle)
                    splash.remove(self.circle_inner)
                    self.circle_inner = Circle(new_circle_x, new_circle_y, 2, fill=0xFFFFFF)
                    self.circle = Circle(
                        new_circle_x,
                        new_circle_y,
                        round(radius),
                        fill=None,
                        outline=0xFFFFFF,
                    )
                    splash.append(self.circle_inner)
                    splash.append(self.circle)


                # Parallax correction frame
                size =  new_frame_l * new_frame_h

                if state.prev_mag != size:
                    state.prev_mag = size
                    splash.remove(self.rect)
                    self.rect = Rect(
                        int((DISPLAY_HEIGHT - new_frame_l) / 2),
                        int(DISPLAY_HEIGHT - new_frame_h),
                        new_frame_l,
                        new_frame_h,
                        fill=None,
                        outline=0xFFFFFF,
                    )
                    splash.append(self.rect)

            await asyncio.sleep(0)
# =============================================================================

# Non-async functions
# =============================================================================
# Cycle through APERTURES
def cycle_aperture(state, interface, direction):
    if direction == "down":
        state.aperture_pos = (state.aperture_pos - 1) % len(APERTURES)
    else:
        state.aperture_pos = (state.aperture_pos + 1) % len(APERTURES)

    state.aperture = APERTURES[state.aperture_pos]
    interface.lm_text_apt.text = f"f{state.aperture}"

# Cycle through ISOS
def cycle_iso(state, interface):
    state.iso_pos = (state.iso_pos + 1) % len(ISOS)
    state.iso = ISOS[state.iso_pos]
    interface.lm_text_iso.text = f"ISO{state.iso}"
# =============================================================================

# async functions
# =============================================================================
# Monitor buttons and act accordingly
# Currently only handles one button on D10, but can be expanded to handle a second on D9
async def monitor_buttons(state, interface):
    with keypad.Keys((board.D10, board.D9), value_when_pressed=False, pull=True) as keys:
        while True:
            key_event = keys.events.get()
            if key_event:
                key_nr = key_event.key_number
                if key_event.pressed:
                    state.button_duration = time.time()
                else:
                    state.button_duration = time.time() - state.button_duration
                    if key_nr == 0:
                        if state.button_duration >= 10:
                            state.rf_mode = "lomograflok" if state.rf_mode == "normal" else "normal"
                        elif state.button_duration >= 5:
                            cycle_iso(state, interface)
                        else:
                            cycle_aperture(state, interface, "up")
                    save_config(state)
            await asyncio.sleep(0)

# Calculate shutter speed based on lux reading
async def get_shutter_speed(state, interface):
    while True:
        lux = lsen.lux

        if lux <= 0:
            print_speed = "Dark!"
        else:
            speed = round(((state.aperture * state.aperture) * K) / (lux * state.iso), 3)

            speed_ranges = [
                (0.001, 0.002, "1/1000"),
                (0.002, 0.004, "1/500"),
                (0.004, 0.008, "1/250"),
                (0.008, 0.016, "1/125"),
                (0.016, 0.033, "1/60"),
                (0.033, 0.066, "1/30"),
                (0.066, 0.125, "1/15"),
                (0.125, 0.250, "1/8"),
                (0.250, 0.500, "1/4"),
                (0.500, 1, "1/2")
            ]

            print_speed = f"{round(speed, 1)}s"

            for lower, upper, print_speed_range in speed_ranges:
                if lower <= speed < upper:
                    print_speed = print_speed_range

        interface.shutter_text.text = f"{print_speed}"

        await asyncio.sleep(0.5)

# Get distance from LiDAR
async def get_distance(state, interface):
    while True:
        state.current_distance_cm = None
        state.current_distance = None
        try:
            state.current_distance_cm = tfluna.distance
            if state.current_distance_cm :
                state.current_distance = format_distance(state.current_distance_cm)
                interface.distance_text.text = f"D:{state.current_distance}"
        except Exception as e:
            print(e)
            pass

        # Uncomment to debug or calibrate LiDAR
        # print(f"Distance: {state.current_distance_cm}")

        await asyncio.sleep(0.5)

# Get distance from lens sensor
async def get_lens(state, interface):
    while True:
        measures = []

        # Take 100 readings and average them
        for _ in range(100):
            if lr.proximity:
                measures.append(lr.proximity)

        sensor_reading = math.floor(numpy.mean(measures))

        # Uncomment to debug or calibrate lens sensor - raw reading + offset
        #print(f"Lens sensor:{sensor_reading}")

        # Clamp lens sensor reading to min and max
        if sensor_reading  <= CLOSE_FOCUS:
            sensor_reading  = CLOSE_FOCUS
        elif sensor_reading  >= INF_FOCUS:
            sensor_reading  = INF_FOCUS

        # Calculate distance from lens sensor reading by interpolating between close focus and infinity focus
        # To calibrate this, for both infinity and close focus:
        # USE A TRIPID AND A FOCUS TARGET like https://www.squit.co.uk/photo/focuschart.html
        # 1. Using ground glass, focus to target at its closest and infinity, lens wide open, and take note of the LiDAR reading where the target is in focus - see line 388
        # 2. Take note of the lens sensor reading the helicoids minimum extension (infinity) and maximum extension (close focus)
        # 3. Set CLOSE_FOCUS and INF_FOCUS to those values
        # 4. Set CLOSE_FOCUS_CM and INF_FOCUS_CM to the distance in cm measured from LiDAR
        # 7. Test your new values by checking focus at infinity and close focus, as well as a few points in between
        # 8. Repeat until you get it right - tedious, but worth it once you dial it in!
        proportion = (sensor_reading - INF_FOCUS) / (CLOSE_FOCUS - INF_FOCUS)
        dist = round(INF_FOCUS_CM + proportion * (CLOSE_FOCUS_CM - INF_FOCUS_CM), 2)
        if state.rf_mode == "lomograflok":
            dist = round(INF_FOCUS_CM_LG + proportion * (CLOSE_FOCUS_CM_LG - INF_FOCUS_CM_LG), 2)

        state.current_lens_cm = dist

        # Uncomment to debug or calibrate lens sensor - distance in cm
        #print(f"Distance: {dist} vs {state.current_distance_cm}")

        # Set current lens text
        state.current_lens = "..."
        if state.current_lens_cm <= CLOSE_FOCUS_CM and state.rf_mode == "normal":
            state.current_lens =  f"{CLOSE_FOCUS_CM} cm"
        elif state.current_lens_cm >= INF_FOCUS_CM and state.rf_mode == "normal":
            state.current_lens = "Inf."
        else:
            state.current_lens = format_distance(dist)

        if state.current_lens:
            if state.rf_mode == "lomograflok":
                interface.ext_text.text = f"LG:{state.current_lens}"
            else:
                interface.ext_text.text = f"L:{state.current_lens}"

        await asyncio.sleep(0.1)

# Get battery level from Analog pin
async def get_bat(interface):
    while True:
        batt_value = ((adc_batt.value * 3.3) / 65535) * 2
        batt_per = round((batt_value * 100) - 320)

        if batt_per > 100:
            batt_per = 100
        elif batt_per <= 0:
            batt_per = 0

        interface.bat_text.text  = f"{batt_per}%"

        await asyncio.sleep(30)

# Main loop
async def main(state, splash, interface):
    tasks = [
        asyncio.create_task(monitor_buttons(state, interface)),
        asyncio.create_task(get_shutter_speed(state, interface)),
        asyncio.create_task(get_lens(state, interface)),
        asyncio.create_task(get_distance(state, interface)),
        asyncio.create_task(get_bat(interface)),
        asyncio.create_task(interface.update(state, splash))
    ]

    await asyncio.gather(*tasks)
# =============================================================================


# Let's go!
# =============================================================================
splash = displayio.Group()
display.show(splash)

state = State()
load_config(state)

interface = Interface(splash)

asyncio.run(main(state, splash, interface))
