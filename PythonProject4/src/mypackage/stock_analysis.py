"""
Stock analysis module for the Korean Stock Analysis System.

This module contains classes for analyzing Korean stocks, including technical
and fundamental analysis.
"""

import time
import logging
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler

from .config import logger, StockInfo, AnalysisConfig
from .data_collection import FundamentalDataCollector, ExternalStockListCollector
from .technical_analysis import AdvancedTechnicalAnalyzer
from .feature_engineering import SmartFeatureEngineering


class AnomalyDetector:
    """Anomaly detection for stock analysis.

    This class provides methods for detecting anomalies in stock data using
    various machine learning algorithms.
    """

    def __init__(self, contamination: float = 0.1):
        """Initialize the AnomalyDetector.

        Args:
            contamination (float, optional): Expected proportion of anomalies. Defaults to 0.1.
        """
        self.contamination = contamination

    def detect_anomalies(self, df: pd.DataFrame, method: str = 'isolation_forest') -> pd.DataFrame:
        """Detect anomalies in stock data.

        Args:
            df (pd.DataFrame): DataFrame containing stock data.
            method (str, optional): Anomaly detection method. Defaults to 'isolation_forest'.

        Returns:
            pd.DataFrame: DataFrame with anomaly detection results.

        Raises:
            ValueError: If method is not supported.
        """
        if df.empty:
            logger.warning("⚠️ Empty DataFrame provided for anomaly detection")
            return df

        # Select numeric columns for analysis
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()

        # Filter out non-feature columns
        exclude_columns = ['is_anomaly', 'anomaly_score']
        feature_columns = [col for col in numeric_columns if col not in exclude_columns]

        if not feature_columns:
            logger.warning("⚠️ No numeric features available for anomaly detection")
            return df

        # Prepare feature data
        feature_data = df[feature_columns].fillna(0)

        # Normalize data
        scaler = RobustScaler()
        scaled_features = scaler.fit_transform(feature_data)

        # Detect anomalies
        if method == 'isolation_forest':
            model = IsolationForest(contamination=self.contamination, random_state=42)
            outliers = model.fit_predict(scaled_features)
            scores = model.score_samples(scaled_features)
        elif method == 'lof':
            model = LocalOutlierFactor(contamination=self.contamination)
            outliers = model.fit_predict(scaled_features)
            scores = model.negative_outlier_factor_
        else:
            raise ValueError(f"Unsupported method: {method}. Use 'isolation_forest' or 'lof'.")

        # Add results to DataFrame
        df_result = df.copy()
        df_result['is_anomaly'] = outliers == -1
        df_result['anomaly_score'] = scores

        anomaly_count = df_result['is_anomaly'].sum()
        logger.info(f"🔍 Detected {anomaly_count} anomalies ({method}, contamination={self.contamination})")

        return df_result


