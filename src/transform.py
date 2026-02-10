"""
Data transformation and aggregation for thermal experiment.
Handles resampling, wall/box aggregations, gradients, thermal lag.
"""

import pandas as pd
import numpy as np
from scipy.signal import correlate
from scipy.stats import pearsonr
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def resample_to_10min(df, periods_data=None):
    """
    Resample sensor data to 10-minute intervals.
    Groups by (box_id, sensor_id) and resamples each sensor independently.
    
    IMPORTANT: Bins start from the earliest timestamp across ALL data to ensure alignment.
    """
    if df is None or len(df) == 0:
        return None
    
    logger.info(f"\n{'='*80}")
    logger.info(f"RESAMPLING TO 10-MINUTE BINS")
    logger.info(f"{'='*80}")
    
    # Find global earliest timestamp (across all periods if provided)
    if periods_data:
        all_timestamps = []
        for period_df in periods_data.values():
            if period_df is not None and len(period_df) > 0:
                all_timestamps.append(period_df['timestamp'].min())
        if all_timestamps:
            global_start = min(all_timestamps)
            logger.info(f"✓ Global earliest timestamp: {global_start}")
        else:
            global_start = df['timestamp'].min()
    else:
        global_start = df['timestamp'].min()
        logger.info(f"✓ Earliest timestamp in this dataset: {global_start}")
    
    # Floor the global start to a clean 10-minute boundary
    global_start_floored = global_start.floor('10min')
    logger.info(f"✓ Bin start time (floored): {global_start_floored}")
    
    # Floor all timestamps to 10-minute bins
    df['t_bin'] = df['timestamp'].dt.floor('10min')
    
    logger.info(f"  Original rows: {len(df):,}")
    logger.info(f"  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Group by box, sensor, and time bin (include period if it exists)
    group_cols = ['box_id', 'sensor_id', 'wall_id', 'position', 't_bin']
    if 'period' in df.columns:
        group_cols = ['period'] + group_cols
    
    agg_dict = {
        'surface_temp': 'mean',
        'internal_temp': 'mean',
        'room_temp': 'mean',
    }
    
    # Handle wall_type - take most common value
    if 'wall_type' in df.columns:
        agg_dict['wall_type'] = lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    
    resampled = df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
    
    # Rename t_bin to timestamp
    resampled = resampled.rename(columns={'t_bin': 'timestamp'})
    
    logger.info(f"  Resampled bins: {len(resampled):,}")
    logger.info(f"  Bin time range: {resampled['timestamp'].min()} to {resampled['timestamp'].max()}")
    logger.info(f"  Unique timestamps: {resampled['timestamp'].nunique()}")
    
    # VALIDATION: Check that each timestamp has exactly 32 values (16 sensors × 2 boxes)
    logger.info(f"\n  ⚠️  VALIDATION: Checking timestamp bin integrity...")
    counts_per_timestamp = resampled.groupby('timestamp').size()
    expected_count = 32  # 16 sensors × 2 boxes
    
    all_correct = (counts_per_timestamp == expected_count).all()
    if all_correct:
        logger.info(f"  ✓ PASS: All {len(counts_per_timestamp)} timestamps have exactly {expected_count} values")
    else:
        incorrect_bins = counts_per_timestamp[counts_per_timestamp != expected_count]
        logger.warning(f"  ❌ FAIL: {len(incorrect_bins)} timestamps have incorrect counts:")
        for ts, count in incorrect_bins.head(10).items():
            logger.warning(f"    {ts}: {count} values (expected {expected_count})")
        if len(incorrect_bins) > 10:
            logger.warning(f"    ... and {len(incorrect_bins) - 10} more")
    
    # Show distribution of counts
    count_distribution = counts_per_timestamp.value_counts().sort_index()
    logger.info(f"\n  Count distribution:")
    for count, freq in count_distribution.items():
        logger.info(f"    {count} values: {freq} timestamps")
    
    # Show sample before/after
    if len(resampled) > 0:
        sample = resampled.iloc[0]
        logger.info(f"\n  Sample resampled row:")
        logger.info(f"    timestamp: {sample['timestamp']}")
        logger.info(f"    box_id: {sample['box_id']}, sensor_id: {sample['sensor_id']}")
        logger.info(f"    surface_temp: {sample['surface_temp']:.2f}°C")
        logger.info(f"    internal_temp: {sample['internal_temp']:.2f}°C")
    
    logger.info(f"{'='*80}\n")
    
    return resampled


def calculate_normalized_temps(df):
    """
    Calculate normalized temperatures (relative to room temp).
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"CALCULATING NORMALIZED TEMPERATURES")
    logger.info(f"{'='*80}")
    
    if 'surface_temp' in df.columns and 'room_temp' in df.columns:
        df['normalized_surface'] = df['surface_temp'] - df['room_temp']
        logger.info(f"✓ Calculated normalized_surface = surface_temp - room_temp")
    
    if 'internal_temp' in df.columns and 'room_temp' in df.columns:
        df['normalized_internal'] = df['internal_temp'] - df['room_temp']
        logger.info(f"✓ Calculated normalized_internal = internal_temp - room_temp")
    
    # Show sample
    if len(df) > 0 and 'normalized_surface' in df.columns:
        sample = df.iloc[0]
        logger.info(f"\n  Sample calculation:")
        logger.info(f"    room_temp:          {sample['room_temp']:.2f}°C")
        logger.info(f"    surface_temp:       {sample['surface_temp']:.2f}°C")
        logger.info(f"    normalized_surface: {sample['normalized_surface']:.2f}°C")
    
    logger.info(f"{'='*80}\n")
    
    return df


def calculate_thermal_gradient(df):
    """
    Calculate thermal gradient for each wall at each timestamp.
    
    Gradient structure (from outside to inside):
    1. room_temp (outside air)
    2. out_surface (outside wall surface)
    3. in_surface (inside wall surface)
    4. internal_temp (average of 4 sensors measuring the wall's internal temp)
    
    For each sensor position (out/in), we have:
    - surface_temp: the surface temperature
    - internal_temp: the internal wall sensor (should average 4 sensors per wall)
    
    Gradients to calculate:
    - gradient_step1: room_temp → out_surface
    - gradient_step2: out_surface → in_surface
    - gradient_step3: in_surface → avg(internal temps on that wall)
    - total_gradient: room_temp → avg(internal temps)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"CALCULATING THERMAL GRADIENTS")
    logger.info(f"{'='*80}")
    logger.info(f"Gradient structure: room_air → out_surface → in_surface → internal_avg")
    
    # This function works on wall-level aggregated data
    # It should have out_surface, in_surface, out_internal, in_internal, room_temp
    
    if 'out_surface' in df.columns and 'room_temp' in df.columns:
        df['gradient_air_to_out_surface'] = df['out_surface'] - df['room_temp']
        logger.info(f"✓ gradient_air_to_out_surface = out_surface - room_temp")
    
    if 'out_surface' in df.columns and 'in_surface' in df.columns:
        df['gradient_out_to_in_surface'] = df['in_surface'] - df['out_surface']
        logger.info(f"✓ gradient_out_to_in_surface = in_surface - out_surface")
    
    # Average internal temp (mean of out and in internal sensors)
    if 'out_internal' in df.columns and 'in_internal' in df.columns:
        df['internal_avg'] = (df['out_internal'] + df['in_internal']) / 2
        logger.info(f"✓ internal_avg = mean(out_internal, in_internal)")
    elif 'out_internal' in df.columns:
        df['internal_avg'] = df['out_internal']
        logger.info(f"✓ internal_avg = out_internal (in_internal missing)")
    elif 'in_internal' in df.columns:
        df['internal_avg'] = df['in_internal']
        logger.info(f"✓ internal_avg = in_internal (out_internal missing)")
    
    if 'in_surface' in df.columns and 'internal_avg' in df.columns:
        df['gradient_in_surface_to_internal'] = df['internal_avg'] - df['in_surface']
        logger.info(f"✓ gradient_in_surface_to_internal = internal_avg - in_surface")
    
    if 'room_temp' in df.columns and 'internal_avg' in df.columns:
        df['total_gradient'] = df['internal_avg'] - df['room_temp']
        logger.info(f"✓ total_gradient = internal_avg - room_temp")
    
    # Show sample
    if len(df) > 0:
        sample_idx = df.index[0]
        logger.info(f"\n  Sample gradient calculation (first row):")
        if 'room_temp' in df.columns:
            logger.info(f"    1. room_temp:              {df.loc[sample_idx, 'room_temp']:.2f}°C")
        if 'out_surface' in df.columns:
            logger.info(f"    2. out_surface:            {df.loc[sample_idx, 'out_surface']:.2f}°C")
            if 'gradient_air_to_out_surface' in df.columns:
                logger.info(f"       → step 1 gradient:      {df.loc[sample_idx, 'gradient_air_to_out_surface']:.2f}°C")
        if 'in_surface' in df.columns:
            logger.info(f"    3. in_surface:             {df.loc[sample_idx, 'in_surface']:.2f}°C")
            if 'gradient_out_to_in_surface' in df.columns:
                logger.info(f"       → step 2 gradient:      {df.loc[sample_idx, 'gradient_out_to_in_surface']:.2f}°C")
        if 'internal_avg' in df.columns:
            logger.info(f"    4. internal_avg:           {df.loc[sample_idx, 'internal_avg']:.2f}°C")
            if 'gradient_in_surface_to_internal' in df.columns:
                logger.info(f"       → step 3 gradient:      {df.loc[sample_idx, 'gradient_in_surface_to_internal']:.2f}°C")
        if 'total_gradient' in df.columns:
            logger.info(f"    TOTAL gradient:            {df.loc[sample_idx, 'total_gradient']:.2f}°C")
    
    logger.info(f"{'='*80}\n")
    
    return df
def aggregate_wall_level(df):
    """
    Aggregate to wall level: (period, box, wall, timestamp).
    Compute outside/inside averages and gradients.
    """
    if df is None or len(df) == 0:
        return None
    
    logger.info(f"\n{'='*80}")
    logger.info(f"WALL-LEVEL AGGREGATION")
    logger.info(f"{'='*80}")
    
    # Group by period, box, wall, position, timestamp
    group_cols = ['period', 'box_id', 'wall_id', 'position', 'timestamp']
    
    agg_dict = {
        'surface_temp': 'mean',
        'internal_temp': 'mean',
        'room_temp': 'mean',
        'sensor_id': 'count',  # Count sensors
    }
    
    if 'normalized_surface' in df.columns:
        agg_dict['normalized_surface'] = 'mean'
    if 'normalized_internal' in df.columns:
        agg_dict['normalized_internal'] = 'mean'
    if 'wall_type' in df.columns:
        agg_dict['wall_type'] = lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    
    logger.info(f"  Grouping by: {group_cols}")
    wall_pos = df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
    wall_pos = wall_pos.rename(columns={'sensor_id': 'sensor_count'})
    
    logger.info(f"  Position-level rows: {len(wall_pos):,}")
    
    # Pivot to get outside and inside columns
    wall_data = []
    
    for (period, box, wall, ts), group in wall_pos.groupby(['period', 'box_id', 'wall_id', 'timestamp']):
        row = {
            'period': period,
            'box_id': box,
            'wall_id': wall,
            'timestamp': ts,
        }
        
        for pos in ['out', 'in']:
            pos_data = group[group['position'] == pos]
            if len(pos_data) > 0:
                row[f'{pos}_surface'] = pos_data['surface_temp'].iloc[0]
                row[f'{pos}_internal'] = pos_data['internal_temp'].iloc[0]
                row[f'{pos}_room'] = pos_data['room_temp'].iloc[0]
                row[f'{pos}_sensor_count'] = pos_data['sensor_count'].iloc[0]
                
                if 'normalized_surface' in pos_data.columns:
                    row[f'{pos}_normalized_surface'] = pos_data['normalized_surface'].iloc[0]
                if 'normalized_internal' in pos_data.columns:
                    row[f'{pos}_normalized_internal'] = pos_data['normalized_internal'].iloc[0]
                if 'wall_type' in pos_data.columns:
                    row['wall_type'] = pos_data['wall_type'].iloc[0]
        
        # Use room_temp from either position (should be the same)
        if 'out_room' in row:
            row['room_temp'] = row['out_room']
        elif 'in_room' in row:
            row['room_temp'] = row['in_room']
        
        wall_data.append(row)
    
    wall_df = pd.DataFrame(wall_data)
    
    logger.info(f"  Wall-level rows: {len(wall_df):,}")
    
    # Calculate gradients using the new function
    wall_df = calculate_thermal_gradient(wall_df)
    
    # Also calculate simple surface and internal gradients for backward compatibility
    if 'out_surface' in wall_df.columns and 'in_surface' in wall_df.columns:
        wall_df['surface_gradient'] = wall_df['out_surface'] - wall_df['in_surface']
    
    if 'out_internal' in wall_df.columns and 'in_internal' in wall_df.columns:
        wall_df['internal_gradient'] = wall_df['out_internal'] - wall_df['in_internal']
    
    logger.info(f"✓ Wall-level aggregation complete")
    logger.info(f"{'='*80}\n")
    
    return wall_df


def aggregate_box_level(df):
    """
    Aggregate to box level: (period, box, timestamp).
    Average across all available sensors.
    Surface temp uses only 'in' position sensors (inside of wall).
    Internal temp uses all sensors.
    """
    if df is None or len(df) == 0:
        return None
    
    logger.info(f"\n{'='*80}")
    logger.info(f"BOX-LEVEL AGGREGATION")
    logger.info(f"{'='*80}")
    
    group_cols = ['period', 'box_id', 'timestamp']
    
    # For internal temp and room temp, use all sensors
    agg_dict = {
        'internal_temp': 'mean',
        'room_temp': 'mean',
        'sensor_id': 'count',
    }
    
    if 'normalized_internal' in df.columns:
        agg_dict['normalized_internal'] = 'mean'
    
    box_df = df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
    box_df = box_df.rename(columns={'sensor_id': 'sensor_count'})
    
    # For surface temp, average only 'in' position sensors
    if 'position' in df.columns:
        logger.info(f"  Calculating surface_temp from 'in' position sensors only")
        in_sensors = df[df['position'] == 'in'].copy()
        
        in_agg = {'surface_temp': 'mean'}
        if 'normalized_surface' in in_sensors.columns:
            in_agg['normalized_surface'] = 'mean'
        
        in_df = in_sensors.groupby(group_cols, dropna=False).agg(in_agg).reset_index()
        
        # Merge with box_df
        box_df = box_df.merge(in_df, on=group_cols, how='left')
    else:
        # Fallback: use all sensors
        logger.info(f"  Warning: No 'position' column, using all sensors for surface_temp")
        surface_agg = df.groupby(group_cols, dropna=False).agg({'surface_temp': 'mean'}).reset_index()
        box_df = box_df.merge(surface_agg, on=group_cols, how='left')
    
    logger.info(f"  Box-level rows: {len(box_df):,}")
    logger.info(f"✓ Box-level aggregation complete")
    logger.info(f"{'='*80}\n")
    
    return box_df


def aggregate_wall_type(df):
    """
    Aggregate by wall type across time ranges.
    For experimental box only (box 2).
    """
    if df is None or len(df) == 0 or 'wall_type' not in df.columns:
        return None
    
    # Filter to experimental box
    exp_df = df[df['box_id'] == 2].copy()
    
    if len(exp_df) == 0:
        return None
    
    # Detect wall type change events
    exp_df = exp_df.sort_values('timestamp')
    exp_df['wall_type_changed'] = exp_df['wall_type'].ne(exp_df['wall_type'].shift())
    exp_df['regime_id'] = exp_df['wall_type_changed'].cumsum()
    
    # Group by period, wall_id, wall_type, regime
    group_cols = ['period', 'wall_id', 'wall_type', 'regime_id']
    
    agg_dict = {
        'timestamp': ['min', 'max', 'count'],
    }
    
    # Add all numeric columns
    for col in exp_df.columns:
        if col.endswith('_surface') or col.endswith('_internal') or col.endswith('_gradient'):
            agg_dict[col] = 'mean'
    
    wall_type_df = exp_df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
    
    # Flatten multi-index columns
    wall_type_df.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col 
                            for col in wall_type_df.columns]
    
    return wall_type_df


