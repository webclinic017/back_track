from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader


class PivotPoint(backtrader.Indicator):

    lines = (
        "p",
        "s1",
        "s2",
        "r1",
        "r2",
    )
    plotinfo = dict(subplot=False)

    params = (
        ("open", False),  # add opening price to the pivot point
        ("close", False),  # use close twice in the calcs
        ("_autoplot", True),  # attempt to plot on real target data
    )

    def _plotinit(self):
        # Try to plot to the actual timeframe master
        if self.p._autoplot:
            if hasattr(self.data, "data"):
                self.plotinfo.plotmaster = self.data.data

    def __init__(self):
        o = self.data.open
        h = self.data.high  # current high
        l = self.data.low  # current low
        c = self.data.close  # current close

        if self.p.close:
            self.lines.p = p = (h + l + 2.0 * c) / 4.0
        elif self.p.open:
            self.lines.p = p = (h + l + c + o) / 4.0
        else:
            self.lines.p = p = (h + l + c) / 3.0

        self.lines.s1 = 2.0 * p - h
        self.lines.r1 = 2.0 * p - l

        self.lines.s2 = p - (h - l)
        self.lines.r2 = p + (h - l)

        super(PivotPoint, self).__init__()  # enable coopertive inheritance

        if self.p._autoplot:
            self.plotinfo.plot = False  # disable own plotting
            self()  # Coupler to follow real object


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

    def _plotinit(self):
        # Try to plot to the actual timeframe master
        if self.p._autoplot:
            if hasattr(self.data, "data"):
                self.plotinfo.plotmaster = self.data.data

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

        super(FibonacciPivotPoint, self).__init__()

        if self.p._autoplot:
            self.plotinfo.plot = False  # disable own plotting
            self()  # Coupler to follow real object


class DemarkPivotPoint(backtrader.Indicator):

    lines = (
        "p",
        "s1",
        "r1",
    )
    plotinfo = dict(subplot=False)
    params = (
        ("open", False),  # add opening price to the pivot point
        ("close", False),  # use close twice in the calcs
        ("_autoplot", True),  # attempt to plot on real target data
        ("level1", 0.382),
        ("level2", 0.618),
        ("level3", 1.0),
    )

    def _plotinit(self):
        # Try to plot to the actual timeframe master
        if self.p._autoplot:
            if hasattr(self.data, "data"):
                self.plotinfo.plotmaster = self.data.data

    def __init__(self):
        x1 = self.data.high + 2.0 * self.data.low + self.data.close
        x2 = 2.0 * self.data.high + self.data.low + self.data.close
        x3 = self.data.high + self.data.low + 2.0 * self.data.close

        x = backtrader.CmpEx(self.data.close, self.data.open, x1, x2, x3)
        self.lines.p = x / 4.0

        self.lines.s1 = x / 2.0 - self.data.high
        self.lines.r1 = x / 2.0 - self.data.low

        super(DemarkPivotPoint, self).__init__()

        if self.p._autoplot:
            self.plotinfo.plot = False  # disable own plotting
            self()  # Coupler to follow real object