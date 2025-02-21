import numpy as np
import random

# Define Constants
GRID_SIZE = 100  
N_HOTSPOTS = 25  
N_BASE_STATIONS = 25  
TRAFFIC_RANGE = (10, 100)  # Mbps
FREQ_BANDS = {
    "Hotspot": (6.5, 6.89),
    "Base Station": (6.9, 7.2)
}
TIME_SNAPSHOTS = [f"Hour {i}" for i in range(24)]  # Every hour
COST_FACTORS = {"latency": 1, "power_usage": 1, "spectrum_efficiency": 1}

database = {
    "hotspots": [],
    "base_stations": [],
    "frequency_bands": {band: {"min": f[0], "max": f[1], "available": True} for band, f in FREQ_BANDS.items()}
}

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
        self.traffic_demand = random.randint(*TRAFFIC_RANGE)
    
    def connect_device(self):
        self.connected_devices += 1
    
    def disconnect_device(self):
        self.connected_devices = max(0, self.connected_devices - 1)
    
    def allocate_spectrum(self):
        #what is our threshold gonna be?
        if self.traffic_demand > 80: 
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
# TODO: Change coz this cant be random - locaiton ofbase stations cant change 
for i in range(N_BASE_STATIONS):
    x, y = random.randint(0, GRID_SIZE), random.randint(0, GRID_SIZE)
    radius = random.randint(5, 15)
    traffic_demand = random.randint(*TRAFFIC_RANGE)
    database["base_stations"].append(NetworkUnit(i, x, y, radius, traffic_demand, "Base Station"))


for snapshot in TIME_SNAPSHOTS:
    print(f"Time: {snapshot}")
    
    for unit in database["hotspots"] + database["base_stations"]:
        if random.random() < 0.2:
            unit.connect_device()
        if random.random() < 0.1:
            unit.disconnect_device()
        
        unit.update_demand()
        
        unit.allocate_spectrum()
        
        print(f"{unit.unit_type} {unit.id}: {unit.connected_devices} devices, Demand: {unit.traffic_demand} Mbps, Freq: {unit.frequency}, Status: {unit.status}")
    
    print("---")

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
