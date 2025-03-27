#!/usr/bin/env python
"""
InkCraft RIP Printer Connection Test

This script tests the connection to an Epson DTG printer and verifies that 
basic communication is working correctly. It's a quick diagnostic tool to 
ensure your setup is ready for reverse engineering work.
"""

import os
import sys
import time
import argparse
import platform
from datetime import datetime

try:
    import usb.core
    import usb.util
except ImportError:
    print("Error: PyUSB library not found.")
    print("Please install it using: pip install pyusb")
    sys.exit(1)

# Epson vendor ID
EPSON_VENDOR_ID = 0x04b8

# Test sequence
TEST_COMMANDS = [
    {
        "name": "Initialize Printer",
        "hex": "1B 40",  # ESC @
        "purpose": "Reset the printer to its initial state",
        "expect_response": False
    },
    {
        "name": "Status Request",
        "hex": "1B 76",  # ESC v - Request status on some Epson printers
        "purpose": "Request printer status information",
        "expect_response": True
    }
]

# Test patterns for more thorough testing
TEST_PATTERNS = {
    "BASIC": [0, 1],  # Just the basic commands
    "STANDARD": [0, 1],  # Currently the same as BASIC
    "THOROUGH": [0, 1]  # Currently the same as BASIC
}

class ConnectionTester:
    def __init__(self, vendor_id=EPSON_VENDOR_ID, product_id=None, interface_num=0):
        self.vendor_id = vendor_id
        self.product_id = product_id  # Can be None to try any Epson printer
        self.interface_num = interface_num
        self.device = None
        self.interface = None
        self.endpoint_in = None
        self.endpoint_out = None
        self.test_results = []
        
    def find_printer(self):
        """Find the DTG printer connected via USB"""
        try:
            # If product ID is specified, look for that specific printer
            if self.product_id:
                self.device = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
                if self.device:
                    print(f"Found printer with VID:PID = {self.vendor_id:04x}:{self.product_id:04x}")
                    return True
                else:
                    print(f"No printer found with VID:PID = {self.vendor_id:04x}:{self.product_id:04x}")
                    return False
            
            # If no product ID is specified, look for any Epson printer
            devices = list(usb.core.find(idVendor=self.vendor_id, find_all=True))
            if not devices:
                print(f"No Epson printers found (Vendor ID: {self.vendor_id:04x})")
                return False
                
            # List all found printers
            print(f"Found {len(devices)} Epson device(s):")
            for i, dev in enumerate(devices):
                try:
                    product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else "Unknown"
                except:
                    product = "Unknown"
                    
                print(f"  {i+1}. {product} (VID:PID = {dev.idVendor:04x}:{dev.idProduct:04x})")
                
            # Use the first printer found
            self.device = devices[0]
            self.product_id = self.device.idProduct
            print(f"\nSelected printer: VID:PID = {self.vendor_id:04x}:{self.product_id:04x}")
            return True
                
        except Exception as e:
            print(f"Error finding printer: {e}")
            return False
    
    def setup_connection(self):
        """Initialize the device for communication"""
        if not self.device:
            return False
            
        try:
            # Get device information
            print("\nPrinter Information:")
            try:
                if hasattr(self.device, 'iManufacturer') and self.device.iManufacturer:
                    manufacturer = usb.util.get_string(self.device, self.device.iManufacturer)
                    print(f"  Manufacturer: {manufacturer}")
                
                if hasattr(self.device, 'iProduct') and self.device.iProduct:
                    product = usb.util.get_string(self.device, self.device.iProduct)
                    print(f"  Product: {product}")
                
                if hasattr(self.device, 'iSerialNumber') and self.device.iSerialNumber:
                    serial = usb.util.get_string(self.device, self.device.iSerialNumber)
                    print(f"  Serial Number: {serial}")
            except Exception as e:
                print(f"  Warning: Could not read device strings: {e}")
            
            print(f"  VID:PID: {self.device.idVendor:04x}:{self.device.idProduct:04x}")
            
            # Set configuration
            self.device.set_configuration()
            print("  Configuration set")
            
            # Get interface
            config = self.device.get_active_configuration()
            self.interface = config[(0,0)]
            print(f"  Interface: {self.interface.bInterfaceNumber}")
            
            # Detach kernel driver if active (AFTER getting interface)
            if platform.system() != 'Windows':  # Only on non-Windows systems
                try:
                    if self.device.is_kernel_driver_active(self.interface.bInterfaceNumber):
                        self.device.detach_kernel_driver(self.interface.bInterfaceNumber)
                        print("  Kernel driver detached")
                except Exception as e:
                    print(f"  Warning: Could not detach kernel driver: {e}")
            
            # Find endpoints
            for ep in self.interface:
                ep_addr = ep.bEndpointAddress
                if usb.util.endpoint_direction(ep_addr) == usb.util.ENDPOINT_IN:
                    self.endpoint_in = ep
                    print(f"  Found IN endpoint: 0x{ep_addr:02x}")
                else:
                    self.endpoint_out = ep
                    print(f"  Found OUT endpoint: 0x{ep_addr:02x}")
                    
            if not self.endpoint_in or not self.endpoint_out:
                print("  Error: Could not find required endpoints")
                return False
                
            print("  Printer connection established")
            return True
            
        except Exception as e:
            print(f"Error setting up connection: {e}")
            return False
    
    def run_tests(self, test_pattern="BASIC"):
        """Run communication tests with the printer"""
        if not self.endpoint_out or not self.endpoint_in:
            print("Error: Printer not connected")
            return False
            
        pattern = TEST_PATTERNS.get(test_pattern.upper(), TEST_PATTERNS["BASIC"])
        
        print(f"\nRunning {test_pattern} test pattern ({len(pattern)} tests):")
        success_count = 0
        
        for i, test_idx in enumerate(pattern):
            test = TEST_COMMANDS[test_idx]
            print(f"\nTest {i+1}: {test['name']}")
            print(f"  Purpose: {test['purpose']}")
            print(f"  Command: {test['hex']}")
            
            result = self.send_test_command(test['hex'], test['expect_response'])
            if result['success']:
                success_count += 1
                print(f"  Result: SUCCESS")
                if result['response']:
                    print(f"  Response: {result['response']}")
            else:
                print(f"  Result: FAILED - {result['error']}")
                
            self.test_results.append({
                "test": test['name'],
                "command": test['hex'],
                "success": result['success'],
                "response": result['response'],
                "error": result['error'],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            })
            
            # Brief pause between tests
            time.sleep(0.5)
            
        print(f"\nTest Summary: {success_count}/{len(pattern)} tests passed")
        return success_count == len(pattern)
    
    def send_test_command(self, hex_command, expect_response=False):
        """Send a test command to the printer"""
        result = {
            "success": False,
            "response": None,
            "error": None
        }
        
        try:
            # Convert hex string to bytes
            hex_command = hex_command.replace(' ', '')
            if len(hex_command) % 2 != 0:
                result['error'] = "Invalid hex command (odd length)"
                return result
                
            command = bytes.fromhex(hex_command)
            
            # Send command
            bytes_written = self.device.write(self.endpoint_out.bEndpointAddress, command)
            
            if bytes_written != len(command):
                result['error'] = f"Failed to write all bytes (wrote {bytes_written}/{len(command)})"
                return result
                
            # Read response if expected
            if expect_response:
                try:
                    response = self.device.read(
                        self.endpoint_in.bEndpointAddress,
                        self.endpoint_in.wMaxPacketSize,
                        timeout=1000
                    )
                    
                    if response:
                        result['response'] = ' '.join([f"{b:02x}" for b in response])
                except usb.core.USBError as e:
                    if e.args and len(e.args) > 0 and isinstance(e.args[0], str) and 'timeout' in e.args[0].lower():
                        if expect_response:
                            result['error'] = "No response received (timeout)"
                            return result
                    else:
                        result['error'] = f"USB error: {e}"
                        return result
            
            result['success'] = True
            return result
                
        except Exception as e:
            result['error'] = f"Error: {e}"
            return result
    
    def check_system_info(self):
        """Check system information for USB support"""
        print("\nSystem Information:")
        print(f"  Operating System: {platform.system()} {platform.release()}")
        print(f"  Python Version: {platform.python_version()}")
        
        # Check for PyUSB version
        try:
            import usb
            print(f"  PyUSB Version: {usb.__version__}")
        except:
            print("  PyUSB: Not available or version unknown")
        
        # Check USB backend
        backend_name = "Unknown"
        try:
            backend = usb.backend.libusb1.get_backend()
            if backend:
                backend_name = "libusb1"
            else:
                backend = usb.backend.libusb0.get_backend()
                if backend:
                    backend_name = "libusb0"
                else:
                    backend = usb.backend.openusb.get_backend()
                    if backend:
                        backend_name = "openusb"
        except:
            pass
            
        print(f"  USB Backend: {backend_name}")
        
        # Check permissions on Linux
        if platform.system() == 'Linux':
            print("\nLinux USB Permissions:")
            try:
                import subprocess
                result = subprocess.run(['groups'], stdout=subprocess.PIPE, text=True)
                groups = result.stdout.strip().split()
                print(f"  User Groups: {', '.join(groups)}")
                if any(g in groups for g in ['lp', 'plugdev', 'uucp']):
                    print("  USB Access: Likely OK (user in relevant groups)")
                else:
                    print("  USB Access: May be restricted (user not in printer-related groups)")
            except:
                print("  Could not determine user groups")
    
    def close(self):
        """Release the USB device"""
        if self.device and self.interface:
            try:
                usb.util.release_interface(self.device, self.interface.bInterfaceNumber)
                # Re-attach kernel driver if needed
                try:
                    self.device.attach_kernel_driver(0)
                except Exception:
                    pass
                    
                print("\nPrinter connection closed")
                
            except Exception as e:
                print(f"\nError closing connection: {e}")
    
    def save_results(self, filename=None):
        """Save test results to a file"""
        if not self.test_results:
            print("No test results to save")
            return
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"connection_test_{timestamp}.json"
            
        try:
            # Get device information
            device_info = {
                "vendor_id": f"0x{self.device.idVendor:04x}" if self.device else None,
                "product_id": f"0x{self.device.idProduct:04x}" if self.device else None,
            }
            
            if self.device:
                try:
                    if hasattr(self.device, 'iManufacturer') and self.device.iManufacturer:
                        device_info["manufacturer"] = usb.util.get_string(self.device, self.device.iManufacturer)
                    
                    if hasattr(self.device, 'iProduct') and self.device.iProduct:
                        device_info["product"] = usb.util.get_string(self.device, self.device.iProduct)
                    
                    if hasattr(self.device, 'iSerialNumber') and self.device.iSerialNumber:
                        device_info["serial_number"] = usb.util.get_string(self.device, self.device.iSerialNumber)
                except:
                    pass
            
            # System information
            system_info = {
                "os": f"{platform.system()} {platform.release()}",
                "python_version": platform.python_version()
            }
            
            import json
            with open(filename, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "system_info": system_info,
                    "device_info": device_info,
                    "test_results": self.test_results
                }, f, indent=2)
                
            print(f"\nTest results saved to {filename}")
            
        except Exception as e:
            print(f"\nError saving test results: {e}")

