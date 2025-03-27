#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="inkcraft-rip",
    version="0.1.0",
    description="Open-source RIP software for Epson DTG printers",
    author="InkCraft RIP Project",
    author_email="info@inkcraft-rip.org",
    url="https://github.com/inkcraft-rip/inkcraft-rip",
    packages=find_packages(),
    install_requires=[
        "pyusb>=1.2.1",
        "pillow>=9.0.0",
        "numpy>=1.20.0",
        "matplotlib>=3.5.0",
        "pyyaml>=6.0.0",
    ],
    extras_require={
        "analysis": ["pyshark>=0.5.3"],
    },
    entry_points={
        "console_scripts": [
            "inkcraft-capture=tools.usb_capture:main",
            "inkcraft-parse=tools.escp_parser:main",
            "inkcraft-command=tools.printer_commander:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Manufacturing",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Printing",
    ],
    python_requires=">=3.8",
) 