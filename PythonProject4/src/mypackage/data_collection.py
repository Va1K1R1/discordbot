"""
Data collection module for the Korean Stock Analysis System.

This module contains classes for collecting stock data, fundamental data,
and macroeconomic indicators.
"""

import os
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import requests
import time
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import logger, StockInfo, DataSource

# Optional imports for external data sources
try:
    from pykrx import stock as pykrx_stock
    HAS_PYKRX = True
    logger.info("✅ pykrx available")
except ImportError:
    HAS_PYKRX = False
    logger.warning("⚠️ pykrx not available")

try:
    import FinanceDataReader as fdr
    HAS_FDR = True
    logger.info("✅ FinanceDataReader available")  
except ImportError:
    HAS_FDR = False
    logger.warning("⚠️ FinanceDataReader not available")

class EnhancedDataCollector:
    """Enhanced data collector for Korean stocks.

    This class provides methods for collecting stock data with volume profile
    and macroeconomic indicators.
    """

    def __init__(self):
        """Initialize the EnhancedDataCollector."""
        self.market_regime_indicators = {}

    def get_samsung_data_with_volume_profile(self, symbol="005930.KS"):
        """Get Samsung Electronics data with volume profile.

        Args:
            symbol (str): Stock symbol. Defaults to "005930.KS" (Samsung Electronics).

        Returns:
            pd.DataFrame: DataFrame containing stock data with volume profile.

        Raises:
            ValueError: If data collection fails.
        """
        logger.info("📊 Collecting enhanced Samsung Electronics data...")

        ticker = yf.Ticker(symbol)
        data = ticker.history(period="max")

        if data.empty:
            raise ValueError("Data collection failed")

        # Normalize index
        data.index = pd.to_datetime(data.index.date)

        # Enhanced volume analysis
        data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()
        data['Volume_Price_Trend'] = data['Close'] * data['Volume']
        data['Price_Volume_Ratio'] = data['Close'] / (data['Volume'] + 1)

        # Gap analysis
        data['Gap'] = (data['Open'] - data['Close'].shift(1)) / data['Close'].shift(1)
        data['Gap_Fill_Ratio'] = np.where(
            data['Gap'] > 0,
            (data['Close'] - data['Open']) / (data['High'] - data['Open'] + 0.001),
            (data['Close'] - data['Open']) / (data['Open'] - data['Low'] + 0.001)
        )

        # Candlestick patterns
        data['Body_Size'] = abs(data['Close'] - data['Open']) / data['Open']
        data['Upper_Shadow'] = (data['High'] - np.maximum(data['Open'], data['Close'])) / data['Open']
        data['Lower_Shadow'] = (np.minimum(data['Open'], data['Close']) - data['Low']) / data['Open']
        data['Doji'] = (abs(data['Close'] - data['Open']) / (data['High'] - data['Low'] + 0.001) < 0.1).astype(int)

        logger.info(f"✅ Enhanced Samsung Electronics data: {len(data)} days")
        return data.fillna(method='ffill').fillna(0)

    def get_macro_economic_indicators(self, start_date, end_date):
        """Collect macroeconomic indicators.

        Args:
            start_date: Start date for data collection.
            end_date: End date for data collection.

        Returns:
            dict: Dictionary containing macroeconomic indicators.
        """
        logger.info("📈 Collecting macroeconomic indicators...")

        macro_data = {}

        # Important macroeconomic indicators
        indicators = {
            'USD_KRW': 'KRW=X',           # USD-KRW exchange rate
            'US_10Y': '^TNX',             # US 10-year Treasury
            'VIX': '^VIX',                # Fear index
            'DXY': 'DX-Y.NYB',            # Dollar index
            'GOLD': 'GC=F',               # Gold
            'OIL': 'CL=F',                # Oil
            'KOSPI': '^KS11',             # KOSPI
            'NASDAQ': '^IXIC',            # NASDAQ
            'SP500': '^GSPC',             # S&P500
            'NIKKEI': '^N225',            # Nikkei
            'COPPER': 'HG=F',             # Copper (leading indicator)
            'SEMICONDUCTOR_ETF': 'SMH'     # Semiconductor ETF
        }

        for name, symbol in indicators.items():
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(start=start_date, end=end_date)

                if not data.empty:
                    data.index = pd.to_datetime(data.index.date)
                    macro_data[name] = data['Close']

            except Exception as e:
                logger.warning(f"⚠️ Failed to collect {name}: {e}")

        logger.info(f"✅ Macroeconomic indicators: {len(macro_data)} items")
        return macro_data


