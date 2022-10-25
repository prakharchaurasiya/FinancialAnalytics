import requests
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

class OptionChain:
  def __init__(self, ticker='NIFTY', expiry='current', lot_size=50, downside=0.05, upside=0.05, strategy_qty=1):
    self.payoff = 0
    self.ticker = ticker
    self.data = self._fetch()
    self.expiry = expiry
    self.expiries = self._expiries()
    self.spot = self._spot()
    self.last_updated = self._timestamp()
    self.strikes = self._strike_prices(expiry=expiry)
    self.price_range = np.arange((1-downside)*self.spot, (1+upside)*self.spot)
    self.lot_size = lot_size
    self.strategy_qty = strategy_qty
    self.option_chain = self.chain(expiry=expiry)
    self.trades = list()

  def _fetch(self):
    url = 'https://www.nseindia.com/api/option-chain-indices?symbol=' + self.ticker.upper()
    headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
    }
    try:
      # print('Data downloaded directly')
      output = requests.get(url, headers=headers).json()
    except ValueError:
      # print('Data from new session')
      s = requests.Session()
      output = s.get("http://nseindia.com", headers=headers)
      output = s.get(url, headers=headers).json()
    return output

  def _spot(self):
    return self.data['records']['underlyingValue']

  def _timestamp(self):
    return self.data['records']['timestamp']

  def _expiries(self):
    return self.data['records']['expiryDates']

  def _strike_prices(self, expiry='current'):
    st_price = list()
    if expiry == 'current':
      for i in self.data['filtered']['data']:
        st_price.append(i['strikePrice'])
    elif expiry in self.expiries:
      for i in self.data['records']['data']:
        if i['expiryDate'] == expiry:
          st_price.append(i['strikePrice'])
    else:
      raise ValueError('Enter right expiry or leave it on default')
    return st_price

  def chain(self, expiry='current'):
    op_chain = dict()
    if expiry == 'current':
      for i in self.data['filtered']['data']:
        op_chain[i['strikePrice']] = dict(CE_OI=(i.get('CE', i)).get('openInterest', 0),
                                    CE_Vol=(i.get('CE', i)).get('totalTradedVolume', 0),
                                    CE_IV=(i.get('CE', i)).get('impliedVolatility', 0),
                                    CE_LTP=(i.get('CE', i)).get('lastPrice', 0),
                                    PE_LTP=(i.get('PE', i)).get('lastPrice', 0),
                                    PE_IV=(i.get('PE', i)).get('impliedVolatility', 0),
                                    PE_Vol=(i.get('PE', i)).get('totalTradedVolume', 0),
                                    PE_OI=(i.get('PE', i)).get('openInterest', 0))  
    elif expiry in self.expiries:
      for i in self.data['records']['data']:
        if i['expiryDate'] == expiry:
          op_chain[i['strikePrice']] = dict(CE_OI=(i.get('CE', i)).get('openInterest', 0),
                                    CE_Vol=(i.get('CE', i)).get('totalTradedVolume', 0),
                                    CE_IV=(i.get('CE', i)).get('impliedVolatility', 0),
                                    CE_LTP=(i.get('CE', i)).get('lastPrice', 0),
                                    PE_LTP=(i.get('PE', i)).get('lastPrice', 0),
                                    PE_IV=(i.get('PE', i)).get('impliedVolatility', 0),
                                    PE_Vol=(i.get('PE', i)).get('totalTradedVolume', 0),
                                    PE_OI=(i.get('PE', i)).get('openInterest', 0))     
    else:
      raise ValueError('Enter right expiry or leave it on default')
    return op_chain

  def new_strategy(self):
    self.payoff = 0
    self.trades = list()

  def add_call(self, strike, position, qty=1):
    if not (strike in self.strikes):
      raise ValueError('Strike price not found')
    premium = self.option_chain[strike]['CE_LTP']
    self.payoff += (self.call_profit(strike, self.price_range, premium=premium, position=position))*qty
    self.trades.append(dict(typ='call', strike=strike, premium=premium,position=position, qty=qty))
  
  def add_put(self, strike, position, qty=1):
    if not (strike in self.strikes):
      raise ValueError('Strike price not found')
    premium = self.option_chain[strike]['PE_LTP']
    self.payoff += (self.put_profit(strike, self.price_range, premium=premium, position=position))*qty
    self.trades.append(dict(typ='put', strike=strike, premium=premium,position=position, qty=qty))

  def add_future(self, position, premium=0, qty=1):
    self.payoff += (self.future_profit(self.spot, self.price_range, premium=premium,position=position))*qty
    self.trades.append(dict(typ='future', premium=premium,position=position, qty=qty))

  def plot(self):
    self.payoff *= self.lot_size*self.strategy_qty
    profit = np.ravel(self.payoff*[self.payoff >= 0])
    loss = np.ravel(self.payoff*[self.payoff < 0])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=self.price_range, y=profit, mode='lines', name='Profit', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=self.price_range, y=loss, mode='lines', name='Loss', line=dict(color='red')))
    fig.add_hline(y=0)        
    fig.add_vline(x=self.spot, line_dash="dash")
    fig.update_layout(title='Option Strategy Payoff', xaxis_tickformat = '%d', autosize=False, width=1280, height=720)
    fig.show()
  
  def max_pain(self, expiry='current', plot=True):
    chain = list()
    if expiry == 'current':
      print(f'Expiry: {self.expiries[0]}')
      for i in self.data['filtered']['data']:
        chain.append(dict(strikePrice=i['strikePrice'], 
                          openInterestCE=(i.get('CE', i)).get('openInterest', 0), 
                          openInterestPE=(i.get('PE', i)).get('openInterest', 0)))
    elif expiry in self.expiries:
      print(f'Expiry: {expiry}')
      for i in self.data['records']['data']:
        if i['expiryDate'] == expiry:
          chain.append(dict(strikePrice=i['strikePrice'], 
                          openInterestCE=(i.get('CE', i)).get('openInterest', 0), 
                          openInterestPE=(i.get('PE', i)).get('openInterest', 0)))
    else:
      raise ValueError('Enter right expiry or leave it on default')
    df_chain = pd.DataFrame(chain)
    df_chain['callPain'] = self.pain(df_chain['strikePrice'], df_chain['openInterestCE'], typ='call')
    df_chain['putPain'] = self.pain(df_chain['strikePrice'], df_chain['openInterestPE'], typ='put')
    df_chain['totalPain'] = df_chain['callPain'] + df_chain['putPain']

    totalCEOI = df_chain['openInterestCE'].sum()
    totalPEOI = df_chain['openInterestPE'].sum()
    pcr = totalPEOI/totalCEOI
    maxCEOI = df_chain['strikePrice'].iloc[df_chain['openInterestCE'].idxmax()]
    maxPEOI = df_chain['strikePrice'].iloc[df_chain['openInterestPE'].idxmax()]
    minTotalPain = df_chain['strikePrice'].iloc[df_chain['totalPain'].idxmin()]
    
    if plot:
      self.max_pain_plot(df_chain['strikePrice'], df_chain['callPain'], df_chain['putPain'])
    
    print('--------------------------')
    print(f'PCR: {pcr}')
    print(f'MAX CE OI AT: {maxCEOI}')
    print(f'MAX PE OI AT: {maxPEOI}')
    print(f'TOTAL CE OI: {totalCEOI}')
    print(f'TOTAL PE OI: {totalPEOI}')
    print(f'MAX PAIN AT: {minTotalPain}')
    print('--------------------------')

    # return dict(ticker=self.ticker, 
    #               expiry=expiry, 
    #               pcr=pcr, 
    #               maxPain=minTotalPain, 
    #               maxCEOI=maxCEOI, 
    #               maxPEOI=maxPEOI)

  def summary(self, expiry='current'):
    print(f'TICKER: {self.ticker}')
    if not expiry == 'all':
      self.max_pain(expiry=expiry)
    else:
      for ex in self.expiries:
        self.max_pain(expiry=ex, plot=False)
        print()
    print(f'Current Spot Price: {self.spot}')
    print(f'Data Last Updated: {self.last_updated}')
    print('All expiries:', end=' ') 
    print(*self.expiries, sep=', ')

  def save(self, indent=None):
    name = self.ticker + self.last_updated + '.json'    
    oc_json = json.dumps(self.data, indent=indent)
    with open(name, "w") as outfile:
      outfile.write(oc_json)

  def pain(self, strike, oi, typ='call'):
    pain = list()
    for exspot in strike:
      t = 0
      for st, o in zip(strike, oi):
        if typ == 'call':
          t += self.call_profit(st, exspot)*o
        if typ == 'put' :
          t += self.put_profit(st, exspot)*o
      pain.append(t)
    return pain

  @staticmethod
  def call_profit(strike, spot, premium=0, position='long'):
    pnl = np.where(spot>strike, spot-strike, 0) - premium
    if position in ['long', 'buy']:
      return pnl
    elif position in ['short', 'sell']:
      return -1.0 * pnl
    else:
      return np.nan
  
  @staticmethod
  def put_profit(strike, spot, premium=0, position='long'):
    pnl = np.where(spot<strike, strike-spot, 0) - premium
    if position in ['long', 'buy']:
      return pnl
    elif position in ['short', 'sell']:
      return -1.0 * pnl
    else:
      return np.nan

  @staticmethod
  def future_profit(spot, price_range, premium=0, position='long'):
    pnl = price_range - spot - premium
    if position in ['long', 'buy']:
      return pnl
    elif position in ['short', 'sell']:
      return -1.0 * pnl
    else:
      return np.nan

  @staticmethod
  def max_pain_plot(strike, callpain, putpain):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=strike, y=callpain,
        name='CALL PAIN',
        marker_color='lightsalmon'))
    fig.add_trace(go.Bar(
        x=strike, y=putpain,
        name='PUT PAIN',
        marker_color='indianred'))
    fig.update_layout(
        title='MAX PAIN', 
        xaxis_tickformat = '%d',
        autosize=False,
        width=1280,
        height=720,)
    fig.show()
