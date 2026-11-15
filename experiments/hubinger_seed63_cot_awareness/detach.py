"""Start a command in its own session so it survives the launching shell. Usage: detach.py LOG CMD..."""
import subprocess, sys
log = open(sys.argv[1], "ab")
p = subprocess.Popen(sys.argv[2:], stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     start_new_session=True)
print(p.pid)
