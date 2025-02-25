import numpy as np
import random

# Define Constants
GRID_SIZE = 100  
N_HOTSPOTS = 25  
N_BASE_STATIONS = 25  
TRAFFIC_RANGE = (10, 100)  # Mbps #TODO change this?
FREQ_BANDS = { # TODO: get rid of this
    "Hotspot": (6.5, 6.89),
    "Base Station": (6.9, 7.2)
}
# TIME_SNAPSHOTS = [f"Hour {i}" for i in range(24)]  # Every hour
COST_FACTORS = {"latency": 1, "power_usage": 1, "spectrum_efficiency": 1}
N_YEARS = 5


database = {
    "hotspots": [],
    "base_stations": [],
    "frequency_bands": {band: {"min": f[0], "max": f[1], "available": True} for band, f in FREQ_BANDS.items()}
}

# db = Database()
# db.wifi = ...

# TODO [swati]: change format of DB
# {
#     id1: {type, Unit()}
#     id2: ...,
# }
class Database:
    def __init__(self):
        self.database = {id: Unit(), ...}
        self.wifi = ... # aggregate BW that wifi devices are using (MHz)
        self.cellular = ...  # aggregate BW that wifi devices are using (MHz)
        self.total_bw = 0.7 # Ghz
        self.wifi_ratio = 50 #%
        self.cellular_ratio = 50 #%

        # needs to be kept in order
        # after every insert, need to sort with band_start as key (O(n) insert)
        self.allocated_bands = {
            "wifi": [(id, band_start, band_end), ...],
            "cellular": [(id, band_start, band_end), ...],
        }

        def insert_allocated_band(item):
            id, band_start, band_end = item
            # TODO: appends item onto self.allocated_bands in order
            # ex.
                # append item onto self.allocated_bands
                # self.allocated_bands.sort(key=band_start) 
            # or use linked list with in-order insertion
            pass

        def search_for_free_band(bandwidth):
            # searches for a free band
            pass


class NetworkUnit:
    def __init__(self, id, x, y, radius, traffic_demand, unit_type):
        self.id = id
        self.x = x
        self.y = y
        self.radius = radius
        self.connected_devices = random.randint(1, 10)
        self.traffic_demand = traffic_demand
        self.frequency = None
        self.power = 0
        self.status = "inactive"
        #Hotspot or base station
        self.unit_type = unit_type  
    
    def update_demand(self):
        # TODO [nicole]: based on what hr it is, increase/decrease the demand
        # keeping in mind what is the threshold
        self.traffic_demand = random.randint(*TRAFFIC_RANGE)
    
    def connect_device(self):
        self.connected_devices += 1
    
    def disconnect_device(self):
        self.connected_devices = max(0, self.connected_devices - 1)
    
    def allocate_spectrum(self):
        #what is our threshold gonna be?
        # TODO [nicole]: how much traffic can a 100mHz/200mHz/x Hz spectrum band support?
        # using self.frequency, and calculate the threshold using formula
        if self.traffic_demand > 80: 
            # TODO [nicole]: calculate how much freq band (MHz) you need to accomodate self.traffic_demand 
            # using same formula but rearranged to solve for bandwidth
            # then assign this to self.frequency if available, otherwise the unit
            # will just be congested (in the same freq band but with too much traffic demand)
            self.frequency = random.uniform(*FREQ_BANDS[self.unit_type])
            self.status = "active"
            self.power = random.uniform(1, 10)
        else:
            self.frequency = None
            self.status = "inactive"
            self.power = 0

#creating the random initial hotspots 
for i in range(N_HOTSPOTS):
    x, y = random.randint(0, GRID_SIZE), random.randint(0, GRID_SIZE)
    radius = random.randint(5, 15)
    traffic_demand = random.randint(*TRAFFIC_RANGE)
    database["hotspots"].append(NetworkUnit(i, x, y, radius, traffic_demand, "Hotspot"))

#creating the random initial BS
# TODO [swati]: Change coz this cant be random - locaiton ofbase stations cant change 
for i in range(N_BASE_STATIONS):
    x, y = random.randint(0, GRID_SIZE), random.randint(0, GRID_SIZE)
    radius = random.randint(5, 15)
    traffic_demand = random.randint(*TRAFFIC_RANGE)
    database["base_stations"].append(NetworkUnit(i, x, y, radius, traffic_demand, "Base Station"))

# initially, all of 6.5-7.2GHz are free
# we reserve 50% for wifi units, and 50% for cell units
# every timestep t, we can allocate parts of this spectrum to requesting units
# we keep track of how much of wifi/cell we have allocated
# every large timestep T, we change the ratios of the reservations for wifi and cell 
#       according to current ratio of cell/wifi units using the allocated spectrum

db = Database()

for year in range(N_YEARS):
    for day in range(365):
        for snapshot in range(24):
            print(f"Time: {snapshot}")

            #TODO: interference
            
            # TODO [swati]: instead of DB polling, unit should request more spectrum from DB and then DB tells it what to do
            # and then we update DB

            # for each unit
            #   you update_demand
            #   unit sees if it needs more spectrum
            #   if unit needs more spectrum, id is added to a global queue

            # while queue not empty:
            #   DB pops a request from the queue and accepts or denies based on current availability
            #       accept: update freq band of the unit, update DB self.wifi/self.cellular
            #       deny: keep freq band of unit the same, nothing in DB changes, mark unit as congested

            for unit in database["hotspots"] + database["base_stations"]:
                if random.random() < 0.2:
                    unit.connect_device()
                if random.random() < 0.1:
                    unit.disconnect_device()
                
                unit.update_demand()
                
                unit.allocate_spectrum()
                
                print(f"{unit.unit_type} {unit.id}: {unit.connected_devices} devices, Demand: {unit.traffic_demand} Mbps, Freq: {unit.frequency}, Status: {unit.status}")
            
            print("---")

    # increase device data usage by 20% each year
    for hotspot in database["hotspots"]:
        hotspot.traffic_demand += 0.2 * hotspot.traffic_demand
    for base_station in database["base_stations"]:
        base_station.traffic_demand += 0.2 * base_station.traffic_demand               


def generate_report():
    report = {
        "spectrum_allocation": {},
        "traffic_patterns": {},
        "performance_metrics": {}
    }
    for unit in database["hotspots"] + database["base_stations"]:
        report["spectrum_allocation"][unit.id] = unit.frequency
        report["traffic_patterns"][unit.id] = unit.traffic_demand
        report["performance_metrics"][unit.id] = {
            "latency": unit.traffic_demand / (unit.connected_devices or 1),
            "power_usage": unit.power,
            "spectrum_efficiency": unit.traffic_demand / (unit.frequency or 1)
        }
    print("Final Report:", report)
    return report

final_report = generate_report()
