"""
Diagnostic analysis for updated data in data/updated folder.
Analyzes Period1 and Period2 CSV files for completeness and date ranges.
"""

import pandas as pd
from pathlib import Path
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Temporarily disable the load.py logging to avoid emoji issues
logging.getLogger('src.load').setLevel(logging.CRITICAL)


def load_csv_simple(filepath):
    """Load CSV file without logging."""
    try:
        df = None
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                df = pd.read_csv(filepath, header=14, encoding=encoding)
                break
            except (UnicodeDecodeError, Exception):
                continue
        
        if df is None:
            return None
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Find date column
        date_col = None
        for col in df.columns:
            if 'date' in col or 'time' in col or col.startswith('m/'):
                date_col = col
                break
        
        if date_col is None:
            date_col = df.columns[0]
        
        # Clean data - stop at rows with too many NaN
        clean_rows = []
        for idx, row in df.iterrows():
            if row.isna().sum() >= 2:  # If 2+ required columns missing
                break
            clean_rows.append(idx)
        
        if clean_rows:
            df = df.loc[clean_rows].copy()
        
        return df
    
    except Exception:
        return None


def analyze_file(filepath):
    """Analyze a single CSV file and return diagnostic info."""
    try:
        # Load the file
        df = load_csv_simple(filepath)
        
        if df is None or len(df) == 0:
            return {
                'filepath': filepath,
                'status': 'FAILED',
                'error': 'Could not parse file or empty',
                'rows': 0
            }
        
        # Extract info
        date_col = df.columns[0]  # First column is date
        dates = pd.to_datetime(df[date_col], errors='coerce')
        
        return {
            'filepath': filepath,
            'status': 'SUCCESS',
            'rows': len(df),
            'min_date': dates.min(),
            'max_date': dates.max(),
            'has_nulls': df.isnull().any().any(),
            'null_count': df.isnull().sum().sum(),
            'date_column': date_col,
            'data': df,
            'dates': dates
        }
    
    except Exception as e:
        return {
            'filepath': filepath,
            'status': 'ERROR',
            'error': str(e),
            'rows': 0
        }


def check_date_range(dates, period):
    """Check if dates fall within expected range."""
    if period == 'Period1':
        # October 23 to November 6, 2025
        start = pd.Timestamp('2025-10-23')
        end = pd.Timestamp('2025-11-06 23:59:59')
    else:  # Period2
        # December 3 after 11:00:00 to December 11 before 12:00:00, 2025
        start = pd.Timestamp('2025-12-03 11:00:00')
        end = pd.Timestamp('2025-12-11 11:59:59')
    
    valid_dates = dates[(dates >= start) & (dates <= end)]
    invalid_dates = dates[(dates < start) | (dates > end)]
    
    return {
        'valid_count': len(valid_dates),
        'invalid_count': len(invalid_dates),
        'total_count': len(dates),
        'percent_valid': (len(valid_dates) / len(dates) * 100) if len(dates) > 0 else 0,
        'invalid_dates': invalid_dates.tolist() if len(invalid_dates) < 10 else None
    }


