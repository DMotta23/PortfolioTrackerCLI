#Author: Diogo Terra Simões da Motta, Alexandre Liaudet - 2nd Year BIE
#Course: Programming for Economists II
import yfinance as yf
import matplotlib.pyplot as plt
import json
import os
import subprocess
import sys


# ---------------------------
# BASE CURRENCY + FX HELPERS
# ---------------------------
BASE_CURRENCY = "EUR"  # change to "USD" if you prefer


def fetch_last_close(ticker, period="5d"):
    """
    Fetches the last close for a ticker (also works for FX tickers like EURUSD=X).
    :param ticker: string
    :param period: yfinance period string
    :return: float or None
    """
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def get_fx_rate(from_cur, to_cur):
    """
    Returns FX rate for converting from_cur -> to_cur.
    Example: EUR->USD returns USD per 1 EUR.
    :param from_cur: string currency code
    :param to_cur: string currency code
    :return: float or None
    """
    if from_cur == to_cur:
        return 1.0

    # Try direct quote (e.g. EURUSD=X)
    direct = f"{from_cur}{to_cur}=X"
    rate = fetch_last_close(direct)
    if rate is not None:
        return rate

    # Try inverse (e.g. USDEUR=X), then invert
    inverse = f"{to_cur}{from_cur}=X"
    inv = fetch_last_close(inverse)
    if inv is not None and inv != 0:
        return 1.0 / inv

    return None


def get_fx_rate_with_fallback(from_cur, to_cur, fx_cache):
    """
    Uses cache first; if FX fetch fails, asks user manually once per pair.
    :param from_cur: string
    :param to_cur: string
    :param fx_cache: dict cache {(from,to): rate}
    :return: float or None
    """
    if from_cur in (None, "", "N/A"):
        from_cur = to_cur

    key = (from_cur, to_cur)
    if key in fx_cache:
        return fx_cache[key]

    fx = get_fx_rate(from_cur, to_cur)
    if fx is not None:
        fx_cache[key] = fx
        return fx

    print(f"\n⚠️ Could not fetch FX rate for {from_cur}->{to_cur}.")
    print("You can enter it manually (example: if 1 USD = 0.92 EUR, type 0.92).")
    while True:
        val = input(f"Enter FX rate {from_cur}->{to_cur} (or press Enter to skip): ").strip()
        if val == "":
            return None
        try:
            fx = float(val)
            if fx <= 0:
                print("FX rate must be > 0.")
                continue
            fx_cache[key] = fx
            return fx
        except ValueError:
            print("Invalid number.")


# ---------------------------
# BASE CURRENCY MENU ACTION (NEW)
# ---------------------------
def change_base_currency():
    """
    Lets the user change the base currency used for totals/weights.
    :return: None
    """
    global BASE_CURRENCY
    print(f"\nCurrent base currency: {BASE_CURRENCY}")
    new_cur = input("Enter new base currency (e.g., EUR, USD, BRL): ").strip().upper()
    if new_cur == "":
        print("Base currency cannot be empty.")
        return
    BASE_CURRENCY = new_cur
    print("Base currency set to:", BASE_CURRENCY)


# ---------------------------
# LOADING/SAVING/DELETING FILE (CRUD)
# ---------------------------
# this code section was done and integrated using ChatGPT
DATA_FILE = "portfolio_data.json"
def load_data():
    """
    Loads portfolio data from a JSON file (if it exists).
    :return: portfolio dictionary
    """
    global BASE_CURRENCY  # NEW: we want to restore base currency from file
    if not os.path.exists(DATA_FILE):
        return {} # returns empty dict in case file does not exist

    try:
        with open(DATA_FILE, "r") as f: # reading
            data = json.load(f)

            # NEW: restore base currency if saved
            if "base_currency" in data and data["base_currency"]:
                BASE_CURRENCY = data["base_currency"]

            if "portfolio" in data:
                return data["portfolio"]
            return {} # empty dict if file exists but is empty
    except Exception:
        print("Warning: Could not load data file. Starting with empty portfolio.")
        return {}

