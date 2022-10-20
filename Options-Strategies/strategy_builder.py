import numpy as np
import plotly.graph_objects as go

class Strategy:
    def __init__(self, spot, lot_size=50, downside=0.05, upside=0.05, strategy_qty=1):
        self.payoff = 0
        self.spot = spot
        self.price_range = np.arange((1-downside)*spot, (1+upside)*spot)
        self.lot_size = lot_size
        self.strategy_qty = strategy_qty
        
    def add_call(self, strike, premium, position, qty=1):
        self.payoff += (self.call_profit(strike, self.price_range, premium=premium, position=position))*qty
    
    def add_put(self, strike, premium, position, qty=1):
        self.payoff += (self.put_profit(strike, self.price_range, premium=premium, position=position))*qty
    
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
