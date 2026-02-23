import joblib
import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# 1. LOAD the existing pkl file (Fixed line)
artifact = joblib.load('energy_model.pkl') 
model = artifact['model']

# 2. Define the input type (Match your 5 features from training)
# features: ['cpu_cores', 'memory_bytes', 'net_rx_bytes_sec', 'net_tx_bytes_sec', 'pod_type_encoded']
initial_type = [('float_input', FloatTensorType([None, 5]))]

# 3. CONVERT to ONNX
onx = convert_sklearn(model, initial_types=initial_type)

# 4. SAVE the ONNX file
with open("energy_model.onnx", "wb") as f:
    f.write(onx.SerializeToString())

print("Successfully converted energy_model.pkl to energy_model.onnx")
