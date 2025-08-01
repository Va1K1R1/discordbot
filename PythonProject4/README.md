# Korean Stock Analysis System

A comprehensive system for analyzing Korean stocks, including data collection, technical analysis, feature engineering, risk management, and visualization.

## Features

- **Data Collection**: Collect stock data, fundamental data, and macroeconomic indicators
- **Technical Analysis**: Calculate various technical indicators and market structure indicators
- **Feature Engineering**: Create advanced features from stock data, including market regime detection
- **Risk Management**: Manage risk in trading operations, including position sizing and stop loss/take profit levels
- **Stock Analysis**: Analyze Korean stocks, including technical and fundamental analysis, and anomaly detection
- **Visualization**: Create visualizations of stock analysis results

## Installation

### Prerequisites

- Python 3.7 or higher

### Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/korean-stock-analysis.git
   cd korean-stock-analysis
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # On Windows
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

## Usage

### Basic Usage

```python
from mypackage.main import run_comprehensive_analysis, create_detailed_report

# Run comprehensive analysis
results = run_comprehensive_analysis()

# Create detailed report
if results:
    create_detailed_report(results)
```

### Analyzing Specific Stocks

```python
from mypackage.stock_analysis import KoreanStockAnalyzer

# Initialize analyzer
analyzer = KoreanStockAnalyzer()

# Define stocks to analyze
stock_codes = ['005930', '000660', '035420']  # Samsung Electronics, SK Hynix, NAVER
stock_names = ['Samsung Electronics', 'SK Hynix', 'NAVER']

# Analyze stocks
analyzed_data = analyzer.analyze_multiple_stocks(stock_codes, stock_names)

# Detect anomalies
anomalies = analyzer.detect_anomalies(method='isolation_forest', contamination=0.1)

# Print results
print(f"Total stocks analyzed: {len(analyzed_data)}")
print(f"Anomalies detected: {len(anomalies)}")
```

### Creating Visualizations

```python
from mypackage.visualization import VisualizationEngine
import plotly.io as pio

# Initialize visualization engine
viz_engine = VisualizationEngine()

# Create risk-return scatter plot
fig = viz_engine.create_risk_return_scatter(analyzed_data, title="Risk-Return Analysis")

# Show plot
pio.show(fig)
```

## Project Structure

```
mypackage/
├── __init__.py          # Package initialization
├── config.py            # Configuration classes and data structures
├── data_collection.py   # Data collection classes
├── technical_analysis.py # Technical analysis classes
├── feature_engineering.py # Feature engineering classes
├── risk_management.py   # Risk management classes
├── stock_analysis.py    # Stock analysis classes
├── visualization.py     # Visualization classes
└── main.py              # Main functionality
```

## Testing

Run tests using pytest:

```bash
python -m pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [yfinance](https://github.com/ranaroussi/yfinance) for providing stock data
- [scikit-learn](https://scikit-learn.org/) for machine learning functionality
- [plotly](https://plotly.com/) for interactive visualizations