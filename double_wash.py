import os
import sys
import json
from dorna2 import Dorna
import time
import RPi.GPIO as GPIO
import math
import subprocess
from datetime import datetime

#Test the timer and then push to github, basically done and then do AMA stuff

# Initializing global variables and objects
flag = False
ROBOT = Dorna()
TIMEOUT = 5   
c_axis = 0.04179
VERSION = "3.0.0"
debug_flag = False

# Represents the physical buttons and switches on the fixture. 
# Dictionary containing the input pin number and their active highs
PUMP_BTN = {"output": 0, "active_high": True}
RUN_SWITCH = {"input":1, "active_high":True}
MOTOR_SWITCH = {"input":2, "active_high":True}
HOME_BTN = {"input":3, "active_high":True}
EMERGENCY_BTN = {"input":6, "active_high":True}
TEMP_BTN = {"input":4, "active_high":False}

# Name of the position json file
POSITIONS_JSON = "positions.json"

# Gets the current path to this python file
def get_position_path():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_directory, POSITIONS_JSON)

# Returns all of the joint degree rotations and cartesian coordinates
# Returns both as a tuple
def get_all_joint_positions():
    all_joints = ROBOT.get_all_joint()
    all_cart = ROBOT.get_all_pose()
    return [all_joints, all_cart]

