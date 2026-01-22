import subprocess

# Start processes
p1 = subprocess.Popen(["python", "front_IO.py"])
p2 = subprocess.Popen(["python", "double_wash.py"])

# Wait for processes to finish
p1.wait()
p2.wait()

# Kill the processes to ensure only required threads are running
p1.terminate()
p2.terminate()