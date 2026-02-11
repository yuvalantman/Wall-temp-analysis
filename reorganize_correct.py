"""
Reorganize data files correctly from data/updated folder:
- Period1: Files with dates 2025-10-23 to 2025-11-06
- Period2: Files with dates >= 2025-12-03 11:00:00
- Excluded: Files that don't fit criteria (marked with original period)
"""

import pandas as pd
from pathlib import Path
import shutil

print("="*100)
print("DATA REORGANIZATION - PROCESSING data/updated FOLDER")
print("="*100)

# Define date ranges
PERIOD1_START = pd.Timestamp('2025-10-23')
PERIOD1_END = pd.Timestamp('2025-11-06 23:59:59')
PERIOD2_START = pd.Timestamp('2025-12-03 11:00:00')
PERIOD2_END = pd.Timestamp('2025-12-11 11:59:59')

# Create output directories
output_dir = Path('data_cleaned')

# Clean up old directories if they exist
for old_dir in [output_dir / 'Period1', output_dir / 'Period2', output_dir / 'Excluded']:
    if old_dir.exists():
        for f in old_dir.glob('*'):
            f.unlink()

period1_dir = output_dir / 'Period1'
period2_dir = output_dir / 'Period2'
excluded_dir = output_dir / 'Excluded'

period1_dir.mkdir(parents=True, exist_ok=True)
period2_dir.mkdir(parents=True, exist_ok=True)
excluded_dir.mkdir(parents=True, exist_ok=True)

print(f"\nCreated fresh output directories:")
print(f"  - {period1_dir}")
print(f"  - {period2_dir}")
print(f"  - {excluded_dir}")

# Stats
stats = {
    'period1': {'files': [], 'rows': 0},
    'period2': {'files': [], 'rows': 0},
    'excluded': {'files': [], 'rows': 0}
}

# Process Period1 folder from data/updated
source_dir = Path('data/updated/Period1')
print(f"\nProcessing data/updated/Period1...")
print(f"{'='*100}")

for csv_file in sorted(source_dir.glob('*.csv')):
    print(f"\n  {csv_file.name}:")
    
    try:
        # Read file with multiple encoding attempts
        df = None
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                df = pd.read_csv(csv_file, header=14, encoding=encoding)
                break
            except:
                continue
        
        if df is None:
            raise ValueError("Could not read file")
        
        df.columns = df.columns.str.strip()
        
        # Find date column
        date_col = next((c for c in df.columns if 'date' in c.lower() and 'time' in c.lower()), None)
        
        if not date_col:
            print(f"    ERROR: No date column - moving to excluded")
            shutil.copy(csv_file, excluded_dir / f"Period1_{csv_file.name}")
            stats['excluded']['files'].append(f"Period1_{csv_file.name}")
            continue
        
        # Parse dates
        df['timestamp'] = pd.to_datetime(df[date_col], format='%m/%d/%Y %H:%M', errors='coerce')
        valid_df = df.dropna(subset=['timestamp'])
        
        if len(valid_df) == 0:
            print(f"    ERROR: No valid timestamps - moving to excluded")
            shutil.copy(csv_file, excluded_dir / f"Period1_{csv_file.name}")
            stats['excluded']['files'].append(f"Period1_{csv_file.name}")
            continue
        
        orig_start = valid_df['timestamp'].min()
        orig_end = valid_df['timestamp'].max()
        print(f"    Date range: {orig_start} to {orig_end} ({len(valid_df)} rows)")
        
        # Check if this belongs in Period1 (Oct 23 - Nov 6)
        if orig_start >= PERIOD1_START and orig_end <= PERIOD1_END:
            # Perfect Period1 file
            print(f"    ✓ Belongs in Period1")
            
            # Copy file with filtered data
            with open(csv_file, 'r', encoding='latin-1') as f:
                header_lines = [f.readline() for _ in range(14)]
            
            output_file = period1_dir / csv_file.name
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                for line in header_lines:
                    f.write(line)
                valid_df.drop('timestamp', axis=1).to_csv(f, index=False, header=True, lineterminator='\n')
            
            stats['period1']['files'].append(csv_file.name)
            stats['period1']['rows'] += len(valid_df)
        else:
            # Doesn't fit Period1 criteria
            print(f"    ✗ Date range outside Period1 - moving to excluded")
            shutil.copy(csv_file, excluded_dir / f"Period1_{csv_file.name}")
            stats['excluded']['files'].append(f"Period1_{csv_file.name}")
            stats['excluded']['rows'] += len(valid_df)
    
    except Exception as e:
        print(f"    ERROR: {e}")
        shutil.copy(csv_file, excluded_dir / f"Period1_{csv_file.name}")
        stats['excluded']['files'].append(f"Period1_{csv_file.name}")

# Process Period2 folder from data/updated
source_dir = Path('data/updated/Period2')
print(f"\nProcessing data/updated/Period2...")
print(f"{'='*100}")