class ExternalStockListCollector:
    """External source stock list collector.

    This class provides methods for collecting stock lists from various external sources
    such as pykrx, FinanceDataReader, KRX web, etc.
    """

    def __init__(self):
        """Initialize the ExternalStockListCollector."""
        self.stock_list = []
        self.available_sources = self._check_available_sources()

    def _check_available_sources(self) -> List[str]:
        """Check available data sources.

        Returns:
            List[str]: List of available data sources.
        """
        sources = []
        if HAS_PYKRX:
            sources.append("pykrx")
        if HAS_FDR:
            sources.append("financedatareader")
        sources.extend(["krx_web", "yfinance", "csv_file"])
        return sources

    def collect_from_pykrx(self) -> List[StockInfo]:
        """Collect stock list from pykrx.

        Returns:
            List[StockInfo]: List of stock information.
        """
        if not HAS_PYKRX:
            logger.warning("⚠️ pykrx not available")
            return []

        try:
            stocks = []

            # KOSPI stocks
            kospi_codes = pykrx_stock.get_market_ticker_list(market="KOSPI")
            for code in kospi_codes:
                name = pykrx_stock.get_market_ticker_name(code)
                stocks.append(StockInfo(code=code, name=name, market="KOSPI"))

            # KOSDAQ stocks  
            kosdaq_codes = pykrx_stock.get_market_ticker_list(market="KOSDAQ")
            for code in kosdaq_codes:
                name = pykrx_stock.get_market_ticker_name(code)
                stocks.append(StockInfo(code=code, name=name, market="KOSDAQ"))

            logger.info(f"✅ Collected {len(stocks)} stocks from pykrx")
            return stocks

        except Exception as e:
            logger.error(f"❌ pykrx collection failed: {e}")
            return []

    def collect_from_fdr(self) -> List[StockInfo]:
        """Collect stock list from FinanceDataReader.

        Returns:
            List[StockInfo]: List of stock information.
        """
        if not HAS_FDR:
            logger.warning("⚠️ FinanceDataReader not available")
            return []

        try:
            df_krx = fdr.StockListing('KRX')

            stocks = []
            for _, row in df_krx.iterrows():
                stocks.append(StockInfo(
                    code=row.get('Symbol', ''),
                    name=row.get('Name', ''),
                    market=row.get('Market', ''),
                    sector=row.get('Sector', '')
                ))

            logger.info(f"✅ Collected {len(stocks)} stocks from FinanceDataReader")
            return stocks

        except Exception as e:
            logger.error(f"❌ FinanceDataReader collection failed: {e}")
            return []

    def collect_from_krx_web(self) -> List[StockInfo]:
        """Collect stock list from KRX website.

        Returns:
            List[StockInfo]: List of stock information.
        """
        try:
            # KRX listed companies URL
            url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'

            # Read table data from web
            df_list = pd.read_html(url, header=0)
            df = df_list[0]

            stocks = []
            for _, row in df.iterrows():
                code = f"{row['종목코드']:06d}"  # Format to 6 digits
                stocks.append(StockInfo(
                    code=code,
                    name=row.get('회사명', ''),
                    sector=row.get('업종', ''),
                    listing_date=str(row.get('상장일', ''))
                ))

            logger.info(f"✅ Collected {len(stocks)} stocks from KRX website")
            return stocks

        except Exception as e:
            logger.error(f"❌ KRX web crawling failed: {e}")
            return []

    def collect_from_csv(self, file_path: str) -> List[StockInfo]:
        """Collect stock list from CSV file.

        Args:
            file_path (str): Path to CSV file.

        Returns:
            List[StockInfo]: List of stock information.
        """
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')

            stocks = []
            for _, row in df.iterrows():
                stocks.append(StockInfo(
                    code=str(row.get('code', row.get('종목코드', ''))),
                    name=str(row.get('name', row.get('종목명', ''))),
                    market=str(row.get('market', row.get('시장', ''))),
                    sector=str(row.get('sector', row.get('업종', '')))
                ))

            logger.info(f"✅ Collected {len(stocks)} stocks from CSV")
            return stocks

        except Exception as e:
            logger.error(f"❌ CSV collection failed: {e}")
            return []

    def collect_sample_stocks(self) -> List[StockInfo]:
        """Collect sample stock list.

        Returns:
            List[StockInfo]: List of sample stock information.
        """
        # Sample major Korean stocks
        sample_stocks = [
            StockInfo(code='005930', name='Samsung Electronics', market='KOSPI'),
            StockInfo(code='000660', name='SK Hynix', market='KOSPI'),
            StockInfo(code='035420', name='NAVER', market='KOSPI'),
            StockInfo(code='051910', name='LG Chem', market='KOSPI'),
            StockInfo(code='207940', name='Samsung Biologics', market='KOSPI'),
            StockInfo(code='035720', name='Kakao', market='KOSPI'),
            StockInfo(code='323410', name='Kakao Bank', market='KOSPI'),
            StockInfo(code='066570', name='LG Electronics', market='KOSPI'),
            StockInfo(code='096770', name='SK Innovation', market='KOSPI'),
            StockInfo(code='003550', name='LG', market='KOSPI')
        ]

        logger.info(f"✅ Using {len(sample_stocks)} sample stocks")
        return sample_stocks

    def auto_collect(self, preferred_source: Optional[str] = None) -> List[StockInfo]:
        """Automatically collect stock list from the best available source.

        Args:
            preferred_source (Optional[str]): Preferred data source.

        Returns:
            List[StockInfo]: List of stock information.
        """
        # Auto order: FDR > pykrx > KRX Web > Sample
        sources_to_try = [
            ("fdr", self.collect_from_fdr),
            ("pykrx", self.collect_from_pykrx), 
            ("krx_web", self.collect_from_krx_web)
        ]

        # Try preferred source first if specified
        if preferred_source:
            if preferred_source == "fdr" and not HAS_FDR:
                logger.warning("⚠️ Preferred source 'fdr' not available")
            elif preferred_source == "pykrx" and not HAS_PYKRX:
                logger.warning("⚠️ Preferred source 'pykrx' not available")
            else:
                for source_name, collect_func in sources_to_try:
                    if source_name == preferred_source:
                        stocks = collect_func()
                        if stocks:
                            return stocks

        # Try all sources in order
        for source_name, collect_func in sources_to_try:
            if source_name == "fdr" and not HAS_FDR:
                continue
            if source_name == "pykrx" and not HAS_PYKRX:
                continue

            stocks = collect_func()
            if stocks:
                logger.info(f"✅ Successfully collected from {source_name}")
                return stocks

        # All sources failed, use sample data
        return self.collect_sample_stocks()


