import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import sqlite3
import calendar
from datetime import datetime, timedelta
import time
import re
import json
import plotly.graph_objects as go

# --- Configuration & Setup ---
st.set_page_config(page_title="Trading Journal Vault", layout="wide")

IMAGE_DIR = "trade_screenshots"
os.makedirs(IMAGE_DIR, exist_ok=True)

# --- Commission Dictionary ---
COMMISSIONS = {
    'ES': 1.75, 'MES': 0.5, 'NQ': 1.75, 'MNQ': 0.5, 'RTY': 1.75, 'M2K': 0.5,
    'NKD': 1.75, 'YM': 1.75, 'MYM': 0.5, 'CL': 2.00, 'MCL': 0.5, 'QM': 2.00,
    'QG': 1.3, 'NG': 2.00, 'PL': 2.3, 'HG': 2.3, 'GC': 2.3, 'MGC': 0.8,
    'SI': 2.3, 'HE': 2.8, 'LE': 2.8, 'ZS': 2.8, 'ZC': 2.8, 'ZL': 2.8,
    'ZM': 2.8, 'ZW': 2.8, 'SIL': 0.8
}

# --- Database Setup & Architecture ---
DB_FILE = "trading_journal.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            instrument TEXT,
            timestamp TEXT,
            pnl REAL,
            duration TEXT,
            qty INTEGER,
            entry_time TEXT,
            exit_time TEXT,
            entry_price REAL,
            exit_price REAL,
            commission REAL,
            net_pnl REAL,
            trade_type TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            trade_id TEXT PRIMARY KEY,
            notes TEXT,
            score INTEGER DEFAULT 0,
            good_bad TEXT,
            improve TEXT,
            action_plan TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_journal (
            date_str TEXT PRIMARY KEY,
            goal TEXT,
            reflection TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_rules (
            id TEXT PRIMARY KEY,
            max_risk TEXT,
            setups TEXT,
            runners TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_goals (
            id TEXT PRIMARY KEY,
            goal TEXT,
            mon_status TEXT, mon_how TEXT, mon_plan TEXT,
            tue_status TEXT, tue_how TEXT, tue_plan TEXT,
            wed_status TEXT, wed_how TEXT, wed_plan TEXT,
            thu_status TEXT, thu_how TEXT, thu_plan TEXT,
            fri_status TEXT, fri_how TEXT, fri_plan TEXT,
            history TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_history (
            week_range TEXT PRIMARY KEY,
            report_text TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            instrument TEXT,
            timestamp TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            PRIMARY KEY (instrument, timestamp)
        )
    ''')
    
    try: cursor.execute("ALTER TABLE trades ADD COLUMN qty INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trades ADD COLUMN entry_time TEXT DEFAULT 'N/A'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trades ADD COLUMN exit_time TEXT DEFAULT 'N/A'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trades ADD COLUMN entry_price REAL DEFAULT 0.0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trades ADD COLUMN exit_price REAL DEFAULT 0.0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trades ADD COLUMN commission REAL DEFAULT 0.0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trades ADD COLUMN net_pnl REAL DEFAULT 0.0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trades ADD COLUMN trade_type TEXT DEFAULT 'Unknown'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE journal_entries ADD COLUMN score INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE journal_entries ADD COLUMN good_bad TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE journal_entries ADD COLUMN improve TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE journal_entries ADD COLUMN action_plan TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trading_rules ADD COLUMN prep_day TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trading_rules ADD COLUMN prep_week TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trading_rules ADD COLUMN max_risk_day TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trading_rules ADD COLUMN position_sizes TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trading_rules ADD COLUMN add_trade TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE trading_rules ADD COLUMN stop_trading TEXT")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE weekly_goals ADD COLUMN mon_grade TEXT DEFAULT '-'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE weekly_goals ADD COLUMN tue_grade TEXT DEFAULT '-'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE weekly_goals ADD COLUMN wed_grade TEXT DEFAULT '-'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE weekly_goals ADD COLUMN thu_grade TEXT DEFAULT '-'")
    except sqlite3.OperationalError: pass 
    try: cursor.execute("ALTER TABLE weekly_goals ADD COLUMN fri_grade TEXT DEFAULT '-'")
    except sqlite3.OperationalError: pass 

    conn.commit()
    conn.close()

def insert_trades_to_db(df):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    inserted_count = 0
    id_counts = {}
    
    for index, row in df.iterrows():
        instrument = row.get('Instrument', 'Unknown')
        timestamp = row['Timestamp']
        pnl = row.get('P&L', 0.0)
        duration = row.get('Duration', 'N/A')
        qty = row.get('Qty', 0)
        entry_time = row.get('Entry_Time', 'N/A')
        exit_time = row.get('Exit_Time', 'N/A')
        entry_price = row.get('Entry_Price', 0.0)
        exit_price = row.get('Exit_Price', 0.0)
        commission = row.get('Commission', 0.0)
        net_pnl = row.get('Net_PnL', pnl)
        trade_type = row.get('trade_type', 'Unknown')
        
        clean_timestamp = str(timestamp).replace(" ", "_").replace(":", "-")
        base_id = f"{instrument}_{clean_timestamp}_{qty}_{entry_price}_{exit_price}"
        
        if base_id in id_counts:
            id_counts[base_id] += 1
        else:
            id_counts[base_id] = 0
            
        trade_id = f"{base_id}_{id_counts[base_id]}"
        
        cursor.execute('''
            REPLACE INTO trades (trade_id, instrument, timestamp, pnl, duration, qty, entry_time, exit_time, entry_price, exit_price, commission, net_pnl, trade_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trade_id, str(instrument), str(timestamp), float(pnl), str(duration), int(qty), str(entry_time), str(exit_time), float(entry_price), float(exit_price), float(commission), float(net_pnl), str(trade_type)))
        
        if cursor.rowcount > 0:
            inserted_count += 1
            
    conn.commit()
    conn.close()
    return inserted_count

def insert_market_data_to_db(df, instrument):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    inserted_count = 0
    
    for index, row in df.iterrows():
        timestamp = str(row['Timestamp'])
        op = float(row['Open'])
        hi = float(row['High'])
        lo = float(row['Low'])
        cl = float(row['Close'])
        
        cursor.execute('''
            REPLACE INTO market_data (instrument, timestamp, open, high, low, close)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (instrument, timestamp, op, hi, lo, cl))
        inserted_count += 1
            
    conn.commit()
    conn.close()
    return inserted_count

def delete_all_market_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM market_data")
    conn.commit()
    conn.close()

def load_all_trades():
    conn = sqlite3.connect(DB_FILE)
    query = '''
        SELECT t.*, j.notes, j.score, j.good_bad, j.improve, j.action_plan
        FROM trades t 
        LEFT JOIN journal_entries j ON t.trade_id = j.trade_id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        df['Datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['Datetime']).copy()
        df = df.sort_values(by='Datetime', ascending=True).reset_index(drop=True)
        
        df = df.rename(columns={
            'instrument': 'Instrument', 
            'timestamp': 'Timestamp', 
            'pnl': 'P&L', 
            'duration': 'Duration',
            'qty': 'Qty',
            'entry_time': 'Entry_Time',
            'exit_time': 'Exit_Time',
            'entry_price': 'Entry_Price',
            'exit_price': 'Exit_Price',
            'commission': 'Commission',
            'net_pnl': 'Net_PnL'
        })
        
        df['notes'] = df['notes'].fillna("")
        df['score'] = df['score'].fillna(0).astype(int)
        df['good_bad'] = df['good_bad'].fillna("")
        df['improve'] = df['improve'].fillna("")
        df['action_plan'] = df['action_plan'].fillna("")
        
    return df

def get_market_data(instrument, start_time, end_time):
    conn = sqlite3.connect(DB_FILE)
    query = '''
        SELECT timestamp, open, high, low, close 
        FROM market_data 
        WHERE instrument = ?
    '''
    df = pd.read_sql_query(query, conn, params=(instrument,))
    conn.close()
    
    if not df.empty:
        df['Datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['Datetime'] = df['Datetime'].dt.tz_localize(None) 
        df = df.dropna(subset=['Datetime'])
        
        mask = (df['Datetime'] >= start_time) & (df['Datetime'] <= end_time)
        df = df.loc[mask].sort_values(by='Datetime')
    return df

def delete_trade_from_db(trade_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trades WHERE trade_id = ?", (trade_id,))
    conn.commit()
    conn.close()

def delete_day_from_db(trade_ids):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for tid in trade_ids:
        cursor.execute("DELETE FROM trades WHERE trade_id = ?", (tid,))
    conn.commit()
    conn.close()

def save_trade_note_to_db(trade_id, notes, score, good_bad, improve, action_plan):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        REPLACE INTO journal_entries (trade_id, notes, score, good_bad, improve, action_plan)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (trade_id, notes, score, good_bad, improve, action_plan))
    conn.commit()
    conn.close()

def save_daily_note_to_db(date_str, goal, reflection):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        REPLACE INTO daily_journal (date_str, goal, reflection)
        VALUES (?, ?, ?)
    ''', (date_str, goal, reflection))
    conn.commit()
    conn.close()

def get_daily_note_from_db(date_str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT goal, reflection FROM daily_journal WHERE date_str = ?', (date_str,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    return "", ""

def save_trading_rules(prep_day, prep_week, max_risk_trade, max_risk_day, setups, position_sizes, add_trade, stop_trading):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        REPLACE INTO trading_rules (
            id, prep_day, prep_week, max_risk, max_risk_day, setups, position_sizes, add_trade, stop_trading
        )
        VALUES ('global', ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (prep_day, prep_week, max_risk_trade, max_risk_day, setups, position_sizes, add_trade, stop_trading))
    conn.commit()
    conn.close()

def get_trading_rules():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT prep_day, prep_week, max_risk, max_risk_day, setups, position_sizes, add_trade, stop_trading 
        FROM trading_rules WHERE id = "global"
    ''')
    result = cursor.fetchone()
    conn.close()
    if result:
        return tuple(val if val is not None else "" for val in result)
    return ("", "", "", "", "", "", "", "")

def save_weekly_goals(goal, mon_s, mon_h, mon_p, mon_g, tue_s, tue_h, tue_p, tue_g, wed_s, wed_h, wed_p, wed_g, thu_s, thu_h, thu_p, thu_g, fri_s, fri_h, fri_p, fri_g, history):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        REPLACE INTO weekly_goals (
            id, goal, 
            mon_status, mon_how, mon_plan, mon_grade,
            tue_status, tue_how, tue_plan, tue_grade,
            wed_status, wed_how, wed_plan, wed_grade,
            thu_status, thu_how, thu_plan, thu_grade,
            fri_status, fri_how, fri_plan, fri_grade,
            history
        ) VALUES ('global', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (goal, mon_s, mon_h, mon_p, mon_g, tue_s, tue_h, tue_p, tue_g, wed_s, wed_h, wed_p, wed_g, thu_s, thu_h, thu_p, thu_g, fri_s, fri_h, fri_p, fri_g, history))
    conn.commit()
    conn.close()

def get_weekly_goals():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT goal, 
               mon_status, mon_how, mon_plan, mon_grade,
               tue_status, tue_how, tue_plan, tue_grade,
               wed_status, wed_how, wed_plan, wed_grade,
               thu_status, thu_how, thu_plan, thu_grade,
               fri_status, fri_how, fri_plan, fri_grade,
               history 
        FROM weekly_goals WHERE id = "global"
    ''')
    result = cursor.fetchone()
    conn.close()
    if result:
        return tuple(val if val is not None else "" for val in result)
    return ("", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "N/A", "", "", "-", "")

def save_weekly_history(week_range, report_text):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO weekly_history (week_range, report_text) VALUES (?, ?)", (week_range, report_text))
    conn.commit()
    conn.close()

def get_weekly_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT week_range, report_text FROM weekly_history ORDER BY week_range DESC")
    result = cursor.fetchall()
    conn.close()
    return result

def delete_weekly_history(week_range):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM weekly_history WHERE week_range = ?", (week_range,))
    conn.commit()
    conn.close()

init_db()

# --- Bulletproof Data Cleaning Engine ---
def force_float(val):
    if pd.isna(val): return 0.0
    val_str = str(val)
    is_negative = '(' in val_str or '-' in val_str
    num_str = re.sub(r'[^\d\.]', '', val_str)
    if not num_str: return 0.0
    try:
        val_float = float(num_str)
        return -val_float if is_negative else val_float
    except:
        return 0.0

def clean_and_prepare_data(df):
    col_mapping = {}
    upper_cols = {col: str(col).strip().upper() for col in df.columns}
    
    for orig_col, clean_col in upper_cols.items():
        clean_col_compact = str(clean_col).replace(" ", "").replace("_", "").replace("&", "").replace("/", "").replace(".", "")
        
        if clean_col_compact in ['SYMBOL', 'CONTRACT', 'PRODUCT', 'INSTRUMENT']:
            col_mapping[orig_col] = 'Instrument'
        elif clean_col_compact in ['DURATION', 'TRADEDURATION']:
            col_mapping[orig_col] = 'Duration'
        elif clean_col_compact in ['PNL', 'NETPL', 'TOTALPL', 'NETPNL', 'PROFITLOSS', 'PL', 'PROFIT', 'GROSSPL', 'GROSSPNL']:
            col_mapping[orig_col] = 'P&L'
        elif clean_col_compact in ['QTY', 'QUANTITY', 'SIZE', 'CONTRACTS', 'VOLUME']:
            col_mapping[orig_col] = 'Qty'
        elif clean_col_compact in ['BOUGHTTIMESTAMP', 'ENTRYTIME', 'OPENTIME', 'BUYTIME', 'INTIME']:
            col_mapping[orig_col] = 'Entry_Time'
        elif clean_col_compact in ['SOLDTIMESTAMP', 'EXITTIME', 'CLOSETIME', 'SELLTIME', 'OUTTIME']:
            col_mapping[orig_col] = 'Exit_Time'
        elif clean_col_compact in ['BUYPRICE', 'ENTRYPRICE', 'OPENPRICE', 'AVGENTRY']:
            col_mapping[orig_col] = 'Entry_Price'
        elif clean_col_compact in ['SELLPRICE', 'EXITPRICE', 'CLOSEPRICE', 'AVGEXIT']:
            col_mapping[orig_col] = 'Exit_Price'
        elif clean_col_compact in ['DATETIME', 'TIME', 'DATE', 'FILLTIME', 'TIMESTAMP', 'TRADEDATE']:
            if 'Timestamp' not in col_mapping.values():
                col_mapping[orig_col] = 'Timestamp'

    df = df.rename(columns=col_mapping)
    
    if 'Entry_Time' in df.columns:
        df['Timestamp'] = df['Entry_Time']
    elif 'Exit_Time' in df.columns:
        df['Timestamp'] = df['Exit_Time']
        
    if 'Timestamp' not in df.columns:
        st.error("Error: Could not find any Date/Time columns.")
        return pd.DataFrame()
        
    if 'Instrument' not in df.columns: df['Instrument'] = 'Unknown'
    if 'Duration' not in df.columns: df['Duration'] = 'N/A'
    
    if 'Qty' not in df.columns: df['Qty'] = 0
    else: df['Qty'] = df['Qty'].apply(force_float).astype(int)

    if 'P&L' not in df.columns: df['P&L'] = 0.0
    else: df['P&L'] = df['P&L'].apply(force_float)

    for price_col in ['Entry_Price', 'Exit_Price']:
        if price_col not in df.columns: df[price_col] = 0.0
        else: df[price_col] = df[price_col].apply(force_float)
            
    if 'Entry_Time' not in df.columns: df['Entry_Time'] = df['Timestamp']
    if 'Exit_Time' not in df.columns: df['Exit_Time'] = df['Timestamp']

    df['trade_type'] = 'Long'
    if 'Entry_Time' in df.columns and 'Exit_Time' in df.columns:
        dt_entry = pd.to_datetime(df['Entry_Time'], errors='coerce')
        dt_exit = pd.to_datetime(df['Exit_Time'], errors='coerce')
        is_short = dt_entry > dt_exit
        df.loc[is_short, 'trade_type'] = 'Short'
        df.loc[is_short, ['Entry_Time', 'Exit_Time']] = df.loc[is_short, ['Exit_Time', 'Entry_Time']].values
        if 'Entry_Price' in df.columns and 'Exit_Price' in df.columns:
            df.loc[is_short, ['Entry_Price', 'Exit_Price']] = df.loc[is_short, ['Exit_Price', 'Entry_Price']].values

    df = df.dropna(subset=['Timestamp']).copy()
    
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
        if req not in df.columns:
            st.error(f"Missing required OHLCV column: {req}")
            return pd.DataFrame()
            
    df = df.dropna(subset=['Timestamp']).copy()
    
    clean_time = df['Timestamp'].astype(str).str.replace('T', ' ', regex=False).str.replace(r'(\+|-)\d{2}:\d{2}$|Z$', '', regex=True)
    df['Timestamp'] = pd.to_datetime(clean_time, errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    df = df.dropna(subset=['Timestamp'])
    
    for col in ['Open', 'High', 'Low', 'Close']:
        df[col] = df[col].apply(force_float)
    return df

def render_tradingview_chart(market_df, entry_time_str, exit_time_str, trade_type):
    market_df = market_df.drop_duplicates(subset=['Datetime']).sort_values(by='Datetime')
    
    valid_times = []
    candles = []
    for _, row in market_df.iterrows():
        unix_time = int(row['Datetime'].timestamp())
        valid_times.append(unix_time)
        candles.append({
            "time": unix_time,
            "open": row['open'],
            "high": row['high'],
            "low": row['low'],
            "close": row['close']
        })
        
    markers = []
    if entry_time_str != 'N/A' and exit_time_str != 'N/A' and valid_times:
        dt_in = pd.to_datetime(entry_time_str).replace(tzinfo=None)
        dt_out = pd.to_datetime(exit_time_str).replace(tzinfo=None)
        
        unix_in = int(dt_in.timestamp())
        unix_out = int(dt_out.timestamp())
        
        if unix_in not in valid_times:
            unix_in = min(valid_times, key=lambda x: abs(x - unix_in))
        if unix_out not in valid_times:
            unix_out = min(valid_times, key=lambda x: abs(x - unix_out))
            
        in_color = "#2196F3" if trade_type == "Long" else "#E91E63"
        out_color = "#E91E63" if trade_type == "Long" else "#2196F3"
        
        raw_markers = [
            {"time": unix_in, "position": "belowBar", "color": in_color, "shape": "arrowUp", "text": "In"},
            {"time": unix_out, "position": "aboveBar", "color": out_color, "shape": "arrowDown", "text": "Out"}
        ]
        markers = sorted(raw_markers, key=lambda x: x["time"])
        
    candles_json = json.dumps(candles)
    markers_json = json.dumps(markers)
    
    html_template = f"""
    <div id="tvchart" style="width: 100%; height: 400px; background-color: #131722;"></div>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        try {{
            const chart = LightweightCharts.createChart(document.getElementById('tvchart'), {{
                autoSize: true, 
                layout: {{ 
                    background: {{ type: 'solid', color: '#131722' }}, 
                    textColor: '#d1d4dc' 
                }},
                grid: {{ 
                    vertLines: {{ color: '#2b2b43' }}, 
                    horzLines: {{ color: '#2b2b43' }} 
                }},
                timeScale: {{ timeVisible: true, secondsVisible: false }},
            }});
            
            const candleSeries = chart.addCandlestickSeries({{
                upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
                wickUpColor: '#26a69a', wickDownColor: '#ef5350'
            }});
            
            const data = {candles_json};
            candleSeries.setData(data);
            
            const markers = {markers_json};
            if (markers.length > 0) {{
                candleSeries.setMarkers(markers);
            }}
            
            chart.timeScale().fitContent();
        }} catch (error) {{
            document.getElementById('tvchart').innerHTML = "<div style='color:red; font-weight:bold; padding:20px; border:1px solid red;'>Chart Rendering Error: " + error.message + "</div>";
        }}
    </script>
    """
    return html_template

# --- Main Dashboard ---
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
                    st.success(f"Successfully processed! Added {new_trades} trades. (Gross P&L Found: ${total_pnl_found:.2f})")
                    time.sleep(1.5)
                    st.rerun()

with col_up2:
    with st.expander("📈 Upload TradingView Market Data (OHLCV)", expanded=False):
        st.markdown("Upload a 1-minute OHLCV CSV from TradingView to generate interactive charts.")
        ohlcv_instrument = st.text_input("Enter Instrument Name exactly as traded (e.g., MNQM6):")
        ohlcv_file = st.file_uploader("Upload TradingView Data (CSV)", type=['csv'], key="ohlcv")
        if ohlcv_file is not None and ohlcv_instrument:
            if st.button("Process & Save Market Data"):
                raw_ohlcv = pd.read_csv(ohlcv_file)
                clean_ohlcv = clean_ohlcv_data(raw_ohlcv)
                if not clean_ohlcv.empty:
                    rows = insert_market_data_to_db(clean_ohlcv, ohlcv_instrument.upper())
                    st.success(f"Successfully processed {rows} minutes of market data for {ohlcv_instrument.upper()}!")
        
        st.markdown("---")
        if st.button("🗑️ Clear All Saved Market Data", use_container_width=True):
            delete_all_market_data()
            st.success("All historical market data has been permanently erased from your vault!")
            time.sleep(1.5)
            st.rerun()

st.divider()

st.header("🎯 Weekly Improvement Goal")
wg_data = get_weekly_goals()
(wg_goal, 
 mon_s, mon_h, mon_p, mon_g,
 tue_s, tue_h, tue_p, tue_g,
 wed_s, wed_h, wed_p, wed_g,
 thu_s, thu_h, thu_p, thu_g,
 fri_s, fri_h, fri_p, fri_g,
 legacy_history) = wg_data

status_options = ["N/A", "Yes", "No"]
grade_options = ["-", "A", "B", "C", "D", "F"]

new_wg_goal = st.text_area("Weekly goal that I plan to improve on and focus on for the week:", value=wg_goal, height=100)

st.markdown("<br>", unsafe_allow_html=True)
day_col1, day_col2, day_col3, day_col4, day_col5 = st.columns(5)

with day_col1:
    st.markdown("<div style='text-align: center; font-weight: bold; font-size: 1.2em;'>Monday</div>", unsafe_allow_html=True)
    new_mon_s = st.radio("Did I follow the goal?", status_options, index=status_options.index(mon_s) if mon_s in status_options else 0, key="mon_s", horizontal=True)
    new_mon_g = st.selectbox("Grade", grade_options, index=grade_options.index(mon_g) if mon_g in grade_options else 0, key="mon_g")
    new_mon_h = st.text_area("How did I follow or not follow this goal?", value=mon_h, key="mon_h", height=100)
    new_mon_p = st.text_area("What do I plan to do to continue following up on this goal?", value=mon_p, key="mon_p", height=100)

with day_col2:
    st.markdown("<div style='text-align: center; font-weight: bold; font-size: 1.2em;'>Tuesday</div>", unsafe_allow_html=True)
    new_tue_s = st.radio("Did I follow the goal?", status_options, index=status_options.index(tue_s) if tue_s in status_options else 0, key="tue_s", horizontal=True)
    new_tue_g = st.selectbox("Grade", grade_options, index=grade_options.index(tue_g) if tue_g in grade_options else 0, key="tue_g")
    new_tue_h = st.text_area("How did I follow or not follow this goal?", value=tue_h, key="tue_h", height=100)
    new_tue_p = st.text_area("What do I plan to do to continue following up on this goal?", value=tue_p, key="tue_p", height=100)

with day_col3:
    st.markdown("<div style='text-align: center; font-weight: bold; font-size: 1.2em;'>Wednesday</div>", unsafe_allow_html=True)
    new_wed_s = st.radio("Did I follow the goal?", status_options, index=status_options.index(wed_s) if wed_s in status_options else 0, key="wed_s", horizontal=True)
    new_wed_g = st.selectbox("Grade", grade_options, index=grade_options.index(wed_g) if wed_g in grade_options else 0, key="wed_g")
    new_wed_h = st.text_area("How did I follow or not follow this goal?", value=wed_h, key="wed_h", height=100)
    new_wed_p = st.text_area("What do I plan to do to continue following up on this goal?", value=wed_p, key="wed_p", height=100)

with day_col4:
    st.markdown("<div style='text-align: center; font-weight: bold; font-size: 1.2em;'>Thursday</div>", unsafe_allow_html=True)
    new_thu_s = st.radio("Did I follow the goal?", status_options, index=status_options.index(thu_s) if thu_s in status_options else 0, key="thu_s", horizontal=True)
    new_thu_g = st.selectbox("Grade", grade_options, index=grade_options.index(thu_g) if thu_g in grade_options else 0, key="thu_g")
    new_thu_h = st.text_area("How did I follow or not follow this goal?", value=thu_h, key="thu_h", height=100)
    new_thu_p = st.text_area("What do I plan to do to continue following up on this goal?", value=thu_p, key="thu_p", height=100)

with day_col5:
    st.markdown("<div style='text-align: center; font-weight: bold; font-size: 1.2em;'>Friday</div>", unsafe_allow_html=True)
    new_fri_s = st.radio("Did I follow the goal?", status_options, index=status_options.index(fri_s) if fri_s in status_options else 0, key="fri_s", horizontal=True)
    new_fri_g = st.selectbox("Grade", grade_options, index=grade_options.index(fri_g) if fri_g in grade_options else 0, key="fri_g")
    new_fri_h = st.text_area("How did I follow or not follow this goal?", value=fri_h, key="fri_h", height=100)
    new_fri_p = st.text_area("What do I plan to do to continue following up on this goal?", value=fri_p, key="fri_p", height=100)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Save Current Weekly Goal Inputs", use_container_width=True):
    save_weekly_goals(new_wg_goal, new_mon_s, new_mon_h, new_mon_p, new_mon_g, new_tue_s, new_tue_h, new_tue_p, new_tue_g, new_wed_s, new_wed_h, new_wed_p, new_wed_g, new_thu_s, new_thu_h, new_thu_p, new_thu_g, new_fri_s, new_fri_h, new_fri_p, new_fri_g, legacy_history)
    st.success("Weekly tracking successfully saved to vault!")

st.divider()

st.markdown("### 🗄️ Archive Week to History Report Card")
col_arch1, col_arch2 = st.columns([2, 1])

with col_arch1:
    week_date_range = st.text_input("Enter Date Range to save this week (e.g., 06.04.2026 - 10.04.2026):")
    
with col_arch2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Archive to History", use_container_width=True):
        if week_date_range:
            report = f"The goal for the week was:\n- {new_wg_goal}\n\n"
            report += f"Monday - {new_mon_s} - {new_mon_g}\n"
            report += f"Tuesday - {new_tue_s} - {new_tue_g}\n"
            report += f"Wednesday - {new_wed_s} - {new_wed_g}\n"
            report += f"Thursday - {new_thu_s} - {new_thu_g}\n"
            report += f"Friday - {new_fri_s} - {new_fri_g}\n"
            
            save_weekly_history(week_date_range, report)
            st.success("Archived to History successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Please type a Date Range first.")

st.markdown("### 📚 Weekly Report Cards History")
history_records = get_weekly_history()

if not history_records:
    st.info("No report cards saved yet. Fill out the date range above and click Archive to create your first report card.")
else:
    for w_range, r_text in history_records:
        with st.expander(f"Week: {w_range}", expanded=False):
            st.text(r_text)
            if st.button(f"🗑️ Delete this Report Card", key=f"del_hist_{w_range}"):
                delete_weekly_history(w_range)
                st.rerun()

st.divider()

with st.expander("📜 My Trading Rules & Master Plan", expanded=False):
    st.markdown("### Core Trading Rules")
    
    rule_data = get_trading_rules()
    (existing_prep_day, existing_prep_week, existing_risk_trade, existing_risk_day, 
     existing_setups, existing_position_sizes, existing_add_trade, existing_stop_trading) = rule_data
    
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
    st.header("Dashboard Filters")
    col_filt1, col_filt2 = st.columns(2)
    
    with col_filt1:
        instrument_list = sorted(list(master_df['Instrument'].dropna().unique()))
        selected_instruments = st.multiselect("Filter by Instrument (leave blank to show all)", instrument_list)
        if selected_instruments:
            master_df = master_df[master_df['Instrument'].isin(selected_instruments)]
            
    with col_filt2:
        min_score, max_score = st.slider("Filter by Trade Score", 0, 10, (0, 10))
        master_df = master_df[(master_df['score'] >= min_score) & (master_df['score'] <= max_score)]
            
    st.divider()
    
    if master_df.empty:
        st.warning("No trades match your current filters.")
    else:
        st.header("Historical Overview & Equity Curve")
        
        total_gross = master_df['P&L'].sum()
        total_commissions = master_df['Commission'].sum()
        total_net = master_df['Net_PnL'].sum()
        total_trades = len(master_df)
        
        total_gross_profit = master_df[master_df['P&L'] > 0]['P&L'].sum()
        total_gross_loss = abs(master_df[master_df['P&L'] < 0]['P&L'].sum())
        
        if total_gross_loss == 0:
            all_time_pf = "∞" if total_gross_profit > 0 else "0.00"
        else:
            all_time_pf = f"{(total_gross_profit / total_gross_loss):.2f}"
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Gross P&L", f"${total_gross:.2f}")
        col2.metric("Commissions", f"-${total_commissions:.2f}")
        col3.metric("Net P&L", f"${total_net:.2f}")
        col4.metric("Win Rate", f"{(len(master_df[master_df['Net_PnL'] > 0]) / total_trades * 100):.1f}%" if total_trades > 0 else "0%")
        col5.metric("Profit Factor", all_time_pf)

        st.subheader("Cumulative Net P&L")
        master_df['Cumulative Net P&L'] = master_df['Net_PnL'].cumsum()
        
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(
            x=master_df['Datetime'], 
            y=master_df['Cumulative Net P&L'], 
            mode='lines',
            fill='tozeroy',
            line=dict(color='#26a69a', width=3),
            fillcolor='rgba(38, 166, 154, 0.1)',
            name='Cumulative P&L'
        ))
        
        fig_equity.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(
                type='date',
                rangebreaks=[
                    dict(bounds=["sat", "sun"])
                ]
            ),
            yaxis=dict(tickprefix="$"),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig_equity.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
        fig_equity.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
        
        st.plotly_chart(fig_equity, use_container_width=True)

        st.divider()

        st.header("📅 Trading Calendar")
        master_df['Month_Year'] = master_df['Datetime'].dt.strftime('%B %Y')
        months = master_df['Month_Year'].unique()
        selected_month = st.selectbox("Select Month to View", months, index=len(months)-1)
        
        month_df = master_df[master_df['Month_Year'] == selected_month].copy()
        month_df['Day'] = month_df['Datetime'].dt.day
        
        daily_stats = month_df.groupby('Day').agg(
            Daily_Net=('Net_PnL', 'sum'),
            Trade_Count=('Net_PnL', 'count')
        )
        
        sample_date = month_df['Datetime'].iloc[0]
        year_num, month_num = sample_date.date().year, sample_date.date().month
        
        cal = calendar.monthcalendar(year_num, month_num)
        days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        header_cols = st.columns(7)
        for i, day_name in enumerate(days_of_week):
            header_cols[i].markdown(f"<div style='text-align: center; font-weight: bold;'>{day_name}</div>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
            
        for week in cal:
            week_cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    week_cols[i].write("") 
                else:
                    if day in daily_stats.index:
                        net_pnl = daily_stats.loc[day, 'Daily_Net']
                        trades = daily_stats.loc[day, 'Trade_Count']
                        if net_pnl > 0:
                            week_cols[i].success(f"**{day}** \n+${net_pnl:.2f}  \n{trades} trades")
                        elif net_pnl < 0:
                            week_cols[i].error(f"**{day}** \n${net_pnl:.2f}  \n{trades} trades")
                        else:
                            week_cols[i].info(f"**{day}** \n$0.00  \n{trades} trades")
                    else:
                        week_cols[i].markdown(f"<div style='text-align: center; padding: 10px; color: gray;'><b>{day}</b><br><br><br></div>", unsafe_allow_html=True)
                        
        st.divider()

        st.header("Daily Reviews & Trade Log")
        
        master_df['Date_str'] = master_df['Datetime'].dt.strftime('%A, %B %d, %Y')
        unique_dates = master_df['Date_str'].unique()
        
        for date_str in reversed(unique_dates):
            daily_df = master_df[master_df['Date_str'] == date_str]
            
            daily_gross = daily_df['P&L'].sum()
            daily_comm = daily_df['Commission'].sum()
            daily_net = daily_df['Net_PnL'].sum()
            
            daily_gross_profit = daily_df[daily_df['P&L'] > 0]['P&L'].sum()
            daily_gross_loss = abs(daily_df[daily_df['P&L'] < 0]['P&L'].sum())
            
            if daily_gross_loss == 0:
                daily_pf = "∞" if daily_gross_profit > 0 else "0.00"
            else:
                daily_pf = f"{(daily_gross_profit / daily_gross_loss):.2f}"
            
            day_color = "🟢" if daily_net >= 0 else "🔴"
            
            with st.expander(f"{day_color} {date_str} | Net P&L: ${daily_net:.2f} (Gross: ${daily_gross:.2f}, Fees: ${daily_comm:.2f}, PF: {daily_pf}) | {len(daily_df)} Trades", expanded=False):
                
                st.markdown("### 🎯 Daily Pre-Market & Post-Market Routine")
                col_goal, col_reflection = st.columns(2)
                
                existing_goal, existing_reflection = get_daily_note_from_db(date_str)
                
                with col_goal:
                    daily_goal = st.text_area("Pre-Market Goal (What is your focus today?):", value=existing_goal, key=f"goal_{date_str}", height=150)
                with col_reflection:
                    daily_reflection = st.text_area("Post-Market Reflection (Did you execute on your goal?):", value=existing_reflection, key=f"ref_{date_str}", height=150)
                
                if st.button("Save Daily Routine", key=f"btn_daily_{date_str}"):
                    save_daily_note_to_db(date_str, daily_goal, daily_reflection)
                    st.success("Daily routine saved successfully.")
                
                st.divider()
                st.markdown("### 📊 Trade Executions")
                
                for index, row in daily_df.iterrows():
                    trade_id = row['trade_id']
                    instrument = row['Instrument']
                    timestamp = row['Timestamp']
                    gross_pnl = row['P&L']
                    comm = row['Commission']
                    net_pnl = row['Net_PnL']
                    
                    duration = row['Duration']
                    qty = row['Qty']
                    entry_time = row['Entry_Time']
                    exit_time = row['Exit_Time']
                    entry_price = row['Entry_Price']
                    exit_price = row['Exit_Price']
                    trade_type = row.get('trade_type', 'Unknown')
                    
                    trade_color = "🟢" if net_pnl >= 0 else "🔴"
                    
                    with st.container(border=True):
                        st.markdown(f"**{trade_color} {trade_type.upper()} Trade at {timestamp}**")
                        
                        col_details, col_journal = st.columns([1, 2.5])
                        
                        with col_details:
                            st.write(f"**Instrument:** {instrument}")
                            st.write(f"**Type:** {trade_type}")
                            st.write(f"**Qty:** {qty}")
                            st.write(f"**Duration:** {duration}")
                            st.markdown("---")
                            st.write(f"**Gross P&L:** ${gross_pnl:.2f}")
                            st.write(f"**Fees:** -${comm:.2f}")
                            st.write(f"**Net P&L:** ${net_pnl:.2f}")
                            st.markdown("---")
                            st.write(f"**In:** {entry_price} @ {entry_time}")
                            st.write(f"**Out:** {exit_price} @ {exit_time}")
                            st.markdown("---")
                            
                            if st.button("🗑️ Delete Trade", key=f"del_trade_{trade_id}"):
                                delete_trade_from_db(trade_id)
                                st.rerun()
                                
                            st.markdown("---")
                            score_val = row['score']
                            score = st.slider("Execution Score (0=Worst, 10=Perfect)", 0, 10, int(score_val), key=f"score_{trade_id}")
                            st.markdown("---")
                            
                            safe_trade_id = str(trade_id).replace("/", "-").replace("\\", "-")
                            
                            try:
                                trade_dt = pd.to_datetime(timestamp)
                                start_time = trade_dt - timedelta(hours=12)
                                end_time = trade_dt + timedelta(hours=12)
                                market_df = get_market_data(instrument, start_time, end_time)
                                
                                if not market_df.empty:
                                    st.markdown("### 📊 TradingView Interactive Chart")
                                    html_chart = render_tradingview_chart(market_df, entry_time, exit_time, trade_type)
                                    components.html(html_chart, height=420)
                            except Exception as e:
                                pass 
                                
                            screenshot = st.file_uploader("Attach/Replace Manual Screenshot", type=['png', 'jpg', 'jpeg'], key=f"img_{trade_id}")
                            if screenshot is not None:
                                for old_img in [f for f in os.listdir(IMAGE_DIR) if f.startswith(safe_trade_id)]:
                                    try: os.remove(os.path.join(IMAGE_DIR, old_img))
                                    except: pass
                                    
                                file_path = os.path.join(IMAGE_DIR, f"{safe_trade_id}_{screenshot.name}")
                                with open(file_path, "wb") as f:
                                    f.write(screenshot.getbuffer())
                                    
                                original_file_path = os.path.join(IMAGE_DIR, screenshot.name)
                                if os.path.exists(original_file_path) and os.path.abspath(original_file_path) != os.path.abspath(file_path):
                                    try: os.remove(original_file_path)
                                    except: pass

                                st.success("Image successfully moved and attached!")
                                st.image(screenshot, caption="Execution Chart", use_container_width=True, output_format="PNG")
                                
                                absolute_path = os.path.abspath(file_path)
                                st.markdown(f"**📁 Full Resolution Raw File:**\n`{absolute_path}`")
                                
                            else:
                                existing_images = [f for f in os.listdir(IMAGE_DIR) if f.startswith(safe_trade_id)]
                                if existing_images:
                                    img_path = os.path.join(IMAGE_DIR, existing_images[0])
                                    st.image(img_path, caption="Saved Execution Chart", use_container_width=True, output_format="PNG")
                                    
                                    absolute_path = os.path.abspath(img_path)
                                    st.markdown(f"**📁 Full Resolution Raw File:**\n`{absolute_path}`")
                                
                        with col_journal:
                            good_bad = st.text_area(
                                "1. What went good and what went bad on that trade?", 
                                value=row['good_bad'], 
                                key=f"gb_{trade_id}",
                                height=80
                            )
                            improve = st.text_area(
                                "2. What can I improve on that trade?", 
                                value=row['improve'], 
                                key=f"imp_{trade_id}",
                                height=80
                            )
                            action_plan = st.text_area(
                                "3. How I plan to improve it for the next trade?", 
                                value=row['action_plan'], 
                                key=f"act_{trade_id}",
                                height=80
                            )
                            
                            general_notes = st.text_area("Additional Notes / Chart Links:", value=row['notes'], key=f"gen_{trade_id}", height=68)
                            
                            if st.button("Save Trade Review", key=f"btn_trade_{trade_id}", use_container_width=True):
                                save_trade_note_to_db(trade_id, general_notes, score, good_bad, improve, action_plan)
                                st.success("Trade review secured in vault!")
                
                st.divider()
                st.markdown("### ⚠️ Data Management")
                if st.button(f"🗑️ Delete All Trades on {date_str}", key=f"del_day_{date_str}"):
                    trade_ids_to_delete = daily_df['trade_id'].tolist()
                    delete_day_from_db(trade_ids_to_delete)
                    st.rerun()
