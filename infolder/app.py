import os
import base64
from io import BytesIO
import io

import random
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, apology2, login_required, lookup, usd

import pandas_datareader.data as web
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import datetime
from datetime import date,timedelta
from matplotlib.animation import FuncAnimation
today = date.today()

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db_path = os.path.join(os.path.dirname(__file__), "finance.db")
db = SQL(f"sqlite:///{db_path}")

# Trading fees configuration
FREE_TRADES = 5  # First 5 trades are free
TRADE_FEE = 5.00  # $5 per trade after free trades


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def get_trade_count(user_id):
    """Get the number of trades a user has made"""
    result = db.execute("SELECT COUNT(*) as count FROM transactions WHERE user_id = ?", user_id)
    return result[0]["count"] if result else 0


def calculate_fee(user_id):
    """Calculate trading fee based on number of trades"""
    trade_count = get_trade_count(user_id)
    if trade_count < FREE_TRADES:
        return 0
    return TRADE_FEE


@app.route("/")
def first():

    return render_template("first.html")


@app.route("/plot", methods=["POST","GET"])
@login_required

def plot():
    fig = create_figure()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

def create_figure():
    Start = date.today() - timedelta(365)
    Start.strftime('%Y-%m-%d')

    End = date.today() + timedelta(2)
    End.strftime('%Y-%m-%d')
    symbol=session['symbol']
    def closing_price(d):
        Asset = pd.DataFrame(yf.download(symbol, start=Start,end=End)['Adj Close'])
        return Asset

    Stoku = closing_price('Asset')

    plt.style.use('seaborn-colorblind')
    fig = plt.figure()
    ax = plt.axes()
    ax.set_facecolor('grey')
    plt.plot(Stoku)
    plt.xlabel("Date")
    plt.ylabel("Stock Price in Dollars")

    return fig

    '''
    what is left is to put this within the quote page as well as add colmn names as well as add prices of the graph to make it pretty
    also figure out how to make it responsive for every input of ticker we enter'''

@app.route("/welcome",methods=["POST" , "GET"])
def welcome():
    return render_template("welcome.html")

@app.route("/site", methods=["POST","GET"])
@login_required
def site():
    symbol=session['symbol']
    return redirect("https://finance.yahoo.com/quote/{}/".format(symbol))