class KoreanStockAnalyzer:
    """Korean listed company risk-return analysis system.

    This class provides methods for analyzing Korean stocks, including
    technical and fundamental analysis, and anomaly detection.
    """

    def __init__(self):
        """Initialize the KoreanStockAnalyzer."""
        self.fundamental_collector = FundamentalDataCollector()
        self.technical_analyzer = AdvancedTechnicalAnalyzer()
        self.feature_engineer = SmartFeatureEngineering()
        self.analyzed_stocks = pd.DataFrame()
        self.anomalies = pd.DataFrame()

    def get_stock_data(self, code: str, name: str, period: str = "1y") -> dict:
        """Collect individual stock data.

        Args:
            code (str): Stock code.
            name (str): Stock name.
            period (str, optional): Data period. Defaults to "1y".

        Returns:
            dict: Dictionary containing stock data.
        """
        try:
            # Auto-detect .KS or .KQ suffix
            if not code.endswith(('.KS', '.KQ')):
                code = f"{code}.KS"

            import yfinance as yf
            ticker = yf.Ticker(code)
            hist_data = ticker.history(period=period)

            if hist_data.empty:
                # Try .KQ if .KS fails
                code = code.replace('.KS', '.KQ')
                ticker = yf.Ticker(code)
                hist_data = ticker.history(period=period)

            if hist_data.empty:
                logger.warning(f"No data for: {name} ({code})")
                return None

            # Collect financial data
            financial_data = self.fundamental_collector.get_financial_data_from_yfinance(code)

            return {
                'code': code,
                'name': name,
                'price_data': hist_data,
                'financial_data': financial_data
            }

        except Exception as e:
            logger.error(f"Error collecting stock data ({name}): {e}")
            return None

    def calculate_technical_indicators(self, price_data: pd.DataFrame) -> dict:
        """Calculate technical indicators.

        Args:
            price_data (pd.DataFrame): Price data.

        Returns:
            dict: Dictionary containing technical indicators.
        """
        try:
            if price_data.empty or len(price_data) < 50:
                return {}

            # Basic return calculation
            returns = price_data['Close'].pct_change().dropna()

            # Risk metrics
            volatility_daily = returns.std()
            volatility_annual = volatility_daily * np.sqrt(252)

            # Return metrics
            total_return = (price_data['Close'].iloc[-1] / price_data['Close'].iloc[0]) - 1
            annualized_return = (1 + total_return) ** (252 / len(price_data)) - 1

            # Sharpe ratio (assuming 3% risk-free rate)
            risk_free_rate = 0.03
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility_annual if volatility_annual > 0 else 0

            # Maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()

            # VaR calculation (95% confidence interval)
            var_95 = np.percentile(returns, 5)

            # CVaR calculation (Conditional Value at Risk)
            cvar_95 = returns[returns <= var_95].mean()

            # Momentum indicators
            momentum_5d = price_data['Close'].pct_change(5).iloc[-1]
            momentum_20d = price_data['Close'].pct_change(20).iloc[-1]

            # Bollinger Bands position
            sma_20 = price_data['Close'].rolling(20).mean()
            std_20 = price_data['Close'].rolling(20).std()
            bb_upper = sma_20 + (2 * std_20)
            bb_lower = sma_20 - (2 * std_20)
            bb_position = ((price_data['Close'] - bb_lower) / (bb_upper - bb_lower)).iloc[-1]

            # RSI
            delta = price_data['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1]

            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility_annual': volatility_annual,
                'sharpe_ratio': sharpe_ratio, 
                'max_drawdown': max_drawdown,
                'var_95': var_95,
                'cvar_95': cvar_95,
                'momentum_5d': momentum_5d,
                'momentum_20d': momentum_20d,
                'bb_position': bb_position,
                'rsi': rsi,
            }

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}

    def analyze_multiple_stocks(self, stock_codes: list, stock_names: list, max_stocks: int = 50) -> pd.DataFrame:
        """Analyze multiple stocks.

        Args:
            stock_codes (list): List of stock codes.
            stock_names (list): List of stock names.
            max_stocks (int, optional): Maximum number of stocks to analyze. Defaults to 50.

        Returns:
            pd.DataFrame: DataFrame containing analysis results.
        """
        results = []

        logger.info(f"📈 Starting analysis of {len(stock_codes[:max_stocks])} stocks...")

        for i, (code, name) in enumerate(zip(stock_codes[:max_stocks], stock_names[:max_stocks])):
            try:
                logger.info(f"Analyzing: {name} ({code}) [{i+1}/{len(stock_codes[:max_stocks])}]")

                # Collect data
                stock_data = self.get_stock_data(code, name)
                if not stock_data:
                    continue

                # Calculate technical indicators
                technical_indicators = self.calculate_technical_indicators(stock_data['price_data'])
                if not technical_indicators:
                    continue

                # Calculate financial ratios
                financial_ratios = self.fundamental_collector.calculate_financial_ratios(stock_data['financial_data'])

                # Merge results
                result = {
                    'company_code': code,
                    'company_name': name,
                    'current_price': stock_data['price_data']['Close'].iloc[-1],
                    **technical_indicators,
                    **financial_ratios
                }

                results.append(result)

                # Prevent API rate limiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error analyzing stock ({name}): {e}")
                continue

        self.analyzed_stocks = pd.DataFrame(results)
        logger.info(f"✅ Completed analysis of {len(self.analyzed_stocks)} stocks")

        return self.analyzed_stocks

    def detect_anomalies(self, method: str = 'isolation_forest', contamination: float = 0.1) -> pd.DataFrame:
        """Detect anomalies in analyzed stocks.

        Args:
            method (str, optional): Anomaly detection method. Defaults to 'isolation_forest'.
            contamination (float, optional): Expected proportion of anomalies. Defaults to 0.1.

        Returns:
            pd.DataFrame: DataFrame containing detected anomalies.

        Raises:
            ValueError: If method is not 'isolation_forest' or 'lof'.
        """
        if self.analyzed_stocks.empty:
            logger.warning("⚠️ No analyzed stock data available.")
            return pd.DataFrame()

        # Select numeric columns for analysis
        numeric_columns = [
            'annualized_return', 'volatility_annual', 'sharpe_ratio', 'max_drawdown',
            'var_95', 'cvar_95', 'momentum_5d', 'momentum_20d', 'bb_position', 'rsi',
            'pe_ratio', 'pb_ratio', 'roe', 'debt_to_equity', 'current_ratio', 'quality_score'
        ]

        # Select available columns
        available_columns = [col for col in numeric_columns if col in self.analyzed_stocks.columns]
        feature_data = self.analyzed_stocks[available_columns].fillna(0)

        if feature_data.empty:
            logger.warning("⚠️ No numeric data available for analysis.")
            return pd.DataFrame()

        # Normalize data
        scaler = RobustScaler()
        scaled_features = scaler.fit_transform(feature_data)

        # Detect anomalies
        if method == 'isolation_forest':
            model = IsolationForest(contamination=contamination, random_state=42)
            outliers = model.fit_predict(scaled_features)
            scores = model.score_samples(scaled_features)
        elif method == 'lof':
            model = LocalOutlierFactor(contamination=contamination)
            outliers = model.fit_predict(scaled_features)
            scores = model.negative_outlier_factor_
        else:
            raise ValueError("method must be 'isolation_forest' or 'lof'.")

        # Add results
        self.analyzed_stocks['is_anomaly'] = outliers == -1
        self.analyzed_stocks['anomaly_score'] = scores

        # Filter anomalies
        self.anomalies = self.analyzed_stocks[self.analyzed_stocks['is_anomaly']].copy()

        logger.info(f"🔍 Detected {len(self.anomalies)} anomalies ({method}, contamination={contamination})")

        return self.anomalies


