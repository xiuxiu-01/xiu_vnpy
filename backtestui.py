
import sys
sys.path.append('/Users/linweiqiang/Desktop/我的工作代码/xiu_vnpy')
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
from vnpy_ctastrategy.template import KLWidget
from vnpy.trader.constant import Exchange, Interval,Status
from datetime import time
from time import sleep
class VolumeEMA(CtaTemplate):
    """"""

    name = "xiuxiuxiu"
    long_stop=0
    short_stop=0
    time=0
    fixed_size=2
    trading=True
    parameters = [
    ]
    mainSigs=["long_stop"]
    subSigs=["short_stop"]
    main_indicator=["sss"]
    variables = [
        "long_stop",
        "short_stop",
        "time"

    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg10 = BarGenerator(self.on_bar,interval=Interval.VOLUME,volumebar=200)#,window=10,on_window_bar=self.on_10_bar)
        self.bgm = BarGenerator(self.on_m_bar,interval=Interval.MINUTE,window=15)
        self.am = ArrayManager(1000)
        self.am2 = ArrayManager(1000)
        self.widget =mainWidget
        self.long_stop=0
        self.max_bid_volume_price=0
        self.short_stop=0
        self.max_ask_volume_price=0
        self.pricetick=1
        self.o1=None
        self.times=[]
        self.name="sssss"
        self.downtrend=0
        self.uptrend=0
        self.timediffs=[]
        self.flag=0

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        #self.load_tick(1)#.load_bar(100,interval=Interval.TICK,use_database=True)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        #mainWidget.load_data_signal.emit()
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
        #self.write_log(str(tick.volume))
        self.bg10.update_v_tick(tick)
        self.bgm.update_tick(tick)
    def on_m_bar(self, bar: BarData):
        #self.cancel_all()
        am = self.am2
        am.update_bar(bar)
        self.put_event()
    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        #self.cancel_all()
        
        am = self.am
        am2 = self.am2
        am.update_bar(bar)
        self.long_stop=bar.close_price+2
        self.short_stop=am.sma(5)
        self.widget.recv_kline({"bar":bar,'sig':0,"long_stop":self.long_stop,"short_stop":self.short_stop})
        
        #sleep(2)
        self.widget.uiKLine.set_xrange_event()
        #self.widget.uiKLine.set_sub_indicator_y_range()#.set_xrange_event()
        self.widget.set_xrange_event_signal.emit()#.adjustSize()
        self.widget.uiKLine.refresh()#set_xrange_event()
        

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """


    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        self.write_log("止损启动")
        #self.cancel_order(self.o1)
        pass
    def on_stop(self) -> None:
        """
        Callback when strategy is stopped.
        """
from vnpy_ctastrategy.backtesting import BacktestingEngine, OptimizationSetting,BacktestingMode
from datetime import datetime


import sys
from PyQt5.QtWidgets import QApplication, QMessageBox, QVBoxLayout, QWidget
app = QApplication(sys.argv)
mainWidget = KLWidget(VolumeEMA)
engine = BacktestingEngine()
engine.set_parameters(
    vt_symbol="600519.SSE",
    interval="d",
    start=datetime(2023, 5, 20),
    end=datetime(2023, 12, 30),
    rate=1/10000,
    slippage=0,
    size=10,
    pricetick=1,
    capital=1_000_000,
    #mode=BacktestingMode.TICK   
)
# from time import time
engine.add_strategy(VolumeEMA, {})
engine.load_data()
mainWidget.show()
def run_backtesting(engine):
    engine.run_backtesting()
import threading
backtesting_thread = threading.Thread(target=run_backtesting, args=(engine,))
backtesting_thread.start()
sys.exit(app.exec_())
