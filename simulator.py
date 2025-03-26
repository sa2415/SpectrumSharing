import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from scipy.spatial.distance import cdist


"""
- Randomly create a "map" of a city that has different population densities so the traffic_demand 
can be proportional to the population. 
- Place BS and HS on the map according to this population density [Store in database]
    - Areas with high traffic_demand will have more number of BS and HS
    - store for every unit (every HS and BS):
        -  (x,y) coordinates
        -  traffic_demand
        -  status: congested or available 
        -  wifi/ cellular range assigned to it 


- Once "map" is initialized. Distribute the spectrum (6.2GHz to 7.1GHz)
    - Start off with a 50-50 split - 50% to wifi and 50% to BS 
    - Allocate spectrum according to split
        - HS
            - Each HS shares wi-fi spectrum with other HS's that are within distance D_w from that HS's location (use the x,y coordinates)
            - Amount of spectrum allocated to all HS's within distance D_w of point P combined cannot exceed the spectrum allocated to Wi-Fi at point P. 
                - otherwise if > D_w, then it can be allocated the same range of spectrum
            - D_w = 20m
        - BS 
            - Each BS shares cellular spectrum with other BS's that are within distance D_c from that BS's location (use the x,y coordinates)
            - amount of spectrum allocated to all BS's within distance D_c of point P combined cannot exceed the spectrum allocated to cellular at point P. 
                - otherwise if > D_c, then it can be allocated the same range of spectrum
            - D_c = 500m 

        - Available spectrum decreases if the distance is less than D_w/ D_c, with a halving of spectrum as distance approaches zero.

- At interval of 4 hours (= 1 snapshot), change the traffic_demand (according to time of day i.e. commute hours, work hours, shopping hours, lunch time etc.)
    - adjust the wifi/cellular frequency allocation at the beginning of every snapshot (based on prediction)
    - if a unit (BS or HS) is requesting more allocation within the 4 hours, put it in a request_queue
        - process queue at every hour + update the DB with this information 

- After 1 year, increase the population density by 20%
    - to see if the current allocation can still handle the traffic_demand 


PURPOSE: to see if a database (centralized system) for a city for dynamic frequency allocation to wifi and cellular is more efficient than static allocation

TODO: Understand the logic for congestion
    - Congested if more traffic_demand for a unit than a unit has been allocated ? 
    - put in better print statements to see if its working properly 
    - RIGHT NOW ITS PROBABLY BOGUS : TO BE DEBUGGED 
    - GAH NICOLE I RLLY DT THIS IS USEFUL IN ANY WAY

"""




"""
STEP 1: Create dat "map"!
"""

city_size = (10, 10)
np.random.seed(42) #to keep the initialization the same

#simulating a pop density: 0 = Low, 1 = Medium, 2 = High
population_density = np.random.choice([0, 1, 2], size=city_size, p=[0.3, 0.4, 0.3])

#TODO:  Mbps demand acc to density - DISCUSS
demand_map = {0: 500, 1: 2000, 2: 5000} 
traffic_demand = np.vectorize(demand_map.get)(population_density) #mapping the population density to the traffic demand

"""
STEP 2: Placing BS and HS 
"""
city_database = {} #initializing the db

#looping thru the matrix 
for x in range(city_size[0]):
    for y in range(city_size[1]):
        pop_density = population_density[x, y]
        #setting the number of hs and bs acc to density 
        if pop_density == 2:
            hs_count = 10
            bs_count = 5
        elif pop_density == 1:
            hs_count = 5
            bs_count = 2
        else:
            hs_count = 3
            bs_count = 1
        city_database[(x, y)] = {
            "traffic_demand": traffic_demand[x, y],
            "hs_count": hs_count,
            "bs_count": bs_count,
            "wifi_range": 0, 
            "cellular_range": 0,  
            "status": "available"
        }


"""
STEP 3: Initial 50-50 split and per unit even split 
"""
# Spectrum Allocation (6.2GHz to 7.1GHz -> 900 MHz total)
# TODO: gotta make it like previous version U6_START, U6_END
wifi_spectrum = 450  
cellular_spectrum = 450  
D_w, D_c = 20, 500  # WiFi and Cellular sharing distances

# Function to distribute spectrum dynamically 
# Assings wifi and cellular spectrum to each HS and BS at each location in the city
def allocate_spectrum():
    for (x, y), data in city_database.items():
        total_hs = data["hs_count"]
        total_bs = data["bs_count"]
        

        if total_hs > 0:
            data["wifi_range"] = wifi_spectrum / total_hs #TODO: currently evenly diving spectrum across all units - shld do acc to traffic demand?
        if total_bs > 0:
            data["cellular_range"] = cellular_spectrum / total_bs #TODO: currently evenly diving spectrum across all units - shld do acc to traffic demand?
        
        #for debuggign
        #print(f"Location ({x}, {y}) - WiFi Range: {data['wifi_range']} MHz, Cellular Range: {data['cellular_range']}")

# allocate_spectrum()

"""
STEP 4: Allocate spectrum according to the rules for HS and BS based on distance.
"""

