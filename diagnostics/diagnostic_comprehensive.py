"""
Comprehensive diagnostic for cleaned data.
Shows: files per period, rows, missing values, files per box and wall.
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
import sys

# Fix encoding for file output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*100)
print("COMPREHENSIVE DIAGNOSTIC - CLEANED DATA")
print("="*100)

def extract_box_sensor(filename):
    """Extract box and sensor from filename."""
    # Remove period prefix if present
    name = filename.replace('Period1_', '').replace('Period2_', '')
    name = name.replace('.csv', '').replace('_121125', '').replace('_111025', '')
    name = name.replace('GW_', '').replace('GW', '')
    if '.' in name:
        parts = name.split('.')
        try:
            box = int(parts[0])
            sensor = int(parts[1])
            # Determine wall based on sensor number
            # Wall 1 (South): S1,S2 (out), S9,S10 (in)
            # Wall 2 (East): S3,S4 (out), S11,S12 (in)
            # Wall 3 (North): S5,S6 (out), S13,S14 (in)
            # Wall 4 (West): S7,S8 (out), S15,S16 (in)
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

# Analyze cleaned data
data_dir = Path('data_cleaned')

for period in ['Period1', 'Period2']:
    period_dir = data_dir / period
    
    if not period_dir.exists():
        print(f"\n{period}: Directory not found")
        continue
    
    print(f"\n{'='*100}")
    print(f"{period.upper()}")
    print(f"{'='*100}")
    
    csv_files = sorted(period_dir.glob('*.csv'))
    
    if not csv_files:
        print("  No files found")
        continue
    
    # Collect file info
    file_info = {}
    box_counts = defaultdict(int)
    wall_counts = defaultdict(lambda: defaultdict(int))  # box -> wall -> count
    total_rows = 0
    total_missing = defaultdict(int)  # column -> missing count
    
    for csv_file in csv_files:
        box, sensor, wall = extract_box_sensor(csv_file.name)
        
        if box:
            box_counts[box] += 1
            if wall:
                wall_counts[box][wall] += 1
        
        # Read file
        try:
            df = pd.read_csv(csv_file, header=14, encoding='utf-8')
            df.columns = df.columns.str.strip()
            
            # Find date column
            date_col = next((c for c in df.columns if 'date' in c.lower() and 'time' in c.lower()), None)
            
            if date_col:
                df['timestamp'] = pd.to_datetime(df[date_col], format='%m/%d/%Y %H:%M', errors='coerce')
                df_clean = df.dropna(subset=['timestamp'])
                
                # Count missing values in each column
                missing_info = {}
                for col in df_clean.columns:
                    if col != 'timestamp':
                        missing_count = df_clean[col].isna().sum()
                        if missing_count > 0:
                            missing_info[col] = missing_count
                            total_missing[col] += missing_count
                
                file_info[csv_file.name] = {
                    'rows': len(df_clean),
                    'start': df_clean['timestamp'].min(),
                    'end': df_clean['timestamp'].max(),
                    'missing': missing_info,
                    'box': box,
                    'sensor': sensor,
                    'wall': wall
                }
                
                total_rows += len(df_clean)
        except Exception as e:
            file_info[csv_file.name] = {
                'error': str(e),
                'box': box,
                'sensor': sensor,
                'wall': wall
            }
    
    # Print summary statistics
    print(f"\n📊 SUMMARY STATISTICS")
    print(f"-"*100)
    print(f"Total files: {len(csv_files)}")
    print(f"Total rows: {total_rows:,}")
    
    # Date range
    if file_info:
        all_starts = [info['start'] for info in file_info.values() if 'start' in info]
        all_ends = [info['end'] for info in file_info.values() if 'end' in info]
        if all_starts and all_ends:
            print(f"Date range: {min(all_starts)} to {max(all_ends)}")
    
    # Missing values summary
    print(f"\nMissing values across all files:")
    if total_missing:
        for col, count in sorted(total_missing.items()):
            print(f"  {col}: {count:,} missing values")
    else:
        print(f"  ✓ No missing values")
    
    # Box summary
    print(f"\n📦 FILES PER BOX")
    print(f"-"*100)
    for box in sorted(box_counts.keys()):
        sensors_present = sorted([info['sensor'] for info in file_info.values() 
                                 if info.get('box') == box and info.get('sensor')])
        missing_sensors = sorted(set(range(1, 17)) - set(sensors_present))
        
        print(f"Box{box}: {box_counts[box]} files ({len(sensors_present)}/16 sensors)")
        if missing_sensors:
            print(f"  Missing sensors: {missing_sensors}")
        else:
            print(f"  ✓ All sensors present")
    
    # Wall summary
    print(f"\n🧱 FILES PER WALL (per box)")
    print(f"-"*100)
    for box in sorted(wall_counts.keys()):
        print(f"Box{box}:")
        for wall in sorted(wall_counts[box].keys()):
            count = wall_counts[box][wall]
            print(f"  Wall {wall}: {count} files (expected 4)")
    
    # Detailed file listing
    print(f"\n📁 DETAILED FILE LIST")
    print(f"-"*100)
    
    # Group by box and wall
    for box in sorted(box_counts.keys()):
        print(f"\nBox{box}:")
        
        for wall in range(1, 5):
            wall_files = [(fname, info) for fname, info in file_info.items() 
                         if info.get('box') == box and info.get('wall') == wall]
            
            if wall_files:
                print(f"  Wall {wall}:")
                wall_files.sort(key=lambda x: x[1].get('sensor', 0))
                
                for fname, info in wall_files:
                    if 'error' in info:
                        print(f"    S{info.get('sensor', '?'):2d} | {fname:30s} | ERROR: {info['error']}")
                    else:
                        sensor = info.get('sensor', '?')
                        rows = info.get('rows', 0)
                        missing = info.get('missing', {})
                        
                        status = "✓" if not missing else "⚠"
                        print(f"    {status} S{sensor:2d} | {fname:30s} | {rows:5d} rows", end="")
                        
                        if missing:
                            missing_str = ", ".join(f"{k}({v})" for k, v in missing.items())
                            print(f" | MISSING: {missing_str}")
                        else:
                            print()

print(f"\n{'='*100}")
print("DIAGNOSTIC COMPLETE")
print(f"{'='*100}")

# Final readiness check
period1_exists = (data_dir / 'Period1').exists() and len(list((data_dir / 'Period1').glob('*.csv'))) > 0
period2_exists = (data_dir / 'Period2').exists() and len(list((data_dir / 'Period2').glob('*.csv'))) > 0

print(f"\n✓ READINESS CHECK:")
if period1_exists and period2_exists:
    print(f"  ✓ Both periods have data")
    print(f"  ✓ Ready to proceed with load -> transform -> plot")
else:
    print(f"  ⚠ Warning: Missing period data")

print(f"\n{'='*100}")
