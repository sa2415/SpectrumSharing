import numpy as np
import random

# Define Constants
GRID_SIZE = 100  
N_HOTSPOTS = 2  
N_BASE_STATIONS = 2  
TRAFFIC_RANGE = (10, 100)  # Mbps #TODO change this?
FREQ_BANDS = { # TODO: get rid of this
    "Hotspot": (6.5, 6.89),
    "Base Station": (6.9, 7.2)
}

COST_FACTORS = {"latency": 1, "power_usage": 1, "spectrum_efficiency": 1}
N_YEARS = 5
FIXED_BASE_STATION_LOCATIONS = [(random.randint(0, GRID_SIZE), random.randint(0, GRID_SIZE)) for _ in range(N_BASE_STATIONS)]

# ------------------------------- Database ----------------------------------- #
class Database:
    def __init__(self):
        self.units = {}
        self.wifi_bw = 0  
        self.cellular_bw = 0  
        self.total_bw = 0.7 
        self.wifi_ratio = 50 
        self.cellular_ratio = 100 - self.wifi_ratio
        self.allocated_bands = {
            "wifi": [],
            "cellular": []
        }
        self.request_queue = [] #for later --> fragmentation 

    def request_spectrum(self, unit_id, bandwidth_needed):
        unit = self.units[unit_id]
        if "Hotspot" in unit.unit_type:
            unit_type = "wifi"
        else: 
            unit_type = "cellular"

        if unit_type == "wifi":
            available_bw = self.total_bw * self.wifi_ratio / 100
            allocated_bw = self.wifi_bw
        else:
            available_bw = self.total_bw * self.cellular_ratio / 100
            allocated_bw = self.cellular_bw

        remaining_bw = available_bw - allocated_bw

        #TODO: revise this logic 
        if bandwidth_needed <= remaining_bw:
            start_freq = 6.5 if unit_type == "wifi" else 6.9
            end_freq = start_freq + bandwidth_needed

            unit.frequency = (start_freq, end_freq) 
            self.allocated_bands[unit_type].append((unit_id, start_freq, end_freq))

            if unit_type == "wifi":
                self.wifi_bw += bandwidth_needed
            else:
                self.cellular_bw += bandwidth_needed

            unit.status = "active"
        else:
            unit.status = "congested"  



class NetworkUnit:
    def __init__(self, id, x, y, radius, traffic_demand, unit_type):
        self.id = id
        self.x = x
        self.y = y
        self.radius = radius
        self.connected_devices = random.randint(1, 2)
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
    
    def __repr__(self):
        return f"NetworkUnit(id={self.id}, type={self.unit_type}, freq={self.frequency}, status={self.status})"

    def allocate_spectrum(self):
        print(f"Allocating spectrum for Unit {self.id}: Demand = {self.traffic_demand}")
        #what is our threshold gonna be?
        # TODO [nicole]: how much traffic can a 100mHz/200mHz/x Hz spectrum band support?
        # using self.frequency, and calculate the threshold using formula
        if self.traffic_demand > 80: 
            # TODO [nicole]: calculate how much freq band (MHz) you need to accomodate self.traffic_demand 
            # using same formula but rearranged to solve for bandwidth
            # then assign this to self.frequency if available, otherwise the unit
            # will just be congested (in the same freq band but with too much traffic demand)
            available_band = FREQ_BANDS[self.unit_type]
            self.frequency = random.uniform(*available_band)
            self.status = "active"
            self.power = random.uniform(1, 10)
            print(f"  --> Assigned Frequency: {self.frequency:.2f} MHz, Status: {self.status}")
        else:
            self.frequency = None
            self.status = "inactive"
            self.power = 0
            print(f"  --> No spectrum allocated, Status: {self.status}")


# ---------------------------- Initialization -------------------------------- #
db = Database()
#creating the random initial hotspots 
for i in range(N_HOTSPOTS):
    x, y = random.randint(0, GRID_SIZE), random.randint(0, GRID_SIZE)
    radius = random.randint(5, 15)
    traffic_demand = random.randint(*TRAFFIC_RANGE)
    db.units[i] = NetworkUnit(i, x, y, radius, traffic_demand, "Hotspot")

