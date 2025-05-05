import re

# Read input report (replace with actual filename or string input if needed)
with open("report.log", "r") as f:
    report = f.read()

# Regular expressions to extract year and percentages
year_pattern = re.compile(r"Year (\d+)")
wifi_pattern = re.compile(r"Percentage of Total Wifi Traffic Demand Met: ([\d.]+)%")
cellular_pattern = re.compile(r"Percentage of Total Cellular Traffic Demand Met: ([\d.]+)%")

# Find all matches
years = list(map(int, year_pattern.findall(report)))
wifi_met = list(map(float, wifi_pattern.findall(report)))
cellular_met = list(map(float, cellular_pattern.findall(report)))

# Sanity check
assert len(years) == len(wifi_met) == len(cellular_met), "Mismatch in parsed data lengths!"

# Output results
print("Year,WifiTrafficMet(%),CellularTrafficMet(%)")
for y, w, c in zip(years, wifi_met, cellular_met):
    print(f"{y}\t{w}%\t{c}%")
