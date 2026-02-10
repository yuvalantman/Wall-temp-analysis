# Dashboard Guide

## Overview

This dashboard analyzes thermal performance data from a green wall experiment comparing two test boxes:
- **Control Box (Box 1)**: Standard exposed walls as baseline
- **Experimental Box (Box 2)**: Green wall treatments (rotating treatments over time)

## Data Structure

### Physical Setup
- **2 Boxes**: Each box represents an enclosed experimental chamber
- **16 Sensors per Box**: Each box has 16 temperature sensors distributed across 4 walls
- **4 Walls per Box**: Each wall has 4 sensors measuring different aspects of thermal performance
- **4 Sensors per Wall**: 
  - 2 Outside sensors (measuring exterior conditions)
  - 2 Inside sensors (measuring interior conditions)

### Sensor Topology
```
Box 1 (Control) & Box 2 (Experimental)
├── Wall 1: Sensors 1, 2 (outside), 9, 10 (inside)
├── Wall 2: Sensors 3, 4 (outside), 11, 12 (inside)
├── Wall 3: Sensors 5, 6 (outside), 13, 14 (inside)
└── Wall 4: Sensors 7, 8 (outside), 15, 16 (inside)

Sensor Numbering:
- Sensors 1-8: Outside positions (exterior of wall)
- Sensors 9-16: Inside positions (interior of wall)
```

### Measurement Types
Each sensor records:
1. **Internal Temperature**: Air temperature measured by the sensor
2. **Surface Temperature**: Heat measured at the wall surface
3. **Room Temperature**: Ambient outside air temperature (same for all sensors)

### Time Periods
- **Period 1**: October 23 - November 6, 2025 (14 days)
  - All sensors operational
  - Box 1: Exposed walls (control)
  - Box 2: Mixed treatments (Exposed → Yarka → Dry soil → Succalents)

- **Period 2**: December 3 (11:00) - December 11, 2025 (8 days)
  - Some sensors missing in Box 2 (sensors 5, 9, 11)
  - Contains 868 missing values within valid date range

### Data Aggregation
- **Raw Data**: Individual CSV files per sensor per period
- **Resampling**: Data aggregated to 10-minute intervals
  - Time bins: 12:00:00-12:09:59 → 12:00, next bin → 12:10
- **Aggregation Levels**:
  1. **Sensor Level**: Individual sensor measurements (65,344 rows for Period1)
  2. **Wall Level**: Aggregated by wall (outside vs inside averages) (16,336 rows)
  3. **Box Level**: Aggregated by entire box (4,084 rows)

### Calculated Metrics

#### Normalized Temperatures
- **Purpose**: Remove ambient temperature effects to isolate box performance
- **Calculation**: `normalized_temp = measured_temp - room_temp`
- **Interpretation**: Shows temperature difference relative to ambient conditions
  - Positive: Warmer than outside
  - Negative: Cooler than outside
  - Zero: Same as outside

#### Thermal Gradient
- **Surface Gradient**: Difference between outside and inside surface temperatures
  - `surface_gradient = out_surface - in_surface`
  - Measures heat flow through wall material
  
- **Internal Gradient**: Difference between outside and inside air temperatures
  - Note: In this dataset, out_internal and in_internal have identical values
  - This occurs because sensors measure the same air space

#### Thermal Lag
- **What**: Time delay for heat to transfer from outside to inside of wall
- **Method**: Cross-correlation analysis between outside and inside surface temperatures
- **Output**: 
  - Lag time in minutes (how long heat takes to penetrate)
  - Correlation coefficient (r) indicating pattern similarity
- **Interpretation**:
  - Higher lag = Better insulation
  - Higher correlation = Consistent heat transfer pattern

---

## Dashboard Tabs

### Tab 1: Main Timeline

**Purpose**: Compare temperature patterns over time across boxes or walls

**View Modes**:

1. **Box Average View** (Default)
   - Shows aggregate thermal behavior of entire boxes
   - **Solid lines**: Average internal temperature (all 16 sensors per box)
   - **Dashed lines**: Average surface temperature (inside sensors 9-16 only)
   - **Dotted line**: Room temperature (ambient outside air)
   - **Vertical gray lines**: Mark wall type changes in Experimental box
   
   **When to use**: 
   - Overall comparison between Control and Experimental boxes
   - Identifying system-level differences
   - Observing impact of green wall treatments

