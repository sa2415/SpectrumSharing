import os
import math
import copy
import queue
import random
import numpy as np
from enum import Enum
from collections import deque
from scipy.spatial import KDTree
import matplotlib.pyplot as plt
from collections import defaultdict
from scipy.spatial.distance import cdist
from matplotlib.colors import ListedColormap

import seaborn as sns
import numpy as np
import matplotlib.animation as animation

import config

U6_START = 6.5
U6_END = 7.2

demand_growth_rate = 1.0
report_file_path = "report.log"

total_num_hs = 0
total_num_bs = 0

# Constants
NUM_YEARS = config.NUM_YEARS
NUM_DAYS = config.NUM_DAYS
D_w = config.D_w 
D_c = config.D_c
traffic_demand_bounds = config.traffic_demand_bounds

db_snapshots = []
yearly_stats = defaultdict(list)
yearly_congestion_hs = {0: [], 1: [], 2: []}
yearly_congestion_bs = {0: [], 1: [], 2: []}
daily_snapshot_stats = defaultdict(lambda: [[] for _ in range(6)])
density_congestion_stats = defaultdict(lambda: defaultdict(list))


class UnitType(Enum):
    BS = 0
    HS = 1

class NetworkUnit:
    def __init__(self, id, position, traffic_demand, unit_type, density, limit=None):
        self.id = id
        self.position = position
        self.traffic_demand = traffic_demand # units = MHz
        self.frequency_bands = set() # list of tuples (start_freq, end_freq)
        self.congested = False
        self.unit_type = unit_type
        self.group_id = None
        self.density = density
        self.limit = limit
        self.bandwidth = 0

    """
    STEP 4: Updating traffic demand according to population density and time of day
    TODO: [Nicole] - acc to # of ppl, remove commuting hours 
                                          low         medium       high
    density = 0: [20, 50] Mbps       --> [20,30],     [30,40],     [40,50]
    density = 1: [200, 500] Mbps     --> [200,300],   [300,400],   [400,500]
    density = 2: [2000, 5000] Mbps   --> [2000,3000], [3000,4000], [4000,5000]

    0:00 -  8:00 : low usage       (wifi:cell = 50:50)
    8:00 - 12:00 : high wifi usage (wifi:cell = 70:30)
    12:00 - 15:00 : high cell usage (wifi:cell = 30:70)
    15:00 - 17:00 : high wifi usage (wifi:cell = 80:20)
    17:00 - 19:00 : high cell usage (wifi:cell = 40:60)
    19:00 - 24:00 : high wifi usage (wifi:cell = 75:25)
    """
    def calculate_traffic_demand(self, snapshot, demand_growth_rate, traffic_demand_bounds):
        
        # pop density --> (lower, upper) traffic demand bound for the unit
        #TODO: fix these numbers (make it respond to traffic demand increase)

        # (snapshot, unit_type) --> traffic intensity level
        traffic_intensity = {
            (0, UnitType.HS): "low",
            (0, UnitType.BS): "low",
            (1, UnitType.HS): "medium",
            (1, UnitType.BS): "low",
            (2, UnitType.HS): "medium",
            (2, UnitType.BS): "high",
            (3, UnitType.HS): "high",
            (3, UnitType.BS): "medium",
            (4, UnitType.HS): "medium",
            (4, UnitType.BS): "high",
            (5, UnitType.HS): "high",
            (5, UnitType.BS): "low",
        }

        lower_bound, upper_bound = traffic_demand_bounds[int(self.density)]
        lower_bound = int(lower_bound * demand_growth_rate)
        upper_bound = int(upper_bound * demand_growth_rate)
        traffic_intensity = traffic_intensity[(snapshot, self.unit_type)]

        range_size = upper_bound - lower_bound
        third = range_size // 3

        match traffic_intensity:
            case "low":
                upper_bound = lower_bound + third
            case "medium":
                lower_bound += third
                upper_bound = lower_bound + third
            case "high":
                lower_bound = upper_bound - third

        return random.randint(lower_bound, upper_bound) #uniform distribution

    def update_traffic_demand(self, snapshot, demand_growth_rate, traffic_demand_bounds):
        self.traffic_demand = self.calculate_traffic_demand(snapshot, demand_growth_rate, traffic_demand_bounds)


    """
    STEP 5: Makes a request to DB for more spectrum if needed, based on current traffic demand.

    Pseudocode:
        for each band allocated to the unit:
            calculate the traffic capacity of the band
            add to total traffic capacity for the unit
        
        if curren_traffic_demand > total_traffic_capacity for the unit:
            make a request to the db for the additional spectrum needed
    
    Formula: 
        required_bw = traffic_demand (Mbps) / 2 (bits/Hz) = 2*traffic_demand MHz
    """
    def make_request(self, db_request_queue):
        required_bw = self.traffic_demand / 2
        
        if self.bandwidth == 0:
            # make a request to DB using self.traffic_demand
            db_request_queue.put((self.id, required_bw))
        else:
            total_traffic_capacity = self.bandwidth * 2
            if (self.traffic_demand - total_traffic_capacity) >= 10:
                # make a request to DB using excess traffic
                assert required_bw > self.bandwidth, f"[NetworkUnit {self.id}][make_request]: Unit made a request to DB for more spectrum but required_bw <= self.bandwidth."
                # print (f"Unit {self.id} made a request to DB for more spectrum: {required_bw - total_current_bw} MHz")
                db_request_queue.put((self.id, required_bw - self.bandwidth)) 



