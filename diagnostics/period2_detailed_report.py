"""
Comprehensive Period2 Original Data Report.
Shows: timestamps, rows after Dec 3 11:00, missing values, per box/wall breakdown.
Includes 8 sample timestamps with actual data values.
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*100)
print("PERIOD2 ORIGINAL DATA - COMPREHENSIVE REPORT")
print("="*100)

def extract_box_sensor_wall(filename):
    """Extract box, sensor, wall from filename."""
    name = filename.replace('.csv', '').replace('_121125', '').replace('_111025', '')
    name = name.replace('GW_', '').replace('GW', '')
    if '.' in name:
        parts = name.split('.')
        try:
            box = int(parts[0])
            sensor = int(parts[1])
            # Determine wall
            if sensor in [1, 2, 9, 10]:
                wall = 1
            elif sensor in [3, 4, 11, 12]:
                wall = 2
            elif sensor in [5, 6, 13, 14]:
                wall = 3
            elif sensor in [7, 8, 15, 16]:
                wall = 4
            else:
                wall = None
            return box, sensor, wall
        except:
            pass
    return None, None, None

# Process Period2 original data
source_dir = Path('data/Period2')
PERIOD2_START = pd.Timestamp('2025-12-03 11:00:00')
PERIOD2_END = pd.Timestamp('2025-12-11 12:00:00')

# Collect all file info
file_info = {}
box_counts = defaultdict(int)
wall_counts = defaultdict(lambda: defaultdict(int))
total_missing = defaultdict(int)

print(f"\n{'='*100}")
print("KNOWN PROBLEMATIC SENSORS")
print(f"{'='*100}\n")
print("Box 1:")
print("  - Sensor 7: Contains Period1 dates (Oct 23 - Nov 6) instead of Period2")
print("  - Sensor 8: Missing most rows (Nov 27 start) and has unmatching data compared to other sensors")
print("  - Sensor 14: Contains Period1 dates (Oct 23 - Nov 6) instead of Period2")
print("\nBox 2:")
print("  - Sensor 1: Only 1 row after Dec 3 11:00 (file starts Nov 27)")
print("  - Sensor 3: Contains Period1 dates (Oct 23 - Nov 6) instead of Period2")
print("  - Sensor 5: File missing from folder entirely")
print("  - Sensor 6: Contains Period1 dates (Oct 23 - Nov 6) instead of Period2")
print("  - Sensor 8: Only 1 row after Dec 3 11:00 (file starts Nov 27)")
print("  - Sensor 9: File missing from folder entirely")
print("  - Sensor 11: File missing from folder entirely")
print("  - Sensor 13: Only 1 row after Dec 3 11:00 (file starts Nov 27)")

print(f"\n{'='*100}")
print(f"ANALYZING ALL FILES IN data/Period2/")
print(f"Valid date range: {PERIOD2_START} to {PERIOD2_END}")
print(f"{'='*100}\n")

for csv_file in sorted(source_dir.glob('*.csv')):
    box, sensor, wall = extract_box_sensor_wall(csv_file.name)
    
    print(f"{csv_file.name}:")
    
    try:
        # Read file
        df = None
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                df = pd.read_csv(csv_file, header=14, encoding=encoding)
                break
            except:
                continue
        
        if df is None:
            print(f"  ERROR: Could not read file\n")
            continue
        
        df.columns = df.columns.str.strip()
        
        # Find date column
        date_col = next((c for c in df.columns if 'date' in c.lower() and 'time' in c.lower()), None)
        
        if not date_col:
            print(f"  ERROR: No date column\n")
            continue
        
        # Parse dates
        df['timestamp'] = pd.to_datetime(df[date_col], format='%m/%d/%Y %H:%M', errors='coerce')
        df_clean = df.dropna(subset=['timestamp'])
        
        if len(df_clean) == 0:
            print(f"  ERROR: No valid timestamps\n")
            continue
        
        # Get overall info
        orig_start = df_clean['timestamp'].min()
        orig_end = df_clean['timestamp'].max()
        orig_rows = len(df_clean)
        
        # Filter for Period2 (Dec 3 11:00 to Dec 11 12:00)
        period2_data = df_clean[(df_clean['timestamp'] >= PERIOD2_START) & 
                                (df_clean['timestamp'] <= PERIOD2_END)]
        period2_rows = len(period2_data)
        
        # Count missing values in period2 data and track timestamps
        missing_info = {}
        missing_timestamps = {}
        for col in df_clean.columns:
            if col != 'timestamp':
                missing_mask = period2_data[col].isna()
                missing_count = missing_mask.sum()
                if missing_count > 0:
                    missing_info[col] = missing_count
                    total_missing[col] += missing_count
                    # Store timestamps if count < 7
                    if missing_count < 7:
                        missing_timestamps[col] = period2_data[missing_mask]['timestamp'].tolist()
        
        # Store info
        file_info[csv_file.name] = {
            'box': box,
            'sensor': sensor,
            'wall': wall,
            'orig_start': orig_start,
            'orig_end': orig_end,
            'orig_rows': orig_rows,
            'period2_rows': period2_rows,
            'missing': missing_info,
            'missing_timestamps': missing_timestamps,
            'data': period2_data
        }
        
        if box:
            box_counts[box] += 1
            if wall:
                wall_counts[box][wall] += 1
        
        # Print file details
        print(f"  Original range: {orig_start} to {orig_end} ({orig_rows} rows)")
        
        # Flag files with different start date
        if orig_start.date() != pd.Timestamp('2025-12-03').date():
            print(f"  [WARNING] Starts on {orig_start.date()} (not Dec 3)")
        
        print(f"  After Dec 3 11:00: {period2_rows} rows", end='')
        
        # Flag files with less than 5 rows
        if period2_rows < 5:
            print(f" [VERY LOW ROW COUNT]")
        else:
            print()
        
        if missing_info:
            print(f"  Missing values: {', '.join(f'{k}({v})' for k, v in missing_info.items())}")
            # Print timestamps if missing count < 7
            for col, ts_list in missing_timestamps.items():
                print(f"    {col} missing at: {', '.join(str(ts) for ts in ts_list)}")
        else:
            print(f"  Missing values: None")
        print()
    
    except Exception as e:
        print(f"  ERROR: {e}\n")

# Summary statistics
print(f"\n{'='*100}")
print("SUMMARY STATISTICS")
print(f"{'='*100}\n")

print(f"Total files analyzed: {len(file_info)}")
total_period2_rows = sum(info['period2_rows'] for info in file_info.values())
print(f"Total rows in valid range (Dec 3 11:00 - Dec 11 12:00): {total_period2_rows:,}")

print(f"\nMissing values (in valid range):")
if total_missing:
    for col, count in sorted(total_missing.items()):
        print(f"  {col}: {count:,}")
else:
    print(f"  None")

# Box summary
print(f"\n{'='*100}")
print("FILES PER BOX")
print(f"{'='*100}\n")

# First, identify which sensors are missing from the folder entirely
all_sensors_box1 = set(range(1, 17))
all_sensors_box2 = set(range(1, 17))
present_sensors_box1 = set([info['sensor'] for info in file_info.values() 
                           if info.get('box') == 1 and info.get('sensor')])
present_sensors_box2 = set([info['sensor'] for info in file_info.values() 
                           if info.get('box') == 2 and info.get('sensor')])

missing_from_folder_box1 = sorted(all_sensors_box1 - present_sensors_box1)
missing_from_folder_box2 = sorted(all_sensors_box2 - present_sensors_box2)

if missing_from_folder_box2:
    print(f"NOTE: Box 2 sensor files {missing_from_folder_box2} are MISSING FROM THE FOLDER (not just lacking data)\n")

for box in sorted(box_counts.keys()):
    sensors_present = sorted([info['sensor'] for info in file_info.values() 
                             if info.get('box') == box and info.get('sensor')])
    missing_sensors = sorted(set(range(1, 17)) - set(sensors_present))
    
    print(f"Box{box}: {box_counts[box]} files ({len(sensors_present)}/16 sensors)")
    if missing_sensors:
        print(f"  Missing sensor files: {missing_sensors}")
    else:
        print(f"  All sensor files present")

# Wall summary
print(f"\n{'='*100}")
print("FILES PER WALL (per box)")
print(f"{'='*100}\n")

for box in sorted(wall_counts.keys()):
    print(f"Box{box}:")
    for wall in sorted(wall_counts[box].keys()):
        count = wall_counts[box][wall]
        print(f"  Wall {wall}: {count} files (expected 4)")

# Sample timestamps - 8 random timestamps, 1 per day
print(f"\n{'='*100}")
print("SAMPLE DATA AT 8 TIMESTAMPS (1 per day)")
print(f"{'='*100}\n")

# Get all dates with data after Dec 3 11:00
all_timestamps = set()
for info in file_info.values():
    if 'data' in info:
        all_timestamps.update(info['data']['timestamp'].tolist())

if all_timestamps:
    all_timestamps = sorted(all_timestamps)
    
    # Group by date
    dates_dict = defaultdict(list)
    for ts in all_timestamps:
        dates_dict[ts.date()].append(ts)
    
    # Sample 1 timestamp per day (up to 8 days)
    sample_timestamps = []
    for date in sorted(dates_dict.keys())[:8]:
        # Pick timestamps around noon or midday
        day_timestamps = dates_dict[date]
        # Find timestamp closest to noon
        noon = pd.Timestamp(date.year, date.month, date.day, 12, 0, 0)
        closest = min(day_timestamps, key=lambda x: abs((x - noon).total_seconds()))
        sample_timestamps.append(closest)
    
    print(f"Selected {len(sample_timestamps)} sample timestamps:\n")
    
    for i, ts in enumerate(sample_timestamps, 1):
        print(f"\n{'='*100}")
        print(f"TIMESTAMP {i}: {ts}")
        print(f"{'='*100}")
        
        # Collect all room temps for this timestamp to find min/max
        room_temps = {}
        
        # First pass: collect all data
        for fname, info in file_info.items():
            if 'data' in info:
                data = info['data']
                # Look for timestamps within 5 minutes of target
                time_window = data[(data['timestamp'] >= ts - pd.Timedelta(minutes=5)) & 
                                  (data['timestamp'] <= ts + pd.Timedelta(minutes=5))]
                
                if len(time_window) > 0:
                    # Use closest timestamp
                    closest_idx = (time_window['timestamp'] - ts).abs().idxmin()
                    row = time_window.loc[closest_idx]
                    room = row.get('Out Air temp')
                    if pd.notna(room):
                        room_temps[fname] = float(room)
        
        # Find min/max room temps
        max_room_file = max(room_temps.items(), key=lambda x: x[1])[0] if room_temps else None
        min_room_file = min(room_temps.items(), key=lambda x: x[1])[0] if room_temps else None
        
        # Group by box
        for box in sorted(box_counts.keys()):
            print(f"\nBox{box}:")
            print(f"{'-'*100}")
            
            # Get files for this box
            box_files = [(fname, info) for fname, info in file_info.items() 
                        if info.get('box') == box]
            box_files.sort(key=lambda x: x[1].get('sensor', 0))
            
            # Print header
            print(f"{'Sensor':<8} {'File':<30} {'Surface Temp':<15} {'Internal Temp':<15} {'Room Temp':<12} {'Wall Type':<15} {'Flags':<20}")
            print(f"{'-'*100}")
            
            for fname, info in box_files:
                sensor = info.get('sensor', '?')
                
                if 'data' in info:
                    # Find row near this timestamp (within 5 minutes)
                    data = info['data']
                    time_window = data[(data['timestamp'] >= ts - pd.Timedelta(minutes=5)) & 
                                      (data['timestamp'] <= ts + pd.Timedelta(minutes=5))]
                    
                    if len(time_window) > 0:
                        # Use the row with timestamp closest to target
                        closest_idx = (time_window['timestamp'] - ts).abs().idxmin()
                        row = time_window.loc[closest_idx]
                        
                        # Get column values
                        surface = row.get('Value Heat Surface Sensor', 'N/A')
                        internal = row.get('Internal temp sensor', 'N/A')
                        room = row.get('Out Air temp', 'N/A')
                        wall_type = row.get('Wall Type', 'N/A')
                        
                        if pd.isna(surface):
                            surface = 'N/A'
                        if pd.isna(internal):
                            internal = 'N/A'
                        if pd.isna(room):
                            room = 'N/A'
                        if pd.isna(wall_type):
                            wall_type = 'N/A'
                        else:
                            wall_type = str(wall_type).strip()
                        
                        # Flag min/max room temps
                        flags = []
                        if fname == max_room_file:
                            flags.append("MAX ROOM TEMP")
                        if fname == min_room_file:
                            flags.append("MIN ROOM TEMP")
                        flag_str = ', '.join(flags)
                        
                        print(f"S{sensor:<7} {fname:<30} {str(surface):<15} {str(internal):<15} {str(room):<12} {wall_type:<15} {flag_str:<20}")
                    else:
                        print(f"S{sensor:<7} {fname:<30} {'NO DATA':<15} {'NO DATA':<15} {'NO DATA':<12} {'NO DATA':<15} {'':<20}")
                else:
                    print(f"S{sensor:<7} {fname:<30} {'ERROR':<15} {'ERROR':<15} {'ERROR':<12} {'ERROR':<15} {'':<20}")

else:
    print("No timestamps available for sampling")

print(f"\n{'='*100}")
print("REPORT COMPLETE")
print(f"{'='*100}")
