# pisugar-wifi-config
PiSugar BLE wifi config tool

## Installation

Install bluez

    sudo apt install bluez

Enable dbus experimental features:

    sudo sed -e 's|ExecStart=.*|ExecStart=/usr/lib/bluetooth/bluetoothd --experimental|g'
        -i /lib/systemd/system/bluetooth.service

