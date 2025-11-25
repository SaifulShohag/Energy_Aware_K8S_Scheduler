#!/usr/bin/env python3
from energy_scheduler_extender import EnergyAwareScheduler

def quick_test():
    """Quick test of the core scheduling logic"""
    print("⚡ Quick Testing Energy-Aware Scheduler...")
    
    scheduler = EnergyAwareScheduler()
    
    # Test a few pod types
    test_cases = [
        ("open5gs-amf-123", "5G Core Pod"),
        ("srsran-gnb-456", "RAN Pod"), 
        ("prometheus-789", "Monitoring Pod"),
        ("kube-proxy-abc", "K8s System Pod")
    ]
    
    for pod_name, description in test_cases:
        mock_pod = {
            'metadata': {'name': pod_name},
            'spec': {'containers': [{'name': 'test'}]}
        }
        
        energy_rate = scheduler.predict_pod_energy_rate(mock_pod, {})
        pod_resources = scheduler.extract_pod_resources(mock_pod)
        
        print(f"\n📦 {description}: {pod_name}")
        print(f"   Pod Type: {pod_resources['pod_type']}")
        print(f"   CPU Estimate: {pod_resources['cpu_avg']:.3f} cores")
        print(f"   Memory Estimate: {pod_resources['memory_gb']:.2f} GB")
        print(f"   Predicted Energy: {energy_rate:.1f} J/min")
        
        # Test scoring on different nodes
        nodes = [
            {'metadata': {'name': 'master-node'}, 'spec': {}},
            {'metadata': {'name': 'worker-node-1'}, 'spec': {}},
        ]
        
        for node in nodes:
            score = scheduler.calculate_node_score(node, mock_pod)
            print(f"   Score on {node['metadata']['name']}: {score:.1f}/100")

if __name__ == '__main__':
    quick_test()
