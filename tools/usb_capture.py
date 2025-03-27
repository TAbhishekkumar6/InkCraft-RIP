#!/usr/bin/env python
"""
USB Capture Utility for DTG Printer Analysis
--------------------------------------------
This script helps capture and analyze USB communication between the 
computer and Epson F2100/F2130 DTG printers.

Requirements:
- Python 3.8+
- pyusb (pip install pyusb[backend-libusb1])
- pyshark (pip install pyshark)
- Wireshark with USBPcap installed
- Platform-specific USB drivers (see below)

Windows: Install libusb-win32 or WinUSB via Zadig
macOS: brew install libusb
Linux: sudo apt-get install libusb-1.0-0-dev
"""

import sys
import os
import time
import argparse
import json
from datetime import datetime

# Try to import pyshark for packet analysis
try:
    import pyshark
    PYSHARK_AVAILABLE = True
except ImportError:
    print("Warning: pyshark not found. Live packet analysis will be disabled.")
    print("To enable packet analysis, install pyshark:")
    print("    pip install pyshark")
    print("\nAlso ensure Wireshark is installed:")
    if sys.platform == 'win32':
        print("    Download from: https://www.wireshark.org/download.html")
        print("    Make sure to install USBPcap during Wireshark installation")
    elif sys.platform == 'darwin':
        print("    brew install wireshark")
    else:
        print("    sudo apt-get install wireshark tshark")
    PYSHARK_AVAILABLE = False

# Handle USB module imports with proper error handling and backend verification
try:
    import usb
    import usb.core
    import usb.util
    import usb.backend.libusb1
    import usb.backend.libusb0
    
    # Verify USB backend availability
    backend = None
    backend_errors = []
    
    # Try libusb1 first
    try:
        backend = usb.backend.libusb1.get_backend()
        if backend:
            print("Using libusb1 backend")
    except Exception as e:
        backend_errors.append(f"libusb1 error: {str(e)}")
    
    # Try libusb0 if libusb1 failed
    if not backend:
        try:
            backend = usb.backend.libusb0.get_backend()
            if backend:
                print("Using libusb0 backend")
        except Exception as e:
            backend_errors.append(f"libusb0 error: {str(e)}")
    
    if not backend:
        error_msg = "\n".join([
            "Error: No USB backend available. Install platform-specific drivers:",
            "Windows: Use Zadig from https://zadig.akeo.ie to install libusb-win32",
            "macOS: brew install libusb",
            "Linux: sudo apt-get install libusb-1.0-0-dev",
            "\nDetailed errors:",
            *backend_errors
        ])
        raise ImportError(error_msg)

except ImportError as e:
    print("USB library initialization failed!")
    print("\nError details:", str(e))
    print("\nTo fix this:")
    print("1. Install PyUSB: pip install pyusb[backend-libusb1]")
    print("2. Install platform-specific drivers:")
    if sys.platform == 'win32':
        print("   Windows:")
        print("   a. Download Zadig from https://zadig.akeo.ie")
        print("   b. Run Zadig and select your printer")
        print("   c. Install libusb-win32 driver")
    elif sys.platform == 'darwin':
        print("   macOS: brew install libusb")
    else:
        print("   Linux: sudo apt-get install libusb-1.0-0-dev")
    sys.exit(1)

# Epson F2100/F2130 USB identifiers
# Note: These need to be verified with actual devices
EPSON_VENDOR_ID = 0x04b8  # Epson vendor ID
POSSIBLE_PRODUCT_IDS = [
    0x0883,  # Possible F2100
    0x0884,  # Possible F2130
    # Add more potential product IDs
]

