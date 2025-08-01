"""
Visualization module for the Korean Stock Analysis System.

This module contains classes for creating visualizations of stock analysis results.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Optional

from .config import logger


class VisualizationEngine:
    """Visualization engine for stock analysis results.
    
    This class provides methods for creating visualizations of stock analysis results,
    including risk-return scatter plots and other visualizations.
    """
    
    def __init__(self):
        """Initialize the VisualizationEngine."""
        pass
    
    def create_risk_return_scatter(self, df: pd.DataFrame, title: str = "Risk-Return Analysis") -> go.Figure:
        """Create a risk-return scatter plot.
        
        Args:
            df (pd.DataFrame): DataFrame containing stock analysis results.
            title (str, optional): Plot title. Defaults to "Risk-Return Analysis".
            
        Returns:
            go.Figure: Plotly figure object.
        """
        if df.empty:
            return go.Figure()
        
        # Separate anomalies and normal points
        anomalies = df[df.get('is_anomaly', False)]
        normal_points = df[~df.get('is_anomaly', False)]
        
        fig = go.Figure()
        
        # Normal points
        if not normal_points.empty:
            fig.add_trace(go.Scatter(
                x=normal_points.get('volatility_annual', []) * 100,
                y=normal_points.get('annualized_return', []) * 100,
                mode='markers',
                name='Normal Stocks',
                text=normal_points.get('company_name', []),
                hovertemplate='<b>%{text}</b><br>' +
                              'Annual Return: %{y:.1f}%<br>' +
                              'Annual Volatility: %{x:.1f}%<br>' +
                              '<extra></extra>',
                marker=dict(
                    size=8,
                    color='lightblue',
                    line=dict(width=1, color='darkblue')
                )
            ))
        
        # Anomalies
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies.get('volatility_annual', []) * 100,
                y=anomalies.get('annualized_return', []) * 100,
                mode='markers',
                name='Anomaly Stocks',
                text=anomalies.get('company_name', []),
                hovertemplate='<b>%{text}</b><br>' +
                              'Annual Return: %{y:.1f}%<br>' +
                              'Annual Volatility: %{x:.1f}%<br>' +
                              'Anomaly Score: %{customdata:.3f}<br>' +
                              '<extra></extra>',
                customdata=anomalies.get('anomaly_score', []),
                marker=dict(
                    size=12,
                    color='red',
                    line=dict(width=2, color='darkred'),
                    symbol='diamond'
                )
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Annual Volatility (%)',
            yaxis_title='Annual Return (%)',
            hovermode='closest',
            width=800,
            height=600
        )
        
        return fig