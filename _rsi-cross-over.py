from __future__ import absolute_import, division, print_function, unicode_literals
import backtrader
import pandas
import sqlite3
from analyzers.trade_statistics import BasicTradeStats
from indicators.swing import SwingInd
from indicators.swing_line import SwingLine


class RsiCrossOver(backtrader.Strategy):
    params = dict(
        upperband=70,
        safelow=50,
        lowerband=30,
        ema=200,
        period=14,
        buying_price=0,
        selling_price=0,
        long_target=0,
        short_target=0,
        long_stoploss=0,
        short_stoploss=0,
    )

    def __init__(self):
        self.order = None
        self.bought_today = False
        self.sold_today = False
        self.rsi = backtrader.indicators.RSI(
            self.data,
            upperband=self.p.upperband,
            lowerband=self.p.lowerband,
        )

        self.ema = backtrader.indicators.EMA(period=self.p.ema, plot=True)
        self.crossover = backtrader.ind.CrossOver(backtrader.ind.RSI(), 50.0, plot=True)
        self.swingline = SwingLine(self.data, plot=True)

    def log(self, txt, dt=None):
        if dt is None:
            dt = self.datas[0].datetime.datetime()

        print("%s, %s" % (dt, txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            order_details = (
                f"{order.executed.price}, {order.executed.value}, {order.executed.comm}"
            )

            if order.isbuy():
                self.p.buying_price = order.executed.price + order.executed.comm
                self.p.long_target = self.p.buying_price + (
                    (self.p.buying_price - self.p.long_stoploss) * 1.5
                )
                self.log(f"BUY EXECUTED, {order_details}")

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

        # buy long
        if (
            not self.position
            and not self.bought_today
            and not self.sold_today
            and self.data.close[0] > self.ema[0]
            and self.crossover[0] > 0
        ):
            self.order = self.buy()
            self.long_stoploss = 0  # nearest swing high
            self.bought_today = True

        # target
        # 1.5:1
        elif (
            self.position
            and self.bought_today
            and not self.sold_today
            and self.data.close[0] > self.long_target
        ):
            self.order = self.close()
            self.bought_today = False

        # stoploss
        # nearest swing low
        elif (
            self.position
            and not self.sold_today
            and not self.bought_today
            and self.data.close[0] < self.long_stoploss
            and self.data.close[0] < self.ema
        ):
            self.order = self.close()
            self.bought_today = False

        # short sell
        if (
            not self.position
            and not self.bought_today
            and not self.sold_today
            and self.data.close[0] < self.ema[0]
            and self.crossover < 0
        ):
            self.order = self.sell()
            self.short_stoploss = 0  # nearest swing high
            self.sold_today = True

        # target
        # 1.5:1
        elif (
            self.position
            and not self.bought_today
            and self.sold_today
            and self.data.close[0] < self.short_target
        ):
            self.order = self.close()
            self.sold_today = False
            self.bought_today = False

        # stoploss
        # nearest swing high
        elif (
            self.position
            and not self.sold_today
            and not self.bought_today
            and self.data.close[0] > self.short_stoploss
            and self.data.close[0] > self.ema
        ):
            self.order = self.close()
            self.sold_today = False

    def start(self):
        self.opening_amount = self.broker.getvalue()
        self.log(f"--- Opening Amount: {self.opening_amount} ---")

    def stop(self):
        self.log("Ending Value %.2f" % (self.broker.getvalue()))
        self.log(
            f"--- Profit[if the value +]/Lose [if the value -] : {self.broker.getvalue() - 100000} ---"
        )

        if self.broker.getvalue() > 130000:
            self.log("*** BIG WINNER ***")

        if self.broker.getvalue() < 70000:
            self.log("*** MAJOR LOSER ***")


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

        # cerebro.addsizer(backtrader.sizers.PercentSizer, percents=95)

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
        cerebro.addstrategy(RsiCrossOver)

        # strats = cerebro.optstrategy(OpeningRangeBreakout, num_opening_bars=[15, 30, 60])
        cerebro.addanalyzer(BasicTradeStats)

        stratList = cerebro.run()
        ss = stratList[0]
        s = ss
        for each in ss.analyzers:
            each.print()
        cerebro.plot(style="candlestick")
