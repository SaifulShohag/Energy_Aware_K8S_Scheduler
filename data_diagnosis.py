#!/usr/bin/env python3
import pandas as pd
import numpy as np
import glob
import matplotlib.pyplot as plt
import seaborn as sns

def diagnose_data_issues():
    """Deep analysis of data quality issues"""
    csv_files = glob.glob("*_metrics.csv")
    print(f"Found {len(csv_files)} metrics files")
    
    all_energy_data = []
    pod_energy_stats = []
    
    for file in csv_files:
        try:
            # Load data with error handling
            df = pd.read_csv(file, on_bad_lines='skip')
            pod_name = file.replace('_metrics.csv', '')
            
            if 'energy_joules' in df.columns:
                energy_data = df['energy_joules']
                valid_energy = energy_data[energy_data > 0]  # Filter out zeros
                
                if len(valid_energy) > 0:
                    pod_stats = {
                        'pod_name': pod_name,
                        'energy_mean': valid_energy.mean(),
                        'energy_std': valid_energy.std(),
                        'energy_max': valid_energy.max(),
                        'energy_min': valid_energy.min(),
                        'data_points': len(valid_energy),
                        'zero_energy_points': len(energy_data) - len(valid_energy)
                    }
                    pod_energy_stats.append(pod_stats)
                    all_energy_data.extend(valid_energy.tolist())
                
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    # Convert to DataFrame
    stats_df = pd.DataFrame(pod_energy_stats)
    
    print("\n=== ENERGY DATA DIAGNOSIS ===")
    print(f"Total pods with valid energy data: {len(stats_df)}")
    print(f"Overall energy range: {np.min(all_energy_data):.2f} - {np.max(all_energy_data):.2f} J")
    print(f"Overall energy mean: {np.mean(all_energy_data):.2f} J")
    print(f"Overall energy std: {np.std(all_energy_data):.2f} J")
    
    # Identify problematic pods
    high_energy_pods = stats_df[stats_df['energy_mean'] > 1000]
    print(f"\nPods with very high energy consumption (>1000J):")
    for _, pod in high_energy_pods.iterrows():
        print(f"  {pod['pod_name']}: {pod['energy_mean']:.2f} J")
    
    # Plot energy distribution
    plt.figure(figsize=(12, 6))
    
    plt.subplot(1, 2, 1)
    plt.hist(all_energy_data, bins=50, edgecolor='black', alpha=0.7)
    plt.title('Distribution of Energy Consumption')
    plt.xlabel('Energy (Joules)')
    plt.ylabel('Frequency')
    plt.axvline(np.mean(all_energy_data), color='red', linestyle='--', label=f'Mean: {np.mean(all_energy_data):.2f}J')
    plt.legend()
    
    plt.subplot(1, 2, 2)
    # Plot top 20 pods by energy consumption
    top_pods = stats_df.nlargest(20, 'energy_mean')
    plt.barh(range(len(top_pods)), top_pods['energy_mean'])
    plt.yticks(range(len(top_pods)), top_pods['pod_name'], fontsize=8)
    plt.title('Top 20 Pods by Energy Consumption')
    plt.xlabel('Mean Energy (Joules)')
    
    plt.tight_layout()
    plt.savefig('energy_diagnosis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return stats_df

if __name__ == '__main__':
    diagnose_data_issues()
