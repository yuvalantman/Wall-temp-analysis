"""
Quick test to verify transform pipeline works with loaded data.
"""
from pathlib import Path
from src.load import load_all_periods
from src.transform import transform_all_data
import sys

# Fix unicode output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*80)
print("TESTING TRANSFORM PIPELINE")
print("="*80)

# Load data
base_folder = Path(__file__).parent / 'data_cleaned'
periods = load_all_periods(base_folder)

if not periods:
    print("ERROR: No data loaded")
    exit(1)

print(f"\nLoaded {len(periods)} period(s)")

# Transform
print("\n" + "="*80)
print("RUNNING TRANSFORM...")
print("="*80)

try:
    transformed = transform_all_data(periods)
    
    if transformed:
        print("\nTRANSFORM SUCCESS!")
        print("\nTransformed data levels:")
        for level, df in transformed.items():
            if df is not None:
                print(f"  {level:10s}: {df.shape[0]:6,} rows x {df.shape[1]:2} columns")
                print(f"             Columns: {list(df.columns[:8])}...")
    else:
        print("\nTransform returned None")
        
except Exception as e:
    print(f"\nTRANSFORM FAILED!")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
