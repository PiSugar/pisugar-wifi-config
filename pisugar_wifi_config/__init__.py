#!/usr/bin/python3

import argparse
import sys
import subprocess
import threading
import time
import re
import logging
import tempfile
import signal

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
 
BLUEZ_SERVICE_NAME =           'org.bluez'
DBUS_OM_IFACE =                'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =              'org.freedesktop.DBus.Properties'

LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE =       'org.bluez.LEAdvertisement1'

GATT_MANAGER_IFACE =           'org.bluez.GattManager1'
GATT_SERVICE_IFACE =           'org.bluez.GattService1'
GATT_CHRC_IFACE =              'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =              'org.bluez.GattDescriptor1'

LOCAL_NAME =                   'rpi-gatt-server'

SERVICE_ID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0000'
SERVICE_NAME= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0001'
DEVICE_MODEL= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0002'
WIFI_NAME= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0003'
IP_ADDRESS= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0004'
INPUT= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0005'
NOTIFY_MESSAGE= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0006'
INPUT_SEP= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0007'
CUSTOM_COMMAND_INPUT= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0008'
CUSTOM_COMMAND_NOTIFY= 'fd2b4448-aa0f-4a15-a62f-eb0be77a0009'
CUSTOM_INFO_LABEL= 'FD2BCCCA'
CUSTOM_INFO_COUNT= 'FD2BCCAA0000'
CUSTOM_INFO= 'FD2BCCCB'
CUSTOM_COMMAND_LABEL= 'FD2BCCCC'
CUSTOM_COMMAND_COUNT= 'FD2BCCAC0000'

SSH_CHRC='fd2b4448-aa0f-4a15-a62f-eb0be77a0020'

WPA_CONFIG = '/etc/wpa_supplicant/wpa_supplicant.conf'

SEP = '%&%'
END = '&#&'

mainloop = None

class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'


class Advertisement(dbus.service.Object):
    PATH_BASE = '/com/pisugar/wifi/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = None
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids,
                                                    signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.include_tx_power is not None:
            properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)

        if self.data is not None:
            properties['Data'] = dbus.Dictionary(
                self.data, signature='yv')
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature='yv')
        self.data[ad_type] = dbus.Array(data, signature='y')

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        print('GetAll')
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        print('returning props')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('%s: Released!' % self.path)


def register_ad_cb():
    print('Advertisement registered')


def register_ad_error_cb(error):
    print('Failed to register advertisement: ' + str(error))
    mainloop.quit()


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """
    PATH_BASE = '/com/pisugar/wifi/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_SERVICE_IFACE: {
                        'UUID': self.uuid,
                        'Primary': self.primary,
                        'Characteristics': dbus.Array(
                                self.get_characteristic_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_CHRC_IFACE: {
                        'Service': self.service.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                        'Descriptors': dbus.Array(
                                self.get_descriptor_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print('Default StartNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print('Default StopNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_DESC_IFACE: {
                        'Characteristic': self.chrc.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print ('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()


class ServiceNameChrc(Characteristic):
    """
    Service Name Characteristic.
    """
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0001'
    NAME = 'PiSugar BLE Wifi Config'

    def __init__(self, bus, index, service):
        super().__init__(bus, index, self.UUID, ['read'], service)
        self.add_descriptor(ServiceNameDescriptor(bus, 0, self))
    
    def ReadValue(self, options):
        return dbus.ByteArray(self.NAME.encode())


class ServiceNameDescriptor(Descriptor):
    """
    Service Name Descriptor.
    """
    UUID = '2001'
    VALUE = 'PiSugar BLE Wifi Config'

    def __init__(self, bus, index, chrc):
        super().__init__(bus, index, self.UUID, ['read'], chrc)
    
    def ReadValue(self, options):
        return dbus.ByteArray(self.VALUE.encode())


class DeviceModelChrc(Characteristic):
    """
    Device Model Charateristic.
    """
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0002'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.UUID, ['read'], service)

        self.model = ''
        try:
            f = open('/proc/device-tree/model')
            self.model = f.read()
        except FileNotFoundError as e:
            print('Failed to open model raspberry pi model file')

        self.add_descriptor(DeviceModelDescriptor(bus, 0, self))

    def ReadValue(self, options):
        print('Read device model')
        return dbus.ByteArray(self.model.encode())


class DeviceModelDescriptor(Descriptor):
    """
    Device Model Descriptor.
    """
    UUID = '2002'
    VALUE = 'Raspberry Hardware Model'

    def __init__(self, bus, index, chrc):
        Descriptor.__init__(self, bus, index, self.UUID, ['read'], chrc)

    def ReadValue(self, options):
        return dbus.ByteArray(self.VALUE.encode())


class ReadWifiNameThread(threading.Thread):
    def __init__(self, chrc):
        super().__init__()
        self.daemon = True
        self.chrc = chrc
        self.wifi_name = ''

    def run(self):
        while self.chrc.notifying:
            try:
                output = subprocess.check_output(['iwconfig', 'wlan0']).decode()
                lines = output.split('\n')
                for line in lines:
                    matches = re.match(r'.*ESSID:"(.*)"', line, re.M|re.I)
                    if matches:
                        self.wifi_name = matches.group(1)
                        self.chrc.PropertiesChanged(GATT_CHRC_IFACE, {'Value': dbus.ByteArray(self.wifi_name.encode())}, [])
                        break
                time.sleep(3)
            except Exception as e:
                print(str(e))
                time.sleep(5)


class WifiNameChrc(Characteristic):
    """
    Wifi Name Characteristic.
    """
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0003'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.UUID, ['notify'], service)
        self.read_wifi_name_thread = ReadWifiNameThread(self)
        self.notifying = False

    def StartNotify(self):
        if self.notifying:
            print("Already notifying, nothing to do")
        else:
            self.notifying = True
            self.read_wifi_name_thread.start()

    def StopNotify(self):
        self.notifying = False


class ReadIPAddrThread(threading.Thread):
    def __init__(self, chrc):
        super().__init__()
        self.daemon = True
        self.chrc = chrc
        self.ip_addr = ''

    def run(self):
        while self.chrc.notifying:
            try:
                output = subprocess.check_output(['ifconfig', 'wlan0']).decode()
                lines = output.split('\n')
                for line in lines:
                    matches = re.match(r'.*inet6?\s(\S*)\s.*', line, re.M|re.I)
                    if matches:
                        self.ip_addr = matches.group(1)
                        self.chrc.PropertiesChanged(GATT_CHRC_IFACE, {'Value': dbus.ByteArray(self.ip_addr.encode())}, [])
                        break
                time.sleep(3)
            except Exception as e:
                print(str(e))
                time.sleep(5)


class IPAddressChrc(Characteristic):
    """
    IP Address Characteristic.
    """
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0004'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.UUID, ['notify'], service)
        self.read_ip_addr_thread = ReadIPAddrThread(self)
        self.notifying = False

    def StartNotify(self):
        if self.notifying:
            print("Already notifying, nothing to do")
        else:
            self.notifying = True
            self.read_ip_addr_thread.start()

    def StopNotify(self):
        self.notifying = False


def set_wifi(ssid, password):
    template="""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=wheel
