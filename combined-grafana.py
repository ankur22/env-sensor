#!/usr/bin/env python3

import colorsys
import sys
import time

import st7735

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

import logging
from subprocess import PIPE, Popen

from bme280 import BME280
from fonts.ttf import RobotoMedium as UserFont
from PIL import Image, ImageDraw, ImageFont
from pms5003 import PMS5003
from pms5003 import ReadTimeoutError as pmsReadTimeoutError
from pms5003 import SerialTimeoutError

from enviroplus import gas

from enviroplus.noise import Noise

from prometheus_client import start_http_server,Gauge

env_sensor_cpu_temp_gauge = Gauge('env_sensor_cpu_temp', 'The CPU temperature')
env_sensor_raw_temp_gauge = Gauge('env_sensor_raw_temp', 'The raw temperature')
env_sensor_avg_temp_gauge = Gauge('env_sensor_avg_temp', 'The average temp')
env_sensor_pressure_gauge = Gauge('env_sensor_pressure', 'The pressure in hPa')
env_sensor_humidity_gauge = Gauge('env_sensor_humidity', 'The humidity in %')
env_sensor_light_gauge = Gauge('env_sensor_light', 'The light in lux')
env_sensor_oxidised_gauge = Gauge('env_sensor_oxidised', 'Oxidised gas in kO')
env_sensor_reduced_gauge = Gauge('env_sensor_reduced', 'Reduced gas in kO')
env_sensor_nh3_gauge = Gauge('env_sensor_nh3', 'nh3 gas in kO')
env_sensor_pm1_gauge = Gauge('env_sensor_pm1', 'particle monitoring 1 in ug/m3')
env_sensor_pm25_gauge = Gauge('env_sensor_pm25', 'particle monitoring 2.5 in ug/m3')
env_sensor_pm10_gauge = Gauge('env_sensor_pm10', 'particle monitoring 10 in ug/m3')
env_sensor_noise_profile_low_gauge = Gauge('env_sensor_noise_profile_low', 'noise profile low')
env_sensor_noise_profile_mid_gauge = Gauge('env_sensor_noise_profile_mid', 'noise profile mid')
env_sensor_noise_profile_high_gauge = Gauge('env_sensor_noise_profile_high', 'noise profile high')
env_sensor_amp_freq_100_200_gauge = Gauge('env_sensor_amp_freq_100_200', 'amplitudes at frequency range 100-200')
env_sensor_amp_freq_500_600_gauge = Gauge('env_sensor_amp_freq_500_600', 'amplitudes at frequency range 500-600')
env_sensor_amp_freq_1000_1200_gauge = Gauge('env_sensor_amp_freq_1000_1200', 'amplitudes at frequency range 1000-1200')
env_sensor_pm_03_pl_gauge = Gauge('env_sensor_pm03_litre', 'particles >0.3um per 1/10 litre of air')
env_sensor_pm_05_pl_gauge = Gauge('env_sensor_pm05_litre', 'particles >0.5um per 1/10 litre of air')
env_sensor_pm_1_pl_gauge = Gauge('env_sensor_pm1_litre', 'particles >1um per 1/10 litre of air')
env_sensor_pm_25_pl_gauge = Gauge('env_sensor_pm25_litre', 'particles >2.5um per 1/10 litre of air')
env_sensor_pm_5_pl_gauge = Gauge('env_sensor_pm5_litre', 'particles >5um per 1/10 litre of air')
env_sensor_pm_10_pl_gauge = Gauge('env_sensor_pm10_litre', 'particles >10um per 1/10 litre of air')


noise = Noise()

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S")

logging.info("""combined.py - Displays readings from all of Enviro plus' sensors

Press Ctrl+C to exit!

""")

# BME280 temperature/pressure/humidity sensor
bme280 = BME280()

# PMS5003 particulate sensor
pms5003 = PMS5003()
time.sleep(1.0)

# Create ST7735 LCD display class
st7735 = st7735.ST7735(
    port=0,
    cs=1,
    dc="GPIO9",
    backlight="GPIO12",
    rotation=270,
    spi_speed_hz=10000000
)

# Initialize display
st7735.begin()

WIDTH = st7735.width
HEIGHT = st7735.height

