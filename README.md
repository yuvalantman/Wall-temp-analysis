# Thermal Experiment Dashboard

Interactive Streamlit dashboard for analyzing thermal performance data from control and experimental boxes equipped with 16 temperature sensors each.

## Quick Start

### 1. Create Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\Activate
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run Dashboard
```powershell
streamlit run app.py
```

### 4. Deactivate Virtual Environment (when done)
```powershell
deactivate
```

## Project Structure

```
Dashboard/
├── data_cleaned/
│   ├── Period1/          # 32 CSV files (Control & Experimental boxes)
│   └── Period2/          # 29 CSV files (some sensors missing)
├── src/
│   ├── __init__.py
│   ├── load.py           # CSV parsing & data loading
│   ├── transform.py      # Resampling, aggregation, validation
│   └── plots.py          # Plotly visualization functions
├── tests/
│   ├── test_load.py
│   └── test_transform.py
├── diagnostics/          # Log files and diagnostic reports
├── app.py                # Main Streamlit dashboard
├── requirements.txt      # Python dependencies
├── README.md
└── .gitignore
```

## Features

### Data Validation & Processing
- **Robust CSV parsing**: Headers at row 15, handles junk rows and encoding issues
- **10-minute bin validation**: Ensures each timestamp has exactly 32 values (16 sensors × 2 boxes)
- **Missing sensor support**: Gracefully handles Period2 missing sensors
- **Time alignment**: Resamples to clean 10-minute intervals
- **Wall type detection**: Auto-detects regime changes from experimental box data
- **Multi-level aggregation**: Sensor → Wall → Box hierarchy

### Dashboard Views

**1. Main Timeline**
- **Box Average**: Compare control vs experimental box internal temperatures
- **Per-Box Detail**: See internal, inside surface, and outside surface temps for one box
- **Individual Walls**: View up to 4 walls simultaneously for one box
- **Wall Comparison**: Compare same wall across both boxes
- Toggles for room temperature, surface temperatures
- Smoothing options (1h, 3h, 12h)
- Wall type change markers with annotations

**2. Sandwich View**
- Outside vs Inside temperature comparison per wall
- Thermal lag calculation (cross-correlation analysis)
- Multi-wall overlay with color coding

**3. Thermal Gradient**
- Surface gradient (outside surface - inside surface)
- Total gradient (outside internal - inside internal)  
- Statistics by wall type (Before/After change)
- Separate trend lines for each gradient type

**4. Diagnostic Overlay**
- All 16 sensors plotted individually
- Box average highlighted for reference
- Color-coded by position (outside/inside sensors)

### Data Export
- CSV export available in sidebar
- Choose data level: Sensor, Wall, or Box
- Includes all calculated metrics and smoothed values

## Sensor Topology

Each box has 4 walls:
- **Wall 1 (South)**: Outside (S1,S2) | Inside (S9,S10)
- **Wall 2 (East)**: Outside (S3,S4) | Inside (S11,S12)
- **Wall 3 (North)**: Outside (S5,S6) | Inside (S13,S14)
- **Wall 4 (West)**: Outside (S7,S8) | Inside (S15,S16)

## Box Configuration
- **Box 1**: Control (GW_1.*)
- **Box 2**: Experimental (GW_2.*)

## Calculated Metrics

### Temperature Metrics
- `surface_temp`: Value Heat Surface
- `internal_temp`: Internal temp sensor
- `room_temp`: Out Air temp

### Derived Metrics
- `normalized_surface`: surface_temp - room_temp
- `normalized_internal`: internal_temp - room_temp
- `surface_gradient`: outside_surface - inside_surface
- `internal_gradient`: outside_internal - inside_internal

### Thermal Lag
- Computed via cross-correlation between outside/inside signals
- Search window: 0-12 hours
- Reports lag in minutes and correlation coefficient