network={
    ssid="{}"
    scan_ssid=1
    key_mgmt=WPA-PSK
    psk="{}"
}
    """
    try:
        # # Old config
        # f = open(WPA_CONFIG, 'r')
        # c = f.read()
        # f.close()
        # # Search existing ssid
        # remain = c
        # network_re = r'[\s]*network[\s\n]*=[\s\n]*\{[^\}]*\}[\s]*'
        # ssid_re = r'[\s\n]*ssid[\s\n]*=[\s\n]*["\']?' + ssid + r'["\']?[\s\n]+'
        # while True:
        #     m = re.search(network_re, remain)
        #     if m:
        #         (start, end) = m.span()
        #         n = remain[start:end]
        #         remain = remain[end:]
        #         if re.search(ssid_re, n):
        #             c = c.replace(n, '')    # Remove same ssid network
        #             break
        #     else:
        #         break
        # # Append new network
        # n = subprocess.check_output(['wpa_passphrase', ssid, password]).decode()
        # if not c.endswith('\n'):
        #     c += '\n'
        # c += n
        # # Flush
        # f = open(WPA_CONFIG, 'w')
        # f.write(c)
        # f.flush()
        # f.close()
        # Restart service, has to be these way
        c = template.format(ssid, password)
        f = tempfile.NamedTemporaryFile('w')
        f.write(c)
        f.flush()
        subprocess.run(['killall', 'wpa_supplicant'])
        subprocess.run(['wpa_supplicant', '-B', '-i', 'wlan0', '-c', f.name])
    except Exception as e:
        print(str(e))

def parse_and_set_wifi(msg):
    configs = msg.split(SEP)
    if len(configs) != 3:
        print('Error config')
    else:
        key = configs[0]
        ssid = configs[1]
        password = configs[2]
        set_wifi(ssid, password)


class InputChrc(Characteristic):
    """
    Set wifi SSID and password.
    """
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0005'

    def __init__(self, bus, index, service):
        super().__init__(bus, index, self.UUID, ['write', 'write-without-response'], service)

    def WriteValue(self, value, options):
        msg = bytes([x for x in value])
        try:
            msg = msg.decode('utf-8')
            parse_and_set_wifi(msg)
        except Exception as e:
            print('Decode error')


class InputNotifyMessageChrc(Characteristic):
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0006'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.UUID, ['notify'], service)

    def StartNotify(self):
        # TODO start notify
        pass

    def StopNotify(self):
        # TODO stop notify
        pass


class InputSepChrc(Characteristic):
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0007'

    def __init__(self, bus, index, service):
        super().__init__(bus, index, self.UUID, ['write', 'write-without-response'], service)
        self.last_update_at = time.time()
        self.full_msg = b''

    def WriteValue(self, value, options):
        msg = bytes([x for x in value])

        # Clear old content, 1s
        timestamp = time.time()
        if timestamp - self.last_update_at > 1:
            self.full_msg = b''
        self.last_update_at = timestamp
        self.full_msg += msg

        try:
            full_msg = self.full_msg.decode('utf8')
            if full_msg.endswith(END):
                print('InputSepChrc: ' + full_msg)
                full_msg = full_msg.split(END)[0]
                parse_and_set_wifi(full_msg)
        except Exception as e:
            print(str(e))

class CommandThread(threading.Thread):
    def __init__(self, chrc, cmd):
        super().__init__()
        self.daemon = True
        self.chrc = chrc
        self.cmd = cmd
    
    def run(self):
        try:
            output = subprocess.run(['bash', '-c', self.msg])
            self.chrc.PropertiesChanged(GATT_CHRC_IFACE, {'Value': dbus.ByteArray(output.encode())}, [])
        except Exception as e:
            print(str(e))

class CommandChrc(Characteristic):
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0020'

    def __init__(self, bus, index, service):
        super().__init__(bus, index, self.UUID, ['write', 'write-without-response', 'notify'], service)

    def WriteValue(self, value, options):
        msg = bytes([x for x in value])
        try:
            cmd_thread = CommandThread(self, msg.decode('utf8'))
            cmd_thread.start()
        except Exception as ex:
            print(str(ex))


class PiSugarWifiConfigService(Service):
    """
    PiSugar Wifi Config Service.
    """
    UUID = 'fd2b4448-aa0f-4a15-a62f-eb0be77a0000'

    def __init__(self, bus, index):
        super().__init__(bus, index, self.UUID, True)

        self.add_characteristic(ServiceNameChrc(bus, 0, self))
        self.add_characteristic(DeviceModelChrc(bus, 1, self))
        self.add_characteristic(WifiNameChrc(bus, 2, self))
        self.add_characteristic(IPAddressChrc(bus, 3, self))
        self.add_characteristic(InputChrc(bus, 4, self))
        self.add_characteristic(InputSepChrc(bus, 5, self))
        self.add_characteristic(InputNotifyMessageChrc(bus, 6, self))
        self.add_characteristic(CommandChrc(bus, 7, self))


class PiSugarWifiConfigApplication(Application):
    def __init__(self, bus):
        super().__init__(bus)
        self.add_service(PiSugarWifiConfigService(bus, 0))


class PiSugarWifiConfigAdvertisement(Advertisement):
    def __init__(self, bus, index):
        super().__init__(bus, index, 'peripheral')
        self.add_service_uuid(PiSugarWifiConfigService.UUID)
        self.add_local_name('pisugar')
        self.include_tx_power = True


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props and GATT_MANAGER_IFACE in props:
            print('Adapter: ' + str(o))
            return o
        print('Skip adapter:', o)
    return None


def register_app_cb():
    print('GATT application registered')


def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()


def register_ad_cb():
    print('Advertisement registered')


def register_ad_error_cb(error):
    print('Failed to register advertisement: ' + str(error))
    mainloop.quit()


def handle_signal(signum, frame):
    global mainloop
    print("Signal: " + str(signum))
    mainloop.quit()


def stop_advertisement_after(ad_manager, adv, seconds):
    if seconds > 0:
        time.sleep(seconds)
    print('Stop advertising...')
    ad_manager.UnregisterAdvertisement(adv)
    dbus.service.Object.remove_from_connection(adv)


def main():
    global mainloop

    parser = argparse.ArgumentParser(description='PiSugar BLE wifi config')
    parser.add_argument('-t', '--time', dest='time', type=int, nargs='?', default=300,
                        help='Bluetooth advertising duration time in seconds (<=0: never stop)')
    args = parser.parse_args()
    seconds = args.time

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # find BLE adapter and power on
    adapter = find_adapter(bus)
    if not adapter:
        print('BLE adapter not found')
        return
    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                   "org.freedesktop.DBus.Properties")
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    # glib mainloop
    mainloop = GLib.MainLoop()
 
    # service/advertising manager
    service_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                     GATT_MANAGER_IFACE)
    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)
 
    app = PiSugarWifiConfigApplication(bus)
    adv = PiSugarWifiConfigAdvertisement(bus, 0)

    # register
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)
    ad_manager.RegisterAdvertisement(adv.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    # stop adevertising after n seconds
    start_at = time.time()
    if seconds and seconds >= 0:
        t = threading.Thread(target=stop_advertisement_after, args=(ad_manager, adv, seconds), daemon=True)
        t.start()

    # handle SIGINT
    signal.signal(signal.SIGINT, handle_signal)

    # run mainloop
    try:
        mainloop.run()
    except Exception as e:
        print(str(e))

    # stop advertising
    now = time.time()
    if (seconds <= 0) or (now - start_at < seconds):
        stop_advertisement_after(ad_manager, adv, 0)


if __name__ == '__main__':
    main()