import argparse
import requests
import json
import datetime
import time
import os
from datetime import date
from dateutil.relativedelta import relativedelta

# Config options
class Config:
    verbose = True

class ShareSell:
    def __init__(self, share_type, quantity, buy_date, buy_price, sell_date, sell_price, espp_discount_price):
        self.share_type = share_type
        self.sell_quantity = float(quantity)
        self.sell_date = datetime.datetime.strptime(sell_date, '%m/%d/%Y').date()
        self.sell_price = float(sell_price.replace("$", ""))
        self.sell_rate = None
        self.buy_date = datetime.datetime.strptime(buy_date, '%m/%d/%Y').date()
        self.buy_price = float(buy_price.replace("$", ""))
        self.buy_rate = None
        self.sell_date_low = None
        self.sell_date_high = None
        self.buy_date_low = None
        self.buy_date_high = None
        if espp_discount_price is not None:
            self.espp_discount_price = float(espp_discount_price.replace("$", ""))
        else:
            self.espp_discount_price = None

    def __repr__(self):
        return f"<ShareSell sell_price={self.sell_price}>"

    def __str__(self):
        return f"Sold: {self.sell_date} Qnty: {self.sell_quantity} Type: \
        {self.share_type} \
        Sell price: {self.sell_price} Sell rate:{self.sell_rate:.2f} \
        Buy date: {self.buy_date} Buy price: {self.buy_price} \
        Buy rate: {self.buy_rate:.2f}"
    
# Verbose print wrapper
def sprint(*args, **kwargs):
    if Config.verbose:
        print(*args, **kwargs)

def print_table(shares):
    # Skriv ut rubriker
    print(f"{'Sell Date':<12}{'Type':<10}{'Quantity':<10}\
        {'Sell Price':<12}{'Sell Rate':<12}{'Sell Rate Date':<25}\
        {'Buy Date':<12}{'Buy Price':<12}{'Buy Rate':<12}\
        {'Buy Rate Date':<25}{'ESPP Gain':<12}{'Profit':<12}{'Tax':<12}")
    print("-" * 180)

    # Iterera över objekten och skriv ut deras attribut
    total_tax = 0.0
    total_profit = 0.0
    prev_sell_date = None
    for share in shares:
        sell_date = share.sell_date.strftime('%Y-%m-%d')
        buy_date = share.buy_date.strftime('%Y-%m-%d')
        if prev_sell_date is not None and prev_sell_date != sell_date:
            print("-" * 180)
        if share.sell_date_low == share.sell_date_high:
            sell_rate_date = share.sell_date_low.strftime('%Y-%m-%d')
        else:
            sell_rate_date = share.sell_date_low.strftime('%Y-%m-%d') + share.sell_date_high.strftime('%Y-%m-%d')
        if share.buy_date_low == share.buy_date_high:
            buy_rate_date = share.buy_date_low.strftime('%Y-%m-%d')
        else:
            buy_rate_date = share.buy_date_low.strftime('%Y-%m-%d') + " - " + share.buy_date_high.strftime('%Y-%m-%d')
        if share.espp_discount_price is not None:
            espp_gain = (share.buy_price - share.espp_discount_price) * share.sell_quantity * share.sell_rate
        else:
            espp_gain = 0.0
        profit = (share.sell_rate * share.sell_price - share.buy_rate * share.buy_price) * share.sell_quantity
        tax = profit * 0.3
        total_tax += tax
        total_profit += profit
        prev_sell_date = sell_date
        print(f"{sell_date:<12}{share.share_type:<10}{share.sell_quantity:<10.2f}{share.sell_price:<12.2f}{share.sell_rate:<12.2f}{sell_rate_date:<25}{buy_date:<12}{share.buy_price:<12.2f}{share.buy_rate:<12.2f}{buy_rate_date:<25}{espp_gain:<12.2f}{profit:<12.2f}{tax:<12.2f}")
    print("-" * 180)
    print(f"Total profit (SEK): {total_profit:.2f}")
    print(f"Total tax (SEK):    {total_tax:.2f}")

def get_valid_value(data, primary_key, fallback_key):
    value = data.get(primary_key)
    return value if value not in (None, "") else data.get(fallback_key)

def get_rates1(shares):
    oldest, newest = get_oldes_and_newest_dates(shares)
    oldest = oldest - relativedelta(months=1)
    newest = newest + relativedelta(months=1)
    return get_rates(oldest, newest)

