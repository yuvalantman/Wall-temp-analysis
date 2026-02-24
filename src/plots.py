"""
Plotting functions using Plotly for thermal experiment dashboard.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from src.transform import calculate_thermal_lag, detect_wall_type_changes


# Color schemes - optimized for visibility and contrast
BOX_COLORS = {
    1: {'internal': '#1E5F8C', 'surface': '#C2185B', 'out_surface': '#2E86AB'},  # Deep Blue / Magenta / Green for Control
    2: {'internal': '#F57C00', 'surface': '#D32F2F', 'out_surface': '#FBC02D'},  # Dark Orange / Red / Yellow for Experimental
}

# Distinct colors for 4 walls - highly contrasting
WALL_COLORS = {
    1: '#D32F2F',  # Strong Red
    2: '#1976D2',  # Strong Blue
    3: '#F57C00',  # Strong Orange
    4: '#7B1FA2',  # Strong Purple
}

# Wall colors for comparison mode (Box1 vs Box2 same wall)
WALL_COMPARISON_COLORS = {
    1: {'box1': '#2E86AB', 'box2': '#F18F01'},  # Blue vs Orange
    2: {'box1': '#06A77D', 'box2': '#E63946'},  # Teal vs Red
    3: {'box1': '#F77F00', 'box2': '#6A4C93'},  # Orange vs Purple
    4: {'box1': '#118AB2', 'box2': '#EF476F'},  # Sky Blue vs Pink
}

POSITION_COLORS = {
    'out': '#E63946',  # Bright Red
    'in': '#118AB2',   # Sky Blue
}

ROOM_TEMP_COLOR = '#6C757D'  # Gray for room temperature


def plot_timeline_box(data, normalized=False, smoothing=None, 
                      include_room=True, include_surface=False, wall_comparison=False, wall_id=None):
    """
    Plot timeline for box-level data.
    
    Parameters:
    - normalized: If True, shows temps relative to room temp (room = 0)
    - include_room: Show room temperature line (dotted gray)
    - include_surface: Show surface temperature lines (dashed)
    - wall_comparison: If True, compare same wall across both boxes
    - wall_id: When wall_comparison=True, which wall to compare (1-4)
    """
    fig = go.Figure()
    
    # Determine y-axis label and variables
    if normalized:
        internal_var = 'normalized_internal'
        surface_var = 'normalized_surface'
        y_label = 'Temperature Relative to Room (°C)'
    else:
        internal_var = 'internal_temp'
        surface_var = 'surface_temp'
        y_label = 'Temperature (°C)'
    
    # Use smoothed columns if available
    internal_col = f'{internal_var}_smooth' if smoothing and f'{internal_var}_smooth' in data.columns else internal_var
    surface_col = f'{surface_var}_smooth' if smoothing and f'{surface_var}_smooth' in data.columns else surface_var
    
    # Plot box internal temps (solid lines)
    for box_id in [1, 2]:
        box_data = data[data['box_id'] == box_id].sort_values('timestamp')
        
        if len(box_data) == 0:
            continue
        
        box_name = 'Control' if box_id == 1 else 'Experimental'
        
        fig.add_trace(go.Scatter(
            x=box_data['timestamp'],
            y=box_data[internal_col],
            mode='lines',
            name=f'{box_name} - Internal Temp',
            line=dict(color=BOX_COLORS[box_id]['internal'], width=2.5),
            legendgroup=f'box{box_id}',
        ))
        
        # Add surface temps if requested (dashed lines)
        if include_surface and surface_var in data.columns:
            # Use same color as internal temp for better matching
            fig.add_trace(go.Scatter(
                x=box_data['timestamp'],
                y=box_data[surface_col],
                mode='lines',
                name=f'{box_name} - Surface Temp (Inside sensors)',
                line=dict(color=BOX_COLORS[box_id]['internal'], width=2, dash='dash'),
                legendgroup=f'box{box_id}',
            ))
    
    # Add room temperature (dotted line)
    if include_room and 'room_temp' in data.columns and not normalized:
        # Average room temp across boxes (should be identical)
        room_data = data.groupby('timestamp')['room_temp'].mean().reset_index()
        
        fig.add_trace(go.Scatter(
            x=room_data['timestamp'],
            y=room_data['room_temp'],
            mode='lines',
            name='Room Temperature',
            line=dict(color=ROOM_TEMP_COLOR, width=2.5, dash='dot'),
        ))
    elif include_room and normalized:
        # In normalized mode, add a reference line at y=0 for room temp
        fig.add_hline(
            y=0,
            line_dash="dot",
            line_color=ROOM_TEMP_COLOR,
            line_width=2,
            annotation_text="Out Air Temp (Room) = 0°C",
            annotation_position="right"
        )
    
    # Add wall type change markers for experimental box (box 2)
    exp_data = data[data['box_id'] == 2].sort_values('timestamp')
    if len(exp_data) > 0 and 'wall_type' in exp_data.columns:
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
    
    title = 'Box-Level Temperature Timeline'
    if normalized:
        title += ' (Normalized)'
    
    fig.update_layout(
        title=title,
        xaxis_title='Time',
        yaxis_title=y_label,
        hovermode='x unified',
        height=500,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    
    return fig


def plot_timeline_wall_comparison(wall_data, wall_id, normalized=False, smoothing=None):
    """
    Plot timeline comparing the same wall across both boxes.
    E.g., Wall 1 in Control vs Wall 1 in Experimental
    """
    fig = go.Figure()
    
    # Determine variable names
    if normalized:
        internal_var = 'in_normalized_internal'
        surface_var = 'in_normalized_surface'
        out_surface_var = 'out_normalized_surface'
        y_label = 'Temperature Relative to Room (°C)'
    else:
        internal_var = 'in_internal'
        surface_var = 'in_surface'
        out_surface_var = 'out_surface'
        y_label = 'Temperature (°C)'
    
    # Use smoothed if available
    internal_col = f'{internal_var}_smooth' if smoothing and f'{internal_var}_smooth' in wall_data.columns else internal_var
    surface_col = f'{surface_var}_smooth' if smoothing and f'{surface_var}_smooth' in wall_data.columns else surface_var
    out_surface_col = f'{out_surface_var}_smooth' if smoothing and f'{out_surface_var}_smooth' in wall_data.columns else out_surface_var
    
    # Plot both boxes for the same wall
    for box_id in [1, 2]:
        wall_subset = wall_data[(wall_data['box_id'] == box_id) & (wall_data['wall_id'] == wall_id)].sort_values('timestamp')
        
        if len(wall_subset) == 0:
            continue
        
        box_name = 'Control' if box_id == 1 else 'Experimental'
        # Use same base color for all three temps within each box for visual consistency
        base_color = WALL_COMPARISON_COLORS[wall_id][f'box{box_id}']
        
        # Internal temp (solid line)
        fig.add_trace(go.Scatter(
            x=wall_subset['timestamp'],
            y=wall_subset[internal_col],
            mode='lines',
            name=f'{box_name} - Internal',
            line=dict(color=base_color, width=2.5),
            legendgroup=f'box{box_id}',
        ))
        
        # Inside Surface temp (dashed line)
        if surface_var in wall_data.columns:
            fig.add_trace(go.Scatter(
                x=wall_subset['timestamp'],
                y=wall_subset[surface_col],
                mode='lines',
                name=f'{box_name} - Inside Surface',
                line=dict(color=base_color, width=2, dash='dash'),
                legendgroup=f'box{box_id}',
            ))
        
        # Outside Surface temp (dotted line)
        if out_surface_var in wall_data.columns:
            fig.add_trace(go.Scatter(
                x=wall_subset['timestamp'],
                y=wall_subset[out_surface_col],
                mode='lines',
                name=f'{box_name} - Outside Surface',
                line=dict(color=base_color, width=2, dash='dot'),
                legendgroup=f'box{box_id}',
            ))
    
    # Add wall type change markers
    exp_wall = wall_data[(wall_data['box_id'] == 2) & (wall_data['wall_id'] == wall_id)].sort_values('timestamp')
    if len(exp_wall) > 0 and 'wall_type' in exp_wall.columns:
        changes = detect_wall_type_changes(exp_wall)
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
    
    title = f'Wall {wall_id} Comparison: Control vs Experimental'
    if normalized:
        title += ' (Normalized)'
    
    fig.update_layout(
        title=title,
        xaxis_title='Time',
        yaxis_title=y_label,
        hovermode='x unified',
        height=500,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    
    return fig


def plot_timeline_wall(data, walls=None, box_id=2, smoothing=None, show_internal=True, show_in_surface=True, show_out_surface=False):
    """
    Plot timeline for individual walls within one box.
    Shows internal, inside surface, and/or outside surface temperatures for each wall.
    """
    fig = go.Figure()
    
    if walls is None:
        walls = [1, 2, 3, 4]
    
    # Use inside sensor values
    internal_var = 'in_internal'
    in_surface_var = 'in_surface'
    out_surface_var = 'out_surface'
    
    internal_col = f'{internal_var}_smooth' if smoothing and f'{internal_var}_smooth' in data.columns else internal_var
    in_surface_col = f'{in_surface_var}_smooth' if smoothing and f'{in_surface_var}_smooth' in data.columns else in_surface_var
    out_surface_col = f'{out_surface_var}_smooth' if smoothing and f'{out_surface_var}_smooth' in data.columns else out_surface_var
    
    # Add averaged internal temp line (all walls have same internal temp)
    if show_internal:
        # Get all selected walls data and average the internal temp
        all_walls_data = data[(data['box_id'] == box_id) & (data['wall_id'].isin(walls))]
        if len(all_walls_data) > 0:
            avg_internal = all_walls_data.groupby('timestamp')[internal_col].mean().reset_index()
            
            fig.add_trace(go.Scatter(
                x=avg_internal['timestamp'],
                y=avg_internal[internal_col],
                mode='lines',
                name='Internal Temp (All Walls Average)',
                line=dict(color='#2D3748', width=2),
                legendgroup='internal',
            ))
    
    # Add surface temps for each wall
    for wall_id in walls:
        wall_data = data[(data['box_id'] == box_id) & (data['wall_id'] == wall_id)].sort_values('timestamp')
        
        if len(wall_data) == 0:
            continue
        
        color = WALL_COLORS.get(wall_id, 'gray')
        
        # Inside surface temp (dashed)
        if show_in_surface and in_surface_var in data.columns:
            fig.add_trace(go.Scatter(
                x=wall_data['timestamp'],
                y=wall_data[in_surface_col],
                mode='lines',
                name=f'Wall {wall_id} - Inside Surface',
                line=dict(color=color, width=2, dash='dash'),
                legendgroup=f'wall{wall_id}',
            ))
        
        # Outside surface temp (dotted)
        if show_out_surface and out_surface_var in data.columns:
            fig.add_trace(go.Scatter(
                x=wall_data['timestamp'],
                y=wall_data[out_surface_col],
                mode='lines',
                name=f'Wall {wall_id} - Outside Surface',
                line=dict(color=color, width=1.5, dash='dot'),
                legendgroup=f'wall{wall_id}',
            ))
    
    # Add wall type change markers (for experimental box)
    if box_id == 2:
        box_subset = data[data['box_id'] == box_id]
        if len(box_subset) > 0 and 'wall_type' in box_subset.columns:
            changes = detect_wall_type_changes(box_subset)
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
    
    box_name = 'Control' if box_id == 1 else 'Experimental'
    fig.update_layout(
        title=f'Individual Walls Timeline - {box_name} Box',
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        hovermode='x unified',
        height=500,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    
    return fig


def plot_sandwich_view(data, box_id=2, wall_ids=None):
    """
    Plot outside vs inside surface temperatures with thermal lag calculation BY WALL TYPE.
    
    Thermal Lag Explanation:
    - Measures time delay for heat to transfer from outside to inside of wall
    - Calculated using cross-correlation between outside and inside surface temps
    - Higher lag = better insulation (heat takes longer to penetrate)
    - Correlation (r) indicates how similar the patterns are (1.0 = identical shape)
    - NOW GROUPED BY WALL TYPE instead of individual walls
    """
    box_data = data[data['box_id'] == box_id].copy()
    
    if len(box_data) == 0:
        return go.Figure()
    
    # Get unique wall types in order
    wall_types = box_data['wall_type'].dropna().unique()
    wall_types = sorted([wt for wt in wall_types if pd.notna(wt)])
    
    if len(wall_types) == 0:
        return go.Figure()
    
    fig = make_subplots(
        rows=len(wall_types), 
        cols=1,
        subplot_titles=[f'Wall Type: {wt}' for wt in wall_types],
        vertical_spacing=0.08,
    )
    
    for idx, wall_type in enumerate(wall_types, 1):
        # Get data for this wall type (aggregate across all walls with this type)
        wall_type_data = box_data[box_data['wall_type'] == wall_type].sort_values('timestamp')
        
        if len(wall_type_data) == 0:
            continue
        
        # Aggregate by timestamp (average across all walls of same type)
        aggregated = wall_type_data.groupby('timestamp').agg({
            'out_surface': 'mean',
            'in_surface': 'mean'
        }).reset_index()
        
        # Outside Surface (heat arriving at exterior)
        if 'out_surface' in aggregated.columns:
            fig.add_trace(go.Scatter(
                x=aggregated['timestamp'],
                y=aggregated['out_surface'],
                mode='lines',
                name='Outside Surface' if idx == 1 else None,
                line=dict(color='#E63946', width=2.5),
                legendgroup='outside',
                showlegend=(idx == 1),
            ), row=idx, col=1)
        
        # Inside Surface (heat arriving at interior)
        if 'in_surface' in aggregated.columns:
            fig.add_trace(go.Scatter(
                x=aggregated['timestamp'],
                y=aggregated['in_surface'],
                mode='lines',
                name='Inside Surface' if idx == 1 else None,
                line=dict(color='#118AB2', width=2.5),
                legendgroup='inside',
                showlegend=(idx == 1),
            ), row=idx, col=1)
        
        # Calculate thermal lag for this wall type
        if 'out_surface' in aggregated.columns and 'in_surface' in aggregated.columns:
            lag, corr = calculate_thermal_lag(aggregated['out_surface'], aggregated['in_surface'])
            
            if lag is not None and corr is not None:
                annotation_text = f'Thermal Lag: {lag:.0f} min | Correlation: {corr:.2f}'
                fig.add_annotation(
                    xref=f'x{idx}', yref=f'y{idx}',
                    x=aggregated['timestamp'].iloc[len(aggregated)//2],
                    y=aggregated[['out_surface', 'in_surface']].max().max(),
                    text=annotation_text,
                    showarrow=False,
                    bgcolor='rgba(255, 255, 255, 0.9)',
                    font=dict(size=12, color='black'),
                    bordercolor='black',
                    borderwidth=1,
                )
        
        fig.update_xaxes(title_text='', row=idx, col=1)
        fig.update_yaxes(title_text='Temperature (°C)', row=idx, col=1)
    
    # Add x-axis title to last subplot
    fig.update_xaxes(title_text='Time', row=len(wall_types), col=1)
    
    box_name = 'Control' if box_id == 1 else 'Experimental'
    fig.update_layout(
        title=f'Thermal Transfer Analysis by Wall Type - {box_name} Box',
        height=300 * len(wall_types),
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    
    return fig


def plot_thermal_gradient_summary(data, periods=None):
    """
    Plot thermal gradient summary by wall type.
    Shows temperature profile: Outside Air → Outside Surface → Inside Surface → Internal Temp
    With 2 key gradients:
    1. Surface gradient: Outside Surface - Inside Surface
    2. Total gradient: Outside Air - Internal Temp
    """
    if periods is None:
        periods = data['period'].unique()
    
    filtered = data[data['period'].isin(periods)]
    
    # Check which columns are available and build aggregation dict dynamically
    agg_dict = {}
    required_cols = []
    
    if 'room_temp' in filtered.columns:
        agg_dict['room_temp'] = 'mean'
        required_cols.append('room_temp')
    
    if 'out_surface' in filtered.columns:
        agg_dict['out_surface'] = 'mean'
        required_cols.append('out_surface')
    
    if 'in_surface' in filtered.columns:
        agg_dict['in_surface'] = 'mean'
        required_cols.append('in_surface')
    
    # Use in_internal for internal temperature (average of inside sensors)
    if 'in_internal' in filtered.columns:
        agg_dict['in_internal'] = 'mean'
        required_cols.append('in_internal')
    
    if not agg_dict:
        fig = go.Figure()
        fig.add_annotation(
            text="Required columns not found in data",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # Group by wall_type and calculate mean values
    summary = filtered.groupby('wall_type').agg(agg_dict).reset_index()
    
    # Filter out rows with missing data in required columns
    summary = summary.dropna(subset=required_cols)
    
    if len(summary) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for gradient analysis",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # Calculate gradients for bar chart
    summary['surface_gradient'] = summary['out_surface'] - summary['in_surface']
    summary['total_gradient'] = summary['room_temp'] - summary['in_internal']
    
    # Define colors for wall types
    wall_type_colors = {
        'Exposed': '#E63946',
        'Yarka': '#06A77D',
        'Dry soil': '#F77F00',
        'Succalents': '#6A4C93',
        'Wet soil': '#1E88E5',
    }
    
    # Create subplots: top for gradient lines, bottom for bar chart
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.15,
        subplot_titles=('Temperature Gradients by Wall Type', 'Temperature Deltas (ΔT)')
    )
    
    # ===== TOP PLOT: Gradient Lines =====
    # Add spacing between wall types by using different y positions
    # We'll have 2 rows per wall type: one for surface gradient, one for total gradient
    wall_types = summary['wall_type'].tolist()
    y_positions = {}
    current_y = 0
    for wt in wall_types:
        y_positions[f"{wt}_surface"] = current_y
        y_positions[f"{wt}_total"] = current_y + 1
        current_y += 2.5  # Add spacing between wall types
    
    # Plot gradients for each wall type
    for idx, row in summary.iterrows():
        wall_type = row['wall_type']
        color = wall_type_colors.get(wall_type, '#6C757D')
        
        # Line 1: Surface gradient (out_surface → in_surface)
        y_surf = y_positions[f"{wall_type}_surface"]
        fig.add_trace(go.Scatter(
            x=[row['out_surface'], row['in_surface']],
            y=[y_surf, y_surf],
            mode='lines+markers',
            marker=dict(
                size=16,
                symbol=['circle', 'square'],
                color=color,
                line=dict(width=2, color='white')
            ),
            line=dict(width=4, color=color),
            name=f"{wall_type} - Surface",
            legendgroup=wall_type,
            hovertemplate='%{text}<br>Temp: %{x:.2f}°C<extra></extra>',
            text=[
                f"{wall_type} - Outside Surface",
                f"{wall_type} - Inside Surface"
            ],
        ), row=1, col=1)
        
        # Surface gradient annotation
        surface_grad = row['surface_gradient']
        mid_x_surf = (row['out_surface'] + row['in_surface']) / 2
        fig.add_annotation(
            xref='x', yref='y',
            x=mid_x_surf,
            y=y_surf,
            text=f"ΔT={surface_grad:.2f}°C",
            showarrow=False,
            yshift=20,
            font=dict(size=10, color='black', family='Arial Black'),
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor=color,
            borderwidth=1,
            borderpad=3,
        )
        
        # Line 2: Total gradient (room_temp → in_internal)
        y_total = y_positions[f"{wall_type}_total"]
        fig.add_trace(go.Scatter(
            x=[row['room_temp'], row['in_internal']],
            y=[y_total, y_total],
            mode='lines+markers',
            marker=dict(
                size=16,
                symbol=['diamond', 'triangle-up'],
                color=color,
                line=dict(width=2, color='white')
            ),
            line=dict(width=4, color=color, dash='dot'),
            name=f"{wall_type} - Total",
            legendgroup=wall_type,
            hovertemplate='%{text}<br>Temp: %{x:.2f}°C<extra></extra>',
            text=[
                f"{wall_type} - Outside Air",
                f"{wall_type} - Internal"
            ],
        ), row=1, col=1)
        
        # Total gradient annotation
        total_grad = row['total_gradient']
        mid_x_total = (row['room_temp'] + row['in_internal']) / 2
        fig.add_annotation(
            xref='x', yref='y',
            x=mid_x_total,
            y=y_total,
            text=f"ΔT={total_grad:.2f}°C",
            showarrow=False,
            yshift=20,
            font=dict(size=10, color='black', family='Arial Black'),
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor=color,
            borderwidth=1,
            borderpad=3,
        )
    
    # ===== BOTTOM PLOT: Horizontal Bar Chart for Deltas =====
    # Sort summary by total gradient for better visualization
    summary_sorted = summary.sort_values('total_gradient', ascending=True)
    
    for idx, row in summary_sorted.iterrows():
        wall_type = row['wall_type']
        color = wall_type_colors.get(wall_type, '#6C757D')
        
        # Surface gradient bar
        fig.add_trace(go.Bar(
            y=[f"{wall_type}<br>(Surface)"],
            x=[row['surface_gradient']],
            orientation='h',
            name=f"{wall_type} - Surface ΔT",
            marker=dict(color=color, line=dict(color='white', width=2)),
            text=f"{row['surface_gradient']:.2f}°C",
            textposition='outside',
            textfont=dict(size=11, color='black'),
            hovertemplate=f"{wall_type}<br>Surface ΔT: %{{x:.2f}}°C<extra></extra>",
            showlegend=False,
        ), row=2, col=1)
        
        # Total gradient bar
        fig.add_trace(go.Bar(
            y=[f"{wall_type}<br>(Total)"],
            x=[row['total_gradient']],
            orientation='h',
            name=f"{wall_type} - Total ΔT",
            marker=dict(color=color, line=dict(color='white', width=2), pattern=dict(shape='/')),
            text=f"{row['total_gradient']:.2f}°C",
            textposition='outside',
            textfont=dict(size=11, color='black'),
            hovertemplate=f"{wall_type}<br>Total ΔT: %{{x:.2f}}°C<extra></extra>",
            showlegend=False,
        ), row=2, col=1)
    
    # Create y-axis labels for top plot
    y_tick_vals = []
    y_tick_labels = []
    for wt in wall_types:
        mid_y = (y_positions[f"{wt}_surface"] + y_positions[f"{wt}_total"]) / 2
        y_tick_vals.append(mid_y)
        y_tick_labels.append(wt)
    
    # Update layout
    fig.update_xaxes(title_text='Temperature (°C)', row=1, col=1, zeroline=True, zerolinewidth=2, zerolinecolor='lightgray')
    fig.update_xaxes(title_text='Temperature Difference (ΔT °C)', row=2, col=1, zeroline=True, zerolinewidth=2, zerolinecolor='lightgray')
    fig.update_yaxes(title_text='Wall Type', row=1, col=1, tickmode='array', tickvals=y_tick_vals, ticktext=y_tick_labels)
    fig.update_yaxes(title_text='', row=2, col=1)
    
    fig.update_layout(
        height=max(700, len(summary) * 120 + 400),
        hovermode='closest',
        showlegend=False,
        margin=dict(b=60, r=100, l=150),
    )
    
    return fig


def plot_diagnostic_overlay(data, box_id=1, y_var='internal_temp'):
    """
    Plot all 16 sensors as semi-transparent lines with box average highlighted.
    Sensors are colored by position (outside=red, inside=blue).
    """
    fig = go.Figure()
    
    # Individual sensors (more visible, less transparent)
    for sensor_id in range(1, 17):
        sensor_data = data[(data['box_id'] == box_id) & (data['sensor_id'] == sensor_id)].sort_values('timestamp')
        
        if len(sensor_data) == 0:
            continue
        
        # Determine position for color
        position = sensor_data['position'].iloc[0] if 'position' in sensor_data.columns else 'unknown'
        color = POSITION_COLORS.get(position, 'gray')
        
        fig.add_trace(go.Scatter(
            x=sensor_data['timestamp'],
            y=sensor_data[y_var],
            mode='lines',
            name=f'S{sensor_id}',
            line=dict(color=color, width=1),
            opacity=0.5,  # Increased from 0.3
        ))
    
    # Box average (less bold, more subtle)
    box_avg = data[data['box_id'] == box_id].groupby('timestamp')[y_var].mean().reset_index()
    
    fig.add_trace(go.Scatter(
        x=box_avg['timestamp'],
        y=box_avg[y_var],
        mode='lines',
        name='Box Average',
        line=dict(color='#2D3748', width=2.5, dash='solid'),  # Reduced from 3, darker gray
        opacity=0.9,
    ))
    
    y_labels = {
        'internal_temp': 'Internal Temperature (°C)',
        'surface_temp': 'Surface Temperature (°C)',
        'normalized_internal': 'Normalized Internal Temp (°C)',
        'normalized_surface': 'Normalized Surface Temp (°C)',
    }
    y_label = y_labels.get(y_var, y_var)
    
    box_name = 'Control' if box_id == 1 else 'Experimental'
    fig.update_layout(
        title=f'Diagnostic Overlay - All Sensors ({box_name} Box)',
        xaxis_title='Time',
        yaxis_title=y_label,
        height=500,
        hovermode='x unified',
        showlegend=False,
    )
    
    return fig


def plot_correlation_heatmap(data):
    """
    Create correlation heatmap between room temp and box metrics.
    Shows relationships between internal temps, surface temps, and room temp for both boxes.
    """
    # Prepare data for correlation
    corr_data = data.pivot_table(
        index='timestamp',
        columns='box_id',
        values=['internal_temp', 'surface_temp', 'room_temp'],
    )
    
    # Flatten column names with clearer labels
    new_cols = []
    for col in corr_data.columns:
        box_name = 'Control' if col[1] == 1 else 'Experimental'
        var_name = col[0].replace('_', ' ').title()
        new_cols.append(f'{box_name}\n{var_name}')
    
    corr_data.columns = new_cols
    
    # Remove duplicate room_temp columns (should be identical)
    # Keep only unique columns
    unique_cols = []
    seen_vars = set()
    for col in corr_data.columns:
        var = col.split('\n')[1]  # Get variable name
        if var == 'Room Temp' and 'Room Temp' in seen_vars:
            continue
        unique_cols.append(col)
        seen_vars.add(var)
    
    corr_data = corr_data[unique_cols]
    
    # Calculate correlation matrix
    corr_matrix = corr_data.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu_r',  # Reversed so red = positive correlation
        zmid=0,
        zmin=-1,
        zmax=1,
        text=corr_matrix.values.round(2),
        texttemplate='%{text}',
        textfont={"size": 11},
        hovertemplate='%{y} vs %{x}<br>Correlation: %{z:.2f}<extra></extra>',
    ))
    
    fig.update_layout(
        title='Temperature Correlation Matrix<br><sub>Pearson correlation between temperature measurements</sub>',
        height=650,
        width=750,
        xaxis={'side': 'bottom'},
        yaxis={'tickmode': 'linear'},
    )
    
    return fig


def create_summary_table(data):
    """
    Create summary statistics table by wall type and period.
    """
    if 'wall_type' not in data.columns:
        return None
    
    summary = data.groupby(['period', 'wall_type']).agg({
        'out_normalized_internal': ['mean', 'std'],
        'in_normalized_internal': ['mean', 'std'],
        'surface_gradient': ['mean', 'std'],
        'internal_gradient': ['mean', 'std'],
    }).round(2)
    
    # Flatten multi-index columns
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    
    return summary


def plot_thermal_gradient_normalized(data, periods=None, normalized=False):
    """
    Plot thermal gradient summary with normalized delta view.
    Shows delta at each timestamp, with 2 key gradients per wall type:
    1. Surface gradient: Outside Surface - Inside Surface
    2. Total gradient: Outside Air - Internal Temp
    
    Parameters:
    - normalized: If True, shows deltas relative to room temperature (temps normalized first)
    """
    if periods is None:
        periods = data['period'].unique()
    
    filtered = data[data['period'].isin(periods)]
    
    # Check which columns are available
    if normalized:
        # Use normalized columns if available
        out_surface_col = 'out_normalized_surface' if 'out_normalized_surface' in filtered.columns else 'out_surface'
        in_surface_col = 'in_normalized_surface' if 'in_normalized_surface' in filtered.columns else 'in_surface'
        internal_col = 'in_normalized_internal' if 'in_normalized_internal' in filtered.columns else 'in_internal'
        # In normalized view, room_temp equivalent is 0
        room_temp_col = None
    else:
        out_surface_col = 'out_surface'
        in_surface_col = 'in_surface'
        internal_col = 'in_internal'
        room_temp_col = 'room_temp'
    
    required_cols = [out_surface_col, in_surface_col, internal_col]
    if not normalized:
        required_cols.append(room_temp_col)
    
    # Check for missing columns
    missing = [c for c in required_cols if c not in filtered.columns]
    if missing:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Required columns not found: {missing}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # Get unique wall types
    wall_types = filtered['wall_type'].dropna().unique()
    wall_types = sorted([wt for wt in wall_types if pd.notna(wt)])
    
    if len(wall_types) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No wall type data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # Define colors for wall types
    wall_type_colors = {
        'Exposed': '#E63946',
        'Yarka': '#06A77D',
        'Dry soil': '#F77F00',
        'Succalents': '#6A4C93',
        'Wet soil': '#1E88E5',
    }
    
    # Create figure with 2 subplots (Surface Gradient, Total Gradient)
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.12,
        subplot_titles=(
            'Surface Temperature Delta (ΔT = Outside Surface - Inside Surface)',
            'Total Temperature Delta (ΔT = Outside Air - Internal Temp)'
        )
    )
    
    # Plot deltas over time for each wall type
    for wall_type in wall_types:
        wall_data_filtered = filtered[filtered['wall_type'] == wall_type].copy()
        
        if len(wall_data_filtered) == 0:
            continue
        
        color = wall_type_colors.get(wall_type, '#6C757D')
        
        # Aggregate by timestamp (mean across walls of same type)
        agg_cols = {'timestamp': 'first'}
        for col in [out_surface_col, in_surface_col, internal_col]:
            if col in wall_data_filtered.columns:
                agg_cols[col] = 'mean'
        if room_temp_col and room_temp_col in wall_data_filtered.columns:
            agg_cols[room_temp_col] = 'mean'
        
        aggregated = wall_data_filtered.groupby('timestamp').agg(agg_cols).reset_index(drop=True)
        aggregated = aggregated.sort_values('timestamp')
        
        # Calculate Surface Gradient (out_surface - in_surface)
        aggregated['surface_delta'] = aggregated[out_surface_col] - aggregated[in_surface_col]
        
        # Calculate Total Gradient (room_temp - internal) or (0 - internal for normalized)
        if normalized:
            # In normalized view, room=0, so delta = 0 - internal = -internal
            aggregated['total_delta'] = -aggregated[internal_col]
        else:
            aggregated['total_delta'] = aggregated[room_temp_col] - aggregated[internal_col]
        
        # Plot Surface Delta
        fig.add_trace(go.Scatter(
            x=aggregated['timestamp'],
            y=aggregated['surface_delta'],
            mode='lines',
            name=wall_type,
            line=dict(color=color, width=2),
            legendgroup=wall_type,
            showlegend=True,
            hovertemplate=f'{wall_type}<br>Time: %{{x}}<br>ΔT: %{{y:.2f}}°C<extra></extra>',
        ), row=1, col=1)
        
        # Plot Total Delta
        fig.add_trace(go.Scatter(
            x=aggregated['timestamp'],
            y=aggregated['total_delta'],
            mode='lines',
            name=wall_type,
            line=dict(color=color, width=2),
            legendgroup=wall_type,
            showlegend=False,
            hovertemplate=f'{wall_type}<br>Time: %{{x}}<br>ΔT: %{{y:.2f}}°C<extra></extra>',
        ), row=2, col=1)
    
    # Add zero line reference
    fig.add_hline(y=0, row=1, col=1, line_dash="dash", line_color="gray", line_width=1)
    fig.add_hline(y=0, row=2, col=1, line_dash="dash", line_color="gray", line_width=1)
    
    # Update layout
    title = 'Thermal Gradients Over Time by Wall Type'
    if normalized:
        title += ' (Normalized View)'
    
    fig.update_layout(
        title=title,
        height=700,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    
    fig.update_xaxes(title_text='Time', row=2, col=1)
    fig.update_yaxes(title_text='ΔT (°C)', row=1, col=1)
    fig.update_yaxes(title_text='ΔT (°C)', row=2, col=1)
    
    return fig


def plot_temperature_relationship(data, periods=None, x_var='room_temp', y_var='in_internal', normalized=False):
    """
    Plot temperature relationship scatter plot grouped by wall type.
    For each x value, calculates mean y values per wall type and connects dots.
    
    Parameters:
    - x_var: Variable for x-axis ('room_temp', 'out_surface', 'in_surface', 'in_internal')
    - y_var: Variable for y-axis ('room_temp', 'out_surface', 'in_surface', 'in_internal')
    - normalized: If True, use normalized temperature columns
    """
    if periods is None:
        periods = data['period'].unique()
    
    filtered = data[data['period'].isin(periods)].copy()
    
    # Map variable names to column names
    var_mapping = {
        'room_temp': ('room_temp', 'Out Air Temp'),
        'out_surface': ('out_surface' if not normalized else 'out_normalized_surface', 'Outside Wall Temp'),
        'in_surface': ('in_surface' if not normalized else 'in_normalized_surface', 'Inside Wall Temp'),
        'in_internal': ('in_internal' if not normalized else 'in_normalized_internal', 'Internal Temp'),
    }
    
    # Handle normalized room_temp (it's always 0 in normalized view)
    if normalized and x_var == 'room_temp':
        x_col = 'room_temp'  # Will be replaced with 0
        x_label = 'Out Air Temp (=0 in normalized)'
    else:
        x_col, x_label = var_mapping.get(x_var, ('room_temp', 'Out Air Temp'))
    
    if normalized and y_var == 'room_temp':
        y_col = 'room_temp'
        y_label = 'Out Air Temp (=0 in normalized)'
    else:
        y_col, y_label = var_mapping.get(y_var, ('in_internal', 'Internal Temp'))
    
    if normalized:
        x_label += ' (Normalized)'
        y_label += ' (Normalized)'
    
    # Check columns exist
    if x_col not in filtered.columns:
        # Try alternative
        alt_col = x_col.replace('normalized_', '')
        if alt_col in filtered.columns:
            x_col = alt_col
        else:
            fig = go.Figure()
            fig.add_annotation(text=f"Column '{x_col}' not found", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
    
    if y_col not in filtered.columns:
        alt_col = y_col.replace('normalized_', '')
        if alt_col in filtered.columns:
            y_col = alt_col
        else:
            fig = go.Figure()
            fig.add_annotation(text=f"Column '{y_col}' not found", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
    
    # Get unique wall types
    wall_types = filtered['wall_type'].dropna().unique()
    wall_types = sorted([wt for wt in wall_types if pd.notna(wt)])
    
    if len(wall_types) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No wall type data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Define colors for wall types
    wall_type_colors = {
        'Exposed': '#E63946',
        'Yarka': '#06A77D',
        'Dry soil': '#F77F00',
        'Succalents': '#6A4C93',
        'Wet soil': '#1E88E5',
    }
    
    fig = go.Figure()
    
    for wall_type in wall_types:
        wall_data_filtered = filtered[filtered['wall_type'] == wall_type].copy()
        
        if len(wall_data_filtered) == 0:
            continue
        
        color = wall_type_colors.get(wall_type, '#6C757D')
        
        # Round x values to bin them (1 decimal place for temperature)
        wall_data_filtered['x_binned'] = wall_data_filtered[x_col].round(1)
        
        # For normalized room_temp, x is always 0
        if normalized and x_var == 'room_temp':
            wall_data_filtered['x_binned'] = 0
        
        # Group by x_binned and calculate mean y
        grouped = wall_data_filtered.groupby('x_binned').agg({
            y_col: 'mean',
            'timestamp': 'count'  # Count for hover info
        }).reset_index()
        grouped = grouped.rename(columns={'timestamp': 'count'})
        grouped = grouped.sort_values('x_binned')
        
        # Plot line with markers
        fig.add_trace(go.Scatter(
            x=grouped['x_binned'],
            y=grouped[y_col],
            mode='lines+markers',
            name=wall_type,
            line=dict(color=color, width=2),
            marker=dict(size=8, color=color, line=dict(width=1, color='white')),
            hovertemplate=f'{wall_type}<br>{x_label}: %{{x:.1f}}°C<br>{y_label}: %{{y:.2f}}°C<br>N=%{{customdata}}<extra></extra>',
            customdata=grouped['count'],
        ))
    
    title = f'{y_label} vs {x_label} by Wall Type'
    if normalized:
        title += ' (Normalized View)'
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label + ' (°C)',
        yaxis_title=y_label + ' (°C)',
        height=500,
        hovermode='closest',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    
    return fig