for csv_file in sorted(source_dir.glob('*.csv')):
    print(f"\n  {csv_file.name}:")
    
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
            raise ValueError("Could not read file")
        
        df.columns = df.columns.str.strip()
        
        # Find date column
        date_col = next((c for c in df.columns if 'date' in c.lower() and 'time' in c.lower()), None)
        
        if not date_col:
            print(f"    ERROR: No date column - moving to excluded")
            shutil.copy(csv_file, excluded_dir / f"Period2_{csv_file.name}")
            stats['excluded']['files'].append(f"Period2_{csv_file.name}")
            continue
        
        # Parse dates
        df['timestamp'] = pd.to_datetime(df[date_col], format='%m/%d/%Y %H:%M', errors='coerce')
        valid_df = df.dropna(subset=['timestamp'])
        
        if len(valid_df) == 0:
            print(f"    ERROR: No valid timestamps - moving to excluded")
            shutil.copy(csv_file, excluded_dir / f"Period2_{csv_file.name}")
            stats['excluded']['files'].append(f"Period2_{csv_file.name}")
            continue
        
        orig_start = valid_df['timestamp'].min()
        orig_end = valid_df['timestamp'].max()
        print(f"    Date range: {orig_start} to {orig_end} ({len(valid_df)} rows)")
        
        # Check if this file has data from Dec 3 11:00 onwards
        if orig_start >= PERIOD2_START:
            # Filter to only keep data up to Dec 11 11:59:59
            period2_data = valid_df[valid_df['timestamp'] <= PERIOD2_END]
            
            if len(period2_data) > 0:
                print(f"    ✓ Data from Dec 3 11:00 to Dec 11 11:59:59 - keeping {len(period2_data)} rows for Period2")
                
                with open(csv_file, 'r', encoding='latin-1') as f:
                    header_lines = [f.readline() for _ in range(14)]
                
                output_file = period2_dir / csv_file.name
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    for line in header_lines:
                        f.write(line)
                    period2_data.drop('timestamp', axis=1).to_csv(f, index=False, header=True, lineterminator='\n')
                
                stats['period2']['files'].append(csv_file.name)
                stats['period2']['rows'] += len(period2_data)
            else:
                print(f"    ✗ No data within Period2 range - moving to excluded")
                shutil.copy(csv_file, excluded_dir / f"Period2_{csv_file.name}")
                stats['excluded']['files'].append(f"Period2_{csv_file.name}")
                stats['excluded']['rows'] += len(valid_df)
            
        elif orig_end >= PERIOD2_START:
            # File spans multiple periods - filter to keep only Dec 3 11:00 to Dec 11 11:59:59
            period2_data = valid_df[(valid_df['timestamp'] >= PERIOD2_START) & 
                                   (valid_df['timestamp'] <= PERIOD2_END)]
            
            if len(period2_data) > 0:
                print(f"    ✓ Filtered to Dec 3 11:00 - Dec 11 11:59:59 - keeping {len(period2_data)} rows for Period2")
                
                with open(csv_file, 'r', encoding='latin-1') as f:
                    header_lines = [f.readline() for _ in range(14)]
                
                output_file = period2_dir / csv_file.name
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    for line in header_lines:
                        f.write(line)
                    period2_data.drop('timestamp', axis=1).to_csv(f, index=False, header=True, lineterminator='\n')
                
                stats['period2']['files'].append(csv_file.name)
                stats['period2']['rows'] += len(period2_data)
            else:
                print(f"    ✗ No data from Dec 3 11:00+ - moving to excluded")
                shutil.copy(csv_file, excluded_dir / f"Period2_{csv_file.name}")
                stats['excluded']['files'].append(f"Period2_{csv_file.name}")
                stats['excluded']['rows'] += len(valid_df)
        
        elif orig_start >= PERIOD1_START and orig_end <= PERIOD1_END:
            # This is actually Period1 data (Oct 23 - Nov 6)
            print(f"    ✗ This is Period1 data (Oct 23 - Nov 6) - moving to excluded")
            shutil.copy(csv_file, excluded_dir / f"Period2_{csv_file.name}")
            stats['excluded']['files'].append(f"Period2_{csv_file.name}")
            stats['excluded']['rows'] += len(valid_df)
        
        else:
            # Doesn't fit any criteria
            print(f"    ✗ Date range doesn't fit Period2 criteria - moving to excluded")
            shutil.copy(csv_file, excluded_dir / f"Period2_{csv_file.name}")
            stats['excluded']['files'].append(f"Period2_{csv_file.name}")
            stats['excluded']['rows'] += len(valid_df)
    
    except Exception as e:
        print(f"    ERROR: {e}")
        shutil.copy(csv_file, excluded_dir / f"Period2_{csv_file.name}")
        stats['excluded']['files'].append(f"Period2_{csv_file.name}")

# Summary
print(f"\n\n{'='*100}")
print("REORGANIZATION SUMMARY")
print(f"{'='*100}")

print(f"\nPeriod1 ({PERIOD1_START.date()} to {PERIOD1_END.date()}):")
print(f"  Files: {len(stats['period1']['files'])}")
print(f"  Total rows: {stats['period1']['rows']:,}")
if stats['period1']['files']:
    for f in stats['period1']['files']:
        print(f"    - {f}")

print(f"\nPeriod2 (from {PERIOD2_START}):")
print(f"  Files: {len(stats['period2']['files'])}")
print(f"  Total rows: {stats['period2']['rows']:,}")
if stats['period2']['files']:
    for f in stats['period2']['files']:
        print(f"    - {f}")

print(f"\nExcluded:")
print(f"  Files: {len(stats['excluded']['files'])}")
print(f"  Total rows: {stats['excluded']['rows']:,}")
if stats['excluded']['files']:
    for f in stats['excluded']['files']:
        print(f"    - {f}")

print(f"\n{'='*100}")
print("✓ Data reorganized successfully!")
print(f"{'='*100}")
