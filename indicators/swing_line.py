import backtrader


class SwingLine(backtrader.Indicator):
    lines = ('swingline', )

    params = dict(swing_low=0, swing_high=0)

    def __init__(self):
        pass

    def next(self):
        try:
            if (self.data.high[0] > self.data.high[1] and self.data.high[-1]
                ) and (self.data.high[0] > self.data.high[2]
                       and self.data.high[-2]):
                self.lines.swingline[0] = 1
                self.p.swing_high = self.data.high[0]
            elif (self.data.low[0] < self.data.low[1] and
                  self.data.low[-1]) and (self.data.low[0] < self.data.low[2]
                                          and self.data.low[-2]):
                self.lines.swingline[0] = -1
                self.p.swing_low = self.data.low[0]
            else:
                self.lines.swingline[0] = 0
        except:
            pass