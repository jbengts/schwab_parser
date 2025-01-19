import argparse
import requests
import json
import datetime
import time
import os
from datetime import date

class ShareSell:
    def __init__(self, t, q, bd, bp, sd, sp):
        self.sell_type = t
        self.sell_quantity = float(q)
        self.sell_date = datetime.datetime.strptime(sd, '%m/%d/%Y').date()
        self.sell_price = float(sp.replace("$", ""))
        self.sell_rate = 0.0
        self.buy_date = datetime.datetime.strptime(bd, '%m/%d/%Y').date()
        self.buy_price = float(bp.replace("$", ""))
        self.buy_rate = 0.0
    def __repr__(self):
        return f"<Test a:{self.sell_price}>"

    def __str__(self):
        return f"Sold: {self.sell_date} Qnty: {self.sell_quantity} Type: \
        {self.sell_type} \
        Sell price: {self.sell_price} Sell rate:{self.sell_rate} \
        Buy date: {self.buy_date} Buy price: {self.buy_price} \
        Buy rate: {self.buy_rate}"
    
    def total(self):
        f"Sold: {self.sell_date} Qnty: {self.sell_quantity} Type: \
        {self.sell_type} \
        Sell price: {self.sell_price} Sell rate:{self.sell_rate} \
        Buy date: {self.buy_date} Buy price: {self.buy_price} \
        Buy rate: {self.buy_rate}"
        cleaned_price_str = price_str.replace("$", "")
        # Convert the string to a float
        price_float = float(cleaned_price_str)
        self.sell_rate
  
def fetch_and_parse_json_from_url(fromd, tod):
    try:
        if os.path.exists("rates.json"):
            with open("rates.json", 'r', encoding='utf-8') as file:
                data = json.load(file)
            return data
        else:
            f = fromd.strftime("%Y-%m-%d")
            t = tod.strftime("%Y-%m-%d")
            url = f"https://api.riksbank.se/swea/v1/Observations/sekusdpmi/{f}/{t}"
            response = requests.get(url)
            print(f"response {url} {response}")
            response.raise_for_status()
            data = response.json()
            print("Data fetched from URL:")
            with open("rates.json", "w") as file:
                json.dump(data, file, indent=4) 
                # print(json.dumps(data, indent=4, ensure_ascii=False))
            return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decoding failed: {e}")

        # https://api.riksbank.se/swea/v1/Observations/Latest/sekusdpmi
        # https://api.riksbank.se/swea/v1/Observations/sekusdpmi/from/to
def parse_json_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        print("Data read from file:")
        shares_sold = get_transactions_list(data)
        for share in shares_sold:
            print(share)
        oldest, newest = get_oldes_and_newest_dates(shares_sold)
        rates = fetch_and_parse_json_from_url(oldest, newest)
        shares = update_rates(rates, shares_sold)
        for share in shares:
            print(share)
        calculate_result(shares)
        # find_in_json(acc, data, "Transactions")
        # print(json.dumps(res, indent=4, ensure_ascii=False))
        return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except json.JSONDecodeError as e:
        print(f"JSON decoding failed: {e}")

def find_in_json(obj, target):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == target:
                return value
            result = find_in_json(value, target)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_in_json(item, target)
            if result:
                return result
    return None

def get_sales_entries(trans_list):
    acc = []
    for item in trans_list:
        for key, value in item.items():
            if key == "Action" and value == "Sale":
                sales = get_sales_object(item)
                acc.extend(sales)
            if key == "Action" and value == "Quick Sale":
                sales = get_sales_object(item)
                acc.extend(sales)
    return acc

def get_oldes_and_newest_dates(shares):
    oldest = date.today()
    newest = datetime.datetime.strptime("11/11/2022", '%m/%d/%Y').date()
    for share in shares:
        if share.sell_date > newest:
            newest = share.sell_date
        if share.buy_date < oldest:
            oldest = share.buy_date
            
    print(f"oldest: {oldest}")
    print(f"newest: {newest}")
    return (oldest, newest)

def calculate_result(shares):
    profit = 0.0
    sold = 0.0
    for share in shares:
        sold = share.sell_quantity * (share.sell_price * share.sell_rate) + sold
        profit = share.sell_quantity * (share.sell_price * share.sell_rate - share.buy_price * share.buy_rate) + profit
    print(f"sold: {sold}")
    print(f"profit: {profit}")
    tax = 0.3 * profit
    print(f"tax: {tax}")
    
def update_rates(rates, shares):
    prev_rated = None
    for rate in rates:
        datestr = rate["date"]
        rated = datetime.datetime.strptime(datestr, '%Y-%m-%d').date()
        value = rate["value"]
        for share in shares:
            print(f"share: {share}")
            if share.sell_date == rated:
                print(f"sell date is the date of the rate...")
                share.sell_rate = float(value)
            elif prev_rated is not None and share.sell_date > prev_rated[0] and share.sell_date < rated:
                print(f"sell date is after the previous rate and before the next rate")
                share.sell_rate = (float(prev_rated[1]) + float(value))/2
            if share.buy_date == rated:
                print(f"buy date is the date of the rate...")
                share.buy_rate = float(value)
            elif share.buy_date < rated and share.buy_rate == 0.0:
                share.buy_rate = float(value)
            elif prev_rated is not None and share.buy_date > prev_rated[0] and share.buy_date < rated:
                print(f"buy date is after the previous rate and before the next rate")
                share.buy_rate = (float(prev_rated[1]) + float(value))/2
            else:
                print(f"hmm: rate is date {rated} and value is {value}")
                print(f"share bought {share.buy_date}")
                # print(f"prev rate {prev_rated[0]} {prev_rated[1]}");
        prev_rated = (rated, value)
    return shares

def get_sales_object(sale):
    sell_date = sale["Date"]
    sell_type = sale["Action"]
    details = sale["TransactionDetails"]
    acc = []
    for detail in details:
        data = detail["Details"]
        quantity = data["Shares"]
        sell_price = data["SalePrice"]
        buy_price = data["PurchasePrice"]
        buy_date = data["PurchaseDate"]
        if not buy_price:
            buy_price = data["VestFairMarketValue"]
        if not buy_date:
            buy_date = data["VestDate"]
        share_sell = ShareSell(sell_type, quantity, buy_date, buy_price,
                               sell_date, sell_price)
        acc.append(share_sell)
    return acc

def get_transactions_list(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "Transactions":
                acc = get_sales_entries(value)
                # print(f"Trans {acc}")
                return acc
    elif isinstance(obj, list):
        for item in obj:
            result = find_in_json(item)
            if result:
                return result
    return None

if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Fetch and parse \
    JSON data from a URL or a file.")

    parser.add_argument("--url", help="The URL to fetch JSON data from.")
    parser.add_argument("--file", help="The file path to read JSON data from.")
    
    # Parse the arguments
    args = parser.parse_args()

    # Handle URL argument
    if args.url:
        fetch_and_parse_json_from_url(args.url)

    # Handle file argument
    if args.file:
        parse_json_from_file(args.file)

    # If neither is provided, print help
    if not args.url and not args.file:
        parser.print_help()
