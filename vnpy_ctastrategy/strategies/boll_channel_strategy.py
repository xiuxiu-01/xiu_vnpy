from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)


class BollChannelStrategy(CtaTemplate):
    """"""

    author = "用Python的交易员"

    boll_window = 18
    boll_dev = 3.4
    cci_window = 10
    atr_window = 30
    sl_multiplier = 5.2
    fixed_size = 1

    boll_up = 0
    boll_down = 0
    cci_value = 0
    atr_value = 0

    intra_trade_high = 0
    intra_trade_low = 0
    long_stop = 0
    short_stop = 0

    parameters = [
        "boll_window",
        "boll_dev",
        "cci_window",
        "atr_window",
        "sl_multiplier",
        "fixed_size"
    ]
    variables = [
        "boll_up",
        "boll_down",
        "cci_value",
        "atr_value",
        "intra_trade_high",
        "intra_trade_low",
        "long_stop",
        "short_stop"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar, 15, self.on_15min_bar)
        self.am = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(10)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg.update_bar(bar)

    def on_15min_bar(self, bar: BarData):
        """"""
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        self.boll_up, self.boll_down = am.boll(self.boll_window, self.boll_dev)
        self.cci_value = am.cci(self.cci_window)
        self.atr_value = am.atr(self.atr_window)

        if self.pos == 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price

            if self.cci_value > 0:
                self.buy(self.boll_up, self.fixed_size, True)
            elif self.cci_value < 0:
                self.short(self.boll_down, self.fixed_size, True)

        elif self.pos > 0:
            self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
            self.intra_trade_low = bar.low_price

            self.long_stop = self.intra_trade_high - self.atr_value * self.sl_multiplier
            self.sell(self.long_stop, abs(self.pos), True)

        elif self.pos < 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = min(self.intra_trade_low, bar.low_price)

            self.short_stop = self.intra_trade_low + self.atr_value * self.sl_multiplier
            self.cover(self.short_stop, abs(self.pos), True)

        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass
from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
from vnpy.trader.constant import Exchange, Interval
from datetime import time
import talib
# 策略开始运行时执行该函数一次
import pandas as pd
import talib
import math
def conv_atr(valu, mintick):
    a = 0
    num = mintick
    s = valu
    if pd.isna(s):
        s = mintick
    if num < 1:
        for i in range(1, 21):
            num *= 10
            if num > 1:
                break
            a += 1
    for x in range(a):
        s *= 10
    s = round(s)
    for x in range(a):
        s /= 10
    s = max(s, mintick)
    return s
# 定义nz函数，用于处理None值
def nz(value, default=0):
    return default if value is None else value
# 定义change函数，检查列表中最后两个值是否不同
def change(series):
    """比较列表中当前元素和前一个元素的值来检测变化"""
    if len(series) > 1:
        return series[-1] != series[-2]
    return False
def f_Brickhigh(trend, icloseprice, iopenprice, box, Length):
    if len(trend) > 1 and trend[-1] == 1:
        _l = math.floor((icloseprice[-1] - iopenprice[-1]) / box[-1]) - 1
        _ret = True
        if _l < Length:
            for x in range(min(3000, len(trend) - 1)):
                if trend[-(x+2)] != trend[-(x+1)]:  # 检查历史趋势变化
                    if trend[-(x+1)] == 1:
                        if icloseprice[-(x+1)] >= icloseprice[-1]:
                            _ret = False
                            break
                        _l += math.floor((icloseprice[-(x+1)] - iopenprice[-(x+1)]) / box[-(x+1)])
                    if trend[-(x+1)] == -1:
                        start = icloseprice[-(x+1)] + box[-(x+1)]
                        forlen = math.floor((iopenprice[-(x+1)] - icloseprice[-(x+1)]) / box[-(x+1)]) - 1
                        for i in range(forlen + 1):
                            if start < icloseprice[-1]:
                                _l += 1
                            start += box[-(x+1)]
                    if _l >= Length:
                        _ret = True
                        break
                else:
                    _ret = False
                    break
        return _ret
    return False
