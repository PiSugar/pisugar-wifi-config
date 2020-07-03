from setuptools import setup, find_packages

setup(
    name="pisugar-wifi-config",
    version="0.1",
    keywords = ("pisugar", "PiSugar", "wifi", "BLE"),
    license = "GPLv3",
    description = "PiSugar wifi BLE config tool",
    long_description = "PiSugar wifi BLE config tool",
    url = "https://www.pisugar.com/",
    author = "PiSugar Team",
    author_email = "pisugar.zero@gmail.com",
    platforms = "any",

    packages = find_packages(),
    include_package_data = True,

    scripts = ["pisugar_wifi_config.py"],
    entry_points={
        "console_scripts": [
            "pisugar-wifi-config = pisugar_wifi_config:main",
        ]
    }
)