# USB Reverse Engineering Guide for DTG Printers

This guide explains the process of reverse engineering the Epson F2100/F2130 DTG printer's USB communication protocol, which is essential for developing a custom RIP software solution.

## Prerequisites

- Windows 10/11 computer
- Epson F2100 or F2130 DTG printer connected via USB
- Wireshark with USBPcap extension installed
- Python 3.8+ with pyusb library
- Basic understanding of printer communication protocols

## USB Sniffing Setup

### 1. Install Required Software

1. **Wireshark with USBPcap**:
   - Download from [Wireshark's official website](https://www.wireshark.org/download.html)
   - During installation, make sure to check the "USBPcap" component

2. **Python Environment**:
   - Install Python 3.8 or newer
   - Install required libraries:
     ```
     pip install pyusb
     pip install pyshark  # Optional, for PCAP file analysis
     ```

### 2. Identify the Printer's USB Identifiers

1. Connect the printer to your computer and turn it on
2. Open Device Manager in Windows
3. Expand "Universal Serial Bus controllers"
4. Find your Epson printer (it may be under "Printers" instead)
5. Right-click and select "Properties"
6. Go to the "Details" tab
7. Select "Hardware Ids" from the Property dropdown
8. Note the VID (Vendor ID) and PID (Product ID) values
   - Example: `USB\VID_04B8&PID_0883` (where 04B8 is Epson's VID)

## Capturing USB Traffic

### 1. Prepare Test Files

1. Create or obtain test image files for printing
2. Load these files in both Kothari Print Pro and Garment Creator software

### 2. Set Up Wireshark for Capturing

1. Launch Wireshark as Administrator
2. Select the appropriate USBPcap interface
   - Look for the interface that includes your Epson printer
3. Set up a display filter to focus on your printer:
   - `usb.idVendor == 0x04b8 && usb.idProduct == 0x0883`
   - Adjust the PID if your printer model is different

### 3. Capture Print Commands

1. Start the capture in Wireshark
2. Launch the printing software (Kothari Print Pro or Garment Creator)
3. Load an image and initiate a print job
4. Let the printer complete its job
5. Stop the capture in Wireshark
6. Save the capture file as a PCAP file (e.g., `epson_f2100_print.pcapng`)

### 4. Parallel Capture with Python Tools

For more detailed analysis, you can use the Python tools provided in this project:

1. Navigate to the tools directory:
   ```
   cd InkCraft-RIP/tools
   ```

2. Run the USB capture script:
   ```
   python usb_capture.py -d 120
   ```
   This will capture USB traffic for 120 seconds

3. Save both Wireshark and Python capture data for analysis

## Analyzing Captured Data

### 1. Initial Protocol Analysis in Wireshark

1. Open your saved PCAP file in Wireshark
2. Look for patterns in the USB data transfers
3. Focus on the beginning of the capture to identify initialization commands
4. Note the sequences that occur before data transfer begins
5. Look for large data transfers which likely contain the actual image data
6. Identify the commands that finalize the print job

### 2. Using the ESC/P Parser

Our ESC/P parser tool can help identify standard ESC/P commands in the capture:

```
python escp_parser.py -p epson_f2100_print.pcapng -o parsed_commands.json
```

This will analyze the PCAP file and identify known ESC/P commands.

### 3. Identifying Command Patterns

1. Look for common ESC/P command patterns:
   - `ESC @` (1B 40): Initialize printer
   - `ESC ( G` (1B 28 47): Select graphics mode
   - `ESC ( U` (1B 28 55): Set unit
   - `ESC ( K` (1B 28 4B): Set color selection
   - `ESC *` (1B 2A): Bit image mode commands

2. Pay attention to sequences that repeat with different parameters:
   - These likely control specific aspects like color channels or print head positioning

3. Look for unique command sequences that aren't standard ESC/P:
   - DTG-specific commands for white ink control
   - Special commands for underbase printing
   - High-resolution control sequences

### 4. Testing Identified Commands

Use the printer commander tool to test individual commands:

```
python printer_commander.py --command "1b 40"  # Try the initialize command
```

Test combinations of commands to verify their function:

```
python printer_commander.py --init --interactive
```

This opens an interactive mode where you can experiment with command sequences.

## Documenting the Protocol

As you discover command patterns, document them in a structured format:

1. Command identifier
2. Hex sequence
3. Parameters and their meanings
4. Function and effect
5. Any variants or related commands

Example documentation format:

```
Command: Initialize Printer
Hex: 1B 40
Parameters: None
Function: Resets the printer to its default state
Notes: Commonly used at start of print job
```

## Building the Driver

Once you've identified the core command set needed for printing, integrate them into the driver module in `src/driver/epson_dtg.py`:

1. Add newly discovered commands to the `COMMANDS` dictionary
2. Implement functions that use these commands for practical printing tasks
3. Test each function individually to ensure it communicates correctly with the printer
4. Document any printer-specific behaviors or limitations

## Common Challenges and Solutions

### Challenge: Identifying Command Boundaries

- **Solution**: Look for escape sequences (`0x1B`) which typically start ESC/P commands. Determine parameter lengths based on the command structure.

### Challenge: Distinguishing Control Commands from Image Data

- **Solution**: Control commands are typically short and contain escape sequences, while image data is usually large blocks of binary data.

### Challenge: Understanding White Ink Controls

- **Solution**: Compare captures when printing with and without white ink. The differences will highlight the white ink control mechanisms.

### Challenge: Determining Resolution Settings

- **Solution**: Capture prints at different resolutions and compare the commands and data sizes.

## Resources

- [ESC/P Reference Manual](https://files.support.epson.com/pdf/general/escp2ref.pdf)
- [USB Protocol Documentation](https://www.usb.org/documents)
- [PyUSB Documentation](https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst)

## Next Steps

After successful reverse engineering of the protocol:

1. Complete the driver implementation
2. Develop the RIP core for image processing
3. Create a user interface that leverages the driver
4. Test with various image types and print settings
5. Optimize performance for production use 