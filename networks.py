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

D_w = 10  # Distance threshold
D_c = 25

class UnitType(Enum):
    BS = 0
    HS = 1

class NetworkUnit:
    def __init__(self, id, position, traffic_demand, unit_type, density, limit=None):
        self.id = id
        self.position = position
        self.traffic_demand = traffic_demand # units = MHz
        self.frequency_bands = [] # list of tuples (start_freq, end_freq)
        self.congested = False
        self.unit_type = unit_type
        self.group_id = None
        self.density = density
        self.limit = limit

    """
    STEP 4: Updating traffic demand according to population density and time of day
    TODO: [Nicole] - acc to # of ppl, remove commuting hours 
                                          low         medium       high
    density = 0: [20, 50] MHz       --> [20,30],     [30,40],     [40,50]
    density = 1: [200, 500] MHz     --> [200,300],   [300,400],   [400,500]
    density = 2: [2000, 5000] MHz   --> [2000,3000], [3000,4000], [4000,5000]

    0:00 -  8:00 : low usage       (wifi:cell = 50:50)
    8:00 - 12:00 : high wifi usage (wifi:cell = 70:30)
    12:00 - 15:00 : high cell usage (wifi:cell = 30:70)
    15:00 - 17:00 : high wifi usage (wifi:cell = 80:20)
    17:00 - 19:00 : high cell usage (wifi:cell = 40:60)
    19:00 - 24:00 : high wifi usage (wifi:cell = 75:25)
    """
    def calculate_traffic_demand(self, snapshot):
        
        # pop density --> (lower, upper) traffic demand bound for the unit
        traffic_demand_bounds = {
            0: (20, 50),
            1: (200, 500),
            2: (2000, 5000)
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

        return random.randint(lower_bound, upper_bound)

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
        
        if len(self.frequency_bands) == 0:
            # make a request to DB using self.traffic_demand
            db_request_queue.put((self.id, required_bw))
        else:
            total_traffic_capacity = 0
            total_current_bw = 0
            for band in self.frequency_bands:
                band_bw = (band[1] - band[0]) * 1000 # multiply by 1000 to convert Ghz to MHz
                band_traffic_capacity = band_bw / 2
                total_current_bw += band_bw
                total_traffic_capacity += band_traffic_capacity
            
            if self.traffic_demand > total_traffic_capacity:
                # make a request to DB using excess traffic
                assert required_bw > total_current_bw, f"[NetworkUnit {self.id}][make_request]: Unit made a request to DB for more spectrum but required_bw <= total_current_bw."
                print(f"Unit {self.id} made a request to DB for more spectrum: {(required_bw - total_current_bw)/1000} Mbps")
                db_request_queue.put((self.id, required_bw - total_current_bw)) 



def total_frequency_allocated(unit):
    total = 0
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
        # self.wifi_bw = 0 # in GHz
        # self.cellular_bw = 0  # in GHz
        # self.total_bw = 0.7
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
block_size = 50
grid_size = 100

for i in range(city_size[0]):
    for j in range(city_size[1]):
        pop_density = population_density[i, j]
        traffic_demand = 0
        # setting the number of hs and bs acc to density [TODO]
        if pop_density == 2:
            hs_count = 2  #10
            bs_count = 1  #5
        elif pop_density == 1:
            hs_count = 0   #5
            bs_count = 0   #2
        else:
            hs_count = 0  #3
            bs_count = 0  #1

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


# Step 3: Process all units and assign groups
for unit_id in db.database.items():
    # if unit_id not in visited:
    assign_group()

#TODO: add print statements to make sure this is working 

"""
STEP 6: Allocate spectrum according to the rules for HS and BS based on distance 
"""
# TODO: Swati
def allocate_spectrum(unit, bandwidth):
    # TODO: once other function implemented: make sure it is within limit for each unit  
    if len(group_dict[unit.id]) > 0:
        if unit.unit_type == UnitType.HS:
            unit.limit = int((db.wifi_freq_range[1]-db.wifi_freq_range[0])/(len(group_dict[unit.id])+1))
            start_freq = db.wifi_ptr
            end_freq = None
            # check if the total frequency allocated to the unit is less than the limit
            # limit is defined by number of units in the group
            if total_frequency_allocated(unit) < unit.limit:
                # print(f"Unit {unit.id} allocated bandwidth: {bandwidth/1000}")
                end_freq = (start_freq) + bandwidth
            else:
                end_freq = None

            if (end_freq != None) and (end_freq <= db.wifi_freq_range[1]):
                db.wifi_ptr = (end_freq)
                unit.frequency_bands.append((start_freq, end_freq)) 
            else:
                unit.congested = True

        elif unit.unit_type == UnitType.BS:
            unit.limit = int((db.cellular_freq_range[1]-db.cellular_freq_range[0]) /(len(group_dict[unit.id])+1))
            start_freq = db.cellular_ptr
            end_freq = None

            if total_frequency_allocated(unit) < unit.limit:
                # print(f"Unit {unit.id} allocated bandwidth: {bandwidth/1000}")
                end_freq = start_freq + bandwidth
            else:
                end_freq = None

            if (end_freq != None) and end_freq <= db.cellular_freq_range[1]:
                db.cellular_ptr = (end_freq)
                unit.frequency_bands.append((start_freq, end_freq)) 
            else:
                unit.congested = True
    else:
        unit.frequency_bands = [db.wifi_freq_range] if unit.unit_type == UnitType.HS else [db.cellular_freq_range]
        unit.limit = int(db.cellular_freq_range[1]-db.cellular_freq_range[0]) if unit.unit_type == UnitType.BS else int(db.wifi_freq_range[1]-db.wifi_freq_range[0])
    unit.congested = False

def print_database_state(db, group_dict):
    """
    Prints the current state of the database in a tabular format.
    """
    header = f"{'ID':<5}{'Type':<10}{'Position':<15}{'Traffic Demand':<30}{'Bands Allocated':<45}{'Congested':<10}{'Density':<10}{'Limit':<10}{'Group Dict':<20}"
    print(header)
    print("-" * len(header))

    for unit in db.database.values():
        bands_list = [f"({start:.2f}-{end:.2f})" for (start, end) in unit.frequency_bands]
        
        # Split bands over multiple lines if too many
        max_bands_per_line = 4
        band_lines = [' '.join(bands_list[i:i+max_bands_per_line]) for i in range(0, len(bands_list), max_bands_per_line)]
        
        group_str = ', '.join(map(str, group_dict.get(unit.id, [])))
        
        # First line with full info
        print(f"{unit.id:<5}{unit.unit_type.name:<10}{str(unit.position):<15}{unit.traffic_demand:<15}"
              f"{band_lines[0] if band_lines else '':<60}{str(unit.congested):<10}{unit.density:<10}{str(unit.limit):<10}{group_str:<20}")
        
        # Additional lines for overflow bands (only print bands)
        for extra_line in band_lines[1:]:
            print(f"{'':<45}{extra_line:<60}")
    
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
                for unit in db.database.values():
                    unit.update_traffic_demand(snapshot)            
                    unit.make_request(db.request_queue)
                    # print(f"      Unit {unit.id}: Traffic Demand updated from {prev_demand} to {unit.traffic_demand}")

                for hour in range(get_snapshot_duration(snapshot)):
                    while not db.request_queue.empty():  
                        request = db.request_queue.get()  
                        unit_id, bandwidth = request 
                        unit = db.database[unit_id]
                        # print(f"Request Queue: {list(db.request_queue.queue)}")
                        # print("group_dict", group_dict)
                        # print(f"Processing request for Unit {unit_id} requesting {bandwidth} Mbps spectrum.")
                        # print (db.wifi_freq_range, db.cellular_freq_range)
                        allocate_spectrum(unit, bandwidth)
                        # request processed
                        # db.request_queue.get()
                db.update_ratios(snapshot)
                # print(f"    Updated spectrum allocation ratios for snapshot {snapshot + 1}.")
                print_database_state(db, group_dict)
           
    
        print(f"\nDatabase after Year {year + 1}, Day {day + 1}:\n")
        for unit in db.database.values():
            unit.traffic_demand *= 1.2


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

