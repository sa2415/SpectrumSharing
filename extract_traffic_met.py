from collections import defaultdict
import re

# Read input report (replace with actual filename or string input if needed)
with open("report.log", "r") as f:
    report = f.read()

# Regular expressions to extract year and percentages
region_year_pattern = re.compile(r"Region Size (\d+), Year (\d+)")
wifi_pattern = re.compile(r"Percentage of Total Wifi Traffic Demand Met: ([\d.]+)%")
cellular_pattern = re.compile(r"Percentage of Total Cellular Traffic Demand Met: ([\d.]+)%")

# Dictionary to hold results grouped by region size
results_by_region = defaultdict(list)

# Split report by section to isolate blocks
sections = re.split(r"={70,}", report)

for section in sections:
    # print("SECTION")
    # print(section)
    region_year_match = region_year_pattern.search(section)
    wifi_match = wifi_pattern.search(section)
    cell_match = cellular_pattern.search(section)

    # print("HERE")
    # print(region_year_match)
    # print(wifi_match)
    # print(cell_match)

    if region_year_match and wifi_match and cell_match:
        region_size = int(region_year_match.group(1))
        year = int(region_year_match.group(2))
        wifi = float(wifi_match.group(1))
        cellular = float(cell_match.group(1))
        results_by_region[region_size].append((year, wifi, cellular))

# Print results grouped by region size
print("RegionSize\tYear\tWifiTrafficMet(%)\tCellularTrafficMet(%)")
for region_size in sorted(results_by_region.keys()):
    for year, wifi, cellular in sorted(results_by_region[region_size]):
        print(f"{region_size}\t{year}\t{wifi}%\t{cellular}%")