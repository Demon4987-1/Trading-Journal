 Hi guys, good time of day.

I've been trading for about 5 years and I understood that I'm not taking it seriously.
I'm reading Brett Steenbarger's book "The Daily Trading Coach", and it gave me the idea to create a custom trading journal.

The reason I'm writing this post is because I forgot that tools like Gemini, Claude etc exist and it could help me in my trading.
Many people still don't use AI to their advantage and even forget that it exists when it can save countless hours and effort.
In trading, it can help whether it's creating a journal or as a talking partner to keep yourself accountable, etc.

I don't have much coding skills so I used to pay a yearly fee for trading journals but I barely used them. It definitely contributed to my lack of success.

This journal is coded for Tradovate prop accounts and I upload the daily CSV file from the "Performance" section, with only these collumns:
symbol _tickSize qty buyPrice sellPrice pnl boughtTimestamp soldTimestamp duration

This journal includes:
- Weekly Improvement Goal (An idea from "The Daily Trading Coach")
- Core Trading Rules
- Dashboard Filters (By instrument and trade score)
- Historical Overview & Equity Curve (zoom in and out and info on each change when hovering the mouse)
- Trading Calendar that shows PNL and Win Rate
- Daily Reviews & Trade Log (You can upload screenshots, there is a TradingView integration and some metrics like profit factor, MAE, MFE etc.)

The TradingView Branch on this repository is the one I use, I branched it to be sure if there are bugs, I can get back to it but for me it works perfectly.

To run it: (you can also ask any chat bot for help with this if struggling)

    Install Python and Streamlit.

    Save the code as dashboard.py.

    Run it using streamlit run dashboard.py.

    Upload Tradovate Performance CSV.