def f_Bricklow(trend, icloseprice, iopenprice, box, Length):
    if len(trend) > 1 and trend[-1] == -1:
        _l = math.floor((iopenprice[-1] - icloseprice[-1]) / box[-1]) - 1
        _ret = True
        if _l < Length:
            for x in range(min(3000, len(trend) - 1)):
                if trend[-(x+2)] != trend[-(x+1)]:  # 检查历史趋势变化
                    if trend[-(x+1)] == -1:
                        if icloseprice[-(x+1)] <= icloseprice[-1]:
                            _ret = False
                            break
                        _l += math.floor((iopenprice[-(x+1)] - icloseprice[-(x+1)]) / box[-(x+1)])
                    if trend[-(x+1)] == 1:
                        start = icloseprice[-(x+1)] - box[-(x+1)]
                        forlen = math.floor((icloseprice[-(x+1)] - iopenprice[-(x+1)]) / box[-(x+1)]) - 1
                        for i in range(forlen + 1):
                            if start > icloseprice[-1]:
                                _l += 1
                            start -= box[-(x+1)]
                    if _l >= Length:
                        _ret = True
                        break
                else:
                    _ret = False
                    break
        return _ret
    return False
def mysma(ser, length):
    if length <= 0:
        return None

    sum_val = ser[-1]
    nn = 1
    for i in range(1, min(4001, len(ser))):
        if i >= len(ser):
            break
        if ser[-(i+1)] is None or ser[-i] is None:
            break
        if ser[-(i+1)] != ser[-i]:
            nn += 1
            sum_val += ser[-(i+1)]
            if nn == length:
                break
    return sum_val / length if nn == length else None
