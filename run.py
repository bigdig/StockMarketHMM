from backtest import Backtest
from data_reader import DatastreamCsvPriceHandler
from train_hmm import RegimeHmmModel

import sys
import pickle
import numpy
from datetime import datetime
import argparse

def get_training_data(daily_returns, start_date, end_date):
    """
    Return training data
    """
    DATE = 0
    start = 0
    end = 0
    for idx, day in enumerate(daily_returns):
        # Check for starting date
        if day[DATE] == start_date:
            start = idx
        elif day[DATE] == end_date:
            end = idx
            break

    return numpy.column_stack([daily_returns[start:end, 1]])

if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Run backtests on stock market")
    argparser.add_argument("--csv-file", default=None, help="CSV file containing stock index prices or individual stock prices")
    argparser.add_argument("--backtest-start", default=None, help="Start date of backtest. Give like this 'day.month.year'")
    argparser.add_argument("--backtest-end", default="31.12.2017", help="End date of backtest")
    argparser.add_argument("--training-start", default=None, help="Start date of training period")
    argparser.add_argument("--training-end", default=None, help="End date of training period")
    argparser.add_argument("--strategy", default=None, help="Investment strategy to backtest. Currently supports 'buy-and-hold' and 'regime-filter'")
    argparser.add_argument("--regimes", default=None, help="Number of volatility regimes")
    argparser.add_argument("--pickle-path", default=None, help="File to store trained HMM")
    args = argparser.parse_args()
    strategy = args.strategy
    if strategy not in ["buy-and-hold", "regime-filter", "new-regime-filter"]:
        print("That strategy isn't on the list of accepted strategies")
        sys.exit()

    # Get daily prices and returns, as numpy arrays with shape (days, 2). First column is dates, second prices or percentage returns.
    price_handler = DatastreamCsvPriceHandler(args.csv_file)
    daily_prices = price_handler.daily_prices
    daily_returns = price_handler.daily_returns

    # Train HMM
    if strategy == "regime-filter" or strategy == "new-regime-filter":
        training_start_date = datetime.strptime(args.training_start, '%d.%m.%Y')
        training_end_date = datetime.strptime(args.training_end, '%d.%m.%Y')
        training_data = get_training_data(daily_returns, training_start_date, training_end_date)
        regimes = int(args.regimes)
        RegimeHmmModel(training_data, n_states=regimes, n_iters=100000, pickle_path=args.pickle_path)

    # Run backtest
    backtest_start_date = datetime.strptime(args.backtest_start, '%d.%m.%Y')
    backtest_end_date = datetime.strptime(args.backtest_end, '%d.%m.%Y')
    if strategy == "regime-filter" or strategy == "new-regime-filter":
        trained_hmm_model = pickle.load(open(args.pickle_path, 'rb'))
        variances = trained_hmm_model.covars_
        flattened_variances = variances.flatten()
        high_regime = 0
        if numpy.argmax(flattened_variances) == 1:
            high_regime = 1
        elif numpy.argmax(flattened_variances) == 2:
            high_regime = 2
        else:
            high_regime = 0

        backtest = Backtest(daily_prices, daily_returns, strategy, backtest_start_date, backtest_end_date, high_regime, trained_hmm_model)
        backtested_portfolio = backtest.run()
    else:
        backtest = Backtest(daily_prices, daily_returns, strategy, backtest_start_date, backtest_end_date, high_regime=None, hmm_model=None)
        backtested_portfolio = backtest.run()

    # Print dates, portfolio equity, and current state if using regime-filter strategy
    DATE = 0
    EQUITY = 1
    REGIME = 2
    for day in backtested_portfolio:
        day[DATE] = day[DATE].date()
        if strategy == "buy-and-hold":
            print(day[DATE], day[EQUITY])
        else:
            print(day[DATE], day[EQUITY], day[REGIME])
