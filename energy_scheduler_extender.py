#!/usr/bin/env python3
from flask import Flask, request, jsonify
import requests
import pandas as pd
import joblib
import numpy as np
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class EnergyAwareScheduler:
    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        self.model_info = self.load_ml_model()
        self.node_cache = {}
        self.cache_ttl = 30
        
    def load_ml_model(self):
        """Load the improved energy rate model"""
        try:
            model_info = joblib.load('corrected_energy_model.pkl')
            logger.info("✅ Loaded improved energy rate model")
            logger.info(f"   Model R²: {model_info['performance']['r2']:.3f}")
            logger.info(f"   Model MAE: {model_info['performance']['mae']:.2f} J/min")
            return model_info
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            return None
    
    def predict_pod_energy_rate(self, pod_spec, node_metrics):
        """Predict energy consumption rate for a pod"""
        if not self.model_info:
            return 100  # Fallback value
            
        try:
            pod_resources = self.extract_pod_resources(pod_spec)
            
            # Prepare features in exact same order as training
            features = [
                pod_resources['cpu_avg'],
                pod_resources['cpu_max'], 
                pod_resources['memory_gb'],
                pod_resources['pod_type']
            ]
            
            # Make prediction
            if self.model_info.get('model_type') == 'rule_based':
                energy_rate = self.model_info['predict_function'](*features)
            else:
                energy_rate = self.model_info['model'].predict([features])[0]
            
            logger.debug(f"Predicted energy rate for {pod_resources['pod_name']}: {energy_rate:.1f} J/min")
            return max(energy_rate, 0.1)  # Minimum 0.1 J/min
            
        except Exception as e:
            logger.error(f"Energy prediction failed: {e}")
            return 50  # Conservative fallback
    
    def extract_pod_resources(self, pod):
        """Extract resource requirements from pod spec"""
        resources = {
            'pod_name': pod['metadata']['name'],
            'cpu_avg': 0.1,  # Default estimate
            'cpu_max': 0.2,   # Default estimate  
            'memory_gb': 0.1, # Default estimate
            'pod_type': 4     # Default: Other
        }
        
        try:
            pod_name = pod['metadata']['name']
            resources['pod_name'] = pod_name
            resources['pod_type'] = self.classify_pod_type(pod_name)
            
            cpu_values = []
            memory_values = []
            
            # Analyze container resource requests
            for container in pod['spec'].get('containers', []):
                container_cpu = 0.1
                container_memory = 0.1
                
                if 'resources' in container and 'requests' in container['resources']:
                    requests = container['resources']['requests']
                    
                    # CPU extraction
                    if 'cpu' in requests:
                        cpu_str = requests['cpu']
                        if cpu_str.endswith('m'):
                            container_cpu = int(cpu_str[:-1]) / 1000
                        else:
                            container_cpu = float(cpu_str)
                    
                    # Memory extraction  
                    if 'memory' in requests:
                        mem_str = requests['memory']
                        if mem_str.endswith('Gi'):
                            container_memory = float(mem_str[:-2])
                        elif mem_str.endswith('Mi'):
                            container_memory = float(mem_str[:-2]) / 1024
                        elif mem_str.endswith('Ki'):
                            container_memory = float(mem_str[:-2]) / (1024**2)
                        else:
                            container_memory = float(mem_str) / (1024**3)
                
                cpu_values.append(container_cpu)
                memory_values.append(container_memory * 1024)  # Convert to MB for calculation
            
            # Use actual resource requests if available
            if cpu_values:
                resources['cpu_avg'] = sum(cpu_values) * 0.7  # Assume 70% of requested
                resources['cpu_max'] = max(cpu_values)
            
            if memory_values:
                resources['memory_gb'] = sum(memory_values) / 1024  # Convert back to GB
            
        except Exception as e:
            logger.warning(f"Could not extract pod resources: {e}")
        
        return resources
    
    def classify_pod_type(self, pod_name):
        """Classify pod type using same logic as training"""
        pod_lower = pod_name.lower()
        if any(x in pod_lower for x in ['5gs', 'open5gs', 'amf', 'smf', 'upf', 'udm', 'nrf']):
            return 0  # 5G Core
        elif any(x in pod_lower for x in ['srsran', 'gnb', 'ue']):
            return 1  # RAN
        elif any(x in pod_lower for x in ['kepler', 'prometheus', 'grafana']):
            return 2  # Monitoring
        elif any(x in pod_lower for x in ['kube', 'coredns', 'etcd', 'controller', 'scheduler', 'proxy']):
            return 3  # Kubernetes System
        else:
            return 4  # Other
    
    def calculate_node_score(self, node, pod):
        """Calculate energy-aware node score (higher is better)"""
        node_name = node['metadata']['name']
        
        # Predict energy impact
        energy_rate = self.predict_pod_energy_rate(pod, {})
        
        # Convert energy rate to score (0-100)
        # Lower energy consumption = higher score
        if energy_rate < 10:
            energy_score = 95  # Very efficient
        elif energy_rate < 50:
            energy_score = 80  # Efficient
        elif energy_rate < 200:
            energy_score = 60  # Moderate
        elif energy_rate < 1000:
            energy_score = 30  # High energy
        else:
            energy_score = 10  # Very high energy
        
        # Get node metrics for load balancing
        node_metrics = self.get_node_metrics(node_name)
        load_score = self.calculate_load_score(node_metrics)
        
        # 5G-aware scheduling preferences
        fiveg_score = self.calculate_5g_score(node_name, pod)
        
        # Composite score (energy efficiency is most important)
        total_score = (
            0.6 * energy_score +    # Energy efficiency (priority)
            0.2 * load_score +      # Load balancing
            0.2 * fiveg_score       # 5G optimization
        )
        
        logger.info(f"Node {node_name} - Energy: {energy_rate:.1f} J/min → Score: {energy_score}, "
                   f"Load: {load_score}, 5G: {fiveg_score}, Total: {total_score:.1f}")
        
        return total_score
    
    def get_node_metrics(self, node_name):
        """Get node metrics (simplified for demo)"""
        # In production, query Prometheus for actual metrics
        return {
            'cpu_usage': 50,  # Placeholder
            'memory_usage': 60,  # Placeholder
        }
    
    def calculate_load_score(self, node_metrics):
        """Calculate load balancing score"""
        # Prefer less loaded nodes
        cpu_load = node_metrics.get('cpu_usage', 50)
        memory_load = node_metrics.get('memory_usage', 50)
        avg_load = (cpu_load + memory_load) / 2
        return max(0, 100 - avg_load)
    
    def calculate_5g_score(self, node_name, pod):
        """5G-aware scheduling preferences"""
        pod_resources = self.extract_pod_resources(pod)
        pod_type = pod_resources['pod_type']
        
        # Prefer master for 5G core functions
        if pod_type == 0:  # 5G Core
            return 90 if "master" in node_name.lower() else 70
        
        # Prefer worker for RAN functions  
        elif pod_type == 1:  # RAN
            return 80 if "worker" in node_name.lower() else 60
        
        # Default preference
        return 50

