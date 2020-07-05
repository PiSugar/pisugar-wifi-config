
import sys
from setuptools import setup

VERSION="0.1"

def main():
    setup(
        name="pisugar-wifi-config",
        version=VERSION,
        license = "GPLv3",
        keywords = ["pisugar", "PiSugar", "wifi", "BLE"],
        description = "PiSugar wifi BLE config tool",
        long_description = ''.join([l for l in _get_long_description()]),
        url = "https://www.pisugar.com/",
        author = "PiSugar Team",
        author_email = "pisugar.zero@gmail.com",
        platforms = ["all"],
        packages = ['pisugar_wifi_config'],

        package_data = {"":["*.service"]},
        data_files = [("/lib/systemd/system", ["pisugar-wifi-config.service"])],
        entry_points={
            'console_scripts': [
                'pisugar-wifi-config=pisugar_wifi_config:main',
            ],
        }
    )

def _get_long_description(fname='README.md'):
    for line in open(fname, 'r'):
        yield line

if __name__ == '__main__':
    main()