#creating the random initial BS
# TODO [swati]: Change coz this cant be random - locaiton ofbase stations cant change 
for i, (x, y) in enumerate(FIXED_BASE_STATION_LOCATIONS, start=N_HOTSPOTS):
    radius = random.randint(5, 15)
    traffic_demand = random.randint(*TRAFFIC_RANGE)
    db.units[i] = NetworkUnit(i, x, y, radius, traffic_demand, "Base Station")

# initially, all of 6.5-7.2GHz are free
# we reserve 50% for wifi units, and 50% for cell units
# every timestep t, we can allocate parts of this spectrum to requesting units
# we keep track of how much of wifi/cell we have allocated
# every large timestep T, we change the ratios of the reservations for wifi and cell 
#       according to current ratio of cell/wifi units using the allocated spectrum

# ---------------------------- Simulation -------------------------------- #
for year in range(1):
    for day in range(365):
        for snapshot in range(24):
            for unit in db.units.values():
                # simulating random connections and diconnections
                if random.random() < 0.00: #TODO
                    unit.connected_devices += 1
                if random.random() < 0.00: #TODO
                    unit.connected_devices = max(0, unit.connected_devices - 1)
                unit.update_demand()
                db.request_spectrum(unit.id, unit.traffic_demand / 10)  
        unit.allocate_spectrum()  
    # break          
    print(f"\nDatabase after Year {year + 1}:\n")
    for unit_id, unit in db.units.items():
        print(f"  Unit {unit_id:02d} | Type: {unit.unit_type:<10} | Devices: {unit.connected_devices:02d} | "
              f"Freq: {unit.frequency if unit.frequency else 'None':<8} | Status: {unit.status}")
    for unit in db.units.values():
        unit.traffic_demand *= 1.2       


def generate_report():
    report = {
        "spectrum_allocation": {},
        "traffic_patterns": {},
        "performance_metrics": {}
    }
    for unit in db.units.values():
        report["spectrum_allocation"][unit.id] = unit.frequency
        report["traffic_patterns"][unit.id] = unit.traffic_demand
        report["performance_metrics"][unit.id] = {
            "latency": unit.traffic_demand / (unit.connected_devices or 1),
            "power_usage": unit.power,
            "spectrum_efficiency": unit.traffic_demand / (unit.frequency or 1)
        }
    print("Final Report:", report)
    return report
 
# final_report = generate_report()



# ------------------------------- NOTES ------------------------------------- #

# TODO [swati]: change format of DB
# {
#     id1: {type, Unit()}
#     id2: ...,
# }

# class Database:
#     def __init__(self):
#         self.database = {id: Unit(), ...}
#         self.wifi = ... # aggregate BW that wifi devices are using (MHz)
#         self.cellular = ...  # aggregate BW that wifi devices are using (MHz)
#         self.total_bw = 0.7 # Ghz
#         self.wifi_ratio = 50 #%
#         self.cellular_ratio = 50 #%

#         # needs to be kept in order
#         # after every insert, need to sort with band_start as key (O(n) insert)
#         self.allocated_bands = {
#             "wifi": [(id, band_start, band_end), ...],
#             "cellular": [(id, band_start, band_end), ...],
#         }

#         def insert_allocated_band(item):
#             id, band_start, band_end = item
#             # TODO: appends item onto self.allocated_bands in order
#             # ex.
#                 # append item onto self.allocated_bands
#                 # self.allocated_bands.sort(key=band_start) 
#             # or use linked list with in-order insertion
#             pass

#         def search_for_free_band(bandwidth):
#             # searches for a free band
#             pass


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

    #         for unit in database["hotspots"] + database["base_stations"]:
    #             if random.random() < 0.2:
    #                 unit.connect_device()
    #             if random.random() < 0.1:
    #                 unit.disconnect_device()
                
    #             unit.update_demand()
                
    #             unit.allocate_spectrum()
                
    #             print(f"{unit.unit_type} {unit.id}: {unit.connected_devices} devices, Demand: {unit.traffic_demand} Mbps, Freq: {unit.frequency}, Status: {unit.status}")
            
    #         print("---")

    # # increase device data usage by 20% each year
    # for hotspot in database["hotspots"]:
    #     hotspot.traffic_demand += 0.2 * hotspot.traffic_demand
    # for base_station in database["base_stations"]:
    #     base_station.traffic_demand += 0.2 * base_station.traffic_demand         