def total_frequency_allocated(unit):
    total = 0.0
    # print (f"Unit {unit.id} frequency bands: {unit.frequency_bands}")
    for band in unit.frequency_bands:
        total += band[1] - band[0]
    return total


#--------------------------------- Debugging Functions ---------------------------------#
# Calculate Euclidean distance between two units
def calculate_distance(unit1, unit2):
    x1, y1 = unit1.position
    x2, y2 = unit2.position
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# Make sure output directory exists
os.makedirs("outputs", exist_ok=True)

def plot_units(unit_type_to_plot, filename, db, D_threshold):
    units = [unit for unit in db.database.values() if unit.unit_type == unit_type_to_plot]
    x_positions = [unit.position[0] for unit in units]
    y_positions = [unit.position[1] for unit in units]

    plt.figure(figsize=(10, 10))
    plt.scatter(x_positions, y_positions, color='blue', label=f"{unit_type_to_plot.name} Unit")

    for i, unit1 in enumerate(units):
        for j, unit2 in enumerate(units):
            if i < j:
                distance = calculate_distance(unit1, unit2)
                if distance <= D_threshold:
                    plt.plot(
                        [unit1.position[0], unit2.position[0]],
                        [unit1.position[1], unit2.position[1]],
                        color='red',
                        alpha=0.6,
                        label="Units within threshold" if i == 0 and j == 1 else ""
                    )

    plt.title(f"{unit_type_to_plot.name} Units within {D_threshold} Distance")
    plt.xlabel("X Position")
    plt.ylabel("Y Position")
    plt.legend(loc="upper right")
    plt.grid(True)

    # Save the figure
    plt.savefig(f"outputs/{filename}.png")
    plt.close()
#-----------------------------------------------------------------------------------#

"""
STEP 1: Create dat "map"!

TODO: [Swati] - change population_density acc to time of day 
Assign areas: Business, Residential, Shopping(Lunch)
"""

city_size = (10, 10)
np.random.seed(42) #to keep the initialization the same

#simulating a pop density: 0 = Low, 1 = Medium, 2 = High
population_density = np.random.choice([0, 1, 2], size=city_size, p=[0.3, 0.4, 0.3])


class Database:
    def __init__(self):
        self.database = {}
        self.wifi_freq_range = (U6_START, ((U6_END-U6_START)*0.50 + U6_START))
        self.cellular_freq_range = (((U6_END-U6_START)*0.50 + U6_START), U6_END)
        self.request_queue = queue.Queue() 
        # self.wifi_ptr = self.wifi_freq_range[0] # if < D_w
        # self.cellular_ptr = self.cellular_freq_range[0] # if < D_w

    def update_ratios(self, snapshot):
        """
         0:00 -  8:00 : low usage       (wifi:cell = 50:50)
         8:00 - 12:00 : high wifi usage (wifi:cell = 70:30)
        12:00 - 15:00 : high cell usage (wifi:cell = 30:70)
        15:00 - 17:00 : high wifi usage (wifi:cell = 80:20)
        17:00 - 19:00 : high cell usage (wifi:cell = 40:60)
        19:00 - 24:00 : high wifi usage (wifi:cell = 75:25)
        """
        if (snapshot == 0):
            wifi_ratio = 50
        elif (snapshot == 1):
            wifi_ratio = 70
        elif (snapshot == 2):
            wifi_ratio = 30
        elif (snapshot == 3):
            wifi_ratio = 80
        elif (snapshot == 4):
            wifi_ratio = 40
        elif (snapshot == 5):
            wifi_ratio = 75
        
        wifi_end = U6_START + (U6_END - U6_START) * (wifi_ratio / 100)
        self.wifi_freq_range = (U6_START, wifi_end)
        self.cellular_freq_range = (wifi_end, U6_END)

 

