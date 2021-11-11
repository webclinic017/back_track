from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from backtrader.indicators import Indicator, And, If, MovAv, ATR


class UpMove(Indicator):

    lines = ('upmove', )

    def __init__(self):
        self.lines.upmove = self.data - self.data(-1)
        super(UpMove, self).__init__()


class DownMove(Indicator):

    lines = ('downmove', )

    def __init__(self):
        self.lines.downmove = self.data(-1) - self.data
        super(DownMove, self).__init__()


class _DirectionalIndicator(Indicator):
    params = (('period', 14), ('movav', MovAv.Smoothed))

    plotlines = dict(plusDI=dict(_name='+DI'), minusDI=dict(_name='-DI'))

    def _plotlabel(self):
        plabels = [self.p.period]
        plabels += [self.p.movav] * self.p.notdefault('movav')
        return plabels

    def __init__(self, _plus=True, _minus=True):
        atr = ATR(self.data, period=self.p.period, movav=self.p.movav)

        upmove = self.data.high - self.data.high(-1)
        downmove = self.data.low(-1) - self.data.low

        if _plus:
            plus = And(upmove > downmove, upmove > 0.0)
            plusDM = If(plus, upmove, 0.0)
            plusDMav = self.p.movav(plusDM, period=self.p.period)

            self.DIplus = 100.0 * plusDMav / atr

        if _minus:
            minus = And(downmove > upmove, downmove > 0.0)
            minusDM = If(minus, downmove, 0.0)
            minusDMav = self.p.movav(minusDM, period=self.p.period)

            self.DIminus = 100.0 * minusDMav / atr

        super(_DirectionalIndicator, self).__init__()


class DirectionalIndicator(_DirectionalIndicator):
    alias = ('DI', )
    lines = (
        'plusDI',
        'minusDI',
    )

    def __init__(self):
        super(DirectionalIndicator, self).__init__()

        self.lines.plusDI = self.DIplus
        self.lines.minusDI = self.DIminus


class PlusDirectionalIndicator(_DirectionalIndicator):

    alias = (('PlusDI', '+DI'), )
    lines = ('plusDI', )

    plotinfo = dict(plotname='+DirectionalIndicator')

    def __init__(self):
        super(PlusDirectionalIndicator, self).__init__(_minus=False)

        self.lines.plusDI = self.DIplus


class MinusDirectionalIndicator(_DirectionalIndicator):
    alias = (('MinusDI', '-DI'), )
    lines = ('minusDI', )

    plotinfo = dict(plotname='-DirectionalIndicator')

    def __init__(self):
        super(MinusDirectionalIndicator, self).__init__(_plus=False)

        self.lines.minusDI = self.DIminus


class AverageDirectionalMovementIndex(_DirectionalIndicator):

    alias = ('ADX', )

    lines = ('adx', )

    plotlines = dict(adx=dict(_name='ADX'))

    def __init__(self):
        super(AverageDirectionalMovementIndex, self).__init__()

        dx = abs(self.DIplus - self.DIminus) / (self.DIplus + self.DIminus)
        self.lines.adx = 100.0 * self.p.movav(dx, period=self.p.period)


class AverageDirectionalMovementIndexRating(AverageDirectionalMovementIndex):

    alias = ('ADXR', )

    lines = ('adxr', )
    plotlines = dict(adxr=dict(_name='ADXR'))

    def __init__(self):
        super(AverageDirectionalMovementIndexRating, self).__init__()

        self.lines.adxr = (self.l.adx + self.l.adx(-self.p.period)) / 2.0


class DirectionalMovementIndex(AverageDirectionalMovementIndex,
                               DirectionalIndicator):

    alias = ('DMI', )


class DirectionalMovement(AverageDirectionalMovementIndexRating,
                          DirectionalIndicator):

    alias = ('DM', )
