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
    def __init__(self, share_type, quantity, buy_date, buy_price, sell_date,
                 sell_price, espp_discount_price):
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

def print_table_section_summary(quantity, buy, sell, result):
    print("")
    print(f"{'':<22}{quantity:<10.2f}"
          f"{'':<122.2}{sell:<14.2f}{buy:<14.2f}{result:<14.2f}")
    print("-" * 195)
    
def print_table(shares):
    print(f"{'Sell Date':<12}{'Type':<10}{'Quantity':<10}{'Sell Price':<12}"
          f"{'Sell Rate':<12}{'Sell Rate Date':<25}{'Buy Date':<12}"
          f"{'Buy Price':<12}{'Buy Rate':<12}{'Buy Rate Date':<25}"
          f"{'ESPP Gain':<12}{'Sell (SEK)':<14}{'Buy (SEK)':<14}{'Result (SEK)':<14}")
    print("-" * 195)
    
    total_result = 0.0
    res_total_sell = 0.0
    res_total_buy = 0.0
    res_total_quantity = 0.0

    total_quantity = 0.0
    total_buy = 0.0
    total_sell = 0.0
    total_diff = 0.0
            
    prev_sell_date = None
    for share in shares:
        sell_date = share.sell_date.strftime('%Y-%m-%d')
        buy_date = share.buy_date.strftime('%Y-%m-%d')
        if prev_sell_date is not None and prev_sell_date != sell_date:
            print_table_section_summary(total_quantity, total_buy,
                                        total_sell, total_diff)
            res_total_sell += total_sell
            res_total_buy += total_buy
            res_total_quantity += total_quantity
            total_quantity = 0.0
            total_buy = 0.0
            total_sell = 0.0
            total_diff = 0.0            
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

        quantity = share.sell_quantity
        buy = (share.buy_rate * share.buy_price) * share.sell_quantity
        sell = (share.sell_rate * share.sell_price) * share.sell_quantity
        diff = sell - buy

        total_quantity += quantity
        total_buy += buy
        total_sell += sell
        total_diff += diff
        total_result += diff

        prev_sell_date = sell_date
        print(f"{sell_date:<12}{share.share_type:<10}"
              f"{share.sell_quantity:<10.2f}{share.sell_price:<12.2f}"
              f"{share.sell_rate:<12.2f}{sell_rate_date:<25}{buy_date:<12}"
              f"{share.buy_price:<12.2f}{share.buy_rate:<12.2f}"
              f"{buy_rate_date:<25}{espp_gain:<12.2f}"
              f"{sell:<14.2f}{buy:<14.2f}{diff:<14.2f}")
    if total_result > 0.0:
        tax = total_result * 0.3
    else:
        tax = 0.0
    print_table_section_summary(total_quantity, total_buy,
                                total_sell, total_diff)
    res_total_sell += total_sell
    res_total_buy += total_buy
    res_total_quantity += total_quantity
    print(f"Total quantity: {res_total_quantity:.2f}")
    print(f"Total buy (SEK): {res_total_buy:.2f}")
    print(f"Total sell (SEK): {res_total_sell:.2f}")
    print(f"Total result (SEK): {total_result:.2f}")
    print(f"Total tax    (SEK): {tax:.2f}")

def get_valid_value(data, primary_key, fallback_key):
    value = data.get(primary_key)
    return value if value not in (None, "") else data.get(fallback_key)

def get_rates(shares, rates_file):
    oldest, newest = get_oldes_and_newest_dates(shares)
    oldest = oldest - relativedelta(months=1)
    newest = newest + relativedelta(months=1)
    return get_rates_range(oldest, newest, rates_file)

def get_rates_range(from_date, to_date, rates_file):
    try:
        if os.path.exists(rates_file):
            with open(rates_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            return data
        else:
            from_str = from_date.strftime("%Y-%m-%d")
            to_str = to_date.strftime("%Y-%m-%d")
            url = f"https://api.riksbank.se/swea/v1/Observations/sekusdpmi/{from_str}/{to_str}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            with open(rates_file, "w") as file:
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
    parser = argparse.ArgumentParser(description=("Parse a Schwab JSON transaction file and calculate the total Tax (SEK) for the shares sold.\n"
                                    "Exchange rates are fetched from Riksbanken for the interval given by the transaction JSON data.\n\n"
                                    "To get a transaction statement file, go to the Schwab page under 'transaction history' and after choosing an "
                                    "interval export the file as JSON.\n\n"
                                    "schwab_parser.py --file <transaction_statement>.json"),
                                    formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--file", help="The file path containing JSON transaction data.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    # Parse the arguments
    args = parser.parse_args()

    # Set verbose option
    Config.verbose = args.verbose

    # Get all transactions from JSON file
    transactions = get_transactions(args.file)
  
    # Get sold shares
    sold_shares = get_sold_shares(transactions)

    # The rates file
    file_name, file_extension = os.path.splitext(args.file)
    rates_file = f"{file_name}_rates{file_extension}"

    # Get exchange rates within the dates of sold shares
    rates = get_rates(sold_shares, rates_file)

    # Update the shares with the correct exchange rate
    sold_shares = update_shares(sold_shares, rates)

    # Print
    print_table(sold_shares)