"""
STEP 2: Placing BS and HS 
"""
db = Database()
unit_id = 0
block_size = 10
grid_size = 100

for i in range(city_size[0]):
    for j in range(city_size[1]):
        pop_density = population_density[i, j]
        traffic_demand = 0
        # setting the number of hs and bs acc to density [TODO]
        if pop_density == 2:
            hs_count = 10  #10
            bs_count = 5 #5
        elif pop_density == 1:
            hs_count = 5   #5
            bs_count = 2   #2
        else:
            hs_count = 3  #3
            bs_count = 1  #1

        coordinates = set()
        for _ in range (hs_count):
            x_pos = random.randint(j * block_size, (j + 1) * block_size - 1)
            y_pos = random.randint(i * block_size, (i + 1) * block_size - 1)

            # no 2 units can have the same coords 
            while (x_pos, y_pos) in coordinates:
                x_pos = random.randint(j * block_size, (j + 1) * block_size - 1)
                y_pos = random.randint(i * block_size, (i + 1) * block_size - 1)

            assert ((x_pos, y_pos) not in coordinates)
            coordinates.add((x_pos, y_pos))

            db.database[unit_id] = NetworkUnit(unit_id, (x_pos, y_pos), traffic_demand, UnitType.HS, pop_density) 
            unit_id += 1


        for _ in range (bs_count):
            x_pos = random.randint(j * block_size, (j + 1) * block_size - 1)
            y_pos = random.randint(i * block_size, (i + 1) * block_size - 1)

            # no 2 units can have the same coords 
            while (x_pos, y_pos) in coordinates:
                x_pos = random.randint(j * block_size, (j + 1) * block_size - 1)
                y_pos = random.randint(i * block_size, (i + 1) * block_size - 1)

            assert ((x_pos, y_pos) not in coordinates)
            coordinates.add((x_pos, y_pos))

            db.database[unit_id] = NetworkUnit(unit_id, (x_pos, y_pos), traffic_demand, UnitType.BS, pop_density) 
            unit_id += 1


for u in db.database.values():
    if u.unit_type == UnitType.HS:
        total_num_hs += 1
    elif u.unit_type == UnitType.BS:
        total_num_bs += 1

"""
STEP 3: Make a group dictionary 
"""
# Maps group_id to a list of unit id 
# every unit in the list is within D_w/ D_c of each other 
#  BFS-style flood fill 
# A = 1/2, B =1/3, C = 1/2

group_dict = {}  # Stores unit_id -> group_id mapping
group_freq_dict = {}  # group_id -> total frequency ,a[[ing]]
group_members_dict = {}  # group_id -> list of unit_ids
grid = defaultdict(set)  # Spatial hash map (grid-based indexing)
group_id = 0  # Counter for group IDs