class ExternalStockAnalyzer:
    """External data source based Korean stock analysis system.

    This class provides methods for analyzing Korean stocks using external data sources,
    including comprehensive analysis and anomaly detection.
    """

    def __init__(self, config: Optional[AnalysisConfig] = None):
        """Initialize the ExternalStockAnalyzer.

        Args:
            config (Optional[AnalysisConfig], optional): Analysis configuration. Defaults to None.
        """
        self.config = config or AnalysisConfig()
        self.collector = ExternalStockListCollector()
        self.individual_analyzer = KoreanStockAnalyzer()
        self.anomaly_detector = AnomalyDetector(self.config.contamination)

        self.analyzed_stocks = pd.DataFrame()
        self.anomalies = pd.DataFrame()

    def collect_stock_list(self, source: Optional[str] = None, file_path: Optional[str] = None) -> List[StockInfo]:
        """Collect stock list from specified source.

        Args:
            source (Optional[str], optional): Data source. Defaults to None.
            file_path (Optional[str], optional): Path to CSV file. Defaults to None.

        Returns:
            List[StockInfo]: List of stock information.
        """
        if source == "pykrx":
            return self.collector.collect_from_pykrx()
        elif source == "fdr":
            return self.collector.collect_from_fdr()
        elif source == "krx_web":
            return self.collector.collect_from_krx_web()
        elif source == "csv_file" and file_path:
            return self.collector.collect_from_csv(file_path)
        else:
            return self.collector.auto_collect(preferred_source=source)

    def analyze_stock_batch(self, stock_batch: List[StockInfo]) -> List[Dict]:
        """Analyze a batch of stocks.

        Args:
            stock_batch (List[StockInfo]): Batch of stocks to analyze.

        Returns:
            List[Dict]: List of analysis results.
        """
        results = []

        for stock in stock_batch:
            try:
                # Collect data
                stock_data = self.individual_analyzer.get_stock_data(
                    stock.code, stock.name, period=self.config.analysis_period
                )

                if not stock_data:
                    continue

                # Calculate technical indicators
                technical_indicators = self.individual_analyzer.calculate_technical_indicators(
                    stock_data['price_data']
                )

                if not technical_indicators:
                    continue

                # Calculate financial ratios
                financial_ratios = self.individual_analyzer.fundamental_collector.calculate_financial_ratios(
                    stock_data['financial_data']
                )

                # Merge results
                result = {
                    'company_code': stock.code,
                    'company_name': stock.name,
                    'market': stock.market,
                    'sector': stock.sector,
                    'current_price': stock_data['price_data']['Close'].iloc[-1],
                    'data_points': len(stock_data['price_data']),
                    **technical_indicators,
                    **financial_ratios
                }

                results.append(result)

                # Prevent API rate limiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error analyzing stock ({stock.name}): {e}")
                continue

        return results

    def analyze_all_stocks(self, 
                          source: Optional[str] = None, 
                          file_path: Optional[str] = None,
                          max_stocks: Optional[int] = None) -> Dict:
        """Analyze all stocks from specified source.

        Args:
            source (Optional[str], optional): Data source. Defaults to None.
            file_path (Optional[str], optional): Path to CSV file. Defaults to None.
            max_stocks (Optional[int], optional): Maximum number of stocks to analyze. Defaults to None.

        Returns:
            Dict: Dictionary containing analysis results.
        """
        logger.info("🚀 Starting comprehensive stock analysis...")
        start_time = time.time()

        # 1. Collect stock list
        stock_list = self.collect_stock_list(source, file_path)
        if not stock_list:
            logger.error("❌ No stocks to analyze.")
            return {}

        # Limit number of stocks if specified
        if max_stocks:
            stock_list = stock_list[:max_stocks]

        logger.info(f"📊 Analyzing {len(stock_list)} stocks")

        # 2. Calculate batch size
        batch_size = max(1, len(stock_list) // self.config.max_workers)
        stock_batches = [stock_list[i:i + batch_size] for i in range(0, len(stock_list), batch_size)]

        # 3. Run parallel analysis
        all_results = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit batch analysis tasks
            future_to_batch = {
                executor.submit(self.analyze_stock_batch, batch): i 
                for i, batch in enumerate(stock_batches)
            }

            # Collect results
            completed = 0
            for future in as_completed(future_to_batch):
                batch_results = future.result()
                all_results.extend(batch_results)
                completed += 1

                logger.info(f"Progress: {completed}/{len(stock_batches)} batches completed "
                          f"({len(all_results)} stocks analyzed)")

        # 4. Organize results
        if not all_results:
            logger.error("❌ No analysis results.")
            return {}

        self.analyzed_stocks = pd.DataFrame(all_results)

        # 5. Detect anomalies
        logger.info("🔍 Detecting anomalies...")
        self.analyzed_stocks = self.anomaly_detector.detect_anomalies(
            self.analyzed_stocks, method='isolation_forest'
        )

        self.anomalies = self.analyzed_stocks[
            self.analyzed_stocks.get('is_anomaly', False)
        ].copy()

        # 6. Save results
        if self.config.save_results:
            self.save_results()

        # 7. Report completion
        elapsed_time = time.time() - start_time
        logger.info(f"\n✅ Analysis completed!")
        logger.info(f"⏱️ Time taken: {elapsed_time:.2f} seconds")
        logger.info(f"📊 Analyzed stocks: {len(self.analyzed_stocks)}")
        logger.info(f"🔍 Anomalies detected: {len(self.anomalies)}")

        return {
            'analyzed_stocks': self.analyzed_stocks,
            'anomalies': self.anomalies,
            'total_analyzed': len(self.analyzed_stocks),
            'anomaly_count': len(self.anomalies),
            'analysis_time': elapsed_time
        }

    def save_results(self) -> None:
        """Save analysis results to CSV files."""
        try:
            # Create timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create results directory if it doesn't exist
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)

            # Save analyzed stocks
            if not self.analyzed_stocks.empty:
                self.analyzed_stocks.to_csv(
                    results_dir / f"analyzed_stocks_{timestamp}.csv", 
                    index=False, 
                    encoding='utf-8-sig'
                )

            # Save anomalies
            if not self.anomalies.empty:
                self.anomalies.to_csv(
                    results_dir / f"anomalies_{timestamp}.csv", 
                    index=False, 
                    encoding='utf-8-sig'
                )

            # Save summary as JSON
            summary = {
                'timestamp': timestamp,
                'total_analyzed': len(self.analyzed_stocks),
                'anomaly_count': len(self.anomalies),
                'positive_return_count': int(self.analyzed_stocks['annualized_return'] > 0).sum(),
                'average_return': float(self.analyzed_stocks['annualized_return'].mean()),
                'average_volatility': float(self.analyzed_stocks['volatility_annual'].mean()),
                'average_sharpe': float(self.analyzed_stocks['sharpe_ratio'].mean()),
                'average_drawdown': float(self.analyzed_stocks['max_drawdown'].mean()),
                'config': {
                    'analysis_period': self.config.analysis_period,
                    'risk_free_rate': self.config.risk_free_rate,
                    'contamination': self.config.contamination
                }
            }

            with open(results_dir / f"analysis_summary_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=4)

            logger.info(f"📁 Results saved to 'results' directory with timestamp {timestamp}")

        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")

    def print_summary_report(self) -> None:
        """Print summary report of analysis results."""
        if self.analyzed_stocks.empty:
            logger.warning("⚠️ No analysis results available.")
            return

        logger.info("\n" + "="*80)
        logger.info("📊 Analysis Results Summary")
        logger.info("="*80)

        # Analysis status
        total_stocks = len(self.analyzed_stocks)
        anomaly_stocks = len(self.anomalies)
        positive_returns = (self.analyzed_stocks['annualized_return'] > 0).sum()

        logger.info(f"\nAnalysis Status:")
        logger.info(f"  Total analyzed stocks: {total_stocks}")
        logger.info(f"  Anomaly stocks: {anomaly_stocks} ({anomaly_stocks/total_stocks*100:.1f}%)")
        logger.info(f"  Positive return stocks: {positive_returns}/{total_stocks} ({positive_returns/total_stocks*100:.1f}%)")

        # Return statistics
        logger.info(f"\nReturn Statistics:")
        logger.info(f"  Average annual return: {self.analyzed_stocks['annualized_return'].mean():.2%}")
        logger.info(f"  Highest return: {self.analyzed_stocks['annualized_return'].max():.2%}")
        logger.info(f"  Lowest return: {self.analyzed_stocks['annualized_return'].min():.2%}")

        # Risk statistics
        logger.info(f"\nRisk Statistics:")
        logger.info(f"  Average annual volatility: {self.analyzed_stocks['volatility_annual'].mean():.2%}")
        logger.info(f"  Average Sharpe ratio: {self.analyzed_stocks['sharpe_ratio'].mean():.3f}")
        logger.info(f"  Average maximum drawdown: {self.analyzed_stocks['max_drawdown'].mean():.2%}")

        # Top performers
        if not self.analyzed_stocks.empty and 'sharpe_ratio' in self.analyzed_stocks.columns:
            logger.info(f"\nTop Performers (by Sharpe ratio):")
            top_sharpe = self.analyzed_stocks.nlargest(5, 'sharpe_ratio')
            for i, (_, row) in enumerate(top_sharpe.iterrows(), 1):
                logger.info(f"  {i}. {row['company_name']}")
                logger.info(f"     Return: {row['annualized_return']:.2%}, Sharpe: {row['sharpe_ratio']:.2f}")

        # Anomalies
        if not self.anomalies.empty:
            logger.info(f"\nNotable Anomalies:")
            extreme_anomalies = self.anomalies.nsmallest(3, 'anomaly_score')
            for i, (_, row) in enumerate(extreme_anomalies.iterrows(), 1):
                logger.info(f"  {i}. {row['company_name']}")
                logger.info(f"     Return: {row['annualized_return']:.2%}, Volatility: {row['volatility_annual']:.2%}")

        logger.info("="*80)
