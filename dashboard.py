import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os
import sqlite3
import calendar
from datetime import datetime, timedelta
import time
import re
import json
import plotly.graph_objects as go
import itertools

# --- The Cache-Busting Trigger ---
if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = 0

# --- Configuration & Setup ---
st.set_page_config(page_title="Trading Journal Vault", layout="wide")

st.sidebar.header("⚙️ Database Configuration")
st.sidebar.markdown("Define the exact filename of your SQLite database to prevent Ghost Vaults.")
db_filename = st.sidebar.text_input("Database Filename:", value="trading_journal.db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "trade_screenshots")
DB_FILE = os.path.join(BASE_DIR, db_filename)

os.makedirs(IMAGE_DIR, exist_ok=True)
st.sidebar.success(f"Locked to Vault:\n`{DB_FILE}`")

COMMISSIONS = {
    'ES': 1.75, 'MES': 0.5, 'NQ': 1.75, 'MNQ': 0.5, 'RTY': 1.75, 'M2K': 0.5,
    'NKD': 1.75, 'YM': 1.75, 'MYM': 0.5, 'CL': 2.00, 'MCL': 0.5, 'QM': 2.00,
    'QG': 1.3, 'NG': 2.00, 'PL': 2.3, 'HG': 2.3, 'GC': 2.3, 'MGC': 0.8,
    'SI': 2.3, 'HE': 2.8, 'LE': 2.8, 'ZS': 2.8, 'ZC': 2.8, 'ZL': 2.8,
    'ZM': 2.8, 'ZW': 2.8, 'SIL': 0.8
}

LESSON_TAGS = [
    "🧠 Psych: Revenge Trading",
    "🧠 Psych: FOMO (Chasing)",
    "🧠 Psych: Boredom / Overtrading",
    "🧠 Psych: Hesitation / Paralysis",
    "🛡️ Risk: Averaging Down",
    "🛡️ Risk: Moving Stop Loss",
    "🛡️ Risk: Risked Daily Max on One Trade",
    "🛡️ Risk: Oversizing",
    "🛡️ Risk: Undersizing",
    "⚙️ Tech: Ignored Higher Timeframe",
    "⚙️ Tech: Trading Into News",
    "⚙️ Tech: Front-Running the Setup",
    "🏆 Win: Textbook Execution",
    "🏆 Win: Held Through Heat",
    "🏆 Win: Took the Planned Stop"
]

CONFLUENCE_TAGS = [
    "📍 Context: HTF Alignment",
    "📍 Context: TR Boundary (Top/Bottom)",
    "📍 Context: Major Trendline / Channel Line",
    "📍 Context: Key Magnet Level",
    "📍 Context: Measured Move Target",
    "🎯 Setup: H2 / L2 (Second Entry)",
    "🎯 Setup: Wedge Flag (3 Pushes)",
    "🎯 Setup: Major Trend Reversal (MTR)",
    "🎯 Setup: Failed Breakout (FBO)",
    "🎯 Setup: Breakout Pullback (BOPB)",
    "🎯 Setup: Micro Double Top / Bottom",
    "🕯️ Signal: Strong Trend Bar",
    "🕯️ Signal: Perfect Reversal Bar",
    "🕯️ Signal: Inside Bar (ii / ioi)",
    "🕯️ Signal: Outside Bar",
    "🪤 Trap: Vacuum Exhaustion",
    "🪤 Trap: Trapped Traders (2nd Entry Trap)"
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    tables = [
        '''CREATE TABLE IF NOT EXISTS trades (trade_id TEXT PRIMARY KEY, instrument TEXT, timestamp TEXT, pnl REAL, duration TEXT, qty INTEGER, entry_time TEXT, exit_time TEXT, entry_price REAL, exit_price REAL, commission REAL, net_pnl REAL, trade_type TEXT, is_deleted INTEGER DEFAULT 0)''',
        '''CREATE TABLE IF NOT EXISTS journal_entries (trade_id TEXT PRIMARY KEY, notes TEXT, score INTEGER DEFAULT 0, good_bad TEXT, improve TEXT, action_plan TEXT, strategy TEXT DEFAULT 'Uncategorized', lesson_tags TEXT DEFAULT '', confluence_tags TEXT DEFAULT '')''',
        '''CREATE TABLE IF NOT EXISTS daily_journal (date_str TEXT PRIMARY KEY, goal TEXT, reflection TEXT)''',
        '''CREATE TABLE IF NOT EXISTS trading_rules (id TEXT PRIMARY KEY, max_risk TEXT, setups TEXT, runners TEXT)''',
        '''CREATE TABLE IF NOT EXISTS weekly_goals (id TEXT PRIMARY KEY, goal TEXT, mon_status TEXT, mon_how TEXT, mon_plan TEXT, tue_status TEXT, tue_how TEXT, tue_plan TEXT, wed_status TEXT, wed_how TEXT, wed_plan TEXT, thu_status TEXT, thu_how TEXT, thu_plan TEXT, fri_status TEXT, fri_how TEXT, fri_plan TEXT, history TEXT)''',
        '''CREATE TABLE IF NOT EXISTS weekly_history (week_range TEXT PRIMARY KEY, report_text TEXT, is_deleted INTEGER DEFAULT 0)''',
        '''CREATE TABLE IF NOT EXISTS monthly_enemy (id TEXT PRIMARY KEY, enemy TEXT, trading_effect TEXT, life_effect TEXT, action_plan TEXT, progress TEXT, w1_status TEXT, w1_how TEXT, w1_plan TEXT, w1_grade TEXT, w2_status TEXT, w2_how TEXT, w2_plan TEXT, w2_grade TEXT, w3_status TEXT, w3_how TEXT, w3_plan TEXT, w3_grade TEXT, w4_status TEXT, w4_how TEXT, w4_plan TEXT, w4_grade TEXT, w5_status TEXT, w5_how TEXT, w5_plan TEXT, w5_grade TEXT)''',
        '''CREATE TABLE IF NOT EXISTS monthly_enemy_history (month_range TEXT PRIMARY KEY, report_text TEXT, is_deleted INTEGER DEFAULT 0)''',
        '''CREATE TABLE IF NOT EXISTS market_data (instrument TEXT, timestamp TEXT, open REAL, high REAL, low REAL, close REAL, is_deleted INTEGER DEFAULT 0, PRIMARY KEY (instrument, timestamp))'''
    ]
    for t in tables: cursor.execute(t)

    alterations = [
        "ALTER TABLE trades ADD COLUMN qty INTEGER DEFAULT 0",
        "ALTER TABLE trades ADD COLUMN entry_time TEXT DEFAULT 'N/A'",
        "ALTER TABLE trades ADD COLUMN exit_time TEXT DEFAULT 'N/A'",
        "ALTER TABLE trades ADD COLUMN entry_price REAL DEFAULT 0.0",
        "ALTER TABLE trades ADD COLUMN exit_price REAL DEFAULT 0.0",
        "ALTER TABLE trades ADD COLUMN commission REAL DEFAULT 0.0",
        "ALTER TABLE trades ADD COLUMN net_pnl REAL DEFAULT 0.0",
        "ALTER TABLE trades ADD COLUMN trade_type TEXT DEFAULT 'Unknown'",
        "ALTER TABLE trades ADD COLUMN is_deleted INTEGER DEFAULT 0",
        "ALTER TABLE weekly_history ADD COLUMN is_deleted INTEGER DEFAULT 0",
        "ALTER TABLE monthly_enemy_history ADD COLUMN is_deleted INTEGER DEFAULT 0",
        "ALTER TABLE market_data ADD COLUMN is_deleted INTEGER DEFAULT 0",
        "ALTER TABLE journal_entries ADD COLUMN score INTEGER DEFAULT 0",
        "ALTER TABLE journal_entries ADD COLUMN good_bad TEXT",
        "ALTER TABLE journal_entries ADD COLUMN improve TEXT",
        "ALTER TABLE journal_entries ADD COLUMN action_plan TEXT",
        "ALTER TABLE journal_entries ADD COLUMN strategy TEXT DEFAULT 'Uncategorized'",
        "ALTER TABLE journal_entries ADD COLUMN lesson_tags TEXT DEFAULT ''",
        "ALTER TABLE journal_entries ADD COLUMN confluence_tags TEXT DEFAULT ''",
        "ALTER TABLE trading_rules ADD COLUMN prep_day TEXT",
        "ALTER TABLE trading_rules ADD COLUMN prep_week TEXT",
        "ALTER TABLE trading_rules ADD COLUMN max_risk_day TEXT",
        "ALTER TABLE trading_rules ADD COLUMN position_sizes TEXT",
        "ALTER TABLE trading_rules ADD COLUMN add_trade TEXT",
        "ALTER TABLE trading_rules ADD COLUMN stop_trading TEXT",
        "ALTER TABLE weekly_goals ADD COLUMN mon_grade TEXT DEFAULT '-'",
        "ALTER TABLE weekly_goals ADD COLUMN tue_grade TEXT DEFAULT '-'",
        "ALTER TABLE weekly_goals ADD COLUMN wed_grade TEXT DEFAULT '-'",
        "ALTER TABLE weekly_goals ADD COLUMN thu_grade TEXT DEFAULT '-'",
        "ALTER TABLE weekly_goals ADD COLUMN fri_grade TEXT DEFAULT '-'"
    ]
    for alt in alterations:
        try: cursor.execute(alt)
        except: pass
    conn.commit()
    conn.close()

def force_float(val):
    if pd.isna(val): return 0.0
    val_str = str(val)
    is_negative = '(' in val_str or '-' in val_str
    num_str = re.sub(r'[^\d\.]', '', val_str)
    if not num_str: return 0.0
    try: return -float(num_str) if is_negative else float(num_str)
    except: return 0.0

def fmt_dollar(val):
    return f"${val:.2f}" if val >= 0 else f"-${abs(val):.2f}"

def parse_duration_to_seconds(d_str):
    if pd.isna(d_str) or str(d_str).strip() == 'N/A': return 0
    d_str = str(d_str).lower()
    hrs = re.search(r'(\d+)\s*hr', d_str)
    mins = re.search(r'(\d+)\s*min', d_str)
    secs = re.search(r'(\d+)\s*sec', d_str)
    h = int(hrs.group(1)) if hrs else 0
    m = int(mins.group(1)) if mins else 0
    s = int(secs.group(1)) if secs else 0
    return h * 3600 + m * 60 + s

def format_seconds_to_duration(total_seconds):
    if pd.isna(total_seconds) or total_seconds <= 0: return "0sec"
    total_seconds = int(total_seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    parts = []
    if h > 0: parts.append(f"{h}hr")
    if m > 0: parts.append(f"{m}min")
    if s > 0 or (h == 0 and m == 0): parts.append(f"{s}sec")
    return " ".join(parts)

def clean_and_prepare_data(df):
    df.columns = df.columns.astype(str).str.encode('ascii', 'ignore').str.decode('ascii').str.strip()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.encode('ascii', 'ignore').str.decode('ascii').str.strip()

    unwanted_cols = ['priceformat', 'priceformattype', 'buyfillid', 'sellfillid']
    drop_targets = [c for c in df.columns if any(u in str(c).lower() for u in unwanted_cols)]
    if drop_targets: df = df.drop(columns=drop_targets, errors='ignore')

    col_mapping = {}
    for orig_col in df.columns:
        c_upper = str(orig_col).upper().replace(" ", "").replace("_", "").replace("&", "").replace("/", "").replace(".", "")
        if 'SYMBOL' in c_upper or 'INSTRUMENT' in c_upper or 'CONTRACT' in c_upper: col_mapping[orig_col] = 'Instrument'
        elif 'DURATION' in c_upper: col_mapping[orig_col] = 'Duration'
        elif 'PNL' in c_upper or 'PROFIT' in c_upper: col_mapping[orig_col] = 'P&L'
        elif 'QTY' in c_upper or 'QUANTITY' in c_upper or 'VOLUME' in c_upper: col_mapping[orig_col] = 'Qty'
        elif 'BOUGHT' in c_upper or 'ENTRYTIME' in c_upper or 'BUYTIME' in c_upper: col_mapping[orig_col] = 'Entry_Time'
        elif 'SOLD' in c_upper or 'EXITTIME' in c_upper or 'SELLTIME' in c_upper: col_mapping[orig_col] = 'Exit_Time'
        elif 'BUYPRICE' in c_upper or 'ENTRYPRICE' in c_upper: col_mapping[orig_col] = 'Entry_Price'
        elif 'SELLPRICE' in c_upper or 'EXITPRICE' in c_upper: col_mapping[orig_col] = 'Exit_Price'

    df = df.rename(columns=col_mapping)
    if 'Instrument' not in df.columns: df['Instrument'] = 'Unknown'
    df['Instrument'] = df['Instrument'].astype(str).str.replace(r'[^\w-]', '', regex=True).str.upper()
    df['Duration'] = df.get('Duration', 'N/A')
    df['Qty'] = df.get('Qty', 0).apply(force_float).astype(int)
    df['P&L'] = df.get('P&L', 0.0).apply(force_float)

    for price_col in ['Entry_Price', 'Exit_Price']:
        if price_col not in df.columns: df[price_col] = 0.0
        else: df[price_col] = df[price_col].apply(force_float)
            
    for col in ['Entry_Time', 'Exit_Time']:
        if col in df.columns:
            df[col] = df[col].apply(pd.to_datetime, errors='coerce')
            
    if 'Entry_Time' not in df.columns and 'Exit_Time' not in df.columns:
        st.error("Error: Could not find any Date/Time columns.")
        return pd.DataFrame()
    elif 'Entry_Time' not in df.columns: df['Entry_Time'] = df['Exit_Time']
    elif 'Exit_Time' not in df.columns: df['Exit_Time'] = df['Entry_Time']

    df['trade_type'] = 'Long'
    is_short = df['Entry_Time'] > df['Exit_Time']
    df.loc[is_short, 'trade_type'] = 'Short'
    df.loc[is_short, ['Entry_Time', 'Exit_Time']] = df.loc[is_short, ['Exit_Time', 'Entry_Time']].values
    
    if 'Entry_Price' in df.columns and 'Exit_Price' in df.columns:
        df.loc[is_short, ['Entry_Price', 'Exit_Price']] = df.loc[is_short, ['Exit_Price', 'Entry_Price']].values

    df['Timestamp'] = df['Entry_Time']
    df = df.dropna(subset=['Timestamp']).copy()
    
    df['Entry_Time'] = df['Entry_Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['Exit_Time'] = df['Exit_Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['Timestamp'] = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

    def calculate_commission(row):
        instrument = str(row['Instrument']).upper().strip()
        qty = row['Qty']
        rate = 0.0
        for base_symbol in sorted(COMMISSIONS.keys(), key=len, reverse=True):
            if instrument.startswith(base_symbol):
                rate = COMMISSIONS[base_symbol]
                break
        return rate * qty * 2

    df['Commission'] = df.apply(calculate_commission, axis=1)
    df['Net_PnL'] = df['P&L'] - df['Commission']
    return df

def clean_ohlcv_data(df):
    col_mapping = {}
    upper_cols = {col: str(col).strip().upper() for col in df.columns}
    for orig_col, clean_col in upper_cols.items():
        clean_col_compact = str(clean_col).replace(" ", "").replace("_", "")
        if clean_col_compact in ['DATE', 'TIME', 'DATETIME', 'TIMESTAMP']: col_mapping[orig_col] = 'Timestamp'
        elif clean_col_compact in ['OPEN', 'O']: col_mapping[orig_col] = 'Open'
        elif clean_col_compact in ['HIGH', 'H']: col_mapping[orig_col] = 'High'
        elif clean_col_compact in ['LOW', 'L']: col_mapping[orig_col] = 'Low'
        elif clean_col_compact in ['CLOSE', 'C']: col_mapping[orig_col] = 'Close'
    df = df.rename(columns=col_mapping)
    required = ['Timestamp', 'Open', 'High', 'Low', 'Close']
    for req in required:
        if req not in df.columns: return pd.DataFrame()
            
    df = df.dropna(subset=['Timestamp']).copy()
    clean_time = df['Timestamp'].astype(str).str.replace('T', ' ', regex=False).str.replace(r'(\+|-)\d{2}:\d{2}$|Z$', '', regex=True)
    df['Timestamp'] = clean_time.apply(pd.to_datetime, errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    df = df.dropna(subset=['Timestamp'])
    for col in ['Open', 'High', 'Low', 'Close']: df[col] = df[col].apply(force_float)
    return df

def insert_trades_to_db(df):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    inserted_count = 0
    id_counts = {}
    for index, row in df.iterrows():
        instrument = str(row.get('Instrument', 'Unknown')).strip()
        timestamp = str(row['Timestamp']).strip()
        pnl = float(row.get('P&L', 0.0))
        duration = str(row.get('Duration', 'N/A')).strip()
        qty = int(row.get('Qty', 0))
        entry_time = str(row.get('Entry_Time', 'N/A')).strip()
        exit_time = str(row.get('Exit_Time', 'N/A')).strip()
        entry_price = float(row.get('Entry_Price', 0.0))
        exit_price = float(row.get('Exit_Price', 0.0))
        commission = float(row.get('Commission', 0.0))
        net_pnl = float(row.get('Net_PnL', pnl))
        trade_type = str(row.get('trade_type', 'Unknown')).strip()
        clean_timestamp = timestamp.replace(" ", "_").replace(":", "-")
        base_id = f"{instrument}_{clean_timestamp}_{qty}_{entry_price}_{exit_price}"
        if base_id in id_counts: id_counts[base_id] += 1
        else: id_counts[base_id] = 0
        trade_id = f"{base_id}_{id_counts[base_id]}"
        
        cursor.execute('''REPLACE INTO trades (trade_id, instrument, timestamp, pnl, duration, qty, entry_time, exit_time, entry_price, exit_price, commission, net_pnl, trade_type, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)''', (trade_id, instrument, timestamp, pnl, duration, qty, entry_time, exit_time, entry_price, exit_price, commission, net_pnl, trade_type))
        if cursor.rowcount > 0: inserted_count += 1
    conn.commit()
    conn.close()
    return inserted_count

def insert_market_data_to_db(df, instrument):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    inserted_count = 0
    for index, row in df.iterrows():
        timestamp = str(row['Timestamp'])
        op, hi, lo, cl = float(row['Open']), float(row['High']), float(row['Low']), float(row['Close'])
        cursor.execute('''REPLACE INTO market_data (instrument, timestamp, open, high, low, close, is_deleted) VALUES (?, ?, ?, ?, ?, ?, 0)''', (instrument, timestamp, op, hi, lo, cl))
        inserted_count += 1
    conn.commit()
    conn.close()
    return inserted_count

@st.cache_data
def load_all_trades():
    conn = sqlite3.connect(DB_FILE)
    query = '''SELECT t.*, j.notes, j.score, j.good_bad, j.improve, j.action_plan, j.strategy, j.lesson_tags, j.confluence_tags FROM trades t LEFT JOIN journal_entries j ON t.trade_id = j.trade_id WHERE t.is_deleted = 0 OR t.is_deleted IS NULL'''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        df['Datetime'] = df['timestamp'].apply(pd.to_datetime, errors='coerce')
        df = df.dropna(subset=['Datetime']).copy()
        df = df.sort_values(by='Datetime', ascending=True).reset_index(drop=True)
        df = df.rename(columns={
            'instrument': 'Instrument', 'timestamp': 'Timestamp', 'pnl': 'P&L', 
            'duration': 'Duration', 'qty': 'Qty', 'entry_time': 'Entry_Time',
            'exit_time': 'Exit_Time', 'entry_price': 'Entry_Price',
            'exit_price': 'Exit_Price', 'commission': 'Commission', 'net_pnl': 'Net_PnL'
        })
        df['notes'] = df['notes'].fillna("")
        df['score'] = df['score'].fillna(0).astype(int)
        df['good_bad'] = df['good_bad'].fillna("")
        df['improve'] = df['improve'].fillna("")
        df['action_plan'] = df['action_plan'].fillna("")
        df['strategy'] = df['strategy'].fillna("Uncategorized")
        df['lesson_tags'] = df.get('lesson_tags', '').fillna("")
        df['confluence_tags'] = df.get('confluence_tags', '').fillna("")
    return df

@st.cache_data
def get_market_data(instrument, start_time, end_time):
    conn = sqlite3.connect(DB_FILE)
    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
    query = '''SELECT timestamp, open, high, low, close FROM market_data WHERE instrument = ? AND timestamp >= ? AND timestamp <= ? AND (is_deleted = 0 OR is_deleted IS NULL)'''
    df = pd.read_sql_query(query, conn, params=(instrument, start_str, end_str))
    conn.close()
    if not df.empty:
        df['Datetime'] = df['timestamp'].apply(pd.to_datetime, errors='coerce')
        df = df.dropna(subset=['Datetime'])
        df = df.sort_values(by='Datetime')
    return df

@st.cache_data
def calculate_mae_mfe(instrument, entry_time_str, exit_time_str, entry_price, trade_type):
    if entry_time_str == 'N/A' or exit_time_str == 'N/A' or entry_price == 0.0: return "N/A", "N/A"
    try:
        dt_in = pd.to_datetime(entry_time_str).replace(tzinfo=None)
        dt_out = pd.to_datetime(exit_time_str).replace(tzinfo=None)
        if dt_in > dt_out: dt_in, dt_out = dt_out, dt_in
        
        search_start = dt_in.replace(second=0, microsecond=0)
        search_end = (dt_out + timedelta(minutes=1)).replace(second=0, microsecond=0)
        market_df = get_market_data(instrument, search_start, search_end)
        
        if market_df.empty: return "N/A", "N/A"
        max_high = market_df['high'].max()
        min_low = market_df['low'].min()
        if trade_type.upper() == 'LONG': mfe = max_high - entry_price; mae = entry_price - min_low
        elif trade_type.upper() == 'SHORT': mfe = entry_price - min_low; mae = max_high - entry_price
        else: return "N/A", "N/A"
        return max(0.0, mfe), max(0.0, mae)
    except: return "N/A", "N/A"

def delete_trade_from_db(trade_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE trades SET is_deleted = 1 WHERE trade_id = ?", (trade_id,))
    conn.commit()
    conn.close()

def delete_day_from_db(trade_ids):
    conn = sqlite3.connect(DB_FILE)
    for tid in trade_ids:
        conn.execute("UPDATE trades SET is_deleted = 1 WHERE trade_id = ?", (tid,))
    conn.commit()
    conn.close()

def delete_weekly_history(week_range):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE weekly_history SET is_deleted = 1 WHERE week_range = ?", (week_range,))
    conn.commit()
    conn.close()

def delete_monthly_enemy_history(month_range):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE monthly_enemy_history SET is_deleted = 1 WHERE month_range = ?", (month_range,))
    conn.commit()
    conn.close()

def delete_all_market_data():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE market_data SET is_deleted = 1")
    conn.commit()
    conn.close()

def restore_trade_from_db(trade_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE trades SET is_deleted = 0 WHERE trade_id = ?", (trade_id,))
    conn.commit()
    conn.close()

def restore_weekly_history(week_range):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE weekly_history SET is_deleted = 0 WHERE week_range = ?", (week_range,))
    conn.commit()
    conn.close()

def restore_monthly_enemy_history(month_range):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE monthly_enemy_history SET is_deleted = 0 WHERE month_range = ?", (month_range,))
    conn.commit()
    conn.close()

def restore_market_data():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE market_data SET is_deleted = 0")
    conn.commit()
    conn.close()

def empty_recycle_bin_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM trades WHERE is_deleted = 1")
    conn.execute("DELETE FROM weekly_history WHERE is_deleted = 1")
    conn.execute("DELETE FROM monthly_enemy_history WHERE is_deleted = 1")
    conn.execute("DELETE FROM market_data WHERE is_deleted = 1")
    conn.commit()
    conn.close()

def save_trade_note_to_db(trade_id, notes, score, good_bad, improve, action_plan, strategy, lesson_tags_str, conf_tags_str):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''REPLACE INTO journal_entries (trade_id, notes, score, good_bad, improve, action_plan, strategy, lesson_tags, confluence_tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (trade_id, notes, score, good_bad, improve, action_plan, strategy, lesson_tags_str, conf_tags_str))
    conn.commit()
    conn.close()
    st.cache_data.clear()

def save_daily_note_to_db(date_str, goal, reflection):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''REPLACE INTO daily_journal (date_str, goal, reflection) VALUES (?, ?, ?)''', (date_str, goal, reflection))
    conn.commit()
    conn.close()

def get_daily_note_from_db(date_str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT goal, reflection FROM daily_journal WHERE date_str = ?', (date_str,))
    result = cursor.fetchone()
    conn.close()
    if result: return result[0], result[1]
    return "", ""

def save_trading_rules(prep_day, prep_week, max_risk_trade, max_risk_day, setups, position_sizes, add_trade, stop_trading):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''REPLACE INTO trading_rules (id, prep_day, prep_week, max_risk, max_risk_day, setups, position_sizes, add_trade, stop_trading) VALUES ('global', ?, ?, ?, ?, ?, ?, ?, ?)''', (prep_day, prep_week, max_risk_trade, max_risk_day, setups, position_sizes, add_trade, stop_trading))
    conn.commit()
    conn.close()

def get_trading_rules():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''SELECT prep_day, prep_week, max_risk, max_risk_day, setups, position_sizes, add_trade, stop_trading FROM trading_rules WHERE id = "global"''')
    result = cursor.fetchone()
    conn.close()
    if result: return tuple(val if val is not None else "" for val in result)
    return ("", "", "", "", "", "", "", "")

def save_weekly_goals(goal, m_s, m_h, m_p, m_g, tu_s, tu_h, tu_p, tu_g, w_s, w_h, w_p, w_g, th_s, th_h, th_p, th_g, f_s, f_h, f_p, f_g, history):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''REPLACE INTO weekly_goals (id, goal, mon_status, mon_how, mon_plan, mon_grade, tue_status, tue_how, tue_plan, tue_grade, wed_status, wed_how, wed_plan, wed_grade, thu_status, thu_how, thu_plan, thu_grade, fri_status, fri_how, fri_plan, fri_grade, history) VALUES ('global', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (goal, m_s, m_h, m_p, m_g, tu_s, tu_h, tu_p, tu_g, w_s, w_h, w_p, w_g, th_s, th_h, th_p, th_g, f_s, f_h, f_p, f_g, history))
    conn.commit()
    conn.close()

def get_weekly_goals():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''SELECT goal, mon_status, mon_how, mon_plan, mon_grade, tue_status, tue_how, tue_plan, tue_grade, wed_status, wed_how, wed_plan, wed_grade, thu_status, thu_how, thu_plan, thu_grade, fri_status, fri_how, fri_plan, fri_grade, history FROM weekly_goals WHERE id = "global"''')
    result = cursor.fetchone()
    conn.close()
    if result: return tuple(val if val is not None else "" for val in result)
    return ("", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "")

def save_weekly_history(week_range, report_text):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("REPLACE INTO weekly_history (week_range, report_text, is_deleted) VALUES (?, ?, 0)", (week_range, report_text))
    conn.commit()
    conn.close()

def get_weekly_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT week_range, report_text FROM weekly_history WHERE is_deleted = 0 OR is_deleted IS NULL ORDER BY week_range DESC")
    result = cursor.fetchall()
    conn.close()
    return result

def save_monthly_enemy(enemy, trading_effect, life_effect, action_plan, progress, w1_s, w1_h, w1_p, w1_g, w2_s, w2_h, w2_p, w2_g, w3_s, w3_h, w3_p, w3_g, w4_s, w4_h, w4_p, w4_g, w5_s, w5_h, w5_p, w5_g):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''REPLACE INTO monthly_enemy (id, enemy, trading_effect, life_effect, action_plan, progress, w1_status, w1_how, w1_plan, w1_grade, w2_status, w2_how, w2_plan, w2_grade, w3_status, w3_how, w3_plan, w3_grade, w4_status, w4_how, w4_plan, w4_grade, w5_status, w5_how, w5_plan, w5_grade) VALUES ('global', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (enemy, trading_effect, life_effect, action_plan, progress, w1_s, w1_h, w1_p, w1_g, w2_s, w2_h, w2_p, w2_g, w3_s, w3_h, w3_p, w3_g, w4_s, w4_h, w4_p, w4_g, w5_s, w5_h, w5_p, w5_g))
    conn.commit()
    conn.close()

def get_monthly_enemy():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''SELECT enemy, trading_effect, life_effect, action_plan, progress, w1_status, w1_how, w1_plan, w1_grade, w2_status, w2_how, w2_plan, w2_grade, w3_status, w3_how, w3_plan, w3_grade, w4_status, w4_how, w4_plan, w4_grade, w5_status, w5_how, w5_plan, w5_grade FROM monthly_enemy WHERE id = "global"''')
    result = cursor.fetchone()
    conn.close()
    if result: return tuple(val if val is not None else "" for val in result)
    return ("", "", "", "", "", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-")

def save_monthly_enemy_history(month_range, report_text):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("REPLACE INTO monthly_enemy_history (month_range, report_text, is_deleted) VALUES (?, ?, 0)", (month_range, report_text))
    conn.commit()
    conn.close()

def get_monthly_enemy_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT month_range, report_text FROM monthly_enemy_history WHERE is_deleted = 0 OR is_deleted IS NULL ORDER BY month_range DESC")
    result = cursor.fetchall()
    conn.close()
    return result

def render_tradingview_chart(market_df, entry_time_str, exit_time_str, trade_type):
    market_df = market_df.drop_duplicates(subset=['Datetime']).sort_values(by='Datetime')
    valid_times, candles = [], []
    for _, row in market_df.iterrows():
        unix_time = int(row['Datetime'].timestamp())
        valid_times.append(unix_time)
        candles.append({"time": unix_time, "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close']})
        
    markers = []
    if entry_time_str != 'N/A' and exit_time_str != 'N/A' and valid_times:
        dt_in = pd.to_datetime(entry_time_str).replace(tzinfo=None)
        dt_out = pd.to_datetime(exit_time_str).replace(tzinfo=None)
        unix_in, unix_out = int(dt_in.timestamp()), int(dt_out.timestamp())
        if unix_in not in valid_times: unix_in = min(valid_times, key=lambda x: abs(x - unix_in))
        if unix_out not in valid_times: unix_out = min(valid_times, key=lambda x: abs(x - unix_out))
        in_color = "#2196F3" if trade_type == "Long" else "#E91E63"
        out_color = "#E91E63" if trade_type == "Long" else "#2196F3"
        raw_markers = [{"time": unix_in, "position": "belowBar", "color": in_color, "shape": "arrowUp", "text": "In"}, {"time": unix_out, "position": "aboveBar", "color": out_color, "shape": "arrowDown", "text": "Out"}]
        markers = sorted(raw_markers, key=lambda x: x["time"])
        
    html_template = f"""
    <div id="tvchart" style="width: 100%; height: 450px; background-color: #131722;"></div>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        try {{
            const chart = LightweightCharts.createChart(document.getElementById('tvchart'), {{
                autoSize: true, 
                layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
                grid: {{ vertLines: {{ color: '#2b2b43' }}, horzLines: {{ color: '#2b2b43' }} }},
                timeScale: {{ timeVisible: true, secondsVisible: false }},
            }});
            const candleSeries = chart.addCandlestickSeries({{upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350'}});
            candleSeries.setData({json.dumps(candles)});
            const markers = {json.dumps(markers)};
            if (markers.length > 0) candleSeries.setMarkers(markers);
            chart.timeScale().fitContent();
        }} catch (error) {{ document.getElementById('tvchart').innerHTML = "<div style='color:red; font-weight:bold; padding:20px; border:1px solid red;'>Chart Rendering Error: " + error.message + "</div>"; }}
    </script>
    """
    return html_template

init_db()

# --- MAIN UI ---
st.title("📈 Permanent Trading Vault & Journal")
st.markdown("Upload a new CSV to add trades to your vault, or simply review your historical performance.")

col_up1, col_up2 = st.columns(2)
with col_up1:
    with st.expander("➕ Upload New Trades", expanded=False):
        uploaded_file = st.file_uploader("Upload Tradovate Trade Report (CSV)", type=['csv'])
        if uploaded_file is not None:
            if st.button("Process & Save Trades to Vault"):
                raw_df = pd.read_csv(uploaded_file)
                clean_df = clean_and_prepare_data(raw_df)
                if not clean_df.empty:
                    new_trades = insert_trades_to_db(clean_df)
                    total_pnl_found = clean_df['P&L'].sum()
                    st.cache_data.clear() 
                    st.success(f"Successfully processed! Added {new_trades} trades. (Gross P&L Found: ${total_pnl_found:.2f})")
                    time.sleep(1.5)
                    st.rerun()

with col_up2:
    with st.expander("📈 Upload TradingView Market Data (OHLCV)", expanded=False):
        ohlcv_instrument = st.text_input("Enter Instrument Name exactly as traded (e.g., MNQM6):")
        ohlcv_file = st.file_uploader("Upload TradingView Data (CSV)", type=['csv'], key="ohlcv")
        if ohlcv_file is not None and ohlcv_instrument:
            if st.button("Process & Save Market Data"):
                raw_ohlcv = pd.read_csv(ohlcv_file)
                clean_ohlcv = clean_ohlcv_data(raw_ohlcv)
                if not clean_ohlcv.empty:
                    rows = insert_market_data_to_db(clean_ohlcv, ohlcv_instrument.upper())
                    st.cache_data.clear() 
                    st.success(f"Successfully processed {rows} minutes of market data for {ohlcv_instrument.upper()}!")
        st.markdown("---")
        
        confirm_md_clear = st.checkbox("I confirm I want to clear all market data.", key="conf_md_clear")
        if st.button("🗑️ Clear All Saved Market Data", use_container_width=True):
            if confirm_md_clear:
                delete_all_market_data()
                st.cache_data.clear()
                st.success("Market data moved to recycle bin.")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("⚠️ Please check the confirmation box above to proceed.")

st.divider()

# --- WEEKLY IMPROVEMENT GOAL ---
st.header("🎯 Weekly Improvement Goal")
wg_data = get_weekly_goals()
wg_goal = wg_data[0]
legacy_history = wg_data[21]
status_opts = ["N/A", "Yes", "No"]
grade_opts = ["-", "A", "B", "C", "D", "F"]

new_wg_goal = st.text_area("Weekly goal that I plan to improve on and focus on for the week:", value=wg_goal, height=100)
st.markdown("<br>", unsafe_allow_html=True)

days = ["mon", "tue", "wed", "thu", "fri"]
day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
saved_s = [wg_data[1], wg_data[5], wg_data[9], wg_data[13], wg_data[17]]
saved_h = [wg_data[2], wg_data[6], wg_data[10], wg_data[14], wg_data[18]]
saved_p = [wg_data[3], wg_data[7], wg_data[11], wg_data[15], wg_data[19]]
saved_g = [wg_data[4], wg_data[8], wg_data[12], wg_data[16], wg_data[20]]

cols = st.columns(5)
new_wg = {}
for i in range(5):
    with cols[i]:
        st.markdown(f"<div style='text-align: center; font-weight: bold;'>{day_names[i]}</div>", unsafe_allow_html=True)
        new_wg[f"{days[i]}_s"] = st.radio("Followed goal?", status_opts, index=status_opts.index(saved_s[i]) if saved_s[i] in status_opts else 0, key=f"{days[i]}_s", horizontal=True)
        new_wg[f"{days[i]}_g"] = st.selectbox("Grade", grade_opts, index=grade_opts.index(saved_g[i]) if saved_g[i] in grade_opts else 0, key=f"{days[i]}_g")
        new_wg[f"{days[i]}_h"] = st.text_area("How?", value=saved_h[i], key=f"{days[i]}_h", height=100)
        new_wg[f"{days[i]}_p"] = st.text_area("Plan:", value=saved_p[i], key=f"{days[i]}_p", height=100)

st.markdown("<br>", unsafe_allow_html=True)
col_w_save, col_w_clear = st.columns([3, 2])
with col_w_save:
    if st.button("Save Current Weekly Goal Inputs", use_container_width=True):
        save_weekly_goals(new_wg_goal, 
            new_wg["mon_s"], new_wg["mon_h"], new_wg["mon_p"], new_wg["mon_g"], 
            new_wg["tue_s"], new_wg["tue_h"], new_wg["tue_p"], new_wg["tue_g"], 
            new_wg["wed_s"], new_wg["wed_h"], new_wg["wed_p"], new_wg["wed_g"], 
            new_wg["thu_s"], new_wg["thu_h"], new_wg["thu_p"], new_wg["thu_g"], 
            new_wg["fri_s"], new_wg["fri_h"], new_wg["fri_p"], new_wg["fri_g"], legacy_history)
        st.success("Weekly tracking successfully saved to vault!")
        time.sleep(1)
        st.rerun()

with col_w_clear:
    confirm_w_clear = st.checkbox("Confirm wiping board", key="conf_w_clear")
    if st.button("🧹 Clear Active Weekly Board", use_container_width=True):
        if confirm_w_clear:
            save_weekly_goals("", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", legacy_history)
            st.success("Weekly board wiped clean!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("⚠️ Please check confirmation box.")

with st.expander("🗄️ Archive Week to History Report Card", expanded=False):
    col_arch1, col_arch2 = st.columns([2, 1])
    with col_arch1: week_date_range = st.text_input("Enter Date Range to save this week:")
    with col_arch2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Archive to History", use_container_width=True) and week_date_range:
            report = f"The goal for the week was:\n- {new_wg_goal}\n\n"
            for i in range(5):
                report += f"{day_names[i]} - {new_wg[f'{days[i]}_s']} - Grade: {new_wg[f'{days[i]}_g']}\nHow: {new_wg[f'{days[i]}_h']}\nPlan: {new_wg[f'{days[i]}_p']}\n\n"
            save_weekly_history(week_date_range, report)
            st.success("Archived to History successfully!")
            time.sleep(1.5)
            st.rerun()
    
    history_records = get_weekly_history()
    if not history_records: st.info("No report cards saved yet.")
    else:
        for w_range, r_text in history_records:
            with st.expander(f"📅 Week Report: {w_range}", expanded=False):
                st.text(r_text)
                confirm_w_del = st.checkbox("Confirm Deletion", key=f"conf_w_{w_range}")
                if st.button(f"🗑️ Delete this Report Card", key=f"del_hist_{w_range}"):
                    if confirm_w_del:
                        delete_weekly_history(w_range)
                        st.rerun()
                    else:
                        st.error("⚠️ Please check the confirmation box.")

st.divider()

# --- MONTHLY ENEMY & PSYCHOLOGICAL TRACKER ---
st.header("🦹 Monthly Enemy & Psychological Tracker")
enemy_data = get_monthly_enemy()
e_enemy, e_trading, e_life, e_plan, e_progress = enemy_data[0:5]
saved_ew_s = [enemy_data[5], enemy_data[9], enemy_data[13], enemy_data[17], enemy_data[21]]
saved_ew_h = [enemy_data[6], enemy_data[10], enemy_data[14], enemy_data[18], enemy_data[22]]
saved_ew_p = [enemy_data[7], enemy_data[11], enemy_data[15], enemy_data[19], enemy_data[23]]
saved_ew_g = [enemy_data[8], enemy_data[12], enemy_data[16], enemy_data[20], enemy_data[24]]

col_e1, col_e2 = st.columns(2)
with col_e1:
    new_enemy = st.text_area("1) The Enemy (Negative trait):", value=e_enemy, height=100)
    new_trading = st.text_area("2) How did it affect my trading?", value=e_trading, height=100)
    new_life = st.text_area("3) How did it affect other areas of my life?", value=e_life, height=100)
with col_e2:
    new_plan = st.text_area("4) What am I going to do to eliminate this enemy?", value=e_plan, height=160)
    new_progress = st.text_area("5) What have I done so far?", value=e_progress, height=160)

st.markdown("<br>", unsafe_allow_html=True)
weeks = ["w1", "w2", "w3", "w4", "w5"]
week_names = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]
cols_e = st.columns(5)
new_ew = {}
for i in range(5):
    with cols_e[i]:
        st.markdown(f"<div style='text-align: center; font-weight: bold;'>{week_names[i]}</div>", unsafe_allow_html=True)
        new_ew[f"{weeks[i]}_s"] = st.radio("Defeated enemy?", status_opts, index=status_opts.index(saved_ew_s[i]) if saved_ew_s[i] in status_opts else 0, key=f"e_{weeks[i]}_s", horizontal=True)
        new_ew[f"{weeks[i]}_g"] = st.selectbox("Grade", grade_opts, index=grade_opts.index(saved_ew_g[i]) if saved_ew_g[i] in grade_opts else 0, key=f"e_{weeks[i]}_g")
        new_ew[f"{weeks[i]}_h"] = st.text_area("How?", value=saved_ew_h[i], key=f"e_{weeks[i]}_h", height=100)
        new_ew[f"{weeks[i]}_p"] = st.text_area("Plan:", value=saved_ew_p[i], key=f"e_{weeks[i]}_p", height=100)

st.markdown("<br>", unsafe_allow_html=True)
col_m_save, col_m_clear = st.columns([3, 2])
with col_m_save:
    if st.button("Save Current Monthly Enemy Tracking", use_container_width=True):
        save_monthly_enemy(new_enemy, new_trading, new_life, new_plan, new_progress, 
            new_ew["w1_s"], new_ew["w1_h"], new_ew["w1_p"], new_ew["w1_g"], 
            new_ew["w2_s"], new_ew["w2_h"], new_ew["w2_p"], new_ew["w2_g"], 
            new_ew["w3_s"], new_ew["w3_h"], new_ew["w3_p"], new_ew["w3_g"], 
            new_ew["w4_s"], new_ew["w4_h"], new_ew["w4_p"], new_ew["w4_g"], 
            new_ew["w5_s"], new_ew["w5_h"], new_ew["w5_p"], new_ew["w5_g"])
        st.success("Monthly enemy tracking successfully saved to vault!")
        time.sleep(1)
        st.rerun()

with col_m_clear:
    confirm_m_clear = st.checkbox("Confirm wiping board", key="conf_m_clear")
    if st.button("🧹 Clear Active Monthly Board", use_container_width=True):
        if confirm_m_clear:
            save_monthly_enemy("", "", "", "", "", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-")
            st.success("Monthly board wiped clean!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("⚠️ Please check confirmation box.")

with st.expander("🗄️ Archive Monthly Enemy to History", expanded=False):
    col_ea1, col_ea2 = st.columns([2, 1])
    with col_ea1: enemy_month_range = st.text_input("Enter Month Range to save:")
    with col_ea2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Archive Enemy to History", use_container_width=True) and enemy_month_range:
            report = f"The Enemy:\n- {new_enemy}\n\nTrading Effect: {new_trading}\nLife Effect: {new_life}\nAction Plan: {new_plan}\nProgress: {new_progress}\n\n"
            for i in range(5):
                report += f"{week_names[i]} - Defeated: {new_ew[f'{weeks[i]}_s']} - Grade: {new_ew[f'{weeks[i]}_g']}\nNotes: {new_ew[f'{weeks[i]}_h']}\nPlan: {new_ew[f'{weeks[i]}_p']}\n\n"
            save_monthly_enemy_history(enemy_month_range, report)
            st.success("Archived Enemy to History successfully!")
            time.sleep(1.5)
            st.rerun()
    
    enemy_hist = get_monthly_enemy_history()
    if not enemy_hist: st.info("No monthly enemy report cards saved yet.")
    else:
        for m_range, m_text in enemy_hist:
            with st.expander(f"🦹 Monthly Report: {m_range}", expanded=False):
                st.text(m_text)
                confirm_m_del = st.checkbox("Confirm Deletion", key=f"conf_m_{m_range}")
                if st.button(f"🗑️ Delete this Report Card", key=f"del_ehist_{m_range}"):
                    if confirm_m_del:
                        delete_monthly_enemy_history(m_range)
                        st.rerun()
                    else:
                        st.error("⚠️ Please check the confirmation box.")

st.divider()

with st.expander("📜 My Trading Rules & Master Plan", expanded=False):
    st.markdown("### Core Trading Rules")
    rule_data = get_trading_rules()
    (existing_prep_day, existing_prep_week, existing_risk_trade, existing_risk_day, existing_setups, existing_position_sizes, existing_add_trade, existing_stop_trading) = rule_data
    col_rule1, col_rule2 = st.columns(2)
    with col_rule1:
        rule_prep_day = st.text_area("1) What do I do to prepare for the day?", value=existing_prep_day, height=100)
        rule_risk_trade = st.text_area("3) Maximum Risk per trade:", value=existing_risk_trade, height=100)
        rule_setups = st.text_area("5) Types of Setups I'm allowed to take:", value=existing_setups, height=150)
        rule_add_trade = st.text_area("7) When do I add to a trade?", value=existing_add_trade, height=100)
    with col_rule2:
        rule_prep_week = st.text_area("2) What do I do to prepare for the week?", value=existing_prep_week, height=100)
        rule_risk_day = st.text_area("4) Maximum Risk Per Day:", value=existing_risk_day, height=100)
        rule_position_sizes = st.text_area("6) Position Sizes for each instrument:", value=existing_position_sizes, height=150)
        rule_stop_trading = st.text_area("8) When do I stop trading?", value=existing_stop_trading, height=100)
    if st.button("Save Trading Rules", use_container_width=True):
        save_trading_rules(rule_prep_day, rule_prep_week, rule_risk_trade, rule_risk_day, rule_setups, rule_position_sizes, rule_add_trade, rule_stop_trading)
        st.success("Trading rules updated and secured in the vault!")

st.divider()

master_df = load_all_trades()

if master_df.empty:
    st.info("Your vault is currently empty. Please upload a Tradovate CSV file using the menu above to begin.")
else:
    master_df['Date_str'] = master_df['Datetime'].dt.strftime('%A, %B %d, %Y')
    
    st.header("Dashboard Filters")
    
    col_filt1, col_filt2, col_filt3, col_filt4 = st.columns(4)
    with col_filt1:
        instrument_list = sorted(list(master_df['Instrument'].dropna().unique()))
        selected_instruments = st.multiselect("Filter by Instrument", instrument_list)
        if selected_instruments: master_df = master_df[master_df['Instrument'].isin(selected_instruments)]
    with col_filt2:
        strategy_list = sorted(list(master_df['strategy'].dropna().unique()))
        selected_strategies = st.multiselect("Filter by Strategy", strategy_list)
        if selected_strategies: master_df = master_df[master_df['strategy'].isin(selected_strategies)]
    with col_filt3:
        selected_confluences = st.multiselect("Filter by PA Confluences", CONFLUENCE_TAGS)
        if selected_confluences:
            def has_confluence(tag_string, tags_to_find):
                if pd.isna(tag_string) or not tag_string: return False
                row_tags = [t.strip() for t in str(tag_string).split(',')]
                return any(t in row_tags for t in tags_to_find)
            master_df = master_df[master_df['confluence_tags'].apply(lambda x: has_confluence(x, selected_confluences))]
    with col_filt4:
        min_score, max_score = st.slider("Filter by Execution Score", 0, 10, (0, 10))
        master_df = master_df[(master_df['score'] >= min_score) & (master_df['score'] <= max_score)]
            
    st.divider()
    
    if master_df.empty:
        st.warning("No trades match your current filters.")
    else:
        st.header("Historical Overview & Equity Curve")
        
        master_df = master_df.sort_values(by='Datetime').reset_index(drop=True)
        
        current_win_streak = 0
        max_win_streak = 0
        current_loss_streak = 0
        max_loss_streak = 0
        
        for pnl in master_df['Net_PnL']:
            if pnl > 0:
                current_win_streak += 1
                current_loss_streak = 0
                if current_win_streak > max_win_streak: max_win_streak = current_win_streak
            elif pnl < 0:
                current_loss_streak += 1
                current_win_streak = 0
                if current_loss_streak > max_loss_streak: max_loss_streak = current_loss_streak
                
        avg_trade_pnl = master_df['Net_PnL'].mean() if len(master_df) > 0 else 0.0
        
        master_df['Cumulative Net P&L'] = master_df['Net_PnL'].cumsum()
        master_df['Running_Peak'] = master_df['Cumulative Net P&L'].cummax()
        master_df['Running_Peak'] = master_df['Running_Peak'].clip(lower=0.0) 
        master_df['Drawdown'] = master_df['Cumulative Net P&L'] - master_df['Running_Peak']
        max_drawdown = master_df['Drawdown'].min() if len(master_df) > 0 else 0.0

        total_gross = master_df['P&L'].sum()
        total_commissions = master_df['Commission'].sum()
        total_net = master_df['Net_PnL'].sum()
        total_trades = len(master_df)
        
        total_gross_profit = master_df[master_df['P&L'] > 0]['P&L'].sum()
        total_gross_loss = abs(master_df[master_df['P&L'] < 0]['P&L'].sum())
        all_time_pf = "∞" if total_gross_loss == 0 and total_gross_profit > 0 else "0.00" if total_gross_loss == 0 else f"{(total_gross_profit / total_gross_loss):.2f}"
        
        winning_trades_count = len(master_df[master_df['P&L'] > 0])
        losing_trades_count = len(master_df[master_df['P&L'] <= 0])
        win_rate_val = f"{(len(master_df[master_df['Net_PnL'] > 0]) / total_trades * 100):.1f}%" if total_trades > 0 else "0%"
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gross P&L", f"${total_gross:.2f}")
        col2.metric("Commissions", f"-${total_commissions:.2f}")
        col3.metric("Net P&L", f"${total_net:.2f}")
        col4.metric("Total Trades", f"{total_trades}")
        
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Win Rate", win_rate_val)
        col6.metric("Profit Factor", all_time_pf)
        col7.metric("Gross Winning Trades", f"{winning_trades_count}")
        col8.metric("Gross Losing Trades", f"{losing_trades_count}")
        
        col9, col10, col11, col12 = st.columns(4)
        col9.metric("Max Consecutive Wins", f"{max_win_streak}")
        col10.metric("Max Consecutive Losses", f"{max_loss_streak}")
        col11.metric("Max Drawdown", f"-${abs(max_drawdown):.2f}")
        col12.metric("Avg Trade P&L", f"${avg_trade_pnl:.2f}" if avg_trade_pnl >= 0 else f"-${abs(avg_trade_pnl):.2f}")

        st.markdown("---")
        col_eq_title, col_eq_tog = st.columns([3, 1])
        with col_eq_title:
            st.subheader("Cumulative Net P&L & Drawdown Profile")
        with col_eq_tog:
            st.markdown("<br>", unsafe_allow_html=True)
            show_drawdown = st.toggle("🚨 Overlay Drawdown", value=False)

        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(x=master_df['Datetime'], y=master_df['Cumulative Net P&L'], mode='lines', fill='tozeroy', line=dict(color='#26a69a', width=3), fillcolor='rgba(38, 166, 154, 0.1)', name='Cumulative P&L'))
        
        if show_drawdown:
            fig_equity.add_trace(go.Scatter(x=master_df['Datetime'], y=master_df['Drawdown'], mode='lines', fill='tozeroy', line=dict(color='#ef5350', width=2), fillcolor='rgba(239, 83, 80, 0.2)', name='Drawdown', yaxis='y2'))
            fig_equity.update_layout(
                yaxis2=dict(
                    title=dict(text="Drawdown ($)", font=dict(color='#ef5350')),
                    tickprefix="-$",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    zeroline=False,
                    tickcolor='#ef5350',
                    tickfont=dict(color='#ef5350')
                )
            )
        
        fig_equity.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(type='date', rangebreaks=[dict(bounds=["sat", "sun"])]), yaxis=dict(tickprefix="$"), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', hovermode="x unified")
        fig_equity.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
        fig_equity.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
        st.plotly_chart(fig_equity, use_container_width=True)
        
        st.markdown("### 🎯 Strategies Review")
        strategies_to_track = ["Trend Continuation", "Reversal break of Trendline", "Buy Low Sell High TR", "Breakout", "Counter Trend", "Uncategorized"]
        strat_cols = st.columns(len(strategies_to_track))
        
        for i, strat in enumerate(strategies_to_track):
            strat_df = master_df[master_df['strategy'] == strat]
            with strat_cols[i]:
                if len(strat_df) == 0:
                    st.metric(f"{strat}", "$0.00", "0 Trades")
                    continue
                
                wins = strat_df[strat_df['Net_PnL'] > 0]
                losses = strat_df[strat_df['Net_PnL'] <= 0]
                
                win_rate = len(wins) / len(strat_df)
                loss_rate = len(losses) / len(strat_df)
                
                avg_win = wins['Net_PnL'].mean() if not wins.empty else 0.0
                avg_loss = abs(losses['Net_PnL'].mean()) if not losses.empty else 0.0
                expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
                
                best_t = strat_df['Net_PnL'].max()
                worst_t = strat_df['Net_PnL'].min()
                
                win_secs = wins['Duration'].apply(parse_duration_to_seconds).mean() if not wins.empty else 0
                loss_secs = losses['Duration'].apply(parse_duration_to_seconds).mean() if not losses.empty else 0
                
                st.metric(f"{strat}", f"{fmt_dollar(expectancy)} / trade", f"{len(strat_df)} Trades")
                st.markdown(f"""
                <div style="font-size:0.9em; line-height:1.5;">
                <b>Avg Win:</b> {fmt_dollar(avg_win)}<br>
                <b>Avg Loss:</b> {fmt_dollar(-avg_loss)}<br>
                <b>Best Trade:</b> {fmt_dollar(best_t)}<br>
                <b>Worst Trade:</b> {fmt_dollar(worst_t)}<br>
                <b>Avg Dur (W):</b> {format_seconds_to_duration(win_secs)}<br>
                <b>Avg Dur (L):</b> {format_seconds_to_duration(loss_secs)}
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        st.header("🏆 Performance Analytics Center")
        if len(master_df) > 0:
            st.subheader("1. Best & Worst Executions")
            best_trade = master_df.loc[master_df['Net_PnL'].idxmax()]
            worst_trade = master_df.loc[master_df['Net_PnL'].idxmin()]
            col_bw1, col_bw2 = st.columns(2)
            with col_bw1:
                st.success(f"**🟢 Best Trade:** +${best_trade['Net_PnL']:.2f}")
                st.write(f"**Date:** {best_trade['Timestamp']}\n**Instrument:** {best_trade['Instrument']} (Qty: {best_trade['Qty']})")
            with col_bw2:
                st.error(f"**🔴 Worst Trade:** ${worst_trade['Net_PnL']:.2f}")
                st.write(f"**Date:** {worst_trade['Timestamp']}\n**Instrument:** {worst_trade['Instrument']} (Qty: {worst_trade['Qty']})")
                
            st.subheader("2. Performance by Time of Day (15-Minute Increments)")
            perf_df = master_df.copy()
            perf_df['Time_15m'] = perf_df['Datetime'].dt.floor('15min').dt.time
            time_df = perf_df.groupby('Time_15m')['Net_PnL'].sum().reset_index()
            time_df['Time_str'] = time_df['Time_15m'].astype(str).str[:5]
            fig_time = go.Figure(data=[go.Bar(x=time_df['Time_str'], y=time_df['Net_PnL'], marker_color=['#26a69a' if val >= 0 else '#ef5350' for val in time_df['Net_PnL']])])
            fig_time.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(title='Time of Day (15m blocks)', tickangle=-45), yaxis=dict(title='Net P&L ($)', tickprefix="$"))
            st.plotly_chart(fig_time, use_container_width=True)
            
            col_perf1, col_perf2 = st.columns(2)
            with col_perf1:
                st.subheader("3. Performance by Day of Week")
                perf_df['Day_Name'] = perf_df['Datetime'].dt.day_name()
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                day_df = perf_df.groupby('Day_Name')['Net_PnL'].sum().reindex(days_order).dropna().reset_index()
                fig_day = go.Figure(data=[go.Bar(x=day_df['Day_Name'], y=day_df['Net_PnL'], marker_color=['#26a69a' if val >= 0 else '#ef5350' for val in day_df['Net_PnL']])])
                fig_day.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(tickprefix="$"))
                st.plotly_chart(fig_day, use_container_width=True)
            with col_perf2:
                st.subheader("4. Performance by Instrument")
                inst_df = perf_df.groupby('Instrument')['Net_PnL'].sum().reset_index()
                fig_inst = go.Figure(data=[go.Bar(x=inst_df['Instrument'], y=inst_df['Net_PnL'], marker_color=['#26a69a' if val >= 0 else '#ef5350' for val in inst_df['Net_PnL']])])
                fig_inst.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(tickprefix="$"))
                st.plotly_chart(fig_inst, use_container_width=True)

            st.markdown("---")
            st.subheader("5. The Scalper's Heatmap (MAE vs. MFE)")
            st.markdown("Visualizes the maximum heat (MAE) taken versus the maximum profit potential (MFE). Use this to mathematically optimize your stop-loss placement.")
            
            hm_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
            selected_hm_inst = st.multiselect("Filter Heatmap by Instrument (leave blank to chart all):", hm_instruments, key="hm_inst_filter")
            
            hm_dates = list(master_df['Date_str'].dropna().unique())[::-1]
            selected_hm_dates = st.multiselect("Filter Heatmap by Trading Day (leave blank to chart all):", hm_dates, key="hm_date_filter")
            
            hm_target_df = master_df.copy()
            if selected_hm_inst:
                hm_target_df = hm_target_df[hm_target_df['Instrument'].isin(selected_hm_inst)]
            if selected_hm_dates:
                hm_target_df = hm_target_df[hm_target_df['Date_str'].isin(selected_hm_dates)]
            
            heatmap_data = []
            efficiency_scores = []
            
            for _, row in hm_target_df.iterrows():
                mfe, mae = calculate_mae_mfe(row['Instrument'], row['Entry_Time'], row['Exit_Time'], row['Entry_Price'], row.get('trade_type', 'Unknown'))
                if mfe != "N/A" and mae != "N/A":
                    heatmap_data.append({'Trade': f"{row['Instrument']} ({row['Timestamp']})", 'MFE': float(mfe), 'MAE': float(mae), 'Net_PnL': row['Net_PnL']})
                    
                    t_type = row.get('trade_type', 'Unknown').upper()
                    captured_pts = (row['Exit_Price'] - row['Entry_Price']) if t_type == 'LONG' else (row['Entry_Price'] - row['Exit_Price'])
                    
                    if float(mfe) > 0 and captured_pts > 0:
                        efficiency_scores.append(min((captured_pts / float(mfe)) * 100, 100.0))
                    elif float(mfe) > 0:
                        efficiency_scores.append(0.0)
            
            if efficiency_scores:
                avg_efficiency = sum(efficiency_scores) / len(efficiency_scores)
                st.metric("🎯 Average MFE Capture Rate (Filtered Data)", f"{avg_efficiency:.1f}%")
            
            if heatmap_data:
                hm_df = pd.DataFrame(heatmap_data)
                fig_hm = go.Figure()
                
                wins = hm_df[hm_df['Net_PnL'] > 0]
                fig_hm.add_trace(go.Scatter(x=wins['MAE'], y=wins['MFE'], mode='markers', name='Winning Trades', marker=dict(color='#26a69a', size=10, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')), text=wins['Trade']))
                
                losses = hm_df[hm_df['Net_PnL'] <= 0]
                fig_hm.add_trace(go.Scatter(x=losses['MAE'], y=losses['MFE'], mode='markers', name='Losing Trades', marker=dict(color='#ef5350', size=10, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')), text=losses['Trade']))
                
                fig_hm.update_layout(height=500, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(title='Max Adverse Excursion (MAE) - Heat Taken', autorange="reversed", gridcolor='rgba(128, 128, 128, 0.2)'), yaxis=dict(title='Max Favorable Excursion (MFE) - Potential Profit', gridcolor='rgba(128, 128, 128, 0.2)'))
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("Upload Market Data to generate the Scalper's Heatmap.")

            st.markdown("---")
            st.subheader("6. Trade Duration vs. Profitability (The 'Hope' Metric)")
            st.markdown("Visualizes how long you hold trades versus how much they pay. If your losing trades cluster to the right of your winning trades, it proves you are holding and hoping instead of cutting losses.")
            
            hope_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
            selected_hope_inst = st.multiselect("Filter Hope Metric by Instrument (leave blank to chart all):", hope_instruments, key="hope_inst_filter")
            
            hope_dates = list(master_df['Date_str'].dropna().unique())[::-1]
            selected_hope_dates = st.multiselect("Filter Hope Metric by Trading Day (leave blank to chart all):", hope_dates, key="hope_date_filter")
            
            dur_df = master_df.copy()
            if selected_hope_inst:
                dur_df = dur_df[dur_df['Instrument'].isin(selected_hope_inst)]
            if selected_hope_dates:
                dur_df = dur_df[dur_df['Date_str'].isin(selected_hope_dates)]
            
            dur_df['Dur_Secs'] = dur_df['Duration'].apply(parse_duration_to_seconds)
            dur_df = dur_df[dur_df['Dur_Secs'] > 0] 
            
            if not dur_df.empty:
                fig_dur = go.Figure()
                
                wins_dur = dur_df[dur_df['Net_PnL'] > 0]
                fig_dur.add_trace(go.Scatter(x=wins_dur['Dur_Secs'], y=wins_dur['Net_PnL'], mode='markers', name='Winning Trades', marker=dict(color='#26a69a', size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')), text=wins_dur['Instrument'] + " | " + wins_dur['Duration']))
                
                loss_dur = dur_df[dur_df['Net_PnL'] <= 0]
                fig_dur.add_trace(go.Scatter(x=loss_dur['Dur_Secs'], y=loss_dur['Net_PnL'], mode='markers', name='Losing Trades', marker=dict(color='#ef5350', size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')), text=loss_dur['Instrument'] + " | " + loss_dur['Duration']))
                
                fig_dur.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(title='Trade Duration (Seconds)', gridcolor='rgba(128, 128, 128, 0.2)'), yaxis=dict(title='Net P&L ($)', gridcolor='rgba(128, 128, 128, 0.2)', tickprefix="$"))
                st.plotly_chart(fig_dur, use_container_width=True)
            else:
                st.info("No duration data available to plot.")

            st.markdown("---")
            st.subheader("7. Tilt Velocity Radar (Time-Between-Trades)")
            st.markdown("Measures the exact time gap between a losing trade's exit and your very next entry. A low win rate on the left side of this chart mathematically proves Revenge Trading.")
            
            tilt_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
            selected_tilt_inst = st.multiselect("Filter Tilt Radar by Instrument (leave blank to chart all):", tilt_instruments, key="tilt_inst_filter")
            
            tilt_dates = list(master_df['Date_str'].dropna().unique())[::-1]
            selected_tilt_dates = st.multiselect("Filter Tilt Radar by Trading Day (leave blank to chart all):", tilt_dates, key="tilt_date_filter")

            tilt_df = master_df.copy().sort_values(by='Datetime').reset_index(drop=True)
            tilt_df['Exit_Datetime'] = pd.to_datetime(tilt_df['Exit_Time'], errors='coerce')
            
            tilt_df['Prev_Net_PnL'] = tilt_df['Net_PnL'].shift(1)
            tilt_df['Prev_Exit'] = tilt_df['Exit_Datetime'].shift(1)
            
            tilt_df['Tilt_Gap_Mins'] = (tilt_df['Datetime'] - tilt_df['Prev_Exit']).dt.total_seconds() / 60.0
            
            tilt_target = tilt_df[(tilt_df['Prev_Net_PnL'] < 0) & (tilt_df['Tilt_Gap_Mins'] > 0) & (tilt_df['Tilt_Gap_Mins'] <= 60)].copy()
            
            if selected_tilt_inst:
                tilt_target = tilt_target[tilt_target['Instrument'].isin(selected_tilt_inst)]
            if selected_tilt_dates:
                tilt_target = tilt_target[tilt_target['Date_str'].isin(selected_tilt_dates)]
            
            if not tilt_target.empty:
                fig_tilt = go.Figure()
                
                tilt_wins = tilt_target[tilt_target['Net_PnL'] > 0]
                fig_tilt.add_trace(go.Scatter(x=tilt_wins['Tilt_Gap_Mins'], y=tilt_wins['Net_PnL'], mode='markers', name='Winning Trades', marker=dict(color='#26a69a', size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')), text=tilt_wins['Instrument']))
                
                tilt_losses = tilt_target[tilt_target['Net_PnL'] <= 0]
                fig_tilt.add_trace(go.Scatter(x=tilt_losses['Tilt_Gap_Mins'], y=tilt_losses['Net_PnL'], mode='markers', name='Losing Trades', marker=dict(color='#ef5350', size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')), text=tilt_losses['Instrument']))
                
                fast_tilt = tilt_target[tilt_target['Tilt_Gap_Mins'] <= 5]
                fast_wr = (len(fast_tilt[fast_tilt['Net_PnL'] > 0]) / len(fast_tilt) * 100) if len(fast_tilt) > 0 else 0
                
                st.markdown(f"**Quick Stat:** Your Win Rate when re-entering within 5 minutes of a loss is **{fast_wr:.1f}%** ({len(fast_tilt)} trades).")
                
                fig_tilt.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(title='Minutes Since Last Losing Trade', gridcolor='rgba(128, 128, 128, 0.2)'), yaxis=dict(title='Net P&L ($)', gridcolor='rgba(128, 128, 128, 0.2)', tickprefix="$"))
                st.plotly_chart(fig_tilt, use_container_width=True)
            else:
                st.info("Not enough sequential data to calculate Tilt Velocity. Keep logging trades!")
                
            st.markdown("---")
            # --- NEW UI: The Scaling Alpha Engine ---
            st.markdown("---")
            st.subheader("8. Scaling Alpha Engine (Efficiency Check)")
            st.markdown("Compares your actual P&L from **overlapping scale-ins** against a simulated baseline: *What if you entered your total position size at your first entry price, and exited everything at your final exit price?*")

            POINT_VALUES = {
                'ES': 50, 'MES': 5, 'NQ': 20, 'MNQ': 2, 'RTY': 50, 'M2K': 5,
                'CL': 1000, 'MCL': 100, 'QM': 500, 'QG': 12.5, 'NG': 10000, 
                'GC': 100, 'MGC': 10, 'YM': 5, 'MYM': 0.5
            }
            
            # --- NEW UI: Localized Scaling Filters ---
            alpha_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
            selected_alpha_inst = st.multiselect("Filter Scaling Alpha by Instrument (leave blank to chart all):", alpha_instruments, key="alpha_inst_filter")
            
            alpha_dates = list(master_df['Date_str'].dropna().unique())[::-1]
            selected_alpha_dates = st.multiselect("Filter Scaling Alpha by Trading Day (leave blank to chart all):", alpha_dates, key="alpha_date_filter")
            # ----------------------------------------

            alpha_df = master_df.copy().sort_values(by='Datetime').reset_index(drop=True)
            
            if selected_alpha_inst:
                alpha_df = alpha_df[alpha_df['Instrument'].isin(selected_alpha_inst)]
            if selected_alpha_dates:
                alpha_df = alpha_df[alpha_df['Date_str'].isin(selected_alpha_dates)]
            
            # --- STRICT OVERLAP MATH ---
            # Convert exit times to datetime for overlap comparison
            alpha_df['Entry_DT'] = pd.to_datetime(alpha_df['Entry_Time'], errors='coerce')
            alpha_df['Exit_DT'] = pd.to_datetime(alpha_df['Exit_Time'], errors='coerce')
            
            # Calculate the furthest exit time seen so far for a given day/instrument/direction
            alpha_df['Max_Exit_So_Far'] = alpha_df.groupby(['Date_str', 'Instrument', 'trade_type'])['Exit_DT'].cummax().shift(1)
            
            # A new campaign starts ONLY if the current entry is AFTER the previous maximum exit
            # (meaning no overlap), or if the instrument/direction/day changes.
            condition = (alpha_df['Entry_DT'] > alpha_df['Max_Exit_So_Far']) | \
                        (alpha_df['Instrument'] != alpha_df['Instrument'].shift(1)) | \
                        (alpha_df['trade_type'] != alpha_df['trade_type'].shift(1)) | \
                        (alpha_df['Date_str'] != alpha_df['Date_str'].shift(1))
                        
            alpha_df['Campaign_ID'] = condition.cumsum()
            
            campaigns = []
            
            for c_id, group in alpha_df.groupby('Campaign_ID'):
                if len(group) > 1: # We ONLY evaluate true overlapping scale-ins
                    actual_net = group['Net_PnL'].sum()
                    true_position_size = group['Qty'].max() 
                    base_comm = group['Commission'].sum()
                    
                    entries = group.sort_values('Entry_DT')
                    first_entry = entries.iloc[0]['Entry_Price']
                    final_exit = group.iloc[-1]['Exit_Price']
                    instrument = group.iloc[0]['Instrument']
                    t_type = group.iloc[0]['trade_type'].upper()
                    
                    # --- NEW MATH: Detect Averaging Down vs Pyramiding ---
                    behavior = "Scale-Out Only"
                    if len(entries['Entry_Time'].unique()) > 1: # They added size later
                        if t_type == 'LONG':
                            if (entries.iloc[1:]['Entry_Price'] < first_entry).any(): behavior = "Averaging Down"
                            else: behavior = "Pyramiding"
                        elif t_type == 'SHORT':
                            if (entries.iloc[1:]['Entry_Price'] > first_entry).any(): behavior = "Averaging Down"
                            else: behavior = "Pyramiding"
                    # -----------------------------------------------------

                    multiplier = 1.0
                    for k in sorted(POINT_VALUES.keys(), key=len, reverse=True):
                        if instrument.startswith(k):
                            multiplier = POINT_VALUES[k]
                            break
                            
                    base_pt_diff = (final_exit - first_entry) if t_type == 'LONG' else (first_entry - final_exit)
                    base_gross = base_pt_diff * true_position_size * multiplier
                    base_net = base_gross - base_comm
                    
                    campaigns.append({
                        'Campaign': f"{instrument} ({t_type}) @ {group.iloc[0]['Datetime'].strftime('%H:%M')} ({len(group)} legs)",
                        'Actual Net': actual_net,
                        'Baseline Net': base_net,
                        'Scaling Alpha': actual_net - base_net,
                        'Behavior': behavior
                    })
                        
            if campaigns:
                camp_df = pd.DataFrame(campaigns)
                total_alpha = camp_df['Scaling Alpha'].sum()
                avg_down_alpha = camp_df[camp_df['Behavior'] == 'Averaging Down']['Scaling Alpha'].sum()
                pyr_alpha = camp_df[camp_df['Behavior'] == 'Pyramiding']['Scaling Alpha'].sum()
                scale_out_alpha = camp_df[camp_df['Behavior'] == 'Scale-Out Only']['Scaling Alpha'].sum()
                
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                col_a1.metric("Total Scaling Alpha", f"${total_alpha:.2f}")
                col_a2.metric("Alpha (Averaging Down)", f"${avg_down_alpha:.2f}", help="Money made/lost specifically when you added to losing positions.")
                col_a3.metric("Alpha (Pyramiding)", f"${pyr_alpha:.2f}", help="Money made/lost specifically when you added to winning positions.")
                col_a4.metric("Alpha (Scale-Out Only)", f"${scale_out_alpha:.2f}", help="Money made/lost when you entered full size and scaled out.")
                
                camp_df = camp_df.sort_values(by='Scaling Alpha').head(20) 
                
                fig_alpha = go.Figure()
                fig_alpha.add_trace(go.Bar(x=camp_df['Campaign'], y=camp_df['Actual Net'], name='Actual Scaled P&L', marker_color='#26a69a'))
                fig_alpha.add_trace(go.Bar(x=camp_df['Campaign'], y=camp_df['Baseline Net'], name='Baseline (1-Shot) P&L', marker_color='rgba(128,128,128,0.4)'))
                
                fig_alpha.update_layout(barmode='group', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(tickprefix="$"))
                st.plotly_chart(fig_alpha, use_container_width=True)
            else:
                st.info("Not enough scaled positions (multiple executions overlapping in time) to calculate Scaling Alpha.")
            # ----------------------------------------

            # --- NEW UI: The Conviction Curve (Size-Induced Panic) ---
            st.markdown("---")
            st.subheader("9. The Conviction Curve (Size-Induced Panic)")
            st.markdown("Plots your Average Exit Efficiency (MFE Capture Rate) against your Position Size. A steep drop-off exposes your psychological volume ceiling.")
            
            if st.toggle("📉 Run Conviction Curve Analysis", key="run_conviction"):
                # --- NEW UI: Localized Conviction Filters ---
                conv_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
                selected_conv_inst = st.multiselect("Filter Conviction Curve by Instrument (leave blank to chart all):", conv_instruments, key="conv_inst_filter")
                
                conv_dates = list(master_df['Date_str'].dropna().unique())[::-1]
                selected_conv_dates = st.multiselect("Filter Conviction Curve by Trading Day (leave blank to chart all):", conv_dates, key="conv_date_filter")
                # --------------------------------------------

                cc_df = master_df.dropna(subset=['Net_PnL', 'Qty']).copy()
                
                if selected_conv_inst:
                    cc_df = cc_df[cc_df['Instrument'].isin(selected_conv_inst)]
                if selected_conv_dates:
                    cc_df = cc_df[cc_df['Date_str'].isin(selected_conv_dates)]
                    
                total_trades = len(cc_df)
                conviction_data = []
                
                if total_trades > 0:
                    my_bar = st.progress(0, text="Crunching MFE data for all historical trades...")
                    
                    for idx, (i, row) in enumerate(cc_df.iterrows()):
                        if idx % 10 == 0:  # Update progress bar every 10 trades
                            my_bar.progress(min(idx / total_trades, 1.0), text=f"Analyzing trade {idx} of {total_trades}...")
                            
                        mfe, mae = calculate_mae_mfe(row['Instrument'], row['Entry_Time'], row['Exit_Time'], row['Entry_Price'], row.get('trade_type', 'Unknown'))
                        
                        if mfe != "N/A" and float(mfe) > 0:
                            t_type = row.get('trade_type', 'Unknown').upper()
                            captured_pts = (row['Exit_Price'] - row['Entry_Price']) if t_type == 'LONG' else (row['Entry_Price'] - row['Exit_Price'])
                            eff = min((captured_pts / float(mfe)) * 100, 100.0) if captured_pts > 0 else 0.0
                            conviction_data.append({'Qty': row['Qty'], 'Efficiency': eff})
                    
                    my_bar.empty() # Hide progress bar when finished
                    
                    if conviction_data:
                        conv_df = pd.DataFrame(conviction_data)
                        grouped_conv = conv_df.groupby('Qty').agg(
                            Avg_Efficiency=('Efficiency', 'mean'),
                            Trade_Count=('Efficiency', 'count')
                        ).reset_index().sort_values('Qty')
                        
                        fig_conv = go.Figure()
                        fig_conv.add_trace(go.Bar(
                            x=grouped_conv['Qty'], 
                            y=grouped_conv['Avg_Efficiency'],
                            text=grouped_conv['Trade_Count'].apply(lambda x: f"n={x}"),
                            textposition='auto',
                            marker_color=['#26a69a' if val >= 50 else '#ef5350' for val in grouped_conv['Avg_Efficiency']],
                            name='Avg Efficiency %'
                        ))
                        
                        fig_conv.update_layout(
                            height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                            xaxis=dict(title='Position Size (Contracts/Shares)', type='category'), 
                            yaxis=dict(title='Average MFE Capture Rate (%)', range=[0, 100])
                        )
                        st.plotly_chart(fig_conv, use_container_width=True)
                    else:
                        st.info("Not enough market data available to calculate MFE efficiencies.")
            # ---------------------------------------------------------

            st.markdown("---")
            st.subheader("10. Monte Carlo Equity Simulator (Risk of Ruin)")
            
            if st.toggle("🧪 Run Monte Carlo Simulator", key="run_mc"):
                mc_df = master_df.dropna(subset=['Net_PnL'])
                if len(mc_df) >= 10:
                    col_mc1, col_mc2 = st.columns([1, 2.5])
                    with col_mc1:
                        st.markdown("**Simulation Parameters**")
                        sim_trades = st.slider("Trades to Simulate (Future Horizon)", min_value=10, max_value=500, value=100, step=10)
                        sim_count = st.slider("Parallel Universes (Simulations)", min_value=100, max_value=2000, value=1000, step=100)
                        risk_threshold = st.number_input("Drawdown Danger Zone ($)", min_value=10.0, value=500.0, step=50.0)
                        
                        historical_pnls = mc_df['Net_PnL'].values
                        sim_data = np.random.choice(historical_pnls, size=(sim_count, sim_trades), replace=True)
                        sim_paths = np.cumsum(sim_data, axis=1)
                        
                        peaks = np.maximum.accumulate(sim_paths, axis=1)
                        drawdowns = peaks - sim_paths
                        max_dds = np.max(drawdowns, axis=1)
                        
                        ruin_probability = (np.sum(max_dds >= risk_threshold) / sim_count) * 100
                        median_ending_pnl = np.median(sim_paths[:, -1])
                        worst_ending_pnl = np.min(sim_paths[:, -1])
                        
                        st.markdown("---")
                        ruin_color = "🔴" if ruin_probability > 20 else "🟡" if ruin_probability > 5 else "🟢"
                        
                        st.metric(f"Risk of -${risk_threshold:.2f} Drawdown", f"{ruin_color} {ruin_probability:.1f}%")
                        st.metric("Median Expected P&L", f"${median_ending_pnl:.2f}")
                        st.metric("Worst Case Scenario", f"${worst_ending_pnl:.2f}")

                    with col_mc2:
                        fig_mc = go.Figure()
                        plot_count = min(sim_count, 150)
                        for i in range(plot_count):
                            fig_mc.add_trace(go.Scatter(y=sim_paths[i], mode='lines', line=dict(width=1, color='rgba(38, 166, 154, 0.05)'), showlegend=False, hoverinfo='skip'))
                        
                        median_path = np.median(sim_paths, axis=0)
                        fig_mc.add_trace(go.Scatter(y=median_path, mode='lines', line=dict(width=3, color='#2196F3'), name='Median Expected Path'))
                        
                        fig_mc.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(title='Future Trade Number'), yaxis=dict(title='Simulated Net P&L ($)', tickprefix="$"))
                        st.plotly_chart(fig_mc, use_container_width=True)
                else:
                    st.info("Log at least 10 valid trades to unlock the Monte Carlo Simulator.")
                    
            # --- NEW UI: The Drawdown Behavior Matrix ---
            st.markdown("---")
            st.subheader("11. The Drawdown Behavior Matrix (In-the-Hole Analytics)")
            st.markdown("Analyzes your position sizing and hold times specifically when your daily P&L is in the red. Exposes desperation, revenge trading, and Martingale sizing.")
            
            if st.toggle("🚨 Run Drawdown Behavior Analysis", key="run_drawdown"):
                # --- NEW UI: Localized Drawdown Filters ---
                dd_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
                selected_dd_inst = st.multiselect("Filter Drawdown Matrix by Instrument (leave blank to chart all):", dd_instruments, key="dd_inst_filter")
                
                dd_dates = list(master_df['Date_str'].dropna().unique())[::-1]
                selected_dd_dates = st.multiselect("Filter Drawdown Matrix by Trading Day (leave blank to chart all):", dd_dates, key="dd_date_filter")
                # ------------------------------------------

                dd_df = master_df.copy().sort_values(by='Datetime').reset_index(drop=True)
                
                # Accurately calculate the exact Daily P&L state BEFORE each trade was taken
                dd_df['Daily_Cum_PnL'] = dd_df.groupby('Date_str')['Net_PnL'].cumsum()
                dd_df['PnL_So_Far'] = dd_df.groupby('Date_str')['Daily_Cum_PnL'].shift(1).fillna(0.0)
                dd_df['Hold_Secs'] = dd_df['Duration'].apply(parse_duration_to_seconds)
                
                # Apply filters AFTER calculating the PnL state to ensure the math stays true to the timeline
                if selected_dd_inst:
                    dd_df = dd_df[dd_df['Instrument'].isin(selected_dd_inst)]
                if selected_dd_dates:
                    dd_df = dd_df[dd_df['Date_str'].isin(selected_dd_dates)]
                    
                if len(dd_df) > 0:
                    red_trades = dd_df[dd_df['PnL_So_Far'] < 0]
                    green_trades = dd_df[dd_df['PnL_So_Far'] >= 0]
                    
                    avg_qty_red = red_trades['Qty'].mean() if len(red_trades) > 0 else 0
                    avg_qty_green = green_trades['Qty'].mean() if len(green_trades) > 0 else 0
                    
                    avg_hold_red = red_trades['Hold_Secs'].mean() if len(red_trades) > 0 else 0
                    avg_hold_green = green_trades['Hold_Secs'].mean() if len(green_trades) > 0 else 0
                    
                    wr_red = (len(red_trades[red_trades['Net_PnL'] > 0]) / len(red_trades) * 100) if len(red_trades) > 0 else 0
                    wr_green = (len(green_trades[green_trades['Net_PnL'] > 0]) / len(green_trades) * 100) if len(green_trades) > 0 else 0
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_dd1, col_dd2, col_dd3 = st.columns(3)
                    col_dd1.metric("Avg Position Size (In the Green)", f"{avg_qty_green:.1f} contracts", f"vs {avg_qty_red:.1f} (In Red)", delta_color="off")
                    col_dd2.metric("Avg Hold Time (In the Green)", f"{format_seconds_to_duration(avg_hold_green)}", f"vs {format_seconds_to_duration(avg_hold_red)} (In Red)", delta_color="off")
                    col_dd3.metric("Win Rate (In the Green)", f"{wr_green:.1f}%", f"vs {wr_red:.1f}% (In Red)", delta_color="off")
                    
                    st.markdown("---")
                    fig_dd = go.Figure()
                    
                    wins = dd_df[dd_df['Net_PnL'] > 0]
                    losses = dd_df[dd_df['Net_PnL'] <= 0]
                    
                    fig_dd.add_trace(go.Scatter(x=wins['PnL_So_Far'], y=wins['Qty'], mode='markers', name='Winning Trades', marker=dict(color='#26a69a', size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')), text=wins['Date_str'] + " | " + wins['Instrument']))
                    fig_dd.add_trace(go.Scatter(x=losses['PnL_So_Far'], y=losses['Qty'], mode='markers', name='Losing Trades', marker=dict(color='#ef5350', size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')), text=losses['Date_str'] + " | " + losses['Instrument']))
                    
                    # Draw the $0 Breakeven Line
                    fig_dd.add_vline(x=0, line_width=2, line_dash="dash", line_color="rgba(255,255,255,0.5)")
                    fig_dd.add_annotation(x=0, y=dd_df['Qty'].max(), text="Daily Breakeven ($0)", showarrow=False, yshift=15, font=dict(color="rgba(255,255,255,0.7)"))
                    
                    fig_dd.update_layout(height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(title='Daily P&L Before Trade Was Taken ($)', tickprefix="$", gridcolor='rgba(128, 128, 128, 0.2)'), yaxis=dict(title='Position Size Executed (Qty)', gridcolor='rgba(128, 128, 128, 0.2)'))
                    
                    st.plotly_chart(fig_dd, use_container_width=True)
                else:
                    st.info("Not enough data to calculate drawdown behavior metrics.")
            # --------------------------------------------------------

            # --- NEW UI: The Chrono-Matrix (2D Time/Day Heatmap) ---
            st.markdown("---")
            st.subheader("12. The Chrono-Matrix (2D Time/Day Heatmap)")
            st.markdown("A visual grid plotting the days of the week against 15-minute time blocks, color-coded by your Net P&L. Mathematically proves your most profitable hours.")
            
            if st.toggle("⏳ Run Chrono-Matrix Analysis", key="run_chrono"):
                
                # --- NEW UI: Localized Chrono Filters ---
                chrono_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
                selected_chrono_inst = st.multiselect("Filter Chrono-Matrix by Instrument (leave blank to chart all):", chrono_instruments, key="chrono_inst_filter")
                
                chrono_dates = list(master_df['Date_str'].dropna().unique())[::-1]
                selected_chrono_dates = st.multiselect("Filter Chrono-Matrix by Trading Day (leave blank to chart all):", chrono_dates, key="chrono_date_filter")
                # ----------------------------------------
                
                chrono_df = master_df.copy()
                
                if selected_chrono_inst:
                    chrono_df = chrono_df[chrono_df['Instrument'].isin(selected_chrono_inst)]
                if selected_chrono_dates:
                    chrono_df = chrono_df[chrono_df['Date_str'].isin(selected_chrono_dates)]
                    
                if not chrono_df.empty:
                    # Extract the Day of Week and the 15-minute Time Block
                    chrono_df['Day_Name'] = chrono_df['Datetime'].dt.day_name()
                    chrono_df['Time_15m'] = chrono_df['Datetime'].dt.floor('15min').dt.time
                    
                    # Group the data to find the total Net P&L for each specific grid square
                    pivot_df = chrono_df.groupby(['Day_Name', 'Time_15m'])['Net_PnL'].sum().reset_index()
                    
                    # Pivot the data into a 2D matrix shape for the heatmap
                    heatmap_data = pivot_df.pivot(index='Day_Name', columns='Time_15m', values='Net_PnL').fillna(0)
                    
                    # Force the Y-Axis to be strictly chronological (Monday -> Friday)
                    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                    available_days = [d for d in days_order if d in heatmap_data.index]
                    heatmap_data = heatmap_data.reindex(available_days)
                    
                    # Format the X-Axis column headers to clean strings
                    heatmap_data.columns = [t.strftime('%H:%M') for t in heatmap_data.columns]
                    
                    # Generate the Custom Plotly Heatmap
                    fig_chrono = go.Figure(data=go.Heatmap(
                        z=heatmap_data.values,
                        x=heatmap_data.columns,
                        y=heatmap_data.index,
                        # Custom Red-to-Green gradient centering exactly at $0
                        colorscale=[[0, '#ef5350'], [0.5, 'rgba(0,0,0,0)'], [1, '#26a69a']],
                        zmid=0,
                        hoverongaps=False,
                        hovertemplate='<b>Day:</b> %{y}<br><b>Time:</b> %{x}<br><b>Net P&L:</b> $%{z:.2f}<extra></extra>'
                    ))
                    
                    fig_chrono.update_layout(
                        height=400,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(title='Time of Day (15-Minute Blocks)', tickangle=-45, gridcolor='rgba(128, 128, 128, 0.1)'),
                        yaxis=dict(title='Day of the Week', autorange='reversed', gridcolor='rgba(128, 128, 128, 0.1)')
                    )
                    
                    st.plotly_chart(fig_chrono, use_container_width=True)
                else:
                    st.info("Not enough data to generate the Chrono-Matrix.")
            # -------------------------------------------------------

            # --- NEW UI: The Overtrading Threshold (Fatigue Matrix) ---
            st.markdown("---")
            st.subheader("13. The Overtrading Threshold (Fatigue Matrix)")
            st.markdown("Sequences your daily executions (Trade #1, Trade #2...) to calculate your Win Rate and profitability for each specific slot. Mathematically pinpoints exactly when decision fatigue sets in.")
            
            if st.toggle("🔋 Run Fatigue Matrix Analysis", key="run_fatigue"):
                
                # --- NEW UI: Localized Fatigue Filters ---
                fatigue_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
                selected_fatigue_inst = st.multiselect("Filter Fatigue Matrix by Instrument (leave blank to chart all):", fatigue_instruments, key="fatigue_inst_filter")
                
                fatigue_dates = list(master_df['Date_str'].dropna().unique())[::-1]
                selected_fatigue_dates = st.multiselect("Filter Fatigue Matrix by Trading Day (leave blank to chart all):", fatigue_dates, key="fatigue_date_filter")
                # -----------------------------------------
                
                fatigue_df = master_df.copy().sort_values(by='Datetime').reset_index(drop=True)
                
                if selected_fatigue_inst:
                    fatigue_df = fatigue_df[fatigue_df['Instrument'].isin(selected_fatigue_inst)]
                if selected_fatigue_dates:
                    fatigue_df = fatigue_df[fatigue_df['Date_str'].isin(selected_fatigue_dates)]
                    
                if not fatigue_df.empty:
                    # Isolate the daily execution sequence (1st trade, 2nd trade, etc.)
                    fatigue_df['Daily_Trade_Number'] = fatigue_df.groupby('Date_str').cumcount() + 1
                    
                    # Aggregate P&L and Win Rate by Execution Number
                    fatigue_stats = fatigue_df.groupby('Daily_Trade_Number').agg(
                        Total_Net_PnL=('Net_PnL', 'sum'),
                        Trade_Count=('Net_PnL', 'count'),
                        Wins=('Net_PnL', lambda x: (x > 0).sum())
                    ).reset_index()
                    
                    fatigue_stats['Win_Rate'] = (fatigue_stats['Wins'] / fatigue_stats['Trade_Count']) * 100
                    
                    fig_fatigue = go.Figure()
                    
                    # Bar Chart for Net P&L (Primary Y-Axis)
                    fig_fatigue.add_trace(go.Bar(
                        x=fatigue_stats['Daily_Trade_Number'], 
                        y=fatigue_stats['Total_Net_PnL'], 
                        name='Total Net P&L',
                        marker_color=['#26a69a' if val >= 0 else '#ef5350' for val in fatigue_stats['Total_Net_PnL']],
                        yaxis='y1'
                    ))
                    
                    # Line Chart for Win Rate (Secondary Y-Axis)
                    fig_fatigue.add_trace(go.Scatter(
                        x=fatigue_stats['Daily_Trade_Number'], 
                        y=fatigue_stats['Win_Rate'], 
                        name='Win Rate %',
                        mode='lines+markers',
                        line=dict(color='#FFD700', width=3),
                        marker=dict(size=8, color='#FFD700', line=dict(width=1, color='DarkSlateGrey')),
                        yaxis='y2'
                    ))
                    
                    fig_fatigue.update_layout(
                        height=450,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(title='Daily Execution Sequence (Trade #)', tickmode='linear', gridcolor='rgba(128, 128, 128, 0.1)'),
                        yaxis=dict(title='Total Net P&L ($)', tickprefix="$", gridcolor='rgba(128, 128, 128, 0.1)'),
                        yaxis2=dict(title='Win Rate (%)', overlaying='y', side='right', range=[0, 105], showgrid=False),
                        hovermode='x unified',
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_fatigue, use_container_width=True)
                    
                    # Generate a quick insight string
                    best_trade_num = fatigue_stats.loc[fatigue_stats['Total_Net_PnL'].idxmax(), 'Daily_Trade_Number']
                    worst_trade_num = fatigue_stats.loc[fatigue_stats['Total_Net_PnL'].idxmin(), 'Daily_Trade_Number']
                    
                    st.markdown(f"**Quick Insight:** Your peak profitability usually occurs on **Trade #{best_trade_num}** of the day. The math shows your decision-making hits rock bottom around **Trade #{worst_trade_num}**.")
                    
                else:
                    st.info("Not enough data to calculate Overtrading Threshold.")
            # -------------------------------------------------------

            # --- NEW UI: The Scratch Autopsy ---
            st.markdown("---")
            st.subheader("14. The \"Scratch\" Autopsy (Opportunity Cost of Anxiety)")
            st.markdown("Isolates your breakeven/scratch trades and calculates their Maximum Favorable (MFE) and Adverse (MAE) Excursions. Proves mathematically if your early exits are saving you from deep losses or choking out massive winners.")
            
            if st.toggle("🔍 Run Scratch Autopsy", key="run_scratch"):
                
                col_filt1, col_filt2 = st.columns(2)
                with col_filt1:
                    scratch_instruments = sorted(list(master_df['Instrument'].dropna().unique()))
                    selected_scratch_inst = st.multiselect("Filter Autopsy by Instrument:", scratch_instruments, key="scratch_inst_filter")
                with col_filt2:
                    scratch_dates = list(master_df['Date_str'].dropna().unique())[::-1]
                    selected_scratch_dates = st.multiselect("Filter Autopsy by Trading Day:", scratch_dates, key="scratch_date_filter")
                
                # Dynamic threshold so you can define what a "Scratch" is based on the instrument
                scratch_limit = st.slider("Define a 'Scratch' Trade ($ PnL Limit)", min_value=1.0, max_value=100.0, value=15.0, step=1.0, help="Trades with a Net P&L between negative and positive this amount will be isolated for autopsy.")
                
                sa_df = master_df.dropna(subset=['Net_PnL', 'Qty']).copy()
                
                if selected_scratch_inst:
                    sa_df = sa_df[sa_df['Instrument'].isin(selected_scratch_inst)]
                if selected_scratch_dates:
                    sa_df = sa_df[sa_df['Date_str'].isin(selected_scratch_dates)]
                    
                # Isolate only the trades that ended near $0
                scratch_trades = sa_df[(sa_df['Net_PnL'] >= -scratch_limit) & (sa_df['Net_PnL'] <= scratch_limit)].copy()
                
                POINT_VALUES = {
                    'ES': 50, 'MES': 5, 'NQ': 20, 'MNQ': 2, 'RTY': 50, 'M2K': 5,
                    'CL': 1000, 'MCL': 100, 'QM': 500, 'QG': 12.5, 'NG': 10000, 
                    'GC': 100, 'MGC': 10, 'YM': 5, 'MYM': 0.5
                }
                
                if len(scratch_trades) > 0:
                    my_bar = st.progress(0, text="Calculating Missed Excursions for scratched trades...")
                    autopsy_data = []
                    total_scratches = len(scratch_trades)
                    
                    for idx, (i, row) in enumerate(scratch_trades.iterrows()):
                        if idx % 5 == 0:
                            my_bar.progress(min(idx / total_scratches, 1.0), text=f"Autopsy in progress: Trade {idx} of {total_scratches}...")
                            
                        mfe, mae = calculate_mae_mfe(row['Instrument'], row['Entry_Time'], row['Exit_Time'], row['Entry_Price'], row.get('trade_type', 'Unknown'))
                        
                        if mfe != "N/A" and mae != "N/A":
                            instrument = row['Instrument']
                            multiplier = 1.0
                            for k in sorted(POINT_VALUES.keys(), key=len, reverse=True):
                                if instrument.startswith(k):
                                    multiplier = POINT_VALUES[k]
                                    break
                                    
                            mfe_dollar = float(mfe) * row['Qty'] * multiplier
                            mae_dollar = float(mae) * row['Qty'] * multiplier
                            
                            autopsy_data.append({
                                'Date': row['Date_str'],
                                'Instrument': instrument,
                                'Actual_PnL': row['Net_PnL'],
                                'Missed_Upside': mfe_dollar,
                                'Saved_Drawdown': mae_dollar
                            })
                    
                    my_bar.empty()
                    
                    if autopsy_data:
                        ad_df = pd.DataFrame(autopsy_data)
                        
                        total_upside = ad_df['Missed_Upside'].sum()
                        total_drawdown = ad_df['Saved_Drawdown'].sum()
                        avg_upside = ad_df['Missed_Upside'].mean()
                        avg_drawdown = ad_df['Saved_Drawdown'].mean()
                        
                        col_sa1, col_sa2, col_sa3 = st.columns(3)
                        col_sa1.metric(f"Total Scratched Trades", f"{len(ad_df)}")
                        col_sa2.metric("Avg Missed Upside (MFE) per Scratch", f"${avg_upside:.2f}", help="The average amount of profit the trade offered before you scratched it.")
                        col_sa3.metric("Avg Heat Avoided (MAE) per Scratch", f"${avg_drawdown:.2f}", help="The average amount of heat you took before scratching.", delta_color="inverse")
                        
                        st.markdown("---")
                        
                        fig_sa = go.Figure()
                        fig_sa.add_trace(go.Bar(name='Missed Upside (Money Left on Table)', x=ad_df.index, y=ad_df['Missed_Upside'], marker_color='#26a69a'))
                        fig_sa.add_trace(go.Bar(name='Heat Avoided (Drawdown Saved)', x=ad_df.index, y=-ad_df['Saved_Drawdown'], marker_color='#ef5350'))
                        
                        fig_sa.update_layout(
                            title='Excursion Profile of Your Scratched Trades',
                            barmode='group',
                            height=400, 
                            plot_bgcolor='rgba(0,0,0,0)', 
                            paper_bgcolor='rgba(0,0,0,0)', 
                            xaxis=dict(title='Scratched Trade Instance', showticklabels=False),
                            yaxis=dict(title='Dollar Amount ($)', tickprefix="$", gridcolor='rgba(128, 128, 128, 0.1)'),
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig_sa, use_container_width=True)
                        
                        st.info(f"**Diagnosis:** By scratching these trades, you left a total of **${total_upside:.2f}** on the table, while saving yourself from **${total_drawdown:.2f}** in potential heat. If the green bar massively outweighs the red, your anxiety is causing you to abandon valid setups prematurely.")
                else:
                    st.info("No scratch trades found within the specified threshold and filters.")
            # -----------------------------------------------

            # --- NEW UI: Automated Edge Combinator ---
            st.markdown("---")
            st.subheader("15. Automated Edge Combinator (A+ Setup Finder)")
            st.markdown("Calculates the Expected Value (EV) of combining specific PA factors to mathematically reveal your highest probability setups.")
            
            if st.toggle("👑 Run Edge Combinator", key="run_edge"):
                pair_stats = {}
                for _, row in master_df.iterrows():
                    if pd.isna(row['confluence_tags']) or not str(row['confluence_tags']).strip():
                        continue
                    tags = [t.strip() for t in str(row['confluence_tags']).split(',') if t.strip()]
                    if len(tags) >= 2:
                        pairs = list(itertools.combinations(sorted(tags), 2))
                        for pair in pairs:
                            if pair not in pair_stats:
                                pair_stats[pair] = {'count': 0, 'wins': 0, 'gross_win': 0.0, 'gross_loss': 0.0}
                            
                            pair_stats[pair]['count'] += 1
                            if row['Net_PnL'] > 0:
                                pair_stats[pair]['wins'] += 1
                                pair_stats[pair]['gross_win'] += row['Net_PnL']
                            elif row['Net_PnL'] <= 0:
                                pair_stats[pair]['gross_loss'] += abs(row['Net_PnL'])
                                
                results = []
                min_trades_required = st.slider("Minimum Trades Required for Statistical Significance", 1, 50, 3, key="edge_min_trades")
                
                for pair, stats in pair_stats.items():
                    count = stats['count']
                    if count >= min_trades_required:
                        wr = stats['wins'] / count
                        lr = 1.0 - wr
                        avg_win = stats['gross_win'] / stats['wins'] if stats['wins'] > 0 else 0.0
                        avg_loss = stats['gross_loss'] / (count - stats['wins']) if (count - stats['wins']) > 0 else 0.0
                        ev = (wr * avg_win) - (lr * avg_loss)
                        
                        results.append({
                            'Confluence Synergy': f"{pair[0]} + {pair[1]}",
                            'Trades': count,
                            'Win Rate': f"{(wr * 100):.1f}%",
                            'Avg Win': f"${avg_win:.2f}",
                            'Avg Loss': f"-${avg_loss:.2f}",
                            'Expected Value (EV)': ev
                        })
                        
                if results:
                    edge_df = pd.DataFrame(results)
                    edge_df = edge_df.sort_values(by='Expected Value (EV)', ascending=False).reset_index(drop=True)
                    edge_df['Expected Value (EV)'] = edge_df['Expected Value (EV)'].apply(lambda x: f"${x:.2f}" if x >= 0 else f"-${abs(x):.2f}")
                    
                    def color_ev(val):
                        color = '#26a69a' if not '-' in str(val) and str(val) != '$0.00' else '#ef5350' if '-' in str(val) else 'gray'
                        return f'color: {color}; font-weight: bold;'
                    
                    st.dataframe(edge_df.style.map(color_ev, subset=['Expected Value (EV)']), use_container_width=True)
                else:
                    st.info(f"No confluence pairs found with at least {min_trades_required} trades. Tag more trades to unlock the Combinator!")

        st.divider()
        st.header("🧠 Reminder Center & Content Vault")
        st.markdown("Filter your historical trades by the psychological and technical lessons they taught you. Use this to instantly generate YouTube script materials or prep for your trading day.")
        
        vault_tags = st.multiselect("Select Lessons to Extract:", LESSON_TAGS)
        
        if vault_tags:
            def has_tag(tag_string, tags_to_find):
                if pd.isna(tag_string) or not tag_string: return False
                row_tags = [t.strip() for t in str(tag_string).split(',')]
                return any(t in row_tags for t in tags_to_find)
                
            vault_df = master_df[master_df['lesson_tags'].apply(lambda x: has_tag(x, vault_tags))]
            
            if vault_df.empty:
                st.info("No trades found matching these specific lessons.")
            else:
                vault_dates = list(vault_df['Date_str'].unique())[::-1]
                selected_vault_dates = st.multiselect("Filter Lessons by Trading Day (leave blank to show all):", vault_dates, key="vault_date_filter")
                
                if selected_vault_dates:
                    vault_df = vault_df[vault_df['Date_str'].isin(selected_vault_dates)]
                
                st.success(f"Extracted {len(vault_df)} flashcards matching your criteria.")
                for _, v_row in vault_df.iterrows():
                    v_color = "🟢" if v_row['Net_PnL'] >= 0 else "🔴"
                    v_pnl_str = f"+${v_row['Net_PnL']:.2f}" if v_row['Net_PnL'] > 0 else f"-${abs(v_row['Net_PnL']):.2f}"
                    v_tags_rendered = " | ".join([f"`{t.strip()}`" for t in str(v_row['lesson_tags']).split(',') if t.strip()])
                    
                    c_tags_rendered = " | ".join([f"`{t.strip()}`" for t in str(v_row['confluence_tags']).split(',') if t.strip()])
                    
                    with st.expander(f"{v_color} {v_row['Date_str']} | {v_row['Instrument']} | {v_pnl_str} | Strategy: {v_row['strategy']}", expanded=False):
                        st.markdown(f"**Tagged Lessons:** {v_tags_rendered}")
                        if c_tags_rendered:
                            st.markdown(f"**PA Confluences:** {c_tags_rendered}")
                        st.markdown("---")
                        
                        col_v1, col_v2 = st.columns([1, 2])
                        with col_v1:
                            v_safe_id = str(v_row['trade_id']).replace("/", "-").replace("\\", "-")
                            v_images = [f for f in os.listdir(IMAGE_DIR) if f.startswith(v_safe_id)]
                            if v_images:
                                st.image(os.path.join(IMAGE_DIR, v_images[0]), caption="Saved Execution Chart", use_container_width=True, output_format="PNG")
                            else:
                                st.info("No manual screenshot attached.")
                        with col_v2:
                            st.markdown(f"**What went good/bad:**\n> {v_row['good_bad']}")
                            st.markdown(f"**How to improve:**\n> {v_row['improve']}")
                            st.markdown(f"**Action Plan:**\n> {v_row['action_plan']}")
                            st.markdown(f"**General Notes:**\n> {v_row['notes']}")
                            
                        st.markdown("---")
                        if st.checkbox("📈 Load Interactive TradingView Chart", key=f"show_chart_vault_{v_row['trade_id']}"):
                            try:
                                trade_dt = pd.to_datetime(v_row['Timestamp'])
                                start_time, end_time = trade_dt - timedelta(hours=16), trade_dt + timedelta(hours=16)
                                market_df = get_market_data(v_row['Instrument'], start_time, end_time)
                                if not market_df.empty:
                                    st.markdown("### 📊 TradingView Interactive Chart")
                                    html_chart = render_tradingview_chart(market_df, v_row['Entry_Time'], v_row['Exit_Time'], v_row.get('trade_type', 'Unknown'))
                                    components.html(html_chart, height=450)
                                else: st.warning("No market data available for this 32-hour window.")
                            except: pass 

        st.divider()

        st.header("📅 Trading Calendar")
        master_df['Month_Year'] = master_df['Datetime'].dt.strftime('%B %Y')
        months = list(master_df['Month_Year'].unique())
        
        current_month_str = datetime.now().strftime('%B %Y')
        default_idx = months.index(current_month_str) if current_month_str in months else len(months) - 1
        selected_month = st.selectbox("Select Month to View", months, index=default_idx)
        month_df = master_df[master_df['Month_Year'] == selected_month].copy()
        month_df['Day'] = month_df['Datetime'].dt.day
        
        month_df['Is_Win'] = (month_df['Net_PnL'] > 0).astype(int)
        daily_stats = month_df.groupby('Day').agg(
            Daily_Net=('Net_PnL', 'sum'), 
            Trade_Count=('Net_PnL', 'count'),
            Win_Count=('Is_Win', 'sum')
        )
        daily_stats['Win_Rate'] = (daily_stats['Win_Count'] / daily_stats['Trade_Count']) * 100
        
        if not month_df.empty:
            sample_date = month_df['Datetime'].iloc[0]
            cal = calendar.monthcalendar(sample_date.date().year, sample_date.date().month)
            days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            header_cols = st.columns(7)
            for i, day_name in enumerate(days_of_week): header_cols[i].markdown(f"<div style='text-align: center; font-weight: bold;'>{day_name}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            for week in cal:
                week_cols = st.columns(7)
                for i, day in enumerate(week):
                    if day == 0: week_cols[i].write("") 
                    elif day in daily_stats.index:
                        net_pnl = daily_stats.loc[day, 'Daily_Net']
                        trades = daily_stats.loc[day, 'Trade_Count']
                        win_rate = daily_stats.loc[day, 'Win_Rate']
                        
                        if net_pnl > 0: week_cols[i].success(f"**{day}** \n+${net_pnl:.2f}  \n{trades} trades  \nWR: {win_rate:.0f}%")
                        elif net_pnl < 0: week_cols[i].error(f"**{day}** \n${net_pnl:.2f}  \n{trades} trades  \nWR: {win_rate:.0f}%")
                        else: week_cols[i].info(f"**{day}** \n$0.00  \n{trades} trades  \nWR: {win_rate:.0f}%")
                    else: week_cols[i].markdown(f"<div style='text-align: center; padding: 10px; color: gray;'><b>{day}</b><br><br><br></div>", unsafe_allow_html=True)
                        
        st.divider()

        st.header("Daily Reviews & Trade Log")
        all_unique_dates = list(master_df['Date_str'].unique())
        
        col_view1, col_view2, col_view3, col_view4 = st.columns(4)
        with col_view1: view_mode = st.selectbox("Trade Log View Range", ["Show Most Recent 3 Days", "Show Specific Date", "Show Specific Month"], index=1)
        with col_view2:
            if view_mode == "Show Specific Date": selected_review_date = st.selectbox("Select Exact Date to Audit", all_unique_dates[::-1])
            elif view_mode == "Show Specific Month": selected_review_month = st.selectbox("Select Exact Month to Audit", list(master_df['Month_Year'].unique())[::-1])
            else: st.empty() 
        with col_view3: outcome_filter = st.selectbox("Filter by Outcome", ["All Trades", "Profitable Only (Gross > $0)", "Losing Only (Gross <= $0)"])
        with col_view4: sort_order = st.selectbox("Sort Trades By", ["Chronological (Time)", "Highest Profit First", "Biggest Loss First"])
            
        dates_to_show = []
        if view_mode == "Show Most Recent 3 Days":
            current_date = datetime.now().date()
            valid_df = master_df[master_df['Datetime'].dt.date <= current_date]
            dates_to_show = list(valid_df['Date_str'].unique())[::-1][:3] if not valid_df.empty else all_unique_dates[::-1][:3]
        elif view_mode == "Show Specific Date": dates_to_show = [selected_review_date]
        elif view_mode == "Show Specific Month":
            dates_to_show = list(master_df[master_df['Month_Year'] == selected_review_month]['Date_str'].unique())[::-1]
            if not dates_to_show: st.info(f"No trades found in {selected_review_month} to display.")

        for date_str in dates_to_show:
            daily_df = master_df[master_df['Date_str'] == date_str].copy()
            
            daily_df = daily_df.sort_values(by='Datetime', ascending=True).reset_index(drop=True)
            daily_df['PnL_So_Far'] = daily_df['Net_PnL'].cumsum().shift(1).fillna(0.0)
            
            d_win_streak, d_max_win_streak = 0, 0
            d_loss_streak, d_max_loss_streak = 0, 0
            
            for pnl in daily_df['Net_PnL']:
                if pnl > 0:
                    d_win_streak += 1
                    d_loss_streak = 0
                    if d_win_streak > d_max_win_streak: d_max_win_streak = d_win_streak
                elif pnl < 0:
                    d_loss_streak += 1
                    d_win_streak = 0
                    if d_loss_streak > d_max_loss_streak: d_max_loss_streak = d_loss_streak
                    
            daily_avg_pnl = daily_df['Net_PnL'].mean() if len(daily_df) > 0 else 0.0
            
            daily_df['Daily_Cum_PnL'] = daily_df['Net_PnL'].cumsum()
            daily_df['Daily_Peak'] = daily_df['Daily_Cum_PnL'].cummax().clip(lower=0.0)
            daily_df['Daily_Drawdown'] = daily_df['Daily_Cum_PnL'] - daily_df['Daily_Peak']
            daily_max_drawdown = daily_df['Daily_Drawdown'].min() if len(daily_df) > 0 else 0.0
            
            daily_longs = daily_df[daily_df['trade_type'].str.upper() == 'LONG']
            daily_shorts = daily_df[daily_df['trade_type'].str.upper() == 'SHORT']
            
            daily_long_wins = len(daily_longs[daily_longs['Net_PnL'] > 0])
            daily_short_wins = len(daily_shorts[daily_shorts['Net_PnL'] > 0])
            
            daily_long_pnl = daily_longs['Net_PnL'].sum()
            daily_short_pnl = daily_shorts['Net_PnL'].sum()
            
            daily_gross = daily_df['P&L'].sum()
            daily_comm = daily_df['Commission'].sum()
            daily_net = daily_df['Net_PnL'].sum()
            daily_gross_profit = daily_df[daily_df['P&L'] > 0]['P&L'].sum()
            daily_gross_loss = abs(daily_df[daily_df['P&L'] < 0]['P&L'].sum())
            daily_pf = "∞" if daily_gross_loss == 0 and daily_gross_profit > 0 else "0.00" if daily_gross_loss == 0 else f"{(daily_gross_profit / daily_gross_loss):.2f}"
            
            daily_total_trades = len(daily_df)
            daily_win_count = len(daily_df[daily_df['P&L'] > 0])
            daily_loss_count = len(daily_df[daily_df['P&L'] <= 0])
            daily_wr = f"{(len(daily_df[daily_df['Net_PnL'] > 0]) / daily_total_trades * 100):.0f}%" if daily_total_trades > 0 else "0%"
            
            daily_winning_trades = daily_df[daily_df['Net_PnL'] > 0]
            daily_losing_trades = daily_df[daily_df['Net_PnL'] < 0]
            daily_max_win = daily_winning_trades['Net_PnL'].max() if not daily_winning_trades.empty else 0.0
            daily_max_loss = daily_losing_trades['Net_PnL'].min() if not daily_losing_trades.empty else 0.0
            
            day_color = "🟢" if daily_net >= 0 else "🔴"
            
            day_title = f"{day_color} {date_str} | Net: \${daily_net:.2f} | WR: {daily_wr} | Best: +\${daily_max_win:.2f} | Worst: -\${abs(daily_max_loss):.2f} | {daily_total_trades} Trades"
            
            with st.expander(day_title, expanded=False):
                st.markdown("### 🎯 Daily Pre-Market & Post-Market Routine")
                col_goal, col_reflection = st.columns(2)
                existing_goal, existing_reflection = get_daily_note_from_db(date_str)
                with col_goal: daily_goal = st.text_area("Pre-Market Goal (What is your focus today?):", value=existing_goal, key=f"goal_{date_str}", height=150)
                with col_reflection: daily_reflection = st.text_area("Post-Market Reflection (Did you execute on your goal?):", value=existing_reflection, key=f"ref_{date_str}", height=150)
                if st.button("Save Daily Routine", key=f"btn_daily_{date_str}"):
                    save_daily_note_to_db(date_str, daily_goal, daily_reflection)
                    st.success("Daily routine saved successfully.")
                
                st.divider()
                st.markdown("### 🧠 Intraday Psychological Stress & Bias")
                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                col_d1.metric("Intraday Max Cons. Wins", f"{d_max_win_streak}")
                col_d2.metric("Intraday Max Cons. Losses", f"{d_max_loss_streak}")
                col_d3.metric("Intraday Max Drawdown", f"-${abs(daily_max_drawdown):.2f}")
                col_d4.metric("Daily Avg Trade P&L", f"${daily_avg_pnl:.2f}" if daily_avg_pnl >= 0 else f"-${abs(daily_avg_pnl):.2f}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_d5, col_d6, col_d7, col_d8 = st.columns(4)
                col_d5.metric("Long Trades Won", f"{daily_long_wins} / {len(daily_longs)}")
                col_d6.metric("Short Trades Won", f"{daily_short_wins} / {len(daily_shorts)}")
                col_d7.metric("Net Long P&L", f"${daily_long_pnl:.2f}" if daily_long_pnl >= 0 else f"-${abs(daily_long_pnl):.2f}")
                col_d8.metric("Net Short P&L", f"${daily_short_pnl:.2f}" if daily_short_pnl >= 0 else f"-${abs(daily_short_pnl):.2f}")
                st.divider()
                
                st.markdown("### 📊 Trade Executions")
                
                display_df = daily_df.copy()
                if outcome_filter == "Profitable Only (Gross > $0)": display_df = display_df[display_df['P&L'] > 0]
                elif outcome_filter == "Losing Only (Gross <= $0)": display_df = display_df[display_df['P&L'] <= 0]
                    
                if sort_order == "Highest Profit First": display_df = display_df.sort_values(by='P&L', ascending=False)
                elif sort_order == "Biggest Loss First": display_df = display_df.sort_values(by='P&L', ascending=True)
                else: display_df = display_df.sort_values(by='Datetime', ascending=True)
                    
                if display_df.empty: st.info("No trades match your current filter settings for this specific day.")
                
                if not display_df.empty:
                    with st.expander("⚡ Bulk Edit Scaled Positions (Group Review)", expanded=False):
                        st.markdown("Select multiple executions below to treat them as a single position. The strategy, tags, notes, and screenshot you provide here will be instantly applied to all selected trades simultaneously.")
                        
                        trade_map = {}
                        for _, row in display_df.iterrows():
                            label = f"{row['trade_type'].upper()} {row['Instrument']} @ {row['Timestamp']} | Net: ${row['Net_PnL']:.2f} (Qty: {row['Qty']})"
                            trade_map[label] = row['trade_id']
                            
                        selected_labels = st.multiselect(
                            "Select Executions to Group:", 
                            options=list(trade_map.keys()),
                            key=f"bulk_sel_{date_str}"
                        )
                        
                        if selected_labels:
                            with st.form(key=f"bulk_form_{date_str}"):
                                col_b1, col_b2 = st.columns([1, 2.5])
                                with col_b1:
                                    bulk_strategy = st.selectbox("Strategy Category", ["Uncategorized", "Trend Continuation", "Reversal break of Trendline", "Buy Low Sell High TR", "Breakout", "Counter Trend"], key=f"b_strat_{date_str}")
                                    bulk_score = st.slider("Execution Score (0=Worst, 10=Perfect)", 0, 10, 5, key=f"b_score_{date_str}")
                                    bulk_tags = st.multiselect("Tag Lessons Learned:", LESSON_TAGS, key=f"b_tags_{date_str}")
                                    bulk_conf = st.multiselect("Price Action Confluences:", CONFLUENCE_TAGS, key=f"b_conf_{date_str}")
                                    st.markdown("---")
                                    bulk_screenshot = st.file_uploader("Attach Screenshot (Applies to ALL)", type=['png', 'jpg', 'jpeg'], key=f"b_img_{date_str}")
                                    
                                with col_b2:
                                    bulk_gb = st.text_area("1. What went good and what went bad?", height=80, key=f"b_gb_{date_str}")
                                    bulk_imp = st.text_area("2. What can I improve?", height=80, key=f"b_imp_{date_str}")
                                    bulk_act = st.text_area("3. How I plan to improve it?", height=80, key=f"b_act_{date_str}")
                                    bulk_notes = st.text_area("Additional Notes / Chart Links:", height=68, key=f"b_notes_{date_str}")
                                    st.markdown("<br><br>", unsafe_allow_html=True)
                                    bulk_submit = st.form_submit_button("💾 Apply Review to All Selected Trades", use_container_width=True)
                                    
                                if bulk_submit:
                                    img_bytes = bulk_screenshot.read() if bulk_screenshot else None
                                    
                                    tags_string = ",".join(bulk_tags)
                                    conf_string = ",".join(bulk_conf)
                                    
                                    for label in selected_labels:
                                        t_id = trade_map[label]
                                        save_trade_note_to_db(t_id, bulk_notes, bulk_score, bulk_gb, bulk_imp, bulk_act, bulk_strategy, tags_string, conf_string)
                                        
                                        if img_bytes is not None:
                                            safe_t_id = str(t_id).replace("/", "-").replace("\\", "-")
                                            for old_img in [f for f in os.listdir(IMAGE_DIR) if f.startswith(safe_t_id)]:
                                                try: os.remove(os.path.join(IMAGE_DIR, old_img))
                                                except: pass
                                            file_path = os.path.join(IMAGE_DIR, f"{safe_t_id}_{bulk_screenshot.name}")
                                            with open(file_path, "wb") as f:
                                                f.write(img_bytes)
                                                
                                        keys_to_clear = [f"strat_{t_id}", f"score_{t_id}", f"tags_{t_id}", f"conf_{t_id}", f"gb_{t_id}", f"imp_{t_id}", f"act_{t_id}", f"gen_{t_id}"]
                                        for k in keys_to_clear:
                                            st.session_state.pop(k, None)
                                                
                                    st.session_state.reset_trigger += 1
                                    
                                    st.success(f"Successfully applied unified review to {len(selected_labels)} executions!")
                                    time.sleep(1)
                                    st.rerun()
                st.divider()
                
                # --- NEW UI: True Pagination for High-Volume Days ---
                total_display_trades = len(display_df)
                max_render = 30
                
                if total_display_trades > max_render:
                    # Create a unique memory key for this specific day's page number
                    page_key = f"page_{date_str}"
                    if page_key not in st.session_state:
                        st.session_state[page_key] = 0
                        
                    current_page = st.session_state[page_key]
                    # Calculate total pages using ceiling division logic
                    total_pages = (total_display_trades + max_render - 1) // max_render
                    
                    # Failsafe: If filters change and the current page no longer exists, reset it
                    if current_page >= total_pages:
                        current_page = max(0, total_pages - 1)
                        st.session_state[page_key] = current_page
                    
                    start_idx = current_page * max_render
                    end_idx = min(start_idx + max_render, total_display_trades)
                    
                    st.info(f"📑 Showing trades {start_idx + 1} to {end_idx} out of {total_display_trades}.")
                    
                    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                    with col_p1:
                        if st.button("⬅️ Previous Page", key=f"prev_{date_str}", use_container_width=True, disabled=(current_page == 0)):
                            st.session_state[page_key] -= 1
                            st.rerun()
                    with col_p2:
                        st.markdown(f"<div style='text-align: center; padding-top: 5px;'><b>Page {current_page + 1} of {total_pages}</b></div>", unsafe_allow_html=True)
                    with col_p3:
                        if st.button("Next Page ➡️", key=f"next_{date_str}", use_container_width=True, disabled=(current_page == total_pages - 1)):
                            st.session_state[page_key] += 1
                            st.rerun()
                            
                    # Slice the dataframe to only render this specific page
                    display_df = display_df.iloc[start_idx:end_idx]
                    st.markdown("<br>", unsafe_allow_html=True)
                # ----------------------------------------------------
                
                for index, row in display_df.iterrows():
                    trade_id, instrument, timestamp = row['trade_id'], row['Instrument'], row['Timestamp']
                    gross_pnl, comm, net_pnl = row['P&L'], row['Commission'], row['Net_PnL']
                    duration, qty, trade_type = row['Duration'], row['Qty'], row.get('trade_type', 'Unknown')
                    entry_time, exit_time = row['Entry_Time'], row['Exit_Time']
                    entry_price, exit_price = row['Entry_Price'], row['Exit_Price']
                    pnl_so_far = row['PnL_So_Far']
                    
                    rt = st.session_state.reset_trigger
                    
                    trade_color = "🟢" if net_pnl >= 0 else "🔴"
                    
                    if net_pnl > 0: net_pnl_colored = f":green[+\${net_pnl:.2f}]"
                    elif net_pnl < 0: net_pnl_colored = f":red[-\${abs(net_pnl):.2f}]"
                    else: net_pnl_colored = "\$0.00"
                        
                    if pnl_so_far > 0: pnl_so_far_colored = f":green[+\${pnl_so_far:.2f}]"
                    elif pnl_so_far < 0: pnl_so_far_colored = f":red[-\${abs(pnl_so_far):.2f}]"
                    else: pnl_so_far_colored = "\$0.00"
                    
                    # --- ADDED QTY TO THE DROPDOWN TITLE ---
                    trade_title = f"{trade_color} {trade_type.upper()} {instrument} @ {timestamp} | Qty: {qty} | Net P&L: {net_pnl_colored} | P&L So Far: {pnl_so_far_colored}"
                    with st.expander(trade_title, expanded=False):
                        with st.form(key=f"review_form_{trade_id}_{rt}"):
                            col_details, col_journal = st.columns([1, 2.5])
                            
                            with col_details:
                                st.write(f"**Instrument:** {instrument}  \n"
                                         f"**Type:** {trade_type}  \n"
                                         f"**Qty:** {qty}  \n"
                                         f"**Duration:** {duration}  \n"
                                         f"  \n"
                                         f"---  \n"
                                         f"**Gross P&L:** \${gross_pnl:.2f}  \n"
                                         f"**Fees:** -\${comm:.2f}  \n"
                                         f"**Net P&L:** {net_pnl_colored}  \n"
                                         f"**PNL So Far:** {pnl_so_far_colored}  \n"
                                         f"  \n"
                                         f"---  \n"
                                         f"**In:** {entry_price} @ {entry_time}  \n"
                                         f"**Out:** {exit_price} @ {exit_time}")
                                
                                mfe_val, mae_val = calculate_mae_mfe(instrument, entry_time, exit_time, entry_price, trade_type)
                                if mfe_val != "N/A": 
                                    st.write(f"**MFE (Max Profit):** +{mfe_val:.2f} pts\n**MAE (Max Heat):** -{mae_val:.2f} pts")
                                    
                                    captured_pts = (exit_price - entry_price) if trade_type.upper() == 'LONG' else (entry_price - exit_price)
                                    if mfe_val > 0 and captured_pts > 0:
                                        eff_score = min((captured_pts / mfe_val) * 100, 100.0)
                                        if eff_score >= 80: eff_badge = "🟢 Sniper"
                                        elif eff_score >= 50: eff_badge = "🟡 Good"
                                        else: eff_badge = "🔴 Left Money on Table"
                                        st.write(f"**Exit Efficiency:** {eff_score:.1f}% ({eff_badge})")
                                    elif mfe_val > 0:
                                        st.write(f"**Exit Efficiency:** 0.0% (🔴 Stopped Out)")
                                        
                                else: st.write("**MFE / MAE:** No market data for window")
                                st.markdown("---")
                                
                                confirm_del_trade = st.checkbox("Confirm Deletion", key=f"conf_trade_{trade_id}_{rt}")
                                del_btn = st.form_submit_button("🗑️ Delete Trade")
                                st.markdown("---")
                                
                                strategy_options = ["Uncategorized", "Trend Continuation", "Reversal break of Trendline", "Buy Low Sell High TR", "Breakout", "Counter Trend"]
                                strat_val = row.get('strategy', 'Uncategorized')
                                if strat_val not in strategy_options: strat_val = "Uncategorized"
                                strategy_choice = st.selectbox("Strategy Category", strategy_options, index=strategy_options.index(strat_val), key=f"strat_{trade_id}_{rt}")
                                score = st.slider("Execution Score (0=Worst, 10=Perfect)", 0, 10, int(row['score']), key=f"score_{trade_id}_{rt}")
                                
                                existing_tags = [t.strip() for t in str(row.get('lesson_tags', '')).split(',') if t.strip() in LESSON_TAGS]
                                selected_tags = st.multiselect("Tag Lessons Learned:", LESSON_TAGS, default=existing_tags, key=f"tags_{trade_id}_{rt}")
                                
                                existing_conf = [t.strip() for t in str(row.get('confluence_tags', '')).split(',') if t.strip() in CONFLUENCE_TAGS]
                                selected_conf = st.multiselect("Price Action Confluences:", CONFLUENCE_TAGS, default=existing_conf, key=f"conf_{trade_id}_{rt}")
                                
                                st.markdown("---")
                                safe_trade_id = str(trade_id).replace("/", "-").replace("\\", "-")
                                screenshot = st.file_uploader("Attach/Replace Manual Screenshot", type=['png', 'jpg', 'jpeg'], key=f"img_{trade_id}_{rt}")
                                
                                existing_images = [f for f in os.listdir(IMAGE_DIR) if f.startswith(safe_trade_id)]
                                if existing_images:
                                    img_path = os.path.join(IMAGE_DIR, existing_images[0])
                                    st.image(img_path, caption="Saved Execution Chart", use_container_width=True, output_format="PNG")
                                    st.markdown(f"**📁 File:**\n`{os.path.abspath(img_path)}`")
                                    
                            with col_journal:
                                good_bad = st.text_area("1. What went good and what went bad on that trade?", value=row['good_bad'], key=f"gb_{trade_id}_{rt}", height=80)
                                improve = st.text_area("2. What can I improve on that trade?", value=row['improve'], key=f"imp_{trade_id}_{rt}", height=80)
                                action_plan = st.text_area("3. How I plan to improve it for the next trade?", value=row['action_plan'], key=f"act_{trade_id}_{rt}", height=80)
                                general_notes = st.text_area("Additional Notes / Chart Links:", value=row['notes'], key=f"gen_{trade_id}_{rt}", height=68)
                                
                                st.markdown("<br><br>", unsafe_allow_html=True)
                                save_btn = st.form_submit_button("Save Trade Review", use_container_width=True)
                                
                        if del_btn:
                            if confirm_del_trade:
                                delete_trade_from_db(trade_id)
                                st.rerun()
                            else:
                                st.error("⚠️ Please check the 'Confirm Deletion' box before clicking Delete.")
                            
                        if save_btn:
                            if screenshot is not None:
                                for old_img in [f for f in os.listdir(IMAGE_DIR) if f.startswith(safe_trade_id)]:
                                    try: os.remove(os.path.join(IMAGE_DIR, old_img))
                                    except: pass
                                file_path = os.path.join(IMAGE_DIR, f"{safe_trade_id}_{screenshot.name}")
                                with open(file_path, "wb") as f: f.write(screenshot.getbuffer())
                                
                            tags_string = ",".join(selected_tags)
                            conf_string = ",".join(selected_conf)
                            
                            save_trade_note_to_db(trade_id, general_notes, score, good_bad, improve, action_plan, strategy_choice, tags_string, conf_string)
                            
                            st.session_state.reset_trigger += 1
                            
                            st.success("Trade review secured in vault!")
                            time.sleep(1)
                            st.rerun()
                            
                        st.markdown("---")
                        if st.checkbox("📈 Load Interactive TradingView Chart", key=f"show_chart_{trade_id}_{rt}"):
                            try:
                                trade_dt = pd.to_datetime(timestamp)
                                start_time, end_time = trade_dt - timedelta(hours=16), trade_dt + timedelta(hours=16)
                                market_df = get_market_data(instrument, start_time, end_time)
                                if not market_df.empty:
                                    st.markdown("### 📊 TradingView Interactive Chart")
                                    html_chart = render_tradingview_chart(market_df, entry_time, exit_time, trade_type)
                                    components.html(html_chart, height=450)
                                else: st.warning("No market data available for this 32-hour window.")
                            except: pass 
                
                st.divider()
                st.markdown("### ⚠️ Data Management")
                confirm_day_del = st.checkbox(f"Confirm deleting all {len(daily_df)} trades on {date_str}", key=f"conf_day_{date_str}")
                if st.button(f"🗑️ Delete All Trades on {date_str}", key=f"del_day_{date_str}"):
                    if confirm_day_del:
                        delete_day_from_db(daily_df['trade_id'].tolist())
                        st.rerun()
                    else:
                        st.error("⚠️ Please check the confirmation box.")

# --- ♻️ The Universal Recycle Bin ---
st.divider()
with st.expander("♻️ Recycle Bin (Restore Deleted Data)", expanded=False):
    st.markdown("All deleted trades, weekly reports, monthly reports, and market data are temporarily held here. You can safely restore them, or permanently empty the trash.")
    
    tab_t, tab_w, tab_m, tab_md = st.tabs(["Deleted Trades", "Deleted Weekly Reports", "Deleted Monthly Reports", "Deleted Market Data"])
    
    with tab_t:
        try:
            conn_bin = sqlite3.connect(DB_FILE)
            bin_df = pd.read_sql_query("SELECT trade_id, instrument, timestamp, pnl FROM trades WHERE is_deleted = 1", conn_bin)
            conn_bin.close()
            if bin_df.empty:
                st.info("No deleted trades.")
            else:
                bin_df['sort_time'] = bin_df['timestamp'].apply(pd.to_datetime, errors='coerce')
                bin_df = bin_df.sort_values(by='sort_time', ascending=False).drop(columns=['sort_time'])
                st.dataframe(bin_df)
                id_to_restore = st.selectbox("Select trade to RESTORE:", bin_df['trade_id'].tolist())
                if st.button("♻️ RESTORE SELECTED TRADE"):
                    restore_trade_from_db(id_to_restore)
                    st.success("Trade safely restored to the vault!")
                    time.sleep(1)
                    st.rerun()
        except: pass

    with tab_w:
        try:
            conn_bin = sqlite3.connect(DB_FILE)
            w_bin_df = pd.read_sql_query("SELECT week_range FROM weekly_history WHERE is_deleted = 1", conn_bin)
            conn_bin.close()
            if w_bin_df.empty:
                st.info("No deleted weekly reports.")
            else:
                st.dataframe(w_bin_df)
                w_to_restore = st.selectbox("Select week to RESTORE:", w_bin_df['week_range'].tolist())
                if st.button("♻️ RESTORE SELECTED WEEK"):
                    restore_weekly_history(w_to_restore)
                    st.success("Weekly report restored!")
                    time.sleep(1)
                    st.rerun()
        except: pass

    with tab_m:
        try:
            conn_bin = sqlite3.connect(DB_FILE)
            m_bin_df = pd.read_sql_query("SELECT month_range FROM monthly_enemy_history WHERE is_deleted = 1", conn_bin)
            conn_bin.close()
            if m_bin_df.empty:
                st.info("No deleted monthly reports.")
            else:
                st.dataframe(m_bin_df)
                m_to_restore = st.selectbox("Select month to RESTORE:", m_bin_df['month_range'].tolist())
                if st.button("♻️ RESTORE SELECTED MONTH"):
                    restore_monthly_enemy_history(m_to_restore)
                    st.success("Monthly report restored!")
                    time.sleep(1)
                    st.rerun()
        except: pass

    with tab_md:
        try:
            conn_bin = sqlite3.connect(DB_FILE)
            md_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM market_data WHERE is_deleted = 1", conn_bin).iloc[0]['cnt']
            conn_bin.close()
            if md_count == 0:
                st.info("No deleted market data.")
            else:
                st.warning(f"There are currently {md_count} rows of deleted market data in the bin.")
                if st.button("♻️ RESTORE ALL MARKET DATA"):
                    restore_market_data()
                    st.success("Market data restored!")
                    time.sleep(1)
                    st.rerun()
        except: pass

    st.markdown("---")
    st.markdown("### Nuclear Option")
    confirm_nuke_bin = st.checkbox("I understand this permanently deletes these items forever.", key="conf_nuke_bin")
    if st.button("🔥 EMPTY ENTIRE RECYCLE BIN", type="primary"):
        if confirm_nuke_bin:
            empty_recycle_bin_db()
            st.error("Recycle bin permanently incinerated. All items deleted forever.")
            time.sleep(1.5)
            st.rerun()
        else:
            st.error("⚠️ Please check the confirmation box.")

# --- The Vault Surgeon ---
st.divider()
with st.expander("🛠️ Vault Surgeon (Emergency Data Extraction)", expanded=False):
    st.markdown("Use this tool to physically delete corrupted trades directly from the SQL database.")
    try:
        conn_surg = sqlite3.connect(DB_FILE)
        raw_db_df = pd.read_sql_query("SELECT trade_id, instrument, timestamp, pnl FROM trades", conn_surg)
        conn_surg.close()
        
        if raw_db_df.empty:
            st.info("The database is currently completely empty.")
        else:
            raw_db_df['sort_time'] = raw_db_df['timestamp'].apply(pd.to_datetime, errors='coerce')
            raw_db_df = raw_db_df.sort_values(by='sort_time', ascending=False).drop(columns=['sort_time']).head(100)
            
            st.markdown("### Raw Database Contents (Top 100 Newest Trades)")
            st.dataframe(raw_db_df)
            
            st.markdown("### Manual Extraction")
            id_to_delete = st.selectbox("Select exact trade_id to physically delete from the vault:", raw_db_df['trade_id'].tolist())
            
            confirm_surg_del = st.checkbox("Confirm physical database deletion", key="conf_surg_del")
            if st.button("🗑️ ERADICATE SELECTED TRADE", type="primary"):
                if confirm_surg_del:
                    conn_surg_del = sqlite3.connect(DB_FILE)
                    conn_surg_del.execute("DELETE FROM trades WHERE trade_id = ?", (id_to_delete,))
                    conn_surg_del.commit()
                    conn_surg_del.close()
                    st.success(f"Trade {id_to_delete} has been permanently destroyed.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⚠️ Please check the confirmation box.")
                
            st.markdown("---")
            st.markdown("### Nuclear Option")
            confirm_nuke_db = st.checkbox("I understand this will wipe the entire trades database.", key="conf_nuke_db")
            if st.button("🚨 DELETE ENTIRE DATABASE", type="primary"):
                if confirm_nuke_db:
                    conn_nuke = sqlite3.connect(DB_FILE)
                    conn_nuke.execute("DELETE FROM trades")
                    conn_nuke.commit()
                    conn_nuke.close()
                    st.error("Database wiped.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⚠️ Please check the confirmation box.")
    except Exception as e:
        st.error(f"Cannot connect to database: {e}")