def calculate_thermal_lag(out_series, in_series, max_lag_hours=12):
    """
    Calculate thermal lag between outside and inside using cross-correlation.
    Returns lag in minutes and correlation coefficient.
    """
    # Remove NaN values
    valid_idx = ~(out_series.isna() | in_series.isna())
    out_clean = out_series[valid_idx].values
    in_clean = in_series[valid_idx].values
    
    if len(out_clean) < 10:
        return None, None
    
    # Normalize
    out_norm = (out_clean - np.mean(out_clean)) / (np.std(out_clean) + 1e-8)
    in_norm = (in_clean - np.mean(in_clean)) / (np.std(in_clean) + 1e-8)
    
    # Cross-correlation
    correlation = correlate(in_norm, out_norm, mode='full')
    lags = np.arange(-len(out_norm) + 1, len(out_norm))
    
    # Convert lags to minutes (assuming 10-minute intervals)
    lags_minutes = lags * 10
    
    # Search within max_lag window
    max_lag_minutes = max_lag_hours * 60
    valid_range = (lags_minutes >= 0) & (lags_minutes <= max_lag_minutes)
    
    if not valid_range.any():
        return None, None
    
    # Find lag with maximum correlation in valid range
    valid_corr = correlation[valid_range]
    valid_lags = lags_minutes[valid_range]
    
    max_idx = np.argmax(valid_corr)
    best_lag = valid_lags[max_idx]
    best_corr = valid_corr[max_idx] / len(out_clean)  # Normalize
    
    return best_lag, best_corr


