#!/usr/bin/env python
"""
InkCraft RIP USB Analysis Runner

This script provides a convenient way to run the complete USB analysis workflow
for reverse engineering Epson DTG printer protocols.

It performs USB capture, ESC/P command parsing, and provides interactive testing.
"""

import os
import sys
import argparse
import subprocess
import time
from datetime import datetime

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import usb.core
    except ImportError:
        print("Error: PyUSB library not found.")
        print("Please install it using: pip install -r requirements.txt")
        return False
        
    return True

def run_capture(duration, output_dir=None):
    """Run the USB capture tool"""
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Build the command
        cmd = [sys.executable, "tools/usb_capture.py", "-d", str(duration)]
        
        print(f"Starting USB capture for {duration} seconds...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait for completion
        stdout, stderr = process.communicate()
        
        print(stdout)
        if stderr:
            print(f"Errors during capture: {stderr}")
            
        # Look for the output file in the stdout
        capture_file = None
        for line in stdout.split('\n'):
            if "Capture data saved to" in line:
                capture_file = line.split("to ")[-1].strip()
                break
                
        if capture_file and output_dir:
            # Move to output directory if specified
            new_path = os.path.join(output_dir, os.path.basename(capture_file))
            os.rename(capture_file, new_path)
            capture_file = new_path
            
        return capture_file
            
    except Exception as e:
        print(f"Error running capture: {e}")
        return None

def run_parser(input_file, output_dir=None):
    """Run the ESC/P parser tool on the captured data"""
    if not input_file or not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return None
        
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Generate output filename
    output_file = os.path.splitext(os.path.basename(input_file))[0] + "_parsed.json"
    if output_dir:
        output_file = os.path.join(output_dir, output_file)
        
    try:
        # Build the command
        cmd = [sys.executable, "tools/escp_parser.py", input_file, "-o", output_file]
        
        print(f"Parsing captured data from {input_file}...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait for completion
        stdout, stderr = process.communicate()
        
        print(stdout)
        if stderr:
            print(f"Errors during parsing: {stderr}")
            
        if os.path.exists(output_file):
            return output_file
        else:
            return None
            
    except Exception as e:
        print(f"Error running parser: {e}")
        return None

def run_interactive_mode():
    """Run the printer commander in interactive mode"""
    try:
        # Build the command
        cmd = [sys.executable, "tools/printer_commander.py", "--init", "--interactive"]
        
        print("Starting interactive printer command mode...")
        print("(This will initialize the printer and allow testing commands)")
        
        # Run interactively with direct I/O
        process = subprocess.run(cmd)
        
        return process.returncode == 0
            
    except Exception as e:
        print(f"Error running interactive mode: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="InkCraft RIP USB Analysis Runner")
    parser.add_argument("--capture", action="store_true", help="Run USB capture")
    parser.add_argument("--parse", action="store_true", help="Run ESC/P parser")
    parser.add_argument("--interactive", action="store_true", help="Run interactive command mode")
    parser.add_argument("--all", action="store_true", help="Run full analysis workflow (capture, parse, interactive)")
    parser.add_argument("--duration", type=int, default=120, help="Duration for USB capture in seconds")
    parser.add_argument("--input-file", help="Input file for parsing (if not using capture)")
    parser.add_argument("--output-dir", help="Directory to save output files")
    
    args = parser.parse_args()
    
    # Default to --all if no specific actions selected
    if not (args.capture or args.parse or args.interactive):
        args.all = True
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Create output directory if specified
    if args.output_dir and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Run the selected actions
    capture_file = None
    parsed_file = None
    
    # Capture
    if args.all or args.capture:
        capture_file = run_capture(args.duration, args.output_dir)
        if not capture_file and args.all:
            print("USB capture failed, but continuing with next steps...")
    
    # Parse
    if args.all or args.parse:
        input_file = args.input_file if args.input_file else capture_file
        if input_file:
            parsed_file = run_parser(input_file, args.output_dir)
        else:
            print("No input file for parsing")
    
    # Interactive
    if args.all or args.interactive:
        run_interactive_mode()
    
    # Summary
    print("\nAnalysis Summary:")
    print(f"Capture file: {capture_file or 'Not created or specified'}")
    print(f"Parsed file: {parsed_file or 'Not created'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 