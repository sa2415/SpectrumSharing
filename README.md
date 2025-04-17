# Dynamic Spectrum Allocation Simulator

This project simulates a dynamic spectrum allocation system across a city, modeling interactions between Wi-Fi hotspots (HS), cellular base stations (BS), and a centralized database. The system is designed to efficiently allocate upper 6 GHz band spectrum (6.5–7.2 GHz) based on traffic demand and population density over time.

---

## 🧠 Purpose

The goal of this simulator is to evaluate the efficiency of a **centralized database** approach for managing spectrum sharing between Wi-Fi and cellular networks in a growing city environment. The simulation tracks:

- Spectrum demand and usage  
- Device distribution (BS and HS)  
- Traffic fluctuations over time  
- Population growth and its effects  
- Efficiency metrics like spectral utilization and conflict resolution

---

## 🏗️ Project Structure
- networks.py 
- output.log 
- config.py (TODO)

---

## 🚀 How It Works

### 1. Grid Initialization

- The city is modeled as a 2D grid of `N x N` cells.
- Each cell is assigned a **population density level**:
  - `0`: Sparse  
  - `1`: Medium  
  - `2`: Dense

### 2. Traffic Demand Simulation

- Every 4 simulated hours, traffic demand is recalculated based on population density:
  - Density 0: 2–5 MHz  
  - Density 1: 10–40 MHz  
  - Density 2: 50–90 MHz

### 3. Device Placement

- **Wi-Fi hotspots (HS)** and **Base stations (BS)** are distributed across the grid.
- Their quantity per cell is determined by local demand and density.

### 4. Spectrum Allocation

- Spectrum is dynamically allocated between 6.5–7.2 GHz.
- Spectrum blocks are assigned according to:
  - Device type (Wi-Fi vs. Cellular)
  - Interference constraints (`D_w = 20m`, `D_c = 500m`)
  - Priority: Cellular gets preferential treatment when conflicts arise.
- A **centralized database** resolves conflicts and coordinates frequency reassignments.

### 5. Conflict Resolution & Queueing

- If a device can’t be allocated spectrum, it is added to a queue.
- The system periodically retries allocation from the queue.

### 6. Population Growth

- Over a year-long simulation, population increases by 20%.
- The simulator evaluates how the system copes with increasing traffic demands and population shifts.

### 7. Metrics and Visualization

- Key metrics include:
  - Spectrum utilization
  - Number of unallocated devices
  - Queue sizes
  - Total bandwidth served
- Results are plotted over time for analysis.

---

## 📦 Requirements

Make sure to install required Python libraries:

```bash 
pip install numpy matplotlib
```

---
## 🧪 Running the Simulation

To run the simulation, execute the following command in the root directory:

```bash
python main.py
```

You can edit simulation parameters inside config.py to customize:
	•	City grid size
	•	Simulation duration
	•	Traffic bounds per population density
	•	Growth rate and time-step frequency

---
## 🛠️ Configuration Options

You can adjust the simulation by editing config.py. Key options include:

| Parameter           | Description                                         | Example Value     |
|---------------------|-----------------------------------------------------|-------------------|
| `GRID_SIZE`         | Size of the simulated city (NxN grid)               | 50                |
| `SPECTRUM_RANGE`    | Frequency range for allocation (in GHz)             | (6.5, 7.2)        |
| `D_w`               | Wi-Fi interference distance                         | 20                |
| `D_c`               | Cellular interference distance                      | 500               |
| `SIMULATION_DAYS`   | Length of the simulation in days                    | 365               |
| `TIME_STEP_HOURS`   | Time interval between updates (in hours)            | 4                 |
| `TRAFFIC_BOUNDS`    | Demand range per density level                      | {0: (2,5), ...}   |
| `GROWTH_RATE`       | Annual city-wide population growth (%)              | 20                |
| `N_HS_PER_DENSITY`  | Initial HS count per density level                  | {0: 2, 1: 4, ...} |
| `N_BS_PER_DENSITY`  | Initial BS count per density level                  | {0: 1, 1: 2, ...} |
---

## 📈 Output

After running the simulation, the following plots and statistics are generated (typically saved or displayed based on your config):

- 📊 **Spectrum Utilization Over Time**  
  Visualizes the total bandwidth usage efficiency.

- 🌆 **Traffic Demand Heatmap**  
  Shows bandwidth demand across the city grid.


- 📉 **Unallocated Devices vs Time**  
  Tracks how many HS/BS couldn’t be assigned spectrum due to conflicts.

- 💡 **Total Bandwidth Served**  
  Measures overall spectrum allocation success over time.

---  

## 🧑‍💻 Authors

Built by students at **Carnegie Mellon University** as part of a dynamic spectrum access research project.  
For academic inquiries or contributions, please contact the project maintainers.
Swati Anshu - sanshu@andrew.cmu.edu
Nicole Feng - nvfeng@andrew.cmu.edu

