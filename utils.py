import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

def fetch_stock_data(ticker, start_date, end_date):
    """
    Fetches stock data for the given ticker and date range
    
    Args:
        ticker (str): Stock ticker symbol
        start_date (datetime): Start date for data
        end_date (datetime): End date for data
        
    Returns:
        pandas.DataFrame: Stock data
    """
    try:
        df = yf.download(ticker, start=start_date, end=end_date)
        return df
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

def fetch_company_info(ticker):
    """
    Fetches company information for the given ticker
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        dict: Company information
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.info
    except Exception as e:
        print(f"Error fetching company info: {str(e)}")
        return None

def calculate_performance_metrics(df):
    """
    Calculates various performance metrics based on stock data
    
    Args:
        df (pandas.DataFrame): Stock price data with OHLC prices
        
    Returns:
        dict: Dictionary containing performance metrics
    """
    metrics = {}
    
    # Calculate daily returns
    df['daily_return'] = df['Close'].pct_change() * 100
    
    # Most recent daily return
    metrics['daily_returns'] = df['daily_return'].iloc[-1] if len(df) > 1 else 0
    
    # Monthly return (last 30 days)
    if len(df) >= 30:
        metrics['monthly_returns'] = ((df['Close'].iloc[-1] / df['Close'].iloc[-30]) - 1) * 100
    else:
        metrics['monthly_returns'] = ((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100
    
    # YTD return
    current_year = datetime.now().year
    start_of_year = datetime(current_year, 1, 1)
    ytd_data = df[df.index >= start_of_year]
    if not ytd_data.empty:
        metrics['ytd_returns'] = ((ytd_data['Close'].iloc[-1] / ytd_data['Close'].iloc[0]) - 1) * 100
    else:
        metrics['ytd_returns'] = 0
    
    # Annual return (past 365 days)
    if len(df) > 252:  # Approx trading days in a year
        metrics['annual_returns'] = ((df['Close'].iloc[-1] / df['Close'].iloc[-252]) - 1) * 100
    else:
        metrics['annual_returns'] = ((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100
    
    # Volatility (annualized standard deviation of returns)
    metrics['volatility'] = df['daily_return'].std() * np.sqrt(252)
    
    # Store daily returns for histogram
    metrics['returns'] = df['daily_return'].dropna().values
    
    # Sharpe ratio (assuming risk-free rate of 0% for simplicity)
    avg_daily_return = df['daily_return'].mean()
    daily_std = df['daily_return'].std()
    if daily_std > 0:
        metrics['sharpe_ratio'] = (avg_daily_return / daily_std) * np.sqrt(252)
    else:
        metrics['sharpe_ratio'] = 0
    
    return metrics
