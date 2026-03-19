"""
OBD-II Data Logger Core Module

This module handles the connection to ELM327 OBD-II adapters,
PID data collection, and CSV logging functionality.
"""

import obd
from obd import OBDCommand, Unit
from obd.protocols import ECU
import csv
import time
from datetime import datetime
from typing import List, Optional, Dict
import os
import serial.tools.list_ports


class OBDLogger:
    """Main OBD-II data logger class for ELM327 adapters."""
    
    def __init__(self):
        """Initialize the OBD logger."""
        self.connection: Optional[obd.OBD] = None
        self.selected_pids: List[obd.OBDCommand] = []
        self.custom_commands: Dict[str, obd.OBDCommand] = {}  # Store custom PIDs
        self.is_logging: bool = False
        self.log_file: Optional[str] = None
        self.csv_writer: Optional[csv.DictWriter] = None
        self.csv_file_handle = None
        
    @staticmethod
    def get_available_ports() -> List[Dict[str, str]]:
        """
        Get a list of available serial ports.
        
        Returns:
            List of dictionaries containing port 'device' and 'description'.
        """
        ports = []
        for p in serial.tools.list_ports.comports():
            # Include standard bluetooth serial ports commonly used by ELM327
            ports.append({
                'device': p.device,
                'description': p.description
            })
        return ports

    def connect(self, port: Optional[str] = None, baudrate: Optional[int] = None, retries: int = 2) -> bool:
        """
        Connect to the ELM327 OBD-II adapter.
        
        Args:
            port: Serial port (e.g., 'COM3'). If None, auto-detect.
            baudrate: Baud rate for connection. If None, try common baudrates.
            retries: Number of connection attempts to make.
            
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            print(f"Attempting to connect to ELM327...")
            
            # Common ELM327 baudrates to try if auto-baudrate fails
            baudrates_to_try = [baudrate] if baudrate else [None, 38400, 115200, 9600]
            
            for attempt in range(1, retries + 1):
                if attempt > 1:
                    print(f"Retry attempt {attempt}/{retries}...")
                    time.sleep(1)
                    
                for baud in baudrates_to_try:
                    baud_str = f" at {baud} baud" if baud else " with auto-baudrate"
                    
                    if port:
                        print(f"Trying port: {port}{baud_str}")
                        if baud:
                            self.connection = obd.OBD(portstr=port, baudrate=baud, fast=False)
                        else:
                            self.connection = obd.OBD(portstr=port, fast=False)
                    else:
                        print(f"Auto-detecting OBD-II adapter{baud_str}...")
                        if baud:
                            self.connection = obd.OBD(baudrate=baud, fast=False)
                        else:
                            self.connection = obd.OBD(fast=False)
                    
                    if self.connection.status() == obd.OBDStatus.CAR_CONNECTED:
                        print(f"✓ Successfully connected to vehicle via {self.connection.port_name()}")
                        return True
                    else:
                        if self.connection:
                            self.connection.close()
                            self.connection = None
                            
            print(f"✗ Connection failed after {retries} attempts.")
            print("  Make sure:")
            print("  1. ELM327 is paired via Bluetooth")
            print("  2. Vehicle ignition is ON")
            print("  3. Correct COM port is selected")
            return False
                
        except Exception as e:
            print(f"✗ Error connecting to OBD-II adapter: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the OBD-II adapter."""
        if self.connection:
            self.connection.close()
            print("Disconnected from OBD-II adapter")
            self.connection = None
    
    def is_connected(self) -> bool:
        """Check if connected to OBD-II adapter."""
        return self.connection is not None and self.connection.status() == obd.OBDStatus.CAR_CONNECTED
    
    def get_available_pids(self) -> List[obd.OBDCommand]:
        """
        Get list of PIDs supported by the connected vehicle.
        
        Returns:
            List of supported OBD commands.
        """
        if not self.is_connected():
            print("Not connected to vehicle")
            return []
        
        try:
            # Get all supported commands
            supported = self.connection.supported_commands
            # Filter out non-data commands (like protocol, status commands)
            data_commands = [cmd for cmd in supported if cmd.name not in 
                           ['ELM_VERSION', 'ELM_VOLTAGE', 'STATUS', 'FREEZE_DTC']]
            return sorted(data_commands, key=lambda x: x.name)
        except Exception as e:
            print(f"Error getting supported PIDs: {e}")
            return []
    
    def get_all_standard_pids(self) -> List[obd.OBDCommand]:
        """
        Get all standard OBD-II PIDs (whether supported or not).
        
        Returns:
            List of all standard OBD commands.
        """
        # Get all commands from the obd library
        all_commands = []
        for cmd in obd.commands[1]:  # Mode 1 commands (current data)
            if cmd.name not in ['ELM_VERSION', 'ELM_VOLTAGE', 'STATUS', 'FREEZE_DTC']:
                all_commands.append(cmd)
        
        # Add custom commands
        all_commands.extend(self.custom_commands.values())
        
        return sorted(all_commands, key=lambda x: x.name)
    
    def _create_custom_decoder(self, equation: str, num_bytes: int):
        """
        Create a decoder function from an equation string.
        
        Args:
            equation: Equation string (e.g., "(A*256+B)/10-273.15")
            num_bytes: Number of bytes expected in response
            
        Returns:
            Decoder function compatible with python-OBD
        """
        def decoder(messages):
            """Decode the OBD response using the custom equation."""
            if not messages:
                return None
            
            # Get the data bytes from the message
            data = messages[0].data
            
            # Skip the first 2 bytes (mode and PID echo)
            if len(data) < 2 + num_bytes:
                return None
            
            # Extract byte values
            if num_bytes >= 1:
                A = data[2]
            if num_bytes >= 2:
                B = data[3] if len(data) > 3 else 0
            
            try:
                # Evaluate the equation
                result = eval(equation)
                return result
            except Exception as e:
                print(f"Error evaluating equation '{equation}': {e}")
                return None
        
        return decoder
    
    def register_custom_pid(self, name: str, pid_code: str, equation: str, description: str) -> bool:
        """
        Register a custom PID with specific decoding equation.
        
        Args:
            name: PID name (e.g., "DPF_TEMPERATURE")
            pid_code: Hexadecimal PID code (e.g., "221167")
            equation: Decoding equation (e.g., "(A*256+B)/10-273.15")
            description: Human-readable description
            
        Returns:
            True if registration successful, False otherwise.
        """
        try:
            # Determine number of bytes needed based on equation
            num_bytes = 2 if 'B' in equation else 1
            
            # Create the custom command
            custom_cmd = OBDCommand(
                name=name,
                desc=description,
                command=bytes.fromhex(pid_code),
                _bytes=num_bytes,
                decoder=self._create_custom_decoder(equation, num_bytes),
                ecu=ECU.ALL,
                fast=False
            )
            
            # Store the custom command
            self.custom_commands[name] = custom_cmd
            
            # Register it with the OBD library if connected
            if self.connection:
                self.connection.supported_commands.add(custom_cmd)
            
            print(f"[OK] Registered custom PID: {name}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error registering custom PID '{name}': {e}")
            return False
    
    def load_custom_pids_from_file(self, filename: str = "custom_pids.txt") -> bool:
        """
        Load custom PIDs from a configuration file.
        
        File format (pipe-delimited):
        NAME|PID_CODE|EQUATION|DESCRIPTION
        
        Args:
            filename: Path to custom PIDs configuration file
            
        Returns:
            True if PIDs loaded successfully, False otherwise.
        """
        if not os.path.exists(filename):
            print(f"[INFO] Custom PIDs file not found: {filename}")
            return False
        
        try:
            loaded_count = 0
            failed_pids = []
            
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse the line
                    parts = line.split('|')
                    if len(parts) != 4:
                        print(f"[WARN] Line {line_num}: Invalid format (expected 4 fields)")
                        failed_pids.append(f"Line {line_num}")
                        continue
                    
                    name, pid_code, equation, description = [p.strip() for p in parts]
                    
                    # Register the custom PID
                    if self.register_custom_pid(name, pid_code, equation, description):
                        loaded_count += 1
                    else:
                        failed_pids.append(name)
            
            if loaded_count > 0:
                print(f"[OK] Loaded {loaded_count} custom PID(s) from {filename}")
                if failed_pids:
                    print(f"  Warning: {len(failed_pids)} PID(s) failed to load")
                return True
            else:
                print(f"[ERROR] No valid custom PIDs loaded from {filename}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error loading custom PIDs from file: {e}")
            return False
    
    def load_pids_from_file(self, filename: str) -> bool:
        """
        Load PIDs from a text file.
        
        Args:
            filename: Path to text file containing PID names (one per line).
            
        Returns:
            True if PIDs loaded successfully, False otherwise.
        """
        if not os.path.exists(filename):
            print(f"✗ File not found: {filename}")
            return False
        
        try:
            with open(filename, 'r') as f:
                pid_names = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not pid_names:
                print("✗ No PIDs found in file")
                return False
            
            self.selected_pids = []
            failed_pids = []
            
            for pid_name in pid_names:
                # Try to find the command
                try:
                    cmd = obd.commands[pid_name]
                    self.selected_pids.append(cmd)
                except KeyError:
                    failed_pids.append(pid_name)
            
            if self.selected_pids:
                print(f"✓ Loaded {len(self.selected_pids)} PIDs from {filename}")
                if failed_pids:
                    print(f"  Warning: {len(failed_pids)} PIDs not recognized: {', '.join(failed_pids)}")
                return True
            else:
                print(f"✗ No valid PIDs found in file")
                return False
                
        except Exception as e:
            print(f"✗ Error loading PIDs from file: {e}")
            return False
    
    def add_pid(self, pid_name: str) -> bool:
        """
        Add a PID to the selected list by name.
        
        Args:
            pid_name: Name of the PID to add.
            
        Returns:
            True if PID added successfully, False otherwise.
        """
        # Try standard commands first
        try:
            cmd = obd.commands[pid_name]
        except KeyError:
            # Try custom commands
            cmd = self.custom_commands.get(pid_name)
            if not cmd:
                print(f"PID {pid_name} not found")
                return False
        
        if cmd not in self.selected_pids:
            self.selected_pids.append(cmd)
            return True
        else:
            print(f"PID {pid_name} already selected")
            return False
    
    def remove_pid(self, pid_name: str) -> bool:
        """
        Remove a PID from the selected list.
        
        Args:
            pid_name: Name of the PID to remove.
            
        Returns:
            True if PID removed successfully, False otherwise.
        """
        for cmd in self.selected_pids:
            if cmd.name == pid_name:
                self.selected_pids.remove(cmd)
                return True
        return False
    
    def clear_selected_pids(self):
        """Clear all selected PIDs."""
        self.selected_pids = []
        print("Cleared all selected PIDs")
    
    def get_selected_pids(self) -> List[str]:
        """
        Get list of currently selected PID names.
        
        Returns:
            List of selected PID names.
        """
        return [cmd.name for cmd in self.selected_pids]
    
    def save_available_pids_to_file(self, filename: str, use_vehicle_supported: bool = True) -> bool:
        """
        Save list of available PIDs to a text file.
        
        Args:
            filename: Path to output file.
            use_vehicle_supported: If True and connected, use vehicle-supported PIDs.
                                 If False or not connected, use all standard PIDs.
        
        Returns:
            True if PIDs saved successfully, False otherwise.
        """
        try:
            # Determine which PID list to use
            if use_vehicle_supported and self.is_connected():
                pids = self.get_available_pids()
                source = "vehicle-supported"
            else:
                pids = self.get_all_standard_pids()
                source = "standard"
            
            if not pids:
                print("✗ No PIDs available to save")
                return False
            
            # Write PIDs to file
            with open(filename, 'w') as f:
                f.write(f"# OBD-II PIDs ({source})\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total PIDs: {len(pids)}\n")
                f.write("#\n")
                f.write("# Format: PID_NAME - Description\n")
                f.write("#" + "=" * 70 + "\n\n")
                
                for cmd in pids:
                    desc = cmd.desc if hasattr(cmd, 'desc') and cmd.desc else "No description"
                    f.write(f"{cmd.name:30s} - {desc}\n")
            
            print(f"✓ Saved {len(pids)} {source} PIDs to {filename}")
            return True
            
        except Exception as e:
            print(f"✗ Error saving PIDs to file: {e}")
            return False
    
    def save_selected_pids_to_file(self, filename: str) -> bool:
        """
        Save currently selected PIDs to a text file.
        This file can be loaded back using load_pids_from_file().
        
        Args:
            filename: Path to output file.
        
        Returns:
            True if PIDs saved successfully, False otherwise.
        """
        if not self.selected_pids:
            print("✗ No PIDs selected to save")
            return False
        
        try:
            with open(filename, 'w') as f:
                f.write(f"# Selected OBD-II PIDs\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total PIDs: {len(self.selected_pids)}\n")
                f.write("#\n")
                f.write("# This file can be loaded using 'Load PIDs from file' option\n")
                f.write("#" + "=" * 70 + "\n\n")
                
                for cmd in self.selected_pids:
                    f.write(f"{cmd.name}\n")
            
            print(f"✓ Saved {len(self.selected_pids)} selected PIDs to {filename}")
            return True
            
        except Exception as e:
            print(f"✗ Error saving selected PIDs to file: {e}")
            return False
    
    def start_logging(self, log_interval: float = 1.0) -> bool:
        """
        Start logging OBD data to CSV file.
        
        Args:
            log_interval: Time interval between log entries in seconds.
            
        Returns:
            True if logging started successfully, False otherwise.
        """
        if not self.is_connected():
            print("✗ Cannot start logging: Not connected to vehicle")
            return False
        
        if not self.selected_pids:
            print("✗ Cannot start logging: No PIDs selected")
            return False
        
        # Create Logs directory if it doesn't exist
        logs_dir = "Logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Generate log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(logs_dir, f"obd_log_{timestamp}.csv")
        
        try:
            # Open CSV file for writing
            self.csv_file_handle = open(self.log_file, 'w', newline='')
            
            # Create CSV writer with fieldnames
            fieldnames = ['Timestamp'] + [cmd.name for cmd in self.selected_pids]
            self.csv_writer = csv.DictWriter(self.csv_file_handle, fieldnames=fieldnames)
            self.csv_writer.writeheader()
            
            self.is_logging = True
            print(f"✓ Started logging to {self.log_file}")
            print(f"  Logging {len(self.selected_pids)} PIDs every {log_interval}s")
            print("  Press Ctrl+C or select 'Stop Logging' from menu to stop")
            
            return True
            
        except Exception as e:
            print(f"✗ Error starting logging: {e}")
            if self.csv_file_handle:
                self.csv_file_handle.close()
            return False
    
    def log_data_point(self) -> Optional[Dict[str, any]]:
        """
        Query all selected PIDs and log a single data point.
        
        Returns:
            Dictionary of logged data, or None if error.
        """
        if not self.is_logging:
            return None
        
        if not self.is_connected():
            print("✗ Connection lost")
            self.stop_logging()
            return None
        
        try:
            # Build data row
            row = {'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}
            
            # Query each PID
            for cmd in self.selected_pids:
                response = self.connection.query(cmd)
                if response.value is not None:
                    # Convert to string, handling units
                    if hasattr(response.value, 'magnitude'):
                        # Pint quantity object
                        row[cmd.name] = f"{response.value.magnitude}"
                    else:
                        row[cmd.name] = str(response.value)
                else:
                    row[cmd.name] = "N/A"
            
            # Write to CSV
            self.csv_writer.writerow(row)
            self.csv_file_handle.flush()  # Ensure data is written immediately
            
            return row
            
        except Exception as e:
            print(f"\n✗ Error logging data: {e}")
            self.stop_logging()
            return None
    
    def stop_logging(self):
        """Stop logging and close the CSV file."""
        if self.is_logging:
            self.is_logging = False
            if self.csv_file_handle:
                self.csv_file_handle.close()
                self.csv_file_handle = None
            print(f"\n✓ Logging stopped. Data saved to {self.log_file}")
            self.log_file = None
            self.csv_writer = None
    
    def get_status(self) -> str:
        """
        Get current logger status.
        
        Returns:
            Status string.
        """
        if not self.connection:
            return "Not connected"
        
        status = f"Connected via {self.connection.port_name()}"
        if self.is_logging:
            status += f" | Logging to {self.log_file}"
        
        return status