def save_data(portfolio):
    """
    Saves portfolio data to a JSON file.
    :param portfolio: dictionary of holdings
    :return: None
    """
    data = {"portfolio": portfolio, "base_currency": BASE_CURRENCY}  # NEW: save base currency too
    try:
        with open(DATA_FILE, "w") as f: # writing
            json.dump(data, f, indent=4) # indent improves readability
    except Exception:
        print("Warning: Could not save data file.")

def delete_data_file():
    """
    Deletes the saved portfolio file if it exists
    :return: None
    """
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
            print("Saved data deleted.")
        except Exception:
            print("Could not delete the data file.")
    else:
        print("No saved data file found.")


# ---------------------------
# METADATA FETCHER
# ---------------------------
def get_ticker_metadata(ticker): # Makes it easier to pull exchange and currency later without using Yahoo API
    """
    Fetches basic ticker metadata from Yahoo Finance.
    :param ticker: stock symbol
    :return: dict with metadata OR None if invalid
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.info # dict with company data

        hist = tk.history(period="1d")
        if hist.empty: # checking if yahoo returned any data
            return None

        price = float(hist["Close"].iloc[-1]) # selecting close column, and returning the last ROW

        return {
            "exchange": info.get("exchange", "N/A"),
            "currency": info.get("currency", "N/A"),
            "price": price,
        }

    except Exception: # catching exception in case fetching metadata fails
        return None


# ---------------------------
# MENU
# ---------------------------
def print_menu():
    """
    Prints the main portfolio menu
    :return: None
    """
    print("\n==== PORTFOLIO MANAGER ====")
    print("1) Add/manage holdings")
    print("2) Portfolio summary")
    print("3) Rebalance suggestions")
    print("4) View stock info from portfolio")
    print("5) Trendline price chart (multiple timeframes)")
    print("6) Delete saved data")
    print("7) Open dashboard")
    print("8) Change base currency")  # NEW
    print("0) Exit")


# ---------------------------
# DASHBOARD
# ---------------------------
def open_dashboard():
    """
    Launches the Streamlit dashboard from this project folder.
    :return: None
    """
    dashboard_file = "dashboard.py"
    if not os.path.exists(dashboard_file):
        print(f"Could not find {dashboard_file} in the current folder.")
        return

    try:
        # Starts Streamlit without blocking the CLI, using the same Python environment.
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", dashboard_file])
        print("Opening dashboard at http://localhost:8501 ...")
    except Exception:
        print("Could not launch dashboard. Make sure streamlit is installed.")

# ---------------------------
# BASIC TICKER INFO
# ---------------------------
def show_basic_ticker_info(ticker):
    """
    Fetches and prints basic info about a ticker and checks if it is valid
    :param ticker: stock symbol entered by the user
    :return: metadata dict if valid, None otherwise
    """

    data = get_ticker_metadata(ticker)

    if data is None:
        print("\nWarning: No price data found.")
        print("Ticker may be invalid, delisted, or require a suffix (e.g., .SA, .L, .PA).")
        return None

    exchange = data["exchange"]
    currency = data["currency"]
    price = data["price"]

    print("\n--- Ticker info ---")
    print("Exchange:", exchange)
    print("Currency:", currency)
    print(f"Current price: {price:.2f}")
    print("-------------------\n")

    return data


# ---------------------------
# HOLDINGS
# portfolio = {"AAPL": {"shares": 5.0, "avg_cost": 150.0}, ...}
# ---------------------------
def manage_holdings(portfolio):
    """
    Lets the user add, update, remove and view holdings
    :param portfolio: dictionary with the current portfolio positions
    :return: None
    """
    while True:
        print("\n-- Manage holdings --")
        print("1) Add/Update holding")
        print("2) Remove holding")
        print("3) View holdings")
        print("0) Back")
        choice = input("Choose a number: ").strip()

        if choice == "1": # add or update/overwrite tickers
            ticker = input("Ticker (e.g., AAPL): ").strip().upper()
            if ticker == "":
                print("Ticker cannot be empty.")
                continue # restarts while loop due to incorrect ticker input

            # in case there's an error fetching metadata, while loop restarts
            info_meta = show_basic_ticker_info(ticker)
            if info_meta is None:
                continue

            try:
                shares = float(input("Number of shares: ").strip())
                avg_cost = float(input("Average cost per share: ").strip())
            except ValueError:
                print("Invalid number.")
                continue

            if shares <= 0 or avg_cost <= 0:
                print("Shares and avg_cost must be > 0.")
                continue

            portfolio[ticker] = {
                "shares": shares,
                "avg_cost": avg_cost,
                "currency": info_meta["currency"],
            } # creating dict which will be saved
            save_data(portfolio) # saving file
            print("Saved:", ticker)

        elif choice == "2": # removing tickers
            ticker = input("Ticker to remove: ").strip().upper()
            if ticker in portfolio:
                del portfolio[ticker]
                save_data(portfolio) # saving file
                print("Removed:", ticker)
            else:
                print("Not found.")

        elif choice == "3": # viewing tickers
            if len(portfolio) == 0:
                print("Portfolio is empty.")
            else:
                for t in portfolio:
                    info = portfolio[t]
                    cur = info.get("currency", "N/A")
                    print(f"{t}: {info['shares']} shares @ avg cost {info['avg_cost']} ({cur})")

        elif choice == "0": # back option
            break
        else:
            print("Invalid option.")


# ---------------------------
# PRICES
# simplest possible: fetch each ticker one by one, if not, user inputs prices manually
# ---------------------------
def fetch_prices(tickers):
    """
    Fetches the latest price for each ticker from Yahoo Finance
    :param tickers: list of ticker symbols
    :return: dictionary mapping each ticker to its latest price (or None)
    """
    prices = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if hist.empty:
                prices[t] = None # if price cannot be found, None is assigned to the ticker's price, which will be altered later
            else:
                prices[t] = float(hist["Close"].iloc[-1]) # price was already found
        except Exception:
            prices[t] = None
    return prices


def manual_fix_prices(prices):
    """
    Asks the user to manually input prices that could not be fetched, making sure that all tickers have prices
    :param prices: dictionary of ticker prices (some may be None)
    :return: updated dictionary with valid prices
    """
    fixed = {}
    for t in prices:
        p = prices[t]
        if p is not None: # these are the prices that were already found
            fixed[t] = p
        else:
            while True:
                try:
                    val = float(input(f"Couldn't fetch {t}. Enter price manually: ").strip())
                    if val <= 0:
                        print("Price must be > 0.")
                        continue
                    fixed[t] = val
                    break # leaves the while loop and moves onto the next ticker
                except ValueError:
                    print("Invalid number.")
    return fixed


# ---------------------------
# STOCK INFO
# ---------------------------
def view_stock_info_from_holdings(portfolio):
    """
    Shows detailed company information for a selected holding
    :param portfolio: dictionary of current holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("\nPortfolio is empty. Add holdings first.")
        return

    tickers = list(portfolio.keys()) # extracting all tickers into one list

    print("\n-- Available holdings --")
    for i in range(len(tickers)):
        print(f"{i+1}) {tickers[i]}")
    print("0) Back")

    choice = input("Choose a stock number: ").strip()

    if choice == "0":
        return

    try:
        i_stock = int(choice) - 1 # stock index
    except ValueError:
        print("Invalid option.")
        return

    if i_stock < 0 or i_stock >= len(tickers):
        print("Invalid option.")
        return
    else:
        ticker = tickers[i_stock]
        print(f"\nFetching info for {ticker}...")

    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        # price (also validates data exists)
        hist = tk.history(period="1d")
        if hist.empty:
            print("No price data found for this ticker right now.")
            return
        else:
            price = float(hist["Close"].iloc[-1])

        # company basics
        name = info.get("longName") or info.get("shortName") or "N/A" # first one that == True
        country = info.get("country", "N/A")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        exchange = info.get("exchange", "N/A")
        currency = info.get("currency", "N/A")

        # financials
        market_cap = info.get("marketCap") # returns None if it doesn't exist
        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")

        # ratios / margins
        pe = info.get("trailingPE")
        pb = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        gross_margin = info.get("grossMargins")
        op_margin = info.get("operatingMargins")
        profit_margin = info.get("profitMargins")

        print("\n===== STOCK INFO =====")
        print("Ticker:", ticker)
        print("Name:", name)
        print("Country:", country)
        print("Sector:", sector)
        print("Industry:", industry)
        print("Exchange:", exchange)
        print("Currency:", currency)
        print(f"Current price: {price:.2f}")

        print("\n--- Size & financials ---")

        if market_cap is not None: # required to ensure correct output formatting
            print("Market cap:", f"{market_cap:,.0f}")
        else:
            print("Market cap: N/A")

        if revenue is not None:
            print("Revenue (TTM):", f"{revenue:,.0f}")
        else:
            print("Revenue (TTM): N/A")

        if net_income is not None:
            print("Net income (TTM):", f"{net_income:,.0f}")
        else:
            print("Net income (TTM): N/A")

        print("\n--- Ratios & margins ---")

        if pe is not None:
            print("P/E (TTM):", f"{pe:.2f}")
        else:
            print("P/E (TTM): N/A")

        if pb is not None:
            print("P/B:", f"{pb:.2f}")
        else:
            print("P/B: N/A")

        if roe is not None:
            print("ROE:", f"{roe * 100:.2f}%")
        else:
            print("ROE: N/A")

        if gross_margin is not None:
            print("Gross margin:", f"{gross_margin * 100:.2f}%")
        else:
            print("Gross margin: N/A")

        if op_margin is not None:
            print("Operating margin:", f"{op_margin * 100:.2f}%")
        else:
            print("Operating margin: N/A")

        if profit_margin is not None:
            print("Profit margin:", f"{profit_margin * 100:.2f}%")
        else:
            print("Profit margin: N/A")

        print("======================\n")

    except Exception:
        print("Could not fetch company info right now.")