# Initialize scheduler
scheduler = EnergyAwareScheduler()

@app.route('/filter', methods=['POST'])
def filter_nodes():
    """Filter out unsuitable nodes"""
    try:
        data = request.json
        nodes = data['nodes']['items']
        pod = data['pod']
        
        filtered_nodes = []
        for node in nodes:
            # Basic filtering - all nodes pass in demo
            if not node['spec'].get('unschedulable', False):
                filtered_nodes.append(node)
        
        logger.info(f"Filtered {len(filtered_nodes)}/{len(nodes)} nodes for {pod['metadata']['name']}")
        return jsonify({'nodes': {'items': filtered_nodes}})
        
    except Exception as e:
        logger.error(f"Filter error: {e}")
        return jsonify({'nodes': {'items': nodes}})

@app.route('/prioritize', methods=['POST'])
def prioritize_nodes():
    """Score and prioritize nodes based on energy efficiency"""
    try:
        data = request.json
        nodes = data['nodes']['items']
        pod = data['pod']
        
        pod_name = pod['metadata']['name']
        logger.info(f"Prioritizing nodes for pod: {pod_name}")
        
        scores = []
        for node in nodes:
            node_name = node['metadata']['name']
            score = scheduler.calculate_node_score(node, pod)
            
            scores.append({
                'host': node_name,
                'score': int(score * 10)  # Convert to 0-1000 scale
            })
        
        # Log the decision
        best_node = max(scores, key=lambda x: x['score'])
        energy_rate = scheduler.predict_pod_energy_rate(pod, {})
        logger.info(f"🎯 Best node for {pod_name}: {best_node['host']} (score: {best_node['score']})")
        logger.info(f"   Predicted energy: {energy_rate:.1f} J/min")
        
        return jsonify({'scores': scores})
        
    except Exception as e:
        logger.error(f"Prioritize error: {e}")
        equal_scores = [{'host': node['metadata']['name'], 'score': 1} for node in nodes]
        return jsonify({'scores': equal_scores})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'model_loaded': scheduler.model_info is not None,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("🚀 Starting Energy-Aware Scheduler Extender with Improved Model")
    app.run(host='0.0.0.0', port=8080, debug=False)
