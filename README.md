# How to Install on RPI Zero

Instructions are mostly here: https://github.com/pimoroni/enviroplus-python/issues/11#issuecomment-3145549978

1. Run `curl -sSL https://get.pimoroni.com/enviroplus | bash`
2. Add `dtoverlay=adau7002-simple` to the end of the file in `/boot/firmware/config.txt`
3. Add the following in `~/.asoundrc`:
    ```
    #This section makes a reference to your I2S hardware, adjust the card name
    #to what is shown in arecord -l after card x: before the name in []
    #You may have to adjust channel count also but stick with default first
    pcm.dmic_hw {
        type hw
        card adau7002
        channels 2
        format S32_LE
    }

    #This is the software volume control, it links to the hardware above and after
    #saving the .asoundrc file you can type alsamixer, press F6 to select
    #your I2S mic then F4 to set the recording volume and arrow up and down
    #to adjust the volume
    #After adjusting the volume - go for 50 percent at first, you can do
    #something like
    #arecord -D dmic_sv -c2 -r 48000 -f S32_LE -t wav -V mono -v myfile.wav
    pcm.dmic_sv {
        type softvol
        slave.pcm dmic_hw
        control {
            name "Master Capture Volume"
            card adau7002
        }
        min_dB -3.0
        max_dB 30.0
    }
    ```
4. Run `arecord -D dmic_sv -c2 -r 48000 -f S32_LE -t wav -V mono -v myfile.wav` to record a file (prerequisite to next step).
5. Run `alsamixer`
6. Press F4 on the keyboard and set the level to 5 with up arrow keyboard key.
7. Esc to exit.
8. Rsync the files from laptop across to the pi with something like `rsync -avrP requirements.txt combined-grafana.py enviroplus pi@192.168.1.219:/home/pi/env-sensor/`.
9. `cd env-sensor`.
10. `python -m venv venv`
11. `source venv/bin/activate` (and when you're done running the python app just type `deactivate` to get out of venv).

### Hardware

Note this will not perform any of the required configuration changes on your Pi, you may additionally need to:

* Enable i2c: `sudo raspi-config nonint do_i2c 0`
* Enable SPI: `sudo raspi-config nonint do_spi 0`

And if you're using a PMS5003 sensor you will need to:

Bookworm
* Enable serial: `sudo raspi-config nonint do_serial_hw 0`
* Disable serial terminal: `sudo raspi-config nonint do_serial_cons 1`
* Add `dtoverlay=pi3-miniuart-bt` to your `/boot/firmware/config.txt`

Bullseye
* Enable serial: `raspi-config nonint set_config_var enable_uart 1 /boot/config.txt`
* Disable serial terminal: `sudo raspi-config nonint do_serial 1`
* Add `dtoverlay=pi3-miniuart-bt` to your `/boot/config.txt`

### Software

1. First rsync the files across e.g. `rsync -avrP enviroplus examples/combined-grafana.py pi@192.168.1.95:/home/pi/env-sensor/`
1. `sudo apt-get install python3-dev`
1. `sudo apt-get install libportaudio2` which is a dependency for the noise feature.
2. Run `cd env-sensor`
2. Run `python -m venv venv`
3. Activate it with `source ./venv/bin/activate`
4. Run `pip install -r requirements.txt` if there is a requirements.txt file already, otherwise go to the next step.
4. Run `pip3 install numpy==2.2.4` to get the pre-built wheel version from https://www.piwheels.org/project/numpy/. If you try to get the latest version where there is no wheel, it just never seems to end the build process.
5. Run `pip3 install st7735` 
6. Run `pip3 install gpiod`
7. Run `pip3 install gpiodevice`
8. Run `pip3 install ltr559`
9. Run `pip3 install bme280`
10. Run `pip3 install pimoroni-bme280`
11. Run `pip3 install fonts`
12. Run `pip3 install font-roboto`
13. Run `sudo apt install liblcms2-2 libopenjp2-7 libwebpmux3 libwebpdemux2` which are dependencies for `pillow`.
14. Run `pip3 install pillow==11.1.0` to get the pre-built wheel version from https://www.piwheels.org/project/pillow/. If you try to get the latest version where there is no wheel, it just never seems to end the build process.
15. Run `pip3 install pms5003`
16. Run `pip3 install ads1015`
17. Run `pip3 install sounddevice`
18. Run `pip install prometheus-client`

19. `sudo reboot` once that's all installed and the hardware is all setup.

## Running Grafana Alloy

Currently there is no armv6 32 bit pre-build binary support. I tried to cross compile build a binary in many different ways, but didn't get anywhere, so now there is a requirement that it must be run on a 64-bit compatible ARM CPU computer.

### Setup

1. Follow the instructions on the grafana connections website for the linux server integration.
2. 