# Set up canvas and font
img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)
font_size_small = 10
font_size_large = 20
font = ImageFont.truetype(UserFont, font_size_large)
smallfont = ImageFont.truetype(UserFont, font_size_small)
x_offset = 2
y_offset = 2

message = ""

# The position of the top bar
top_pos = 25

# Create a values dict to store the data
variables = ["temperature",
             "pressure",
             "humidity",
             "light",
             "oxidised",
             "reduced",
             "nh3",
             "pm1",
             "pm25",
             "pm10"]

units = ["C",
         "hPa",
         "%",
         "Lux",
         "kO",
         "kO",
         "kO",
         "ug/m3",
         "ug/m3",
         "ug/m3"]

# Define your own warning limits
# The limits definition follows the order of the variables array
# Example limits explanation for temperature:
# [4,18,28,35] means
# [-273.15 .. 4] -> Dangerously Low
# (4 .. 18]      -> Low
# (18 .. 28]     -> Normal
# (28 .. 35]     -> High
# (35 .. MAX]    -> Dangerously High
# DISCLAIMER: The limits provided here are just examples and come
# with NO WARRANTY. The authors of this example code claim
# NO RESPONSIBILITY if reliance on the following values or this
# code in general leads to ANY DAMAGES or DEATH.
limits = [[4, 18, 28, 35],
          [250, 650, 1013.25, 1015],
          [20, 30, 60, 70],
          [-1, -1, 30000, 100000],
          [-1, -1, 40, 50],
          [-1, -1, 450, 550],
          [-1, -1, 200, 300],
          [-1, -1, 50, 100],
          [-1, -1, 50, 100],
          [-1, -1, 50, 100]]

# RGB palette for values on the combined screen
palette = [(0, 0, 255),           # Dangerously Low
           (0, 255, 255),         # Low
           (0, 255, 0),           # Normal
           (255, 255, 0),         # High
           (255, 0, 0)]           # Dangerously High

values = {}


# Displays data and text on the 0.96" LCD
def display_text(variable, data, unit):
    # Maintain length of list
    values[variable] = values[variable][1:] + [data]
    # Scale the values for the variable between 0 and 1
    vmin = min(values[variable])
    vmax = max(values[variable])
    colours = [(v - vmin + 1) / (vmax - vmin + 1) for v in values[variable]]
    # Format the variable name and value
    message = f"{variable[:4]}: {data:.1f} {unit}"
    logging.info(message)
    draw.rectangle((0, 0, WIDTH, HEIGHT), (255, 255, 255))
    for i in range(len(colours)):
        # Convert the values to colours from red to blue
        colour = (1.0 - colours[i]) * 0.6
        r, g, b = [int(x * 255.0) for x in colorsys.hsv_to_rgb(colour, 1.0, 1.0)]
        # Draw a 1-pixel wide rectangle of colour
        draw.rectangle((i, top_pos, i + 1, HEIGHT), (r, g, b))
        # Draw a line graph in black
        line_y = HEIGHT - (top_pos + (colours[i] * (HEIGHT - top_pos))) + top_pos
        draw.rectangle((i, line_y, i + 1, line_y + 1), (0, 0, 0))
    # Write the text at the top in black
    draw.text((0, 0), message, font=font, fill=(0, 0, 0))
    st7735.display(img)


# Saves the data to be used in the graphs later and prints to the log
def save_data(idx, data):
    variable = variables[idx]
    # Maintain length of list
    values[variable] = values[variable][1:] + [data]
    unit = units[idx]
    message = f"{variable[:4]}: {data:.1f} {unit}"
    logging.info(message)


