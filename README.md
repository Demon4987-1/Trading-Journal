Hi guys, good time of day.

I've been trading for about 5 years and I understood that I'm not taking it seriously. I'm reading Brett Steenbarger's book "The Daily Trading Coach", and it gave me the idea to create a custom trading journal.

The reason I'm writing this post is because I forgot that tools like Gemini, Claude etc exist and it could help me in my trading. Many people still don't use AI to their advantage and even forget that it exists when it can save countless hours and effort. In trading, it can help whether it's creating a journal or as a talking partner to keep yourself accountable, etc.

I don't have much coding skills so I used to pay a yearly fee for trading journals but I barely used them. It definitely contributed to my lack of success.

This journal is coded for Tradovate prop accounts and I upload the daily CSV file from the "Performance" section, with only these collumns: symbol _tickSize qty buyPrice sellPrice pnl boughtTimestamp soldTimestamp duration

Here is a breakdown of the main features I’ve implemented:

📊 **Core Analytics & Data Processing**

Automated Import: Drag-and-drop Tradovate CSV uploads that automatically calculate Net P&L, strict commission tracking, and trade duration.

Performance Dashboard: Tracks total Equity Curve, Win Rate, Profit Factor, Gross Winners/Losers, and Best/Worst trades.

Time & Instrument Heatmaps: Automatically visualizes performance by Time of Day (15-min blocks), Day of the Week, and specific Instruments.

Strategy Tracking: Categorizes trades by setup (e.g., Breakout, Counter Trend) and tracks Expectancy, Win Rate, and Average Win/Loss strictly per strategy.

⚙️ **Advanced Trade Mechanics**

MAE / MFE Engine: Imports raw TradingView OHLCV data (1-min or 15-sec) to automatically calculate the Max Adverse Excursion (Heat) and Max Favorable Excursion (Potential Profit) for every individual execution.

The Scalper’s Heatmap: A dedicated 2D scatter plot plotting MAE vs. MFE across all trades. Allows you to mathematically visualize where your stop-losses should be based on real heat taken. Filterable by specific instruments and trading days.

"PNL So Far" Watermark: Every trade log displays the exact chronological Net P&L of the day right before that trade was taken. Instantly exposes whether a bad trade was caused by being up big (cocky) or down big (revenge/tilt).

Interactive Charts: Generates an embedded, interactive Lightweight TradingView chart directly inside the specific trade's log, plotting the exact entry and exit markers.

🧠 **Psychology & Discipline Engine**

Reminder Center & Content Vault: Allows tagging trades with specific human errors (e.g., FOMO, Over Sizing, Counter Trend Stubbornness). A dedicated vault filters the database to generate "Flashcards" of these exact trades so you can study your psychological leaks (or prep video content).

Monthly Enemy Tracker: A specialized module to define a core psychological "enemy" for the month, track its effect on your trading/life, and grade your progress week by week before archiving it to history.

Weekly Goals & Master Rules: Dedicated sections for your overarching trading rules, max risk limits, and weekly graded improvement goals.

Deep Trade Journaling: Form-buffered text areas for Good/Bad analysis, Improvement plans, Execution Scoring (1-10), and manual chart screenshot uploads.

🛡️ **Data Safety**

Recycle Bin Architecture: Every delete button (trades, days, market data, weekly reports) uses a "Soft Delete" safety switch. Data goes to a built-in Recycle Bin where it can be fully restored or permanently incinerated.

----------------------------------------------------------------------------------------------------------------------------------------------------
**Instructions**
To run it: (you can also ask any chat bot for help with this if struggling) Since this runs entirely on your own machine, none of your trading data is ever sent to the cloud. Here is how to get it running in 3 minutes:

Step 1: Get Python & Setup your Folder Make sure you have Python installed on your computer. Create a new folder on your desktop called Trading_Journal (or whatever you want).

Step 2: Save the Code Open a text editor (like VS Code, or even Notepad), paste the entire Python script I shared, and save it inside that folder as dashboard.py.

Step 3: Install the Required Libraries Open your computer's Terminal or Command Prompt, navigate to your new folder, and install the three required external libraries by running this exact command: (without the ")

"
Bash

pip install streamlit pandas plotly
"

(Note: SQLite and the other modules are already built into Python natively!)

Step 4: Launch the Vault Once the installation finishes, run this command in your terminal to start the engine: (without the ")

"
Bash

streamlit run dashboard.py
"

Step 5: Start Journaling A local web browser tab will instantly pop up. The first time you run it, the Python script will automatically build your encrypted SQLite database (trading_journal.db) and the image folder right next to your code.

Just expand the "Upload New Trades" tab, drop in your raw Tradovate CSV file, and the dashboard will instantly populate!

**How to add market data:**
1) Go to tradingview and get the 1 minute chart of your instrument loaded, go backwards to load as many candles as you want.
2) Besides the "Layout" menu click on the dropdown arrow and select "Download Chart Data"
3) Download in "ISO Time" format
4) In the tab of market data in the journal, upload the file and write the exact name of the ticker (i.e MNQM6) that the data corresponds to and click on save
5) The Tradingview intergration should be working in the bottom section of the individual trade reviews.
