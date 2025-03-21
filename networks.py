import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from scipy.spatial.distance import cdist
import random
from enum import Enum
import queue
from collections import defaultdict
import math


# Origin is top-left
# D_w, D_c = 10, 25

'''
Available spectrum decreases if the distance is less than D_w/ D_c, with a halving of spectrum as distance approaches zero. (TODO)
'''


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
    """
    # For every unit in the db, if group_id == None allocate the entire spectrum 
    # else
    # TODO: Nicole
    def calculate_traffic_demand(self, snapshot):
        # do the per 4 hours logic 
        pass


    def update_traffic_demand(self, snapshot):
        self.traffic_demand = self.calculate_traffic_demand(snapshot, self.density)
        pass


    """
    STEP 5: 
    """
    def make_request(self, db_request_queue):
        """
        Makes a request to DB for more spectrum if needed, based on current traffic demand.

        Pseudocode:
            for each band allocated to the unit:
                calculate the traffic capacity of the band
                add to total traffic capacity for the unit
            
            if curren_traffic_demand > total_traffic_capacity for the unit:
                make a request to the db for the additional spectrum needed
        
        Formula: 
            required_bw = traffic_demand (MHz) * 2 bits/Hz = 2*traffic_demand Mbps
        """
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
                db_request_queue.put((self.id, required_bw - total_current_bw))


# TODO: Swati: Ask what the halving logic is 
def assign_limits():
    for unit_id in db.database:
        pass
    # Available spectrum decreases if the distance is less than D_w/ D_c, with a halving of spectrum as distance approaches zero.
    pass

"""
STEP 1: Create dat "map"!
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
        self.wifi_freq_range = (U6_START, (U6_END-U6_START)*50 + U6_START)
        self.cellular_freq_range = ((U6_END-U6_START)*50 + U6_START + 0.1, U6_END)
        self.request_queue = queue.Queue() 
        self.wifi_ptr = U6_START # if < D_w
        self.cellular_ptr = U6_END # if < D_w

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
        
        wifi_end = U6_START + (U6_END - U6_START) * wifi_ratio
        self.wifi_freq_range = (U6_START, wifi_end)
        self.cellular_freq_range = (wifi_end + 0.1, U6_END)
        

"""
STEP 2: Placing BS and HS 
"""
db = Database()
unit_id = 0

for x in range(city_size[0]):
    for y in range(city_size[1]):
        pop_density = population_density[x, y]
        traffic_demand = 0
        #setting the number of hs and bs acc to density [TODO]
        if pop_density == 2:
            hs_count = 10
            bs_count = 5
            # traffic_demand = random.randint(2000, 5000)
        elif pop_density == 1:
            hs_count = 5
            bs_count = 2
            # traffic_demand = random.randint(200, 500)
        else:
            hs_count = 3
            bs_count = 1
            # traffic_demand = random.randint(20, 50)

        # TODO: Nicole
        for i in range (hs_count):
            # x_pos = random.randint(___, ___) for region x, y
            # y_pos = random.randint(___, ___) for region x, y
            # no 2 units can have the same coords 
            db.database[unit_id] = NetworkUnit(unit_id, (x_pos, y_pos), traffic_demand, UnitType.HS, pop_density) 
            unit_id += 1


        for i in range (bs_count):
            # x_pos = random.randint(___, ___) for region x, y
            # y_pos = random.randint(___, ___) for region x, y
            # no 2 units can have the same coords 
            db.database[unit_id] = NetworkUnit(unit_id, (x_pos, y_pos), traffic_demand, UnitType.BS, pop_density) 
            unit_id += 1


"""
STEP 3: Make a group dictionary 
"""
# Maps group_id to a list of unit id 
# every unit in the list is within D_w/ D_c of each other 
#  BFS-style flood fill 

D_w = 10  # Distance threshold
D_c = 25
group_dict = {}  # Stores unit_id -> group_id mapping
grid = defaultdict(set)  # Spatial hash map (grid-based indexing)
group_id = 0  # Counter for group IDs

def get_grid_cell(x, y, cell_size):
    """Returns the grid cell coordinates for a given position."""
    return (x // cell_size, y // cell_size)

# Step 1: Populate the spatial grid
for unit_id in db.database.items():
    unit = db.database[unit_id]
    x, y = unit.position
    cell = get_grid_cell(x, y, D_w)
    grid[cell].add(unit_id)

# Step 2: Group units by checking only nearby grid cells
visited = set()

def assign_group(unit_id, x, y):
    """Assigns a group ID to all units within D_w of the given unit."""
    global group_id_counter
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

# Step 3: Process all units and assign groups
for unit_id, unit in db.database.items():
    if unit_id not in visited:
        assign_group(unit_id, unit.position[0], unit.position[1])
#TODO: add print statements to make sure this is working 

"""
STEP 6: Allocate spectrum according to the rules for HS and BS based on distance 
"""
# TODO: Swati
def allocate_spectrum():
    # loop through database for each unit 
    for unit_id in db.database:
        unit = db.database[unit_id]
        if unit.group_id != None:
            # ptr logic 
            # make sure it is within limit for each unit  
            pass
        else:
            unit.frequency_bands = db.wifi_freq_range
        # update unit.congestion

    # if unit.unit_type == "Hotspot":
    #     start_freq = db.wifi_ptr
    #     end_freq = start_freq + req

    #     if end_freq <= db.wifi_freq_range[1]:
    #         unit.frequency_bands.append((start_freq, end_freq)) 
    #         db.wifi_ptr = end_freq  
    #         unit.status = "active"  
    #         return True
        
    # elif unit.unit_type == "Base Station":
    #     start_freq = db.cellular_ptr - req
    #     end_freq = db.cellular_ptr

    #     if start_freq >= db.cellular_freq_range[0]:
    #         unit.frequency_bands.append((start_freq, end_freq))  
    #         db.cellular_ptr = start_freq 
    #         unit.status = "active" 
    #         return True 
        
    # print(f"Unable to allocate spectrum to Unit {unit}, status: congested.")    
    # unit.status = "congested" 
    # return False


"""
STEP 7: Simulation loop 
"""
# TODO: Nicole
def get_snapshot_duration(snapshot):
    match snapshot:
        case 0:
            pass 

    pass


def simulate_dynamic_allocation():
    for year in range(3):
        for day in range(365):
            for snapshot in range(6):
                for unit in db.database.values():
                    unit.update_traffic_demand(snapshot)            
                    unit.make_request(db.request_queue)

                for hour in get_snapshot_duration(snapshot):
                    while not db.request_queue.empty():  
                        request = db.request_queue.get()  
                        unit_id, bandwidth = request 
                        unit = db.units.get(unit_id)
                        print(f"Processing request for Unit {unit_id} requesting {bandwidth} Mbps spectrum.")
                        allocate_spectrum(unit, bandwidth) # check - stored as a tuple with request as second term 
                        # request processed
                        db.request_queue.get()
                db.update_ratios(snapshot)
    
        print(f"\nDatabase after Year {year + 1}, Day {day + 1}:\n")
        for unit in db.units.values():
            unit.traffic_demand *= 1.2
