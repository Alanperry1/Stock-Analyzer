import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import os
from utils import calculate_performance_metrics, fetch_stock_data, fetch_company_info
import database as db

# Set page config
st.set_page_config(
    page_title="Stock Market Analyzer",
    page_icon="📈",
    layout="wide"
)

# Function to apply theme based on user preferences
def apply_theme(theme="light"):
    if theme == "dark":
        # Dark theme CSS
        st.markdown("""
        <style>
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stTabs [data-baseweb="tab-list"] {
            background-color: #262730;
        }
        .stTabs [data-baseweb="tab"] {
            color: #fafafa;
        }
        .stDataFrame {
            background-color: #262730;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light theme (default) - No custom CSS needed
        pass

# Define popular stock tickers for the dropdown
popular_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'DIS', 'NFLX', 'INTC', 'AMD', 'BA', 'KO', 'PEP']

# Default user ID (in a real app, this would come from authentication)
USER_ID = 'default_user'

# Initialize database and session
if 'db_initialized' not in st.session_state:
    try:
        db_init_success = db.init_db()
        st.session_state.db_initialized = True
        st.session_state.db_connected = db_init_success
    except Exception as e:
        st.session_state.db_initialized = True
        st.session_state.db_connected = False
        print(f"Database initialization error: {str(e)}")

# Set default watchlist
default_watchlist = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']

# Get user preferences from database
if 'user_preferences' not in st.session_state:
    try:
        st.session_state.user_preferences = db.get_user_preferences(USER_ID)
    except Exception as e:
        st.session_state.user_preferences = {
            'default_ticker': 'AAPL',
            'default_period': '1 Year',
            'theme': 'light',
            'show_ma50': 1,
            'show_ma200': 1
        }
        st.warning("Using default preferences - database connection unavailable.")

# Get watchlist from database
if 'watchlist' not in st.session_state:
    try:
        watchlist_from_db = db.get_watchlist(USER_ID)
        if watchlist_from_db:
            st.session_state.watchlist = watchlist_from_db
        else:
            # Default watchlist if none in database
            st.session_state.watchlist = default_watchlist
            # Try to add default watchlist to database
            for ticker in st.session_state.watchlist:
                db.add_to_watchlist(ticker, USER_ID)
    except Exception as e:
        # If database error, use default watchlist
        st.session_state.watchlist = default_watchlist
        print(f"Error getting watchlist: {str(e)}")

# Initialize selected ticker based on user preferences or default
if 'selected_ticker' not in st.session_state:
    if st.session_state.user_preferences and st.session_state.user_preferences.get('default_ticker'):
        st.session_state.selected_ticker = st.session_state.user_preferences.get('default_ticker')
    else:
        st.session_state.selected_ticker = 'AAPL'

# Apply theme based on user preferences
if st.session_state.user_preferences:
    theme = st.session_state.user_preferences.get('theme', 'light')
    apply_theme(theme)

# App title
st.title("Stock Market Analysis Tool")
st.write("Analyze stocks with interactive charts and technical indicators")

# Sidebar for inputs
with st.sidebar:
    st.header("Settings")
    
    # Stock ticker selection with dropdown and text input
    st.subheader("Select Stock")
    selection_method = st.radio("Selection Method", ["Choose from list", "Enter manually"])
    
    if selection_method == "Choose from list":
        ticker_input = st.selectbox("Select Stock Ticker", 
                                  options=sorted(list(set(popular_tickers + st.session_state.watchlist))),
                                  index=0).upper()
    else:
        ticker_input = st.text_input("Enter Stock Ticker", "AAPL").upper()
    
    # Date range selection
    st.subheader("Select Date Range")
    today = datetime.now()
    
    # Predefined periods
    period_options = {
        "1 Month": 30,
        "3 Months": 90,
        "6 Months": 180,
        "1 Year": 365,
        "2 Years": 730,
        "5 Years": 1825
    }
    
    selected_period = st.selectbox("Choose Period", list(period_options.keys()), index=3)
    days_to_subtract = period_options[selected_period]
    
    start_date = st.date_input(
        "Start Date",
        today - timedelta(days=days_to_subtract)
    )
    end_date = st.date_input("End Date", today)
    
    # Recent searches section - only show if database is connected
    if st.session_state.get('db_connected', False):
        st.subheader("Recent Searches")
        try:
            recent_searches = db.get_recent_searches(USER_ID)
            
            if recent_searches:
                st.write("Click on a ticker to view it:")
                recent_cols = st.columns(3)
                
                # Show only unique tickers from recent searches
                seen = set()
                unique_searches = []
                for ticker, _ in recent_searches:
                    if ticker not in seen and ticker != st.session_state.selected_ticker:
                        seen.add(ticker)
                        unique_searches.append(ticker)
                        
                for i, ticker in enumerate(unique_searches[:6]):  # Limit to 6 recent searches
                    col_idx = i % 3
                    with recent_cols[col_idx]:
                        if st.button(f"{ticker}", key=f"recent_{ticker}"):
                            st.session_state.selected_ticker = ticker
                            # Add to search history
                            try:
                                db.add_to_search_history(ticker, USER_ID)
                            except:
                                pass  # Ignore errors
                            st.rerun()
            else:
                st.write("Your recent searches will appear here.")
        except Exception as e:
            st.write("Recent search history not available.")
            print(f"Error retrieving search history: {str(e)}")
    
    # Technical indicator selection
    st.subheader("Technical Indicators")
    show_ma50 = st.checkbox("50-Day Moving Average", value=True)
    show_ma200 = st.checkbox("200-Day Moving Average", value=True)
    
    # Watchlist section
    st.subheader("Watchlist")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_ticker = st.text_input("Add stock to watchlist").upper()
    with col2:
        if st.button("Add", use_container_width=True):
            if new_ticker and new_ticker not in st.session_state.watchlist:
                # Verify if ticker exists
                try:
                    ticker_obj = yf.Ticker(new_ticker)
                    # Quick check if ticker is valid by getting recent data
                    recent_data = ticker_obj.history(period="1d")
                    if not recent_data.empty:
                        # Try to add to database if connected
                        added_to_db = False
                        if st.session_state.get('db_connected', False):
                            try:
                                added_to_db = db.add_to_watchlist(new_ticker, USER_ID)
                            except Exception as e:
                                print(f"Error adding to watchlist in DB: {str(e)}")
                        
                        # Whether DB operation succeeded or not, update local state
                        if added_to_db or new_ticker not in st.session_state.watchlist:
                            st.session_state.watchlist.append(new_ticker)
                            st.success(f"Added {new_ticker} to watchlist")
                            st.rerun()
                        else:
                            st.info(f"{new_ticker} is already in your watchlist")
                    else:
                        st.error(f"Invalid ticker: {new_ticker}")
                except Exception as e:
                    st.error(f"Error adding ticker: {str(e)}")
    
    # Display watchlist as a simple list in the sidebar
    if st.session_state.watchlist:
        st.write("**Your Watchlist:**")
        for i, ticker in enumerate(st.session_state.watchlist):
            col1, col2 = st.columns([4, 1])
            with col1:
                # If clicked, set as current ticker
                if st.button(f"{ticker}", key=f"select_{ticker}", use_container_width=True):
                    # Set the ticker via session state
                    st.session_state.selected_ticker = ticker
                    # Add to search history
                    db.add_to_search_history(ticker, USER_ID)
                    st.rerun()
            with col2:
                if st.button("×", key=f"remove_{i}"):
                    # Remove from database
                    if db.remove_from_watchlist(ticker, USER_ID):
                        st.session_state.watchlist.remove(ticker)
                        st.rerun()

# Settings tab for theme and preferences
with st.sidebar.expander("⚙️ Settings & Preferences"):
    # Theme selection
    theme = st.radio("Theme", ["Light", "Dark"], index=0 if st.session_state.user_preferences.get('theme', 'light') == 'light' else 1)
    
    # Default ticker
    default_ticker = st.text_input("Default Ticker", value=st.session_state.user_preferences.get('default_ticker', 'AAPL')).upper()
    
    # Default time period
    default_period = st.selectbox(
        "Default Time Period", 
        list(period_options.keys()),
        index=list(period_options.keys()).index(st.session_state.user_preferences.get('default_period', '1 Year'))
    )
    
    # Save button
    if st.button("Save Preferences"):
        new_prefs = {
            'theme': theme.lower(),
            'default_ticker': default_ticker,
            'default_period': default_period,
            'show_ma50': 1 if show_ma50 else 0,
            'show_ma200': 1 if show_ma200 else 0
        }
        
        # Try to save to database if connected
        if st.session_state.get('db_connected', False):
            try:
                db.update_user_preferences(new_prefs, USER_ID)
                st.session_state.user_preferences = new_prefs
                st.success("Preferences saved!")
            except Exception as e:
                st.error("Could not save preferences to database.")
                print(f"Error saving preferences: {str(e)}")
        else:
            # Just update session state
            st.session_state.user_preferences = new_prefs
            st.success("Preferences saved to session!")

# Main content area
try:
    # Update selected ticker if needed
    if 'selection_method' in locals() and selection_method == "Choose from list":
        if ticker_input != st.session_state.selected_ticker:
            st.session_state.selected_ticker = ticker_input
            # Add to search history
            if st.session_state.get('db_connected', False):
                try:
                    db.add_to_search_history(ticker_input, USER_ID)
                except:
                    pass  # Ignore errors
    elif 'ticker_input' in locals():
        if ticker_input != st.session_state.selected_ticker:
            st.session_state.selected_ticker = ticker_input
            # Add to search history
            if st.session_state.get('db_connected', False):
                try:
                    db.add_to_search_history(ticker_input, USER_ID)
                except:
                    pass  # Ignore errors
    
    # Fetch stock data using the selected ticker
    current_ticker = st.session_state.selected_ticker
    df = fetch_stock_data(current_ticker, start_date, end_date)
    
    if df.empty:
        st.error(f"No data found for {current_ticker}. Please check the ticker symbol.")
    else:
        # Create tabs for different sections
        tab1, tab2, tab3 = st.tabs(["Price Chart", "Company Overview", "Performance Metrics"])
        
        with tab1:
            st.subheader(f"{current_ticker} Stock Price")
            
            # Create figure with secondary y-axis
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Add candlestick trace
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name="Price"
                )
            )
            
            # Add volume trace on secondary y-axis
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['Volume'],
                    name="Volume",
                    marker_color='rgba(128, 128, 128, 0.5)'
                ),
                secondary_y=True
            )
            
            # Add moving averages if selected
            if show_ma50:
                df['MA50'] = df['Close'].rolling(window=50).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df['MA50'],
                        name="50-Day MA",
                        line=dict(color='rgba(255, 165, 0, 0.8)', width=2)
                    )
                )
                
            if show_ma200:
                df['MA200'] = df['Close'].rolling(window=200).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df['MA200'],
                        name="200-Day MA",
                        line=dict(color='rgba(0, 0, 255, 0.8)', width=2)
                    )
                )
                
            # Set figure layout
            fig.update_layout(
                title=f"{current_ticker} Stock Price and Volume",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                yaxis2_title="Volume",
                xaxis_rangeslider_visible=False,
                height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            # Update y-axis
            fig.update_yaxes(title_text="Price ($)", secondary_y=False)
            fig.update_yaxes(title_text="Volume", secondary_y=True)
            
            # Plot the figure
            st.plotly_chart(fig, use_container_width=True)
            
            # Display data table with the most recent data
            st.subheader("Recent Price Data")
            st.dataframe(df.tail(10).reset_index())
        
        with tab2:
            st.subheader(f"{current_ticker} Company Overview")
            
            try:
                # Fetch company info
                info = fetch_company_info(current_ticker)
                
                if info:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Company Name:** {info.get('longName', 'N/A')}")
                        st.write(f"**Sector:** {info.get('sector', 'N/A')}")
                        st.write(f"**Industry:** {info.get('industry', 'N/A')}")
                        st.write(f"**Country:** {info.get('country', 'N/A')}")
                        st.write(f"**Exchange:** {info.get('exchange', 'N/A')}")
                    
                    with col2:
                        st.write(f"**Market Cap:** ${info.get('marketCap', 0):,.2f}")
                        st.write(f"**P/E Ratio:** {info.get('trailingPE', 'N/A')}")
                        st.write(f"**Dividend Yield:** {info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "Dividend Yield: N/A")
                        st.write(f"**52-Week High:** ${info.get('fiftyTwoWeekHigh', 0):.2f}")
                        st.write(f"**52-Week Low:** ${info.get('fiftyTwoWeekLow', 0):.2f}")
                    
                    st.subheader("Business Summary")
                    st.write(info.get('longBusinessSummary', 'No business summary available.'))
                else:
                    st.warning(f"Unable to fetch company information for {current_ticker}")
            except Exception as e:
                st.error(f"Error fetching company information: {str(e)}")
        
        with tab3:
            st.subheader(f"{current_ticker} Performance Metrics")
            
            try:
                # Calculate performance metrics
                metrics = calculate_performance_metrics(df)
                
                # Display metrics in columns
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="Daily Returns",
                        value=f"{metrics['daily_returns']:.2f}%",
                        delta=f"{metrics['daily_returns']:.2f}%"
                    )
                    st.metric(
                        label="Monthly Returns",
                        value=f"{metrics['monthly_returns']:.2f}%",
                        delta=f"{metrics['monthly_returns']:.2f}%"
                    )
                
                with col2:
                    st.metric(
                        label="YTD Returns",
                        value=f"{metrics['ytd_returns']:.2f}%",
                        delta=f"{metrics['ytd_returns']:.2f}%"
                    )
                    st.metric(
                        label="Annual Returns",
                        value=f"{metrics['annual_returns']:.2f}%",
                        delta=f"{metrics['annual_returns']:.2f}%"
                    )
                
                with col3:
                    st.metric(
                        label="Volatility (Annual)",
                        value=f"{metrics['volatility']:.2f}%"
                    )
                    st.metric(
                        label="Sharpe Ratio",
                        value=f"{metrics['sharpe_ratio']:.2f}"
                    )
                
                # Plot returns histogram
                if 'returns' in metrics and len(metrics['returns']) > 0:
                    st.subheader("Daily Returns Distribution")
                    fig = go.Figure()
                    fig.add_trace(
                        go.Histogram(
                            x=metrics['returns'],
                            nbinsx=50,
                            marker_color='rgba(0, 123, 255, 0.6)',
                            name="Daily Returns"
                        )
                    )
                    fig.update_layout(
                        title=f"{current_ticker} Daily Returns Distribution",
                        xaxis_title="Daily Return (%)",
                        yaxis_title="Frequency",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error calculating performance metrics: {str(e)}")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.write("Please check the ticker symbol and try again.")

# Add a footer with disclaimer
st.markdown("---")
st.caption("**Disclaimer:** This tool is for informational purposes only. It is not intended to provide investment advice.")
st.caption("Data provided by Yahoo Finance")