def print_recommendations(success):
    """Print recommendations based on test results"""
    print("\nRecommendations:")
    
    if success:
        print("✓ Your printer connection is working correctly!")
        print("✓ You can proceed with USB sniffing and reverse engineering.")
        print("\nNext steps:")
        print("1. Use Wireshark with USBPcap to capture print data")
        print("2. Send test prints from Kothari Print Pro or Garment Creator")
        print("3. Analyze the captured data with tools/escp_parser.py")
        print("4. Use tools/command_dictionary.py to catalog discovered commands")
    else:
        print("✗ There were issues with your printer connection.")
        print("\nTroubleshooting steps:")
        print("1. Ensure the printer is powered on and connected via USB")
        print("2. Check USB cable and try a different USB port")
        print("3. Ensure no other software is currently using the printer")
        print("4. On Windows: Check Device Manager for issues")
        print("5. On Linux: Ensure you have proper permissions (try running with sudo)")
        print("6. On macOS: Check System Information > USB for device recognition")
        print("\nAfter resolving issues, run this test again.")

def main():
    parser = argparse.ArgumentParser(description="InkCraft RIP Printer Connection Test")
    parser.add_argument("--vendor", type=lambda x: int(x, 0), default=EPSON_VENDOR_ID,
                      help="USB Vendor ID (default: 0x04B8 for Epson)")
    parser.add_argument("--product", type=lambda x: int(x, 0),
                      help="USB Product ID (if not specified, will try to find any Epson printer)")
    parser.add_argument("--interface", type=int, default=0,
                      help="Interface number (default: 0)")
    parser.add_argument("--pattern", choices=["BASIC", "STANDARD", "THOROUGH"], default="BASIC",
                      help="Test pattern to use (default: BASIC)")
    parser.add_argument("--save", action="store_true",
                      help="Save test results to a file")
    parser.add_argument("--output", help="Output file for test results")
    
    args = parser.parse_args()
    
    print("\n=== InkCraft RIP Printer Connection Test ===\n")
    
    # Create tester
    tester = ConnectionTester(
        vendor_id=args.vendor,
        product_id=args.product,
        interface_num=args.interface
    )
    
    # Check system information
    tester.check_system_info()
    
    # Find and connect to printer
    print("\nLooking for printer...")
    if not tester.find_printer():
        print("\nNo compatible printer found.")
        print_recommendations(False)
        return 1
    
    if not tester.setup_connection():
        print("\nFailed to establish connection with the printer.")
        print_recommendations(False)
        return 1
    
    # Run tests
    print("\nPrinter found and connected successfully.")
    success = tester.run_tests(args.pattern)
    
    # Save results if requested
    if args.save or args.output:
        tester.save_results(args.output)
    
    # Print recommendations
    print_recommendations(success)
    
    # Close connection
    tester.close()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 