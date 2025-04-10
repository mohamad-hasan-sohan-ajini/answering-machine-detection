# coding: utf-8
import re
import numpy as np
import matplotlib.pyplot as plt
from argparse import ArgumentParser

# HOW TO USE:
# 1. Run the CPU usage logging script to generate "cpu_log.txt": top -b -d 0.1 | grep "^%Cpu" >> cpu_log.txt
# 2. Run this script with the log file as an argument: python plot_cpu_usage.py --log-file cpu_log.txt

# Parse command-line arguments
parser = ArgumentParser(description="Plot CPU usage from a log file.")
parser.add_argument(
    "--log-file", type=str, required=True, help="Path to the CPU log file."
)
args = parser.parse_args()

# Initialize dictionary to store all CPU fields
cpu_data = {
    "us": [],
    "sy": [],
    "ni": [],
    "id": [],
    "wa": [],
    "hi": [],
    "si": [],
    "st": [],
}

# Read the file
with open(args.log_file, "r") as f:
    for line in f:
        if line.startswith("%Cpu"):
            # Use regex to extract fields
            matches = re.findall(r"([\d.]+) (\w+)", line)
            for value, key in matches:
                if key in cpu_data:
                    cpu_data[key].append(float(value))

# Convert lists to numpy arrays
for key in cpu_data:
    cpu_data[key] = np.array(cpu_data[key])

# Plot
plt.figure(figsize=(10, 6))
for key, values in cpu_data.items():
    plt.plot(values, label=key)

plt.title("CPU Usage Over Time")
plt.xlabel("Time (samples)")
plt.ylabel("Percentage (%)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# Statistics
# Compute mean and std of `us`
us = cpu_data["us"]
us_mean = us.mean()
us_std = us.std()
threshold = us_mean + us_std

# Find start and end indices
start = next((i for i, val in enumerate(us) if val > threshold), None)
end = next(
    (i for i in reversed(range(len(us))) if us[i] < threshold and i > start), None
)

# Check if valid window found
if start is not None and end is not None and end > start:
    us_avg = us[start : end + 1].mean()
    sy_avg = cpu_data["sy"][start : end + 1].mean()
    id_avg = cpu_data["id"][start : end + 1].mean()

    print(f"\n\nAverages between time steps {start} and {end} (us > mean + std):")
    print(f"us (user):    {us_avg:.2f}%")
    print(f"sy (system):  {sy_avg:.2f}%")
    print(f"id (idle):    {id_avg:.2f}%")
else:
    print("No active interval found where 'us' exceeds mean + std.")