def plot_price_trend_from_holdings(portfolio): # using matplotlib
    """
    Plots a simple trendline chart of a selected holding's price.
    :param portfolio: dictionary of holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("\nPortfolio is empty. Add holdings first.")
        return

    tickers = list(portfolio.keys()) # same code as view_stock_info_from_holdings()

    print("\n-- Available holdings --")
    for i in range(len(tickers)):
        print(f"{i+1}) {tickers[i]}")
    print("0) Back")

    choice = input("Choose a stock number: ").strip()
    if choice == "0":
        return

    try:
        i_stock = int(choice) - 1
    except ValueError:
        print("Invalid option.")
        return

    if i_stock < 0 or i_stock >= len(tickers):
        print("Invalid option.")
        return

    ticker = tickers[i_stock] # getting ticker from list of portfolio dict using stock index

    print("\nChoose a timeframe:")
    print("1) 1w")
    print("2) 1m")
    print("3) ytd")
    print("4) 1y")
    print("5) 2y")
    print("6) 5y")
    print("7) 10y")
    print("8) all")
    tf = input("Choose timeframe number: ").strip()

    # timeframe mapping
    if tf == "1":
        period = "5d"
        interval = "1h"
        title_tf = "1 Week"
    elif tf == "2":
        period = "1mo"
        interval = "1d"
        title_tf = "1 Month"
    elif tf == "3":
        period = "ytd"
        interval = "1d"
        title_tf = "YTD"
    elif tf == "4":
        period = "1y"
        interval = "1wk"
        title_tf = "1 Year"
    elif tf == "5":
        period = "2y"
        interval = "1wk"
        title_tf = "2 Years"
    elif tf == "6":
        period = "5y"
        interval = "1wk"
        title_tf = "5 Years"
    elif tf == "7":
        period = "10y"
        interval = "1mo"
        title_tf = "10 Years"
    elif tf == "8":
        period = "max"
        interval = "1mo"
        title_tf = "All Time"
    else:
        print("Invalid option.")
        return

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period, interval=interval) # changes depending on if statement above

        if hist.empty:
            print("No price data found for this timeframe.")
            return

        dates = hist.index
        closes = hist["Close"]

        plt.figure()
        plt.plot(dates, closes)
        plt.title(f"{ticker} Price Trend ({title_tf})")
        plt.xlabel("Date")
        plt.ylabel("Close Price")
        plt.xticks(rotation=30) # date needs to be slightly tilted in order to fit on graph
        plt.tight_layout() # fixes margins and spacing
        plt.show()

    except Exception:
        print("Could not fetch or plot price data right now.")


# ---------------------------
# SUMMARY
# ---------------------------
def portfolio_summary(portfolio):
    """
    Computes and prints the portfolio valuation and unrealized P/L
    :param portfolio: dictionary of holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("\nPortfolio is empty. Add holdings first.")
        return

    tickers = list(portfolio.keys())