class USBPrinterAnalyzer:
    def __init__(self, vendor_id=EPSON_VENDOR_ID, product_ids=POSSIBLE_PRODUCT_IDS):
        self.vendor_id = vendor_id
        self.product_ids = product_ids
        self.device = None
        self.interface = None
        self.endpoint_in = None
        self.endpoint_out = None
        self.capture_data = []
        self.wireshark_capture = None
        
    def find_printer(self):
        """Find the DTG printer connected via USB"""
        for product_id in self.product_ids:
            try:
                # Use the verified backend
                dev = usb.core.find(
                    backend=backend,
                    idVendor=self.vendor_id, 
                    idProduct=product_id
                )
                if dev is not None:
                    print(f"Found printer with VID:PID = {self.vendor_id:04x}:{product_id:04x}")
                    self.device = dev
                    return True
            except usb.core.USBError as e:
                print(f"USB Error while searching for printer: {e}")
                return False
            except Exception as e:
                print(f"Unexpected error while searching for printer: {e}")
                return False
        
        print("No Epson DTG printer found. Is it connected and powered on?")
        print("\nTroubleshooting steps:")
        print("1. Check USB cable connection")
        print("2. Ensure printer is powered on")
        print("3. On Windows, verify correct driver is installed using Zadig")
        print("4. Try a different USB port")
        print("5. Run this script with administrator/root privileges")
        return False
        
    def get_device_info(self):
        """Get detailed information about the connected printer"""
        if not self.device:
            return None
            
        try:
            # Get device information
            manufacturer = usb.util.get_string(self.device, self.device.iManufacturer)
            product = usb.util.get_string(self.device, self.device.iProduct)
            serial_number = usb.util.get_string(self.device, self.device.iSerialNumber)
            
            # Get configuration information
            config = self.device.get_active_configuration()
            interface_number = config[(0,0)].bInterfaceNumber
            
            return {
                "manufacturer": manufacturer,
                "product": product,
                "serial_number": serial_number,
                "vendor_id": f"0x{self.device.idVendor:04x}",
                "product_id": f"0x{self.device.idProduct:04x}",
                "interface_number": interface_number
            }
            
        except Exception as e:
            print(f"Error getting device info: {e}")
            return None
    
    def setup_capture(self):
        """Initialize the device for communication"""
        if not self.device:
            return False
            
        try:
            # Detach kernel driver if active
            if self.device.is_kernel_driver_active(0):
                self.device.detach_kernel_driver(0)
            
            # Set configuration
            self.device.set_configuration()
            
            # Get configuration and interface
            config = self.device.get_active_configuration()
            self.interface = config[(0,0)]
            
            # Find endpoints
            for ep in self.interface:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    self.endpoint_in = ep
                else:
                    self.endpoint_out = ep
                    
            if not self.endpoint_in or not self.endpoint_out:
                print("Could not find required endpoints")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error setting up capture: {e}")
            return False
    
    def start_wireshark_capture(self, interface=None):
        """Start capturing packets with Wireshark/pyshark if available"""
        if not PYSHARK_AVAILABLE:
            return False
            
        try:
            # If no interface specified, try to find a USBPcap interface
            if interface is None:
                capture = pyshark.LiveCapture()
                for iface in capture.interfaces:
                    if 'USBPcap' in iface:
                        interface = iface
                        break
                
                if interface is None:
                    print("No USBPcap interface found. Please install USBPcap or specify interface manually.")
                    return False
            
            # Set up capture with USB filters for our device
            self.wireshark_capture = pyshark.LiveCapture(
                interface=interface,
                display_filter=f'usb.idVendor == {self.vendor_id:#04x}'
            )
            
            print(f"Started Wireshark capture on interface: {interface}")
            return True
            
        except Exception as e:
            print(f"Error starting Wireshark capture: {e}")
            if "Permission denied" in str(e):
                print("\nTry running with administrator/root privileges")
                if sys.platform != 'win32':
                    print("Or add your user to the 'wireshark' group:")
                    print("    sudo usermod -a -G wireshark $USER")
                    print("    (Log out and back in for this to take effect)")
            return False
    
    def analyze_packet(self, packet):
        """Analyze a USB packet captured by pyshark"""
        if not hasattr(packet, 'usb'):
            return None
            
        try:
            # Extract USB-specific information
            packet_info = {
                'timestamp': packet.sniff_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'source': packet.usb.src,
                'destination': packet.usb.dst,
                'endpoint': getattr(packet.usb, 'endpoint_address', None),
                'length': packet.length,
                'setup_flag': hasattr(packet.usb, 'setup_flag'),
                'data_flag': hasattr(packet.usb, 'data_flag'),
                'status_flag': hasattr(packet.usb, 'status_flag'),
                'direction': 'IN' if hasattr(packet.usb, 'endpoint_address_direction') 
                            and packet.usb.endpoint_address_direction == '1' else 'OUT'
            }
            
            # Try to get the actual data
            if hasattr(packet.usb, 'capdata'):
                data = bytes.fromhex(packet.usb.capdata.replace(':', ''))
                packet_info['data'] = {
                    'hex': ' '.join(f'{b:02x}' for b in data),
                    'ascii': ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
                }
                
                # Look for known ESC/P commands
                if data.startswith(b'\x1b'):  # ESC command
                    if len(data) > 1:
                        cmd = data[1:2]
                        if cmd == b'@':
                            packet_info['command'] = 'ESC @ (Initialize printer)'
                        elif cmd == b'(':
                            if len(data) > 2:
                                subcmd = data[2:3]
                                if subcmd == b'G':
                                    packet_info['command'] = 'ESC ( G (Graphics mode)'
                                elif subcmd == b'U':
                                    packet_info['command'] = 'ESC ( U (Set unit)'
                                elif subcmd == b'K':
                                    packet_info['command'] = 'ESC ( K (Set color)'
                                elif subcmd == b'i':
                                    packet_info['command'] = 'ESC ( i (Set ink)'
            
            return packet_info
            
        except Exception as e:
            print(f"Error analyzing packet: {e}")
            return None
    
    def capture_traffic(self, duration=30, save_to_file=True, use_wireshark=True):
        """Capture USB traffic using both direct USB access and Wireshark if available"""
        if use_wireshark and PYSHARK_AVAILABLE:
            if not self.start_wireshark_capture():
                print("Falling back to direct USB capture only")
            else:
                print("Using both direct USB capture and Wireshark for analysis")
        
        if not self.endpoint_in or not self.endpoint_out:
            print("Device not properly set up for capture")
            return False
            
        print(f"Starting USB traffic capture for {duration} seconds...")
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                try:
                    # Read data from the printer
                    data = self.device.read(self.endpoint_in.bEndpointAddress, 
                                          self.endpoint_in.wMaxPacketSize, 
                                          timeout=100)
                    
                    if data:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                        packet_data = {
                            "timestamp": timestamp,
                            "direction": "IN",
                            "data": data.tolist(),
                            "hex": ' '.join([f"{b:02x}" for b in data]),
                            "ascii": ''.join([chr(b) if 32 <= b <= 126 else '.' for b in data])
                        }
                        self.capture_data.append(packet_data)
                        print(f"IN: {packet_data['hex'][:64]}{'...' if len(packet_data['hex']) > 64 else ''}")
                
                except usb.core.USBError as e:
                    # Timeout is normal, continue
                    if e.args[0] != 'Operation timed out':
                        print(f"USB Error: {e}")
                
                time.sleep(0.001)  # Short delay to prevent CPU overuse
                
            print(f"Capture completed. Collected {len(self.capture_data)} packets.")
            
            if save_to_file and self.capture_data:
                self.save_capture_data()
                
            return True
            
        except KeyboardInterrupt:
            print("\nCapture stopped by user")
            if save_to_file and self.capture_data:
                self.save_capture_data()
            return True
            
        except Exception as e:
            print(f"Error during capture: {e}")
            return False
        
    def save_capture_data(self):
        """Save captured data to a file"""
        if not self.capture_data:
            print("No data to save")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dtg_usb_capture_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump({
                    "capture_info": {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "device_info": self.get_device_info(),
                        "packet_count": len(self.capture_data)
                    },
                    "packets": self.capture_data
                }, f, indent=2)
                
            print(f"Capture data saved to {filename}")
            
        except Exception as e:
            print(f"Error saving capture data: {e}")
    
    def close(self):
        """Release the USB device"""
        if self.device:
            try:
                usb.util.release_interface(self.device, self.interface.bInterfaceNumber)
                # Re-attach kernel driver if needed
                try:
                    self.device.attach_kernel_driver(0)
                except Exception:
                    pass
            except Exception as e:
                print(f"Error closing device: {e}")

