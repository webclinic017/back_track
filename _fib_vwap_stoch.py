from __future__ import absolute_import, division, print_function, unicode_literals
import backtrader
import pandas
import sqlite3
from analyzers.trade_statistics import BasicTradeStats
from backtrader.indicators import (
    Indicator,
    MovAv,
    RelativeStrengthIndex,
    Highest,
    Lowest,
)


class FibonacciPivotPoint(backtrader.Indicator):

    lines = ("p", "s1", "s2", "s3", "r1", "r2", "r3")
    plotinfo = dict(subplot=False)
    params = (
        ("open", False),  # add opening price to the pivot point
        ("close", False),  # use close twice in the calcs
        ("_autoplot", True),  # attempt to plot on real target data
        ("level1", 0.382),
        ("level2", 0.618),
        ("level3", 1.0),
    )

    def __init__(self):
        o = self.data.open
        h = self.data.high  # current high
        l = self.data.low  # current high
        c = self.data.close  # current high

        if self.p.close:
            self.lines.p = p = (h + l + 2.0 * c) / 4.0
        elif self.p.open:
            self.lines.p = p = (h + l + c + o) / 4.0
        else:
            self.lines.p = p = (h + l + c) / 3.0

        self.lines.s1 = p - self.p.level1 * (h - l)
        self.lines.s2 = p - self.p.level2 * (h - l)
        self.lines.s3 = p - self.p.level3 * (h - l)

        self.lines.r1 = p + self.p.level1 * (h - l)
        self.lines.r2 = p + self.p.level2 * (h - l)
        self.lines.r3 = p + self.p.level3 * (h - l)


class VolumeWeightedAveragePrice(backtrader.Indicator):
    plotinfo = dict(subplot=False)

    params = (('period', 30), )

    alias = (
        'VWAP',
        'VolumeWeightedAveragePrice',
    )
    lines = ('VWAP', )
    plotlines = dict(VWAP=dict(alpha=0.50, linestyle='-.', linewidth=2.0))

    def __init__(self):
        cumvol = backtrader.ind.SumN(self.data.volume, period=self.p.period)
        typprice = ((self.data.close + self.data.high + self.data.low) /
                    3) * self.data.volume
        cumtypprice = backtrader.ind.SumN(typprice, period=self.p.period)
        self.lines[0] = cumtypprice / cumvol

        super(VolumeWeightedAveragePrice, self).__init__()


class StochasticRSI(Indicator):
    lines = ("fastk", "fastd")

    params = (
        ("k_period", 3),
        ("d_period", 3),
        ("rsi_period", 14),
        ("stoch_period", 14),
        ("movav", MovAv.Simple),
        ("rsi", RelativeStrengthIndex),
        ("upperband", 80.0),
        ("lowerband", 20.0),
    )

    plotlines = dict(percD=dict(_name="%D", ls="--"), percK=dict(_name="%K"))

    def _plotlabel(self):
        plabels = [
            self.p.k_period,
            self.p.d_period,
            self.p.rsi_period,
            self.p.stoch_period,
        ]
        plabels += [self.p.movav] * self.p.notdefault("movav")
        return plabels

    def _plotinit(self):
        self.plotinfo.plotyhlines = [self.p.upperband, self.p.lowerband]

    def __init__(self):
        rsi_hh = Highest(self.p.rsi(period=self.p.rsi_period),
                         period=self.p.stoch_period)
        rsi_ll = Lowest(self.p.rsi(period=self.p.rsi_period),
                        period=self.p.stoch_period)
        knum = self.p.rsi(period=self.p.rsi_period) - rsi_ll
        kden = rsi_hh - rsi_ll

        self.k = self.p.movav(100.0 * (knum / kden), period=self.p.k_period)
        self.d = self.p.movav(self.k, period=self.p.d_period)

        self.lines.fastk = self.k
        self.lines.fastd = self.d