# Trys to parse the position.json file in the current directory if
# file does not exist make a new file with predefined joints
def parse_positions_json():
    positions_json_path = get_position_path()
    try:
        with open(positions_json_path,  'r') as position_file:
            data = json.load(position_file)
            for key, value in data.items():
                data[key] = tuple(value)
            return data
    except FileNotFoundError:
        default_position_json = {
            "HOME":            (180.0, 180.0, -142.0, 135.0, 0.0, 0.0),
            "SAFE":            (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "DISPEN_BENEATH":  (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "DISPEN_GRAB":     (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "EJEC_ABOVE":      (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "EJEC_ATTACH":     (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "EJECT_WAIT":      (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "TRASH":           (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "TRASH_GENTLE1":   (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "TRASH_GENTLE2":   (90.0, -40.0, 130.0, 135.0, 0.0, 0.0),
            "test": (90.0, -40.0, 130.0, 135.0, 0.0, 10.0)
        }
        #create_json(positions_json_path, default_position_json)
        return default_position_json

# Checks pins of the raspberry pi to see if they are active and usable
def check_input(input_item:dict):
    input_index = input_item["input"]
    active_high = input_item["active_high"]
    return ROBOT.get_input(input_index) == active_high

# Sends the robot to the homed position on the rail
# Important for later moving into start position and wash positions
def new_homing_position():
    # Rotate away from j0 hard stop
    ROBOT.play(TIMEOUT = -1,
        cmd = "jmove",
        rel=1,
        j0= -5,
        j1= 0,
        j2= 0,
        j3= 0,
        j4= 0,
        j5= 0,
        vel = 5,
        accel = 250,
        jerk = 500
        )
    
    # Move towards homing switch
    ROBOT.play(TIMEOUT = 1,
        cmd = "jmove",
        rel=1,
        j0= 0,
        j1= 0,
        j2= 0,
        j3= 0,
        j4= 0,
        j5= -50,
        vel = 0.2,
        accel = 0.5,
        jerk = 0.5
        )

    # Read from comm file to confirm homing complete
    with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "r") as f:
        while True:
            new_text = bool(f.read())
            if new_text == False:
                pass
            elif new_text == True:
                print("1")
                break
    
    # Clear comm file
    with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "r+") as f:
        f.truncate(0)

    # Write pid to comm file
    with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "a") as f:
        f.write("*{}^".format(str(os.getpid())))
    time.sleep(0.5)

    # Clears the alarm FrontIO made when the homing switch was pressed
    ROBOT.halt()
    ROBOT.clear_all_event()
    ROBOT.set_alarm(0)
    print("Alarms cleared")

    # Move away from homing switch and move back against j0 stop
    ROBOT.play(TIMEOUT = -1,
        cmd = "jmove",
        rel=1,
        j0= 5,
        j1= 0,
        j2= 0,
        j3= 0,
        j4= 0,
        j5= 5,
        vel = 15,
        accel = 1000,
        jerk = 2000
        )

    using_home_pos = get_all_joint_positions()
    zero = (-float(using_home_pos[0][5]))
    return(zero)
    
# Function for coordinated movement of cleaning a screen
def wash_single_screen(zero, screen):
    ROBOT.set_alarm(0)

    # Angle of screens, standard
    angle = math.radians(22) 
    
    # Pull positions and data from Json
    dict_pos = parse_positions_json()
    width = dict_pos["width"]
    height = dict_pos["height"]
    ready_cart =  dict_pos["ready_cart"]
    using_pos = [dict_pos["left_pos_screen"], dict_pos["right_pos_screen"] ]
    left_seg = dict_pos["left_seg"]
    right_seg = dict_pos["right_seg"]
    segments = (float(left_seg[0]), float(right_seg[0]))

    # Calculate cartesian movement from json inputs
    Delta_Y = [(math.sin(angle) * height[0]) , (math.sin(angle)* height[1]) ]
    Delta_Z = [(math.cos(angle) * height[0]), (math.cos(angle) * height[1])]
    Delta_C = [width[0] /left_seg[0] * .04179, width[1] / right_seg[0] * .04179]

    if debug_flag:
        print("Moving to ready position")
    # Move to the ready position
    ROBOT.play(TIMEOUT = -1,
        cmd = "jmove",
        rel=0, 
        x=ready_cart[0], 
        y=ready_cart[1], 
        z=ready_cart[2], 
        a=ready_cart[3], 
        b=ready_cart[4],
        c=ready_cart[5] - zero,
        vel=250, 
        accel=1000, 
        jerk=2000
        )
   
    if debug_flag:
        print("Moving to screen")
    # Move to the specified screen
    ROBOT.play(TIMEOUT = -1, 
        cmd = "jmove",
        rel=0, 
        j0=using_pos[screen][0], 
        j1=using_pos[screen][1], 
        j2=using_pos[screen][2], 
        j3=using_pos[screen][3], 
        j4=using_pos[screen][4],
        j5=using_pos[screen][5] - zero,
        vel=250, 
        accel=50, 
        jerk=100
        )
    if debug_flag:
        print("Washing")
    # Repeat up-down wash motion of screen
    for i in range(int(segments[screen]/2)):
        # Move down at an angle
        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=-Delta_Y[screen], 
            z=-Delta_Z[screen], 
            a=0.0, 
            b=180.0,
            c=-Delta_C[screen],
            vel=250, 
            accel=1000, 
            jerk=2000
        )
        # Move up at an angle
        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=Delta_Y[screen], 
            z=Delta_Z[screen], 
            a=0.0, 
            b=-180.0,
            c=-Delta_C[screen],
            vel=250, 
            accel=1000, 
            jerk=2000
            )

# For washing edge of a screen
def wash_single_perimeter(zero, screen):
    # Screen angle, standardized
    angle = math.radians(22)

    # Pull positions and other data from the Json file
    dict_pos = parse_positions_json()
    depthY = dict_pos["tool_length"]
    radius = dict_pos["radius"]
    using_pos = (dict_pos["left_pos_device"], dict_pos["right_pos_device"])
    width = dict_pos["width"]
    height = dict_pos["height"]
    depth = dict_pos["depth"]
    perm_disp = dict_pos["Perimeter displacement"]

    # Calculate catresian offsets from jJson data
    Delta_RY = math.sin(angle) * radius[0]
    Delta_RZ = math.cos(angle) * radius[0]
    
    # Calculate offsets for cleaning edges
    Delta_move_side_y = [(height[0]+ 2 *radius[0]) * math.sin(angle), (height[1]+ 2 *radius[0]) * math.sin(angle)]
    Delta_move_side_z = [(height[0]+ 2 *radius[0]) * math.cos(angle), (height[1]+ 2 *radius[0]) * math.cos(angle)]

    if debug_flag:
        print("Moving to screen")
    # Move to the robot's specified screen
    ROBOT.play(TIMEOUT = -1, 
        cmd = "jmove",
        rel=0, 
        j0=using_pos[screen][0], 
        j1=using_pos[screen][1], 
        j2=using_pos[screen][2], 
        j3=using_pos[screen][3], 
        j4=using_pos[screen][4],
        j5=using_pos[screen][5] - zero,
        vel=100, 
        accel=500, 
        jerk=1000
        )
    if debug_flag:
        print("Moving away from screen corner")
    # Move with offsets away from the screen corner
    ROBOT.play(TIMEOUT = -1, 
        cmd = "lmove",
        rel=1, 
        x=0.0, 
        y=Delta_RY, 
        z=Delta_RZ, 
        a=0.0, 
        b=0.0,
        c=radius[0] * c_axis,
        vel=75, 
        accel=750, 
        jerk=1500
    )

    
    if debug_flag:
        print("changing depth")
    # change depth to clean full screen
    for i in range(math.ceil(depth[0] / depthY[0])):
        # Move the end effector in so it can reach the edge of the screen
        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=math.cos(angle) * depthY[0], 
            z=math.sin(angle) * -depthY[0], 
            a=0.0, 
            b=0.0,
            c=0.0,
            vel = 100, 
            accel=1000, 
            jerk=2000
        )
    

        # Move down left side screen
        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=-Delta_move_side_y[screen],
            z=-Delta_move_side_z[screen],
            a=0.0, 
            b=0.0,
            c=0.0,
            vel=75, 
            accel=2000, 
            jerk=4000
        )
    
        # Move across the bottom side
        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=0.0, 
            z=-0.0, 
            a=0.0, 
            b=0.0,
            c=-(((width[screen] + 2 * radius[0]) - perm_disp[0])/2) * c_axis,
            vel=3.124, 
            accel=2000,
            jerk=4000
        )

        # Move down to avoid mounting hardware
        ROBOT.play(TIMEOUT = -1,
            cmd = "lmove",
            rel=1,
            x=0.0,
            y=0.0,
            z=-perm_disp[0],
            a=0.0,
            b=0.0,
            c=0.0,
            vel=50,
            accel=2000,
            jerk=4000)

        # Move to avoid mounting hardware
        ROBOT.play(TIMEOUT = -1,
            cmd = "lmove",
            rel=1,
            x=0.0,
            y=0.0,
            z=0.0,
            a=0.0,
            b=0.0,
            c=-perm_disp[1] * c_axis,
            vel=3.124,
            accel=2000,
            jerk=4000)

        # Move back in to keep washing perimiter
        ROBOT.play(TIMEOUT = -1,
            cmd = "lmove",
            rel=1,
            x=0.0,
            y=0.0,
            z=perm_disp[0],
            a=0.0,
            b=0.0,
            c=0.0,
            vel=50,
            accel=2000,
            jerk=4000)

        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=0.0, 
            z=-0.0, 
            a=0.0, 
            b=0.0,
            c=-(((width[screen] + 2 * radius[0]) - perm_disp[0])/2) * c_axis,
            vel=3.124, 
            accel=2000,
            jerk=4000
        )


    
