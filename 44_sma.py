from __future__ import absolute_import, division, print_function, unicode_literals
import backtrader
import pandas
import sqlite3
from analyzers.trade_statistics import BasicTradeStats
from indicators.adx import AverageDirectionalMovementIndex as adx
from datetime import time, datetime, timedelta, date


class FourtyFourSma(backtrader.Strategy):
    params = dict(
        period=44,
        sma_long=200,
    )

    def __init__(self):
        self.order = None
        self.bought_today = False
        self.sold_today = False
        self.buying_price = 0
        self.selling_price = 0
        self.long_stoploss = 0
        self.short_stoploss = 0
        self.long_target = 0
        self.short_target = 0
        self.sma_high = backtrader.indicators.SimpleMovingAverage(
            self.data.high, period=self.p.period, plot=True
        )
        self.sma = backtrader.indicators.SimpleMovingAverage(
            self.data, period=self.p.period, plot=True
        )
        self.sma_low = backtrader.indicators.SimpleMovingAverage(
            self.data.low, period=self.p.period, plot=True
        )
        self.sma_long = backtrader.indicators.SimpleMovingAverage(
            self.data, period=self.p.sma_long, plot=True
        )
        self.crossover = backtrader.indicators.CrossOver(
            self.data, self.sma_high, plot=True
        )

    def log(self, txt, dt=None):
        if dt is None:
            dt = self.datas[0].datetime.datetime()

        print("%s, %s" % (dt, txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            order_details = f"{order.executed.price}, Cost: {order.executed.value}, Commision: {order.executed.comm}"

            if order.isbuy():
                self.buying_price = order.executed.price + order.executed.comm
                self.long_target = self.buying_price + (
                    (self.buying_price - self.long_stoploss) * 1.5
                )
                self.log(f"*** BUY EXECUTED, Price: {order_details} ***")

            elif order.issell():
                self.selling_price = order.executed.price - order.executed.comm
                self.short_target = self.selling_price - (
                    (self.short_stoploss - self.selling_price) * 1.5
                )
                self.log(f"*** SELL EXECUTED, Price: {order_details} ***")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def next(self):
        if self.order:
            return

        # long buy when buying cabdles and uptrend
        if (
            not self.position
            and not self.bought_today
            and not self.sold_today
            and self.data.close[0] > self.sma[0]
            and self.data.close[0] > self.sma_long
            and (
                self.data.close[0] == self.data.high[0]
                or self.data.high[0] == self.data.open[0]
                or (
                    self.data.high[0] == self.data.close[0]
                    and self.data.open[0] == self.data.low[0]
                )
                or (self.data.close[0] > self.data.open[0])
            )
            and not self.sold_today
            and self.crossover > 0
        ):
            self.order = self.buy()
            self.long_stoploss = self.data.low[0]  # stoploss value
            self.bought_today = True
            self.log(f"=== LONG BUY EXECUTED ===")

        # long target
        # 1.5:1
        elif (
            self.position
            and self.bought_today
            and not self.sold_today
            and self.data.close[0] > self.long_target
            and self.data.close <= self.sma_long
        ):
            self.order = self.close()
            self.bought_today = False
            self.log(f"=== LONG BUY TARGET HIT ===")

        # stoploss
        # stoploss will be low of the selling candle and below SMA 200
        elif (
            self.position
            and self.bought_today
            and self.data.close[0] < self.long_stoploss
            and not self.sold_today
            and self.data.close[0] < self.sma_long[0]
        ):
            self.order = self.close()
            self.bought_today = False
            self.log(f"=== LONG BUY STOPLOSS HIT | LOSER ===")

        # short sell when selling candle signals and down trend
        if (
            not self.position
            and not self.bought_today
            and not self.sold_today
            and self.data.close[0] < self.sma_long
            and (
                (self.data.close[0] == self.data.high[0])
                or (
                    self.data.high[0] == self.data.open[0]
                    and self.data.close[0] == self.data.low[0]
                    or (self.data.open[0] > self.data.close[0])
                )
            )
            and self.crossover < 0
        ):
            self.order = self.sell()
            self.short_stoploss = self.data.high[0]  # stoploss value
            self.sold_today = True
            self.log(f"=== SHORT SELL EXECUTED ===")

        # short target
        # 1.5:1
        elif (
            self.position
            and not self.bought_today
            and self.sold_today
            and self.data.close[0] < self.short_target
            and self.data.close[0] >= self.sma_long
        ):
            self.order = self.close()
            self.sold_today = False
            self.log(f"=== SHORT SELL TARGET HIT ===")

        # stoploss
        # stoploss will be high of the selling candle and above SMA 200
        elif (
            self.position
            and not self.bought_today
            and self.sold_today
            and self.data.close[0] > self.short_stoploss
            and self.data.close[0] > self.sma_long[0]
        ):
            self.order = self.close()
            self.sold_today = False
            self.log(f"=== SHORT SELL STOPLOSS HIT | LOSER ===")

    def start(self):
        self.opening_amount = self.broker.getvalue()
        self.log(f"--- Opening Amount: {self.opening_amount} ---")

    def stop(self):
        self.log("Ending Value %.2f" % (self.broker.getvalue()))
        self.log(f"--- PNL : {self.broker.getvalue() - self.opening_amount} ---")

        if self.broker.getvalue() > 130000:
            self.log("*** WINNER ***")

        if self.broker.getvalue() < 70000:
            self.log("*** LOSER ***")


if __name__ == "__main__":
    database_path_one_minute = "./databases/app-minute-one.db"
    database_path_fifteen_minute = "./databases/app-minute-fifteen.db"
    database_path_crypto = "./databases/crypto-data.db"
    database_path_five_minute = "./databases/app-minute-five.db"

    # conn = sqlite3.connect(database_path_one_minute)
    conn = sqlite3.connect(database_path_fifteen_minute)
    # conn = sqlite3.connect(database_path_crypto)
    # conn = sqlite3.connect(database_path_five_minute)

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT(stock_id) as stock_id FROM stock_price_minute
    """
    )

    stocks = cursor.fetchall()
    for stock in stocks:
        print(f"*** Testing {stock['stock_id']} ***")
        cerebro = backtrader.Cerebro()
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.010)

        # cerebro.addsizer(backtrader.sizers.PercentSizer, percents=50)

        dataframe = pandas.read_sql(
            """
            select datetime, open, high, low, close, volume
            from stock_price_minute
            where stock_id = :stock_id
            and strftime('%H:%M:%S', datetime) >= '09:30:00' 
            and strftime('%H:%M:%S', datetime) < '16:00:00'
            order by datetime asc
        """,
            conn,
            params={"stock_id": stock["stock_id"]},
            index_col="datetime",
            parse_dates=["datetime"],
        )

        data = backtrader.feeds.PandasData(dataname=dataframe)
        cerebro.adddata(data)
        cerebro.addstrategy(FourtyFourSma)

        # strats = cerebro.optstrategy(OpeningRangeBreakout, num_opening_bars=[15, 30, 60])
        cerebro.addanalyzer(BasicTradeStats)

        stratList = cerebro.run()
        ss = stratList[0]
        s = ss
        for each in ss.analyzers:
            each.print()
        cerebro.plot(style="candlestick")