def get_grid_cell(x, y, cell_size):
    """Returns the grid cell coordinates for a given position."""
    return (x // cell_size, y // cell_size)

# Step 1: Populate the spatial grid
for unit_id in db.database:
    unit = db.database[unit_id]
    x, y = unit.position
    cell = get_grid_cell(x, y, D_w)
    grid[cell].add(unit_id)

# Step 2: Group units by checking only nearby grid cells
def assign_group():
    bs_units = [unit for unit in db.database.values() if unit.unit_type == UnitType.BS]
    hs_units = [unit for unit in db.database.values() if unit.unit_type == UnitType.HS]

    # Create k-d trees for BS and HS units
    bs_positions = [unit.position for unit in bs_units]
    hs_positions = [unit.position for unit in hs_units]
    
    bs_tree = KDTree(bs_positions)
    hs_tree = KDTree(hs_positions)
    
    # For BS units
    for i, unit in enumerate(bs_units):
        # Query k-d tree for BS units within distance D_w
        indices = bs_tree.query_ball_point(unit.position, D_w)  # Returns indices of nearby units
        group_dict[unit.id] = [bs_units[i].id for i in indices if bs_units[i] != unit]  

    # For HS units
    for i, unit in enumerate(hs_units):
        # Query k-d tree for HS units within distance D_c
        indices = hs_tree.query_ball_point(unit.position, D_c)  # Returns indices of nearby units
        group_dict[unit.id] = [hs_units[i].id for i in indices if hs_units[i] != unit]  

def get_frequency_allocated(unit):
    """Returns total frequency allocated to a unit in MHz."""
    total = 0
    for band in unit.frequency_bands:
        total += (band[1] - band[0]) * 1000  # GHz to MHz
    return total


def find_groups_and_sum_frequencies():
    visited = set()
    group_id = 0

    for unit_id in group_dict:
        if unit_id not in visited:
            # Start BFS for new group
            queue = deque([unit_id])
            group_members = set()

            while queue:
                current = queue.popleft()
                if current not in visited:
                    visited.add(current)
                    group_members.add(current)
                    for neighbor in group_dict[current]:
                        if neighbor not in visited:
                            queue.append(neighbor)

            # Assign frequency sum
            total_freq = sum(get_frequency_allocated(db.database[uid]) for uid in group_members)
            group_freq_dict[group_id] = total_freq
            group_members_dict[group_id] = group_members

            for uid in group_members:
                db.database[uid].group_id = group_id

            group_id += 1

        
# Step 3: Process all units and assign groups
assign_group()
find_groups_and_sum_frequencies()


"""
STEP 6: Allocate spectrum according to the rules for HS and BS based on distance 
"""
# TODO: Swati
def allocate_spectrum(unit, bandwidth):
    unit.congested = False

    if len(group_dict[unit.id]) > 0:
        if unit.unit_type == UnitType.HS:
            groupID = unit.group_id
            total_freq_allocated = group_freq_dict[groupID]

            if (bandwidth+total_freq_allocated) <= ((db.wifi_freq_range[1]-db.wifi_freq_range[0])*1000):
                unit.bandwidth = bandwidth
                group_freq_dict[groupID] += bandwidth

            else: 
                unit.bandwidth = bandwidth / (total_freq_allocated + bandwidth) * ((db.wifi_freq_range[1]-db.wifi_freq_range[0])*1000)  
                for member in group_members_dict[unit.group_id]:
                    if member == unit.id:
                        continue
                    member_unit = db.database[member]
                    member_unit.bandwidth = member_unit.bandwidth / (total_freq_allocated + bandwidth) * ((db.wifi_freq_range[1]-db.wifi_freq_range[0])*1000)

        elif unit.unit_type == UnitType.BS:
            groupID = unit.group_id
            total_freq_allocated = group_freq_dict[groupID]

            if (bandwidth+total_freq_allocated) <= ((db.cellular_freq_range[1]-db.cellular_freq_range[0])*1000):
                unit.bandwidth = bandwidth
                group_freq_dict[groupID] += bandwidth

            else: 
                unit.bandwidth = bandwidth / (total_freq_allocated + bandwidth) * ((db.cellular_freq_range[1]-db.cellular_freq_range[0])*1000)
                # reallocating the other unit's bandwidths
                for member in group_members_dict[unit.group_id]:
                    if member == unit.id:
                        continue
                    member_unit = db.database[member]
                    member_unit.bandwidth = member_unit.bandwidth / (total_freq_allocated + bandwidth) * ((db.cellular_freq_range[1]-db.cellular_freq_range[0])*1000)
            
            
    else:
        if unit.unit_type == UnitType.HS:
            unit.bandwidth = (db.wifi_freq_range[1]-db.wifi_freq_range[0])*1000
        else:
            unit.bandwidth = (db.cellular_freq_range[1]-db.cellular_freq_range[0])*1000
        unit.limit = round((db.cellular_freq_range[1]-db.cellular_freq_range[0]), 3) if unit.unit_type == UnitType.BS else round((db.wifi_freq_range[1]-db.wifi_freq_range[0]), 3)
    unit.congested = unit.bandwidth < unit.traffic_demand / 2


def print_database_state(db, group_dict):
    """
    Prints the current state of the database in a tabular format.
    """
    header = f"\n\n\n{'ID':<5}{'Type':<10}{'Position':<15}{'Traffic Demand (Mbps)':<30}{'Bandwidth (MHz)':<20}{'Congested':<10}{'Density':<10}{'Group Members':<20}"
    print(header)
    print("-" * len(header))

    for unit in db.database.values():
        
        group_str = ', '.join(map(str, group_dict.get(unit.id, [])))
        
        print(f"{unit.id:<5}{unit.unit_type.name:<10}{str(unit.position):<15}{unit.traffic_demand:<30}"
              f"{unit.bandwidth:<20.2f}{str(unit.congested):<10}{unit.density:<10}{group_str:<20}")
    
    print("\n")


def get_snapshot_duration(snapshot):
    """
    0:00 -  8:00
    8:00 - 12:00
    12:00 - 15:00 
    15:00 - 17:00
    17:00 - 19:00
    19:00 - 24:00
    """
    match snapshot:
        case 0: return 8 
        case 1: return 4
        case 2: return 3
        case 3: return 2
        case 4: return 2
        case 5: return 5
    return 0

def calc_unserviced_traffic_demand(unit):
    desired_bw = unit.traffic_demand / 2
    allocated_bw = unit.bandwidth
    # assert(desired_bw > allocated_bw)
    unserviced_bw = desired_bw - allocated_bw
    unserviced_traffic_demand = unserviced_bw * 2
    return max(0, unserviced_traffic_demand)
    

# Store yearly stats
yearly_stats = {
    "congested_hs_percent": [],
    "congested_bs_percent": [],
    "percent_traffic_demand_met_hs": [],
    "percent_traffic_demand_met_bs": []
}

def generate_report(year, total_num_hs, total_num_bs):
    with open(report_file_path, "a") as f:
        f.write(f"\n\n\n=============================================================================\n")
        f.write(f"================================== Year {year} ==================================\n")
        f.write(f"=============================================================================\n")

        num_congested_hs = 0
        num_congested_bs = 0

        hs_congestion = {}
        bs_congestion = {}

        sum_desired_hs, sum_allocated_hs = 0, 0
        sum_desired_bs, sum_allocated_bs = 0, 0

        for unit in db.database.values():
            if unit.unit_type == UnitType.HS:
                if unit.congested:
                    num_congested_hs += 1
                    hs_congestion[unit.id] = calc_unserviced_traffic_demand(unit)
                sum_desired_hs += unit.traffic_demand / 2
                sum_allocated_hs += min(unit.traffic_demand / 2, unit.bandwidth)

            elif unit.unit_type == UnitType.BS:
                if unit.congested:
                    num_congested_bs += 1
                    bs_congestion[unit.id] = calc_unserviced_traffic_demand(unit)
                sum_desired_bs += unit.traffic_demand / 2
                sum_allocated_bs += min(unit.traffic_demand / 2, unit.bandwidth)
        
        congested_bs = 100 * num_congested_bs / total_num_bs
        congested_hs = 100 * num_congested_hs / total_num_hs

        f.write(f"Percentage of congested Hotspots: {congested_hs:.3f}%\n")
        f.write(f"Percentage of congested Base Stations: {congested_bs:.3f}%\n")

        total_unserviced_traffic_demand_hs = 0
        for unit_id in hs_congestion:
            total_unserviced_traffic_demand_hs += hs_congestion[unit_id]

        total_unserviced_traffic_demand_bs = 0
        for unit_id in bs_congestion:
            total_unserviced_traffic_demand_bs += bs_congestion[unit_id]

        avg_unserviced_traffic_demand_hs = total_unserviced_traffic_demand_hs / total_num_hs
        avg_unserviced_traffic_demand_bs = total_unserviced_traffic_demand_bs / total_num_bs

        percent_traffic_demand_met_hs = (sum_allocated_hs / sum_desired_hs)*100
        percent_traffic_demand_met_bs = (sum_allocated_bs / sum_desired_bs)*100

        f.write(f"\nTotal Unserviced Traffic Demand (Mbps) for Hotspots: {total_unserviced_traffic_demand_hs:.3f}")
        f.write(f"\nAvg Unserviced Traffic Demand (Mbps) per Hotspot: {avg_unserviced_traffic_demand_hs:.3f}")
        f.write(f"\nPercentage of Total Wifi Traffic Demand Met: {percent_traffic_demand_met_hs:.3f}%\n")

        # for unit_id in hs_congestion:
        #     x, y = db.database[unit_id].position
        #     f.write(f"Unit {unit_id} Pos {(x, y)}: {hs_congestion[unit_id]}\n")
        
        f.write(f"\nTotal Unserviced Traffic Demand (Mbps) for Base Stations: {total_unserviced_traffic_demand_bs:.3f}")
        f.write(f"\nAvg Unserviced Traffic Demand (Mbps) per Base Station: {avg_unserviced_traffic_demand_bs:.3f}")
        f.write(f"\nPercentage of Total Cellular Traffic Demand Met: {percent_traffic_demand_met_bs:.3f}%\n")

        # for unit_id in bs_congestion:
        #     x, y = db.database[unit_id].position
        #     f.write(f"Unit {unit_id} Pos {(x, y)}: {bs_congestion[unit_id]}\n")

        f.write(f"\n=============================================================================\n")
        f.write(f"=============================================================================\n")
        f.write(f"=============================================================================\n")

        yearly_stats["congested_hs_percent"].append(congested_hs)
        yearly_stats["congested_bs_percent"].append(congested_bs)
        yearly_stats["percent_traffic_demand_met_hs"].append(percent_traffic_demand_met_hs)
        yearly_stats["percent_traffic_demand_met_bs"].append(percent_traffic_demand_met_bs)

        if year == 0:
            # --- Intra-Day Congestion and Allocation Plots for Day 1 --- #
            # for metric in ["hs_congestion", "bs_congestion", "hs_bandwidth", "bs_bandwidth"]:
            #     plt.figure(figsize=(8, 5))
            #     values_for_day1 = [daily_snapshot_stats[metric][snapshot][0] for snapshot in range(6)]
            #     plt.plot(range(1, 7), values_for_day1, marker="o")
            #     plt.xlabel("Snapshot")
            #     ylabel = "% Congestion" if "congestion" in metric else "Total Spectrum Allocated (MHz)"
            #     plt.ylabel(ylabel)
            #     title = f"{'Wi-Fi' if 'hs' in metric else 'Cellular'} {'Congestion' if 'congestion' in metric else 'Spectrum'} - Day 1"
            #     plt.title(title)
            #     plt.grid(True)
            #     plt.savefig(f"outputs/{NUM_YEARS}_{metric}_snapshot_day1_plot.png")
            #     plt.close()
            snapshots = range(6)
            # === Plot 1: Congestion (Grouped bar chart) ===
            hs_congestion = [daily_snapshot_stats["hs_congestion"][snap][0] for snap in snapshots]
            bs_congestion = [daily_snapshot_stats["bs_congestion"][snap][0] for snap in snapshots]

            bar_width = 0.35
            x = np.arange(len(snapshots))

            plt.figure(figsize=(10, 5))
            plt.bar(x - bar_width/2, hs_congestion, width=bar_width, label='Wi-Fi (HS)', color='skyblue')
            plt.bar(x + bar_width/2, bs_congestion, width=bar_width, label='Cellular (BS)', color='salmon')
            plt.xlabel("Snapshot")
            plt.ylabel("% Congestion")
            plt.title("Congestion Comparison (Wi-Fi vs Cellular) - Day 1")
            plt.xticks(x, [f"{i+1}" for i in snapshots])
            plt.legend()
            plt.grid(True, axis='y')
            plt.tight_layout()
            # plt.savefig(f"outputs/{NUM_YEARS}_congestion_comparison_day1_bar.png")
            plt.close()

            # === Plot 2: Spectrum Allocation (Stacked bar chart) ===
            hs_bandwidth = [daily_snapshot_stats["hs_bandwidth"][snap][0] for snap in snapshots]
            bs_bandwidth = [daily_snapshot_stats["bs_bandwidth"][snap][0] for snap in snapshots]

            plt.figure(figsize=(10, 5))
            plt.bar(x, hs_bandwidth, label='Wi-Fi (HS)', color='skyblue')
            plt.bar(x, bs_bandwidth, bottom=hs_bandwidth, label='Cellular (BS)', color='salmon')
            plt.xlabel("Snapshot")
            plt.ylabel("Total Spectrum Allocated (MHz)")
            plt.title("Spectrum Allocation (Wi-Fi + Cellular) - Day 1")
            plt.xticks(x, [f"{i+1}" for i in snapshots])
            plt.legend()
            plt.grid(True, axis='y')
            plt.tight_layout()
            plt.savefig(f"outputs/{NUM_YEARS}_bandwidth_comparison_day1_bar.png")
            plt.close()

        if year == NUM_YEARS - 1:
            os.makedirs("outputs", exist_ok=True)
            years = list(range(1, NUM_YEARS + 1))

            # --- Over all (Over years) ---#

            # Plot 1: Hotspot Congestion Over Time
            plt.figure(figsize=(8, 5))
            plt.plot(years, yearly_stats["congested_hs_percent"], color="royalblue", marker="o")
            plt.xlabel("Year")
            plt.ylabel("HS Congestion (%)")
            plt.title("Hotspot Congestion Over Time")
            plt.grid(True)
            plt.savefig(f"outputs/{NUM_YEARS}_hs_congestion_plot.png")
            plt.close()

            # Plot 2: Base Station Congestion Over Time
            plt.figure(figsize=(8, 5))
            plt.plot(years, yearly_stats["congested_bs_percent"], color="firebrick", marker="o")
            plt.xlabel("Year")
            plt.ylabel("BS Congestion (%)")
            plt.title("Base Station Congestion Over Time")
            plt.grid(True)
            plt.savefig(f"outputs/{NUM_YEARS}_bs_congestion_plot.png")
            plt.close()

            # Plot 3: Wi-Fi Traffic Demand Met
            plt.figure(figsize=(8, 5))
            plt.plot(years, yearly_stats["percent_traffic_demand_met_hs"], color="seagreen", marker="o")
            plt.xlabel("Year")
            plt.ylabel("Wi-Fi Traffic Demand Met (%)")
            plt.title("Wi-Fi Traffic Demand Satisfaction Over Time")
            plt.grid(True)
            plt.savefig(f"outputs/{NUM_YEARS}_wifi_demand_met_plot.png")
            plt.close()

            # Plot 4: Cellular Traffic Demand Met
            plt.figure(figsize=(8, 5))
            plt.plot(years, yearly_stats["percent_traffic_demand_met_bs"], color="goldenrod", marker="o")
            plt.xlabel("Year")
            plt.ylabel("Cellular Traffic Demand Met (%)")
            plt.title("Cellular Traffic Demand Satisfaction Over Time")
            plt.grid(True)
            plt.savefig(f"outputs/{NUM_YEARS}_cellular_demand_met_plot.png")
            plt.close()


def plot_yearly_congestion(congestion_dict, label_prefix):
    x_vals = list(range(1, NUM_YEARS + 1))
    plt.figure(figsize=(8, 5))
    for d in [0, 1, 2]:
        yearly_congestion = congestion_dict.get(d, [])
        if len(yearly_congestion) == len(x_vals):
            print(f"Plotting {label_prefix} Density {d}: x_vals = {x_vals}, y_vals = {yearly_congestion}")
            plt.plot(x_vals, yearly_congestion, label=f"{label_prefix} Density {d}")
        else:
            print(f"[DEBUG] Skipping Density {d} — len(x_vals): {len(x_vals)}, len(yearly_congestion): {len(yearly_congestion)}")

    plt.xlabel("Year")
    plt.ylabel("% Congestion")
    plt.title(f"{label_prefix} Congestion Over Time by Geographic Density")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"outputs/{NUM_YEARS}_{label_prefix.lower()}_density_congestion.png")
    plt.close()

