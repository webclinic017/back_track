from backtrader.indicators import (
    Indicator,
    MovAv,
    RelativeStrengthIndex,
    Highest,
    Lowest,
)


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
