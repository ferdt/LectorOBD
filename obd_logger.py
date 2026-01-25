"""
OBD-II Data Logger Core Module

This module handles the connection to ELM327 OBD-II adapters,
PID data collection, and CSV logging functionality.
"""

import obd
import csv
import time
from datetime import datetime
from typing import List, Optional, Dict
import os


class OBDLogger:
    """Main OBD-II data logger class for ELM327 adapters."""
    
    def __init__(self):
        """Initialize the OBD logger."""
        self.connection: Optional[obd.OBD] = None
        self.selected_pids: List[obd.OBDCommand] = []
        self.is_logging: bool = False
        self.log_file: Optional[str] = None
        self.csv_writer: Optional[csv.DictWriter] = None
        self.csv_file_handle = None
        
    def connect(self, port: Optional[str] = None, baudrate: Optional[int] = None) -> bool:
        """
        Connect to the ELM327 OBD-II adapter.
        
        Args:
            port: Serial port (e.g., 'COM3'). If None, auto-detect.
            baudrate: Baud rate for connection. If None, use default.
            
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            print(f"Attempting to connect to ELM327...")
            if port:
                print(f"Using specified port: {port}")
                if baudrate:
                    self.connection = obd.OBD(portstr=port, baudrate=baudrate)
                else:
                    self.connection = obd.OBD(portstr=port)
            else:
                print("Auto-detecting OBD-II adapter...")
                self.connection = obd.OBD()
            
            if self.connection.status() == obd.OBDStatus.CAR_CONNECTED:
                print(f"✓ Successfully connected to vehicle via {self.connection.port_name()}")
                return True
            else:
                print(f"✗ Connection failed. Status: {self.connection.status()}")
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
        return sorted(all_commands, key=lambda x: x.name)
    
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
                cmd = obd.commands.has_name(pid_name)
                if cmd:
                    self.selected_pids.append(cmd)
                else:
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
        cmd = obd.commands.has_name(pid_name)
        if cmd:
            if cmd not in self.selected_pids:
                self.selected_pids.append(cmd)
                return True
            else:
                print(f"PID {pid_name} already selected")
                return False
        else:
            print(f"PID {pid_name} not found")
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
        
        # Generate log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"obd_log_{timestamp}.csv"
        
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
