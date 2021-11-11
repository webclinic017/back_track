import backtrader


class SwingInd(backtrader.Indicator):
    lines = ('swings', 'signal')
    params = dict(period=7, sl=0, sh=0)

    def __init__(self):

        #Set the swing range - The number of bars before and after the swing
        #needed to identify a swing
        self.swing_range = (self.p.period * 2) + 1
        self.addminperiod(self.swing_range)

    def next(self):
        #Get the highs/lows for the period
        highs = self.data.high.get(size=self.swing_range)
        lows = self.data.low.get(size=self.swing_range)
        #check the bar in the middle of the range and check if greater than rest
        if highs.pop(self.p.period) > max(highs):
            self.lines.swings[-self.p.period] = 1  #add new swing
            self.p.sh = self.data.high[0]
            self.lines.signal[0] = 1  #give a signal
        elif lows.pop(self.p.period) < min(lows):
            self.lines.swings[-self.p.period] = -1  #add new swing
            self.p.sl = self.data.low[0]
            self.lines.signal[0] = -1  #give a signal
        else:
            self.lines.swings[-self.p.period] = 0
            self.lines.signal[0] = 0