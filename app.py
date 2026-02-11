"""
Streamlit Dashboard for Thermal Experiment Analysis
Control Box vs Experimental Box
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import plotly.graph_objects as go

from src.load import load_all_periods
from src.transform import transform_all_data, apply_smoothing, detect_wall_type_changes
from src.plots import (
    plot_timeline_box, plot_timeline_wall, plot_timeline_wall_comparison, plot_sandwich_view,
    plot_thermal_gradient_summary, plot_diagnostic_overlay,
    plot_correlation_heatmap, create_summary_table, BOX_COLORS, ROOM_TEMP_COLOR
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Thermal Experiment Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌡️ Thermal Experiment Dashboard")
st.markdown("**Control Box vs Experimental Box - Thermal Performance Analysis**")


# ===== DATA LOADING =====

@st.cache_data
def load_data():
    """Load and transform all period data."""
    base_folder = Path(__file__).parent / 'data_cleaned'
    
    with st.spinner("Loading CSV files..."):
        periods = load_all_periods(base_folder)
    
    if not periods:
        st.error("No data could be loaded. Check data_cleaned folder.")
        st.stop()
    
    with st.spinner("Transforming data..."):
        transformed = transform_all_data(periods)
    
    return transformed


# Load data
data = load_data()

if not data:
    st.error("Data transformation failed.")
    st.stop()

# Extract data levels
sensor_data = data.get('sensor')
wall_data = data.get('wall')
box_data = data.get('box')


# ===== SIDEBAR CONTROLS =====

st.sidebar.header("⚙️ Controls")

# Period selection
available_periods = sorted(sensor_data['period'].unique()) if sensor_data is not None else []
period_option = st.sidebar.selectbox(
    "Period",
    options=available_periods,  # Remove 'Both' option for now
    index=0 if 'Period1' in available_periods else 0
)

# Sensor exclusion
st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Sensor Exclusion")
st.sidebar.markdown("*Exclude sensors from all calculations*")

# Create sensor options for both boxes
sensor_options = []
for box in [1, 2]:
    box_name = 'Control' if box == 1 else 'Experimental'
    for sensor in range(1, 17):
        sensor_options.append(f"{box_name} Box - Sensor {sensor}")

excluded_sensors = st.sidebar.multiselect(
    "Exclude Sensors",
    options=sensor_options,
    default=[],
    help="Select sensors to exclude from all averages and calculations"
)

# Parse excluded sensors into (box_id, sensor_id) tuples
excluded_pairs = []
for s in excluded_sensors:
    if 'Control' in s:
        box_id = 1
    else:
        box_id = 2
    sensor_id = int(s.split('Sensor ')[1])
    excluded_pairs.append((box_id, sensor_id))

st.sidebar.markdown("---")

# View level
view_level = st.sidebar.radio(
    "View Level",
    options=['Box Average', 'Per-Box Detail', 'Individual Walls (One Box)', 'Wall Comparison (Both Boxes)'],
    index=0
)

# Temperature display mode
normalized = st.sidebar.checkbox(
    "Normalized View",
    value=False,
    help="Show temperatures relative to room temperature (room = 0°C)"
)

# Smoothing
smoothing_option = st.sidebar.selectbox(
    "Smoothing",
    options=[None, '1h', '3h', '12h'],
    format_func=lambda x: 'None' if x is None else x,
    index=0
)

# Additional toggles for box average view
if view_level == 'Box Average':
    st.sidebar.markdown("---")
    st.sidebar.subheader("Display Options")
    include_room = st.sidebar.checkbox("Show Room Temperature", value=True, help="Gray dotted line")
    include_surface = st.sidebar.checkbox("Show Surface Temperature", value=False, help="Dashed lines (inside sensors average)")
    include_out_surface = False
elif view_level == 'Per-Box Detail':
    st.sidebar.markdown("---")
    selected_box_detail = st.sidebar.radio(
        "Box",
        options=[1, 2],
        format_func=lambda x: 'Control' if x == 1 else 'Experimental',
        index=1,
        key='per_box_detail_box'
    )
    include_room = False
    include_surface = False
    include_out_surface = True
else:
    include_room = True
    include_surface = False
    include_out_surface = False

# Wall/Box selection (context-dependent)
if view_level == 'Individual Walls (One Box)':
    st.sidebar.markdown("---")
    st.sidebar.subheader("Wall Selection")
    
    selected_box = st.sidebar.radio(
        "Box", 
        options=[1, 2], 
        format_func=lambda x: 'Control' if x == 1 else 'Experimental', 
        index=1
    )
    
    selected_walls = []
    for wall_id in [1, 2, 3, 4]:
        if st.sidebar.checkbox(f"Wall {wall_id}", value=True, key=f"wall_{wall_id}"):
            selected_walls.append(wall_id)
    
    show_internal = st.sidebar.checkbox("Show Internal Temp", value=True, help="Solid lines")
    show_in_surface = st.sidebar.checkbox("Show Inside Surface Temp", value=True, help="Dashed lines")
    show_out_surface = st.sidebar.checkbox("Show Outside Surface Temp", value=False, help="Dotted lines")

elif view_level == 'Wall Comparison (Both Boxes)':
    st.sidebar.markdown("---")
    st.sidebar.subheader("Wall Selection")
    
    selected_wall = st.sidebar.radio(
        "Compare Wall",
        options=[1, 2, 3, 4],
        format_func=lambda x: f'Wall {x}',
        index=0,
        help="Compare this wall between Control and Experimental boxes"
    )
    
    selected_walls = [selected_wall]
    selected_box = 2  # Not used in comparison mode
    show_internal = True
    show_surface = True

else:  # Box Average or Per-Box Detail or Wall Comparison
    if view_level != 'Per-Box Detail':
        selected_box = 2
    selected_walls = [1, 2, 3, 4]
    show_internal = True
    show_in_surface = True
    if view_level != 'Per-Box Detail':
        show_out_surface = False


# ===== FILTER DATA BY PERIOD AND EXCLUDED SENSORS =====

def filter_by_period(df, period_opt):
    """Filter dataframe by period selection."""
    if df is None or period_opt is None:
        return df
    # Filter to specific period
    return df[df['period'] == period_opt].copy()


def exclude_sensors(sensor_df, wall_df, box_df, excluded_pairs):
    """Remove excluded sensors and re-aggregate wall/box levels."""
    if not excluded_pairs or sensor_df is None:
        return sensor_df, wall_df, box_df
    
    # Filter sensor data
    filtered_sensor = sensor_df.copy()
    for box_id, sensor_id in excluded_pairs:
        filtered_sensor = filtered_sensor[
            ~((filtered_sensor['box_id'] == box_id) & (filtered_sensor['sensor_id'] == sensor_id))
        ]
    
    # Re-aggregate wall level from filtered sensors
    from src.transform import aggregate_wall_level, aggregate_box_level
    
    filtered_wall = aggregate_wall_level(filtered_sensor)
    filtered_box = aggregate_box_level(filtered_sensor)
    
    return filtered_sensor, filtered_wall, filtered_box


# Apply sensor exclusion FIRST (before period filtering)
filtered_sensor_all_periods, filtered_wall_all_periods, filtered_box_all_periods = exclude_sensors(
    sensor_data, wall_data, box_data, excluded_pairs
)

# Then apply period filter
filtered_sensor = filter_by_period(filtered_sensor_all_periods, period_option)
filtered_wall = filter_by_period(filtered_wall_all_periods, period_option)
filtered_box = filter_by_period(filtered_box_all_periods, period_option)

# Apply smoothing
if smoothing_option:
    if filtered_box is not None:
        filtered_box = apply_smoothing(
            filtered_box, 
            ['internal_temp', 'surface_temp', 'normalized_internal', 'normalized_surface'],
            smoothing_option
        )
    
    if filtered_wall is not None:
        filtered_wall = apply_smoothing(
            filtered_wall,
            ['out_internal', 'in_internal', 'out_surface', 'in_surface', 'surface_gradient', 'internal_gradient'],
            smoothing_option
        )


# ===== CSV EXPORT (in sidebar) =====
with st.sidebar:
    st.markdown("---")
    st.subheader("📥 Export Data")
    export_level = st.selectbox(
        "Data Level",
        options=['Sensor', 'Wall', 'Box'],
        help="Choose aggregation level for export"
    )
    
    if st.button("Generate CSV", type="primary"):
        # Get the appropriate filtered dataset
        if export_level == 'Sensor':
            export_df = filtered_sensor
        elif export_level == 'Wall':
            export_df = filtered_wall
        else:
            export_df = filtered_box
        
        if export_df is not None and len(export_df) > 0:
            csv = export_df.to_csv(index=False)
            st.download_button(
                label=f"Download {export_level} Data CSV",
                data=csv,
                file_name=f"thermal_data_{export_level.lower()}_{period_option}.csv",
                mime="text/csv",
            )
        else:
            st.error("No data available for export")


# ===== TABS =====

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Main Timeline",
    "🥪 Sandwich View",
    "📊 Thermal Gradient",
    "🔍 Diagnostic Overlay"
])


# ----- TAB 1: MAIN TIMELINE -----
with tab1:
    st.header("Main Timeline")
    st.info("💡 **Tip:** Click on any line name in the legend to hide/show it on the plot")
    
    if view_level == 'Box Average':
        st.markdown("""
        **Box-Level Temperature Comparison**
        - Solid lines: Average internal temperature of all 16 sensors in each box
        - Dashed lines: Average surface temperature from inside sensors (9-16) only
        - Dotted line: Room temperature (outside air)
        - Vertical lines: Wall type changes in Experimental box
        """)
        
        if filtered_box is not None:
            fig = plot_timeline_box(
                filtered_box,
                normalized=normalized,
                smoothing=smoothing_option,
                include_room=include_room,
                include_surface=include_surface
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No box-level data available.")
    
    elif view_level == 'Per-Box Detail':
        st.markdown(f"""
        **Per-Box Detail View - {'Control' if selected_box_detail == 1 else 'Experimental'} Box**
        - Solid lines: Internal temperature (average of all 16 sensors)
        - Dashed lines: Inside surface temperature (average of sensors 9-16)
        - Dotted lines: Outside surface temperature (average of sensors 1-8)
        - Shows complete temperature profile from outside air to inside
        """)
        
        if filtered_box is not None:
            box_subset = filtered_box[filtered_box['box_id'] == selected_box_detail]
            
            fig = go.Figure()
            
            # Use distinct colors regardless of box
            internal_color = '#2E86AB'  # Blue
            inside_surf_color = '#E63946'  # Red
            outside_surf_color = '#F77F00'  # Orange
            
            # Internal temp (solid)
            fig.add_trace(go.Scatter(
                x=box_subset['timestamp'],
                y=box_subset['internal_temp'] if not normalized else box_subset['normalized_internal'],
                mode='lines',
                name='Internal Temp',
                line=dict(color=internal_color, width=2.5),
            ))
            
            # Inside surface (dashed)
            fig.add_trace(go.Scatter(
                x=box_subset['timestamp'],
                y=box_subset['surface_temp'] if not normalized else box_subset['normalized_surface'],
                mode='lines',
                name='Inside Surface',
                line=dict(color=inside_surf_color, width=2, dash='dash'),
            ))
            
            # Outside surface (dotted) - need to get from wall data
            if filtered_wall is not None:
                wall_subset = filtered_wall[filtered_wall['box_id'] == selected_box_detail]
                out_surf_avg = wall_subset.groupby('timestamp')['out_surface' if not normalized else 'out_normalized_surface'].mean().reset_index()
                
                fig.add_trace(go.Scatter(
                    x=out_surf_avg['timestamp'],
                    y=out_surf_avg['out_surface' if not normalized else 'out_normalized_surface'],
                    mode='lines',
                    name='Outside Surface',
                    line=dict(color=outside_surf_color, width=2, dash='dot'),
                ))
            
            # Room temp or 0 line
            if not normalized:
                fig.add_trace(go.Scatter(
                    x=box_subset['timestamp'],
                    y=box_subset['room_temp'],
                    mode='lines',
                    name='Room Temperature (Outside Air)',
                    line=dict(color=ROOM_TEMP_COLOR, width=2),
                ))
            else:
                fig.add_hline(
                    y=0,
                    line_dash="dot",
                    line_color=ROOM_TEMP_COLOR,
                    line_width=2,
                    annotation_text="Out Air Temp (Room) = 0°C",
                    annotation_position="right"
                )
            
            # Add wall type changes for experimental box
            if selected_box_detail == 2 and filtered_wall is not None:
                exp_data = filtered_wall[filtered_wall['box_id'] == 2]
                if 'wall_type' in exp_data.columns:
                    from src.transform import detect_wall_type_changes
                    changes = detect_wall_type_changes(exp_data)
                    for ts, wall_type in changes:
                        fig.add_vline(
                            x=ts,
                            line_width=2,
                            line_dash="solid",
                            line_color="rgba(128, 128, 128, 0.4)",
                        )
                        # Add annotation separately to avoid timestamp arithmetic issues
                        fig.add_annotation(
                            x=ts,
                            y=1,
                            yref='paper',
                            text=f"→ {wall_type}",
                            showarrow=False,
                            yshift=10,
                            font=dict(size=10, color="black"),
                            bgcolor="rgba(255, 255, 255, 0.8)",
                        )
            
            fig.update_layout(
                title=f"{'Control' if selected_box_detail == 1 else 'Experimental'} Box - Complete Temperature Profile" + (" (Normalized)" if normalized else ""),
                xaxis_title='Time',
                yaxis_title='Temperature Relative to Room (°C)' if normalized else 'Temperature (°C)',
                hovermode='x unified',
                height=500,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No box-level data available.")
    
    elif view_level == 'Individual Walls (One Box)':
        st.markdown(f"""
        **Individual Wall Analysis - {'Control' if selected_box == 1 else 'Experimental'} Box**
        - Solid lines: Internal temperature (inside sensors)
        - Dashed lines: Inside surface temperature
        - Dotted lines: Outside surface temperature (if enabled)
        - Each color represents a different wall (1-4)
        """)
        
        if filtered_wall is not None and selected_walls:
            fig = plot_timeline_wall(
                filtered_wall,
                walls=selected_walls,
                box_id=selected_box,
                smoothing=smoothing_option,
                show_internal=show_internal,
                show_in_surface=show_in_surface,
                show_out_surface=show_out_surface
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No wall-level data available or no walls selected.")
    
    else:  # Wall Comparison
        st.markdown(f"""
        **Wall {selected_wall} Comparison: Control vs Experimental**
        - Compare the same wall across both boxes
        - Solid lines: Internal temperature
        - Dashed lines: Surface temperature
        - Different colors for Control (blue tones) vs Experimental (orange/red tones)
        """)
        
        if filtered_wall is not None:
            fig = plot_timeline_wall_comparison(
                filtered_wall,
                wall_id=selected_wall,
                normalized=normalized,
                smoothing=smoothing_option
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No wall-level data available.")
    
    # Show wall type change events (for experimental box)
    if filtered_wall is not None and (view_level == 'Box Average' or 
                                      (view_level == 'Individual Walls (One Box)' and selected_box == 2) or
                                      view_level == 'Wall Comparison (Both Boxes)'):
        with st.expander("🔄 Wall Type Change Events (Experimental Box)"):
            changes = detect_wall_type_changes(filtered_wall[filtered_wall['box_id'] == 2])
            
            if changes:
                change_df = pd.DataFrame(changes, columns=['Timestamp', 'Wall Type'])
                st.dataframe(change_df, use_container_width=True)
            else:
                st.info("No wall type changes detected.")


# ----- TAB 2: SANDWICH VIEW -----
with tab2:
    st.header("Sandwich View - Thermal Transfer Analysis by Wall Type")
    
    st.info("""
    **Thermal Lag Analysis by Wall Type**
    
    Calculated via cross-correlation between outside and inside surface temperature time series.
    - Temperatures are **aggregated across all walls of the same type** (e.g., all "Exposed" walls)
    - Lag value indicates time delay (minutes) for temperature changes to propagate through the wall
    - Correlation coefficient (r) indicates pattern similarity between surfaces
    - Each subplot shows one wall type
    """)
    
    sandwich_box = st.radio(
        "Select Box", 
        options=[1, 2], 
        format_func=lambda x: 'Control' if x == 1 else 'Experimental', 
        index=1, 
        key='sandwich_box'
    )
    
    if filtered_wall is not None:
        fig = plot_sandwich_view(filtered_wall, box_id=sandwich_box)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available.")


# ----- TAB 3: THERMAL GRADIENT -----
with tab3:
    st.header("Thermal Gradient Summary")
    st.markdown("""
    **Temperature Gradients by Wall Type**
    
    Two key metrics:
    1. **Surface Gradient** (Outside Surface - Inside Surface): Heat transfer through the wall material
    2. **Total Gradient** (Outside Air - Internal Temp): Overall insulation performance including air gaps
    
    Higher absolute values indicate better insulation (larger temperature difference maintained).
    """)
    
    # Period selection for gradient
    gradient_period_mode = st.radio(
        "Period View",
        options=['Current Period Only', 'Both Periods Combined'],
        index=0,
        help="View gradient for current sidebar period or combine both periods",
        horizontal=True
    )
    
    # Determine which data to use
    if gradient_period_mode == 'Both Periods Combined':
        # Use all periods data (with sensor exclusions already applied)
        gradient_wall_data = filtered_wall_all_periods
        gradient_periods = available_periods
    else:
        # Use current filtered data (single period)
        gradient_wall_data = filtered_wall
        gradient_periods = [period_option] if period_option else []
    
    if gradient_wall_data is not None and len(gradient_wall_data) > 0:
        if 'wall_type' in gradient_wall_data.columns:
            fig = plot_thermal_gradient_summary(gradient_wall_data, periods=gradient_periods)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Wall type information not available.")
    else:
        st.warning("No data available.")


# ----- TAB 4: DIAGNOSTIC OVERLAY -----
with tab4:
    st.header("Diagnostic Overlay - All Sensors")
    st.markdown("*All 16 sensors visualized with box average*")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        diag_box = st.radio("Select Box", options=[1, 2], format_func=lambda x: 'Control' if x == 1 else 'Experimental', index=0, key='diag_box')
        
        diag_y_var = st.selectbox(
            "Y Variable",
            options=['surface_temp', 'internal_temp', 'normalized_surface', 'normalized_internal'],
            format_func=lambda x: x.replace('_', ' ').title(),
            index=0,
            key='diag_y_var'
        )
        
        st.markdown("---")
        st.markdown("**Sensor Selection:**")
        
        # Get available sensors for this box
        if filtered_sensor is not None:
            box_sensors = sorted(filtered_sensor[filtered_sensor['box_id'] == diag_box]['sensor_id'].unique())
        else:
            box_sensors = list(range(1, 17))
        
        # Quick select/deselect all
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Select All", key='select_all_sensors'):
                for s in box_sensors:
                    st.session_state[f'sensor_{s}'] = True
        with col_b:
            if st.button("Clear All", key='clear_all_sensors'):
                for s in box_sensors:
                    st.session_state[f'sensor_{s}'] = False
        
        selected_sensors = []
        for sensor_id in range(1, 17):
            # Default all to checked if not in session state
            default_val = sensor_id in box_sensors
            if f'sensor_{sensor_id}' not in st.session_state:
                st.session_state[f'sensor_{sensor_id}'] = default_val
            
            is_available = sensor_id in box_sensors
            label = f"Sensor {sensor_id}" + ("" if is_available else " (N/A)")
            
            if st.checkbox(label, value=st.session_state[f'sensor_{sensor_id}'], key=f'sensor_check_{sensor_id}', disabled=not is_available):
                if is_available:
                    selected_sensors.append(sensor_id)
                st.session_state[f'sensor_{sensor_id}'] = True
            else:
                st.session_state[f'sensor_{sensor_id}'] = False
        
        st.markdown("---")
        st.markdown("**Legend:**")
        st.markdown("🔴 Red = Outside sensors (1-8)")
        st.markdown("🔵 Blue = Inside sensors (9-16)")
        st.markdown("⚫ Black = Box average")
    
    with col2:
        if filtered_sensor is not None and selected_sensors:
            # Filter sensor data based on selection
            sensor_subset = filtered_sensor[
                (filtered_sensor['box_id'] == diag_box) & 
                (filtered_sensor['sensor_id'].isin(selected_sensors))
            ]
            
            fig = plot_diagnostic_overlay(sensor_subset, box_id=diag_box, y_var=diag_y_var)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show sensor availability
            available_sensors = sorted(filtered_sensor[filtered_sensor['box_id'] == diag_box]['sensor_id'].unique())
            missing_sensors = [s for s in range(1, 17) if s not in available_sensors]
            
            st.info(f"**Displaying {len(selected_sensors)} sensors** | Available: {', '.join(map(str, available_sensors))}")
            if missing_sensors:
                st.warning(f"**Missing sensors:** {', '.join(map(str, missing_sensors))}")
        elif filtered_sensor is not None:
            st.warning("No sensors selected. Please select at least one sensor.")
        else:
            st.warning("No sensor data available.")


# ===== FOOTER =====

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    """
    **Thermal Experiment Dashboard**
    
    Comparing thermal performance:
    - **Control Box**: Standard walls (Exposed)
    - **Experimental Box**: Green wall treatments
    
    **Data Structure:**
    - 2 boxes, 16 sensors each
    - 4 walls per box, 4 sensors per wall
    - Sensors 1-8: Outside, 9-16: Inside
    - 10-minute aggregated intervals
    
    **Periods:**
    - Period 1: Oct 23 - Nov 6, 2025 (14 days)
    - Period 2: Dec 3-11, 2025 (8 days)
    
    **Experimental Treatments (Box 2):**
    Exposed → Yarka → Dry soil → Succalents
    """
)

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit + Plotly")
