# coding: utf-8
import re
import numpy as np
import matplotlib.pyplot as plt

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
with open("cpu_log.txt", "r") as f:
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
