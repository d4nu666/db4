import os

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Raw OD datasets live in ../data/raw relative to this script.
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

pure = pd.read_csv(os.path.join(DATA_DIR, "pure_water.csv"))
algae = pd.read_csv(os.path.join(DATA_DIR, "algae.csv"))

channels = ["clear", "red", "green", "blue"]

# Label by filename because both files may contain test=BLANK
pure_label = "Pure water"
algae_label = "Algae water"

# Plot clear channel over time
plt.figure(figsize=(9, 5))
plt.plot(pure["time_s"], pure["clear"], label=pure_label)
plt.plot(algae["time_s"], algae["clear"], label=algae_label)
plt.xlabel("Time (s)")
plt.ylabel("Clear channel intensity")
plt.title("Clear channel intensity over time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# Compare mean channel readings
pure_means = pure[channels].mean()
algae_means = algae[channels].mean()

x = np.arange(len(channels))
width = 0.35

plt.figure(figsize=(9, 5))
plt.bar(x - width/2, pure_means.values, width, label=pure_label)
plt.bar(x + width/2, algae_means.values, width, label=algae_label)
plt.xticks(x, channels)
plt.xlabel("TCS34725 channel")
plt.ylabel("Mean intensity")
plt.title("Mean RGB/clear intensity: pure water vs algae water")
plt.legend()
plt.grid(True, axis="y")
plt.tight_layout()
plt.show()

# Estimate OD using pure water as blank/reference
# OD = -log10(I_sample / I_blank)
od = -np.log10(algae_means / pure_means)

plt.figure(figsize=(8, 5))
plt.bar(channels, od.values)
plt.xlabel("TCS34725 channel")
plt.ylabel("OD = -log10(sample / blank)")
plt.title("Estimated optical density of algae water")
plt.grid(True, axis="y")
plt.tight_layout()
plt.show()

print(pd.DataFrame({
    "channel": channels,
    "pure_water_mean": pure_means.values,
    "algae_water_mean": algae_means.values,
    "percent_change_algae_vs_pure": ((algae_means - pure_means) / pure_means * 100).values,
    "estimated_OD": od.values
}))
