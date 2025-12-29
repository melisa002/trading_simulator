import os
import yfinance as yf

from flask import redirect, render_template, request, session
from functools import wraps


def apology2(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology2.html", top=code, bottom=escape(message)), code

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol using yfinance (free!)"""

    try:
        # Get stock info from yfinance
        stock = yf.Ticker(symbol.upper())

        # Get current price and company info
        info = stock.info

        # Try to get current price from multiple sources
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')

        if price is None:
            return None

        # Get company name
        name = info.get('longName') or info.get('shortName') or symbol.upper()

        return {
            "name": name,
            "price": float(price),
            "symbol": symbol.upper()
        }
    except Exception as e:
        # Return None if there's any error (invalid symbol, network issue, etc.)
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