# Move up right side of screen
        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=Delta_move_side_y[screen],
            z=Delta_move_side_z[screen],
            a=0.0, 
            b=0.0,
            c=0.0,
            vel=75, 
            accel=2000, 
            jerk=4000
        )
    
        # Move across the top of the screen
        # Is Z supposed to be equal to negative 0?
        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=0.0, 
            z=-0.0, 
            a=0.0, 
            b=0.0,
            c=(((width[screen] + 2 * radius[0])  - perm_disp[1])/2) * c_axis,
            vel=3.124, 
            accel=2000,
            jerk=4000
        )

        # Move up to avoid mounting hardware
        ROBOT.play(TIMEOUT = -1,
            cmd = "lmove",
            rel=1,
            x=0.0,
            y=0.0,
            z=perm_disp[0],
            a=0.0,
            b=0.0,
            c=0.0,
            vel=50,
            accel=2000,
            jerk=4000)

        # Move accross to avoid mounting hardware
        ROBOT.play(TIMEOUT = -1,
            cmd = "lmove",
            rel=1,
            x=0.0,
            y=0.0,
            z=0.0,
            a=0.0,
            b=0.0,
            c=perm_disp[1] * c_axis,
            vel=3.124,
            accel=2000,
            jerk=4000)

        # Move back in to keep cleaning perimiter
        ROBOT.play(TIMEOUT = -1,
            cmd = "lmove",
            rel=1,
            x=0.0,
            y=0.0,
            z=-perm_disp[0],
            a=0.0,
            b=0.0,
            c=0.0,
            vel=50,
            accel=2000,
            jerk=4000)

        ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=0.0, 
            z=-0.0, 
            a=0.0, 
            b=0.0,
            c=(((width[screen] + 2 * radius[0])  - perm_disp[1])/2) * c_axis,
            vel=3.124, 
            accel=2000,
            jerk=4000
        )
    
    if debug_flag:
        print("Moving away from screen")
    # Move away from screen
    ROBOT.play(TIMEOUT = -1, 
            cmd = "lmove",
            rel=1, 
            x=0.0, 
            y=(-math.ceil(depth[0]/depthY[0]) - 1) * (math.cos(angle)* depthY[0]), 
            z=(math.ceil(depth[0]/depthY[0]) + 1) * (math.sin(angle) * depthY[0]), 
            a=0.0, 
            b=0.0,
            c=0.0,
            vel=100, 
            accel=1000, 
            jerk=2000
        )

