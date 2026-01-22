from dorna2 import Dorna
import os
from double_wash import parse_positions_json
from double_wash import new_homing_position
import time
from double_wash import parse_logger

# Set up coordinates pulled from json file
dict_pos = parse_positions_json()
ready_cart = dict_pos["ready_cart"]
tool_length = dict_pos["tool_length"]
folded = dict_pos["fold"]

# Thread communication
# Clear and then write 0 to comm file
with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "r+") as f:
    f.truncate(0)
with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "a") as f:
    f.write('0')

# Standard Robot Initilization
robot = Dorna()
robot.connect()

# State tracking
E_STOP_STATE = True 
Motor_State = bool(robot.get_input(12))
Run_State = False 
PUMP_State = robot.get_input(4) # <-- CHANGE FOR LATER
END_STOP_STATE = False 


print("I/O Connected")
robot.set_motor(Motor_State)

# Robot clears alarm if E_Stop or Run aren't active
if not E_STOP_STATE or Run_State:
    robot.set_alarm(1)
    robot.halt()
else:
    robot.set_alarm(0)

# Write 1 to comm file to signal 'double' to run
with open("thatreallyawfulsongcalledWalkieTalkieMan.txt" , "a") as f:
    f.write('1')


# Monitor I/O states
while True: # <-- CHANGE TO CHECK IF THE OTHER PROGRAM IS RUNNING
    # E-STOP
    E_IO = robot.get_input(15)
    # Motor Switch
    M_IO = robot.get_input(12)
    # Run Switch
    R_IO = robot.get_input(14)
    # Pump Resivour Sensor
    L_IO = robot.get_input(4) # <-- Jake says for now it is 4
    # Home Button
    H_IO = robot.get_input(13)
    # C Axis End Stop 
    S_IO = robot.get_input(3)

    time.sleep(0.075)
    if robot.get_input(14) is not R_IO:
        R_IO = not R_IO
        print(f"R_IO: {R_IO}")
    if robot.get_input(15) is not E_IO:
        E_IO = not E_IO
        print(f"E_IO: {E_IO}")
    if robot.get_input(12) is not M_IO:
        M_IO = not M_IO
        print(f"M_IO: {M_IO}")
    """
    if robot.get_input(4) is not L_IO:
        L_IO = not L_IO
        print(f"L_IO: {L_IO}")
    if robot.get_input(13) is not H_IO:
        H_IO = not H_IO
        print(f"H_IO: {H_IO}")
    """
    if robot.get_input(3) is not S_IO:
        S_IO = not S_IO
        print(f"S_IO: {S_IO}")

# E-Stop while in Run going to pause causes a crash

    # Halt robot if E-Stop is pressed
    
    if E_IO == True and E_STOP_STATE == False:
        robot.halt()
        E_STOP_STATE = True
        print("E-STOP Released")
        

    if E_IO == False and E_STOP_STATE == True:
        # If the E-Stop is no longer pressed, remove the halt
        robot.set_alarm(0)
        E_STOP_STATE = False
        print("E-STOP!")
    
    # Run switch controls
    if R_IO == True and Run_State == False and M_IO:
        robot.set_alarm(0)
        Run_State = True

        # After clearing alarm write to comm file to signal back to 'double'
        with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "r+") as q:
            q.truncate(0)

        with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", "a") as w:
            w.write('00')

        print("Run")
    # Stop current movement and fold up
    # Write to killfile to terminate pids
    if R_IO == False and Run_State == True:
        
        # Freeze the robot
        robot.halt()
        robot.clear_all_event()

        # Get the robots current position
        robot_pose = robot.get_all_joint()

        # Pull the PID of other porgram from communication file
        with open("thatreallyawfulsongcalledWalkieTalkieMan.txt", 'r') as z:
            last_line = z.readline()
            lid = last_line[last_line.index('*')+1:last_line.index('^')]
            print(f"{lid} <-- lid (PID of double wash)")

        # Send pid to a killfile to stop the old process
        os.system('bash ./killfile.sh {}'.format(lid))

        # remove the alarm from the robot
        time.sleep(0.5)
        robot.set_alarm(0)

        # Pull the robot away from the device and to the ready position
        print(robot_pose)
        if robot_pose[0] > 157 or robot_pose[1] < -118 or robot_pose[2] > 136:
            # Saftey check so the robot doesn't fold up beyond a certian limit and crash
            print("All in!! JACKPOT (The robot is not folding up)")
            pass
        else:
            # Move -y away from screen
            robot.play(TIMEOUT = -1,
                rel = 1,
                cmd = "lmove",
                y = -tool_length[0],
                vel = 25,
                accel = 200,
                jerk = 400
                )
            
            # Go to ready position
            robot.play(TIMEOUT = -1,
                rel = 0,
                cmd = "lmove",
                x = ready_cart[0],
                y = ready_cart[1],
                z = ready_cart[2],
                a = ready_cart[3],
                b = ready_cart[4],
                vel = 25,
                accel = 10,
                jerk = 20
                )
        
        # Move to folded position
        robot.play(TIMEOUT = -1,
            rel = 0,
            cmd = "jmove",
            j0 = folded[0],
            j1 = folded[1],
            j2 = folded[2],
            j3 = folded[3],
            j4 = folded[4],
            vel = 25,
            accel = 10,
            jerk = 20
        )

        # restart the program 
        print("Paused")
        robot.set_alarm(0)
        robot.set_motor(0)
        time.sleep(.5)
        robot.set_motor(robot.get_input(12))
        robot.close()
        os.system('bash ./screen_cleaning_start.sh {}' .format(os.getpid()))
        print("NOT EXITED")

        


    # Motor State Switch
    # Clear alarm and enable motor if the switch is flipped
    if M_IO == True and E_STOP_STATE and Motor_State == False:
        robot.set_alarm(0)
        robot.set_motor(1)
        Motor_State = True
        print("Motors On")
        """
        robot_pose = robot.get_all_joint()
        if robot_pose[0] < 157 or robot_pose[1] > -118 or robot_pose[2] < 136:
            zero = new_homing_position()
        """
    # Disable motor if switch is flipped
    if M_IO == False and E_STOP_STATE and Motor_State == True:
        robot.set_alarm(0)
        robot.set_motor(0)
        Motor_State = False
        print("Motors Off")


    """
    # Pump/ Lump for resivour
    if H_IO == False and E_STOP_STATE and PUMP_State == False:
        robot.set_output(15, 0) 
        print("pump state true")
        PUMP_State = True
        
    if H_IO == True and E_STOP_STATE and PUMP_State == True:
        robot.set_output(15, 1)
        print("pump state false")
        PUMP_State = False
    """
    
    # C Axis homing switch

    # trigger a stop then write to comm file
    if S_IO == False and END_STOP_STATE == False:
        robot.halt()
        with open("thatreallyawfulsongcalledWalkieTalkieMan.txt" , "a") as f:
            f.write('1')
        END_STOP_STATE = True
        print("End Stop Triggered")
    

    
    
"""
    # Misc hardware for other projects
    if H_IO:
        print("This button is not used for this project")
"""
