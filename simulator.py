import random

class BaseStation:
    def __init__(self, id, freq_band):
        self.id = id
        self.freq_band = freq_band
        self.devices = []

    def allocate_devices(self, num_devices):
        self.devices = ["Cell" for _ in range(num_devices)]

    def request_spectrum(self, db):
        return db.assign_freq_band(self, sum(db.cell_traffic_per_hour for _ in self.devices))

class Hotspot:
    def __init__(self, id, freq_band):
        self.id = id
        self.freq_band = freq_band
        self.devices = []

    def allocate_devices(self, num_devices):
        self.devices = ["WiFi" for _ in range(num_devices)]

    def request_spectrum(self, db):
        return db.assign_freq_band(self, sum(25 for _ in self.devices))

class NetworkDatabase:
    def __init__(self):
        self.freq_band_capacity = {"Low": 500, "Medium": 1000, "High": 2000}
        self.cell_traffic_per_hour = 50
        self.efficient_network_traffic = 5000

    def assign_freq_band(self, node, projected_traffic):
        for band, capacity in sorted(self.freq_band_capacity.items(), key=lambda x: x[1]):
            if projected_traffic <= capacity:
                node.freq_band = band
                return
        node.freq_band = node.freq_band  # No upgrade available

    def calculate_performance_degradation(self, total_traffic):
        return max(0, total_traffic - self.efficient_network_traffic)

class NetworkSimulator:
    def __init__(self, num_base_stations, num_hotspots):
        self.db = NetworkDatabase()
        self.base_stations = [BaseStation(i, "Low") for i in range(num_base_stations)]
        self.hotspots = [Hotspot(i, "Low") for i in range(num_hotspots)]
        self.time_intervals = {
            (8, 12): (0.7, 0.3),
            (12, 15): (0.3, 0.7),
            (15, 17): (0.8, 0.2),
            (17, 19): (0.4, 0.6),
            (19, 24): (0.75, 0.25),
            (0, 8): (0.5, 0.5)
        }
    
    def get_time_ratio(self, t):
        for (start, end), ratio in self.time_intervals.items():
            if start <= t < end:
                return ratio
        return (0.5, 0.5)
    
    def run(self):
        for t in range(1, 25):
            wifi_ratio, cell_ratio = self.get_time_ratio(t)
            max_capacity = 1000 if (0 <= t < 8) else 2000
            total_devices = int(max_capacity / (wifi_ratio * 25 + cell_ratio * self.db.cell_traffic_per_hour))
            wifi_devices = int(total_devices * wifi_ratio)
            cell_devices = int(total_devices * cell_ratio)
            
            for bs in self.base_stations:
                bs.allocate_devices(cell_devices // len(self.base_stations))
                bs.request_spectrum(self.db)
                
            for hs in self.hotspots:
                hs.allocate_devices(wifi_devices // len(self.hotspots))
                hs.request_spectrum(self.db)
                
            total_traffic = sum(bs.request_spectrum(self.db) for bs in self.base_stations)
            total_traffic += sum(hs.request_spectrum(self.db) for hs in self.hotspots)
            
            degradation = self.db.calculate_performance_degradation(total_traffic)
            print(f"Hour {t}: Traffic = {total_traffic} Mbps, Degradation = {degradation} Mbps")

# Run the simulator
sim = NetworkSimulator(num_base_stations=random.randint(1, 100), num_hotspots=random.randint(1, 10))
sim.run()
