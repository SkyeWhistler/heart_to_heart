# Heart to Heart: Dual-Stream Physiological Synchrony Pipeline
An asynchronous Bluetooth Low Energy (BLE) pipeline for concurrent heart rate logging, real-time haptic feedback, and windowed cross-correlation analysis between paired participants.

## Description
This project provides an reusable software and experimental pipeline developed to investigate physiological synchrony and collaborative task performance. The system connects to two Polar H10 chest straps over Bluetooth Low Energy, asynchronously records RR-interval and heart rate data, and triggers real-time 90 Hz tactile pulses through bone-conduction transducers to deliver a partner's live heartbeat. 
The accompanying analysis pipeline handles physiological artefact filtering (40–160 BPM), 1 Hz linear resampling, first-differencing prewhitening, and 30-second windowed cross-correlation (WCC) to evaluate interpersonal cardiac coupling against collaborative puzzle task scores.

## Getting Started
### Dependencies
* **Operating System:** macOS 

* **Python Version:** Python 3.10 or higher.
* **Hardware Requirements (for live recording only):**
  * 2 × Polar H10 Heart Rate Monitors (with BLE support).
  * 2 × Bone-conduction / resonance vibration transducers (or stereo audio output).
* **Required Python Libraries:**
  * `numpy` (array handling and numerical difference calculations)
  * `pandas` (time-series alignment and data manipulation)
  * `scipy` (Pearson correlations and Wilcoxon statistical tests)
  * `matplotlib` (visualisation and figures)
  * `sounddevice` (multi-channel audio synthesis for haptic speakers)
  * `bleak` (asynchronous Bluetooth Low Energy communication)
  * `bleak-heart` (Bluetooth Low Energy library for decoding Polar H10 heart rate data)

  ### Installing
    * **Step 1: Open project directory:**
    
    cd ...
    
    * **Step 2: Install required packages:**
  
    pip install numpy pandas scipy matplotlib sounddevice bleak bleak-heart


### Executing program

Follow these steps in chronological order to record data, validate the hardware, and reproduce the statistical findings:

* **Step 1: Live Hardware Recording / Simulation**
  * To test the asynchronous queue without physical hardware using simulated data:

    python mock_sensor.py

  * To launch an interactive live recording session with dual Polar H10 sensors:

    python data_logger.py

  * *Output: Generates raw session CSV files in experiment_data

* **Step 2: Data Cleaning & 1 Hz Resampling**
  * Loads raw files from experiment_data/, applies 40–160 BPM artefact filtering, linearly resamples to 1 Hz, and aligns timestamps:

    python preprocessing.py

  * *Output: Generates resampled_data.csv.*

* **Step 3: Signal Validation & Hardware Timing Benchmarking**
  * Evaluates packet coverage, missing beat time, delivery jitter, and hardware clock drift:

    python validation.py
    python timedifference.py

  * *Output: Generates validation_summary.csv and prints timing metrics.*

* **Step 4: Physiological Synchrony Computation**
  * Applies first-differencing prewhitening and calculates 30-second windowed cross-correlations across all pairs:

    python synchrony.py

  * *Output: Generates synchrony_data.csv.*

* **Step 5: Statistical Analysis & Figures (Jupyter Notebooks)**
  * Open Jupyter Notebook to run the hypothesis tests and view dissertation plots:

    jupyter notebook

  * Open finalanlysis.ipynb for Wilcoxon signed-rank tests and Spearman correlation analyses.
  * Open synchrony_plots.ipynb for dual-stream time series, multi-pair synchrony over time, and window-size robustness tables.


## Help
* **Bluetooth Timeouts:** Ensure both Polar H10 sensors are moistened with water or conductive gel before wearing and disconnected from any other phones or apps.

# Authors
* **Skye Whistler**  
  MSc Computer Science, Queen Mary University of London  
  Supervisor: Dr. Fabrizio Smeraldi

## License
This project is submitted as part of the MSc Computer Science Dissertation at Queen Mary University of London.
