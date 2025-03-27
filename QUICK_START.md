# InkCraft RIP Software - Quick Start Guide

This guide will help you quickly set up and start using the InkCraft RIP software for reverse engineering Epson DTG printer protocols.

## Prerequisites

- Windows 10/11
- Python 3.8 or newer
- Epson F2100 or F2130 DTG printer
- USB connection to printer
- Administrator privileges (for USB access)

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Install Wireshark with USBPcap** (for protocol analysis):
   - Download from [Wireshark's official website](https://www.wireshark.org/download.html)
   - Make sure to include the USBPcap component during installation

## Quick Setup for USB Analysis

The fastest way to start analyzing your DTG printer is to use the all-in-one runner script:

```
python run_usb_analysis.py --all
```

This will:
1. Capture USB traffic from your connected DTG printer
2. Parse the captured data for ESC/P commands
3. Launch an interactive mode to test commands with the printer

## Using Individual Tools

### USB Capture

To capture USB traffic from your printer:

```
python tools/usb_capture.py -d 120
```

This will capture for 120 seconds and save the results to a JSON file.

### ESC/P Parser

To analyze a previous capture:

```
python tools/escp_parser.py captured_file.json -o parsed_output.json
```

### Printer Commander

To test specific commands with your printer:

```
python tools/printer_commander.py --init --interactive
```

## Understanding the Project Structure

- `tools/`: Utilities for reverse engineering
  - `usb_capture.py`: USB traffic capture tool
  - `escp_parser.py`: ESC/P command parser
  - `printer_commander.py`: Tool to send commands to printer

- `src/driver/`: Printer driver implementation
  - `epson_dtg.py`: Core driver for Epson DTG printers

- `docs/`: Documentation
  - `usb_reverse_engineering_guide.md`: Detailed protocol analysis guide

## Next Steps

1. **Capture Print Jobs**: Use the capture tools while printing from Kothari Print Pro or Garment Creator

2. **Analyze Commands**: Use the parser to identify patterns in the print protocol

3. **Test Commands**: Use the commander to verify your understanding of commands

4. **Contribute Findings**: Add discovered commands to the driver implementation

## Troubleshooting

### USB Access Issues

If you encounter permission issues accessing the USB device:

1. Run your terminal or command prompt as Administrator
2. Verify that no other software is connected to the printer
3. Check that the printer is powered on and ready

### Python Dependency Issues

If you have issues with dependencies:

```
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Printer Not Found

If the tools can't find your printer:

1. Check Device Manager to verify the printer is properly connected
2. Note the Vendor ID and Product ID from Device Manager
3. Use these IDs explicitly with the tools:
   ```
   python tools/usb_capture.py --vendor 0x04b8 --product 0x0883
   ```

## Getting Help

- Check the [detailed documentation](docs/usb_reverse_engineering_guide.md)
- Open an issue on GitHub
- Contribute your findings back to the project 