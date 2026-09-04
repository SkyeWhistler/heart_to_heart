
import sys
import asyncio as aio
import csv
from datetime import datetime
from bleak import BleakScanner, BleakClient
from bleakheart import HeartRate, BatteryLevel

# Import simulated 2nd device, my early testing
from mock_sensor import simulated_producer

# HAPTICS: vibrations (haptics.py)
from haptics import Haptics

# Experiment Configuration
SIMULATE = False    # True = 1 real sensor + 1 mock; False = 2 real sensors
UNPACK = True            # Assign each heartbeat its own row
INSTANT_RATE = True      # Use raw RR-derived heart rate, not averaged
HEADER = ['participant', 'timestamp_ns', 'bpm', 'rr_interval_ms', 'phase']

# HAPTICS: 
# Crossover = each person feels their PARTNER, so an incoming HR is sent to the
# partner's device: Alpha's heartbeat -> Bravo's speaker, and vice versa.
ALPHA_CH = 0          # Alpha's speaker 
BRAVO_CH = 1        # Bravo's speaker 
PARTNER_DEVICE = {'Alpha': BRAVO_CH, 'Bravo': ALPHA_CH}


def collect_session_info():
    # Prompt me for a Dyad ID and generate a unique filename.


    print("\n------SESSION SETUP-------")
    user_input = input("Enter Dyad ID (e.g. dyad_01): ").strip()

    if user_input =="":
        user_input ="unknown_pair"

    # clean input
    clean_characters =[]
    for character in user_input:
        if character.isalnum() or character =="-" or character == "_":
            clean_characters.append(character)
        else:
            clean_characters.append("_")
       
    dyad_id = "".join(clean_characters)

    # timestamp
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
    # build CSV
    filename = f"data_{dyad_id}_{current_time}.csv"
    print(f"Data will be saved to: {filename}")

    return dyad_id, filename

async def check_battery(client, participant_tag):
    # Read and display the sensor's battery level before recording.

    # Warns me if battery is below 20%.

    level = await BatteryLevel(client).read()
    print(f"  {participant_tag} battery: {level}%")
    if level < 20:
        print(f"{participant_tag} battery is low")
    return level


def is_polar_device(dev, adv):
    # Return True if this BLE device is a Polar sensor.
    return dev.name and "polar" in dev.name.lower()


async def scan_for_sensors(expected=2, scan_time=10.0):
    # Scan for all nearby Polar devices and return them as a list.


    print(f"Scanning for {expected} Polar sensor(s) ({scan_time}s)...")
    all_devices = await BleakScanner.discover(timeout=scan_time)

    # Keep only devices with 'polar' in the name
    polar_devices = [d for d in all_devices if d.name and "polar" in d.name.lower()]

    for index, d in enumerate(polar_devices):
        print(f"  [{index}] {d.name} — {d.address}")

    if len(polar_devices) < expected:
        print(f"Found {len(polar_devices)} of {expected} sensors. Check Bluetooth and sensor power.")

    return polar_devices


async def csv_consumer(hrqueue, filename, session, expected_producers=2, haptics=None):
    # Consume heart rate data from the shared queue and write it to a CSV file.

    # Reads session["phase"] when writing each row,
    # The CSV reflects the phase that has been selected.
 

    print(f"Logging data to {filename}...")

    quit_signals_received = 0
    counts = {}  # Track how many samples per participant

    # Open file and keep it open for the duration
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)

        while True:
            item = await hrqueue.get()

            # Wait for all producer channels to send END
            if item == 'END':
                quit_signals_received += 1
                if quit_signals_received >= expected_producers:
                    break
                continue

            # Unpack tagged data — (participant_tag, frame)
            participant_tag, frame = item

            # Isolate the data from the BleakHeart tuple:
            # frame: ('HR', t_est, (bpm, rr), energy)
            t_est = frame[1]
            bpm = frame[2][0]
            rr = frame[2][1]
            phase = session["phase"]

            writer.writerow([participant_tag, t_est, bpm, rr, phase])
            print(f"  Recorded {participant_tag} | BPM: {bpm} | RR: {rr} | Phase: {phase}")

            # HAPTICS: 
            if haptics is not None and bpm:
                device_index = PARTNER_DEVICE.get(participant_tag)
                if device_index is not None:
                    haptics.set_bpm(device_index, bpm)

            # Update sample count for this participant
            counts[participant_tag] = counts.get(participant_tag, 0) + 1

            # Tell queue this entry is processed
            hrqueue.task_done()

    print("Logging complete for all channels. File closed.")
    return counts