2. **Individual Walls (One Box)**
   - Examines variation between 4 walls within a single box
   - Each colored line represents a different wall
   - **Solid lines**: Internal temperature
   - **Dashed lines**: Surface temperature
   - Select which box to analyze (Control or Experimental)
   
   **When to use**:
   - Detecting wall-to-wall variability
   - Identifying problematic or exceptional walls
   - Comparing treatment effects on different walls in Experimental box

3. **Wall Comparison (Both Boxes)**
   - Directly compares the same wall number across both boxes
   - E.g., Wall 1 in Control vs Wall 1 in Experimental
   - Different colors for Control (blue) vs Experimental (orange)
   - Shows both internal and surface temps
   
   **When to use**:
   - Isolating treatment effect on specific wall orientation
   - Controlling for positional effects
   - Detailed wall-by-wall performance analysis

**Display Options**:
- **Normalized View**: Toggle to show temps relative to room temp (room = 0°C)
  - Useful for removing ambient temperature fluctuations
  - Highlights thermal performance independent of weather
  
- **Smoothing**: Apply rolling average (1h, 3h, 12h)
  - Reduces noise for clearer trends
  - Use 12h for daily patterns, 1h for detailed features

**Color Scheme**:
- **Control Box**: Blue tones (#2E86AB)
- **Experimental Box**: Orange/Red tones (#F18F01, #C73E1D)
- **Room Temp**: Gray (#6C757D)
- **Individual Walls**: Distinct colors (Red, Teal, Orange, Purple)

---

### Tab 2: Sandwich View

**Purpose**: Analyze heat transfer through wall materials using thermal lag

**What it shows**:
- Outside surface temperature (heat arriving at exterior): Red line
- Inside surface temperature (heat arriving at interior): Blue line
- Lag calculation for each wall (time delay in minutes)

**Thermal Lag Explanation**:
The lag measures how long it takes for temperature changes on the outside surface to appear on the inside surface. This is calculated using cross-correlation:

1. Take outside surface temperature time series
2. Take inside surface temperature time series  
3. Shift one series relative to the other
4. Find the shift that maximizes correlation
5. That shift (in minutes) is the thermal lag

**Interpreting Results**:
- **Lag = 60 minutes, r = 0.95**: Heat takes 1 hour to penetrate, very consistent pattern
- **Lag = 180 minutes, r = 0.85**: Slower heat transfer (better insulation), good consistency
- **Low lag (<30 min)**: Poor insulation, heat transfers quickly
- **Low r (<0.7)**: Inconsistent or complex heat transfer patterns

**Use Cases**:
- Evaluating insulation effectiveness of green wall treatments
- Comparing thermal mass between wall types
- Identifying which treatments provide best thermal buffering

---

### Tab 3: Thermal Gradient Summary

**Purpose**: Summarize average thermal performance by wall type treatment

**Visualization**:
- Y-axis: Different wall type treatments (Exposed, Yarka, Dry soil, Succalents)
- X-axis: Surface temperature (°C)
- **Circle marker (●)**: Average outside surface temperature
- **Square marker (■)**: Average inside surface temperature
- **Line connecting them**: Represents thermal gradient
- **Annotation**: Exact gradient value (ΔT in °C)

**What the gradient means**:
- **Large gradient** (long line): Big temperature difference between outside and inside
  - Could indicate good insulation OR high heat flow
  - Context matters: check if inside is protected or exposed
  
- **Small gradient** (short line): Similar temps on both sides
  - Could indicate poor insulation OR effective thermal equilibrium
  - Depends on desired outcome

**Current Limitations**:
- Averages across all time periods selected
- Doesn't show temporal variation or daily cycles
- May not capture full complexity of thermal behavior

**Potential Improvements** (for future consideration):
- Add time-of-day breakdown (morning vs afternoon gradients)
- Include error bars or confidence intervals
- Separate analysis by weather conditions
- Interactive filtering by temperature range

---

### Tab 4: Diagnostic Overlay

**Purpose**: Quality control and outlier detection at sensor level

**What it shows**:
- All 16 individual sensor traces as semi-transparent lines
- Box average as darker line for reference
- Color coding:
  - **Red lines**: Outside sensors (1-8)
  - **Blue lines**: Inside sensors (9-16)
  - **Dark gray line**: Box average

**Use Cases**:
- **Sensor Validation**: Identify malfunctioning or outlier sensors
- **Spatial Variation**: See spread between sensors
- **Data Quality**: Check for missing data, spikes, or drift
- **Uniformity Assessment**: Determine if box has consistent thermal distribution

**What to look for**:
- Sensors that diverge significantly from the group
- Sudden jumps or discontinuities (sensor failures)
- Excessive noise or flat lines
- Expected patterns: inside sensors should be more stable than outside

---

### Tab 5: Summary

**Purpose**: Overall statistics and data export

**Components**:

1. **Data Overview Metrics**:
   - Number of periods loaded
   - Total sensors available
   - Record counts at different aggregation levels
   - Unique wall combinations

2. **Temperature Correlation Analysis**:
   - Heatmap showing Pearson correlations between measurements
   - Expected high correlation: Internal and surface temps within same box
   - Expected moderate correlation: Box temps with room temp
   - Useful for: Understanding dependencies, validating data consistency
   
   **Current Limitation**: 
   - Room temp columns may be duplicated (should be identical for both boxes)
   - Future improvement: Clean up to show only unique variables

3. **Sensor Availability**:
   - Table showing which sensors have data for each period/box
   - Helps identify missing sensor issues
   - Critical for Period 2 where some sensors failed

4. **Data Export**:
   - Download button for filtered box-level CSV
   - Includes currently selected period
   - Pre-aggregated to 10-minute intervals
   - Ready for external analysis (R, Python, Excel)

---

## Visualization Design Choices

### Why These Plots?

1. **Main Timeline**: Most versatile view for comparing temporal patterns
   - Line plots are standard for time series
   - Multiple view modes accommodate different research questions
   - Normalized option removes confounding ambient effects

2. **Sandwich View**: Specifically designed for thermal lag analysis
   - Stacked subplots allow per-wall comparison
   - Outside vs inside on same axis makes lag visually apparent
   - Quantitative lag metric supplements visual assessment

3. **Thermal Gradient**: Quick summary of treatment effectiveness
   - Abstract from time dimension to see overall patterns
   - Visual gradient representation intuitive
   - Good for presentation and communication

4. **Diagnostic Overlay**: Standard QA tool in sensor data analysis
   - Overlay format lets you spot outliers quickly
   - Color coding by position aids interpretation
   - Semi-transparency prevents overplotting

5. **Summary Tab**: Standard dashboard feature for context and export
   - Correlation matrix is common in multivariate analysis
   - Metrics provide data inventory
   - Export enables reproducible workflows

### Potential Issues and Alternatives

#### Current Gradient View Concerns

**Potential Problems**:
- **Overly simplified**: Averaging across time loses diurnal patterns
- **Unclear interpretation**: Is larger gradient better or worse?
- **Limited information**: Doesn't show variability or confidence
- **Static**: No interactive exploration

**Alternative Visualizations to Consider**:

1. **Time-of-Day Gradient Heatmap**:
   - X: Time of day (0-24 hours)
   - Y: Wall type
   - Color: Gradient magnitude
   - Shows when thermal differences are strongest

2. **Gradient Distribution Box Plots**:
   - Box plot per wall type showing gradient distribution
   - Reveals variability and outliers
   - More statistically informative

3. **Gradient vs Room Temp Scatter**:
   - Examine if gradient depends on ambient conditions
   - Identify non-linear effects
   - Could reveal treatment effectiveness in different weather

4. **Time Series of Gradient**:
   - Plot gradient magnitude over time
   - See how insulation changes as treatments mature
   - Detect temporal patterns or degradation

#### Correlation Heatmap Concerns

**Potential Problems**:
- **Duplicate room temp**: Same data plotted multiple times
- **Expected correlations**: Internal and surface temps always correlate
- **Limited insight**: Doesn't show treatment effects directly

**Alternative Approaches**:

1. **Cross-Correlation Time Lag Matrix**:
   - Show lag times between all sensor pairs
   - Reveals propagation delays
   - More informative than simple correlation

2. **Feature Importance Plot**:
   - If predicting outcomes, show which variables matter most
   - Statistical model-based approach
   - Directly answers "what drives differences?"

3. **Difference-Based Correlation**:
   - Correlate (Experimental - Control) with environmental factors
   - Shows what conditions enhance treatment effects
   - More directly tests hypotheses

---

## Data Analysis Workflow Recommendations

### For New Users (Exploring Data)

1. **Start with Tab 5 (Summary)**:
   - Check data availability
   - Understand period coverage
   - Note missing sensors

2. **Go to Tab 1 (Main Timeline) - Box Average**:
   - Get overall sense of Control vs Experimental
   - Enable "Show Room Temperature" to see ambient context
   - Try normalized view to remove weather effects
   - Note wall type change events

3. **Switch to Individual Walls view**:
   - Check wall-to-wall variability
   - Look for outlier walls
   - Confirm all walls behave similarly (or not)

4. **Check Tab 4 (Diagnostic Overlay)**:
   - Validate sensor data quality
   - Identify any problematic sensors to exclude
   - Assess uniformity within boxes

### For Detailed Analysis

1. **Hypothesis Testing** (e.g., "Yarka reduces internal temp"):
   - Tab 1: Wall Comparison mode, select specific wall
   - Filter to Period with Yarka treatment
   - Enable normalized view
   - Export data for statistical testing

2. **Thermal Lag Analysis**:
   - Tab 2: Select experimental box
   - Compare lag values across wall types
   - Note correlation coefficients
   - Look for wall-specific effects

3. **Treatment Effectiveness**:
   - Tab 3: Include both periods
   - Compare gradients across treatments
   - Cross-reference with Tab 1 timeline to see when changes occurred
   - Consider seasonal/weather context

### For Presentations

1. **Create Comparison Figure**:
   - Tab 1: Box Average, normalized view
   - Apply 3h or 12h smoothing for clean lines
   - Screenshot for publication

2. **Show Treatment Transitions**:
   - Tab 1: Individual Walls, Experimental box
   - Vertical lines mark treatment changes
   - Clear visual evidence of interventions

3. **Quantify Insulation**:
   - Tab 2: Sandwich view with lag annotations
   - Include all walls to show consistency
   - Lag numbers provide concrete metrics

---

## Consulting with AI for Dashboard Improvements

When asking another AI to suggest changes to this dashboard, provide the following context:

### Data Context
```
- 2 test boxes (Control vs Experimental)
- 16 temperature sensors per box (4 walls × 4 sensors)
- Sensors measure: internal air temp, surface heat, room temp
- 10-minute time resolution
- Period 1: 14 days, all sensors working
- Period 2: 8 days, some missing sensors
- Experimental box has rotating green wall treatments
```

### Research Questions
```
Primary: Does green wall treatment reduce internal temperature?
Secondary: How does thermal lag differ between treatments?
Tertiary: Which wall orientation benefits most from treatment?
```

### Current Visualizations
```
1. Timeline plots (box/wall/comparison views)
2. Sandwich view (outside vs inside surface with lag)
3. Gradient summary (average temps by treatment)
4. Diagnostic overlay (all sensor traces)
5. Summary statistics (correlations, metrics)
```

### Specific Issues to Address

**Gradient View**:
- "The current gradient plot just shows averages across all time. How can I better visualize thermal performance differences between wall treatments? Should I use time-of-day patterns, distribution plots, or something else?"

**Correlation Heatmap**:
- "The correlation heatmap mostly shows expected correlations (internal vs surface temps). What visualization would better reveal treatment effects and their relationship to environmental conditions?"

**Statistical Testing**:
- "I want to add statistical significance testing for treatment comparisons. What plots would best show confidence intervals or effect sizes? Should I add a dedicated analysis tab?"

**Temporal Patterns**:
- "My experiment has diurnal cycles and multi-day trends. How can I decompose these patterns and visualize them separately? Is a time series decomposition plot useful here?"

**Comparative Metrics**:
- "I want a summary metric for 'treatment effectiveness' that combines lag, gradient, and temp reduction. How should I visualize this composite score across treatments?"

### Expected AI Response Elements
When consulting with AI, ask for:
1. **Specific plot types** with justification (why this plot for this data/question)
2. **Mock-up description** or pseudocode for implementation
3. **Interpretation guidance** (how to read the new visualization)
4. **Pros and cons** compared to current approach
5. **Statistical rigor** (appropriate tests, confidence intervals, etc.)

---

## Technical Implementation Notes

### Dependencies
```python
streamlit          # Dashboard framework
plotly             # Interactive visualizations
pandas             # Data manipulation
numpy              # Numerical operations
pathlib            # File path handling
```

### File Structure
```
Dashboard/
├── app.py                 # Main Streamlit app
├── src/
│   ├── load.py           # CSV loading, encoding handling
│   ├── transform.py      # Data aggregation, normalization
│   └── plots.py          # Plotly figure generation
├── data_cleaned/
│   ├── Period1/          # Cleaned Period 1 CSVs
│   └── Period2/          # Cleaned Period 2 CSVs
├── requirements.txt      # Python dependencies
└── DASHBOARD_GUIDE.md    # This file
```

### Color Palette
```python
# Box colors
Control: #2E86AB (Blue)
Experimental: #F18F01 (Orange)

# Wall colors (distinct for visibility)
Wall 1: #E63946 (Red)
Wall 2: #06A77D (Teal)
Wall 3: #F77F00 (Orange)
Wall 4: #6A4C93 (Purple)

# Position colors
Outside: #E63946 (Red)
Inside: #118AB2 (Sky Blue)
Room: #6C757D (Gray)
```

### Performance Considerations
- Data loaded once via `@st.cache_data` decorator
- Filtering happens in-memory (fast for this data size)
- Smoothing applied on-demand to filtered data
- Large plots (sandwich view with 4 walls) may take 1-2 seconds to render

---

## Future Enhancement Ideas

### Short-Term (Easy to Implement)

1. **Add Download Button for Plots**:
   - Export current figure as PNG/SVG
   - Useful for presentations and reports
   - Streamlit has built-in download capabilities

2. **Expand Summary Statistics**:
   - Mean/median temps by treatment
   - Daily min/max temperatures
   - Degree-hours above/below threshold

3. **Add Date Range Filter**:
   - Zoom into specific time windows
   - Useful for event-based analysis
   - Sidebar date range slider

### Medium-Term (Moderate Effort)

1. **Treatment Comparison Table**:
   - Side-by-side metrics for each green wall type
   - Statistical tests (t-test, ANOVA)
   - Effect size calculations (Cohen's d)

2. **Weather Data Integration**:
   - If external weather data available
   - Overlay solar radiation, humidity
   - Correlate treatment effectiveness with conditions

3. **Anomaly Detection**:
   - Flag unusual sensor readings automatically
   - Time series outlier detection algorithms
   - Visual indicators on timeline plots

### Long-Term (Research Projects)

1. **Machine Learning Models**:
   - Predict internal temp from external conditions
   - Quantify treatment effect via model coefficients
   - Feature importance analysis

2. **Energy Savings Estimation**:
   - Calculate cooling load reduction
   - Estimate kWh savings from treatments
   - Cost-benefit analysis

3. **Real-Time Dashboard**:
   - Live sensor feed integration
   - Alerting for anomalies
   - Continuous data logging

---

## Troubleshooting Common Issues

### "No data available" Warning

**Causes**:
- Selected period doesn't exist
- Data filtering removed all rows
- Missing CSV files in data_cleaned folder

**Solutions**:
1. Check Period selection in sidebar
2. Verify CSV files exist: `data_cleaned/Period1/` and `Period2/`
3. Review data loading log: `data_loading_log_*.txt`

### Missing Sensors in Plots

**Normal Behavior**:
- Period 2 is missing Box 2 sensors: 5, 9, 11
- This is expected due to sensor failures

**Verification**:
- Tab 5 → Sensor Availability table
- Check which sensors have data

### Plots Look Noisy

**Solutions**:
- Enable smoothing (try 3h or 12h)
- Use normalized view to remove ambient fluctuations
- Check if outlier sensors exist (Tab 4)

### Thermal Lag Shows "None"

**Causes**:
- Insufficient data points for correlation
- Temperature signals too different (low correlation)
- Wall might have very fast or very slow response

**Interpretation**:
- Check correlation coefficient (r)
- If r < 0.5, signals may not be related
- Visual inspection in sandwich plot recommended

---

## Contact and Contribution

This dashboard is part of a thermal experiment research project. 

For questions about:
- **Data interpretation**: Consult with thermal engineering experts
- **Statistical analysis**: Use AI assistants with the consultation guide above
- **Code improvements**: Follow standard Python/Streamlit best practices
- **New features**: Consider the enhancement ideas section and research needs

---

**Last Updated**: February 2026  
**Version**: 1.0  
**Dashboard Framework**: Streamlit + Plotly
