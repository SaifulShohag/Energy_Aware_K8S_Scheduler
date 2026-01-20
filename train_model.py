#!/usr/bin/env python3
import pandas as pd
import numpy as np
import glob
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder

def train():
    print("--- 1. Loading Data ---")
    all_files = glob.glob("*_metrics.csv")
    df_list = []
    
    for f in all_files:
        try:
            temp_df = pd.read_csv(f)
            # Filter out idle/startup noise (energy < 0.1 Joules)
            temp_df = temp_df[temp_df['energy_joules'] > 0.1]
            df_list.append(temp_df)
        except:
            pass
            
    if not df_list:
        print("Error: No data found!")
        return

    df = pd.concat(df_list, ignore_index=True)
    print(f"Loaded {len(df)} data points.")

    # --- 2. Feature Engineering ---
    # We need to turn text 'RAN', '5G_CORE' into numbers for the AI
    le = LabelEncoder()
    df['pod_type_encoded'] = le.fit_transform(df['pod_type'].astype(str))
    
    # Calculate Averages per Type (Crucial for the Scheduler later!)
    # The Scheduler won't know 'Network I/O' for a new pod, so it will use these averages.
    type_stats = df.groupby('pod_type')[['net_rx_bytes_sec', 'net_tx_bytes_sec']].mean().to_dict('index')
    
    # Define Features (Inputs) and Target (Output)
    features = ['cpu_cores', 'memory_bytes', 'net_rx_bytes_sec', 'net_tx_bytes_sec', 'pod_type_encoded']
    target = 'energy_joules'

    X = df[features]
    y = df[target]

    # --- 3. Training ---
    print("--- 2. Training Random Forest Model ---")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # --- 4. Evaluation ---
    score = model.score(X_test, y_test)
    print(f"Model Accuracy (R2 Score): {score:.4f}")
    
    # --- 5. Save Everything ---
    artifact = {
        'model': model,
        'encoder': le,
        'type_stats': type_stats, # Saving the averages for the scheduler
        'features': features
    }
    joblib.dump(artifact, 'energy_model.pkl')
    print("Success! Model saved to 'energy_model.pkl'")

if __name__ == "__main__":
    train()
