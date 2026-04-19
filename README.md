# 🍃 Energy-Aware Kubernetes Scheduler

[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.2x-blue.svg)](https://kubernetes.io/)
[![Go](https://img.shields.io/badge/Go-1.20+-00ADD8.svg)](https://golang.org/)
[![Kepler](https://img.shields.io/badge/Kepler-Energy_Monitoring-green.svg)](https://sustainable-computing.io/)
[![Academic Project](https://img.shields.io/badge/Research-Nokia_%7C_IP--Paris-red.svg)](https://www.ip-paris.fr/)

## 📌 Project Overview
The **Energy-Aware K8S Scheduler** is a custom Kubernetes scheduling plugin developed as part of a research initiative in collaboration with **Nokia**. 

Traditional Kubernetes schedulers prioritize resource availability (CPU/Memory) and workload distribution. However, in modern telecommunications and edge computing, energy efficiency is a critical metric. This project introduces a custom scheduler that integrates real-time node power consumption metrics to make intelligent, energy-efficient pod placement decisions without compromising the performance of high-demand 5G workloads.

## 🏗️ Architecture & Stack
This project leverages a multi-node Kubernetes cluster and a state-of-the-art observability stack to achieve energy-aware scheduling:

* **Orchestration:** Kubernetes (K8s), Docker / Containerd
* **Energy Metrics Exporter:** **Kepler** (Kubernetes-based Efficient Power Level Exporter) uses eBPF to capture granular power consumption data per node/pod.
* **Metrics Aggregation:** **Prometheus** scrapes and stores energy metrics from Kepler.
* **Custom Scheduler:** A custom K8s scheduler plugin (written in Go) queries Prometheus to evaluate the real-time energy efficiency of nodes and scores them accordingly.
* **Visualization:** **Grafana** dashboards are used to visualize cluster energy consumption and scheduler performance.
* **5G Workloads (Testbed):** The scheduler's efficiency is evaluated using containerized telecommunication workloads, specifically **srsRAN** (radio access network) and **Open5GS** (5G core network).

## 🚀 How It Works
1. **Metrics Collection:** Kepler monitors CPU, memory, and energy consumption across the multi-node cluster.
2. **Prometheus Integration:** The custom scheduler periodically fetches `node_energy_stat` queries from Prometheus.
3. **Scoring Phase:** During the Kubernetes scheduling cycle, the `Score` extension point is overridden. Nodes with lower current energy consumption or better predicted energy-to-compute ratios are given higher scores.
4. **Binding:** The Pod (e.g., a 5G core UPF component) is scheduled on the most energy-efficient node.

## 📂 Repository Structure
```text
Energy_Aware_K8S_Scheduler/
│
├── manifests/              # Kubernetes YAML files (deployments, RBAC, ConfigMaps)
│   ├── scheduler.yaml      # Deployment manifest for the custom scheduler
│   ├── kepler/             # Kepler daemonset deployment manifests
│   └── monitoring/         # Prometheus and Grafana setup
│
├── workloads/              # Telco workload manifests for testing
│   ├── open5gs/
│   └── srsran/
│
├── pkg/                    # Custom scheduler Go source code
│   └── energyscheduler/    # Scoring and filtering logic
│
├── dashboards/             # Exported Grafana JSON dashboards
├── go.mod                  # Go module dependencies
└── README.md               # Project documentation
````

## 🛠️ Prerequisites

  * A running Kubernetes cluster (kubeadm, Minikube, or Kind) - *Multi-node recommended for testing*.
  * `kubectl` configured to interact with your cluster.
  * **Prometheus** installed and running in the cluster.
  * **Kepler** deployed as a DaemonSet for power metrics.

## ⚙️ Installation & Setup

**1. Deploy the Monitoring Stack (Kepler + Prometheus):**

```bash
# Deploy Kepler
kubectl apply -k manifests/kepler/

# Deploy Prometheus and Grafana
kubectl apply -f manifests/monitoring/
```

**2. Deploy the Custom Scheduler:**
Build the custom scheduler image and deploy it to your cluster.

```bash
# Build the Docker image
docker build -t saifulshohag/energy-scheduler:v1 .

# Apply RBAC and Scheduler deployment
kubectl apply -f manifests/scheduler-rbac.yaml
kubectl apply -f manifests/scheduler.yaml
```

**3. Deploy 5G Workloads:**
To test the scheduler, deploy a workload and specify the `schedulerName` in the Pod spec.

```yaml
# Example snippet from workloads/open5gs/amf.yaml
spec:
  schedulerName: energy-aware-scheduler
  containers:
  ...
```

```bash
kubectl apply -f workloads/open5gs/
```

## 📊 Monitoring & Evaluation

Once the workloads are running, open Grafana (port-forward if necessary):

```bash
kubectl port-forward svc/grafana 3000:80 -n monitoring
```

Import the dashboard JSON files located in the `/dashboards` directory to view:

  * Total Cluster Power Consumption (Watts).
  * Power consumption per Node & per Pod.
  * Scheduler placement decisions vs. Node power states.

## 👤 Author

**Saiful Shohag** \* **LinkedIn:** [linkedin.com/in/saifeir990](https://www.google.com/search?q=https://linkedin.com/in/saifeir990)