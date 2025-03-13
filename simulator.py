import numpy as np
import random
import queue

# Define Constants
U6_START = 6.5
U6_END = 7.2
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
        self.wifi_freq_range = (U6_START, (U6_END-U6_START)*50 + U6_START)
        self.cellular_freq_range = ((U6_END-U6_START)*50 + U6_START + 0.1, U6_END)
        self.allocated_bands = {
            "wifi": [],
            "cellular": []
        }
        self.request_queue = queue.Queue() 
        self.wifi_ptr = U6_START
        self.cellular_ptr = U6_END

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
            db.wifi_ratio = 50
        elif (snapshot == 1):
            db.wifi_ratio = 70
        elif (snapshot == 2):
            db.wifi_ratio = 30
        elif (snapshot == 3):
            db.wifi_ratio = 80
        elif (snapshot == 4):
            db.wifi_ratio = 40
        elif (snapshot == 5):
            db.wifi_ratio = 75
        
        wifi_end = U6_START + (U6_END - U6_START) * db.wifi_ratio
        self.wifi_freq_range = (U6_START, wifi_end)
        self.cellular_freq_range = (wifi_end + 0.1, U6_END)
        


class NetworkUnit:
    def __init__(self, id, x, y, radius, traffic_demand, unit_type):
        self.id = id
        self.x = x
        self.y = y
        self.radius = radius
        self.connected_devices = random.randint(1, 2)
        self.traffic_demand = traffic_demand # units = MHz
        self.frequency_bands = [] # list of tuples (start_freq, end_freq)
        self.power = 0
        self.status = "inactive"
        self.unit_type = unit_type # Hotspot or base station
    
    def update_demand(self, snapshot, hr):
        """
        Based on what hr it is, increase/decrease the demand
        TODO: rewrite this code to change the demand based on hour (24) instead of snapshot
            - demand can be increased/decreased by connecting/disconnecting devices (i.e. users, population density)
        """
        if (snapshot == 0):
            if self.unit_type == "Base Station":
                self.traffic_demand *= 0.5
            else:
                self.traffic_demand *= 0.5
        elif (snapshot == 1):
            if self.unit_type == "Base Station":
                self.traffic_demand *= 1.5
            else:
                self.traffic_demand *= 4
        elif (snapshot == 2):
            if self.unit_type == "Base Station":
                self.traffic_demand *= 2
            else:
                self.traffic_demand *= 0.5
        elif (snapshot == 3):
            if self.unit_type == "Base Station":
                self.traffic_demand *= 0.25
            else:
                self.traffic_demand *= 4
        elif (snapshot == 4):
            if self.unit_type == "Base Station":
                self.traffic_demand *= 2
            else:
                self.traffic_demand *= 0.5
        elif (snapshot == 5):
            if self.unit_type == "Base Station":
                self.traffic_demand *= 0.5
            else:
                self.traffic_demand *= 2
    
    def __repr__(self):
        return f"NetworkUnit(id={self.id}, type={self.unit_type}, freq={self.frequency}, status={self.status})"

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
            db_request_queue.push(self.id, required_bw)
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
                db_request_queue.push(self.id, required_bw - total_current_bw)
    
    def allocate_spectrum(self, spectrum, status, power):
        # TODO: need some way of passing in what freq band to allocate to myself from the DB
        print(f"Allocating spectrum for Unit {self.id}: Demand = {self.traffic_demand}")

        #  if amt requested < end - ptr - allocaf.frequency = spectrum

        # threshold = self.frequency * 2

        # if self.traffic_demand > threshold: 
        #    

        #     bw_required = self.traffic_demand / 2
            
        #     available_band = FREQ_BANDS[self.unit_type]
        #     self.frequency = random.uniform(*available_band)
        #     self.status = "active"
        #     self.power = random.uniform(1, 10)
        #     print(f"  --> Assigned Frequency: {self.frequency:.2f} MHz, Status: {self.status}")
        # else:
        #     self.frequency = None
        #     self.status = "inactive"
        #     self.power = 0
        #     print(f"  --> No spectrum allocated, Status: {self.status}")


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

     
def is_available_spectrum(req):
    # TODO: check indexing properly 
    if db.units[req[0]].unit_type == "Hotspot":
        if (db.wifi_ptr < (U6_END-U6_START)*50 + U6_START and 
            db.wifi_ptr > U6_START): # end of allocated wifi 
            return True
        else: 
            return False
        
    if db.units[req[0]].unit_type == "Base Station":
        if (db.cellular_ptr > (U6_END-U6_START)*50 + U6_START + 0.1 and
            db.cellular_ptr < U6_END) : # end of allocated cellular  
            return True
        else: 
            return False

