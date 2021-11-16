from __future__ import absolute_import, division, print_function, unicode_literals
import backtrader
import pandas
import sqlite3
from indicators.dmi import DirectionalMovementIndex
from analyzers.trade_statistics import BasicTradeStats
from datetime import date, datetime, time, timedelta


class SupertrendEMA(backtrader.Strategy):
    params = dict(ema=200, num_opening_bars=15)

    def __init__(self):
        self.order = None
        self.bought_today = False
        self.sold_today = False
        self.buying_price = 0
        self.selling_price = 0
        self.long_stoploss = 0
        self.short_stoploss = 0
        self.ema = backtrader.indicators.EMA(period=self.p.ema, plot=True)
        self.adx = DirectionalMovementIndex(self.data, plot=True)

    def log(self, txt, dt=None):
        if dt is None:
            dt = self.datas[0].datetime.datetime()

        print("%s, %s" % (dt, txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            order_details = f"{order.executed.price}, Cost: {order.executed.value}, Commission: {order.executed.comm}"

            if order.isbuy():
                self.log(f"*** BUY EXECUTED, Price: {order_details} ***")

            elif order.issell():
                self.log(f"*** SELL EXECUTED, Price: {order_details} ***")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def next(self):
        if self.order:
            return

        current_bar_datetime = self.data.num2date(self.data.datetime[0])
        previous_bar_datetime = self.data.num2date(self.data.datetime[-1])

        if current_bar_datetime.date() != previous_bar_datetime.date():
            self.opening_range_low = self.data.low[0]
            self.opening_range_high = self.data.high[0]
            self.bought_today = False

        opening_range_start_time = time(9, 30, 0)
        dt = datetime.combine(date.today(),
                              opening_range_start_time) + timedelta(
                                  minutes=self.p.num_opening_bars)
        opening_range_end_time = dt.time()

        if (current_bar_datetime.time() >= opening_range_start_time
                and current_bar_datetime.time() < opening_range_end_time):
            self.opening_range_high = max(self.data.high[0],
                                          self.opening_range_high)
            self.opening_range_low = min(self.data.low[0],
                                         self.opening_range_low)
            self.opening_range = self.opening_range_high - self.opening_range_low

        else:
            if (not self.position and not self.bought_today
                    and not self.sold_today and self.data.close[0] > self.ema
                    and self.data.close[0] > self.opening_range_high):
                self.order = self.buy()
                self.bought_today = True

            elif (self.position and self.bought_today and not self.sold_today
                  and self.data.close[0] < self.ema):
                self.order = self.close()
                self.bought_today = False

            if (not self.position and not self.bought_today
                    and not self.sold_today and self.data.close[0] < self.ema
                    and self.data.close[0] < self.opening_range_high):
                self.order = self.sell()
                self.sold_today = True

            if (self.position and self.sold_today and not self.bought_today
                    and self.data.close[0] > self.ema):
                self.order = self.close()
                self.sold_today = False

    def start(self):
        self.opening_amount = self.broker.getvalue()
        self.log(f"[ Broker Balance: {self.opening_amount}]")

    def stop(self):
        self.log(f" [Broker Balance: {self.broker.getvalue()}] ")
        self.log(
            f"--- PNL: {self.broker.getvalue() - self.opening_amount} ---")

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
    cursor.execute("""
        SELECT DISTINCT(stock_id) as stock_id FROM stock_price_minute
    """)

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
        cerebro.addstrategy(SupertrendEMA)
        cerebro.addanalyzer(BasicTradeStats)

        # strats = cerebro.optstrategy(OpeningRangeBreakout, num_opening_bars=[15, 30, 60])
        stratList = cerebro.run()
        ss = stratList[0]
        s = ss
        for each in ss.analyzers:
            each.print()
        cerebro.plot(style="candlestick")
