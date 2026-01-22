#!/bin/sh

# This script has two optional arguments. 
# The first argument will kill a specified PID. You can also pass in -1 to skip this argument.
# The second argument is the program to start. If none is specified, the default below will run.

cd /home/dorna/cleaning_fixture

# Optional argument to kill a PID
arg1=${1:-"-1"}
# Optional argument to specify a program to start
arg2=${2:-"subproc.py"}
# Debugging toggle
Debug=1

if [ $arg1 = "START" ]; then
    sleep 10
    if [ Debug ]; then
        echo "screen_cleaning_start.sh sucessfully ran on boot at $(date)" > Startup_log.txt
    fi
    arg1="-1"
fi

# If an argument was provided, kill that PID
if [ $arg1 -ne "-1" ]; then
    sudo kill -9 ${arg1}
    if [ Debug ]; then
        echo "Killed: $arg1"
    fi
fi

# Start new programs
python3 ${arg2}
if [ Debug ]; then
    echo "Started $arg2"
fi