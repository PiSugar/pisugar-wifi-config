# pisugar-wifi-config

![PR build on master](https://github.com/PiSugar/pisugar-wifi-config/workflows/PR%20build%20on%20master/badge.svg)

PiSugar BLE wifi config tool. This is a BLE GATT server to config raspberry pi wifi.

Wifi configuration is not an easy job with raspberry pi. When you bring pi to an unfamiliar place, 
having no keyboard, no display, it is not possible to reconfigure the rpi's wifi.

`pisugar-wifi-config` makes it easy to talk to rpi via BLE and setup the wifi configuration. Your rpi 
could be discovered by BLE advertisement, then configurated by pushing a simple SSID/password message.

NOTE 1: Users need to launch `PiSugar` wechat mini program to communicate with `pisugar-wifi-config`.
NOTE 2: Only WPA-PSK is supported.

## Build
Build and package

    sudo bash build.sh

## Installation
Install bluez

    sudo apt install bluez

Old bluez in the raspberry repository need to enable experimental features to support GATT. 
If you don't want to enable experimental features, compile and install a newer version of 
bluez from source.

    sudo sed -e 's|ExecStart=.*|ExecStart=/usr/lib/bluetooth/bluetoothd --experimental|g'
        -i /lib/systemd/system/bluetooth.service
    sudo systemctl daemon-reload
    sudo systemctl restart bluetooth

Download `pisugar-wifi-config_<version>.deb` from https://github.com/PiSugar/pisugar-wifi-config/releases , and install

    sudo dpkg -i pisugar-wifi-config_<version>.deb

## Security consideration
GATT server stops advertising after 5 miniutes since lunached. To adjust the advertising duration, 
edit `/lib/systemd/system/pisugar-wifi-config.server`, add `-t <seconds>`, e.g.

    # 600 seconds
    sudo sed -e 's|ExecStart=.*|ExecStart=/usr/bin/pisugar-wifi-config -t 600|g' \
        -i /lib/systemd/system/pisugar-wifi-config.service
    sudo systemctl daemon-reload
    sudo systemctl restart pisugar-wifi-config

If advertising duration less or equal than 0, GATT server would never stop advertising.

## Bug report
Report bugs here: https://github.com/PiSugar/pisugar-wifi-config/issues

## License
GPLv3