class FundamentalDataCollector:
    """Fundamental data collector for Korean and international stocks.

    This class provides methods for collecting financial data and calculating
    financial ratios.
    """

    def __init__(self):
        """Initialize the FundamentalDataCollector."""
        self.fmp_key = os.getenv("FMP_API_KEY")

    def get_financial_data_from_yfinance(self, ticker: str) -> dict:
        """Collect basic financial information from yfinance.

        Args:
            ticker (str): Stock ticker symbol.

        Returns:
            dict: Dictionary containing financial data.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Extract basic financial information
            financial_data = {
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'roe': info.get('returnOnEquity', 0),
                'revenue': info.get('totalRevenue', 0),
                'gross_margin': info.get('grossMargins', 0),
                'operating_margin': info.get('operatingMargins', 0),
                'profit_margin': info.get('profitMargins', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 1.0),
                'book_value': info.get('bookValue', 0),
                'price_to_sales': info.get('priceToSalesTrailing12Months', 0),
                'enterprise_value': info.get('enterpriseValue', 0),
                'ev_to_revenue': info.get('enterpriseToRevenue', 0),
                'ev_to_ebitda': info.get('enterpriseToEbitda', 0)
            }

            return financial_data
        except Exception as e:
            logger.error(f"Error collecting financial data ({ticker}): {e}")
            return {}

    def calculate_financial_ratios(self, financial_data: dict) -> dict:
        """Calculate financial ratios.

        Args:
            financial_data (dict): Dictionary containing financial data.

        Returns:
            dict: Dictionary containing financial ratios.
        """
        ratios = {}

        try:
            # Basic ratios are already collected
            ratios.update(financial_data)

            # Calculate Quality Score (0-100)
            quality_score = 0
            if financial_data.get('roe', 0) > 0.15:  # ROE > 15%
                quality_score += 20
            if financial_data.get('debt_to_equity', 100) < 50:  # Debt ratio < 50%
                quality_score += 20
            if financial_data.get('current_ratio', 0) > 1.5:  # Current ratio > 1.5
                quality_score += 20
            if financial_data.get('operating_margin', 0) > 0.1:  # Operating margin > 10%
                quality_score += 20
            if financial_data.get('pe_ratio', 100) < 20 and financial_data.get('pe_ratio', 0) > 0:  # Appropriate PER
                quality_score += 20

            ratios['quality_score'] = quality_score

        except Exception as e:
            logger.error(f"Error calculating financial ratios: {e}")

        return ratios
