"""
OBD-II Data Logger - Main CLI Interface

A Python application to log PID data from OBD-II port via ELM327 Bluetooth adapter.
"""

import sys
import time
import os
from obd_logger import OBDLogger
import obd


def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print application header."""
    print("=" * 60)
    print("        OBD-II Data Logger - ELM327 Bluetooth")
    print("=" * 60)
    print()


def print_menu():
    """Print main menu."""
    print("\n" + "-" * 60)
    print("MAIN MENU")
    print("-" * 60)
    print("1. Connect to ELM327")
    print("2. Disconnect")
    print("3. Select PIDs")
    print("4. Show Selected PIDs")
    print("5. Start Logging")
    print("6. Stop Logging")
    print("7. Show Status")
    print("8. Exit")
    print("-" * 60)


def connect_menu(logger: OBDLogger):
    """Handle connection menu."""
    print("\n" + "-" * 60)
    print("CONNECTION OPTIONS")
    print("-" * 60)
    print("1. Auto-detect (recommended)")
    print("2. Manual COM port selection")
    print("3. Back to main menu")
    print("-" * 60)
    
    choice = input("Select option: ").strip()
    
    if choice == '1':
        print("\nAttempting auto-detection...")
        if logger.connect():
            print("\n✓ Connection successful!")
            input("Press Enter to continue...")
        else:
            print("\n✗ Connection failed!")
            print("\nTroubleshooting tips:")
            print("- Make sure ELM327 is paired via Windows Bluetooth settings")
            print("- Turn on vehicle ignition")
            print("- Try manual COM port selection")
            input("\nPress Enter to continue...")
    
    elif choice == '2':
        print("\nAvailable COM ports are typically COM1-COM20 on Windows")
        print("Check Windows Device Manager > Ports (COM & LPT) for your ELM327 port")
        port = input("\nEnter COM port (e.g., COM3): ").strip().upper()
        
        if not port.startswith("COM"):
            print("Invalid port format. Should be like COM3, COM4, etc.")
            input("Press Enter to continue...")
            return
        
        print(f"\nAttempting to connect to {port}...")
        if logger.connect(port=port):
            print("\n✓ Connection successful!")
            input("Press Enter to continue...")
        else:
            print(f"\n✗ Connection to {port} failed!")
            print("\nMake sure:")
            print(f"- {port} is the correct port for your ELM327")
            print("- ELM327 is paired and connected via Bluetooth")
            print("- Vehicle ignition is ON")
            input("\nPress Enter to continue...")


def pid_selection_menu(logger: OBDLogger):
    """Handle PID selection menu."""
    while True:
        print("\n" + "-" * 60)
        print("PID SELECTION MENU")
        print("-" * 60)
        print("1. Load PIDs from file")
        print("2. Interactive PID selection")
        print("3. Clear selected PIDs")
        print("4. List all available PIDs and save to file")
        print("5. Save selected PIDs to file")
        print("6. Back to main menu")
        print("-" * 60)
        
        current = logger.get_selected_pids()
        if current:
            print(f"\nCurrently selected: {len(current)} PID(s)")
        else:
            print("\nNo PIDs currently selected")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            filename = input("\nEnter filename (e.g., pids_example.txt): ").strip()
            if not filename:
                filename = "pids_example.txt"
            
            logger.load_pids_from_file(filename)
            input("\nPress Enter to continue...")
        
        elif choice == '2':
            interactive_pid_selection(logger)
        
        elif choice == '3':
            logger.clear_selected_pids()
            print("✓ All selected PIDs cleared")
            input("\nPress Enter to continue...")
        
        elif choice == '4':
            list_and_save_available_pids(logger)
        
        elif choice == '5':
            save_selected_pids(logger)
        
        elif choice == '6':
            break


def interactive_pid_selection(logger: OBDLogger):
    """Interactive PID selection interface."""
    print("\n" + "-" * 60)
    print("INTERACTIVE PID SELECTION")
    print("-" * 60)
    
    if logger.is_connected():
        print("\nFetching supported PIDs from vehicle...")
        available_pids = logger.get_available_pids()
        if not available_pids:
            print("✗ No PIDs available. Using standard PID list.")
            available_pids = logger.get_all_standard_pids()
    else:
        print("\nNot connected to vehicle. Showing standard PID list.")
        print("(Some PIDs may not be supported by your vehicle)")
        available_pids = logger.get_all_standard_pids()
    
    if not available_pids:
        print("✗ No PIDs available")
        input("\nPress Enter to continue...")
        return
    
    # Show PIDs in pages of 20
    page_size = 20
    page = 0
    max_page = (len(available_pids) - 1) // page_size
    
    while True:
        print("\n" + "-" * 60)
        print(f"Available PIDs (Page {page + 1} of {max_page + 1})")
        print("-" * 60)
        
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(available_pids))
        
        for i, cmd in enumerate(available_pids[start_idx:end_idx], start=start_idx + 1):
            selected = "✓" if cmd.name in logger.get_selected_pids() else " "
            desc = cmd.desc if hasattr(cmd, 'desc') and cmd.desc else "No description"
            print(f"{i:3d}. [{selected}] {cmd.name:25s} - {desc}")
        
        print("\n" + "-" * 60)
        print("Commands: [number] to toggle, [n]ext page, [p]rev page, [d]one")
        print("-" * 60)
        
        choice = input("Enter command: ").strip().lower()
        
        if choice == 'n' and page < max_page:
            page += 1
        elif choice == 'p' and page > 0:
            page -= 1
        elif choice == 'd':
            break
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(available_pids):
                cmd = available_pids[idx]
                if cmd.name in logger.get_selected_pids():
                    logger.remove_pid(cmd.name)
                    print(f"✓ Removed {cmd.name}")
                else:
                    logger.add_pid(cmd.name)
                    print(f"✓ Added {cmd.name}")
            else:
                print("✗ Invalid PID number")


def list_and_save_available_pids(logger: OBDLogger):
    """List all available PIDs and save to a file."""
    print("\n" + "-" * 60)
    print("LIST AND SAVE AVAILABLE PIDs")
    print("-" * 60)
    
    # Determine which PIDs to list
    if logger.is_connected():
        print("\n1. Save vehicle-supported PIDs (recommended)")
        print("2. Save all standard PIDs")
        print("3. Cancel")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '3':
            return
        
        use_vehicle = choice == '1'
    else:
        print("\nNot connected to vehicle.")
        print("Will save all standard PIDs.")
        use_vehicle = False
    
    # Get filename
    default_filename = "available_pids.txt"
    filename = input(f"\nEnter filename (default: {default_filename}): ").strip()
    if not filename:
        filename = default_filename
    
    # Save PIDs to file
    logger.save_available_pids_to_file(filename, use_vehicle_supported=use_vehicle)
    input("\nPress Enter to continue...")


def save_selected_pids(logger: OBDLogger):
    """Save currently selected PIDs to a file."""
    print("\n" + "-" * 60)
    print("SAVE SELECTED PIDs")
    print("-" * 60)
    
    selected = logger.get_selected_pids()
    if not selected:
        print("\n✗ No PIDs selected")
        print("Select some PIDs first using 'Interactive PID selection'")
        input("\nPress Enter to continue...")
        return
    
    print(f"\nCurrently selected: {len(selected)} PID(s)")
    
    # Get filename
    default_filename = "selected_pids.txt"
    filename = input(f"\nEnter filename (default: {default_filename}): ").strip()
    if not filename:
        filename = default_filename
    
    # Save selected PIDs to file
    logger.save_selected_pids_to_file(filename)
    input("\nPress Enter to continue...")


def show_selected_pids(logger: OBDLogger):
    """Display currently selected PIDs."""
    selected = logger.get_selected_pids()
    
    print("\n" + "-" * 60)
    print("SELECTED PIDs")
    print("-" * 60)
    
    if selected:
        print(f"\nTotal: {len(selected)} PID(s)")
        print()
        for i, pid_name in enumerate(selected, 1):
            print(f"{i:3d}. {pid_name}")
    else:
        print("\nNo PIDs selected")
        print("\nUse 'Select PIDs' menu to choose PIDs for logging")
    
    print("-" * 60)
    input("\nPress Enter to continue...")


def start_logging_menu(logger: OBDLogger):
    """Start logging with user-specified interval."""
    if not logger.is_connected():
        print("\n✗ Cannot start logging: Not connected to vehicle")
        input("\nPress Enter to continue...")
        return
    
    if not logger.get_selected_pids():
        print("\n✗ Cannot start logging: No PIDs selected")
        input("\nPress Enter to continue...")
        return
    
    print("\n" + "-" * 60)
    print("START LOGGING")
    print("-" * 60)
    
    interval_input = input("\nLog interval in seconds (default: 1.0): ").strip()
    
    try:
        interval = float(interval_input) if interval_input else 1.0
        if interval <= 0:
            print("✗ Interval must be positive")
            input("\nPress Enter to continue...")
            return
    except ValueError:
        print("✗ Invalid interval value")
        input("\nPress Enter to continue...")
        return
    
    if not logger.start_logging(interval):
        input("\nPress Enter to continue...")
        return
    
    # Real-time logging display
    print("\n" + "=" * 60)
    print("LOGGING IN PROGRESS - Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        while logger.is_logging:
            data = logger.log_data_point()
            
            if data:
                # Display the logged data
                print(f"\n[{data['Timestamp']}]")
                for key, value in data.items():
                    if key != 'Timestamp':
                        print(f"  {key:20s}: {value}")
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\nLogging interrupted by user")
        logger.stop_logging()
    
    except Exception as e:
        print(f"\n✗ Logging error: {e}")
        logger.stop_logging()
    
    input("\nPress Enter to continue...")


def show_status(logger: OBDLogger):
    """Display current logger status."""
    print("\n" + "-" * 60)
    print("SYSTEM STATUS")
    print("-" * 60)
    
    print(f"\nConnection: {logger.get_status()}")
    print(f"Selected PIDs: {len(logger.get_selected_pids())}")
    print(f"Logging: {'Yes' if logger.is_logging else 'No'}")
    
    if logger.is_connected():
        print(f"\nConnected to: {logger.connection.port_name()}")
        print(f"Protocol: {logger.connection.protocol_name()}")
    
    print("-" * 60)
    input("\nPress Enter to continue...")


def main():
    """Main application entry point."""
    logger = OBDLogger()
    
    try:
        while True:
            clear_screen()
            print_header()
            
            # Show quick status
            if logger.is_connected():
                print(f"Status: ✓ Connected | PIDs: {len(logger.get_selected_pids())} | Logging: {'Yes' if logger.is_logging else 'No'}")
            else:
                print("Status: ✗ Not connected")
            
            print_menu()
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '1':
                connect_menu(logger)
            
            elif choice == '2':
                logger.disconnect()
                print("\n✓ Disconnected")
                input("\nPress Enter to continue...")
            
            elif choice == '3':
                pid_selection_menu(logger)
            
            elif choice == '4':
                show_selected_pids(logger)
            
            elif choice == '5':
                if logger.is_logging:
                    print("\n✗ Logging already in progress")
                    input("\nPress Enter to continue...")
                else:
                    start_logging_menu(logger)
            
            elif choice == '6':
                if logger.is_logging:
                    logger.stop_logging()
                    input("\nPress Enter to continue...")
                else:
                    print("\n✗ Not currently logging")
                    input("\nPress Enter to continue...")
            
            elif choice == '7':
                show_status(logger)
            
            elif choice == '8':
                print("\nExiting...")
                if logger.is_logging:
                    logger.stop_logging()
                if logger.is_connected():
                    logger.disconnect()
                print("Goodbye!")
                sys.exit(0)
            
            else:
                print("\n✗ Invalid option")
                input("\nPress Enter to continue...")
    
    except KeyboardInterrupt:
        print("\n\nExiting...")
        if logger.is_logging:
            logger.stop_logging()
        if logger.is_connected():
            logger.disconnect()
        print("Goodbye!")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        if logger.is_logging:
            logger.stop_logging()
        if logger.is_connected():
            logger.disconnect()
        sys.exit(1)


if __name__ == "__main__":
    main()
