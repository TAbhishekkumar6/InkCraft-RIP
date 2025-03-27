#!/usr/bin/env python
"""
InkCraft RIP System Test Suite

This script checks that all components of the InkCraft RIP software are 
working correctly and that your environment is properly set up for 
reverse engineering Epson DTG printer protocols.
"""

import os
import sys
import time
import argparse
import subprocess
import importlib
import platform
from datetime import datetime

# Required Python version
REQUIRED_PYTHON = (3, 8)

# Required dependencies
REQUIRED_PACKAGES = [
    "pyusb",
    "pillow",
    "numpy",
    "matplotlib",
    "pyyaml"
]

# Optional dependencies
OPTIONAL_PACKAGES = [
    "pyshark"
]

class SystemTester:
    """Tests the complete InkCraft RIP system"""
    
    def __init__(self, options=None):
        """Initialize the tester"""
        self.options = options or {}
        self.results = {
            "environment": [],
            "dependencies": [],
            "components": [],
            "connectivity": None,
            "summary": {
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
    
    def run_all_tests(self):
        """Run all system tests"""
        self._print_header("InkCraft RIP System Test Suite")
        
        # Test environment
        self._print_section("Testing Python Environment")
        self.test_python_environment()
        
        # Test dependencies
        self._print_section("Testing Dependencies")
        self.test_dependencies()
        
        # Test components
        self._print_section("Testing System Components")
        self.test_components()
        
        # Test printer connectivity
        if self.options.get('test_printer', True):
            self._print_section("Testing Printer Connectivity")
            self.test_printer_connectivity()
        
        # Print summary
        self._print_summary()
        
        return self.results["summary"]["failed"] == 0
    
    def test_python_environment(self):
        """Test the Python environment"""
        # Check Python version
        py_version = sys.version_info
        version_ok = py_version.major > REQUIRED_PYTHON[0] or (
            py_version.major == REQUIRED_PYTHON[0] and 
            py_version.minor >= REQUIRED_PYTHON[1]
        )
        
        self._add_result("environment", 
                        "Python Version", 
                        f"{py_version.major}.{py_version.minor}.{py_version.micro}",
                        version_ok,
                        f"Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ required")
        
        # Check operating system
        os_name = platform.system()
        os_version = platform.release()
        
        self._add_result("environment", 
                        "Operating System", 
                        f"{os_name} {os_version}",
                        True,  # Not a pass/fail check
                        None)
        
        # Check environment variables
        if os_name == "Windows":
            path_var = os.environ.get("PATH", "")
            # More robust check for Python in PATH on Windows
            python_in_path = False
            for p in path_var.split(";"):
                p = p.strip('"')  # Remove quotes that might be in PATH
                if p and os.path.exists(p):
                    python_exe = os.path.join(p, "python.exe")
                    if os.path.exists(python_exe):
                        python_in_path = True
                        break
            
            self._add_result("environment", 
                           "Python in PATH", 
                           "Yes" if python_in_path else "No",
                           python_in_path,
                           "Python should be in your PATH")
    
    def test_dependencies(self):
        """Test required and optional dependencies"""
        # Check required packages
        for package in REQUIRED_PACKAGES:
            self._check_package(package, required=True)
        
        # Check optional packages
        for package in OPTIONAL_PACKAGES:
            self._check_package(package, required=False)
    
    def _check_package(self, package_name, required=True):
        """Check if a package is installed and its version"""
        try:
            module = importlib.import_module(package_name)
            version = getattr(module, "__version__", "Unknown")
            
            # Special check for pyusb to verify backend availability
            if package_name == "pyusb" or package_name == "usb":
                backend_available = False
                backend_name = "None"
                try:
                    import usb.core
                    import usb.backend.libusb1
                    import usb.backend.libusb0
                    
                    # Check for available backends
                    if usb.backend.libusb1.get_backend():
                        backend_available = True
                        backend_name = "libusb1"
                    elif usb.backend.libusb0.get_backend():
                        backend_available = True
                        backend_name = "libusb0"
                    
                    # Special message for missing backend
                    if not backend_available:
                        self._add_result("dependencies", 
                                      "USB Backend", 
                                      f"Missing (PyUSB installed but no backend available)",
                                      False,
                                      "Install platform-specific USB drivers (libusb)")
                        
                    self._add_result("dependencies", 
                                  "USB Backend", 
                                  f"Available ({backend_name})",
                                  backend_available,
                                  None)
                except Exception as e:
                    self._add_result("dependencies", 
                                  "USB Backend", 
                                  f"Error checking ({str(e)})",
                                  False,
                                  "Error checking USB backend availability")
            
            self._add_result("dependencies", 
                           package_name, 
                           f"Installed (version: {version})",
                           True,
                           None)
                           
        except ImportError:
            status = "Missing" if required else "Not installed (optional)"
            self._add_result("dependencies", 
                           package_name, 
                           status,
                           not required,  # Fail if required, warning if optional
                           f"Required package {package_name} is missing" if required else 
                           f"Optional package {package_name} is not installed")
    
    def test_components(self):
        """Test InkCraft RIP system components"""
        # Check if we're in the project directory
        if not os.path.exists("tools") or not os.path.exists("src"):
            self._add_result("components", 
                           "Project Structure", 
                           "Invalid",
                           False,
                           "Must run from InkCraft RIP project directory")
            return
        
        # Check for key files
        components = [
            ("USB Capture Tool", "tools/usb_capture.py"),
            ("ESC/P Parser", "tools/escp_parser.py"),
            ("Printer Commander", "tools/printer_commander.py"),
            ("Command Dictionary", "tools/command_dictionary.py"),
            ("Connection Test", "tools/connection_test.py"),
            ("Test Pattern Generator", "tools/test_pattern.py"),
            ("DTG Driver", "src/driver/epson_dtg.py")
        ]
        
        for name, path in components:
            exists = os.path.exists(path)
            self._add_result("components", 
                           name, 
                           "Found" if exists else "Missing",
                           exists,
                           f"Component {path} is missing" if not exists else None)
        
        # Check tools are executable
        if platform.system() != "Windows":  # Skip executable check on Windows
            for name, path in components:
                if os.path.exists(path):
                    executable = os.access(path, os.X_OK)
                    if not executable:
                        self._add_result("components", 
                                       f"{name} (Executable)", 
                                       "Not executable",
                                       False,
                                       f"Component {path} is not executable")
    
    def test_printer_connectivity(self):
        """Test connectivity to the printer"""
        try:
            # Build the command to run the connection test
            cmd = [sys.executable, "tools/connection_test.py"]
            
            # Add vendor ID if specified
            if self.options.get('vendor_id'):
                cmd.extend(["--vendor", self.options['vendor_id']])
            
            # Add product ID if specified
            if self.options.get('product_id'):
                cmd.extend(["--product", self.options['product_id']])
            
            # Run the connection test
            print("Running printer connection test...")
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if the test succeeded
            success = process.returncode == 0
            
            # Store results
            self.results["connectivity"] = {
                "success": success,
                "output": process.stdout,
                "error": process.stderr
            }
            
            # Print the output
            print(process.stdout)
            if process.stderr:
                print("Errors:", process.stderr)
            
            return success
            
        except Exception as e:
            print(f"Error running connection test: {e}")
            self.results["connectivity"] = {
                "success": False,
                "output": "",
                "error": str(e)
            }
            return False
    
    def _add_result(self, category, name, value, success, message):
        """Add a test result"""
        result = {
            "name": name,
            "value": value,
            "success": success,
            "message": message
        }
        
        self.results[category].append(result)
        
        # Update summary counters
        if success is False:
            self.results["summary"]["failed"] += 1
        elif success is True:
            self.results["summary"]["passed"] += 1
        else:  # None or other value indicates a warning or info
            self.results["summary"]["warnings"] += 1
        
        # Print the result
        status = "✓ " if success else "✗ "
        details = f": {message}" if message else ""
        
        if success:
            print(f"{status}{name}: {value}{details}")
        else:
            print(f"{status}{name}: {value}{details}")
    
    def _print_header(self, title):
        """Print a header"""
        print("\n" + "=" * 80)
        print(f"{title}".center(80))
        print("=" * 80)
    
    def _print_section(self, title):
        """Print a section header"""
        print("\n" + "-" * 80)
        print(f"{title}")
        print("-" * 80)
    
    def _print_summary(self):
        """Print a summary of the test results"""
        self._print_section("Test Summary")
        
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]
        warnings = self.results["summary"]["warnings"]
        total = passed + failed
        
        if total > 0:
            pass_rate = (passed / total) * 100
        else:
            pass_rate = 0
        
        print(f"Passed: {passed}/{total} tests ({pass_rate:.1f}%)")
        print(f"Failed: {failed}")
        print(f"Warnings/Info: {warnings}")
        
        # Check if there were any issues with USB dependencies
        usb_issues = False
        for result in self.results["dependencies"]:
            if ("pyusb" in result["name"] or "USB Backend" in result["name"]) and not result["success"]:
                usb_issues = True
        
        if usb_issues:
            self._print_usb_help()
        
        if failed == 0:
            print("\n✓ All critical tests passed!")
            
            if not self.results["connectivity"] or not self.results["connectivity"]["success"]:
                print("\n⚠️  Note: Printer connectivity test did not succeed.")
                print("   This is only an issue if you're ready to start reverse engineering.")
                print("   You can still develop and test the software without a printer.")
                
            print("\nNext steps:")
            print("1. Review any warnings above")
            print("2. Try capturing USB traffic with Wireshark and USBPcap")
            print("3. Run the USB analysis script to analyze captured data")
            
        else:
            print("\n✗ Some tests failed. Please address the issues above before continuing.")
    
    def _print_usb_help(self):
        """Print help information for USB dependencies"""
        self._print_section("USB Dependencies Help")
        
        print("USB library issues were detected. Here's how to fix them:")
        print("\n1. Install PyUSB package:")
        print("   pip install pyusb")
        
        print("\n2. Install platform-specific USB drivers:")
        
        if platform.system() == "Windows":
            print("\n   Windows:")
            print("   - Option 1: Install libusb-win32 via Zadig (recommended):")
            print("     a. Download Zadig from https://zadig.akeo.ie/")
            print("     b. Connect your printer")
            print("     c. Run Zadig, select your printer from the dropdown")
            print("     d. Select libusb-win32 driver and click 'Install Driver'")
            print("\n   - Option 2: Install via pip:")
            print("     pip install pyusb[backend-libusb1]")
            
        elif platform.system() == "Darwin":
            print("\n   macOS:")
            print("   - Install libusb using Homebrew:")
            print("     brew install libusb")
            
        else:
            print("\n   Linux:")
            print("   - Install libusb development packages:")
            print("     sudo apt-get install libusb-1.0-0-dev")
            print("   - Add user to the plugdev group for USB access:")
            print("     sudo usermod -a -G plugdev $USER")
            print("     (Log out and back in for this to take effect)")
            
        print("\n3. Test USB library:")
        print("   python -c \"import usb.core; print('USB library works!')\"")
        print("\nIf problems persist, check the PyUSB documentation:")
        print("   https://github.com/pyusb/pyusb")
    
    def save_results(self, filename=None):
        """Save test results to a file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_test_{timestamp}.json"
            
        try:
            import json
            
            # Add system information
            self.results["system_info"] = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "os": f"{platform.system()} {platform.release()}"
            }
            
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
                
            print(f"\nTest results saved to {filename}")
            
        except Exception as e:
            print(f"\nError saving test results: {e}")

def main():
    parser = argparse.ArgumentParser(description="InkCraft RIP System Test Suite")
    parser.add_argument("--skip-printer", action="store_true", 
                      help="Skip printer connectivity tests")
    parser.add_argument("--vendor", help="USB Vendor ID for printer (e.g., 0x04b8)")
    parser.add_argument("--product", help="USB Product ID for printer")
    parser.add_argument("--save", action="store_true", 
                      help="Save test results to a file")
    parser.add_argument("--output", help="Output file for test results")
    
    args = parser.parse_args()
    
    # Set up options
    options = {
        'test_printer': not args.skip_printer
    }
    
    if args.vendor:
        options['vendor_id'] = args.vendor
        
    if args.product:
        options['product_id'] = args.product
    
    # Run tests
    tester = SystemTester(options)
    success = tester.run_all_tests()
    
    # Save results if requested
    if args.save or args.output:
        tester.save_results(args.output)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 