# Calculate distance-based spectrum sharing - based on the email
# TODO: MAN IDK IF THIS IS RIGHT! 
def distance_based_sharing():
    hs_positions = [(x, y) for (x, y), data in city_database.items() if data["hs_count"] > 0]
    bs_positions = [(x, y) for (x, y), data in city_database.items() if data["bs_count"] > 0]
    
    # For each HS and BS, adjust spectrum allocation based on distance
    for (x, y), data in city_database.items():
        if data["hs_count"] > 0:
            distances = cdist([[(x, y)]], hs_positions)[0]
            for i, dist in enumerate(distances):
                if dist < D_w:
                    # Halving spectrum if distance is closer than D_w
                    data["wifi_range"] -= (wifi_spectrum / data["hs_count"]) * (1 - (dist / D_w)) 
        if data["bs_count"] > 0:
            distances = cdist([[(x, y)]], bs_positions)[0]
            for i, dist in enumerate(distances):
                if dist < D_c:
                    # Halve spectrum if distance is closer than D_c
                    data["cellular_range"] -= (cellular_spectrum / data["bs_count"]) * (1 - (dist / D_c))  # Decrease based on distance


"""
STEP 5: Congestion 
"""

# Simulating congestion detection
# is it meant to be this simple?? @nicole
def detect_congestion():
    for data in city_database.values():
        if data["traffic_demand"] > data["wifi_range"] and data["hs_count"] > 0:
            data["status"] = "congested"
        elif data["traffic_demand"] > data["cellular_range"] and data["bs_count"] > 0:
            data["status"] = "congested"
        else:
            data["status"] = "available"

# detect_congestion()



"""
STEP 6: @ every 4 hours, change the traffic demand and adjust spectrum allocation.
"""
def simulate_dynamic_allocation():
    congestion_levels_dynamic = []
    request_queue = deque()

    for hour in range(24):  # Simulate for 24 hours
        if hour % 4 == 0: #doing it every 4 hrs 

            if 6 <= hour < 9:  
                traffic_demand = np.vectorize(lambda x: x * 1.5 if x > 0 else x)(population_density) 
            elif 9 <= hour < 12: 
                traffic_demand = np.vectorize(lambda x: x * 1.2 if x > 0 else x)(population_density)  
            elif 12 <= hour < 14:  
                traffic_demand = np.vectorize(lambda x: x * 1.3 if x > 0 else x)(population_density) 
            elif 14 <= hour < 18:  
                traffic_demand = np.vectorize(lambda x: x * 1.1 if x > 0 else x)(population_density)  
            elif 18 <= hour < 20:  
                traffic_demand = np.vectorize(lambda x: x * 1.8 if x > 0 else x)(population_density) 
            else:  
                traffic_demand = np.vectorize(lambda x: x * 0.5 if x > 0 else x)(population_density)  
            
            # Apply updated traffic demand to city database
            for (x, y), data in city_database.items():
                data["traffic_demand"] = traffic_demand[x, y]
        
        congested_count = 0
        for (x, y), data in city_database.items():
            if data["status"] == "congested": # yea okay idt my congestion logic is correct 
                request_queue.append((x, y, "HS" if data["hs_count"] > 0 else "BS"))
                congested_count += 1
        
        # Process Requests every hour (as we discussed)
        process_requests(request_queue)
        congestion_levels_dynamic.append(congested_count)

    return congestion_levels_dynamic

# Dynamic Allocation Processing
def process_requests(request_queue):
    while request_queue:
        x, y, unit_type = request_queue.popleft()
        data = city_database[(x, y)]
        
        if unit_type == "HS" and wifi_spectrum >= 50:
            data["wifi_range"] += 50 #TODO: currently hardcoded to increase by 50 MHz - need to change
        elif unit_type == "BS" and cellular_spectrum >= 50:
            data["cellular_range"] += 50 #TODO: currently hardcoded to increase by 50 MHz - need to change

"""
STEP 7: Increase population density by 20% after 1 year
"""

def increase_population_density():
    global population_density
    population_density = np.clip(population_density * 1.2, 0, 2)  #From GPT
    for (x, y), data in city_database.items():
        pop_density = population_density[x, y]
        if pop_density == 2:
            data["hs_count"] = 10
            data["bs_count"] = 5
        elif pop_density == 1:
            data["hs_count"] = 5
            data["bs_count"] = 2
        else:
            data["hs_count"] = 3
            data["bs_count"] = 1


#TODO: put in a loop!

# Run the Simulation
allocate_spectrum()
distance_based_sharing()  
detect_congestion()
congestion_dynamic = simulate_dynamic_allocation()

# After 1 Year, increase population density
increase_population_density()
allocate_spectrum() 
distance_based_sharing()  
detect_congestion() 


# Plot Results
plt.figure(figsize=(10, 5))
plt.plot(range(24), congestion_dynamic, label="Dynamic Allocation", linestyle="-", marker="s")
plt.xlabel("Time of Day (Hours)")
plt.ylabel("Number of Congested Units")
plt.title("Dynamic Spectrum Allocation Performance")
plt.legend()
plt.grid(True)
plt.show()




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
    # Congestion = x more units needed - $$ ?
    print("Final Report:", report)
    return report