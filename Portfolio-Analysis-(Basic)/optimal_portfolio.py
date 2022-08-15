'''
This fuction takes list of stocks from which desired number of stocks can be selected in a portfolio.
Outputs the optimal weights of the selected portfolio.
'''

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import minimize, Bounds
from urllib.request import urlopen
import math
import datetime

def loadprices(symbol, years = 1):
  end = ((datetime.date.today() - datetime.date(1970, 1, 2)).days)*24*3600
  start = end - years*365*24*3600
  if(symbol[0] == '^'):
    symbol = symbol.upper()
  else:
    symbol = symbol.upper() +'.NS'
  link = 'https://query1.finance.yahoo.com/v7/finance/download/'+ symbol +'?period1='+ str(start) + '&period2='+ str(end) +'&interval=1d&events=history&includeAdjustedClose=true'
  f = urlopen(link)
  data = f.read()
  data = data.decode('utf-8')
  data = data.split('\n')
  daily_adjusted_close = []
  for line in data[1:]:
    row = line.split(',')
    daily_adjusted_close.append(float(row[5]))
  return(daily_adjusted_close)

# objective function
def sharpe_ratio(weights, covar_matrix, annual_returns, Rf=0.0633, sign=-1.0):
  std = np.sqrt(np.dot(np.dot(weights.T, covar_matrix), weights))
  mean = np.dot(weights.T, annual_returns)
  return sign*(mean - Rf)/std # multiplied by -1 because scipy don't have maximize function

def constraint(weights):
  return weights.sum() - 1

def optimal_portfolio(portfolio, portfolio_size=10):
  if portfolio_size > len(portfolio):
    print('Portfolio size must be less than or equal to list of stocks!')
    return None
  portfolio_df = pd.DataFrame()
  for stock in portfolio:
    portfolio_df[stock] = loadprices(stock)

  daily_log_returns = np.log(portfolio_df) - np.log(portfolio_df.shift(1))
  daily_log_returns = daily_log_returns.dropna()
  annual_returns = daily_log_returns.sum()
  annual_returns = annual_returns.sort_values(ascending=False)[:portfolio_size]
  covariance_matrix = daily_log_returns[annual_returns.index].cov()
  annual_covariance_matrix = covariance_matrix*250

  n = portfolio_size
  w = np.random.rand(n)
  w0 = w/w.sum() # random guess
  cons = [{'type': 'eq', 'fun': constraint}]
  bnds = Bounds(np.zeros(n),np.ones(n))
  sol = minimize(sharpe_ratio, w0, args=(annual_covariance_matrix.values, annual_returns.values), method='SLSQP', constraints=cons, bounds=bnds)

  PORTFOLIO = pd.DataFrame()
  PORTFOLIO['Annual Returns'] = annual_returns
  PORTFOLIO['Annual Returns'] = PORTFOLIO['Annual Returns'].apply(lambda x: np.round_(x, decimals=4))
  PORTFOLIO['Optimal Weights'] = pd.Series(np.round_(sol.x, decimals=4), index=annual_returns.index)

  portfolio_return = round(np.dot((PORTFOLIO['Optimal Weights'].values).T, PORTFOLIO['Annual Returns'].values)*100, 2)
  portfolio_standard_deviation = round(np.sqrt(np.dot((PORTFOLIO['Optimal Weights'].values).T, np.dot(annual_covariance_matrix.values, PORTFOLIO['Optimal Weights'].values)))*100, 2)

  print(f"Return of the portfilio is: {portfolio_return}%")
  print()
  print(f"Standard deviation of the portfolio is: {portfolio_standard_deviation}%")
  print()
  return PORTFOLIO[['Annual Returns', 'Optimal Weights']]*100
