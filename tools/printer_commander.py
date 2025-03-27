#!/usr/bin/env python
"""
DTG Printer Commander
--------------------
A utility to send custom ESC/P commands to Epson F2100/F2130 DTG printers.

This tool allows testing identified commands during the reverse engineering process
to verify their functions and effects on the printer directly.
"""

import sys
import os
import time
import argparse
import json
import binascii
from datetime import datetime

try:
    import usb.core
    import usb.util
except ImportError:
    print("Error: PyUSB library not found.")
    print("Please install it using: pip install pyusb")
    sys.exit(1)

# Epson F2100/F2130 USB identifiers (same as in usb_capture.py)
EPSON_VENDOR_ID = 0x04b8  # Epson vendor ID
POSSIBLE_PRODUCT_IDS = [
    0x0883,  # Possible F2100
    0x0884,  # Possible F2130
    # Add more potential product IDs as discovered
]

# Common ESC/P command templates
INIT_PRINTER = b'\x1b@'              # ESC @ - Initialize printer
SELECT_GRAPHICS = b'\x1b(G\x01\x00\x01'  # ESC ( G - Select graphics mode
SELECT_COLOR = b'\x1b(K\x02\x00\x00\x01'  # ESC ( K - Set color (replace last byte for color)

class PrinterCommander:
    def __init__(self, vendor_id=EPSON_VENDOR_ID, product_ids=POSSIBLE_PRODUCT_IDS):
        self.vendor_id = vendor_id
        self.product_ids = product_ids
        self.device = None
        self.interface = None
        self.endpoint_in = None
        self.endpoint_out = None
        self.command_log = []
        
    def find_printer(self):
        """Find the DTG printer connected via USB"""
        for product_id in self.product_ids:
            dev = usb.core.find(idVendor=self.vendor_id, idProduct=product_id)
            if dev is not None:
                print(f"Found printer with VID:PID = {self.vendor_id:04x}:{product_id:04x}")
                self.device = dev
                return True
        
        print("No Epson DTG printer found. Is it connected and powered on?")
        return False
    
    def setup_printer(self):
        """Initialize the device for communication"""
        if not self.device:
            return False
            
        try:
            # Detach kernel driver if active
            if self.device.is_kernel_driver_active(0):
                try:
                    self.device.detach_kernel_driver(0)
                    print("Kernel driver detached")
                except Exception as e:
                    print(f"Warning: Could not detach kernel driver: {e}")
            
            # Set configuration
            self.device.set_configuration()
            
            # Get configuration and interface
            config = self.device.get_active_configuration()
            self.interface = config[(0,0)]
            
            # Find endpoints
            for ep in self.interface:
                ep_addr = ep.bEndpointAddress
                if usb.util.endpoint_direction(ep_addr) == usb.util.ENDPOINT_IN:
                    self.endpoint_in = ep
                    print(f"Found IN endpoint: {ep_addr:02x}")
                else:
                    self.endpoint_out = ep
                    print(f"Found OUT endpoint: {ep_addr:02x}")
                    
            if not self.endpoint_in or not self.endpoint_out:
                print("Could not find required endpoints")
                return False
                
            print("Printer successfully initialized")
            return True
            
        except Exception as e:
            print(f"Error setting up printer: {e}")
            return False
    
    def send_command(self, command, read_response=True, response_timeout=1000):
        """Send a raw command to the printer"""
        if not self.endpoint_out:
            print("Printer not initialized")
            return False
        
        # Ensure command is in bytes format
        if isinstance(command, str):
            if command.startswith('0x') or ' ' in command:
                # Convert from hex string
                command = bytes.fromhex(command.replace('0x', '').replace(' ', ''))
            else:
                # Convert from ASCII
                command = command.encode()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        try:
            # Log the command
            cmd_hex = ' '.join([f"{b:02x}" for b in command])
            print(f"Sending: {cmd_hex}")
            
            # Send the command
            bytes_written = self.device.write(self.endpoint_out.bEndpointAddress, command)
            
            cmd_log = {
                "timestamp": timestamp,
                "direction": "OUT",
                "bytes_count": bytes_written,
                "data_hex": cmd_hex,
                "description": f"Sent {bytes_written} bytes"
            }
            self.command_log.append(cmd_log)
            
            # Read response if requested
            if read_response:
                response = self._read_response(timeout=response_timeout)
                if response:
                    return True
            
            return bytes_written > 0
            
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def _read_response(self, timeout=1000, max_reads=5):
        """Read response from the printer"""
        if not self.endpoint_in:
            return None
        
        responses = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        try:
            # Try reading multiple times if needed
            for _ in range(max_reads):
                try:
                    response = self.device.read(
                        self.endpoint_in.bEndpointAddress,
                        self.endpoint_in.wMaxPacketSize,
                        timeout=timeout
                    )
                    
                    if response:
                        resp_hex = ' '.join([f"{b:02x}" for b in response])
                        print(f"Response: {resp_hex}")
                        
                        resp_log = {
                            "timestamp": timestamp,
                            "direction": "IN",
                            "bytes_count": len(response),
                            "data_hex": resp_hex,
                            "description": f"Received {len(response)} bytes"
                        }
                        self.command_log.append(resp_log)
                        responses.append(response)
                        
                        # Short timeout for additional data
                        timeout = 100
                        
                except usb.core.USBError as e:
                    # Timeout is normal after getting all data
                    if e.args[0] == 'Operation timed out':
                        break
                    print(f"USB Error: {e}")
                    break
            
            return responses
                
        except Exception as e:
            print(f"Error reading response: {e}")
            return None
    
    def run_command_file(self, filename):
        """Run a series of commands from a JSON file"""
        try:
            with open(filename, 'r') as f:
                commands = json.load(f)
            
            if not isinstance(commands, list):
                print(f"Error: Expected a list of commands in {filename}")
                return False
            
            success_count = 0
            for i, cmd in enumerate(commands):
                print(f"\nExecuting command {i+1}/{len(commands)}")
                
                # Get command data
                if isinstance(cmd, dict):
                    command_data = cmd.get('command', '')
                    delay = cmd.get('delay', 0)
                    description = cmd.get('description', '')
                    
                    if description:
                        print(f"Description: {description}")
                        
                    if not command_data:
                        print("Warning: Empty command, skipping")
                        continue
                else:
                    command_data = cmd
                    delay = 0
                
                # Send the command
                if self.send_command(command_data):
                    success_count += 1
                
                # Delay if specified
                if delay > 0:
                    print(f"Waiting {delay} ms...")
                    time.sleep(delay / 1000)
            
            print(f"\nCommand execution complete. {success_count}/{len(commands)} successful.")
            return success_count > 0
                
        except Exception as e:
            print(f"Error executing command file {filename}: {e}")
            return False
    
    def save_log(self, filename=None):
        """Save command log to a file"""
        if not self.command_log:
            print("No commands logged")
            return
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dtg_command_log_{timestamp}.json"
            
        try:
            with open(filename, 'w') as f:
                json.dump({
                    "log_info": {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "command_count": len(self.command_log)
                    },
                    "commands": self.command_log
                }, f, indent=2)
                
            print(f"Command log saved to {filename}")
            
        except Exception as e:
            print(f"Error saving command log: {e}")
    
    def initialize_printer(self):
        """Initialize the printer with standard commands"""
        print("Initializing printer...")
        
        # Send initialize command
        if not self.send_command(INIT_PRINTER):
            print("Failed to initialize printer")
            return False
            
        # Slight delay
        time.sleep(0.5)
        
        # Enter graphics mode
        if not self.send_command(SELECT_GRAPHICS):
            print("Failed to enter graphics mode")
            return False
            
        print("Printer initialized successfully")
        return True
    
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
                    
                print("Printer connection closed")
                
            except Exception as e:
                print(f"Error closing device: {e}")