class renkochartsStrategy(CtaTemplate):
    """"""
    g_params={}
    author = "咻咻咻"
    trailing_long =0.4
    trailing_short =0.4
    intra_trade_high = 0
    intra_trade_low = 0
    
    modevalue =14 # 参数示例
    Length = 3  # 参数示例
    reversal =11  # 逆转值

    boxsize =5 # 参数示例\
    g_params['mode'] = 'ATR'    # 参数示例
    g_params['source'] = 'hl'   # 参数示例
    g_params['showstyle'] = 'Area'   # 参数示例
    g_params['breakoutcolor'] = 'Blue/Red'   # 参数示例
    g_params['changebarcol'] = True   # 参数示例
    
    g_params['showbreakout'] = True   # 参数示例

    box = [None]  # 初始值为None
    trend = [0]  # 初始值为0
    currentprice = [0.0]  # 初始值
    beginprice = [None]  # 初始值为None
    iopenprice = [0.0]
    icloseprice = [0.0]
    numcell =[ None]
    nok = [True]

    top =[ 0.0]
    bottom = [0.0]
    oprice=[0]
    chigh= [None]
    clow= [None]
    ctrend= [0]
    switch = [0]
    setA =[0]
    setB = [0]
    botrend = [0]
    trcnt1=[0]
    countch=[0]
    trch = [False]
    em=[None]
    tema=[None]
    obox=[None]
    TrendUp=[0]
    TrendDown=[0]
    waitit=[0]
    mtrend = [0]
    Tsl=[None]
    Tsl2=[None]
    fixed_size=1
    atrboxsize=0
    exit_time = time(hour=14, minute=55)
    setup_coef = 0.25
    break_coef = 0.2
    enter_coef_1 = 1.07
    enter_coef_2 = 0.07
    fixed_size = 1
    donchian_window = 30

    trailing_long = 0.4
    trailing_short = 0.4
    multiplier = 3

    buy_break = 0   # 突破买入价
    sell_setup = 0  # 观察卖出价
    sell_enter = 0  # 反转卖出价
    buy_enter = 0   # 反转买入价
    buy_setup = 0   # 观察买入价
    sell_break = 0  # 突破卖出价

    intra_trade_high = 0
    intra_trade_low = 0

    day_high = 0
    day_open = 0
    day_close = 0
    day_low = 0
    tend_high = 0
    tend_low = 0
    parameters = [
        "modevalue",
        "boxsize",
        "reversal"
    ]
    variables = [
        "intra_trade_high",
        "intra_trade_low"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = BarGenerator(self.on_bar,interval=Interval.TICK)
        self.am = ArrayManager()
        self.bars = []

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.atrboxsize = conv_atr(self.modevalue,0.2)
        self.load_bar(10)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        
        self.bg.update_tick(tick)

    def myema(self,ser, length, trcnt, obox, countch, trch, reversal):
        if length <= 0:
            return
        if countch[-1] <= length:
            em_value = mysma(ser, length)
        else:
            idx = len(ser) - 1
            if idx >= trcnt and ser[idx - trcnt] is not None and ser[idx] != nz(ser[idx - trcnt]):
                alpha = 2 / (length + 1)
                bb = 1 if ser[idx] > nz(ser[idx - trcnt]) else -1
                kats = reversal if trch[idx] else 1
                st = nz(ser[idx - trcnt]) + bb * obox[idx - trcnt] * kats
                prev_em = nz(self.em[idx - trcnt]) if idx - trcnt < len(self.em) else 0
                em_value = alpha * st + (1 - alpha) * prev_em
                st += bb * obox[idx - trcnt]
                for x in range(1, min(4001, idx)):
                    if (st > ser[idx] and bb > 0) or (st < ser[idx] and bb < 0):
                        break
                    em_value = alpha * st + (1 - alpha) * em_value
                    st += bb * obox[idx - trcnt]
            else:
                em_value = nz(self.em[-1]) if len(self.em) > 0 else 0
        self.em.append(em_value)
        return self.em[-1]


    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.cancel_all()
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        
        mode=self.g_params['mode']
        boxsize=self.boxsize
        open_price =am.open_array[-1]
        high_price = am.high_array[-1]
        low_price = am.low_array[-1]
        close_price = am.close_array[-1]
        new_box_value = self.atrboxsize if mode == 'ATR' else boxsize if self.box[-1] is None else self.box[-1]
        self.box.append(new_box_value)
        self.top.append(0.0)
        self.bottom.append( 0.0)
        # 更新trend
        new_trend_value = 0 if len(self.trend) == 1 else self.trend[-1]  # 使用nz(trend[1])的逻辑
        self.trend.append(new_trend_value)

        # 更新currentprice
        new_currentprice_value = close_price if self.g_params['source']  == 'close' else high_price if self.trend[-1] == 1 else low_price
        self.currentprice.append(new_currentprice_value)
        current_price=new_currentprice_value 

        # 更新beginprice
        new_beginprice_value = (open_price // self.box[-1]) * self.box[-1] if self.beginprice[-1] is None else self.beginprice[-1]
        self.beginprice.append(new_beginprice_value)

        self.iopenprice.append(self.beginprice[-1])
        self.icloseprice.append(0)
        self.nok.append(True)
        self.numcell.append(0)
        if self.trend[-1] == 0 and self.box[-1] * self.reversal <= abs(self.beginprice[-1] - self.currentprice[-1]):
            self.numcell[-1] = math.floor(abs(self.beginprice[-1] - self.currentprice[-1]) / self.box[-1])
            self.iopenprice[-1]=self.beginprice[-1]
            if self.beginprice[-1] > self.currentprice[-1]:
                self.icloseprice[-1]=self.beginprice[-1] - self.numcell[-1] * self.box[-1]
                self.trend[-1] = -1
            elif self.beginprice[-1] < self.currentprice[-1]:
                self.icloseprice[-1]=self.beginprice[-1] + self.numcell[-1] * self.box[-1]
                self.trend[-1] = 1
        if self.trend[-1] == -1:
            self.nok[-1] = True
            if self.beginprice[-1] > current_price and self.box[-1] <= abs(self.beginprice[-1] - current_price):
                self.numcell[-1] = math.floor(abs(self.beginprice[-1] - current_price) / self.box[-1])
                self.icloseprice[-1]=self.beginprice[-1] - self.numcell[-1]  * self.box[-1]
                self.trend[-1]=-1
                self.beginprice[-1] = self.icloseprice[-1]
                self.nok[-1]=False
            else:
                self.iopenprice[-1]=self.iopenprice[-1] if self.iopenprice[-1] != 0 else self.iopenprice[-2]
                self.icloseprice[-1]=self.icloseprice[-1] if self.icloseprice[-1] != 0 else self.icloseprice[-2]

                tempcurrentprice = close_price if self.g_params['source'] == 'close' else high_price
                if self.beginprice[-1] < tempcurrentprice and self.box[-1] * self.reversal <= abs(self.beginprice[-1] - tempcurrentprice) and self.nok[-1]:
                    self.numcell[-1]  = math.floor(abs(self.beginprice[-1] - tempcurrentprice) / self.box[-1])
                    self.iopenprice[-1]=self.beginprice[-1] + self.box[-1]
                    self.icloseprice[-1]=self.beginprice[-1] + self.numcell[-1]  * self.box[-1]
                    self.trend[-1]=1
                    self.beginprice[-1] = self.icloseprice[-1]
                else:
                    self.iopenprice[-1]=self.iopenprice[-1] if self.iopenprice[-1] != 0 else self.iopenprice[-2]
                    self.icloseprice[-1]=self.icloseprice[-1] if self.icloseprice[-1] != 0 else self.icloseprice[-2]
        elif self.trend[-1] == 1:
            self.nok[-1] = True
            if self.beginprice[-1] < current_price and self.box[-1] <= abs(self.beginprice[-1] - current_price):
                self.numcell[-1] =math.floor(abs(self.beginprice[-1] - current_price) / self.box[-1])
                self.icloseprice[-1]=self.beginprice[-1] + self.numcell[-1]  * self.box[-1]
                self.trend[-1]=1
                self.beginprice[-1] = self.icloseprice[-1]
                self.nok[-1]=False
            else:
                self.iopenprice[-1]=self.iopenprice[-1] if self.iopenprice[-1] != 0 else self.iopenprice[-2]
                self.icloseprice[-1]=self.icloseprice[-1] if self.icloseprice[-1] != 0 else self.icloseprice[-2]

                tempcurrentprice = close_price if self.g_params['source'] == 'close' else low_price
                if self.beginprice[-1] > tempcurrentprice and self.box[-1] * self.reversal <= abs(self.beginprice[-1] - tempcurrentprice) and self.nok[-1]:
                    self.numcell[-1] = math.floor(abs(self.beginprice[-1] - tempcurrentprice) / self.box[-1])
                    self.iopenprice[-1]=self.beginprice[-1] - self.box[-1]
                    self.icloseprice[-1]=self.beginprice[-1] - self.numcell[-1] * self.box[-1]
                    self.trend[-1]=-1
                    self.beginprice[-1] = self.icloseprice[-1]
                else:
                    self.iopenprice[-1]=self.iopenprice[-1] if self.iopenprice[-1] != 0 else self.iopenprice[-2]
                    self.icloseprice[-1]=self.icloseprice[-1] if self.icloseprice[-1] != 0 else self.icloseprice[-2]
        if len(self.icloseprice) > 1 and self.icloseprice[-1] != self.icloseprice[-2]:
            self.box[-1] = self.atrboxsize if mode == 'ATR' else boxsize
        # 注意这里只更新了box的最后一个值，不添加新元素
        if len(self.trend) > 1 and len(self.icloseprice) > 1 and len(self.box) > 1:
            if self.trend[-1] == 1:
                if nz(self.trend[-2]) == 1:
                    new_oprice = nz(self.icloseprice[-2]) - nz(self.box[-2])
                else:
                    new_oprice = nz(self.icloseprice[-2]) + nz(self.box[-2])
            elif self.trend[-1] == -1:
                if nz(self.trend[-2]) == -1:
                    new_oprice = nz(self.icloseprice[-2]) + nz(self.box[-2])
                else:
                    new_oprice = nz(self.icloseprice[-2]) - nz(self.box[-2])
            else:
                new_oprice = nz(self.icloseprice[-2])

            self.oprice.append(max(new_oprice, 0))  # 确保oprice不小于0
        else:
            self.oprice.append(0)  # 或其他合适的默认值
        # if self.oprice[-1]!=0:
        #     self.PlotNumeric("openline",self.oprice[-1],self.RGB_Red(),True,False)
        # if icloseprice[-1]!=0:
        #     PlotNumeric("closeline",icloseprice[-1],RGB_Green(),True,False)
        if change(self.trend):
            if self.iopenprice[-2]!=None and  self.icloseprice[-2]!=None:
                self.chigh.append(max(self.iopenprice[-2], self.icloseprice[-2]))
                self.clow.append(min(self.iopenprice[-2], self.icloseprice[-2]))
            self.ctrend.append(self.trend[-2])
        else:
            self.chigh.append(None)
            self.clow.append(None)
            self.ctrend.append(None)
        Brickhigh = f_Brickhigh(self.trend, self.icloseprice, self.iopenprice, self.box, self.Length)
        Bricklow = f_Bricklow(self.trend, self.icloseprice, self.iopenprice, self.box, self.Length)

        # 获取最新的 Brickhigh 和 Bricklow 值
        current_Brickhigh = Brickhigh
        current_Bricklow = Bricklow
        # 更新 switch, setA, 和 setB 的状态
        if current_Brickhigh and self.switch[-1] == 0:
            self.switch.append(1)
            self.setA.append(1)
            self.setB.append(0)
        elif current_Bricklow and self.switch[-1] == 1:
            self.switch.append(0)
            self.setA.append(0)
            self.setB.append(1)
        else:
            self.switch.append(self.switch[-1] if len(self.switch) > 0 else 0)
            self.setA.append(0)
            self.setB.append(0)
        # 更新 botrend
        if self.setA[-1] == 1:
            self.botrend.append(1)
        elif self.setB[-1] == 1:
            self.botrend.append(-1)
        else:
            self.botrend.append(self.botrend[-1] if len(self.botrend) > 0 else 0)
        # 计算 boline
        if self.g_params['showbreakout'] :
            if self.botrend[-1] == 1:
                self.boline = self.icloseprice[-1] if self.trend[-1] == 1 else self.oprice[-1]
            elif self.botrend[-1] == -1:
                self.boline = self.oprice[-1] if self.trend[-1] == 1 else self.icloseprice[-1]
            else:
                self.boline = None  # 或者其他表示不可用的值

        else:
            self.boline = None  # 或者其他表示不可用的值
        # if boline!=None:
        #     if botrend[-1] == 1:
        #         PlotNumeric("boline1",boline ,RGB_Red(),True,False)
        #     if botrend[-1] == -1:
        #         PlotNumeric("boline0",boline ,RGB_Green(),True,False)
        
        self.bars.append(bar)
        if len(self.bars) <= 2:
            return
        else:
            self.bars.pop(0)
        last_bar = self.bars[-2]

        # New Day
        if last_bar.datetime.date() != bar.datetime.date():
            if self.day_open:

                self.buy_setup = self.day_low - self.setup_coef * (self.day_high - self.day_close)  # 观察买入价
                self.sell_setup = self.day_high + self.setup_coef * (self.day_close - self.day_low)  # 观察卖出价

                self.buy_enter = (self.enter_coef_1 / 2) * (self.day_high + self.day_low) - self.enter_coef_2 * self.day_high  # 反转买入价
                self.sell_enter = (self.enter_coef_1 / 2) * (self.day_high + self.day_low) - self.enter_coef_2 * self.day_low  # 反转卖出价

                self.buy_break = self.buy_setup + self.break_coef * (self.sell_setup - self.buy_setup)  # 突破买入价
                self.sell_break = self.sell_setup - self.break_coef * (self.sell_setup - self.buy_setup)  # 突破卖出价

            self.day_open = bar.open_price
            self.day_high = bar.high_price
            self.day_close = bar.close_price
            self.day_low = bar.low_price

        # Today
        else:
            self.day_high = max(self.day_high, bar.high_price)
            self.day_low = min(self.day_low, bar.low_price)
            self.day_close = bar.close_price

        if not self.sell_setup:
            return

        self.tend_high, self.tend_low = am.donchian(self.donchian_window)

        if bar.datetime.time() < self.exit_time:

            if self.pos == 0:
                self.intra_trade_low = bar.low_price
                self.intra_trade_high = bar.high_price

                if self.tend_high > self.sell_setup and self.trend[-1]==1:
                    long_entry = max(self.buy_break, self.day_high)
                    self.buy(long_entry, self.fixed_size, stop=True)

                    self.short(self.sell_enter, self.multiplier * self.fixed_size, stop=True)

                elif self.tend_low < self.buy_setup and self.trend[-1]==-1:
                    short_entry = min(self.sell_break, self.day_low)
                    self.short(short_entry, self.fixed_size, stop=True)

                    self.buy(self.buy_enter, self.multiplier * self.fixed_size, stop=True)

            elif self.pos > 0:
                if self.trend[-1]==-1:
                    self.sell(bar.close_price * 0.99, abs(self.pos))
                else:
                    self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
                    long_stop = self.intra_trade_high * (1 - self.trailing_long / 100)
                    self.sell(long_stop, abs(self.pos), stop=True)

            elif self.pos < 0:
                if self.trend[-1]==1:
                    self.cover(bar.close_price * 1.01, abs(self.pos))
                else:
                    self.intra_trade_low = min(self.intra_trade_low, bar.low_price)
                    short_stop = self.intra_trade_low * (1 + self.trailing_short / 100)
                    self.cover(short_stop, abs(self.pos), stop=True)

        # Close existing position
        else:
            if self.pos > 0:
                self.sell(bar.close_price * 0.99, abs(self.pos))
            elif self.pos < 0:
                self.cover(bar.close_price * 1.01, abs(self.pos))
        # if bar.datetime.time() < self.exit_time:
        
        #     if self.pos == 0:
        #         self.intra_trade_high = bar.high_price
        #         self.intra_trade_low = bar.low_price

        #         if self.setA[-1]==1:
        #             self.buy(bar.close_price + 0.2, self.fixed_size)
        #         elif self.setB[-1]==1:
        #             self.short(bar.close_price - 0.2, self.fixed_size)

        #     elif self.pos > 0:
        #         self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
        #         self.intra_trade_low = bar.low_price
        #         long_stop = self.intra_trade_high * \
        #             (1 - self.trailing_long / 100)
        #         self.sell(long_stop, abs(self.pos), stop=True)

        #     elif self.pos < 0:
        #         self.intra_trade_low = min(self.intra_trade_low, bar.low_price)
        #         self.intra_trade_high = bar.high_price

        #         short_stop = self.intra_trade_low * \
        #             (1 + self.trailing_short / 100)
        #         self.cover(short_stop, abs(self.pos), stop=True)
        # else:
        #     if self.pos > 0:
        #         self.sell(bar.close_price * 0.99, abs(self.pos))
        #     elif self.pos < 0:
        #         self.cover(bar.close_price * 1.01, abs(self.pos))
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass
