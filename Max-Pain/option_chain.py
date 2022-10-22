import requests
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

class OptionChain:
  def __init__(self, ticker='NIFTY'):
    self.ticker = ticker
    self.data = self._fetch()
    self.expiries = self._expiries()
    self.spot = self._spot()
    self.last_updated = self._timestamp()

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
      print('Data downloaded directly')
      output = requests.get(url, headers=headers).json()
    except ValueError:
      print('Data from new session')
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

  def strike_prices(self, expiry='current'):
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
    pd.set_option('display.max_rows', 200)
    op_chain = list()
    if expiry == 'current':
      for i in self.data['filtered']['data']:
        op_chain.append(dict(CE_OI=(i.get('CE', i)).get('openInterest', 0),
                                    CE_Vol=(i.get('CE', i)).get('totalTradedVolume', 0),
                                    CE_IV=(i.get('CE', i)).get('impliedVolatility', 0),
                                    CE_LTP=(i.get('CE', i)).get('lastPrice', 0),
                                    strikePrice=i['strikePrice'],
                                    PE_LTP=(i.get('PE', i)).get('lastPrice', 0),
                                    PE_IV=(i.get('PE', i)).get('impliedVolatility', 0),
                                    PE_Vol=(i.get('PE', i)).get('totalTradedVolume', 0),
                                    PE_OI=(i.get('PE', i)).get('openInterest', 0)))    
    elif expiry in self.expiries:
      for i in self.data['records']['data']:
        if i['expiryDate'] == expiry:
          op_chain.append(dict(CE_OI=(i.get('CE', i)).get('openInterest', 0),
                                    CE_Vol=(i.get('CE', i)).get('totalTradedVolume', 0),
                                    CE_IV=(i.get('CE', i)).get('impliedVolatility', 0),
                                    CE_LTP=(i.get('CE', i)).get('lastPrice', 0),
                                    strikePrice=i['strikePrice'],
                                    PE_LTP=(i.get('PE', i)).get('lastPrice', 0),
                                    PE_IV=(i.get('PE', i)).get('impliedVolatility', 0),
                                    PE_Vol=(i.get('PE', i)).get('totalTradedVolume', 0),
                                    PE_OI=(i.get('PE', i)).get('openInterest', 0)))    
    else:
      raise ValueError('Enter right expiry or leave it on default')
    return pd.DataFrame(op_chain)

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
      self.plot(df_chain['strikePrice'], df_chain['callPain'], df_chain['putPain'])
    
    print('--------------------------')
    print(f'PCR: {pcr}')
    print(f'MAX CE OI AT: {maxCEOI}')
    print(f'MAX PE OI AT: {maxPEOI}')
    print(f'TOTAL CE OI: {totalCEOI}')
    print(f'TOTAL PE OI: {totalPEOI}')
    print(f'MAX PAIN AT: {minTotalPain}')
    print('--------------------------')
    # display(df_chain.iloc[df_chain['totalPain'].idxmin()].astype('int64'))

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

  def save(self, name='OC.json', indent=None):
    oc_json = json.dumps(self.data, indent=indent)
    with open("OC4.json", "w") as outfile:
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
  def plot(strike, callpain, putpain):
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
