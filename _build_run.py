import json
import subprocess
import sys
import os

args_file = sys.argv[1]

if not os.path.exists(args_file):
    print("ERROR: args file not found: " + args_file)
    sys.exit(1)

with open(args_file, "r", encoding="utf-8") as f:
    args = json.load(f)

print("  Running PyInstaller...")
print("")

result = subprocess.run(args)
sys.exit(result.returncode)
