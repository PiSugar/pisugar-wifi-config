
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
        long_description = 'PiSugar wifi BLE config tool',
        url = "https://www.pisugar.com/",
        author = "PiSugar Team",
        author_email = "pisugar.zero@gmail.com",
        platforms = ["all"],
        packages = ['pisugar_wifi_config'],

        entry_points={
            'console_scripts': [
                'pisugar-wifi-config=pisugar_wifi_config:main',
            ],
        }
    )

if __name__ == '__main__':
    main()