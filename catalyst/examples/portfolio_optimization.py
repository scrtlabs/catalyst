'''
   Author: Rodrigo Gomez-Grassi
   Date: Sep. 20, 2017  

   Use this code to execute a portfolio optimization model. This code
   will select the portfolio with the maximum Sharpe Ratio. The parameters
   are set to use 180 days of historical data and rebalance every 30 days.

   This is the code used in the following article:
   https://blog.enigma.co/markowitz-portfolio-optimization-for-cryptocurrencies-in-catalyst-b23c38652556

   You can run this code using the Python interpreter:

   $ python portfolio_optimization.py
'''

from __future__ import division
import os
import pytz
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

from catalyst.api import record, symbols, order_target_percent
from catalyst.utils.run_algo import run_algorithm

np.set_printoptions(threshold='nan', suppress=True)


def initialize(context):
    # Portfolio assets list
    context.assets = symbols('btc_usdt', 'eth_usdt', 'ltc_usdt', 'dash_usdt',
                             'xmr_usdt')
    context.nassets = len(context.assets)
    # Set the time window that will be used to compute expected return
    # and asset correlations
    context.window = 180
    # Set the number of days between each portfolio rebalancing
    context.rebalance_period = 30
    context.i = 0


def handle_data(context, data):
    # Only rebalance at the beggining of the algorithm execution and
    # every multiple of the rebalance period
    if context.i == 0 or context.i % context.rebalance_period == 0:
        n = context.window
        prices = data.history(context.assets, fields='price',
                              bar_count=n + 1, frequency='1d')
        pr = np.asmatrix(prices)
        t_prices = prices.iloc[1:n + 1]
        t_val = t_prices.values
        tminus_prices = prices.iloc[0:n]
        tminus_val = tminus_prices.values
        # Compute daily returns (r)
        r = np.asmatrix(t_val / tminus_val - 1)
        # Compute the expected returns of each asset with the average
        # daily return for the selected time window
        m = np.asmatrix(np.mean(r, axis=0))
        # ###
        stds = np.std(r, axis=0)
        # Compute excess returns matrix (xr)
        xr = r - m
        # Matrix algebra to get variance-covariance matrix
        cov_m = np.dot(np.transpose(xr), xr) / n
        # Compute asset correlation matrix (informative only)
        corr_m = cov_m / np.dot(np.transpose(stds), stds)

        # Define portfolio optimization parameters
        n_portfolios = 50000
        results_array = np.zeros((3 + context.nassets, n_portfolios))
        for p in range(n_portfolios):
            weights = np.random.random(context.nassets)
            weights /= np.sum(weights)
            w = np.asmatrix(weights)
            p_r = np.sum(np.dot(w, np.transpose(m))) * 365
            p_std = np.sqrt(np.dot(np.dot(w, cov_m),
                                   np.transpose(w))) * np.sqrt(365)

            # store results in results array
            results_array[0, p] = p_r
            results_array[1, p] = p_std
            # store Sharpe Ratio (return / volatility) - risk free rate element
            # excluded for simplicity
            results_array[2, p] = results_array[0, p] / results_array[1, p]
            i = 0
            for iw in weights:
                results_array[3 + i, p] = weights[i]
                i += 1

        # convert results array to Pandas DataFrame
        results_frame = pd.DataFrame(np.transpose(results_array),
                                     columns=['r', 'stdev', 'sharpe']
                                             + context.assets)
        # locate position of portfolio with highest Sharpe Ratio
        max_sharpe_port = results_frame.iloc[results_frame['sharpe'].idxmax()]
        # locate positon of portfolio with minimum standard deviation
        # min_vol_port = results_frame.iloc[results_frame['stdev'].idxmin()]

        # order optimal weights for each asset
        for asset in context.assets:
            if data.can_trade(asset):
                order_target_percent(asset, max_sharpe_port[asset])

        # create scatter plot coloured by Sharpe Ratio
        plt.scatter(results_frame.stdev,
                    results_frame.r,
                    c=results_frame.sharpe,
                    cmap='RdYlGn')
        plt.xlabel('Volatility')
        plt.ylabel('Returns')
        plt.colorbar()
        # plot red star to highlight position of portfolio
        # with highest Sharpe Ratio
        plt.scatter(max_sharpe_port[1],
                    max_sharpe_port[0],
                    marker='o',
                    color='b',
                    s=200)
        # plot green star to highlight position of minimum variance portfolio
        plt.show()
        print(max_sharpe_port)
        record(pr=pr,
               r=r,
               m=m,
               stds=stds,
               max_sharpe_port=max_sharpe_port,
               corr_m=corr_m)
    context.i += 1


def analyze(context=None, results=None):
    # Form DataFrame with selected data
    data = results[['pr', 'r', 'm', 'stds', 'max_sharpe_port', 'corr_m',
                    'portfolio_value']]

    # Save results in CSV file
    filename = os.path.splitext(os.path.basename(__file__))[0]
    data.to_csv(filename + '.csv')


if __name__ == '__main__':
    # Bitcoin data is available from 2015-3-2. Dates vary for other tokens.
    start = datetime(2017, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2017, 8, 16, 0, 0, 0, 0, pytz.utc)
    results = run_algorithm(initialize=initialize,
                            handle_data=handle_data,
                            analyze=analyze,
                            start=start,
                            end=end,
                            exchange_name='poloniex',
                            capital_base=100000,
                            quote_currency='usdt', )
