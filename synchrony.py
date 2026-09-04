import pandas as pd
import numpy as np
from scipy.stats import pearsonr



# Load preprocessed data
resampled_data = pd.read_csv("resampled_data.csv")
print(f"Loaded {len(resampled_data)} rows of resampled data")

window_size_seconds = 30  # seconds

synchrony_results = []

unique_pair_ids = sorted(resampled_data["pair_id"].unique())
phases_to_analyse = ["hapticsON_task", "hapticsOFF_task", "baseline"]

for pair_id in unique_pair_ids:
    pair_data = resampled_data[resampled_data["pair_id"] == pair_id]

    for phase in phases_to_analyse:
        # Filter data for Participant Alpha and Participant Bravo in this phase
        alpha_data = pair_data[(pair_data["participant"] == "Alpha") & (pair_data["phase"] == phase)].sort_values("time_s")
        bravo_data = pair_data[(pair_data["participant"] == "Bravo") & (pair_data["phase"] == phase)].sort_values("time_s")

        # Keep only the exact seconds where both participants have valid data
        shared_seconds = set(alpha_data["time_s"]) & set(bravo_data["time_s"])
        alpha_aligned = alpha_data[alpha_data["time_s"].isin(shared_seconds)].sort_values("time_s")
        bravo_aligned = bravo_data[bravo_data["time_s"].isin(shared_seconds)].sort_values("time_s")
       

        alpha_bpm_values = alpha_aligned["bpm"].values
        bravo_bpm_values = bravo_aligned["bpm"].values

        # Skip if there are not enough data points to fill at least one window
        if len(alpha_bpm_values) <= window_size_seconds:
            continue


        # Prewhiten: 
        alpha_bpm_changes = np.diff(alpha_bpm_values)
        bravo_bpm_changes = np.diff(bravo_bpm_values)

        # Slide the window and correlate
        window_correlations = []
        total_possible_windows = len(alpha_bpm_changes) - window_size_seconds +1

        for start_index in range(total_possible_windows):
            end_index = start_index + window_size_seconds

            # compute pearsons correlation within 30s
            pearson_r, p_value = pearsonr(alpha_bpm_changes[start_index:end_index],
                                        bravo_bpm_changes[start_index:end_index])
            window_correlations.append(pearson_r)

        # average pearson r values across all windows to get single synchrony score
        mean_synchrony = np.mean(window_correlations)

        synchrony_results.append({
            "pair_id": pair_id,
            "phase": phase,
            "synchrony": mean_synchrony,
            "n_windows": len(window_correlations),
        })

synchrony_table = pd.DataFrame(synchrony_results)
print(synchrony_table)

# save for synchrony 
synchrony_table.to_csv("synchrony_data.csv", index=False)
print(f"Saved synchrony data to synchrony_data.csv")