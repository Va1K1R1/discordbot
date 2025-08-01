"""
Main module for the Korean Stock Analysis System.

This module provides integrated functionality for the Korean Stock Analysis System,
including comprehensive analysis and detailed reporting.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from typing import Dict, Optional, List, Union

from .config import logger, AnalysisConfig
from .stock_analysis import KoreanStockAnalyzer, ExternalStockAnalyzer
from .visualization import VisualizationEngine
from .risk_management import AdvancedRiskManager


def run_comprehensive_analysis() -> Optional[Dict]:
    """Run comprehensive analysis of Korean stocks.

    This function initializes system components, analyzes a list of major Korean stocks,
    detects anomalies, and outputs a summary of the results.

    Returns:
        Optional[Dict]: Dictionary containing analysis results, or None if analysis fails.
    """
    try:
        logger.info("🚀 Starting integrated Korean stock analysis system")

        # 1. Initialize system components
        analyzer = KoreanStockAnalyzer()
        viz_engine = VisualizationEngine()
        risk_manager = AdvancedRiskManager()

        # 2. List of major Korean stocks to analyze
        stock_codes = [
            '005930',  # Samsung Electronics
            '000660',  # SK Hynix
            '035420',  # NAVER
            '051910',  # LG Chem
            '207940',  # Samsung Biologics
            '035720',  # Kakao
            '323410',  # Kakao Bank
            '066570',  # LG Electronics
            '096770',  # SK Innovation
            '003550',  # LG
            '018260',  # Samsung SDS
            '028050',  # Samsung Engineering
            '009150',  # Samsung Electro-Mechanics
            '017670',  # SK Telecom
            '259960'   # Krafton
        ]

        stock_names = [
            'Samsung Electronics', 'SK Hynix', 'NAVER', 'LG Chem', 'Samsung Biologics',
            'Kakao', 'Kakao Bank', 'LG Electronics', 'SK Innovation', 'LG',
            'Samsung SDS', 'Samsung Engineering', 'Samsung Electro-Mechanics', 'SK Telecom', 'Krafton'
        ]

        # 3. Run multiple stock analysis
        analyzed_data = analyzer.analyze_multiple_stocks(stock_codes, stock_names, max_stocks=15)

        if analyzed_data.empty:
            logger.error("❌ No data to analyze.")
            return None

        # 4. Detect anomalies
        anomalies = analyzer.detect_anomalies(method='isolation_forest', contamination=0.2)

        # 5. Output summary of results
        logger.info("\n" + "="*80)
        logger.info("📊 Analysis Results Summary")
        logger.info("="*80)

        logger.info(f"✅ Total stocks analyzed: {len(analyzed_data)}")
        logger.info(f"🔍 Anomalies detected: {len(anomalies)}")

        if not analyzed_data.empty:
            logger.info(f"\n📈 Return Statistics:")
            logger.info(f"   Highest return: {analyzed_data['annualized_return'].max():.2%}")
            logger.info(f"   Lowest return: {analyzed_data['annualized_return'].min():.2%}")
            logger.info(f"   Average return: {analyzed_data['annualized_return'].mean():.2%}")

            logger.info(f"\n📊 Risk Statistics:")
            logger.info(f"   Average volatility: {analyzed_data['volatility_annual'].mean():.2%}")
            logger.info(f"   Average Sharpe ratio: {analyzed_data['sharpe_ratio'].mean():.3f}")
            logger.info(f"   Average maximum drawdown: {analyzed_data['max_drawdown'].mean():.2%}")

        # 6. Detailed information on anomalies
        if not anomalies.empty:
            logger.info(f"\n🔍 Detailed Anomaly Information:")
            logger.info("-" * 80)
            display_columns = ['company_name', 'annualized_return', 'volatility_annual', 
                             'sharpe_ratio', 'max_drawdown', 'quality_score']
            available_columns = [col for col in display_columns if col in anomalies.columns]

            for _, row in anomalies[available_columns].iterrows():
                logger.info(f"📍 {row['company_name']}")
                if 'annualized_return' in row:
                    logger.info(f"   Annual return: {row['annualized_return']:.2%}")
                if 'volatility_annual' in row:
                    logger.info(f"   Annual volatility: {row['volatility_annual']:.2%}")
                if 'sharpe_ratio' in row:
                    logger.info(f"   Sharpe ratio: {row['sharpe_ratio']:.3f}")
                if 'max_drawdown' in row:
                    logger.info(f"   Maximum drawdown: {row['max_drawdown']:.2%}")
                if 'quality_score' in row:
                    logger.info(f"   Quality score: {row['quality_score']:.0f}/100")
                logger.info("")

        logger.info("✅ Comprehensive analysis complete!")

        return {
            'analyzed_data': analyzed_data,
            'anomalies': anomalies,
            'analyzer': analyzer
        }

    except Exception as e:
        logger.error(f"Error running comprehensive analysis: {e}")
        return None


def create_detailed_report(results: Dict) -> None:
    """Create a detailed analysis report.

    Args:
        results (Dict): Dictionary containing analysis results.
    """
    if not results:
        logger.error("❌ No data available for report generation.")
        return

    analyzed_data = results['analyzed_data']
    anomalies = results['anomalies']

    logger.info("\n" + "="*100)
    logger.info("📋 Detailed Analysis Report")
    logger.info("="*100)

    # Overall market overview
    logger.info("\n🌍 Market Overview")
    logger.info("-" * 50)
    if not analyzed_data.empty:
        positive_returns = analyzed_data[analyzed_data['annualized_return'] > 0]
        logger.info(f"Stocks with positive returns: {len(positive_returns)}/{len(analyzed_data)} ({len(positive_returns)/len(analyzed_data)*100:.1f}%)")

        high_quality = analyzed_data[analyzed_data.get('quality_score', 0) >= 60]
        logger.info(f"High-quality stocks (60+ score): {len(high_quality)}/{len(analyzed_data)} ({len(high_quality)/len(analyzed_data)*100:.1f}%)")

    # Investment recommendations
    logger.info("\n⭐ Investment Recommendations (by Sharpe ratio)")
    logger.info("-" * 50)
    if not analyzed_data.empty and 'sharpe_ratio' in analyzed_data.columns:
        top_sharpe = analyzed_data.nlargest(5, 'sharpe_ratio')
        for i, (_, row) in enumerate(top_sharpe.iterrows(), 1):
            logger.info(f"{i}. {row['company_name']}")
            logger.info(f"   Sharpe ratio: {row['sharpe_ratio']:.3f}")
            logger.info(f"   Annual return: {row['annualized_return']:.2%}")
            logger.info(f"   Annual volatility: {row['volatility_annual']:.2%}")
            logger.info("")


def save_results_to_csv(results: Dict, base_filename: str = "korean_stocks") -> None:
    """Save analysis results to CSV files.

    Args:
        results (Dict): Dictionary containing analysis results.
        base_filename (str, optional): Base filename for CSV files. Defaults to "korean_stocks".
    """
    if not results:
        logger.error("❌ No data available to save.")
        return

    try:
        # Save analyzed data
        results['analyzed_data'].to_csv(f'{base_filename}_analysis_results.csv', index=False, encoding='utf-8-sig')

        # Save anomalies
        results['anomalies'].to_csv(f'{base_filename}_anomalies.csv', index=False, encoding='utf-8-sig')

        logger.info(f"📁 Analysis results saved to CSV files: {base_filename}_*.csv")
    except Exception as e:
        logger.error(f"Error saving results to CSV: {e}")


def run_external_data_analysis(
    source: Optional[str] = None,
    file_path: Optional[str] = None,
    max_stocks: Optional[int] = None
) -> Optional[Dict]:
    """Run comprehensive analysis of Korean stocks using external data sources.

    This function initializes the ExternalStockAnalyzer, collects stock lists from
    external sources, analyzes the stocks, detects anomalies, and outputs a summary
    of the results.

    Args:
        source (Optional[str], optional): Data source. Defaults to None (auto-select).
        file_path (Optional[str], optional): Path to CSV file. Defaults to None.
        max_stocks (Optional[int], optional): Maximum number of stocks to analyze. Defaults to None.

    Returns:
        Optional[Dict]: Dictionary containing analysis results, or None if analysis fails.
    """
    try:
        logger.info("🚀 Starting external data source based Korean stock analysis system")

        # 1. Configure analysis parameters
        config = AnalysisConfig(
            analysis_period="1y",
            risk_free_rate=0.03,
            max_workers=8,
            contamination=0.1,
            save_results=True
        )

        # 2. Initialize the external stock analyzer
        analyzer = ExternalStockAnalyzer(config)

        # 3. Run the analysis
        results = analyzer.analyze_all_stocks(
            source=source,
            file_path=file_path,
            max_stocks=max_stocks
        )

        if not results:
            logger.error("❌ Analysis failed.")
            return None

        # 4. Print summary report
        analyzer.print_summary_report()

        return results

    except Exception as e:
        logger.error(f"Error running external data analysis: {e}")
        return None


if __name__ == "__main__":
    # Choose which analysis to run
    analysis_type = os.environ.get("ANALYSIS_TYPE", "external")

    if analysis_type.lower() == "external":
        # Run the external data source based analysis
        results = run_external_data_analysis(
            source=None,  # Auto-select best available source
            max_stocks=15  # Limit to 15 stocks for demonstration
        )
    else:
        # Run the traditional analysis
        results = run_comprehensive_analysis()

    if results:
        # Create detailed report (for traditional analysis)
        if analysis_type.lower() != "external":
            create_detailed_report(results)
            save_results_to_csv(results)

        logger.info("✅ Analysis completed successfully!")
