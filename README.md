# OBD-II Data Logger

A Python application to log PID (Parameter ID) data from a car's OBD-II port using an ELM327 Bluetooth adapter.

## Features

- 🔌 **Easy Connection**: Auto-detect or manually select your ELM327 Bluetooth adapter
- 📋 **Flexible PID Selection**: 
  - Load PIDs from a text file
  - Interactive selection from available/standard PIDs
  - Toggle PIDs on/off easily
  - Support for custom manufacturer-specific PIDs
- 📊 **Real-time Logging**: Log data to CSV files with customizable intervals
- 💾 **CSV Export**: Timestamped data files for easy analysis
- 🖥️ **User-friendly CLI**: Simple menu-driven interface

## Requirements

- Python 3.7 or higher
- ELM327 Bluetooth OBD-II adapter
- Vehicle with OBD-II port (most cars manufactured after 1996)

## Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   cd c:\repo\LectorOBD
   pip install -r requirements.txt
   ```

## Setup - Pairing ELM327 (Windows)

Before running the application, you need to pair your ELM327 adapter via Windows Bluetooth:

1. **Turn on vehicle ignition** (engine can be off, but ignition must be ON)
2. **Plug in ELM327** to the OBD-II port (usually under the dashboard)
3. **Open Windows Bluetooth Settings**:
   - Settings → Devices → Bluetooth & other devices
   - Turn on Bluetooth if not already enabled
   - Click "Add Bluetooth or other device"
   - Select "Bluetooth"
4. **Find and pair ELM327**:
   - Look for device named "OBDII", "ELM327", "OBD-II", or similar
   - Click on it to pair
   - Default PIN is usually `1234` or `0000`
5. **Note the COM port**:
   - After pairing, go to Device Manager → Ports (COM & LPT)
   - Find your ELM327 device (e.g., "Standard Serial over Bluetooth link")
   - Note the COM port number (e.g., COM3, COM4)

## Usage

### Starting the Application

```bash
python main.py
```

### Basic Workflow

1. **Connect to ELM327**:
   - Select option 1 from the main menu
   - Choose auto-detect or enter your COM port manually

2. **Select PIDs to Log**:
   - Select option 3 from the main menu
   - Either:
     - Load from a file (option 1) - see `pids_example.txt` for format
     - Interactive selection (option 2) - browse and select PIDs

3. **Start Logging**:
   - Select option 5 from the main menu
   - Choose log interval (how often to record data)
   - Watch real-time data appear on screen
   - Press Ctrl+C to stop logging

4. **Find Your Data**:
   - CSV files are saved as `Logs/obd_log_YYYYMMDD_HHMMSS.csv`
   - Located in the `Logs` subdirectory

### Creating a PID List File

Create a text file (e.g., `my_pids.txt`) with one PID name per line:

```
SPEED
RPM
COOLANT_TEMP
ENGINE_LOAD
THROTTLE_POS
INTAKE_TEMP
MAF
```

Comments (lines starting with `#`) are ignored.

### Common PIDs

Here are some commonly used PIDs:

- `SPEED` - Vehicle speed
- `RPM` - Engine RPM
- `COOLANT_TEMP` - Engine coolant temperature
- `ENGINE_LOAD` - Calculated engine load
- `THROTTLE_POS` - Throttle position
- `INTAKE_TEMP` - Intake air temperature
- `MAF` - Mass air flow rate
- `FUEL_PRESSURE` - Fuel pressure
- `SHORT_FUEL_TRIM_1` - Short term fuel trim
- `LONG_FUEL_TRIM_1` - Long term fuel trim
- `O2_B1S1` - O2 sensor bank 1 sensor 1
- `TIMING_ADVANCE` - Timing advance
- `INTAKE_PRESSURE` - Intake manifold pressure
- `FUEL_LEVEL` - Fuel level
- `BAROMETRIC_PRESSURE` - Barometric pressure

### Custom (Manufacturer-Specific) PIDs

In addition to standard OBD-II PIDs, the application supports custom manufacturer-specific PIDs through the `PID_database/custom_pids.txt` configuration file.

**Loading Custom PIDs**:
1. Select option 3 (Select PIDs) from main menu
2. Select option 6 (Load custom PIDs)
3. Enter filename or press Enter for default (`PID_database/custom_pids.txt`)

