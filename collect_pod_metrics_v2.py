#!/usr/bin/env python3
import requests
import csv
import time
import tempfile
from datetime import datetime

# Configuration
DURATION = 600        # 10 minutes
INTERVAL = 30         # 30 seconds
PROM_URL = "http://localhost:9090"
UL_RATE = "50M"       # Constant uplink rate

# Temporary file for previous energy values
prev_energy_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', newline='')
prev_energy = {}

# --- Helper Functions ---

def prom_query(query):
    """Send a query to Prometheus and return a dict {pod: value}."""
    try:
        resp = requests.get(f"{PROM_URL}/api/v1/query", params={"query": query})
        data = resp.json()
        results = {}
        for item in data.get("data", {}).get("result", []):
            pod = item["metric"].get("pod") or item["metric"].get("pod_name")
            val = float(item["value"][1])
            if pod:
                results[pod] = val
        return results
    except Exception as e:
        print(f"[ERROR] Prometheus query failed: {e}")
        return {}

def init_prev_energy():
    """Initialize the previous energy values."""
    global prev_energy
    prev_energy = prom_query("sum by(pod_name) (kepler_container_joules_total)")
    for pod, energy in prev_energy.items():
        prev_energy_file.write(f"{pod},{energy}\n")
    prev_energy_file.flush()

def fetch_metrics():
    """Fetch and save CPU, memory, and energy metrics per pod."""
    global prev_energy
    timestamp = datetime.now().isoformat(timespec='seconds')

    # Fetch Prometheus metrics
    cpu_data = prom_query("node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate")
    mem_data = prom_query("sum by(namespace,pod) (node_namespace_pod_container:container_memory_working_set_bytes)")
    energy_data = prom_query("sum by(pod_name) (kepler_container_joules_total)")

    # Compute energy delta
    energy_delta = {}
    for pod, current_energy in energy_data.items():
        prev_val = prev_energy.get(pod, current_energy)
        delta = max(current_energy - prev_val, 0)
        energy_delta[pod] = delta
        prev_energy[pod] = current_energy

    # Merge and write per-pod CSVs
    for pod in cpu_data.keys():
        cpu_val = cpu_data.get(pod, 0)
        mem_val = mem_data.get(pod, 0)
        energy_val = energy_delta.get(pod, 0)
        filename = f"{pod}_metrics.csv"

        # Write header if file doesn't exist
        try:
            open(filename, 'x').write("timestamp,cpu_cores,memory_bytes,energy_joules,UL-Rate\n")
        except FileExistsError:
            pass

        # Append new line with UL-Rate field
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, cpu_val, mem_val, energy_val, UL_RATE])

    print(f"[{timestamp}] Metrics collected for {len(cpu_data)} pods.")

# --- Main Execution ---
def main():
    print("Initializing energy baseline...")
    init_prev_energy()

    end_time = time.time() + DURATION
    while time.time() < end_time:
        fetch_metrics()
        time.sleep(INTERVAL)

    print("Data collection finished. Check *_metrics.csv files per pod.")

if __name__ == "__main__":
    main()
