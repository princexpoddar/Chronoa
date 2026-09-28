"""
CHRONOS Evaluation Harness.

Orchestrator that runs the CHRONOS engine over synthetic data to collect 
False Alarm Rate (FAR) and detection delay metrics.
"""

import numpy as np
from chronos.data.synthetic import generate_synthetic_tile_history
from chronos.engine.field_fitter import FieldFitter
from chronos.engine.change_engine import ChronosEngine
from datetime import datetime

def run_evaluation(num_tiles: int = 100, alpha: float = 0.05):
    """
    Run the sequential e-process over synthetic tiles to calculate FAR.
    """
    fitter = FieldFitter()
    engine = ChronosEngine(fitter)
    
    false_alarms = 0
    true_detections = 0
    delays = []
    
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 1, 1)
    
    # Generate Null (No change) tiles
    for i in range(num_tiles // 2):
        records, embeddings, _ = generate_synthetic_tile_history(
            tile_id=f"null_{i}",
            start_date=start_date,
            end_date=end_date,
            change_date=None,
            seed=42 + i
        )
        
        hist_idx = 20
        ep_state, change_idx = engine.evaluate_sequential(
            historical_records=records[:hist_idx],
            historical_embeddings=embeddings[:hist_idx],
            streaming_records=records[hist_idx:],
            streaming_embeddings=embeddings[hist_idx:],
            alpha=alpha
        )
        
        if change_idx != -1:
            false_alarms += 1
            
    # Generate Alternative (Change) tiles
    for i in range(num_tiles // 2):
        change_dt = datetime(2024, 6, 1)
        records, embeddings, _ = generate_synthetic_tile_history(
            tile_id=f"alt_{i}",
            start_date=start_date,
            end_date=end_date,
            change_date=change_dt,
            seed=1042 + i
        )
        
        hist_idx = 20
        ep_state, change_idx = engine.evaluate_sequential(
            historical_records=records[:hist_idx],
            historical_embeddings=embeddings[:hist_idx],
            streaming_records=records[hist_idx:],
            streaming_embeddings=embeddings[hist_idx:],
            alpha=alpha
        )
        
        if change_idx != -1:
            true_detections += 1
            # Delay in number of observations
            # Find the actual index of change in streaming_records
            true_idx = next(idx for idx, r in enumerate(records[hist_idx:]) if r.timestamp >= change_dt)
            delays.append(max(0, change_idx - true_idx))
            
    far = false_alarms / (num_tiles // 2)
    tpr = true_detections / (num_tiles // 2)
    avg_delay = float(np.mean(delays)) if delays else 0.0
    
    return {
        "alpha_target": alpha,
        "false_alarm_rate": far,
        "true_positive_rate": tpr,
        "average_delay_obs": avg_delay,
        "total_evaluated": num_tiles
    }
