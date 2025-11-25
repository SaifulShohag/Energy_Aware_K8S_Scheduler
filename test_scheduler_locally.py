#!/usr/bin/env python3
import json
from energy_scheduler_extender import EnergyAwareScheduler

def test_scheduler_locally():
    """Test the scheduler logic without Kubernetes"""
    print("🧪 Testing Energy-Aware Scheduler Locally...")
    
    scheduler = EnergyAwareScheduler()
    
    # Create mock pod specifications
    test_pods = [
        {
            'name': '5g-core-pod',
            'spec': {
                'metadata': {'name': 'open5gs-amf-12345'},
                'spec': {
                    'containers': [
                        {
                            'name': 'amf',
                            'resources': {
                                'requests': {'cpu': '100m', 'memory': '256Mi'}
                            }
                        }
                    ]
                }
            }
        },
        {
            'name': 'ran-pod', 
            'spec': {
                'metadata': {'name': 'srsran-gnb-67890'},
                'spec': {
                    'containers': [
                        {
                            'name': 'gnb',
                            'resources': {
                                'requests': {'cpu': '500m', 'memory': '512Mi'}
                            }
                        }
                    ]
                }
            }
        },
        {
            'name': 'monitoring-pod',
            'spec': {
                'metadata': {'name': 'prometheus-exporter'},
                'spec': {
                    'containers': [
                        {
                            'name': 'exporter',
                            'resources': {
                                'requests': {'cpu': '50m', 'memory': '128Mi'}
                            }
                        }
                    ]
                }
            }
        }
    ]
    
    # Create mock nodes
    test_nodes = [
        {
            'metadata': {'name': 'master-node'},
            'spec': {'unschedulable': False}
        },
        {
            'metadata': {'name': 'worker-node-1'}, 
            'spec': {'unschedulable': False}
        },
        {
            'metadata': {'name': 'worker-node-2'},
            'spec': {'unschedulable': False}
        }
    ]
    
    print("\n=== TESTING POD ENERGY PREDICTIONS ===")
    for pod_test in test_pods:
        energy_rate = scheduler.predict_pod_energy_rate(pod_test['spec'], {})
        pod_type = scheduler.extract_pod_resources(pod_test['spec'])['pod_type']
        type_name = ['5G Core', 'RAN', 'Monitoring', 'K8s System', 'Other'][pod_type]
        
        print(f"📊 {pod_test['name']} ({type_name}):")
        print(f"   Predicted energy rate: {energy_rate:.1f} J/min")
    
    print("\n=== TESTING NODE SCORING ===")
    for pod_test in test_pods:
        print(f"\n🎯 Scoring nodes for: {pod_test['name']}")
        for node in test_nodes:
            score = scheduler.calculate_node_score(node, pod_test['spec'])
            print(f"   {node['metadata']['name']}: {score:.1f}/100")
    
    print("\n✅ Local testing completed!")

if __name__ == '__main__':
    test_scheduler_locally()
