"""
Data loading module for thermal experiment dashboard.
Handles CSV parsing, missing sensors, and irregular timestamps.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
import logging
import sys

# Configure console logging only
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# Sensor topology: wall_id -> (outside_sensors, inside_sensors)
WALL_TOPOLOGY = {
    1: ([1, 2], [9, 10]),     # South
    2: ([3, 4], [11, 12]),    # East
    3: ([5, 6], [13, 14]),    # North
    4: ([7, 8], [15, 16]),    # West
}


def get_sensor_wall(sensor_id):
    """Return (wall_id, 'out'/'in') for a sensor ID."""
    for wall_id, (out_sensors, in_sensors) in WALL_TOPOLOGY.items():
        if sensor_id in out_sensors:
            return wall_id, 'out'
        if sensor_id in in_sensors:
            return wall_id, 'in'
    return None, None


def parse_filename(filename):
    """
    Parse box_id and sensor_id from filename.
    Example: GW_1.1_111025.csv -> box_id=1, sensor_id=1
             GW_2.5_111025.csv -> box_id=2, sensor_id=5
    """
    pattern = r'GW_?(\d+)\.(\d+)_'
    match = re.search(pattern, filename)
    if match:
        box_id = int(match.group(1))
        sensor_id = int(match.group(2))
        return box_id, sensor_id
    
    # Try alternative pattern (Period2 format)
    pattern2 = r'GW(\d+)\.(\d+)_'
    match = re.search(pattern2, filename)
    if match:
        box_id = int(match.group(1))
        sensor_id = int(match.group(2))
        return box_id, sensor_id
    
    logger.warning(f"Could not parse filename: {filename}")
    return None, None


def load_csv_file(filepath):
    """
    Load a single CSV file with proper header handling.
    - Headers are on row 15 (index 14)
    - Data ends when 2+ required columns are missing
    - Expected date format: M/D/YYYY H:MM (e.g., "10/23/2025 12:01")
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"📄 FILE: {filepath.name}")
    logger.info(f"   Path: {filepath}")
    logger.info(f"{'='*70}")
    
    try:
        # Try multiple encodings
        df = None
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                df = pd.read_csv(filepath, header=14, encoding=encoding)
                logger.info(f"✓ Loaded with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            logger.error(f"❌ Could not read file with any encoding")
            return None
        logger.info(f"✓ Raw rows read: {len(df)}")
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        logger.info(f"✓ Columns found: {list(df.columns[:5])}...")  # Show first 5
        
        # Expected columns (flexible matching)
        date_col = None
        surface_col = None
        internal_col = None
        room_col = None
        wall_type_col = None
        
        for col in df.columns:
            if 'date' in col and 'time' in col:
                date_col = col
            elif 'value' in col and 'heat' in col and 'surface' in col:
                # 'Value Heat Surface Sensor' or similar
                surface_col = col
            elif 'internal' in col and 'temp' in col:
                internal_col = col
            elif 'out' in col and 'air' in col and 'temp' in col:
                room_col = col
            elif 'wall' in col and 'type' in col:
                wall_type_col = col
        
        if not date_col:
            logger.error(f"❌ No date/time column found in {filepath}")
            return None
        
        logger.info(f"✓ Found columns:")
        logger.info(f"  Date: '{date_col}'")
        if surface_col:
            logger.info(f"  Surface: '{surface_col}'")
        if internal_col:
            logger.info(f"  Internal: '{internal_col}'")
        if room_col:
            logger.info(f"  Room: '{room_col}'")
        
        # Parse Date/Time with explicit format for "10/23/2025 12:01"
        logger.info(f"  Parsing timestamps (format: M/D/YYYY H:MM)...")
        df['timestamp'] = pd.to_datetime(df[date_col], format='%m/%d/%Y %H:%M', errors='coerce')
        
        # Check for data completeness (end of file when 2+ required columns missing)
        required_cols = [date_col]
        if surface_col:
            required_cols.append(surface_col)
        if internal_col:
            required_cols.append(internal_col)
        if room_col:
            required_cols.append(room_col)
        
        logger.info(f"  Checking data completeness (required columns: {len(required_cols)})...")
        df['_missing_count'] = df[required_cols].isna().sum(axis=1)
        
        # Find first row where 2+ required values are missing
        invalid_rows = df[df['_missing_count'] >= 2]
        if len(invalid_rows) > 0:
            first_invalid = invalid_rows.index[0]
            if first_invalid > 0:
                dropped_rows = len(df) - first_invalid
                logger.warning(f"⚠ Found row with 2+ missing values at index {first_invalid}")
                logger.warning(f"  Dropping {dropped_rows} rows from that point (end of data)")
                df = df.iloc[:first_invalid]
        
        # Drop the helper column
        df = df.drop(columns=['_missing_count'], errors='ignore')
        
        # Drop any remaining rows with invalid timestamp
        df = df.dropna(subset=['timestamp'])
        
        # Log sample raw vs parsed
        if len(df) > 0 and not df['timestamp'].isna().all():
            first_valid_idx = df['timestamp'].first_valid_index()
            logger.info(f"  Sample: '{df[date_col].iloc[first_valid_idx]}' → {df['timestamp'].iloc[first_valid_idx]}")
        
        if len(df) == 0:
            logger.warning(f"❌ No valid data in {filepath}")
            return None
        
        logger.info(f"✓ Valid timestamp rows: {len(df)}")
        logger.info(f"  Time range: {df['timestamp'].min()} → {df['timestamp'].max()}")
        
        # Rename columns to standard names
        rename_map = {}
        if surface_col:
            rename_map[surface_col] = 'surface_temp'
        if internal_col:
            rename_map[internal_col] = 'internal_temp'
        if room_col:
            rename_map[room_col] = 'room_temp'
        if wall_type_col:
            rename_map[wall_type_col] = 'wall_type'
        
        df = df.rename(columns=rename_map)
        
        # Strip trailing/leading spaces from wall_type values
        if 'wall_type' in df.columns:
            df['wall_type'] = df['wall_type'].astype(str).str.strip()
            # Fix typo: 'Yraka' should be 'Yarka'
            df['wall_type'] = df['wall_type'].replace('Yraka', 'Yarka')
        
        # Keep only needed columns
        keep_cols = ['timestamp', 'surface_temp', 'internal_temp', 'room_temp', 'wall_type']
        keep_cols = [c for c in keep_cols if c in df.columns]
        df = df[keep_cols]
        
        # Convert numeric columns
        for col in ['surface_temp', 'internal_temp', 'room_temp']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Check for missing values
        logger.info(f"\n  Missing value check:")
        for col in ['surface_temp', 'internal_temp', 'room_temp', 'wall_type']:
            if col in df.columns:
                missing_count = df[col].isna().sum()
                if missing_count > 0:
                    pct = (missing_count / len(df)) * 100
                    logger.warning(f"    ⚠ {col}: {missing_count} missing ({pct:.1f}%)")
                else:
                    logger.info(f"    ✓ {col}: no missing values")
        
        # Show sample data
        if len(df) > 0:
            logger.info(f"\n  Sample data from {filepath.name} (first valid row):")
            first_idx = df.index[0]
            logger.info(f"    timestamp:     {df.loc[first_idx, 'timestamp']}")
            if 'surface_temp' in df.columns:
                logger.info(f"    surface_temp:  {df.loc[first_idx, 'surface_temp']:.2f}°C")
            if 'internal_temp' in df.columns:
                logger.info(f"    internal_temp: {df.loc[first_idx, 'internal_temp']:.2f}°C")
            if 'room_temp' in df.columns:
                logger.info(f"    room_temp:     {df.loc[first_idx, 'room_temp']:.2f}°C")
            if 'wall_type' in df.columns:
                logger.info(f"    wall_type:     '{df.loc[first_idx, 'wall_type']}'")
                
                # Show wall type distribution
                wall_types = df['wall_type'].value_counts()
                logger.info(f"\n  Wall types in this file:")
                for wt, count in wall_types.items():
                    pct = (count / len(df)) * 100
                    logger.info(f"    '{wt}': {count} rows ({pct:.1f}%)")
        
        return df
    
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None


def load_period_data(period_folder):
    """
    Load all CSV files from a period folder.
    Returns a DataFrame with columns:
      surface_temp, internal_temp, room_temp, wall_type
    """
    logger.info(f"\n{'#'*80}")
    logger.info(f"# LOADING PERIOD: {Path(period_folder).name}")
    logger.info(f"# Path: {period_folder}")
    logger.info(f"{'#'*80}")
    
    folder_path = Path(period_folder)
    
    if not folder_path.exists():
        logger.error(f"❌ Folder not found: {period_folder}")
        return None
    
    csv_files = sorted(list(folder_path.glob("*.csv")))
    logger.info(f"\n📊 Found {len(csv_files)} CSV files")
    logger.info(f"   Files: {[f.name for f in csv_files[:5]]}{'...' if len(csv_files) > 5 else ''}")
    
    all_data = []
    success_count = 0
    fail_count = 0
    total_rows = 0
    
    for csv_file in csv_files:
        box_id, sensor_id = parse_filename(csv_file.name)
        
        if box_id is None or sensor_id is None:
            logger.error(f"❌ Skipping {csv_file.name} - could not parse filename")
            fail_count += 1
            continue
        
        wall_id, position = get_sensor_wall(sensor_id)
        logger.info(f"\n→ Box{box_id} / Sensor{sensor_id} / Wall{wall_id} / Position:{position}")
        
        df = load_csv_file(csv_file)
        
        if df is None or len(df) == 0:
            logger.warning(f"  ❌ Skipping - no valid data")
            fail_count += 1
            continue
        
        # Add metadata
        df['box_id'] = box_id
        df['sensor_id'] = sensor_id
        df['wall_id'] = wall_id
        df['position'] = position
        
        all_data.append(df)
        success_count += 1
        total_rows += len(df)
        logger.info(f"  ✓ SUCCESS: {len(df):,} rows loaded")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"PERIOD SUMMARY: {folder_path.name}")
    logger.info(f"{'='*80}")
    logger.info(f"  Files processed:  {len(csv_files)}")
    logger.info(f"  Successfully loaded: {success_count}")
    logger.info(f"  Failed:           {fail_count}")
    logger.info(f"  Total rows:       {total_rows:,}")
    
    if not all_data:
        logger.error(f"❌ No data loaded from {period_folder}")
        return None
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # Detailed file-to-sensor mapping
    logger.info(f"\n  File-to-Sensor Mapping:")
    logger.info(f"  {'File':<25} {'Box':<5} {'Sensor':<8} {'Wall':<6} {'Pos':<5} {'Rows':<8} {'Wall Types':<30}")
    logger.info(f"  {'-'*100}")
    for csv_file in csv_files:
        box_id, sensor_id = parse_filename(csv_file.name)
        if box_id and sensor_id:
            wall_id, position = get_sensor_wall(sensor_id)
            file_data = combined[(combined['box_id'] == box_id) & (combined['sensor_id'] == sensor_id)]
            if len(file_data) > 0:
                rows = len(file_data)
                wall_types = file_data['wall_type'].dropna().unique() if 'wall_type' in file_data.columns else []
                wall_types_str = ', '.join([str(wt) for wt in wall_types]) if len(wall_types) > 0 else 'N/A'
                if len(wall_types_str) > 28:
                    wall_types_str = wall_types_str[:25] + '...'
                logger.info(f"  {csv_file.name:<25} {box_id:<5} {sensor_id:<8} {wall_id or 'N/A':<6} {position or 'N/A':<5} {rows:<8,} {wall_types_str:<30}")
    
    # Sensor availability summary
    sensors_found = sorted(combined['sensor_id'].unique())
    sensors_missing = [s for s in range(1, 17) if s not in sensors_found]
    
    logger.info(f"\n  Sensor availability:")
    logger.info(f"    Found ({len(sensors_found)}):   {sensors_found}")
    if sensors_missing:
        logger.warning(f"    ⚠ Missing ({len(sensors_missing)}): {sensors_missing}")
    
    # Box/Wall breakdown
    logger.info(f"\n  Box and Wall breakdown:")
    for box_id in sorted(combined['box_id'].unique()):
        box_data = combined[combined['box_id'] == box_id]
        box_sensors = sorted(box_data['sensor_id'].unique())
        logger.info(f"    Box {box_id}: {len(box_sensors)} sensors → {box_sensors}")
        
        # Wall breakdown for this box
        for wall_id in sorted([1, 2, 3, 4]):
            wall_data = box_data[box_data['wall_id'] == wall_id]
            if len(wall_data) > 0:
                wall_sensors = sorted(wall_data['sensor_id'].unique())
                expected_out, expected_in = WALL_TOPOLOGY[wall_id]
                expected_sensors = sorted(expected_out + expected_in)
                out_sensors = sorted(wall_data[wall_data['position'] == 'out']['sensor_id'].unique())
                in_sensors = sorted(wall_data[wall_data['position'] == 'in']['sensor_id'].unique())
                logger.info(f"      Wall {wall_id}: {len(wall_sensors)}/{len(expected_sensors)} sensors | Out: {out_sensors}, In: {in_sensors}")
    
    logger.info(f"{'='*80}\n")
    
    return combined