# Reads log file and gathers data on last movements
def parse_logger():

    # Open the log file and get the last line
    with open("screen_tracker.log", 'r') as z:
        last_line = ""
        for line in z:
            if line.find('-') == 0:
                last_line = line
    # Parse the last line of the log file to get basic info
    try: 
        screen_or_perim = last_line[last_line.index('~') + 2]
        device_num = last_line[last_line.index('#') + 1]
        iteration = last_line[last_line.index('d') + 1:last_line.index('/')]
        total_iterations = last_line[last_line.index('/') + 1:last_line.index('s') - 5]
    except:
        return None

    # Log the time this funtion runs
    with open("screen_tracker.log",'a') as s:
        s.write("\nTime: {}\n".format(datetime.now()))

    # Return necessary data
    return [device_num, screen_or_perim, iteration, total_iterations]

def gelgoog(cycles):
    try: 
        parse = parse_logger()
        # Typecast data drom parsed log file
        if parse is not None:
            counter = int(parse[0])
            start_iteration = int(parse[2])
            revs = int(parse[3])
            Type = parse[1]
            print("Resuming")
        else:
            # This is not supposed to exist
            error()
    except Exception as E:
        #open("screen_tracker.log", 'a').close()
        counter = 0
        start_iteration = 1
        Type = 'S'
        revs = cycles[0]
        print("Using Defaults")
    return [counter, start_iteration, Type, revs]

