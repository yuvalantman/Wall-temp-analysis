"""
Fix timestamps in Period2 updated files that have incorrect dates.
Sets first timestamp to 12/03/2025 11:11:00 and increments by 10 minutes.
"""

import pandas as pd
from pathlib import Path

# Files to fix
files_to_fix = [
    'GW2.1_121125.csv',
    'GW2.13_121125.csv',
    'GW2.8_121125.csv',
    'GW1.8_121125.csv'
]

base_path = Path('data/updated/Period2')

for filename in files_to_fix:
    filepath = base_path / filename
    
    if not filepath.exists():
        print(f"[!] File not found: {filepath}")
        continue
    
    print(f"\nProcessing: {filename}")
    
    # Try different encodings
    encoding = None
    for enc in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                lines = f.readlines()
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    
    if encoding is None:
        print(f"  [X] Could not read file with any encoding")
        continue
    
    print(f"  Encoding: {encoding}")
    
    # Read the data part (header at row 14)
    df = pd.read_csv(filepath, header=14, encoding=encoding)
    
    # Find the date/time column
    date_col = None
    for col in df.columns:
        if 'date' in col.lower() and 'time' in col.lower():
            date_col = col
            break
    
    if not date_col:
        print(f"  [X] Could not find date column")
        continue
    
    print(f"  Date column: '{date_col}'")
    print(f"  Original rows: {len(df)}")
    print(f"  Original first timestamp: {df[date_col].iloc[0]}")
    print(f"  Original last timestamp: {df[date_col].iloc[-1]}")
    
    # Generate new timestamps starting from 12/03/2025 11:11:00
    start_time = pd.Timestamp('2025-12-03 11:11:00')
    new_timestamps = [start_time + pd.Timedelta(minutes=10*i) for i in range(len(df))]
    
    # Format timestamps as M/D/YYYY H:MM (matching original format without seconds)
    def format_timestamp(ts):
        month = ts.month
        day = ts.day
        year = ts.year
        hour = ts.hour
        minute = ts.minute
        return f"{month}/{day}/{year} {hour}:{minute:02d}"
    
    formatted_timestamps = [format_timestamp(ts) for ts in new_timestamps]
    
    # Update the dataframe
    df[date_col] = formatted_timestamps
    
    print(f"  New first timestamp: {df[date_col].iloc[0]}")
    print(f"  New last timestamp: {df[date_col].iloc[-1]}")
    
    # Write back the file, preserving the header structure
    # Keep the first 14 lines (header lines) and write new data
    with open(filepath, 'w', encoding=encoding, newline='') as f:
        # Write original header lines (first 14 lines)
        for i in range(14):
            f.write(lines[i])
        
        # Write the column headers
        f.write(','.join(df.columns) + '\n')
        
        # Write the data
        df.to_csv(f, index=False, header=False)
    
    print(f"  [+] File updated successfully")

print("\n[+] All files processed")