class OpenHigh_OpenLow(backtrader.Strategy):
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
        self.pivot = FibonacciPivotPoint(self.data, plot=True)
        self.vwap = VolumeWeightedAveragePrice(self.data, plot=True)
        self.stochastic_rsi = StochasticRSI(self.data, plot=True)

    def log(self, txt, dt=None):
        if dt is None:
            dt = self.datas[0].datetime.datetime()

        print("%s, %s" % (dt, txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            order_details = f" Price: {order.executed.price}, Cost: {order.executed.value}, Commission: {order.executed.comm}"

            if order.isbuy():
                self.buying_price = order.executed.price + order.executed.comm
                self.long_target = self.buying_price + (
                    (self.buying_price - self.long_stoploss) * 1.69)
                self.log(f"BUY EXECUTED:  {order_details}")

            elif order.issell():
                self.selling_price = order.executed.price - order.executed.comm
                self.short_target = self.selling_price - (
                    (self.short_stoploss - self.selling_price) * 1.69)
                self.log(f"*** SELL EXECUTED: {order_details} ***")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def next(self):
        if self.order:
            return

        # long buy
        # cmp should be just above pivots
        # cmp should be just above vwap
        # stoch fastk > stoch fastd
        if (not self.position and not self.bought_today and not self.sold_today
                and self.data.close[0] > self.vwap[0] and
            (self.data.close[0] >
             (self.pivot.lines.p or self.pivot.lines.s1 or self.pivot.lines.s2
              or self.pivot.lines.s3 or self.pivot.lines.r1
              or self.pivot.lines.r2 or self.pivot.lines.r3))
                and self.stochastic_rsi.fastk > self.stochastic_rsi.fastd):
            self.order = self.buy()
            # below previews candle low and vwap(which ever is low)
            if self.data.low[-1] < self.vwap[-1]:
                self.long_stoploss = self.data.low[-1]
            elif self.vwap[-1] < self.data.low[-1]:
                self.long_stoploss = self.vwap[-1]
            self.bought_today = True
            self.log(f"=== LONG BUY EXECUTED ===")

        # target
        # RRR: 1.5:1
        elif (self.position and self.bought_today and not self.sold_today
              and self.data.close[0] > self.long_target):
            self.order = self.close()
            self.bought_today = False
            self.log(f"=== LONG BUY TARGET HIT  ===")

        # stoploss
        elif (self.position and not self.sold_today and self.bought_today
              and self.data.close[0] < self.long_stoploss):
            self.order = self.close()
            self.bought_today = False
            self.log(f"=== LONG BUY STOPLOSS HIT | LOSER ===")

        # short sell
        if (not self.position and not self.sold_today and not self.bought_today
                and (self.data.close[0] > self.pivot.lines.s1
                     and self.data.close[0] < self.vwap[0])):
            self.order = self.sell()
            if self.data.high[-1] < self.vwap[-1]:
                self.short_stoploss = self.data.high[-1]
            elif self.vwap[-1] < self.data.high[-1]:
                self.short_stoploss = self.vwap[-1]
            self.sold_today = True
            self.log(f"=== SHORT SELL EXECUTED ===")

        # target
        elif (self.position and self.sold_today and not self.bought_today
              and self.data.close[0] < self.short_target):
            self.order = self.close()
            self.sold_today = False
            self.log(f"=== SHORT SELL TARGET HIT ===")

        # stoploss
        elif (self.position and self.sold_today and not self.bought_today
              and self.data.close[0] > self.short_stoploss):
            self.order = self.close()
            self.sold_today = False
            self.log(f"=== SHORT SELL STOPLOSS HIT | LOSER ===")

    def start(self):
        self.opening_amount = self.broker.getvalue()
        self.log(f"[ Broker Balance: {self.opening_amount} ]")

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
    # conn = sqlite3.connect(database_path_fifteen_minute)
    # conn = sqlite3.connect(database_path_crypto)
    conn = sqlite3.connect(database_path_five_minute)

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
        cerebro.addstrategy(OpenHigh_OpenLow)

        cerebro.addanalyzer(BasicTradeStats)
        # strats = cerebro.optstrategy(OpeningRangeBreakout, num_opening_bars=[15, 30, 60])
        stratList = cerebro.run()
        ss = stratList[0]
        s = ss
        for each in ss.analyzers:
            each.print()
        cerebro.plot(style="candlestick")