def apply_smoothing(df, columns, window):
    """
    Apply rolling mean smoothing to specified columns.
    window: e.g., '1h', '3h', '12h'
    """
    if window is None or window == 'None':
        return df
    
    df = df.sort_values('timestamp')
    
    for col in columns:
        if col in df.columns:
            df[f'{col}_smooth'] = df.set_index('timestamp')[col].rolling(window).mean().values
    
    return df


def detect_wall_type_changes(df):
    """
    Detect timestamps where wall type changes.
    Returns list of (timestamp, new_wall_type) tuples.
    """
    if df is None or 'wall_type' not in df.columns:
        return []
    
    df = df.sort_values('timestamp')
    changes = df[df['wall_type'].ne(df['wall_type'].shift())].copy()
    
    events = [(row['timestamp'], row['wall_type']) for _, row in changes.iterrows()]
    
    return events


def transform_all_data(periods_dict):
    """
    Apply all transformations to loaded period data.
    Returns dict with sensor_level, wall_level, and box_level DataFrames.
    """
    all_sensor = []
    all_wall = []
    all_box = []
    
    for period_name, df in periods_dict.items():
        logger.info(f"Transforming {period_name}...")
        
        # Resample to 10 minutes
        df_resampled = resample_to_10min(df)
        
        if df_resampled is None:
            continue
        
        # Calculate normalized temps
        df_resampled = calculate_normalized_temps(df_resampled)
        
        all_sensor.append(df_resampled)
        
        # Wall-level aggregation
        wall_df = aggregate_wall_level(df_resampled)
        if wall_df is not None:
            all_wall.append(wall_df)
        
        # Box-level aggregation
        box_df = aggregate_box_level(df_resampled)
        if box_df is not None:
            all_box.append(box_df)
    
    result = {}
    
    if all_sensor:
        result['sensor'] = pd.concat(all_sensor, ignore_index=True)
        logger.info(f"Total sensor-level data: {len(result['sensor'])} rows")
    
    if all_wall:
        result['wall'] = pd.concat(all_wall, ignore_index=True)
        logger.info(f"Total wall-level data: {len(result['wall'])} rows")
    
    if all_box:
        result['box'] = pd.concat(all_box, ignore_index=True)
        logger.info(f"Total box-level data: {len(result['box'])} rows")
    
    return result
