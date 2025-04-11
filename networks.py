import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from scipy.spatial.distance import cdist
import random
from enum import Enum
import queue
from collections import defaultdict
import math
from scipy.spatial import KDTree


# Origin is top-left
# D_w, D_c = 10, 25

report_file_path = "report.log"

D_w = 3  # Distance threshold
D_c = 5

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
    def calculate_traffic_demand(self, snapshot):
        
        # pop density --> (lower, upper) traffic demand bound for the unit
        #TODO: fix these numbers
        traffic_demand_bounds = {
            0: (2, 5),
            1: (2, 5),
            2: (2, 5)
        }

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

    def update_traffic_demand(self, snapshot):
        self.traffic_demand = self.calculate_traffic_demand(snapshot)


    """
    STEP 5: Makes a request to DB for more spectrum if needed, based on current traffic demand.

    Pseudocode:
        for each band allocated to the unit:
            calculate the traffic capacity of the band
            add to total traffic capacity for the unit
        
        if curren_traffic_demand > total_traffic_capacity for the unit:
            make a request to the db for the additional spectrum needed
    
    Formula: 
        required_bw = traffic_demand (MHz) * 2 bits/Hz = 2*traffic_demand Mbps
    """
    def make_request(self, db_request_queue):
        required_bw = self.traffic_demand * 2
        
        if self.bandwidth == 0:
            # make a request to DB using self.traffic_demand
            db_request_queue.put((self.id, required_bw))
        else:
            total_traffic_capacity = self.bandwidth / 2
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

# Plotting function
def plot_units():
    # Create lists for x and y positions of BS units
    bs_units = [unit for unit in db.database.values() if unit.unit_type == UnitType.BS]
    x_positions = [unit.position[0] for unit in bs_units]
    y_positions = [unit.position[1] for unit in bs_units]

    # Create a plot
    plt.figure(figsize=(10, 10))
    
    # Plot all BS units in blue
    plt.scatter(x_positions, y_positions, color='blue', label="BS Unit")
    
    # Check distance between units and color code them
    for i, unit1 in enumerate(bs_units):
        for j, unit2 in enumerate(bs_units):
            if i < j:  # Avoid double counting
                distance = calculate_distance(unit1, unit2)
                if distance <= D_c:
                    # If units are within D_w distance, color them in red
                    plt.scatter([unit1.position[0], unit2.position[0]], 
                                [unit1.position[1], unit2.position[1]], 
                                color='red', label="Units within D_w" if i == 0 else "")
    
    # Label and show plot
    plt.title(f"BS Units and Units within {D_c} Units Distance")
    plt.xlabel("X Position")
    plt.ylabel("Y Position")
    plt.legend(loc="upper right")
    plt.grid(True)
    plt.show()

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


U6_START = 6.5
U6_END = 7.2

class Database:
    def __init__(self):
        self.database = {}
        self.wifi_freq_range = (U6_START, ((U6_END-U6_START)*0.50 + U6_START))
        self.cellular_freq_range = (((U6_END-U6_START)*0.50 + U6_START), U6_END)
        self.request_queue = queue.Queue() 
        self.wifi_ptr = self.wifi_freq_range[0] # if < D_w
        self.cellular_ptr = self.cellular_freq_range[0] # if < D_w

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
            hs_count = 5  #10
            bs_count = 3 #5
        elif pop_density == 1:
            hs_count = 4   #5
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

# plot_units()

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

print("Group Dictionary:", len(group_dict))
print("Group Frequency Dictionary:", len(group_freq_dict))
for gid, members in group_members_dict.items():
    print(f"Group {gid} has {len(members)} units")



#TODO: add print statements to make sure this is working 

