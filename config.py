
# Origin is top-left
D_w = 3  
D_c = 2.2

NUM_YEARS = 1
NUM_DAYS = 30

traffic_demand_bounds = {
    0: (100, 200),
    1: (201, 300),
    2: (301, 400)
}

# Different modes of spectrum allocation
# Static: Fixed allocation of spectrum to each user
# Dynamic: Spectrum allocation changes based on demand
MODE = "Static_Range" 

spectrum_split = 0
