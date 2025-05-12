"""
Database module for stock analyzer application.
Handles database connections, schema, and operations using SQLite.
"""

import os
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Table, MetaData
from sqlalchemy import select, insert, delete, update, text, inspect
from sqlalchemy import DateTime, func
from datetime import datetime
import pathlib

# Create data directory if it doesn't exist
data_dir = pathlib.Path("./data")
data_dir.mkdir(exist_ok=True)

# Use a persistent SQLite database
DATABASE_URL = "sqlite:///data/stockanalyzer.db"

# Flag to track database status
using_fallback = False

# Create engine with proper error handling
try:
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    print("Database engine created successfully")
except Exception as e:
    print(f"Error creating database engine: {str(e)}")
    # Create a in-memory SQLite database as fallback
    print("Using in-memory SQLite database as fallback")
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    using_fallback = True

# Define tables
watchlists = Table(
    'watchlists',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(50), nullable=False),  # Using string as we don't have user auth yet
    Column('ticker', String(10), nullable=False),
    Column('added_at', DateTime, default=datetime.now)
)

search_history = Table(
    'search_history',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(50), nullable=False),
    Column('ticker', String(10), nullable=False),
    Column('searched_at', DateTime, default=datetime.now)
)

user_preferences = Table(
    'user_preferences',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(50), nullable=False, unique=True),
    Column('default_ticker', String(10), default='AAPL'),
    Column('default_period', String(20), default='1 Year'),
    Column('theme', String(10), default='light'),
    Column('show_ma50', Integer, default=1),
    Column('show_ma200', Integer, default=1),
    Column('updated_at', DateTime, default=datetime.now)
)

# Create tables if they don't exist
def init_db():
    """Initialize database and create tables if they don't exist"""
    try:
        inspector = inspect(engine)
        tables_exist = all(table.name in inspector.get_table_names() 
                          for table in [watchlists, search_history, user_preferences])
        
        if not tables_exist:
            metadata.create_all(engine)
            print("Database tables created successfully.")
        else:
            print("Database tables already exist.")
            
        # If using fallback SQLite database, always create tables
        if using_fallback:
            metadata.create_all(engine)
            print("Created tables in fallback database.")
            
        return True
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False

# Initialize connection
def get_connection():
    """Get a connection to the database"""
    global engine
    try:
        return engine.connect()
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        # Recreate engine if needed
        if str(e).lower().find('closed') >= 0:
            engine = create_engine(DATABASE_URL)
            return engine.connect()
        raise

# Watchlist operations
def get_watchlist(user_id='default_user'):
    """Get user's watchlist from database"""
    try:
        with get_connection() as conn:
            query = select(watchlists.c.ticker).where(watchlists.c.user_id == user_id)
            result = conn.execute(query)
            return [row[0] for row in result.fetchall()]
    except Exception as e:
        print(f"Error getting watchlist: {str(e)}")
        return []

def add_to_watchlist(ticker, user_id='default_user'):
    """Add ticker to user's watchlist"""
    try:
        with get_connection() as conn:
            # Check if already exists
            query = select(watchlists.c.id).where(
                (watchlists.c.user_id == user_id) & 
                (watchlists.c.ticker == ticker)
            )
            existing = conn.execute(query).first()
            
            if not existing:
                stmt = insert(watchlists).values(
                    user_id=user_id,
                    ticker=ticker,
                    added_at=datetime.now()
                )
                conn.execute(stmt)
                conn.commit()
                return True
            return False
    except Exception as e:
        print(f"Error adding to watchlist: {str(e)}")
        return False

def remove_from_watchlist(ticker, user_id='default_user'):
    """Remove ticker from user's watchlist"""
    try:
        with get_connection() as conn:
            stmt = delete(watchlists).where(
                (watchlists.c.user_id == user_id) & 
                (watchlists.c.ticker == ticker)
            )
            conn.execute(stmt)
            conn.commit()
            return True
    except Exception as e:
        print(f"Error removing from watchlist: {str(e)}")
        return False

# Search history operations
def add_to_search_history(ticker, user_id='default_user'):
    """Add ticker to search history"""
    try:
        with get_connection() as conn:
            stmt = insert(search_history).values(
                user_id=user_id,
                ticker=ticker,
                searched_at=datetime.now()
            )
            conn.execute(stmt)
            conn.commit()
            return True
    except Exception as e:
        print(f"Error adding to search history: {str(e)}")
        return False

def get_recent_searches(user_id='default_user', limit=5):
    """Get user's recent searches"""
    try:
        with get_connection() as conn:
            query = select(search_history.c.ticker, search_history.c.searched_at).where(
                search_history.c.user_id == user_id
            ).order_by(search_history.c.searched_at.desc()).limit(limit)
            
            result = conn.execute(query)
            return [(row[0], row[1]) for row in result.fetchall()]
    except Exception as e:
        print(f"Error getting recent searches: {str(e)}")
        return []

# User preferences operations
def get_user_preferences(user_id='default_user'):
    """Get user preferences"""
    try:
        with get_connection() as conn:
            query = select(user_preferences).where(
                user_preferences.c.user_id == user_id
            )
            result = conn.execute(query).first()
            
            if result:
                # Convert row to dictionary
                return {c.name: getattr(result, c.name) for c in user_preferences.c}
            else:
                # Create default preferences
                default_prefs = {
                    'user_id': user_id,
                    'default_ticker': 'AAPL',
                    'default_period': '1 Year',
                    'theme': 'light',
                    'show_ma50': 1,
                    'show_ma200': 1,
                    'updated_at': datetime.now()
                }
                
                stmt = insert(user_preferences).values(**default_prefs)
                conn.execute(stmt)
                conn.commit()
                
                # Return the default preferences
                return default_prefs
    except Exception as e:
        print(f"Error getting user preferences: {str(e)}")
        # Return default preferences without DB interaction
        return {
            'default_ticker': 'AAPL',
            'default_period': '1 Year',
            'theme': 'light',
            'show_ma50': 1,
            'show_ma200': 1
        }

def update_user_preferences(preferences, user_id='default_user'):
    """Update user preferences"""
    try:
        with get_connection() as conn:
            # Check if preferences exist
            query = select(user_preferences.c.id).where(
                user_preferences.c.user_id == user_id
            )
            existing_id = conn.execute(query).scalar()
            
            if existing_id:
                # Update existing preferences
                stmt = update(user_preferences).where(
                    user_preferences.c.user_id == user_id
                ).values(**preferences)
            else:
                # Create new preferences
                preferences['user_id'] = user_id
                stmt = insert(user_preferences).values(**preferences)
            
            conn.execute(stmt)
            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating user preferences: {str(e)}")
        return False

# Initialize the database
init_db()