"""
STEP 6: Allocate spectrum according to the rules for HS and BS based on distance 
"""
# TODO: Swati
def allocate_spectrum(unit, bandwidth):
    unit.congested = False

    if len(group_dict[unit.id]) > 0:
        if unit.unit_type == UnitType.HS:
            # find the group ID 
            # index the group frequency dict to add to the total frequency allocated to the group
             # check if its less than the total bandwidth allocation
                # if yes, allocate the bandwidth
            # if no, then use ratios 
                # if unit requests x, assign it x/total_freq * total_bandwidth
            # unit.limit = round((db.wifi_freq_range[1]-db.wifi_freq_range[0])/(len(group_dict[unit.id])+1), 5)

            groupID = db.database[unit.id].group_id
            total_freq_allocated = group_freq_dict.get(groupID, 0)
            if total_freq_allocated == 0:
                group_freq_dict[groupID] = 0

            if (bandwidth+total_freq_allocated) <= (db.wifi_freq_range[1]-db.wifi_freq_range[0]):
                unit.bandwidth = bandwidth
                group_freq_dict[groupID] += bandwidth

            else: 
                unit.bandwidth = bandwidth / (total_freq_allocated + bandwidth) * (db.wifi_freq_range[1]-db.wifi_freq_range[0])
                # reallocating the other unit's bandwidths
                for member in group_members_dict[unit.group_id]:
                    member_unit = db.database[member]
                    member_unit.bandwidth = member_unit.bandwidth / (total_freq_allocated + bandwidth) * (db.wifi_freq_range[1]-db.wifi_freq_range[0])
                
                unit.congested = True

        elif unit.unit_type == UnitType.BS:
            unit.limit = round((db.cellular_freq_range[1]-db.cellular_freq_range[0]) /(len(group_dict[unit.id])+1), 5)
            groupID = db.database[unit.id].group_id
            total_freq_allocated = group_freq_dict[groupID]

            if (bandwidth+total_freq_allocated) <= (db.cellular_freq_range[1]-db.cellular_freq_range[0]):
                unit.bandwidth = bandwidth
                group_freq_dict[groupID] += bandwidth

            else: 
                unit.bandwidth = bandwidth / (total_freq_allocated + bandwidth) * (db.cellular_freq_range[1]-db.cellular_freq_range[0])
                # reallocating the other unit's bandwidths
                for member in group_members_dict[unit.group_id]:
                    member_unit = db.database[member]
                    member_unit.bandwidth = member_unit.bandwidth / (total_freq_allocated + bandwidth) * (db.cellular_freq_range[1]-db.cellular_freq_range[0])
                
                unit.congested = True
            
            
    else:
        if unit.unit_type == UnitType.HS:
            unit.bandwidth = (db.wifi_freq_range[1]-db.wifi_freq_range[0])
            # unit.frequency_bands.add(db.wifi_freq_range)
        else:
            unit.bandwidth = (db.cellular_freq_range[1]-db.cellular_freq_range[0])
            # unit.frequency_bands.add(db.cellular_freq_range)
        unit.limit = round((db.cellular_freq_range[1]-db.cellular_freq_range[0]), 3) if unit.unit_type == UnitType.BS else round((db.wifi_freq_range[1]-db.wifi_freq_range[0]), 3)
        unit.congested = False

def print_database_state(db, group_dict):
    """
    Prints the current state of the database in a tabular format.
    """
    header = f"\n\n\n{'ID':<5}{'Type':<10}{'Position':<15}{'Traffic Demand (Mbps)':<30}{'Bandwidth Allocated (MHz)':<45}{'Congested':<10}{'Density':<10}{'Limit':<10}{'Group Members':<20}"
    print(header)
    print("-" * len(header))

    for unit in db.database.values():
        group_str = ', '.join(map(str, group_dict.get(unit.id, [])))
        
        # First line with full info
        print(f"{unit.id:<5}{unit.unit_type.name:<10}{str(unit.position):<15}{unit.traffic_demand:<15}"
              f"{unit.bandwidth:<60}{str(unit.congested):<10}{unit.density:<10}{str(unit.limit):<10}{group_str:<20}")
    
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
    desired_bw = unit.traffic_demand * 2
    allocated_bw = unit.bandwidth
    assert(desired_bw > allocated_bw)
    unserviced_bw = desired_bw - allocated_bw
    unserviced_traffic_demand = unserviced_bw / 2
    return unserviced_traffic_demand
    
def generate_report(year):
    with open(report_file_path, "a") as f:
        f.write(f"\n\n\n=============================================================================\n")
        f.write(f"================================== Year {year} ==================================\n")
        f.write(f"=============================================================================\n")

        total_num_hs, num_congested_hs = 0, 0
        total_num_bs, num_congested_bs = 0, 0

        hs_congestion = {}
        bs_congestion = {}

        sum_desired_hs, sum_allocated_hs = 0, 0
        sum_desired_bs, sum_allocated_bs = 0, 0

        for unit in db.database.values():
            if unit.unit_type == UnitType.HS:
                total_num_hs += 1
                if unit.congested:
                    num_congested_hs += 1
                    hs_congestion[unit.id] = calc_unserviced_traffic_demand(unit)
                sum_desired_hs += unit.traffic_demand * 2
                sum_allocated_hs += unit.bandwidth

            elif unit.unit_type == UnitType.BS:
                total_num_bs += 1
                if unit.congested:
                    num_congested_bs += 1
                    bs_congestion[unit.id] = calc_unserviced_traffic_demand(unit)
                sum_desired_bs += unit.traffic_demand * 2
                sum_allocated_bs += unit.bandwidth
        
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
        f.write(f"\nAvg Unserviced Traffic Demand (Mbps) per Base Station: {avg_unserviced_traffic_demand_bs:.3f}\n")
        f.write(f"\nPercentage of Total Cellular Traffic Demand Met: {percent_traffic_demand_met_bs:.3f}%\n")

        # for unit_id in bs_congestion:
        #     x, y = db.database[unit_id].position
        #     f.write(f"Unit {unit_id} Pos {(x, y)}: {bs_congestion[unit_id]}\n")

        f.write(f"\n=============================================================================\n")
        f.write(f"=============================================================================\n")
        f.write(f"=============================================================================\n")