# Displays all the text on the 0.96" LCD
def display_everything():
    draw.rectangle((0, 0, WIDTH, HEIGHT), (0, 0, 0))
    column_count = 2
    row_count = (len(variables) / column_count)
    for i in range(len(variables)):
        variable = variables[i]
        data_value = values[variable][-1]
        unit = units[i]
        x = x_offset + ((WIDTH // column_count) * (i // row_count))
        y = y_offset + ((HEIGHT / row_count) * (i % row_count))
        message = f"{variable[:4]}: {data_value:.1f} {unit}"
        lim = limits[i]
        rgb = palette[0]
        for j in range(len(lim)):
            if data_value > lim[j]:
                rgb = palette[j + 1]
        draw.text((x, y), message, font=smallfont, fill=rgb)
    st7735.display(img)


# Get the temperature of the CPU for compensation
def get_cpu_temperature():
    process = Popen(["vcgencmd", "measure_temp"], stdout=PIPE, universal_newlines=True)
    output, _error = process.communicate()
    return float(output[output.index("=") + 1:output.rindex("'")])


def main():
    pms5003.reset()

    # Tuning factor for compensation. Decrease this number to adjust the
    # temperature down, and increase to adjust up
    factor = 2.25

    cpu_temps = [get_cpu_temperature()] * 5

    delay = 0.5  # Debounce the proximity tap
    mode = 12    # The starting mode
    last_page = 0

    for v in variables:
        values[v] = [1] * WIDTH

    # The main loop
    while True:
        proximity = ltr559.get_proximity()

        # If the proximity crosses the threshold, toggle the mode
        if proximity > 1500 and time.time() - last_page > delay:
            mode += 1
            mode %= (len(variables) + 1)
            last_page = time.time()

        # One mode for each variable
        if mode == 0:
            # variable = "temperature"
            unit = "°C"
            cpu_temp = get_cpu_temperature()
            # Smooth out with some averaging to decrease jitter
            cpu_temps = cpu_temps[1:] + [cpu_temp]
            avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
            raw_temp = bme280.get_temperature()
            data = raw_temp - ((avg_cpu_temp - raw_temp) / factor)
            display_text(variables[mode], data, unit)

        if mode == 1:
            # variable = "pressure"
            unit = "hPa"
            data = bme280.get_pressure()
            display_text(variables[mode], data, unit)

        if mode == 2:
            # variable = "humidity"
            unit = "%"
            data = bme280.get_humidity()
            display_text(variables[mode], data, unit)

        if mode == 3:
            # variable = "light"
            unit = "Lux"
            if proximity < 10:
                data = ltr559.get_lux()
            else:
                data = 1
            display_text(variables[mode], data, unit)

        if mode == 4:
            # variable = "oxidised"
            unit = "kO"
            data = gas.read_all()
            data = data.oxidising / 1000
            display_text(variables[mode], data, unit)

        if mode == 5:
            # variable = "reduced"
            unit = "kO"
            data = gas.read_all()
            data = data.reducing / 1000
            display_text(variables[mode], data, unit)

        if mode == 6:
            # variable = "nh3"
            unit = "kO"
            data = gas.read_all()
            data = data.nh3 / 1000
            display_text(variables[mode], data, unit)

        if mode == 7:
            # variable = "pm1"
            unit = "ug/m3"
            try:
                data = pms5003.read()
            except (SerialTimeoutError, pmsReadTimeoutError):
                logging.warning("Failed to read PMS5003")
            else:
                data = float(data.pm_ug_per_m3(1.0))
                display_text(variables[mode], data, unit)

        if mode == 8:
            # variable = "pm25"
            unit = "ug/m3"
            try:
                data = pms5003.read()
            except (SerialTimeoutError, pmsReadTimeoutError):
                logging.warning("Failed to read PMS5003")
            else:
                data = float(data.pm_ug_per_m3(2.5))
                display_text(variables[mode], data, unit)

        if mode == 9:
            # variable = "pm10"
            unit = "ug/m3"
            try:
                data = pms5003.read()
            except (SerialTimeoutError, pmsReadTimeoutError):
                logging.warning("Failed to read PMS5003")
            else:
                data = float(data.pm_ug_per_m3(10))
                display_text(variables[mode], data, unit)

        if mode == 10:
            low, mid, high, amp = noise.get_noise_profile()
            low *= 128
            mid *= 128
            high *= 128
            amp *= 64

            img2 = img.copy()
            draw.rectangle((0, 0, st7735.width, st7735.height), (0, 0, 0))
            img.paste(img2, (1, 0))
            draw.line((0, 0, 0, amp), fill=(int(low), int(mid), int(high)))

            st7735.display(img2)

        if mode == 11:
            amps = noise.get_amplitudes_at_frequency_ranges([
                (100, 200),
                (500, 600),
                (1000, 1200)
            ])
            amps = [n * 32 for n in amps]
            img2 = img.copy()
            draw.rectangle((0, 0, st7735.width, st7735.height), (0, 0, 0))
            img.paste(img2, (1, 0))
            draw.line((0, 0, 0, amps[0]), fill=(0, 0, 255))
            draw.line((0, 0, 0, amps[1]), fill=(0, 255, 0))
            draw.line((0, 0, 0, amps[2]), fill=(255, 0, 0))

            st7735.display(img2)

        if mode == 12:
            # Everything on one screen
            cpu_temp = get_cpu_temperature()
            # Smooth out with some averaging to decrease jitter
            cpu_temps = cpu_temps[1:] + [cpu_temp]
            avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
            env_sensor_cpu_temp_gauge.set(avg_cpu_temp)
            raw_temp = bme280.get_temperature()
            env_sensor_raw_temp_gauge.set(raw_temp)
            raw_data = raw_temp - ((avg_cpu_temp - raw_temp) / factor)
            env_sensor_avg_temp_gauge.set(raw_data)
            save_data(0, raw_data)
            display_everything()
            raw_data = bme280.get_pressure()
            env_sensor_pressure_gauge.set(raw_data)
            save_data(1, raw_data)
            display_everything()
            raw_data = bme280.get_humidity()
            env_sensor_humidity_gauge.set(raw_data)
            save_data(2, raw_data)
            if proximity < 10:
                raw_data = ltr559.get_lux()
            else:
                raw_data = 1
            env_sensor_light_gauge.set(raw_data)
            save_data(3, raw_data)
            display_everything()
            gas_data = gas.read_all()
            raw_data = gas_data.oxidising / 1000
            save_data(4, raw_data)
            env_sensor_oxidised_gauge.set(raw_data)
            raw_data = gas_data.reducing / 1000
            save_data(5, raw_data)
            env_sensor_reduced_gauge.set(raw_data)
            raw_data = gas_data.nh3 / 1000
            save_data(6, raw_data)
            env_sensor_nh3_gauge.set(raw_data)
            display_everything()
            pms_data = None
            try:
                pms_data = pms5003.read()
            except (SerialTimeoutError, pmsReadTimeoutError):
                logging.warning("Failed to read PMS5003")
            else:
                raw_data = pms_data.pm_ug_per_m3(1.0)
                save_data(7, float(raw_data))
                env_sensor_pm1_gauge.set(raw_data)
                raw_data = pms_data.pm_ug_per_m3(2.5)
                save_data(8, float(raw_data))
                env_sensor_pm25_gauge.set(raw_data)
                raw_data = pms_data.pm_ug_per_m3(10)
                save_data(9, float(raw_data))
                env_sensor_pm10_gauge.set(raw_data)
                display_everything()
                env_sensor_pm_03_pl_gauge.set(pms_data.pm_per_1l_air(0.3))
                env_sensor_pm_05_pl_gauge.set(pms_data.pm_per_1l_air(0.5))
                env_sensor_pm_1_pl_gauge.set(pms_data.pm_per_1l_air(1))
                env_sensor_pm_25_pl_gauge.set(pms_data.pm_per_1l_air(2.5))
                env_sensor_pm_5_pl_gauge.set(pms_data.pm_per_1l_air(5))
                env_sensor_pm_10_pl_gauge.set(pms_data.pm_per_1l_air(10))
            # get noise profile
            low, mid, high, amp = noise.get_noise_profile()
            low *= 128
            mid *= 128
            high *= 128
            amp *= 64
            env_sensor_noise_profile_low_gauge.set(int(low))
            env_sensor_noise_profile_mid_gauge.set(int(mid))
            env_sensor_noise_profile_high_gauge.set(int(high))
            # get amplitudes at frequency ranges
            amps = noise.get_amplitudes_at_frequency_ranges([
                (100, 200),
                (500, 600),
                (1000, 1200)
            ])
            amps = [n * 32 for n in amps]
            env_sensor_amp_freq_100_200_gauge.set(amps[0])
            env_sensor_amp_freq_500_600_gauge.set(amps[1])
            env_sensor_amp_freq_1000_1200_gauge.set(amps[2])
        
        time.sleep(30) # Sleep for 30 seconds before getting more data


if __name__ == "__main__":
    try:
        start_http_server(8000)
        main()
    except KeyboardInterrupt:
        print("shutting down")
        sys.exit(0)