@app.route("/index")
@login_required
def index():
    user_id = session["user_id"]
    stocks = db.execute("SELECT symbol, name, price, SUM(shares) as shares FROM transactions WHERE user_id =? GROUP BY symbol", user_id )
    cash= db.execute("SELECT cash FROM users WHERE id= ?", user_id)[0]['cash']

    total_cash_stocks = 0
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            stock["name"] = quote["name"]
            stock["price"] = quote["price"]
            stock["total"] = stock["price"] * stock["shares"]
            total_cash_stocks = total_cash_stocks + stock["total"]

    total_cash = total_cash_stocks + cash
    return render_template(
        "index_new.html", stocks=stocks, cash=cash, total_cash=total_cash
    )



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        stock = lookup(symbol)
        user_id= session["user_id"]

        if not symbol:
            return apology("Please enter a symbol")
        if not stock:
            return apology("Invalid symbol")

        stock_name= stock["name"]
        stock_price= stock["price"]
        user_cash = db.execute("SELECT cash FROM users WHERE id=?", user_id)[0]['cash']

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Shares must be an integer!")

        if shares <= 0:
            return apology("Shares should be positive")

        # Calculate trading fee
        fee = calculate_fee(user_id)
        trade_count = get_trade_count(user_id)

        # Calculate total cost including fee
        totstock_price = stock_price * shares
        total_cost = totstock_price + fee

        if user_cash < total_cost:
            if fee > 0:
                return apology(f"Insufficient funds! Cost: ${totstock_price:.2f} + ${fee:.2f} fee = ${total_cost:.2f}")
            return apology("Insufficient funds!")

        # Update user cash (deduct stock cost + fee)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash - total_cost, user_id)

        # Record transaction
        db.execute("INSERT INTO transactions(user_id, name, shares, price, type, symbol) VALUES (?,?,?,?,?,?)",
            user_id, stock_name, shares, stock_price, 'buy', symbol)

        # Flash appropriate message
        if trade_count == 0:
            flash(f"🎉 Congratulations on your first trade! ({FREE_TRADES - 1} free trades remaining)")
        elif trade_count < FREE_TRADES - 1:
            flash(f"✅ Bought {shares} shares of {symbol}! ({FREE_TRADES - trade_count - 1} free trades remaining)")
        elif trade_count == FREE_TRADES - 1:
            flash(f"✅ Bought {shares} shares of {symbol}! (This was your last free trade. ${TRADE_FEE} fee applies from now on)")
        else:
            flash(f"✅ Bought {shares} shares of {symbol}! (Fee: ${fee:.2f})")

        return redirect('/index')
    else:
        # Check if symbol provided in query string
        symbol = request.args.get('symbol')
        fee = calculate_fee(session["user_id"])
        trade_count = get_trade_count(session["user_id"])
        return render_template("buy.html",
                             prefill_symbol=symbol,
                             fee_amount=fee,
                             free_trades_remaining=max(0, FREE_TRADES - trade_count))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session['user_id']
    transactions= db.execute("SELECT type,symbol,price,shares,time FROM transactions WHERE user_id=?",user_id)
    return render_template("history.html",transactions=transactions,usd=usd)


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    password= request.form.get("password")
    username= request.form.get("username")
    if request.method == "POST":

        if not username:
            return apology2("Missing Username")

        elif not password:
            return apology2("Missing Password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology2("invalid username or password")

        session["user_id"] = rows[0]["id"]
        return redirect("/index")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/index")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get('symbol').upper()
        session['symbol']= symbol

        if not symbol:
            return apology("Please enter a symbol")

        stock = lookup(symbol)

        if not stock:
            return apology("Symbol does not exist")

        return render_template("quote_result.html", stock=stock)

    else:
        # Check if symbol provided in query string
        symbol = request.args.get('symbol')
        if symbol:
            stock = lookup(symbol.upper())
            if stock:
                session['symbol'] = symbol.upper()
                return render_template("quote_result.html", stock=stock)
        return render_template("quote_new.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        user_name = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        rows = db.execute("SELECT * FROM users WHERE username = ?", user_name)

        if not user_name:
            return apology2("missing username", 400)

        elif len(rows) != 0:
            return apology2("username taken", 400)

        elif len(password) <= 5:
            return apology2("password too short",400)

        elif not password:
            return apology2("missing password", 400)

        elif not request.form.get("confirmation"):
            return apology2("provide a confirmation", 400)

        elif not password == confirmation:
            return apology2("passwords do not match", 400)

        else:
            hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?) ", user_name, hash,)
            return redirect('/index')
    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        user_id = session["user_id"]

        try:
            shares = int(request.form.get("shares"))
            if shares < 1:
                return apology("shares must be a positive integer")
        except ValueError:
            return apology("shares must be an integer")
        if not symbol:
            return apology("missing symbol")

        stocks = db.execute(
            "SELECT SUM(shares) as shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol;",
            user_id,
            symbol,
        )

        if not stocks or shares > stocks[0]["shares"]:
            return apology("You don't have this number of shares")

        # Calculate trading fee
        fee = calculate_fee(user_id)
        trade_count = get_trade_count(user_id)

        price = lookup(symbol)["price"]
        shares_value = price * shares
        proceeds = shares_value - fee  # Deduct fee from proceeds
        item_name = lookup(symbol)['name']

        # Record transaction
        db.execute(
            "INSERT INTO transactions (user_id, name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)",
            user_id,
            item_name,
            -shares,
            price,
            "sell",
            symbol
        )

        # Update cash (add proceeds after fee)
        db.execute(
            "UPDATE users SET cash = cash + ? WHERE id = ?",
            proceeds,
            user_id,
        )

        # Flash appropriate message
        if fee > 0:
            flash(f"✅ Sold {shares} shares of {symbol} for ${shares_value:.2f} (Fee: ${fee:.2f}, Net: ${proceeds:.2f})")
        else:
            flash(f"✅ Sold {shares} shares of {symbol} for ${shares_value:.2f}! ({FREE_TRADES - trade_count - 1} free trades remaining)")

        return redirect("/index")
    else:
        stocks = db.execute(
            "SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol",
            session["user_id"],
        )
        fee = calculate_fee(session["user_id"])
        trade_count = get_trade_count(session["user_id"])

        # Filter out stocks with 0 shares
        user_stocks = []
        for stock in stocks:
            total_shares = db.execute(
                "SELECT SUM(shares) as shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol",
                session["user_id"], stock["symbol"]
            )[0]["shares"]
            if total_shares > 0:
                user_stocks.append(stock)

        return render_template("sell.html",
                             stocks=user_stocks,
                             fee_amount=fee,
                             free_trades_remaining=max(0, FREE_TRADES - trade_count))


@app.route("/learn")
@login_required
def learn():
    """Educational content page"""
    fee = calculate_fee(session["user_id"])
    return render_template("learn.html", fee_amount=fee, free_trades=FREE_TRADES)


@app.route("/api/stock-history/<symbol>/<period>")
@login_required
def stock_history(symbol, period):
    """API endpoint to get real stock history data from yfinance"""
    import json

    # Map period to yfinance period and interval for granularity
    period_interval_map = {
        '1D': ('1d', '5m'),      # 1 day with 5-minute intervals
        '5D': ('5d', '30m'),     # 5 days with 30-minute intervals
        '1M': ('1mo', '1d'),     # 1 month with daily data
        '3M': ('3mo', '1d'),     # 3 months with daily data
        '6M': ('6mo', '1d'),     # 6 months with daily data
        '1Y': ('1y', '1wk'),     # 1 year with weekly data
        '5Y': ('5y', '1wk'),     # 5 years with weekly data
        'MAX': ('max', '1mo')    # Max with monthly data
    }

    yf_period, yf_interval = period_interval_map.get(period, ('1y', '1d'))

    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            return json.dumps({'error': 'No data found'}), 404

        # Format data for Chart.js with OHLC data for candlesticks
        labels = []
        prices = []
        ohlc_data = []
        timestamps = []  # Store actual timestamps for matching trades

        for idx, (date, row) in enumerate(hist.iterrows()):
            # Store the actual timestamp (convert to ISO format for JavaScript)
            timestamps.append(date.isoformat())

            # Format label based on interval
            if yf_interval in ['1m', '2m', '5m', '15m', '30m', '60m', '90m']:
                label = date.strftime('%H:%M')
            elif yf_interval == '1d':
                label = date.strftime('%m/%d')
            elif yf_interval == '1wk':
                label = date.strftime('%m/%d/%y')
            else:
                label = date.strftime('%Y-%m')

            labels.append(label)
            prices.append(float(row['Close']))

            # OHLC data for candlestick charts - use index for x-axis
            ohlc_data.append({
                'x': idx,  # Use numeric index instead of string label
                'o': float(row['Open']),
                'h': float(row['High']),
                'l': float(row['Low']),
                'c': float(row['Close'])
            })

        return json.dumps({
            'labels': labels,
            'prices': prices,
            'ohlc': ohlc_data,
            'timestamps': timestamps  # Include actual timestamps for trade matching
        })
    except Exception as e:
        return json.dumps({'error': str(e)}), 500


@app.route("/api/stock-news/<symbol>")
@login_required
def stock_news(symbol):
    """API endpoint to get news for a stock - tries yfinance then falls back to scraping"""
    import json
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime
    import time

    try:
        # Method 1: Try yfinance first
        stock = yf.Ticker(symbol)
        news = stock.news

        print(f"DEBUG: yfinance returned {len(news) if news else 0} news items for {symbol}")

        news_items = []

        if news and len(news) > 0:
            for item in news[:10]:
                # Safely extract thumbnail URL
                thumbnail_url = ''
                try:
                    if 'thumbnail' in item and item['thumbnail']:
                        if isinstance(item['thumbnail'], dict):
                            resolutions = item['thumbnail'].get('resolutions', [])
                            if resolutions and len(resolutions) > 0:
                                thumbnail_url = resolutions[0].get('url', '')
                        elif isinstance(item['thumbnail'], str):
                            thumbnail_url = item['thumbnail']
                except:
                    pass

                # Extract publication time
                published_time = item.get('providerPublishTime', 0)

                title = item.get('title', '')
                publisher = item.get('publisher', 'Unknown')
                link = item.get('link', '#')

                # Only add if we have a real title
                if title and title != 'No title':
                    news_items.append({
                        'title': title,
                        'publisher': publisher,
                        'link': link,
                        'published': published_time,
                        'thumbnail': thumbnail_url
                    })

        # Method 2: If yfinance didn't work well, scrape Yahoo Finance
        if len(news_items) < 3:
            print(f"DEBUG: Falling back to web scraping for {symbol}")
            url = f'https://finance.yahoo.com/quote/{symbol}/news'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Find news items (Yahoo Finance structure)
                    news_articles = soup.find_all(['li', 'div'], class_=lambda x: x and ('stream-item' in x or 'news-item' in x))[:10]

                    for article in news_articles:
                        try:
                            title_elem = article.find(['h3', 'a'], class_=lambda x: x and 'title' in str(x).lower())
                            if not title_elem:
                                title_elem = article.find('a')

                            if title_elem:
                                title = title_elem.get_text().strip()
                                link = title_elem.get('href', '#')
                                if link and not link.startswith('http'):
                                    link = f'https://finance.yahoo.com{link}'

                                # Get publisher and time
                                publisher_elem = article.find(['span', 'div'], class_=lambda x: x and 'provider' in str(x).lower())
                                publisher = publisher_elem.get_text().strip() if publisher_elem else 'Yahoo Finance'

                                # Get thumbnail
                                img_elem = article.find('img')
                                thumbnail = img_elem.get('src', '') if img_elem else ''

                                if title and len(title) > 10:  # Valid title
                                    news_items.append({
                                        'title': title,
                                        'publisher': publisher,
                                        'link': link,
                                        'published': int(time.time()),  # Current time as fallback
                                        'thumbnail': thumbnail
                                    })
                        except Exception as e:
                            print(f"DEBUG: Error parsing article: {e}")
                            continue
            except Exception as e:
                print(f"DEBUG: Error scraping news: {e}")

        print(f"DEBUG: Returning {len(news_items)} news items")
        return json.dumps({'news': news_items})

    except Exception as e:
        print(f"DEBUG: Error fetching news: {str(e)}")
        import traceback
        traceback.print_exc()
        return json.dumps({'error': str(e)}), 500


@app.route("/api/user-trades/<symbol>")
@login_required
def user_trades(symbol):
    """API endpoint to get user's trades for a specific stock with individual P&L"""
    import json
    from datetime import datetime

    try:
        user_id = session["user_id"]

        # Get all buy transactions for this stock (only positive shares = buys)
        transactions = db.execute(
            """SELECT id, timestamp, shares, price
               FROM transactions
               WHERE user_id = ? AND symbol = ? AND shares > 0
               ORDER BY timestamp""",
            user_id, symbol.upper()
        )

        # Calculate current holdings and unrealized P&L
        current_stock = lookup(symbol)
        if not current_stock:
            return json.dumps({'error': 'Stock not found'}), 404

        current_price = current_stock['price']

        # Get total shares currently owned (accounting for sales)
        holdings = db.execute(
            """SELECT SUM(shares) as total_shares
               FROM transactions
               WHERE user_id = ? AND symbol = ?""",
            user_id, symbol.upper()
        )

        total_shares = holdings[0]['total_shares'] if holdings and holdings[0]['total_shares'] else 0

        # Calculate P&L for EACH individual trade
        trades = []
        total_cost = 0
        total_current_value = 0

        for txn in transactions:
            trade_shares = txn['shares']
            purchase_price = float(txn['price'])
            purchase_cost = trade_shares * purchase_price
            current_value = trade_shares * current_price
            trade_pl = current_value - purchase_cost
            trade_pl_pct = (trade_pl / purchase_cost * 100) if purchase_cost > 0 else 0

            total_cost += purchase_cost
            total_current_value += current_value

            trades.append({
                'id': txn['id'],
                'timestamp': txn['timestamp'],
                'shares': trade_shares,
                'purchase_price': purchase_price,
                'purchase_cost': purchase_cost,
                'current_value': current_value,
                'unrealized_pl': trade_pl,
                'unrealized_pl_pct': trade_pl_pct
            })

        # Calculate overall weighted P&L
        total_pl = total_current_value - total_cost
        total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

        # Calculate weighted average purchase price
        avg_price = total_cost / sum(t['shares'] for t in trades) if trades else 0

        return json.dumps({
            'trades': trades,
            'holdings': {
                'total_shares': float(total_shares) if total_shares else 0,
                'shares_from_purchases': sum(t['shares'] for t in trades),
                'avg_price': float(avg_price),
                'current_price': float(current_price),
                'total_cost': float(total_cost),
                'total_current_value': float(total_current_value),
                'unrealized_pl': float(total_pl),
                'unrealized_pl_pct': float(total_pl_pct)
            }
        })
    except Exception as e:
        print(f"DEBUG: Error fetching user trades: {str(e)}")
        import traceback
        traceback.print_exc()
        return json.dumps({'error': str(e)}), 500


@app.route("/api/portfolio-sectors")
@login_required
def portfolio_sectors():
    """API endpoint to get portfolio breakdown by sector"""
    import json

    try:
        user_id = session["user_id"]

        # Get all stocks the user owns
        portfolio = db.execute(
            """SELECT symbol, SUM(shares) as total_shares
               FROM transactions
               WHERE user_id = ?
               GROUP BY symbol
               HAVING total_shares > 0""",
            user_id
        )

        if not portfolio:
            return json.dumps({'sectors': {}, 'error': 'No holdings'})

        # Get sector information and current values for each stock
        sector_values = {}

        for stock in portfolio:
            symbol = stock['symbol']
            shares = stock['total_shares']

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                # Get sector (with fallbacks)
                sector = (
                    info.get('sector') or
                    info.get('sectorKey') or
                    info.get('industry') or
                    'Other'
                )

                # Get current price
                current_price = info.get('regularMarketPrice') or info.get('currentPrice', 0)

                # Calculate value
                value = shares * current_price

                # Add to sector total
                if sector in sector_values:
                    sector_values[sector] += value
                else:
                    sector_values[sector] = value

                print(f"DEBUG: {symbol} - Sector: {sector}, Value: ${value:.2f}")

            except Exception as e:
                print(f"DEBUG: Error getting sector for {symbol}: {e}")
                # Fallback
                if 'Other' in sector_values:
                    sector_values['Other'] += 100  # Placeholder
                else:
                    sector_values['Other'] = 100

        # Convert to labels and values for pie chart
        labels = list(sector_values.keys())
        values = list(sector_values.values())

        return json.dumps({
            'labels': labels,
            'values': values
        })

    except Exception as e:
        print(f"DEBUG: Error fetching portfolio sectors: {str(e)}")
        import traceback
        traceback.print_exc()
        return json.dumps({'error': str(e)}), 500


@app.route("/api/portfolio-performance")
@login_required
def portfolio_performance():
    """API endpoint to get weighted portfolio performance"""
    import json
    from datetime import datetime, timedelta

    try:
        user_id = session["user_id"]

        # Get all stocks the user owns
        portfolio = db.execute(
            """SELECT symbol, SUM(shares) as total_shares,
                      SUM(shares * price) / SUM(shares) as avg_price
               FROM transactions
               WHERE user_id = ?
               GROUP BY symbol
               HAVING total_shares > 0""",
            user_id
        )

        if not portfolio:
            return json.dumps({'labels': [], 'values': [], 'error': 'No holdings'})

        # Get historical data for each stock (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # Collect all price histories
        all_dates = set()
        stock_histories = {}

        for stock in portfolio:
            symbol = stock['symbol']
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='1mo', interval='1d')

                if not hist.empty:
                    stock_histories[symbol] = {
                        'history': hist,
                        'shares': stock['total_shares'],
                        'avg_price': stock['avg_price']
                    }
                    all_dates.update(hist.index)
            except:
                continue

        if not stock_histories:
            return json.dumps({'labels': [], 'values': [], 'error': 'No data'})

        # Sort dates
        sorted_dates = sorted(list(all_dates))

        # Calculate portfolio value for each date
        labels = []
        values = []

        for date in sorted_dates:
            portfolio_value = 0
            total_cost = 0

            for symbol, data in stock_histories.items():
                hist = data['history']
                shares = data['shares']
                avg_price = data['avg_price']

                # Get price for this date (or nearest)
                if date in hist.index:
                    price = hist.loc[date]['Close']
                    portfolio_value += shares * price
                    total_cost += shares * avg_price

            if total_cost > 0:
                # Calculate percentage return
                pct_return = ((portfolio_value - total_cost) / total_cost) * 100
                labels.append(date.strftime('%m/%d'))
                values.append(float(pct_return))

        return json.dumps({
            'labels': labels,
            'values': values
        })
    except Exception as e:
        print(f"DEBUG: Error fetching portfolio performance: {str(e)}")
        import traceback
        traceback.print_exc()
        return json.dumps({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)
