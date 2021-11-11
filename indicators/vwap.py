import backtrader


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