# pisugar-wifi-config
PiSugar BLE wifi config tool.

## Requirements
Install bluez

    sudo apt install bluez

Enable dbus experimental features (Required by old bluez):

    sudo sed -e 's|ExecStart=.*|ExecStart=/usr/lib/bluetooth/bluetoothd --experimental|g'
        -i /lib/systemd/system/bluetooth.service

## Installation
Packaging the project

    python3 setup.py sdist

Install

    sudo pip3 install pisugar-wifi-config-<version>.tar.gz
    sudo systemctl daemon-reload
    sudo systemctl enable pisugar-wifi-config
    sudo systemctl start pisugar-wifi-config

## Bug report
Report bugs here: https://github.com/PiSugar/pisugar-wifi-config/issues

## License
GPLv3