def analyze_period(period_path, period_name):
    """Analyze all files in a period folder."""
    print(f"\n{'='*80}")
    print(f"ANALYZING {period_name}")
    print(f"{'='*80}\n")
    
    csv_files = sorted(period_path.glob("*.csv"))
    
    if not csv_files:
        print(f"[X] No CSV files found in {period_path}")
        return
    
    print(f"Found {len(csv_files)} CSV files\n")
    
    results = []
    for csv_file in csv_files:
        result = analyze_file(csv_file)
        results.append(result)
    
    # Summary by status
    success_files = [r for r in results if r['status'] == 'SUCCESS']
    failed_files = [r for r in results if r['status'] != 'SUCCESS']
    
    print(f"OVERALL SUMMARY")
    print(f"{'-'*80}")
    print(f"  Total files: {len(results)}")
    print(f"  [+] Successfully parsed: {len(success_files)}")
    print(f"  [-] Failed to parse: {len(failed_files)}")
    
    if failed_files:
        print(f"\n[X] FAILED FILES:")
        for f in failed_files:
            print(f"  - {f['filepath'].name}: {f.get('error', 'Unknown error')}")
    
    if not success_files:
        return
    
    # Date range analysis
    print(f"\nDATE RANGE ANALYSIS")
    print(f"{'-'*80}")
    
    date_results = []
    for r in success_files:
        filename = r['filepath'].name
        dates = r['dates']
        date_check = check_date_range(dates, period_name)
        
        date_results.append({
            'filename': filename,
            'rows': r['rows'],
            'min_date': r['min_date'],
            'max_date': r['max_date'],
            'valid_rows': date_check['valid_count'],
            'invalid_rows': date_check['invalid_count'],
            'percent_valid': date_check['percent_valid'],
            'invalid_dates': date_check['invalid_dates']
        })
        
        status = "[+]" if date_check['percent_valid'] == 100 else "[!]"
        print(f"{status} {filename}")
        print(f"   Rows: {r['rows']:,} | Valid: {date_check['valid_count']:,} ({date_check['percent_valid']:.1f}%)")
        print(f"   Date range: {r['min_date']} → {r['max_date']}")
        
        if date_check['invalid_count'] > 0 and date_check['invalid_dates'] is not None:
            print(f"   Invalid dates ({date_check['invalid_count']} total):")
            for invalid_date in date_check['invalid_dates'][:10]:
                print(f"     - {invalid_date}")
        elif date_check['invalid_count'] > 0:
            print(f"   Invalid dates: {date_check['invalid_count']} (too many to list)")
        print()
    
    # Per-box analysis
    print(f"\nPER-BOX ANALYSIS")
    print(f"{'-'*80}")
    
    box1_files = [r for r in success_files if 'GW1.' in r['filepath'].name]
    box2_files = [r for r in success_files if 'GW2.' in r['filepath'].name]
    
    print(f"Box 1 (Control):")
    print(f"  Files: {len(box1_files)}/16 expected")
    print(f"  Total rows: {sum(r['rows'] for r in box1_files):,}")
    box1_valid = sum(check_date_range(r['dates'], period_name)['valid_count'] for r in box1_files)
    print(f"  Valid date rows: {box1_valid:,}")
    
    print(f"\nBox 2 (Experimental):")
    print(f"  Files: {len(box2_files)}/16 expected")
    print(f"  Total rows: {sum(r['rows'] for r in box2_files):,}")
    box2_valid = sum(check_date_range(r['dates'], period_name)['valid_count'] for r in box2_files)
    print(f"  Valid date rows: {box2_valid:,}")
    
    # Per-wall analysis
    print(f"\nPER-WALL ANALYSIS")
    print(f"{'-'*80}")
    
    for wall_id in [1, 2, 3, 4]:
        # Sensors for each wall
        if wall_id == 1:
            sensors = [1, 2, 9, 10]
        elif wall_id == 2:
            sensors = [3, 4, 11, 12]
        elif wall_id == 3:
            sensors = [5, 6, 13, 14]
        else:  # wall_id == 4
            sensors = [7, 8, 15, 16]
        
        print(f"\nWall {wall_id} (Sensors {sensors}):")
        
        for box_id in [1, 2]:
            box_name = "Control" if box_id == 1 else "Experimental"
            wall_files = [r for r in success_files 
                         if f"{box_id}." in r['filepath'].name 
                         and any(f"{box_id}.{s}_" in r['filepath'].name for s in sensors)]
            
            wall_valid = sum(check_date_range(r['dates'], period_name)['valid_count'] for r in wall_files)
            print(f"  {box_name}: {len(wall_files)}/4 files, {wall_valid:,} valid rows")
    
    # Rows per day analysis
    print(f"\nROWS PER DAY ANALYSIS")
    print(f"{'-'*80}")
    
    # Use first successful file as sample
    sample = success_files[0]
    dates = sample['dates']
    dates_clean = dates.dropna()
    
    if len(dates_clean) > 0:
        days = dates_clean.dt.date.value_counts().sort_index()
        
        print(f"Sample file: {sample['filepath'].name}")
        print(f"Expected: 144 rows/day (10-minute intervals)")
        print(f"\nDaily breakdown:")
        for day, count in days.items():
            status = "[+]" if count == 144 else "[!]"
            print(f"  {status} {day}: {count} rows")
        
        avg_per_day = days.mean()
        print(f"\nAverage: {avg_per_day:.1f} rows/day")
    
    # Missing values analysis
    print(f"\nMISSING VALUES ANALYSIS")
    print(f"{'-'*80}")
    
    for r in success_files[:5]:  # Check first 5 files
        filename = r['filepath'].name
        df = r['data']
        
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()
        
        if total_nulls == 0:
            print(f"[+] {filename}: No missing values")
        elif total_nulls < 10:
            print(f"[!] {filename}: {total_nulls} missing values")
            
            # Find which rows have missing values
            rows_with_nulls = df[df.isnull().any(axis=1)].index.tolist()
            print(f"   Rows with missing values: {rows_with_nulls}")
            
            # Show which columns
            cols_with_nulls = null_counts[null_counts > 0]
            for col, count in cols_with_nulls.items():
                print(f"   - {col}: {count} missing")
        else:
            print(f"[-] {filename}: {total_nulls} missing values (too many)")
            cols_with_nulls = null_counts[null_counts > 0]
            for col, count in cols_with_nulls.items():
                print(f"   - {col}: {count} missing")
    
    if len(success_files) > 5:
        print(f"\n... and {len(success_files) - 5} more files not shown")
    
    # Row samples for data alignment check
    print(f"\nROW SAMPLES FOR DATA ALIGNMENT")
    print(f"{'-'*100}")
    print(f"Random timestamp from each day - showing all sensor values per box\n")
    
    # Get all unique dates from first successful file
    if success_files:
        sample_dates = success_files[0]['dates'].dropna()
        unique_days = sample_dates.dt.date.unique()
        
        import random
        random.seed(42)  # For reproducibility
        
        for day in sorted(unique_days):
            # Get all timestamps for this day
            day_timestamps = sample_dates[sample_dates.dt.date == day]
            
            if len(day_timestamps) == 0:
                continue
            
            # Pick timestamp closest to noon
            noon = pd.Timestamp(day.year, day.month, day.day, 12, 0, 0)
            closest_ts = min(day_timestamps.tolist(), key=lambda x: abs((x - noon).total_seconds()))
            
            print(f"\n{'='*100}")
            print(f"Day: {day} | Sample Timestamp: {closest_ts}")
            print(f"{'='*100}")
            
            # Collect all room temps to find min/max
            room_temps = {}
            
            # First pass: collect all data
            for r in success_files:
                filename = r['filepath'].name
                df = r['data']
                dates = r['dates']
                
                # Find row within 5 minutes of target timestamp
                time_window_mask = (dates >= closest_ts - pd.Timedelta(minutes=5)) & \
                                   (dates <= closest_ts + pd.Timedelta(minutes=5))
                matching_rows = dates[time_window_mask]
                
                if len(matching_rows) > 0:
                    # Use closest timestamp
                    closest_idx = (matching_rows - closest_ts).abs().idxmin()
                    row = df.loc[closest_idx]
                    
                    # Find room temp column
                    room_col = None
                    for col in df.columns:
                        if 'air' in col.lower() and 'temp' in col.lower():
                            room_col = col
                            break
                    
                    if room_col and pd.notna(row.get(room_col)):
                        room_temps[filename] = float(row[room_col])
            
            # Find min/max room temps
            max_room_file = max(room_temps.items(), key=lambda x: x[1])[0] if room_temps else None
            min_room_file = min(room_temps.items(), key=lambda x: x[1])[0] if room_temps else None
            
            # Group files by box
            box1_files = sorted([r for r in success_files if ('GW1.' in r['filepath'].name or '_1.' in r['filepath'].name)], 
                               key=lambda x: x['filepath'].name)
            box2_files = sorted([r for r in success_files if ('GW2.' in r['filepath'].name or '_2.' in r['filepath'].name)], 
                               key=lambda x: x['filepath'].name)
            
            # Print Box 1
            print(f"\nBox 1 (CONTROL) - {len(box1_files)} files:")
            print(f"{'-'*100}")
            print(f"{'Sensor':<8} {'File':<30} {'Surface Temp':<15} {'Internal Temp':<15} {'Room Temp':<12} {'Wall Type':<15} {'Flags':<20}")
            print(f"{'-'*100}")
            
            for r in box1_files:
                filename = r['filepath'].name
                df = r['data']
                dates = r['dates']
                
                # Extract sensor number
                sensor = filename.split('.')[1].split('_')[0] if '.' in filename else '?'
                
                # Find row within 5 minutes
                time_window_mask = (dates >= closest_ts - pd.Timedelta(minutes=5)) & \
                                   (dates <= closest_ts + pd.Timedelta(minutes=5))
                matching_rows = dates[time_window_mask]
                
                if len(matching_rows) > 0:
                    closest_idx = (matching_rows - closest_ts).abs().idxmin()
                    row = df.loc[closest_idx]
                    
                    # Extract values
                    surface = internal = room = wall_type = 'N/A'
                    
                    for col in df.columns:
                        if 'surface' in col.lower() and 'heat' in col.lower():
                            surface = row.get(col, 'N/A')
                        elif 'internal' in col.lower() and 'temp' in col.lower():
                            internal = row.get(col, 'N/A')
                        elif 'air' in col.lower() and 'temp' in col.lower():
                            room = row.get(col, 'N/A')
                        elif 'wall' in col.lower() and 'type' in col.lower():
                            wall_type = row.get(col, 'N/A')
                    
                    # Format values
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
                    
                    # Flags
                    flags = []
                    if filename == max_room_file:
                        flags.append("MAX ROOM TEMP")
                    if filename == min_room_file:
                        flags.append("MIN ROOM TEMP")
                    flag_str = ', '.join(flags)
                    
                    print(f"S{sensor:<7} {filename:<30} {str(surface):<15} {str(internal):<15} {str(room):<12} {wall_type:<15} {flag_str:<20}")
                else:
                    print(f"S{sensor:<7} {filename:<30} {'NO DATA':<15} {'NO DATA':<15} {'NO DATA':<12} {'NO DATA':<15} {'':<20}")
            
            # Print Box 2
            print(f"\n\nBox 2 (EXPERIMENTAL) - {len(box2_files)} files:")
            print(f"{'-'*100}")
            print(f"{'Sensor':<8} {'File':<30} {'Surface Temp':<15} {'Internal Temp':<15} {'Room Temp':<12} {'Wall Type':<15} {'Flags':<20}")
            print(f"{'-'*100}")
            
            for r in box2_files:
                filename = r['filepath'].name
                df = r['data']
                dates = r['dates']
                
                # Extract sensor number
                sensor = filename.split('.')[1].split('_')[0] if '.' in filename else '?'
                
                # Find row within 5 minutes
                time_window_mask = (dates >= closest_ts - pd.Timedelta(minutes=5)) & \
                                   (dates <= closest_ts + pd.Timedelta(minutes=5))
                matching_rows = dates[time_window_mask]
                
                if len(matching_rows) > 0:
                    closest_idx = (matching_rows - closest_ts).abs().idxmin()
                    row = df.loc[closest_idx]
                    
                    # Extract values
                    surface = internal = room = wall_type = 'N/A'
                    
                    for col in df.columns:
                        if 'surface' in col.lower() and 'heat' in col.lower():
                            surface = row.get(col, 'N/A')
                        elif 'internal' in col.lower() and 'temp' in col.lower():
                            internal = row.get(col, 'N/A')
                        elif 'air' in col.lower() and 'temp' in col.lower():
                            room = row.get(col, 'N/A')
                        elif 'wall' in col.lower() and 'type' in col.lower():
                            wall_type = row.get(col, 'N/A')
                    
                    # Format values
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
                    
                    # Flags
                    flags = []
                    if filename == max_room_file:
                        flags.append("MAX ROOM TEMP")
                    if filename == min_room_file:
                        flags.append("MIN ROOM TEMP")
                    flag_str = ', '.join(flags)
                    
                    print(f"S{sensor:<7} {filename:<30} {str(surface):<15} {str(internal):<15} {str(room):<12} {wall_type:<15} {flag_str:<20}")
                else:
                    print(f"S{sensor:<7} {filename:<30} {'NO DATA':<15} {'NO DATA':<15} {'NO DATA':<12} {'NO DATA':<15} {'':<20}")



def main():
    """Main diagnostic function."""
    base_path = Path(__file__).parent.parent / 'data' / 'updated'
    
    if not base_path.exists():
        print(f"[X] Updated data folder not found: {base_path}")
        return
    
    # Analyze Period1
    period1_path = base_path / 'Period1'
    if period1_path.exists():
        analyze_period(period1_path, 'Period1')
    else:
        print(f"[!] Period1 folder not found: {period1_path}")
    
    # Analyze Period2
    period2_path = base_path / 'Period2'
    if period2_path.exists():
        analyze_period(period2_path, 'Period2')
    else:
        print(f"[!] Period2 folder not found: {period2_path}")
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