def plot_congestion_heatmap(congestion_dict, label_prefix):
    # Prepare data as 2D array: rows = density, cols = years
    data = []
    for d in [0, 1, 2]:
        data.append(congestion_dict.get(d, []))

    data = np.array(data)
    plt.figure(figsize=(10, 4))
    sns.heatmap(data, annot=True, fmt=".1f", cmap="YlOrRd", cbar_kws={'label': '% Congestion'},
                xticklabels=[f"Year {i+1}" for i in range(data.shape[1])],
                yticklabels=[f"Density {i}" for i in range(data.shape[0])])
    
    plt.title(f"{label_prefix} Congestion Heatmap")
    plt.xlabel("Year")
    plt.ylabel("Geographic Density")
    plt.tight_layout()
    plt.savefig(f"outputs/{NUM_YEARS}_{label_prefix.lower()}_congestion_heatmap.png")
    plt.close()

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import os

# Function to animate congestion and show unit movement over time
def animate_congestion(db_snapshots, unit_type_to_plot, filename, city_size, population_density):
    fig, ax = plt.subplots(figsize=(10, 10))

    # Background population density
    cmap = ListedColormap(["#e0e0e0", "#a0a0a0", "#505050"])  # 0 = light, 1 = medium, 2 = dark
    ax.imshow(population_density, cmap=cmap, extent=(0, city_size[0], 0, city_size[1]), origin="lower")

    ax.set_xlim(0, city_size[0])
    ax.set_ylim(0, city_size[1])
    ax.set_title(f"{unit_type_to_plot.name} Congestion Over Time")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    # Get all unit positions of the relevant type from the first snapshot
    first_snapshot = db_snapshots[0]
    all_units_of_type = {
        unit.id: unit.position
        for unit in first_snapshot.values()
        if unit.unit_type == unit_type_to_plot
    }

    unit_ids = list(all_units_of_type.keys())
    all_x = [pos[0] for pos in all_units_of_type.values()]
    all_y = [pos[1] for pos in all_units_of_type.values()]

    # Static scatter for all units in black
    ax.scatter(all_x, all_y, s=10, c='black', label='Unit')

    # Animated scatter for congested units in red
    scatter_congested = ax.scatter([], [], s=10, c='red', label='Congested')
    ax.legend()

    def update(frame):
        units = db_snapshots[frame]
        x_cong, y_cong = [], []

        for uid in unit_ids:
            unit = units.get(uid)
            if unit and unit.congested:
                x, y = unit.position
                x_cong.append(x)
                y_cong.append(y)

        scatter_congested.set_offsets(np.column_stack((x_cong, y_cong)))
        ax.set_title(f"{unit_type_to_plot.name} Congestion - Year {frame + 1}")

    ani = animation.FuncAnimation(fig, update, frames=len(db_snapshots), repeat=False)
    ani.save(f"outputs/{filename}.gif", writer="pillow", fps=1)
    plt.close()

