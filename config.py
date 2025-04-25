
# Origin is top-left
# D_w, D_c = 10, 25
D_w = 3  
D_c = 2.2

NUM_YEARS = 10
NUM_DAYS = 3

traffic_demand_bounds = {
    0: (100, 200),
    1: (201, 300),
    2: (301, 400)
}

# Different modes of spectrum allocation
# Static: Fixed allocation of spectrum to each user
# Dynamic: Spectrum allocation changes based on demand
MODE = "Dynamic" 

spectrum_split = 10 