# initially, all of 6.5-7.2GHz are free
# we reserve 50% for wifi units, and 50% for cell units
# every timestep t, we can allocate parts of this spectrum to requesting units
# we keep track of how much of wifi/cell we have allocated
# every large timestep T, we change the ratios of the reservations for wifi and cell 
#       according to current ratio of cell/wifi units using the allocated spectrum

# ---------------------------- Simulation -------------------------------- #

def hour_to_snapshot(hour):
    """
    Given an hour (0-23), returns the snapshot number.
    """
    if (0 <= hr and hr <= 7):
        return 0
    elif (8 <= hr and hr <= 11):
        return 1
    elif (12 <= hr and hr <= 14):
        return 2
    elif (15 <= hr and hr <= 16):
        return 3
    elif (17 <= hr and hr <= 18):
        return 4
    elif (19 <= hr and hr <= 23):
        return 5
    return None

for year in range(3):
    for day in range(365):
        # TODO: make a request every time the demand updates?
        # or only make a request if traffic demand is greater than the current threshold,
        # so some units will be underutilizing their spectrum.

        for hr in range(24):
            for unit in db.units.values():
                # # simulating random connections and disconnections
                # if random.random() < 0.00: #TODO
                #     unit.connected_devices += 1
                # if random.random() < 0.00: #TODO
                #     unit.connected_devices = max(0, unit.connected_devices - 1)
                
                # Step 1: Unit simulates device/population movement by updating traffic demand
                unit.update_demand(snapshot, hr)
                # Step 2: Unit sees if it needs more spectrum from the DB + makes a request if needed
                unit.make_request()



            # db.request_spectrum(unit.id, unit.traffic_demand / 10) ?? maybe delete this
            # Step 3: DB processes all requests from request queue for this hr
            # TODO: assignment of spectrum does not have to be contiguous
            #       assign wifi from the bottom up, cellular from the top down
            #   for each req in request_queue:
            #       check if DB can fulfill the unit's request (either partially or fully)
            #       call unit.allocate_spectrum(spectrum, status=congested) for unit if needed
                    # unit.allocate_spectrum(spectrum) spectrum = how much spectrum DB is giving to the unit
            #       update the unit's status in the DB
            
            # loop through all the requests in the rq queue 
            for request in db.request_queue():
                # if space available allocate the spectrum 
                if is_available_spectrum(): #TODO
                    request[0].allocate_spectrum(request[1]) # check - stored as a tuple with request as second term 
                    request[0].status = "active"
                else: 
                    request[0].status = "congested"
                    
                # request processed
                db.request_queue.pop()
                    

            # Step 4: DB re-reserves the portion of total spectrum for wifi vs cellular based on snapshot
            snapshot = hour_to_snapshot(hr)
            db.update_ratios(snapshot)
    
    # Step 5: increase data rate of each user by 20%

    print(f"\nDatabase after Year {year + 1}, Day {day + 1}:\n")
    for unit_id, unit in db.units.items():
        print(f"  Unit {unit_id:02d} | Type: {unit.unit_type:<10} | Devices: {unit.connected_devices:02d} | "
                f"Freq: {unit.frequency if unit.frequency else 'None':<8} | Status: {unit.status}")
        
    # Increase traffic demand for each unit
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