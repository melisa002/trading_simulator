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
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


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
        stock["name"] = quote["name"]
        stock["price"] = quote["price"]
        stock["total"] = stock["price"] * stock["shares"]
        total_cash_stocks = total_cash_stocks + stock["total"]

    total_cash = total_cash_stocks + cash
    return render_template(
        "index.html", stocks=stocks, cash=cash, total_cash=total_cash
    )



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        stock = lookup(symbol)
        user_id= session["user_id"]
        stock_name= stock["name"]
        stock_price= stock["price"]
        user_cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])[0]['cash']


        # what is lookup ???
        if not symbol:
            return apology("Please enter a symbol")
        if not stock:
            return apology("Invalid symbol")

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Shares must be an intiger!")

        if shares <= 0:
            return apology("Shares should be positive")

        #totstock_price = cash
        totstock_price= stock_price * shares
        if user_cash < totstock_price:
            return apology("Insufficent funds!")
        if db.execute("SELECT * FROM transactions WHERE user_id=?",user_id)==db.execute("SELECT * FROM transactions WHERE user_id=? LIMIT 1",user_id):
            db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash - totstock_price, user_id)
            db.execute("INSERT INTO transactions(user_id, name, shares, price, type,symbol) VALUES (?,?,?,?,?,?)",
            user_id,stock_name,shares, stock_price,'buy',symbol )
            flash("Congratulations on your first buy!! Don't forget to keep checking the graphs and sell when the price rises!")
        else:
            db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash - totstock_price, user_id)
            db.execute("INSERT INTO transactions(user_id, name, shares, price, type,symbol) VALUES (?,?,?,?,?,?)",
            user_id,stock_name,shares, stock_price,'buy',symbol )
            flash("Bought!")
        #is the the stock putchased is the first one bought then make sure to flash the congratulations, first buy sign.
        return redirect('/index')
    else:
        return render_template("buy.html")


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
        symbol = request.form.get('symbol')
        session['symbol']= symbol

        if not symbol:
            return apology("Please enter a symbol")

        stock = lookup(symbol)

        if not stock:
            return apology("Symbol does not exist")

        return render_template("quotsa.html", stock=stock )

    else:
        return render_template("quotes.html")


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
            session["user_id"],
            symbol,
        )[0]["shares"]

        if shares > stocks:
            return apology("You don't have this number of shares")
        price = lookup(symbol)["price"]
        shares_value = price * shares
        item_name = lookup(symbol)['name']

        db.execute(
            "INSERT INTO transactions (user_id, name,shares, price, type, symbol) VALUES (?, ?, ?, ?, ?,?)",
            session["user_id"],
            item_name,
            -shares,
            price,
            "sell",
            symbol
        )

        db.execute(
            "UPDATE users SET cash = cash + ? WHERE id = ?",
            shares_value,
            session["user_id"],
        )

        flash("Sold!")
        return redirect("/index")
    else:
        stocks = db.execute(
            "SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol",
            session["user_id"],
        )
        return render_template("sell.html", stocks=stocks)