**Included Custom PIDs** (in `PID_database/custom_pids.txt`):
- `DPF_TEMPERATURE` - Diesel Particulate Filter temperature (°C)
- `DPF_CLOGGING_LEVEL` - DPF clogging level (%)
- `DPF_PRESSURE` - DPF pressure (kPa)
- `OIL_TEMPERATURE` - Engine oil temperature (°C)
- `EGR_POSITION` - EGR valve position (%)
- `BOOST_PRESSURE` - Turbo boost pressure (kPa)
- `FUEL_PRESSURE` - Fuel rail pressure (kPa)
- `ENGINE_OIL_LIGHT` - Engine oil light status

**Creating Your Own Custom PIDs**:

Edit `PID_database/custom_pids.txt` using this format:
```
NAME|PID_CODE|EQUATION|DESCRIPTION
```

Examples:
```
DPF_TEMPERATURE|221167|(A*256+B)/10-273.15|DPF Temperature (°C)
OIL_TEMPERATURE|221310|A-40|Oil Temperature (°C)
```

Where:
- `NAME`: Identifier (use underscores, no spaces)
- `PID_CODE`: Hexadecimal PID command
- `EQUATION`: Decoding formula (A = byte 1, B = byte 2)
- `DESCRIPTION`: Human-readable description

Common equation patterns:
- Single byte: `A`, `A-40`, `A/2.55`
- Two bytes: `(A*256+B)/10`, `(A*256+B)/100`, `(A*256+B)/10-273.15`

**Note**: Not all PIDs are supported by all vehicles. Use the interactive selection after connecting to see which PIDs your vehicle supports.

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to ELM327

**Solutions**:
- Ensure ELM327 is paired via Windows Bluetooth settings
- Verify vehicle ignition is ON
- Check the correct COM port in Device Manager
- Try disconnecting and reconnecting the ELM327
- Restart Bluetooth on your computer
- Try a different USB Bluetooth adapter if using one

### No PIDs Available

**Problem**: No PIDs show up when trying to select

**Solutions**:
- Make sure you're connected to the vehicle first
- Verify vehicle ignition is ON (not just accessories)
- Some vehicles may take a moment to initialize - try reconnecting
- Use the standard PID list (shows even when not connected)

### Data Shows "N/A"

**Problem**: Some PIDs return "N/A" during logging

**Solutions**:
- The PID may not be supported by your vehicle
- Use interactive selection to choose only supported PIDs
- Check vehicle manual for OBD-II compatibility

### Slow Logging

**Problem**: Logging is slower than expected interval

**Solutions**:
- Reduce the number of selected PIDs
- Increase the log interval
- Some PIDs respond slower than others
- ELM327 Bluetooth has bandwidth limitations

## Project Structure

```
LectorOBD/
├── main.py              # Main application entry point with CLI
├── obd_logger.py        # Core OBD logging functionality
├── requirements.txt     # Python dependencies
├── pids_example.txt     # Example PID configuration file
├── PID_database/        # PID configuration folder
│   └── custom_pids.txt  # Custom manufacturer-specific PIDs
├── README.md           # This file
└── Logs/               # Generated log files directory
    └── obd_log_*.csv   # Timestamped CSV log files
```

## CSV Output Format

Log files are saved as CSV with the following structure:

```csv
Timestamp,SPEED,RPM,COOLANT_TEMP
2026-01-24 10:30:15.123,45.5,2100,85
2026-01-24 10:30:16.124,46.2,2150,85
...
```

- **Timestamp**: Date and time with milliseconds
- **PID Columns**: One column per selected PID
- **Values**: Numeric values (units depend on PID)

## Technical Details

- **Library**: Uses `python-obd` for ELM327 communication
- **Protocol**: Supports all ELM327 protocols (automatically detected)
- **Connection**: Serial over Bluetooth (RFCOMM)
- **Data Format**: CSV for easy import into Excel, Python pandas, etc.

## License

This project is open source and available for personal and educational use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Acknowledgments

- Built with [python-obd](https://python-obd.readthedocs.io/) library
- Supports standard ELM327 OBD-II adapters

---

**Happy Logging! 🚗📊**
