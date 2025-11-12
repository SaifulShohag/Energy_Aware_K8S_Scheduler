# ML_Integration_K8s_Scheduler

# Validation of ML Algorithms and Integration into Kubernetes Scheduler

**Telecom SudParis x Nokia Bell Labs - M2 CSN Project 2 (Oct 2025 - Feb 2026)**  
Authors: Md Saiful Islam, Grégoire Tournois 
Supervisors: Dr. Gopalasingham Aravinthan, Dr. Jérémie Leguay (Nokia Bell Labs), Prof. Natalia Kushik (Telecom SudParis)

---

## 1. Overview

Kubernetes’ default scheduler is performance-driven, focusing on CPU and memory availability rather than energy consumption.  
-> energy-efficient workload scheduling is our goal here

This project aims to:
1. Validate machine learning models trained on energy telemetry collected using group 1 results  
2. Integrate these models into the Kubernetes scheduler to enable energy-aware decision

goal is to see if we can achieve energy saving without a terrible tradeoff

---

## 2. Architecture Summary

- **Kepler**: Collects fine-grained power metrics per container or pod using eBPF and RAPL counters.  
- **MLflow**: Used for tracking experiments and hyperparameter tuning.   
- **Kubernetes Scheduler Plugin/Extender**: Integrates predictions into the node scoring process.  
- **Grafana + Prometheus**: Used for monitoring and validation.



## 3. Before running the pod metrics python scripts port-forward the prometheus service as below
- pip install requests
- sudo kubectl port-forward svc/prometheus-operated 9090:9090 -n monitoring
## 4. you can access prometheus dashboard 
  - 127.0.0.1:9090


---

## 3. TODO
- REDO  THE README
