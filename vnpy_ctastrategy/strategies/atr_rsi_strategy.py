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
from datetime import time

class AtrRsiStrategy(CtaTemplate):
    """"""

    author = "用Python的交易员"
    fixed_size = 1

    intra_trade_high = 0
    intra_trade_low = 0
    setup_coef = 0.1
    enter_coef_1 = 1.07
    enter_coef_2 = 0.07

    sell_setup = 0  # 观察卖出价
    buy_setup = 0   # 观察买入价
    sell_enter = 0  # 反转卖出价
    buy_enter = 0   # 反转买入价
    trailing_long=1
    trailing_short=1

    donchian_window=30
    tend_high=0
    tend_low=0


    day_high = 0
    day_open = 0
    day_close = 0
    day_low = 0
    tend_high = 0
    tend_low = 0

    exit_time = time(hour=22, minute=55)
    
    parameters = [
        "setup_coef",
        "trailing_long",
        "trailing_short"

    ]
    variables = [
        "intra_trade_high",
        "intra_trade_low"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
        self.bars = []

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
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        self.bars.append(bar)
        if len(self.bars) <= 2:
            return
        else:
            self.bars.pop(0)
        last_bar = self.bars[-2]

        # New Day
        if last_bar.datetime.date() != bar.datetime.date():
            if self.day_open:

                self.buy_setup = bar.close_price + self.setup_coef * (self.day_high - self.day_low)  # 观察买入价
                self.sell_setup = bar.close_price -self.setup_coef * (self.day_high - self.day_low)  # 观察卖出价


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
                self.buy(self.tend_high, self.fixed_size, stop=True)
                self.short(self.tend_low, self.fixed_size, stop=True)

            if self.pos >0:
                self.sell(self.tend_high+5, abs(self.pos), stop=True)
                self.sell(self.tend_high-2, abs(self.pos), stop=True)
            if self.pos <0:
                self.cover(self.tend_high-5, abs(self.pos), stop=True)
                self.cover(self.tend_high+2, abs(self.pos), stop=True)
        # Close existing position
        
        else:
            if self.pos > 0:
                self.sell(bar.close_price * 0.99, abs(self.pos))
            elif self.pos < 0:
                self.cover(bar.close_price * 1.01, abs(self.pos))
        
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
