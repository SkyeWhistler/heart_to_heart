
import asyncio as aio
import random
import time

async def simulated_producer(participant_tag, hrqueue, quit_event,  duration=60):
    print(f"[SIMULATOR] Starting data stream for Participant: {participant_tag}")

    # record starting timestamp
    start_time = time.time()
    # run until 'q' is pressed session durion epxires 
    while not quit_event.is_set():

        elapsed_time = time.time() - start_time
        if elapsed_time >= duration:
            break

        # generate heart rate numbers
        fake_bpm = random.randint(65, 85)
        fake_rr = random.randint(700, 950)
        current_nanoseconds = time.time_ns()
        
        # Exact BleakHeart unpacked tuple format: ('HR', tstamp, (bpm, rr_interval), energy)
        fake_frame = ('HR', current_nanoseconds, (fake_bpm, fake_rr), None)

        
        # Put into the shared queue safely
        hrqueue.put_nowait((participant_tag, fake_frame))
        
        # Stream at approximately 1 Hz
        await aio.sleep(1.0)
        
    print(f"[SIMULATOR] Stream for {participant_tag} finished.")
    await hrqueue.put('END') 