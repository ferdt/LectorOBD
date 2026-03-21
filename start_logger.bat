@echo off
title OBD-II Auto Logger
echo ==============================================
echo        OBD-II Data Logger Auto-Start
echo ==============================================
echo.

:: Modify this command to match your preferred configuration.
::
:: Arguments:
:: pids_example.txt   : The file containing the list of PIDs you actually want to log
:: -c custom_pids.txt : Loads your custom manufacturer-specific PID definitions
:: -r                 : Automatically connects and starts logging!
:: -i 1.0             : Logs data every 1.0 seconds
::
:: Note: Press Ctrl+C while logging to stop and save the CSV file cleanly.

python main.py pids_log_boost.txt -c pid_database\PID_JTD.txt -p COM10 -r -e -i 1.0

echo.
pause