async def run_ble_client(device, hrqueue, quit_event, participant_tag='Alpha'):
    # Connect to a Polar H10 sensor and stream heart rate data into the shared queue.



    def disconnected_callback(client):
        # Shutdown if the sensor loses connection unexpectedly
        print(f"\n Sensor {participant_tag} disconnected")
        quit_event.set()

    print(f"Connecting to {device.name} [{device.address}]...")

    async with BleakClient(device, disconnected_callback=disconnected_callback) as client:
        print(f"Connected to {participant_tag}: {client.is_connected}")

        # Check battery before recording
        await check_battery(client, participant_tag)

        # Override bleakheart callback to push to shared queue with a tag
        def tagged_callback(frame):
            hrqueue.put_nowait((participant_tag, frame))

        heartrate = HeartRate(
            client,
            queue=None,
            callback=tagged_callback,
            instant_rate=INSTANT_RATE,
            unpack=UNPACK
        )
        await heartrate.start_notify()

        # wait until quit_event is triggered (by keyboard or disconnection)
        await quit_event.wait()

        if client.is_connected:
            await heartrate.stop_notify()

        await hrqueue.put('END')


async def main():
    # Collect session info and generate unique filename
    dyad_id, filename = collect_session_info()

    #Shared state for phase tracking.
    session = {"phase": "baseline"}

    # HAPTICS:
    haptics = Haptics()

    #Shared communication channels
    quit_event = aio.Event()
    hrqueue = aio.Queue()

    # Discover sensor(s)
    if SIMULATE:
        # Practice mode: 1 real sensor + 1 simulated sensor
        print("Running in SIMULATE mode (1 real sensor + 1 mock)")
        device_alpha = await BleakScanner.find_device_by_filter(is_polar_device)
        if not device_alpha:
            print("Polar sensor not found. Ensure Bluetooth is enabled.")
            sys.exit(-4)
    else:
        # Real thing: 2 real sensors
        polar_devices = await scan_for_sensors(expected=2)
        if len(polar_devices) < 2:
            print("Could not find 2 Polar sensors. Exiting.")
            sys.exit(-4)
        alpha_index = int(input("Enter index for Alpha: ").strip())
        device_alpha = polar_devices[alpha_index]
        device_bravo = polar_devices[1 - alpha_index]

    #5: Register keyboard handler - phase configuration
    
    session["condition"] = None

    def set_phase(phase, note=""):
        session["phase"] = phase
        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n>> [{stamp}] phase -> {phase}   {note}")

    def keyboard_handler():
        command = sys.stdin.readline().strip().lower()
        if command == "b":
            session["condition"] = None
            haptics.off()
            set_phase("baseline")
        elif command == "h":
            session["condition"] = "hapticsON"
            haptics.on()            # participants feel their partner's heartbeat
            set_phase("hapticsON_settle", "[haptics ON]")
        elif command == "o":
            session["condition"] = "hapticsOFF"
            haptics.off()           # control round, no vibration
            set_phase("hapticsOFF_settle", "[haptics OFF]")
        elif command == "s":
            cond = session.get("condition") or "unknown"
            set_phase(f"{cond}_task", "PUZZLE START")
        elif command == "t":
            session["condition"] = None
            haptics.off()
            set_phase("transition")
        elif command == "q":
            haptics.off()
            print("\n>> Stopping recording")
            quit_event.set()

    loop = aio.get_running_loop()
    loop.add_reader(sys.stdin, keyboard_handler)
    print("\n>>> Controls:  b=Baseline | h=Haptics-ON round | o=haptics-Off round "
          "| s=puzzle Start | t=Transition rest | q=Quit <<<\n")

    #setting up concurrent tasks
   
    try:
        if SIMULATE:
            results = await aio.gather(
                run_ble_client(device_alpha, hrqueue, quit_event, participant_tag='Alpha'),
                simulated_producer('Bravo', hrqueue, quit_event, duration=1800),
                csv_consumer(hrqueue, filename, session, expected_producers=2, haptics=haptics)
            )
        else:
            results = await aio.gather(
                run_ble_client(device_alpha, hrqueue, quit_event, participant_tag='Alpha'),
                run_ble_client(device_bravo, hrqueue, quit_event, participant_tag='Bravo'),
                csv_consumer(hrqueue, filename, session, expected_producers=2, haptics=haptics)
            )
    finally:
        loop.remove_reader(sys.stdin)
        haptics.close()  #  stop the audio stream 

    #Print session summary

    counts = results[-1]
    print(f"\n-----SESSION COMPLETE-----")
    print(f"Dyad: {dyad_id}")
    print(f"File saved: {filename}")
    for tag, count in counts.items():
        print(f"  {tag} samples: {count}")
    print("------------------------------\n")


if __name__ == "__main__":
    aio.run(main())