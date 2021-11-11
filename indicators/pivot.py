import backtrader


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