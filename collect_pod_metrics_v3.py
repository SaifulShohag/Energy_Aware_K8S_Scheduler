#!/usr/bin/env python3
import requests
import csv
import time
import tempfile
from datetime import datetime

# Configuration
DURATION = 900        # 15 minutes (extended for better training data)
INTERVAL = 15         # 15 seconds (finer granularity)
PROM_URL = "http://localhost:9090"

# Temporary file for previous energy values (Kepler is a counter)
prev_energy_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', newline='')
prev_energy = {}

def get_pod_type(pod_name):
    """Categorize pods to help the ML model distinguish workload types."""
    name = pod_name.lower()
    if any(x in name for x in ['srsran', 'gnb', 'ue']):
        return "RAN"
    elif any(x in name for x in ['open5gs', 'amf', 'smf', 'upf', 'nrf', 'ausf', 'udm', 'pcf']):
        return "5G_CORE"
    elif 'mongo' in name:
        return "DATABASE"
    elif any(x in name for x in ['prometheus', 'grafana', 'kepler']):
        return "MONITORING"
    else:
        return "SYSTEM"

def prom_query(query):
    """Send a query to Prometheus and return a dict {pod: value}."""
    try:
        # We use a shorter range [30s] for rates to get instantaneous usage
        resp = requests.get(f"{PROM_URL}/api/v1/query", params={"query": query})
        data = resp.json()
        results = {}
        for item in data.get("data", {}).get("result", []):
            # Try to get pod name from 'pod' label, fallback to 'pod_name'
            pod = item["metric"].get("pod") or item["metric"].get("pod_name")
            if pod:
                results[pod] = float(item["value"][1])
        return results
    except Exception as e:
        print(f"[ERROR] Prometheus query failed: {e}")
        return {}

def init_prev_energy():
    """Initialize the previous energy values."""
    global prev_energy
    # Get current counter values
    prev_energy = prom_query("sum by(pod_name) (kepler_container_joules_total)")

def fetch_metrics():
    """Fetch and save CPU, memory, Network, and energy metrics per pod."""
    global prev_energy
    timestamp = datetime.now().isoformat(timespec='seconds')

    # --- 1. Define Queries ---
    # CPU (Cores)
    q_cpu = "sum by(pod) (irate(container_cpu_usage_seconds_total{image!=''}[30s]))"
    # Memory (Bytes)
    q_mem = "sum by(pod) (container_memory_working_set_bytes{image!=''})"
    # Network RX (Bytes/sec)
    q_net_rx = "sum by(pod) (irate(container_network_receive_bytes_total{image!=''}[30s]))"
    # Network TX (Bytes/sec)
    q_net_tx = "sum by(pod) (irate(container_network_transmit_bytes_total{image!=''}[30s]))"
    # Energy (Joules Counter)
    q_energy = "sum by(pod_name) (kepler_container_joules_total)"

    # --- 2. Execute Queries ---
    cpu_data = prom_query(q_cpu)
    mem_data = prom_query(q_mem)
    net_rx_data = prom_query(q_net_rx)
    net_tx_data = prom_query(q_net_tx)
    energy_data_raw = prom_query(q_energy)

    # --- 3. Compute Energy Delta (Joules used in last interval) ---
    energy_delta = {}
    for pod, current_joules in energy_data_raw.items():
        prev_joules = prev_energy.get(pod, current_joules)
        # Handle counter resets (if pod restarted, current < prev)
        if current_joules < prev_joules:
            delta = 0
        else:
            delta = current_joules - prev_joules
        
        energy_delta[pod] = delta
        prev_energy[pod] = current_joules

    # --- 4. Merge Data and Write CSVs ---
    # We iterate over CPU data as the 'master list' of active pods
    count = 0
    for pod in cpu_data.keys():
        # Skip pods with no energy data (Kepler might not track them yet)
        if pod not in energy_data_raw:
            continue

        row = {
            'timestamp': timestamp,
            'pod_type': get_pod_type(pod),
            'cpu_cores': cpu_data.get(pod, 0),
            'memory_bytes': mem_data.get(pod, 0),
            'net_rx_bytes_sec': net_rx_data.get(pod, 0),
            'net_tx_bytes_sec': net_tx_data.get(pod, 0),
            'energy_joules': energy_delta.get(pod, 0) # This is effectively Power (Watts * time)
        }
        
        filename = f"{pod}_metrics.csv"

        # Initialize file with header if missing
        try:
            with open(filename, 'x') as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()
        except FileExistsError:
            pass

        # Append Data
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)
        count += 1

    print(f"[{timestamp}] Metrics collected for {count} pods.")

def main():
    print("--- Starting Enhanced Data Collection (v3) ---")
    print(f"Duration: {DURATION}s | Interval: {INTERVAL}s")
    print("Initializing energy baseline...")
    init_prev_energy()
    time.sleep(1) # Small pause to let counters tick

    end_time = time.time() + DURATION
    try:
        while time.time() < end_time:
            fetch_metrics()
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nCollection stopped manually.")

    print("Data collection finished. Files updated.")

if __name__ == "__main__":
    main()
