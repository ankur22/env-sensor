# How to Install on RPI Zero

## Install Dependencies

1. First rsync the files across e.g. `rsync -avrP enviroplus examples/combined-grafana.py pi@192.168.1.95:/home/pi/env-sensor/`
2. Run `python -m venv venv`
3. Activate it with `source ./venv/bin/activate`
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

## Exit

When you've finished running the application, remember to run `deactivate` to move out of `venv`.

## Running Grafana Alloy

Currently there is no armv6 32 bit pre-build binary support. So let's build it:

### Install Go

1. `mkdir ~/src && cd ~/src`
2. `wget https://dl.google.com/go/go1.24.4.linux-armv6l.tar.gz`
3. `sudo tar -C /usr/local -xzf go1.24.4.linux-armv6l.tar.gz`
4. `rm go1.24.4.linux-armv6l.tar.gz`
5. `vi ~/.profile`
6. Append:
    ```
    export PATH=$PATH:/usr/local/go/bin
    export GOPATH=$HOME/go
    ```
7. `source ~/.profile`
8. `go version` to validate.

### Clone and Build Grafana Alloy

1. `git clone https://github.com/grafana/alloy.git`
2. `go mod vendor`
3. `make alloy`
