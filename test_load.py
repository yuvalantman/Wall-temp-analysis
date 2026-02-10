"""
Test script to validate data loading with Period1 cleaned data.
"""
from pathlib import Path
from src.load import load_all_periods

print("Testing data loading...")
print("="*80)

base_folder = Path(__file__).parent / 'data_cleaned'
print(f"Base folder: {base_folder}")
print(f"Exists: {base_folder.exists()}")

if base_folder.exists():
    period1_path = base_folder / 'Period1'
    print(f"Period1 path: {period1_path}")
    print(f"Period1 exists: {period1_path.exists()}")
    
    if period1_path.exists():
        csv_files = list(period1_path.glob('*.csv'))
        print(f"CSV files found: {len(csv_files)}")
        print(f"Sample files: {[f.name for f in csv_files[:3]]}")

print("\n" + "="*80)
print("Starting data load...")
print("="*80 + "\n")

periods = load_all_periods(base_folder)

if periods:
    print("\n" + "="*80)
    print("DATA LOAD TEST COMPLETE")
    print("="*80)
    print(f"Periods loaded: {list(periods.keys())}")
    for name, df in periods.items():
        print(f"\n{name}:")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Sensors: {sorted(df['sensor_id'].unique())}")
        print(f"  First timestamp: {df['timestamp'].min()}")
        print(f"  Last timestamp: {df['timestamp'].max()}")
else:
    print("\n❌ No data loaded!")

print("\nCheck the log file for detailed loading information.")
