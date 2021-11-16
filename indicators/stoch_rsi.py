import backtrader


class StochRSI(backtrader.Indicator):
    lines = ('stochrsi', )
    params = dict(
        period=14,  # to apply to RSI
        pperiod=None,  # if passed apply to HighestN/LowestN, else "period"
    )

    def __init__(self):
        rsi = backtrader.ind.RSI(self.data, period=self.p.period)

        pperiod = self.p.pperiod or self.p.period
        maxrsi = backtrader.ind.Highest(rsi, period=pperiod)
        minrsi = backtrader.ind.Lowest(rsi, period=pperiod)

        self.l.stochrsi = (rsi - minrsi) / (maxrsi - minrsi)
        self.l.stochmin = ''