# This controls all of the robots movements
def zgok():
    dict_pos = parse_positions_json()
    cycles = dict_pos["cleaning_cycles"]
    dwell_time = dict_pos["dwell_time"]
    
    try: 
        parse = parse_logger()
        # Typecast data drom parsed log file
        if parse is not None:
            counter = int(parse[0])
            start_iteration = int(parse[2])
            revs = int(parse[3])
            Type = parse[1]
            print("Resuming")
        else:
            # This is not supposed to exist
            error()
    except Exception as E:
        #open("screen_tracker.log", 'a').close()
        counter = 0
        start_iteration = 1
        Type = 'S'
        revs = cycles[0]
        print("Using Defaults")

        
    # Pull ready position from Json
    dict_pos = parse_positions_json()
    ready_cart = dict_pos["ready_cart"]
    
    # Get c axis offset & home the c axis
    zero = new_homing_position()

    # Check the previous logged event to determine whether to clean screen, perim, or move to next device
    if Type == 'S':
        ROBOT.play(TIMEOUT = -1, 
            cmd = "jmove",
            rel=0, 
            x=ready_cart[0], 
            y=ready_cart[1], 
            z=ready_cart[2], 
            a=ready_cart[3], 
            b=ready_cart[4],
            c=ready_cart[5] - zero,
            vel=45, 
            accel=2000, 
            jerk=4000
        )

        # Above if-statement checks to see if last logged event was a screen, so do a perimeter wash now
        if debug_flag:
            print("wash perimeter is going to run")

        wash_single_perimeter(zero, counter)
        # If-statement so that robot cannot write to log file when the motor is off
        if ROBOT.get_motor() and not ROBOT.get_alarm():
            with open("screen_tracker.log", "a") as s:
                s.write("-{}~ Perimeter #{} cleaned {}/{} times\n".format(datetime.now(),counter ,start_iteration, revs ))
        
        print("Cleaned screen {} {} times\n".format(str(counter), start_iteration))

    
    # Counters to keep track of which screen is being cleaned when logging
    if counter == 0:
        counter = 1
    elif counter == 1:
        counter = 0
    if debug_flag:
        print("Robot moving to ready position")
    # Move to ready position
    ROBOT.play(TIMEOUT = -1, 
        cmd = "jmove",
        rel=0, 
        x=ready_cart[0], 
        y=ready_cart[1], 
        z=ready_cart[2], 
        a=ready_cart[3], 
        b=ready_cart[4],
        c=ready_cart[5] - zero,
        vel=15, 
        accel=10, 
        jerk=20
    )

    # Loop for washing motion of screen
    for i in range((int(start_iteration) -1) * 2, 2 * revs):
        ROBOT.play(TIMEOUT = -1, 
            cmd = "jmove",
            rel=0, 
            x=ready_cart[0], 
            y=ready_cart[1],  
            z=ready_cart[2], 
            a=ready_cart[3], 
            b=ready_cart[4],
            c=ready_cart[5] - zero,
            vel=15, 
            accel=10, 
            jerk=20
        )

        lala = int(i/2)+1
        if debug_flag:
            print("washing screen")

        print("Turning pump on")


        operation_device_time = time.time()
        # Block of code to briefly run the pump to wet the 
        # brush of the robot
        start_pump_time = time.time()
        duration = 0.5
        

        while time.time() - start_pump_time < duration:
            ROBOT.set_output(15, 1)
        ROBOT.set_output(15, 0)
        wash_single_screen(zero, counter)
        


        if ROBOT.get_motor() and not ROBOT.get_alarm():
            with open("screen_tracker.log", "a") as s:
                s.write("-{}~ Screen #{} cleaned {}/{} times\n".format(datetime.now(),counter ,lala, revs ))

        wash_single_perimeter(zero, counter)
        print("Turning pump off")
        completion_device_time = time.time() - start_pump_time

        


        if ROBOT.get_motor() and not ROBOT.get_alarm():
            with open("screen_tracker.log", "a") as s:
                s.write("-{}~ Perimeter #{} cleaned {}/{} times\n".format(datetime.now(),counter ,lala, revs ))

        print("Cleaned screen {} {} times".format(str(counter), str(lala)))
        print("")
        if counter == 0:
            counter = 1
        else:
            counter = 0

        if completion_device_time < dwell_time[0]:
            time.sleep(int(dwell_time[0])- completion_device_time)
        else:
            print("dwell time is shorter than operation time, no need to wait")
        print("Robot is waiting: {}".format(dwell_time))
    
    # Move to ready position
    ROBOT.play(TIMEOUT = -1, 
        cmd = "jmove",
        rel=0, 
        x=ready_cart[0], 
        y=ready_cart[1], 
        z=ready_cart[2], 
        a=ready_cart[3], 
        b=ready_cart[4],
        c=ready_cart[5] - zero,
        vel=15, 
        accel=10, 
        jerk=20
    )
    flag = True
"""
def zeong():
    dict_pos = parse_positions_json()
    cycles = dict_pos["cleaning_cycles"]

    vars = new_homing_position()

    Big_Zam = gelgoog(cycles)

    ready_cart = dict_pos["ready_cart"]

    start_iteration = Big_Zam["start_iteration"]
    revs = Big_Zam["revs"]
    counter = Big_Zam["counter"]




    for i in range((int(start_iteration) -1) * 2, 2 * revs):

"""


    




def Lain():
    time.sleep(5)
    pid = os.getpid()
    try:
        print("Robot Connected") if ROBOT.connect() else sys.exit()
        #help()
        while True:
            command = input("> ")
            if command in ['q', 'quit']:
                break
            elif command in ['g', 'get']:
                print(get_all_joint_positions())
            elif command in ['h', 'homing']:
                new_homing_position()
            elif command in ['l', 'larse']:
                test = parse_logger()
                print(f"cleaning {test[1]} of device {test[0]} for the {test[2]} of {test[3]} times")
            elif command in ['t', 'test']:
                test = parse_logger()
                zgok(test[0], test[1], test[2], test[3])
                break
            else:
                #help()
                print("")
    except Exception as e:
        print(e)
    finally:
        ROBOT.close()
        print("Robot Disconnected")

def main():
    while not ROBOT.connect():
        pass
    print("Robot Connected")
    while True:
        with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "r") as p:
            spade = p.read()
            if spade == '00':
                if debug_flag:
                    print("zgok running")
                zgok()

        if flag == True:
            break
    ROBOT.close()
    print("Robot Disconnected")



if __name__ == "__main__":
    print(f"Version: {VERSION}")
    main()


