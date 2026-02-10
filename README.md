# Thermal Experiment Dashboard

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

## Project Structure

```
Dashboard/
├── Period1/          # 32 CSV files (P1 data)
├── Period2/          # 29 CSV files (P2 data - sensors 5,9,11 missing)
├── src/
│   ├── load.py       # CSV parsing & data loading
│   ├── transform.py  # Resampling, aggregation, metrics
│   └── plots.py      # Plotly visualization functions
├── app.py            # Main Streamlit dashboard
└── requirements.txt
```

## Features

### Data Handling
- **Robust CSV parsing**: Headers at row 15, handles junk rows
- **Missing sensor support**: Gracefully handles Period2 missing sensors (5, 9, 11)
- **Time alignment**: Resamples to clean 10-minute intervals
- **Regime detection**: Auto-detects wall type changes from CSV data

### Dashboard Tabs

**1. Main Timeline**
- Box-level or wall-level views
- Toggle room/surface temperatures
- Smoothing options (1h, 3h, 12h)
- Wall type change markers

**2. Sandwich View**
- Outside vs Inside temperature comparison
- Thermal lag calculation (cross-correlation)
- Multi-wall comparison

**3. Thermal Gradient**
- Summary by wall type
- Normalized temperature visualization
- Statistics table

**4. Diagnostic Overlay**
- All 16 sensors on one plot
- Box average highlighted
- Color-coded outside/inside sensors

**5. Summary**
- Data overview metrics
- Correlation heatmap
- Sensor availability table
- CSV export

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