# currency code below done with ChatGPT to identify different
    currencies = set() # similar to lists, but no duplicated are allowed
    for t in portfolio:
        cur = portfolio[t].get("currency")
        if cur: # An actual currency (truthy value), not False, None, 0, etc...
            currencies.add(cur)
    if len(currencies) > 1: # means that there's more than one currency
        print("\n⚠️ Warning: Portfolio contains multiple currencies:", ", ".join(sorted(currencies))) # sorts currencies into alphabetical order and joins each element into one string
        print(f"Converting totals/weights to base currency: {BASE_CURRENCY}\n")

    prices = fetch_prices(tickers)
    prices = manual_fix_prices(prices) # just in case yahoo finance cannot get stock price

    fx_cache = {}

    total_value_base = 0.0
    total_cost_base = 0.0
    total_unreal_base = 0.0
    rows = []

    for t in tickers:
        shares = portfolio[t]["shares"] # no need to use .get(), as we're sure that the ticker exists
        avg_cost = portfolio[t]["avg_cost"]
        price = prices[t]
        currency = portfolio[t].get("currency", "N/A")

        value_local = shares * price # total stock value
        cost_local = shares * avg_cost # total stock cost
        unreal_local = (price - avg_cost) * shares # total stock P/L

        # unrealized % for each position (local)
        if avg_cost > 0:
            unreal_pct = ((price - avg_cost) / avg_cost) * 100
        else:
            unreal_pct = 0.0

        fx = get_fx_rate_with_fallback(currency, BASE_CURRENCY, fx_cache)
        if fx is None:
            print(f"⚠️ Skipping {t} in totals/weights (missing FX {currency}->{BASE_CURRENCY}).")
            continue

        value_base = value_local * fx
        cost_base = cost_local * fx
        unreal_base = unreal_local * fx

        total_value_base += value_base
        total_cost_base += cost_base
        total_unreal_base += unreal_base

        rows.append([t, currency, shares, avg_cost, price, value_local, unreal_local, unreal_pct, value_base, unreal_base])

    # total unrealized % (based on total cost in base currency)
    if total_cost_base > 0:
        total_unreal_pct_base = (total_unreal_base / total_cost_base) * 100
    else:
        total_unreal_pct_base = 0.0

    print("\n===== PORTFOLIO SUMMARY =====")
    print(f"Base currency: {BASE_CURRENCY}")
    print(f"Total value: {total_value_base:.2f} {BASE_CURRENCY}")
    print(f"Total cost: {total_cost_base:.2f} {BASE_CURRENCY}")
    print(f"Total unrealized P/L: {total_unreal_base:.2f} {BASE_CURRENCY} ({total_unreal_pct_base:.2f}%)\n")

    print(f"{'Ticker':<10} {'Curr':<6} {'Shares':>10} {'AvgCost':>10} {'Price':>10} {'Value(local)':>14}"
          f" {'Unreal(local)':>14} {'Unr%':>8} {'Value(base)':>14} {'Weight':>8}")
    print("-" * 135)

    best_t = None
    best_pl_base = None
    worst_t = None
    worst_pl_base = None

    for r in rows:
        t, currency, shares, avg_cost, price, value_local, unreal_local, unreal_pct, value_base, unreal_base = r

        if total_value_base > 0:
            weight = (value_base / total_value_base) * 100
        else:
            weight = 0

        print(f"{t:<10} {currency:<6} {shares:>10.2f} {avg_cost:>10.2f} {price:>10.2f} {value_local:>14.2f}"
              f" {unreal_local:>14.2f} {unreal_pct:>7.2f}% {value_base:>14.2f} {weight:>7.2f}%")

        # compare winners/losers in base currency (this is correct across currencies)
        if best_pl_base is None or unreal_base > best_pl_base:
            best_pl_base = unreal_base
            best_t = t
        if worst_pl_base is None or unreal_base < worst_pl_base:
            worst_pl_base = unreal_base
            worst_t = t

    if best_t is not None and worst_t is not None:
        print("\nBiggest winner (unrealized):", best_t, f"{best_pl_base:.2f} {BASE_CURRENCY}")
        print("Biggest loser  (unrealized):", worst_t, f"{worst_pl_base:.2f} {BASE_CURRENCY}")