def get_rates(from_date, to_date):
    try:
        if os.path.exists("rates.json"):
            with open("rates.json", 'r', encoding='utf-8') as file:
                data = json.load(file)
            return data
        else:
            from_str = from_date.strftime("%Y-%m-%d")
            to_str = to_date.strftime("%Y-%m-%d")
            url = f"https://api.riksbank.se/swea/v1/Observations/sekusdpmi/{from_str}/{to_str}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            with open("rates.json", "w") as file:
                json.dump(data, file, indent=4) 
            return data
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error loading JSON data: {e}")
        return None

        # https://api.riksbank.se/swea/v1/Observations/Latest/sekusdpmi
        # https://api.riksbank.se/swea/v1/Observations/sekusdpmi/from/to

def get_oldes_and_newest_dates(shares):
    oldest = date.today()
    newest = datetime.datetime.strptime("11/11/2011", '%m/%d/%Y').date()
    for share in shares:
        if share.sell_date > newest:
            newest = share.sell_date
        if share.buy_date < oldest:
            oldest = share.buy_date
    return (oldest, newest)

def update_shares(shares, rates):
    for share in shares:
        sell_rate, sell_date_low, sell_date_high, buy_rate, buy_date_low, buy_date_high = get_rate(rates, share.sell_date, share.buy_date)
        share.sell_rate = sell_rate
        share.buy_rate = buy_rate
        share.sell_date_low = sell_date_low
        share.sell_date_high = sell_date_high
        share.buy_date_low = buy_date_low
        share.buy_date_high = buy_date_high
        print(f"{share}")
    return shares

def get_rate(rates, sell_date, buy_date):
    prev_rate = None
    sell_rate = None
    buy_rate = None
    sell_date_high = None
    sell_date_low = None
    buy_date_high = None
    buy_date_low = None
    for rate in rates:
        rate_date = datetime.datetime.strptime(rate["date"], '%Y-%m-%d').date()
        rate_value = rate["value"]            
        if sell_date == rate_date:
            sell_rate = float(rate_value)
            sell_date_low = rate_date
            sell_date_high = rate_date
        elif sell_date < rate_date and sell_rate is None:
            sell_rate =  (float(prev_rate[1]) + float(rate_value)) / 2
            sell_date_low = prev_rate[0]
            sell_date_high = rate_date
        if buy_date == rate_date:
            buy_rate = float(rate_value)
            buy_date_low = rate_date
            buy_date_high = rate_date
        elif buy_date < rate_date and buy_rate is None:
            buy_rate =  (float(prev_rate[1]) + float(rate_value)) / 2
            buy_date_low = prev_rate[0]
            buy_date_high = rate_date
        prev_rate = (rate_date, rate_value)
    return sell_rate, sell_date_low, sell_date_high, buy_rate, buy_date_low, buy_date_high

def get_sold_shares(transactions):
    sold_shares = []
    for transaction in transactions:
        if transaction["Action"] in {"Sale", "Quick Sale"}:
            sell_date = transaction["Date"]
            details = transaction["TransactionDetails"]
            espp_discount_price = None
            for detail in details:
                data = detail["Details"]
                type = data["Type"]
                quantity = data["Shares"]
                sell_price = data["SalePrice"]
                if type == "Div Reinv":
                    buy_date = data["PurchaseDate"]
                    buy_price = data["PurchasePrice"]
                elif type == "RS":
                    buy_date = data["VestDate"]
                    buy_price = data["VestFairMarketValue"]
                elif type == "ESPP":
                    espp_discount_price = data["PurchasePrice"]
                    buy_date = data["PurchaseDate"]
                    buy_price = data["PurchaseFairMarketValue"]
                sold_shares.append(ShareSell(type, quantity, buy_date, buy_price, sell_date, sell_price, espp_discount_price))
    return sold_shares

def get_transactions(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "Transactions":
                    return value
        return None
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON data: {e}")
    return None

if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Fetch and parse \
    JSON data from a URL or a file.")

    parser.add_argument("--url", help="The URL to fetch JSON data from.")
    parser.add_argument("--file", help="The file path to read JSON data from.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    # Parse the arguments
    args = parser.parse_args()

    # Set verbose option
    Config.verbose = args.verbose

    # Get all transactions from JSON file
    transactions = get_transactions(args.file)
  
    # Get sold shares
    sold_shares = get_sold_shares(transactions)

    # Get exchange rates within the dates of sold shares
    rates = get_rates1(sold_shares)

    # Update the shares with the correct exchange rate
    sold_shares = update_shares(sold_shares, rates)

    # Print
    print_table(sold_shares)
    # Calculate profit or losses, and eventual taxes
    # Total sale amount minus total purchase amount.
    # And 30% taxes on eventual profit.
    # calculate_and_print_totals(sold_shares)

    # Handle file argument
    # if args.file:
    #    parse_json_from_file(args.file)

    # If neither is provided, print help
    
    if not args.url and not args.file:
        parser.print_help()