def load_all_periods(base_folder='.'):
    """
    Load Period1 and Period2 data from data_cleaned folder.
    Returns dict: {'Period1': df1, 'Period2': df2}
    """
    logger.info(f"\n\n{'*'*80}")
    logger.info(f"{'*'*80}")
    logger.info(f"**  THERMAL EXPERIMENT DATA LOADING")
    logger.info(f"**  Base folder: {Path(base_folder).absolute()}")
    logger.info(f"{'*'*80}")
    logger.info(f"{'*'*80}\n")
    
    base_path = Path(base_folder)
    periods = {}
    
    # Load both Period1 and Period2
    for period_name in ['Period1', 'Period2']:
        period_path = base_path / period_name
        if period_path.exists():
            logger.info(f"\n\ud83d\udcc2 Found {period_name} folder at: {period_path}")
            df = load_period_data(period_path)
            if df is not None:
                df['period'] = period_name
                periods[period_name] = df
                logger.info(f"\u2713 {period_name} loaded successfully")
        else:
            logger.warning(f"⚠ Period folder not found: {period_path}")
    
    # Final summary
    logger.info(f"\n{'*'*80}")
    logger.info(f"FINAL DATA SUMMARY")
    logger.info(f"{'*'*80}")
    
    if not periods:
        logger.error(f"\u274c NO DATA LOADED!")
        return periods
    
    for period_name, df in periods.items():
        logger.info(f"\n{period_name}:")
        logger.info(f"  Total rows:    {len(df):,}")
        logger.info(f"  Unique sensors: {df['sensor_id'].nunique()}")
        logger.info(f"  Boxes:         {sorted(df['box_id'].unique())}")
        logger.info(f"  Time span:     {df['timestamp'].min()} to {df['timestamp'].max()}")
        logger.info(f"  Duration:      {(df['timestamp'].max() - df['timestamp'].min()).days} days")
        
        # Detailed sensor breakdown
        logger.info(f"\n  Detailed sensor breakdown:")
        for box_id in sorted(df['box_id'].unique()):
            box_df = df[df['box_id'] == box_id]
            sensors = sorted(box_df['sensor_id'].unique())
            logger.info(f"    Box {box_id}: {len(sensors)} sensors")
            for sensor_id in sensors:
                sensor_df = box_df[box_df['sensor_id'] == sensor_id]
                wall_id = sensor_df['wall_id'].iloc[0] if len(sensor_df) > 0 else '?'
                position = sensor_df['position'].iloc[0] if len(sensor_df) > 0 else '?'
                rows = len(sensor_df)
                missing_surface = sensor_df['surface_temp'].isna().sum()
                missing_internal = sensor_df['internal_temp'].isna().sum()
                missing_room = sensor_df['room_temp'].isna().sum()
                logger.info(f"      Sensor {sensor_id:2d} (Wall {wall_id}, {position:>3}): {rows:5,} rows | Missing: surf={missing_surface}, int={missing_internal}, room={missing_room}")
    
    logger.info(f"\n{'*'*80}\n")
    
    return periods
