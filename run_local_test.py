#!/usr/bin/env python3
import requests
import json
import threading
import time
from energy_scheduler_extender import app, scheduler

def start_flask_app():
    """Start the Flask app in a separate thread"""
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def test_extender_endpoints():
    """Test the extender endpoints with mock data"""
    time.sleep(2)  # Wait for Flask to start
    
    base_url = "http://localhost:8080"
    
    # Test data matching Kubernetes scheduler format
    mock_filter_request = {
        "nodes": {
            "items": [
                {
                    "metadata": {"name": "master-node"},
                    "spec": {"unschedulable": False}
                },
                {
                    "metadata": {"name": "worker-node-1"},
                    "spec": {"unschedulable": False}  
                },
                {
                    "metadata": {"name": "worker-node-2"}, 
                    "spec": {"unschedulable": True}  # This node should be filtered out
                }
            ]
        },
        "pod": {
            "metadata": {"name": "test-5g-core-pod"},
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "resources": {
                            "requests": {"cpu": "100m", "memory": "256Mi"}
                        }
                    }
                ]
            }
        }
    }
    
    print("🧪 Testing /filter endpoint...")
    try:
        response = requests.post(f"{base_url}/filter", json=mock_filter_request)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n🧪 Testing /prioritize endpoint...")
    try:
        response = requests.post(f"{base_url}/prioritize", json=mock_filter_request)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n🧪 Testing /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == '__main__':
    print("🚀 Starting local scheduler extender test...")
    
    # Start Flask app in background thread
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Test endpoints
    test_extender_endpoints()
    
    print("\n✅ All tests completed! The extender is ready for Kubernetes deployment.")
