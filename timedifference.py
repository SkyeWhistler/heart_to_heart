
# how evenly did heartbeat data arrive, steady stream or with many pauses ?
# clock drift?
from pathlib import Path
import pandas as pd

data_directory = Path("experiment_data")


all_mean_drift_values = []
all_delivery_jitter_values = []

for csv_file in sorted(data_directory.glob("data_*.csv")):
    session_dataframe = pd.read_csv(csv_file)
    

    for participant in ["Alpha", "Bravo"]:
        participant_data = session_dataframe[session_dataframe["participant"] == participant]
        # Calculate the arrival gap between consecutive packets (in ms)
        arrival_gap_ms = participant_data["timestamp_ns"].diff() / 1_000_000

        # Compare the arrival gap against the actual RR interval duration
        difference_from_expected = arrival_gap_ms - participant_data["rr_interval_ms"]

        # Calculate mean clock drift and delivery jitter (standard deviation)
        mean_drift_ms = difference_from_expected.mean()
        delivery_jitter_ms = difference_from_expected.std()

        all_mean_drift_values.append(mean_drift_ms)
        all_delivery_jitter_values.append(delivery_jitter_ms)

        print(f"{csv_file.name} ({participant}): Mean Drift = {mean_drift_ms:+.2f} ms | Jitter (SD) = {delivery_jitter_ms:.0f} ms")


        
overall_mean_drift = sum(all_mean_drift_values) / len(all_mean_drift_values)
overall_average_jitter = sum(all_delivery_jitter_values) / len(all_delivery_jitter_values)

print(f"\n average clock drift: {overall_mean_drift:.2f} ms")
print(f" average jitter: {overall_average_jitter:.0f} ms ")