# ---------------------------
# REBALANCE
# ---------------------------
def rebalance_suggestions(portfolio):
    """
    Suggests buy/sell amounts to reach target portfolio weights
    :param portfolio: dictionary of holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("Portfolio is empty.")
        return

    tickers = list(portfolio.keys())

    prices = fetch_prices(tickers)
    prices = manual_fix_prices(prices)

    fx_cache = {}

    total_value_base = 0.0
    values_base = {}
    fx_by_ticker = {}

    # Compute current values in BASE currency
    for t in tickers:
        currency = portfolio[t].get("currency", "N/A")
        fx = get_fx_rate_with_fallback(currency, BASE_CURRENCY, fx_cache)
        if fx is None:
            print(f"⚠️ Skipping {t} in rebalance (missing FX {currency}->{BASE_CURRENCY}).")
            continue

        fx_by_ticker[t] = fx
        v_local = portfolio[t]["shares"] * prices[t]
        v_base = v_local * fx
        values_base[t] = v_base
        total_value_base += v_base

    if total_value_base == 0:
        print("Could not compute portfolio value in base currency.")
        return

    print("\nEnter target weights in % for each ticker.")
    print("Example: if you want 50%, type 50")

    targets = {}
    total_w = 0.0

    # Only ask weights for tickers that were successfully converted
    for t in values_base:
        while True:
            try:
                w = float(input(f"Target weight for {t} (in %): ").strip())
                if w < 0:
                    print("Weight must be >= 0.")
                    continue
                targets[t] = w
                total_w += w
                break
            except ValueError:
                print("Invalid number.")

    if total_w == 0: # error handling, because total weight (denominator) cannot be zero
        print("All weights are 0. Nothing to do.")
        return

    # normalize to sum to 100
    for t in targets:
        targets[t] = (targets[t] / total_w) * 100

    print("\n===== REBALANCE SUGGESTIONS =====")
    print(f"Base currency: {BASE_CURRENCY}")
    print(f"Total portfolio value: {total_value_base:.2f} {BASE_CURRENCY}")
    print("Targets normalized to sum to 100%.\n")

    for t in targets:
        current_val_base = values_base[t]
        target_val_base = (targets[t] / 100) * total_value_base
        gap_base = target_val_base - current_val_base

        price_local = prices[t]
        currency = portfolio[t].get("currency", "")
        fx = fx_by_ticker[t]

        gap_local = gap_base / fx

        if gap_base > 0: # BUY
            if price_local > 0:
                shares_to_buy = gap_local / price_local
            else:
                shares_to_buy = 0
            print(f"{t}: BUY about {gap_base:.2f} {BASE_CURRENCY} (~{gap_local:.2f} {currency}, about {shares_to_buy:.2f} shares)")

        elif gap_base < 0: # SELL
            sell_base = abs(gap_base)
            sell_local = abs(gap_local)
            if price_local > 0:
                shares_to_sell = sell_local / price_local
            else:
                shares_to_sell = 0
            print(f"{t}: SELL about {sell_base:.2f} {BASE_CURRENCY} (~{sell_local:.2f} {currency}, about {shares_to_sell:.2f} shares)")
        else:
            print(f"{t}: already on target")


# ---------------------------
# MAIN
# ---------------------------
def main():
    """
    Runs the main portfolio manager loop
    :return: None
    """
    portfolio = load_data() # loading portfolio from existing file

    while True:
        print_menu()
        choice = input("Choose an option number: ").strip()

        if choice == "1":
            manage_holdings(portfolio)
        elif choice == "2":
            portfolio_summary(portfolio)
        elif choice == "3":
            rebalance_suggestions(portfolio)
        elif choice == "4":
            view_stock_info_from_holdings(portfolio)
        elif choice == "5":
            plot_price_trend_from_holdings(portfolio)
        elif choice == "6":
            delete_data_file()
            portfolio = {} # resetting memory, as without this line, the portfolio would remain in the memory
        elif choice == "7":
            open_dashboard()
        elif choice == "8":  # NEW
            change_base_currency()
            save_data(portfolio)  # NEW: persist base currency
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__": #ChatGPT recommended this instead of just main()
    main()