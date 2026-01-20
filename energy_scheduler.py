#!/usr/bin/env python3
from flask import Flask, request, jsonify
import joblib
import pandas as pd
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Load the Brain
try:
    artifact = joblib.load('energy_model.pkl')
    model = artifact['model']
    encoder = artifact['encoder']
    type_stats = artifact['type_stats']
    logging.info("Model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load model: {e}")
    model = None

def get_pod_type(name):
    # Same logic as data collection
    name = name.lower()
    if any(x in name for x in ['srsran', 'gnb', 'ue']): return "RAN"
    if any(x in name for x in ['open5gs', 'amf', 'smf', 'upf']): return "5G_CORE"
    if 'mongo' in name: return "DATABASE"
    return "SYSTEM"

@app.route('/filter', methods=['POST'])
def filter():
    # We don't filter nodes (allow all), only prioritize them.
    data = request.json
    return jsonify({'nodes': data['nodes']})

@app.route('/prioritize', methods=['POST'])
def prioritize():
    data = request.json
    nodes = data['nodes']['items']
    pod = data['pod']
    pod_name = pod['metadata']['name']
    
    # 1. Identify Pod Features
    p_type = get_pod_type(pod_name)
    
    # Get Resource Requests (default to small if missing)
    try:
        reqs = pod['spec']['containers'][0]['resources']['requests']
        cpu_req = float(reqs.get('cpu', '100m').replace('m', '')) / 1000
        mem_req = float(reqs.get('memory', '128Mi').replace('Mi', '')) * 1024 * 1024
    except:
        cpu_req = 0.1
        mem_req = 128 * 1024 * 1024

    # Get Average Network Usage for this type (from Training stats)
    stats = type_stats.get(p_type, {'net_rx_bytes_sec': 0, 'net_tx_bytes_sec': 0})
    
    # Prepare Input for ML Model
    try:
        type_encoded = encoder.transform([p_type])[0]
    except:
        type_encoded = 0 # Default if unknown

    # Predict Energy Cost (Joules per 15s)
    features = [[cpu_req, mem_req, stats['net_rx_bytes_sec'], stats['net_tx_bytes_sec'], type_encoded]]
    predicted_energy = model.predict(features)[0]
    
    logging.info(f"Pod: {pod_name} ({p_type}) -> Predicted Impact: {predicted_energy:.2f} J")

    # 2. Score Nodes (0-100)
    # Strategy: We want to pack pods onto nodes to save energy (Consolidation)
    # OR distribute them to avoid thermal throttling.
    # Simple Strategy: Load Balance based on predicted efficiency.
    
    scored_nodes = []
    for node in nodes:
        node_name = node['metadata']['name']
        score = 100 # Default score
        
        # Here you could query Prometheus for current node temperature/load
        # For now, we give a preference to Workers over Master for RAN workloads
        if p_type == "RAN" and "worker" in node_name:
            score += 50
        elif p_type == "5G_CORE" and "master" in node_name:
            score += 50
            
        # Penalize by predicted energy (Higher energy cost = Lower score)
        # Normalized simple deduction
        score = max(0, score - int(predicted_energy / 100))
        
        scored_nodes.append({"host": node_name, "score": score})
        logging.info(f"Node: {node_name} -> Score: {score}")

    return jsonify({'scores': scored_nodes})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
