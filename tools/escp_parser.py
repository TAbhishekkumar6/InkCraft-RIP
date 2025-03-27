#!/usr/bin/env python
"""
ESC/P Command Parser for DTG Printer Analysis
---------------------------------------------
This script parses and interprets ESC/P commands from captured USB data
for Epson F2100/F2130 DTG printers.

It helps identify the commands used for controlling the printer, facilitating
the reverse engineering process of the printer's communication protocol.
"""

import sys
import os
import json
import argparse
from collections import defaultdict

# ESC/P Command Dictionary
# Based on known ESC/P2 and ESC/POS commands, needs validation for DTG printers
ESCP_COMMANDS = {
    b'\x1b@': 'Initialize printer',
    b'\x1b(G': 'Select graphics mode',
    b'\x1b(U': 'Set unit',
    b'\x1b(K': 'Set color selection',
    b'\x1b(i': 'Set ink density/type',
    b'\x1b(c': 'Set page format',
    b'\x1b(C': 'Set page length',
    b'\x1b(V': 'Set absolute vertical position',
    b'\x1b(v': 'Set relative vertical position',
    b'\x1b(H': 'Set horizontal spacing',
    b'\x1b$': 'Set absolute horizontal position',
    b'\x1b\\': 'Set relative horizontal position',
    b'\x1b(R': 'Select print color',
    b'\x1b(r': 'Select color tables',
    b'\x1b.': 'Graphics dot control',
    b'\x1b*': 'Select bit image mode',
    b'\x1bK': 'Select single-density graphics',
    b'\x1bL': 'Select double-density graphics',
    b'\x1bY': 'Select high-speed double-density graphics',
    b'\x1bZ': 'Select quadruple-density graphics',
    # Add more commands as discovered
}

# Special command sequence markers
ESC = b'\x1b'  # Escape character that typically starts ESC/P commands

