import math
import numpy as np

from backtrader import Analyzer
from backtrader.utils import AutoOrderedDict


class BasicTradeStats(Analyzer):
    params = (
        ("calcStatsAfterEveryTrade", False),
        ("filter", "all"),
        ("useStandardPrint", False),
    )

    def nextstart(self):
        o = self.rets
        o.all.firstStrategyTradingDate = self.datas[0].datetime.datetime(0)
        self.next()

    def next(self):
        self.rets.all.lastStrategyTradingDate = self.datas[0].datetime.datetime(0)

    def create_analysis(self):
        if self.p.filter == "long":
            self._tableLongShort = "LONG"
        elif self.p.filter == "short":
            self._tableLongShort = "SHORT"
        elif self.p.filter == "all":
            self._tableLongShort = "TRADES"
        else:
            raise Exception(
                "Parameter 'filter' must be 'long', 'short', or"
                + " 'all' not '%s'." % str(self.p.filter)
            )

        self._all_pnl_list = []
        self._won_pnl_list = []
        self._lost_pnl_list = []
        self._curStreak = None
        self._wonStreak_list = []
        self._lostStreak_list = []

        o = self.rets = AutoOrderedDict()
        o.all.firstStrategyTradingDate = None
        o.all.lastStrategyTradingDate = None

        o.all.trades.total = 0
        o.all.trades.open = 0
        o.all.trades.closed = 0

        o.all.pnl.total = None
        o.all.pnl.average = None

        o.all.streak.zScore = None

        o.all.stats.profitFactor = None
        o.all.stats.winFactor = None
        o.all.stats.winRate = None
        o.all.stats.rewardRiskRatio = None
        o.all.stats.expectancyPercentEstimated = None
        o.all.stats.kellyPercent = None
        o.all.stats.tradesPerYear = None
        o.all.stats.perTradeOpportunityPercent = None
        o.all.stats.annualOpportunityPercent = None
        o.all.stats.annualOpportunityCompoundedPercent = None

        for each in ["won", "lost"]:
            oWL = self.rets[each]
            oWL.trades.closed = 0
            oWL.trades.percent = None
            oWL.pnl.total = None
            oWL.pnl.average = None
            oWL.pnl.median = None
            oWL.pnl.max = None
            oWL.streak.current = 0
            oWL.streak.max = None
            oWL.streak.average = None
            oWL.streak.median = None

    def calculate_statistics(self):
        if self._all_pnl_list != []:
            oA = self.rets.all
            oW = self.rets.won
            oL = self.rets.lost
            oA.pnl.total = np.sum(self._all_pnl_list)
            oA.pnl.average = np.mean(self._all_pnl_list)

            for each in ["won", "lost"]:
                pnlList = eval("self._" + str(each) + "_pnl_list")
                if pnlList != []:
                    oWL = self.rets[each]
                    oWL.trades.closed = np.size(pnlList)
                    oWL.trades.percent = len(pnlList) / len(self._all_pnl_list) * 100
                    oWL.pnl.total = np.sum(pnlList)
                    oWL.pnl.max = np.max(pnlList) if each == "won" else np.min(pnlList)
                    oWL.pnl.average = np.mean(pnlList)
                    oWL.pnl.median = np.median(pnlList)
                    streak = eval("self._" + str(each) + "Streak_list")
                    if streak != []:
                        oWL.streak.max = np.max(streak)
                        oWL.streak.average = np.mean(streak)
                        oWL.streak.median = int(np.median(streak))
            oA.stats.winRate = oW.trades.percent
            if self._won_pnl_list != [] and self._lost_pnl_list != []:
                oA.streak.zScore = self.zScore(
                    oW.trades.closed, oL.trades.closed, len(self._wonStreak_list)
                )
                oA.stats.profitFactor = oW.pnl.total / (-1 * oL.pnl.total)
                oA.stats.winFactor = oW.trades.closed / oL.trades.closed
                if oW.pnl.average != 0:
                    oA.stats.kellyPercent = oA.pnl.average / oW.pnl.average * 100
                if oL.pnl.average != 0:
                    oA.stats.rewardRiskRatio = oW.pnl.average / (-1 * oL.pnl.average)
                    oA.stats.expectancyPercentEstimated = (
                        oA.pnl.average / (-1 * oL.pnl.average) * 100
                    )

            if (
                oA.stats.kellyPercent is not None
                and oA.stats.expectancyPercentEstimated is not None
            ):
                oA.stats.perTradeOpportunityPercent = (
                    (oA.stats.kellyPercent / 100)
                    * (oA.stats.expectancyPercentEstimated / 100)
                    * 100
                )

                _daysStrategyRan = (
                    oA.lastStrategyTradingDate - oA.firstStrategyTradingDate
                ).days
                oA.stats.tradesPerYear = oA.trades.closed * 365 / _daysStrategyRan
                oA.stats.annualOpportunityPercent = (
                    oA.stats.tradesPerYear * oA.stats.perTradeOpportunityPercent
                )

                _power = oA.stats.tradesPerYear
                _value = (oA.stats.perTradeOpportunityPercent / 100) + 1
                oA.stats.annualOpportunityCompoundedPercent = (
                    np.power(_value, _power) - 1
                ) * 100

    def preparation_pre_calculation(self, trade):

        if trade.justopened:
            self.rets.all.trades.total += 1
            self.rets.all.trades.open += 1

        elif trade.status == trade.Closed:
            self.rets.all.trades.open += -1
            self.rets.all.trades.closed += 1
            pnl = trade.pnlcomm
            self._all_pnl_list.append(pnl)
            if pnl >= 0:
                self._won_pnl_list.append(pnl)
                if self._curStreak == "Won":
                    self.rets.won.streak.current += 1
                else:
                    self._curStreak = "Won"
                    self._lostStreak_list.append(self.rets.lost.streak.current)
                    self.rets.lost.streak.current = 0
                    self.rets.won.streak.current += 1
            else:
                self._lost_pnl_list.append(pnl)
                if self._curStreak == "Lost":
                    self.rets.lost.streak.current += 1

                else:
                    self._curStreak = "Lost"
                    self._wonStreak_list.append(self.rets.won.streak.current)
                    self.rets.won.streak.current = 0
                    self.rets.lost.streak.current += 1

    def notify_trade(self, trade):

        longMatch = trade.long and self.p.filter == "long"
        shortMatch = not trade.long and self.p.filter == "short"
        allMatch = self.p.filter == "all"

        if True in [longMatch, shortMatch, allMatch]:
            self.preparation_pre_calculation(trade)

            if self.p.calcStatsAfterEveryTrade:
                self.calculate_statistics()

    def stop(self):
        self.calculate_statistics()
        self._all_pnl_list = []
        self._won_pnl_list = []
        self._lost_pnl_list = []
        self._curStreak = None
        self._wonStreak_list = []
        self._lostStreak_list = []

        self.rets._close()

    def zScore(self, wins, losses, streaks):
        w = wins
        L = losses
        s = streaks
        n = w + L
        x = 2 * w * L

        denominator = math.sqrt((x * (x - n)) / (n - 1))
        if denominator != 0:
            numerator = n * (s - 0.5) - x
            z = numerator / denominator
            return z

        return None

    def print(self, *args, **kwargs):
        if self.p.useStandardPrint:
            super().print(*args, **kwargs)
            return
        oAt = self.rets.all.trades
        oAp = self.rets.all.pnl
        oAs = self.rets.all.stats
        oAk = self.rets.all.streak
        oWt = self.rets.won.trades
        oWp = self.rets.won.pnl
        oWk = self.rets.won.streak
        oLt = self.rets.lost.trades
        oLp = self.rets.lost.pnl
        oLk = self.rets.lost.streak
        dpsf = self.dpsf
        d = [
            {"rowType": "table-top"},
            {
                "rowType": "row-title",
                "data": [
                    "",
                    "ALL " + self._tableLongShort,
                    "",
                    self._tableLongShort + " WON",
                    self._tableLongShort + " LOST",
                ],
            },
            {"rowType": "table-seperator"},
            {
                "rowType": "row-data",
                "data": [
                    "TRADES       open",
                    dpsf(oAt.open),
                    "TRADES          ",
                    "",
                    "",
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "closed",
                    dpsf(oAt.closed),
                    "closed",
                    dpsf(oWt.closed),
                    dpsf(oLt.closed),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "Win Factor",
                    dpsf(oAs.winFactor, dp=2),
                    "%",
                    dpsf(oWt.percent, dp=2),
                    dpsf(oLt.percent, dp=2),
                ],
            },
            {
                "rowType": "row-data",
                "data": ["Trades per year", dpsf(oAs.tradesPerYear, dp=1), "", "", ""],
            },
            {"rowType": "table-seperator"},
            {
                "rowType": "row-data",
                "data": [
                    "PROFIT      total",
                    dpsf(oAp.total, dp=2),
                    "PROFIT     total",
                    dpsf(oWp.total, dp=2),
                    dpsf(oLp.total, dp=2),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "average",
                    dpsf(oAp.average, dp=2),
                    "average",
                    dpsf(oWp.average, dp=2),
                    dpsf(oLp.average, dp=2),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "Profit Factor",
                    dpsf(oAs.profitFactor, dp=2),
                    "median",
                    dpsf(oWp.median, dp=2),
                    dpsf(oLp.median, dp=2),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "Reward : Risk",
                    dpsf(oAs.rewardRiskRatio, dp=2),
                    "max",
                    dpsf(oWp.max, dp=2),
                    dpsf(oLp.max, dp=2),
                ],
            },
            {"rowType": "table-seperator"},
            {
                "rowType": "row-data",
                "data": [
                    "Kelly %",
                    dpsf(oAs.kellyPercent, dp=1),
                    "STREAK   current",
                    dpsf(oWk.current),
                    dpsf(oLk.current),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "Expectancy %",
                    dpsf(oAs.expectancyPercentEstimated, dp=1),
                    "max",
                    dpsf(oWk.max),
                    dpsf(oLk.max),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "TO %",
                    dpsf(oAs.perTradeOpportunityPercent, dp=2),
                    "average",
                    dpsf(oWk.average, dp=2),
                    dpsf(oLk.average, dp=2),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "AO %",
                    dpsf(oAs.annualOpportunityPercent, dp=1),
                    "median",
                    dpsf(oWk.median),
                    dpsf(oLk.median),
                ],
            },
            {
                "rowType": "row-data",
                "data": [
                    "AOC %",
                    dpsf(oAs.annualOpportunityCompoundedPercent, dp=1),
                    "Z-Score",
                    dpsf(oAk.zScore, dp=1),
                    dpsf(oAk.zScore, dp=1),
                ],
            },
            {"rowType": "table-bottom"},
        ]

        s = self.displayTable(d)
        print(s)

    def fixedWidthText(self, string, nChars=15, align="centre"):
        string = str(string)
        _s = " " * nChars + string + " " * nChars

        if align == "left" or align == "l":
            return _s[nChars : nChars + nChars]

        elif align == "right" or align == "r":
            return _s[len(string) : nChars + len(string)]

        elif align == "centre" or align == "center" or align == "c":
            startIndex = nChars - (int((nChars - len(string)) / 2))
            return _s[startIndex : startIndex + nChars]

        else:
            raise Exception(
                "Parameter 'align' must be 'left', 'right', or 'center' not '%s'."
                % str(align)
            )

    def displayTable(self, i):
        fWT = self.fixedWidthText
        cs = [0, 0, 0, 0, 0]

        for d in i:
            if d["rowType"] in ["row-title", "row-data", "row-data2"]:

                for c in range(5):
                    _l = len(str(d["data"][c]))
                    if _l > cs[c]:
                        cs[c] = _l
        (x, rx, lx, v, h) = ("╬", "╣", "╠", "║", "═")
        (sv, hx, srx) = (" " + v, h + x, h + "╣")

        s = ""
        for d in i:
            if d["rowType"] == "table-top":
                s += (
                    "╔═"
                    + "═" * cs[0]
                    + "╦"
                    + "═" * cs[1]
                    + "═╗"
                    + "  ╔═"
                    + "═" * cs[2]
                    + "╦"
                    + "═" * cs[3]
                    + "═╦"
                    + "═" * cs[4]
                    + "═╗\n"
                )
            if d["rowType"] == "table-seperator":
                s += (
                    "╠═"
                    + "═" * cs[0]
                    + "╬"
                    + "═" * cs[1]
                    + "═╣"
                    + "  ╠═"
                    + "═" * cs[2]
                    + "╬"
                    + "═" * cs[3]
                    + "═╬"
                    + "═" * cs[4]
                    + "═╣\n"
                )
            if d["rowType"] == "table-bottom":
                s += (
                    "╚═"
                    + "═" * cs[0]
                    + "╩"
                    + "═" * cs[1]
                    + "═╝"
                    + "  ╚═"
                    + "═" * cs[2]
                    + "╩"
                    + "═" * cs[3]
                    + "═╩"
                    + "═" * cs[4]
                    + "═╝"
                )

            if d["rowType"] == "row-title":
                l = d["data"]
                s += (
                    v
                    + fWT(l[0], cs[0])
                    + sv
                    + fWT(l[1], cs[1], "center")
                    + sv
                    + "  "
                    + v
                    + fWT(l[2], cs[2])
                    + sv
                    + fWT(l[3], cs[3], "center")
                    + sv
                    + fWT(l[4], cs[4], "center")
                    + sv
                    + "\n"
                )

            if d["rowType"] == "row-data":
                l = d["data"]
                s += (
                    v
                    + fWT(l[0], cs[0], "right")
                    + sv
                    + fWT(l[1], cs[1], "left")
                    + sv
                    + "  "
                    + v
                    + fWT(l[2], cs[2], "right")
                    + sv
                    + fWT(l[3], cs[3], "left")
                    + sv
                    + fWT(l[4], cs[4], "left")
                    + sv
                    + "\n"
                )

            if d["rowType"] == "row-data2":
                l = d["data"]
                s += (
                    v
                    + fWT(l[0], cs[0], "center")
                    + sv
                    + fWT(l[1], cs[1], "left")
                    + sv
                    + "  "
                    + v
                    + fWT(l[2], cs[2], "right")
                    + sv
                    + fWT(l[3], cs[3], "left")
                    + sv
                    + fWT(l[4], cs[4], "left")
                    + sv
                    + "\n"
                )

        return s

    def dpsf(self, n=None, dp=None, sf=None):
        if n == None:
            return "None"
        if dp != None:
            _st = f"{dp}"
            _st = ("%." + _st + "f") % n
            return _st
        else:
            return str(n)