def print_instructions():
    """Print additional instructions for USB packet analysis"""
    print("\nAdditional Instructions:")
    print("1. Make sure Wireshark with USBPcap is installed")
    print("2. In Wireshark, select the appropriate USBPcap interface")
    print("3. Apply a filter like 'usb.idVendor == 0x04b8' to focus on Epson traffic")
    print("4. Start a capture in Wireshark before printing a test page")
    print("5. Save the Wireshark capture as a PCAP file for detailed analysis")
    print("6. Use this script alongside Wireshark for comprehensive analysis")
    print("\nCommon ESC/P commands to look for:")
    print("- ESC @ : Initialize printer")
    print("- ESC ( G : Select graphics mode")
    print("- ESC ( U : Set unit")
    print("- ESC ( K : Set color")
    print("- ESC ( i : Set ink type/density")

def main():
    parser = argparse.ArgumentParser(description="DTG Printer USB Communication Analyzer")
    parser.add_argument("-d", "--duration", type=int, default=60, 
                        help="Duration to capture USB traffic (seconds)")
    parser.add_argument("-i", "--info", action="store_true", 
                        help="Only show device information, no capture")
    parser.add_argument("--vendor", type=lambda x: int(x, 0), default=EPSON_VENDOR_ID,
                        help="USB Vendor ID (default: 0x04b8 for Epson)")
    parser.add_argument("--no-wireshark", action="store_true",
                        help="Disable Wireshark/pyshark capture even if available")
    parser.add_argument("--interface", type=str,
                        help="Specify Wireshark capture interface (default: auto-detect USBPcap)")
    args = parser.parse_args()
    
    # Check if running with sufficient privileges
    if os.geteuid() if hasattr(os, 'geteuid') else 0 != 0:
        if sys.platform != 'win32':
            print("Warning: Not running with root privileges. USB capture may fail.")
            print("Consider running with sudo if you encounter permission errors.")
    
    analyzer = USBPrinterAnalyzer(vendor_id=args.vendor)
    
    if not analyzer.find_printer():
        print_instructions()
        return 1
    
    device_info = analyzer.get_device_info()
    if device_info:
        print("\nPrinter Information:")
        for key, value in device_info.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
    
    if args.info:
        return 0
    
    if not analyzer.setup_capture():
        print("Failed to set up capture. Try running with administrator/root privileges.")
        print_instructions()
        return 1
    
    try:
        analyzer.capture_traffic(
            duration=args.duration,
            use_wireshark=not args.no_wireshark,
            save_to_file=True
        )
    except KeyboardInterrupt:
        print("\nCapture stopped by user")
    except Exception as e:
        print(f"Error during capture: {e}")
    finally:
        analyzer.close()
    
    print_instructions()
    return 0

if __name__ == "__main__":
    sys.exit(main()) 