def print_help_examples():
    """Print examples of how to use the tool"""
    print("\nExamples:")
    print("  1. Send initialize command:")
    print("     python printer_commander.py --command \"1b 40\"")
    print()
    print("  2. Send graphics mode command:")
    print("     python printer_commander.py --command \"1b 28 47 01 00 01\"")
    print()
    print("  3. Run a sequence of commands from a file:")
    print("     python printer_commander.py --file commands.json")
    print()
    print("  4. Initialize the printer and enter interactive mode:")
    print("     python printer_commander.py --init --interactive")
    print()
    print("Command File Format (JSON):")
    print("""  [
    {
      "command": "1b 40",
      "description": "Initialize printer",
      "delay": 500
    },
    {
      "command": "1b 28 47 01 00 01",
      "description": "Enter graphics mode",
      "delay": 100
    }
  ]""")

def interactive_mode(commander):
    """Interactive command mode"""
    print("\nEntering interactive mode. Type 'exit' to quit, 'help' for help.")
    
    while True:
        try:
            cmd = input("\nEnter command (hex): ").strip()
            
            if not cmd:
                continue
                
            if cmd.lower() == 'exit' or cmd.lower() == 'quit':
                break
                
            if cmd.lower() == 'help':
                print("\nCommands:")
                print("  hex_value  - Send hex bytes (e.g., '1b 40')")
                print("  init       - Initialize printer")
                print("  log        - Save command log")
                print("  exit/quit  - Exit interactive mode")
                continue
                
            if cmd.lower() == 'init':
                commander.initialize_printer()
                continue
                
            if cmd.lower() == 'log':
                commander.save_log()
                continue
                
            # Default: treat as hex command
            commander.send_command(cmd)
                
        except KeyboardInterrupt:
            print("\nExiting interactive mode...")
            break
            
        except Exception as e:
            print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="DTG Printer Command Utility")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-c", "--command", help="Hex command to send (e.g., '1b 40')")
    group.add_argument("-f", "--file", help="JSON file containing commands to run")
    group.add_argument("-i", "--interactive", action="store_true", help="Enter interactive mode")
    
    parser.add_argument("--init", action="store_true", help="Initialize printer before sending commands")
    parser.add_argument("--log", help="Save command log to specified file")
    parser.add_argument("--vendor", type=lambda x: int(x, 0), default=EPSON_VENDOR_ID,
                      help="USB Vendor ID (default: 0x04b8 for Epson)")
    parser.add_argument("--product", type=lambda x: int(x, 0), 
                      help="USB Product ID (will try known IDs if not specified)")
    
    args = parser.parse_args()
    
    # Show help if no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        print_help_examples()
        return 0
    
    # Setup printer commander
    if args.product:
        commander = PrinterCommander(vendor_id=args.vendor, product_ids=[args.product])
    else:
        commander = PrinterCommander(vendor_id=args.vendor)
    
    # Find and setup printer
    if not commander.find_printer():
        return 1
        
    if not commander.setup_printer():
        return 1
    
    # Initialize printer if requested
    if args.init:
        if not commander.initialize_printer():
            return 1
    
    try:
        # Process command, file, or interactive mode
        if args.command:
            commander.send_command(args.command)
            
        elif args.file:
            commander.run_command_file(args.file)
            
        elif args.interactive:
            interactive_mode(commander)
        
        # Save log if requested
        if args.log:
            commander.save_log(args.log)
        
    finally:
        # Always close the connection
        commander.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 