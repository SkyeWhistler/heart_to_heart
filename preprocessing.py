import pandas as pd
from pathlib import Path
import numpy as np



# load my data
data_directory = Path("experiment_data")

all_session_dataframes = []

for csv_file in sorted(data_directory.glob("data_*.csv")):
    filename_parts = csv_file.stem.split("_")        
    pair_id = f"{filename_parts[1]}_{filename_parts[2]}"

    session_dataframe = pd.read_csv(csv_file)
    session_dataframe["pair_id"] = pair_id

    all_session_dataframes.append(session_dataframe)

data = pd.concat(all_session_dataframes, ignore_index=True)
print(f"Loaded {len(all_session_dataframes)} sessions, {len(data)} rows")


# artefact rejection
bpm_ok = data["bpm"].between(40, 160)
valid = bpm_ok 

# keep track of what is removed
total_rows_before = len(data)
total_rejected_rows = total_rows_before - valid.sum()
percent_rejected = (total_rejected_rows / total_rows_before) * 100

print(f"\nRow counts per pair before filtering:\n{data.groupby('pair_id').size()}")
print(f"\nRejecting {total_rejected_rows} of {total_rows_before} rows ({percent_rejected:.1f}% artefact rejection rate)") #show percent of rejection 

# keep valid data
data = data[valid].reset_index(drop=True)


# resample to 1hz for analysis 

resampled_dataframes = []

for pair_id, pair_data in data.groupby("pair_id"):

    session_start_ns = pair_data["timestamp_ns"].min()
    pair_data = pair_data.copy()
    pair_data["time_seconds"] = (pair_data["timestamp_ns"] - session_start_ns) / 1000000000

    for participant in ["Alpha", "Bravo"]:
        participant_data = pair_data[pair_data["participant"] == participant].sort_values("time_seconds")

        # a regular time grid from first to last sample 
        first_second = int(participant_data["time_seconds"].min()) +1
        last_second = int(participant_data["time_seconds"].max())
        time_grid = np.arange(first_second, last_second)
                              
        # interpolate bpm on grid
        bpm_interpolated= np.interp(time_grid, participant_data["time_seconds"].values,
                                participant_data["bpm"].values)
        
        phase_on_grid = []
        for second in time_grid:
            rows_before_second = participant_data[participant_data["time_seconds"] <= second]
            active_phase = rows_before_second["phase"].values[-1]
            phase_on_grid.append(active_phase)


        resampled_dataframes.append(pd.DataFrame({
            "pair_id": pair_id,
            "participant": participant,
            "time_s": time_grid,
            "bpm": bpm_interpolated,
            "phase": phase_on_grid
        }))

resampled_data = pd.concat(resampled_dataframes, ignore_index = True)
print(f"resampled: {len(resampled_data)} rows")


# 4 per phase metrics

hr_summary = resampled_data.groupby(["pair_id", "participant", "phase"])["bpm"].mean().reset_index()
hr_summary = hr_summary.rename(columns={"bpm": "mean_hr"})
print(hr_summary)


# save for synchrony 
resampled_data.to_csv("resampled_data.csv", index=False)
print(f"Saved resampled data to resampled_data.csv")