"""
STEP 7: Simulation loop 
"""
def simulate_dynamic_allocation(demand_growth_rate):
    for year in range(NUM_YEARS):
        print(f"\nStarting Year {year + 1}...\n")
        yearly_density_congestion_hs = {0: 0, 1: 0, 2: 0}
        yearly_density_congestion_bs = {0: 0, 1: 0, 2: 0}
        hs_total = {0: 0, 1: 0, 2: 0}
        bs_total = {0: 0, 1: 0, 2: 0}

        for day in range(NUM_DAYS):
            print(f"\n  Starting Day {day + 1}...\n")
            for snapshot in range(6):
                print(f"    Snapshot {snapshot + 1}:")

                # Clear congestion tracking
                hs_congested = 0
                bs_congested = 0

                for unit in db.database.values():
                    unit.update_traffic_demand(snapshot, demand_growth_rate, traffic_demand_bounds)            
                    unit.make_request(db.request_queue)
                    level = unit.density
                    if unit.unit_type == UnitType.HS:
                        hs_total[level] += 1
                        if unit.congested:
                            hs_congested += 1
                            yearly_density_congestion_hs[level] += 1
 
                    elif unit.unit_type == UnitType.BS:
                        bs_total[level] += 1
                        if unit.congested:
                            bs_congested += 1
                            yearly_density_congestion_bs[level] += 1


                while not db.request_queue.empty():  
                    request = db.request_queue.get()  
                    unit_id, bandwidth = request 
                    unit = db.database[unit_id]

                    allocate_spectrum(unit, bandwidth)

                db.update_ratios(snapshot)

                daily_snapshot_stats["hs_congestion"][snapshot].append(hs_congested / total_num_hs * 100)
                daily_snapshot_stats["bs_congestion"][snapshot].append(bs_congested / total_num_bs * 100)
                daily_snapshot_stats["hs_bandwidth"][snapshot].append(db.cellular_freq_range[1] - db.cellular_freq_range[0])
                daily_snapshot_stats["bs_bandwidth"][snapshot].append(db.wifi_freq_range[1] - db.wifi_freq_range[0])
            
        db_snapshots.append(copy.deepcopy(db.database))


        for d in [0, 1, 2]:
            hs_ratio = 100 * yearly_density_congestion_hs[d] / max(1, hs_total[d])
            bs_ratio = 100 * yearly_density_congestion_bs[d] / max(1, bs_total[d])
            # print(f"[DEBUG] Appending to congestion stats — Year {year}, Density {d}, BS Ratio = {bs_ratio}")
            # print(f"[DEBUG] yearly_density_congestion_bs[{d}] = {yearly_density_congestion_bs[d]}, bs_total[{d}] = {bs_total[d]}")
            yearly_congestion_hs[d].append(hs_ratio)
            yearly_congestion_bs[d].append(bs_ratio)
           
        print(f"\nDatabase after Year {year + 1}, Day {day + 1}:\n")
        print_database_state(db, group_dict)
        demand_growth_rate *= 1.2
        
        generate_report(year, total_num_hs, total_num_bs)

if __name__ == "__main__":
    open(report_file_path, "w").close()
    simulate_dynamic_allocation(demand_growth_rate)
    plot_units(UnitType.BS, "bs_units_distance", db, D_c)
    plot_units(UnitType.HS, "hs_units_distance", db, D_w)
    plot_yearly_congestion(yearly_congestion_bs, "BS")
    plot_yearly_congestion(yearly_congestion_hs, "HS")
    plot_congestion_heatmap(yearly_congestion_bs, "BS")
    plot_congestion_heatmap(yearly_congestion_hs, "HS")
    # animate_congestion(db_snapshots, UnitType.HS, "hs_congestion", city_size=(100, 100), population_density=population_density)
    # animate_congestion(db_snapshots, UnitType.BS, "bs_congestion", city_size=(100, 100), population_density=population_density)
    # animate_congestion(db_snapshots, population_density, UnitType.HS, "hs_congestion", city_size)
    # animate_congestion(db_snapshots, population_density, UnitType.BS, "bs_congestion", city_size)
    # animate_congestion(db_snapshots, UnitType.HS, "hs_congestion", city_size)
    # animate_congestion(db_snapshots, UnitType.BS, "bs_congestion", city_size)
    