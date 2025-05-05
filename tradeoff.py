# import os
# import re
# import matplotlib.pyplot as plt

# def parse_tradeoff_report(filepath):
#     with open(filepath, 'r') as file:
#         content = file.read()

#     # Split based on each Year 0 block
#     year_blocks = re.split(r'=+\n=+ Year 0 =+\n=+', content)
#     results = []

#     # Skip the first block entirely
#     for block in year_blocks[1:]:
#         match = re.search(
#             r'config\.spectrum_split: (\d+)%.*?'
#             r'Percentage of Total Wifi Traffic Demand Met: ([\d.]+)%.*?'
#             r'Percentage of Total Cellular Traffic Demand Met: ([\d.]+)%',
#             block,
#             re.DOTALL
#         )
#         if match:
#             split = int(match.group(1)) - 10  # Apply the -10 offset
#             wifi_met = float(match.group(2))
#             cellular_met = float(match.group(3))
#             results.append((split, wifi_met, cellular_met))

#     return results

# def plot_wifi_vs_cellular_demand_met(results):
#     splits = [split for split, _, _ in results]
#     wifi_met = [wifi for _, wifi, _ in results]
#     cellular_met = [cell for _, _, cell in results]

#     plt.figure(figsize=(8, 6))
#     plt.plot(wifi_met, cellular_met, marker='o', linestyle='-', color='teal')

#     for i in range(len(results)):
#         plt.text(wifi_met[i], cellular_met[i], f'{splits[i]}%', fontsize=8, ha='right', va='bottom')

#     plt.xlabel('Wi-Fi Demand Met (%)')
#     plt.ylabel('Cellular Demand Met (%)')
#     plt.title('Tradeoff: Wi-Fi vs Cellular Demand Met (Offset Split)')
#     plt.grid(True)

#     output_folder = 'outputs'
#     os.makedirs(output_folder, exist_ok=True)

#     plot_path = os.path.join(output_folder, 'wifi_vs_cellular_demand_met_offset.png')
#     plt.savefig(plot_path)
#     plt.close()
#     print(f'Plot saved to {plot_path}')

# # === Example Usage ===
# report_path = 'report.log'  # Change this to your actual .log file
# results = parse_tradeoff_report(report_path)
# plot_wifi_vs_cellular_demand_met(results)



import os
import matplotlib.pyplot as plt
import re

def plot_met_demand_from_log(log_file_path):
    with open(log_file_path, 'r') as file:
        log_data = file.read()

    blocks = re.split(r'=+\n=+ Year \d+ =+\n=+', log_data)[1:]  # Skip the first block
    results = []

    for block in blocks:
        split_match = re.search(r'config\.spectrum_split:\s+(\d+)%', block)
        wifi_match = re.search(r'Percentage of Total Wifi Traffic Demand Met:\s+([\d.]+)%', block)
        cell_match = re.search(r'Percentage of Total Cellular Traffic Demand Met:\s+([\d.]+)%', block)

        if split_match and wifi_match and cell_match:
            spectrum_split = int(split_match.group(1)) - 10  # Subtract 10
            if spectrum_split == -10:
                continue  # Skip the -10% (original 0%) data point
            wifi_met = float(wifi_match.group(1))
            cell_met = float(cell_match.group(1))
            results.append((wifi_met, cell_met))

    # Plotting
    wifi_vals = [x[0] for x in results]
    cell_vals = [x[1] for x in results]

    plt.figure(figsize=(8, 6))
    plt.plot(wifi_vals, cell_vals, marker='o', linestyle='-', color='blue')
    plt.xlabel('% Wi-Fi Demand Met')
    plt.ylabel('% Cellular Demand Met')
    plt.title('Wi-Fi vs Cellular Demand Met (Excluding -10% Split)')
    plt.grid(True)

    output_folder = 'outputs'
    os.makedirs(output_folder, exist_ok=True)
    plt.savefig(os.path.join(output_folder, 'wifi_vs_cellular_met.png'))
    plt.close()