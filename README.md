# Dorna Cleaning Fixture
Uses the dorna arm with additional attachments to run cleaning tests on Rhino T105 Screens

## Table of Contents
- [Usage](#usage)
- [Functionality](#functionality)
- [Warnings](#warnings)


## Usagex
to run the project, navigate to the proper directory:
```
cd cleaning_fixture
```
Once in the directory navigate to the Python folder:
```
cd Python
```
Open the file __positions.json__
coordinate values inside the file are labeled. Change dimensions of the tablets that need to be cleaned
and customize the amount of times you want the robot to wash the screens in cycles. 

Then run the following command in the terminal:
```
python3 subproc.py
```

If you wish to stop the robot from the terminal you can do so by fisrt pressing
"ctrl + c" and then opening htop which will bring you to a screen 
to kill all processes.
```
sudo htop
```

## Functionality
The dorna fixture operates on multiple files that communicate with each other. The code files
that are important to note are **double_wash.py** and **front_io.py**

**double_wash** contains the program that gives the robot an automated cycle of
cleaning a tablet's screen and perimeter before moving to the second device on the 
fixture. There are also functions within it for communication with other files as 
well as recording logs to **screen_tracker**

**front_io.py** is what enables the control panel to interface with the robot and 
have functioning buttons the user can work with while the robot is operating. It 
operates on reading IO from the raspberry PI and running them through case statements.
The file also contains state tracking for organization --> this is important for toggling
switches during operation

## File communication
The fixture works from a central file called **subproc.py** this file starts both double_wash and front_io
as two seperate processes to run simultaneously, then setting both pipelines to wait for both processes
to complete their functions and then kill both of them. This helps the fixture with being able to avoid crashing
and recovering from accidents.

There are two other sh files: 
The first sh file called killfile is simple as it is meant for a pid to be passed into it for being terminated.
A second file called screen_cleaning_start functions a bit similairly but it has multiple routes. Passing in a pid
will have the file kill it but a -1 can also be passed in order to skip this function. These files exist so that
if the robot crashes or it a stop button is pressed, the process will be killed which allows the robot to restart on
a new wash cycle without being slowed down by still having other processes running in the background. 

## Logging
The fixture features a robust logging system for both the wash cycles intended for the testers and a system log for
maintainence purposes. The wash cycle log will print out a line to file after a screen or perimeter of a device is washed.
There would be two new added lines for each device cleaned because of this. Time stamps will also be given with each line
as well as a fractional amount of # of washes over the amount the user has given in the json.

The second log file reports system updates like when homing is complete or other functions of the robot run or if end
or emergency stops are pressed. This is mostly meant for troubleshooting in case the operation runs into errors. 


## Warnings

