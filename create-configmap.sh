#!/bin/bash
# Create a ConfigMap with your scheduler code and model
kubectl create configmap energy-scheduler-config -n kube-system \
  --from-file=energy_scheduler_extender.py \
  --from-file=corrected_energy_model.pkl \
  --dry-run=client -o yaml > configmap.yaml