"""
STEP 7: Simulation loop 
"""
def simulate_dynamic_allocation():
    for year in range(3):
        print(f"\nStarting Year {year + 1}...\n")
        for day in range(3):
            print(f"\n  Starting Day {day + 1}...\n")
            for snapshot in range(2):
                print(f"    Snapshot {snapshot + 1}:")
                # print(f"db.wifi_freq_range: {db.wifi_freq_range}")
                # print(f"db.cellular_freq_range: {db.cellular_freq_range}")
                for unit in db.database.values():
                    unit.update_traffic_demand(snapshot)            
                    unit.make_request(db.request_queue)
                    # print(f"      Unit {unit.id}: Traffic Demand updated from {prev_demand} to {unit.traffic_demand}")
                # for hour in range(get_snapshot_duration(snapshot)):
                while not db.request_queue.empty():  
                    request = db.request_queue.get()  
                    unit_id, bandwidth = request 
                    unit = db.database[unit_id]
                    # print(f"Request Queue: {list(db.request_queue.queue)}")
                    # print(f"Processing request for Unit {unit_id} requesting {bandwidth} Mbps spectrum.")
                    # print (db.wifi_freq_range, db.cellular_freq_range)
                    allocate_spectrum(unit, bandwidth)
                    # request processed
                    # db.request_queue.get()
                db.update_ratios(snapshot)
                print(f"    Updated spectrum allocation ratios for snapshot {snapshot + 1}.")
                print_database_state(db, group_dict)
           
    
        print(f"\nDatabase after Year {year + 1}, Day {day + 1}:\n")
        for unit in db.database.values():
            unit.traffic_demand *= 1.2
        
        generate_report(year)

if __name__ == "__main__":
    open(report_file_path, "w").close()
    simulate_dynamic_allocation()
    



#---------------------------- Alternate Functions -----------------------------#
'''
# Alternate function to assign groups using BFS

# visited = set()

# def assign_group():
#     for unit_id1, unit1 in db.database.items():
#         if unit1.unit_type == UnitType.BS:     
#             group_dict[unit_id1] = []
#             for unit_id2, unit2 in db.database.items():
#                 if (unit2.unit_type == UnitType.BS) and (unit_id1 == unit_id2):
#                     continue  
#                 distance = calculate_distance(unit1, unit2)
#                 if distance <= D_w:
#                     group_dict[unit_id1].append(unit_id2)
#         elif unit1.unit_type == UnitType.HS:     
#             group_dict[unit_id1] = []
#             for unit_id2, unit2 in db.database.items():
#                 if (unit2.unit_type == UnitType.HS) and (unit_id1 == unit_id2):
#                     continue  
#                 distance = calculate_distance(unit1, unit2)
#                 if distance <= D_c:
#                     group_dict[unit_id1].append(unit_id2)

def assign_group(unit_id, x, y):
    """Assigns a group ID to all units within D_w of the given unit."""
    global group_id_counter
    group_id_counter = 0
    queue = deque([(unit_id, x, y)])
    visited.add(unit_id)
    group_dict[unit_id] = group_id_counter
    db.database[unit_id].group_id = group_id_counter  # Update unit itself

    while queue:
        uid, ux, uy = queue.popleft()
        cell_x, cell_y = get_grid_cell(ux, uy, D_w)

        # Check this cell and 8 neighboring cells
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                neighbor_cell = (cell_x + dx, cell_y + dy)

                for neighbor_id in grid.get(neighbor_cell, []):
                    if neighbor_id not in visited:
                        nx, ny = db.database[neighbor_id].position
                        distance = math.sqrt((nx - ux) ** 2 + (ny - uy) ** 2)

                        if db.database[unit_id].unit_type == UnitType.HS:
                            if distance <= D_w:  # Within threshold
                                visited.add(neighbor_id)
                                group_dict[neighbor_id] = group_id_counter
                                db.database[neighbor_id].group_id = group_id_counter  # Update unit itself
                                queue.append((neighbor_id, nx, ny))
                        elif db.database[unit_id].unit_type == UnitType.BS:
                            if distance <= D_c:  # Within threshold
                                visited.add(neighbor_id)
                                group_dict[neighbor_id] = group_id_counter
                                db.database[neighbor_id].group_id = group_id_counter  # Update unit itself
                                queue.append((neighbor_id, nx, ny))

    group_id_counter += 1  # Move to next group
'''

