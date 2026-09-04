# did all my parcels arrive?
import pandas as pd
from pathlib import Path


data_directory = Path("experiment_data")

validation_results = []

for csv_file in sorted(data_directory.glob("data_*.csv")):
    # filename looks like
    filename_parts = csv_file.stem.split("_")
    pair_id = f"{filename_parts[1]}_{filename_parts[2]}"

    session_data = pd.read_csv(csv_file)

    for participant in ["Alpha", "Bravo"]:

        participant_data = session_data[session_data["participant"] == participant].sort_values("timestamp_ns")
        # Calculate how long the recording lasted in seconds
        first_timestamp_ns = participant_data["timestamp_ns"].min()
        last_timestamp_ns = participant_data["timestamp_ns"].max()
        recording_length_seconds = (last_timestamp_ns - first_timestamp_ns) / 1_000_000_000
        
        # calculate summed time accounted for by all rr intervals
        rr_intervals_ms = participant_data["rr_interval_ms"].values
        heartbeat_time_seconds = rr_intervals_ms[1:].sum() / 1_000

        # calculate data coverage and missing time
        coverage_percentage = (heartbeat_time_seconds / recording_length_seconds) * 100
        missing_time_seconds = recording_length_seconds - heartbeat_time_seconds


        #  artefact rejection
        bpm_ok = participant_data["bpm"].between(40, 160)
        valid = bpm_ok 
        rejected_beats_count = len(participant_data)-valid.sum()
        percent_rejected = (rejected_beats_count / len(participant_data)) * 100

        validation_results.append({
            "pair_id": pair_id,
            "participant": participant,
            "beats": len(participant_data),
            "coverage_percent": coverage_percentage,
            "missing_time_s": missing_time_seconds,
            "rejected": rejected_beats_count,
            "percent_rejected": percent_rejected,
        })


validation_summary = pd.DataFrame(validation_results)

print(validation_summary.round(2).to_string(index=False))

# overall figures 
total_beats = validation_summary["beats"].sum()
total_rejected = validation_summary["rejected"].sum()

print()
print(f"Mean coverage: {validation_summary['coverage_percent'].mean():.2f}%")
print(f"Mean missing time: {validation_summary['missing_time_s'].mean():.2f}s per recording")
print(f"Total beats: {total_beats}")
print(f"Rejected: {total_rejected} ({100 * total_rejected / total_beats:.2f}%)")

validation_summary.to_csv("validation_summary.csv", index=False)
print()
print("Saved validation_summary.csv")