class ESCPParser:
    def __init__(self):
        self.commands_found = defaultdict(int)
        self.parsed_data = []
        self.unknown_commands = set()
        
    def parse_file(self, filename):
        """Parse a JSON file containing captured USB data"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            if 'packets' not in data:
                print(f"Error: Invalid file format in {filename}")
                return False
                
            # Process each packet
            for packet in data['packets']:
                if 'data' in packet:
                    # If data is in hex string format, convert it to bytes
                    if isinstance(packet['data'], str):
                        try:
                            # Handle space-separated hex format
                            packet_data = bytes.fromhex(packet['data'].replace(' ', ''))
                        except ValueError:
                            print(f"Error: Could not parse hex data: {packet['data'][:50]}...")
                            continue
                    # If data is in list format (integers), convert to bytes
                    elif isinstance(packet['data'], list):
                        packet_data = bytes(packet['data'])
                    else:
                        print(f"Error: Unsupported data format: {type(packet['data'])}")
                        continue
                        
                    parsed = self.parse_packet(packet_data)
                    if parsed:
                        parsed_entry = {
                            "timestamp": packet.get('timestamp', ''),
                            "direction": packet.get('direction', ''),
                            "parsed_commands": parsed
                        }
                        self.parsed_data.append(parsed_entry)
            
            return True
                
        except Exception as e:
            print(f"Error parsing file {filename}: {e}")
            return False
    
    def parse_pcap(self, filename):
        """Parse a PCAP file containing USB capture data (requires pyshark)"""
        try:
            import pyshark
        except ImportError:
            print("Error: pyshark library not found.")
            print("Please install it using: pip install pyshark")
            return False
            
        try:
            cap = pyshark.FileCapture(filename, display_filter='usb.data_fragment')
            
            for packet in cap:
                if hasattr(packet, 'usb') and hasattr(packet.usb, 'data_fragment'):
                    packet_data = bytes.fromhex(packet.usb.data_fragment.replace(':', ''))
                    direction = "OUT" if hasattr(packet.usb, 'endpoint_address.direction') and packet.usb.get_field_value('endpoint_address.direction') == '1' else "IN"
                    
                    parsed = self.parse_packet(packet_data)
                    if parsed:
                        parsed_entry = {
                            "timestamp": packet.sniff_time.strftime("%Y-%m-%d %H:%M:%S.%f") if hasattr(packet, 'sniff_time') else '',
                            "direction": direction,
                            "parsed_commands": parsed
                        }
                        self.parsed_data.append(parsed_entry)
            
            cap.close()
            return True
                
        except Exception as e:
            print(f"Error parsing PCAP file {filename}: {e}")
            return False
    
    def parse_packet(self, data):
        """Parse a packet for ESC/P commands"""
        parsed_commands = []
        i = 0
        
        while i < len(data):
            # Look for ESC character
            if data[i:i+1] == ESC:
                # Try to match commands of different lengths
                matched = False
                for cmd_len in range(5, 1, -1):  # Try 5-char commands, then 4, 3, 2
                    if i + cmd_len <= len(data):
                        cmd = data[i:i+cmd_len]
                        if cmd in ESCP_COMMANDS:
                            # Extract parameter length for variable-length commands
                            param_len = 0
                            if cmd_len >= 3:  # Commands like ESC ( X n m
                                if i + cmd_len + 1 < len(data):
                                    param_len = data[i+cmd_len] + (data[i+cmd_len+1] * 256 if i+cmd_len+2 < len(data) else 0)
                            
                            # Extract parameters if present
                            params = []
                            if param_len > 0 and i + cmd_len + 2 + param_len <= len(data):
                                params = data[i+cmd_len+2:i+cmd_len+2+param_len]
                                
                            cmd_info = {
                                "position": i,
                                "command": cmd.hex(),
                                "description": ESCP_COMMANDS[cmd],
                                "parameters": params.hex() if params else ""
                            }
                            parsed_commands.append(cmd_info)
                            
                            self.commands_found[cmd] += 1
                            i += cmd_len + (param_len + 2 if param_len > 0 else 0)
                            matched = True
                            break
                
                # Try 2-character commands if no match yet
                if not matched and i + 2 <= len(data):
                    cmd = data[i:i+2]
                    if cmd in ESCP_COMMANDS:
                        # For simple commands like ESC @
                        cmd_info = {
                            "position": i,
                            "command": cmd.hex(),
                            "description": ESCP_COMMANDS[cmd],
                            "parameters": ""
                        }
                        parsed_commands.append(cmd_info)
                        
                        self.commands_found[cmd] += 1
                        i += 2
                        matched = True
                
                # If still no match, record as unknown command and continue
                if not matched:
                    # Try to capture complete unknown command
                    unknown_cmd = data[i:i+2]
                    self.unknown_commands.add(unknown_cmd)
                    i += 1
            else:
                i += 1
                
        return parsed_commands
    
    def print_statistics(self):
        """Print statistics about parsed commands"""
        print("\nCommand Statistics:")
        print("-" * 50)
        print(f"Total parsed command sequences: {sum(self.commands_found.values())}")
        print(f"Unique command types: {len(self.commands_found)}")
        print(f"Unknown command sequences: {len(self.unknown_commands)}")
        
        if self.commands_found:
            print("\nCommand Frequency:")
            print("-" * 50)
            sorted_cmds = sorted(self.commands_found.items(), key=lambda x: x[1], reverse=True)
            for cmd, count in sorted_cmds:
                cmd_hex = cmd.hex()
                description = ESCP_COMMANDS.get(cmd, "Unknown")
                print(f"{cmd_hex:<10} : {count:<5} : {description}")
        
        if self.unknown_commands:
            print("\nUnknown Commands (first 10):")
            print("-" * 50)
            for i, cmd in enumerate(list(self.unknown_commands)[:10]):
                print(f"{i+1}. {cmd.hex()}")
    
    def save_parsed_data(self, output_filename):
        """Save parsed data to a JSON file"""
        if not self.parsed_data:
            print("No parsed data to save")
            return False
        
        try:
            output_data = {
                "statistics": {
                    "total_commands": sum(self.commands_found.values()),
                    "unique_commands": len(self.commands_found),
                    "unknown_commands": len(self.unknown_commands),
                    "command_frequency": {cmd.hex(): count for cmd, count in self.commands_found.items()}
                },
                "unknown_commands": [cmd.hex() for cmd in self.unknown_commands],
                "parsed_data": self.parsed_data
            }
            
            with open(output_filename, 'w') as f:
                json.dump(output_data, f, indent=2)
                
            print(f"Parsed data saved to {output_filename}")
            return True
            
        except Exception as e:
            print(f"Error saving parsed data: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="ESC/P Command Parser for DTG Printer Analysis")
    parser.add_argument("input_file", help="Input file (JSON capture or PCAP file)")
    parser.add_argument("-o", "--output", help="Output JSON file for parsed commands")
    parser.add_argument("-p", "--pcap", action="store_true", help="Input is a PCAP file (requires pyshark)")
    args = parser.parse_args()
    
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1
    
    escp_parser = ESCPParser()
    
    if args.pcap:
        success = escp_parser.parse_pcap(args.input_file)
    else:
        success = escp_parser.parse_file(args.input_file)
    
    if not success:
        return 1
    
    escp_parser.print_statistics()
    
    if args.output:
        escp_parser.save_parsed_data(args.output)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 