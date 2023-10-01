import yfinance as yahooFinance

# Here We are getting Facebook financial information
# We need to pass FB as argument for that
# GetFacebookInformation = yahooFinance.Ticker("META")
 
# # whole python dictionary is printed here
# # print(GetFacebookInformation.info)
 
# # # display Company Sector
# # print("Company Sector : ", GetFacebookInformation.info['sector'])
 
# # # display Price Earnings Ratio
# # print("Price Earnings Ratio : ", GetFacebookInformation.info['trailingPE'])
 
# # # display Company Beta
# # print(" Company Beta : ", GetFacebookInformation.info['beta'])

# # get all key value pairs that are available
# for key, value in GetFacebookInformation.info.items():
#     print(key, ":", value)

# print(GetFacebookInformation.history(period="max"))

import yfinance as yf
from yfinance import Ticker

msft = yf.Ticker("MSFT")

# get all stock info
msft.info

# get historical market data
# hist = msft.history(period="1mo")

hist2 = msft.history(period="10y")

print(hist2)
# # show meta information about the history (requires history() to be called first)
# print(msft.history_metadata)

# # show actions (dividends, splits, capital gains)
# print(msft.actions)
# print(msft.dividends)
# print(msft.splits)
# print(msft.capital_gains)  # only for mutual funds & etfs

# # show share count
# print(msft.get_shares_full(start="2022-01-01", end=None))

# # show financials:
# # - income statement
# print(msft.income_stmt)
# print(msft.quarterly_income_stmt)
# # - balance sheet
# print(msft.balance_sheet)
# print(msft.quarterly_balance_sheet)
# # - cash flow statement
# print(msft.cashflow)
# print(msft.quarterly_cashflow)
# # see `Ticker.get_income_stmt()` for more options

# # show holders
# print(msft.major_holders)
# print(msft.institutional_holders)
# print(msft.mutualfund_holders)

# # Show future and historic earnings dates, returns at most next 4 quarters and last 8 quarters by default. 
# # Note: If more are needed use msft.get_earnings_dates(limit=XX) with increased limit argument.
# print(msft.earnings_dates)

# # show ISIN code - *experimental*
# # ISIN = International Securities Identification Number
# print(msft.isin)

# # show options expirations
# print(msft.options)

# # show news
# print(msft.news)

# # get option chain for specific expiration
# opt = msft.option_chain('YYYY-MM-DD')
# # data available via: opt.calls, opt.puts

# print(opt)