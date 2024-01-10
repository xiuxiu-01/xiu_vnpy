from abc import ABC
from copy import copy
from typing import Any, Callable, List,Dict

from vnpy.trader.constant import Interval, Direction, Offset
from vnpy.trader.object import BarData, TickData, OrderData, TradeData
from vnpy.trader.utility import virtual
from threading import Thread, Timer
from .base import StopOrder, EngineType
from .uiKLine import KLineWidget
import pandas as pd
from PyQt5 import QtCore
from PyQt5.QtGui import QCloseEvent, QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QVBoxLayout, QWidget
import sys
class CtaTemplate(ABC):
    """"""
    t: Thread = None
    author: str = ""
    parameters: list = []
    variables: list = []

    def __init__(
        self,
        cta_engine: Any,
        strategy_name: str,
        vt_symbol: str,
        setting: dict,
    ) -> None:
        """"""
        self.cta_engine: Any = cta_engine
        self.strategy_name: str = strategy_name
        self.vt_symbol: str = vt_symbol
        self.widget:KLWidget=None

        self.inited: bool = False
        self.trading: bool = False
        self.pos: int = 0

        # Copy a new variables list here to avoid duplicate insert when multiple
        # strategy instances are created with the same strategy class.
        self.variables = copy(self.variables)
        self.variables.insert(0, "inited")
        self.variables.insert(1, "trading")
        self.variables.insert(2, "pos")
        
        self.update_setting(setting)

    def update_setting(self, setting: dict) -> None:
        """
        Update strategy parameter wtih value in setting dict.
        """
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])

    @classmethod
    def get_class_parameters(cls) -> dict:
        """
        Get default parameters dict of strategy class.
        """
        class_parameters: dict = {}
        for name in cls.parameters:
            class_parameters[name] = getattr(cls, name)
        return class_parameters

    def get_parameters(self) -> dict:
        """
        Get strategy parameters dict.
        """
        strategy_parameters: dict = {}
        for name in self.parameters:
            strategy_parameters[name] = getattr(self, name)
        return strategy_parameters

    def get_variables(self) -> dict:
        """
        Get strategy variables dict.
        """
        strategy_variables: dict = {}
        for name in self.variables:
            strategy_variables[name] = getattr(self, name)
        return strategy_variables

    def get_data(self) -> dict:
        """
        Get strategy data.
        """
        strategy_data: dict = {
            "strategy_name": self.strategy_name,
            "vt_symbol": self.vt_symbol,
            "class_name": self.__class__.__name__,
            "author": self.author,
            "parameters": self.get_parameters(),
            "variables": self.get_variables(),
        }
        return strategy_data

    @virtual
    def on_init(self) -> None:
        """
        Callback when strategy is inited.
        """
        pass

    @virtual
    def on_start(self) -> None:
        """
        Callback when strategy is started.
        """
        pass

    @virtual
    def on_stop(self) -> None:
        """
        Callback when strategy is stopped.
        """
        pass

    @virtual
    def on_tick(self, tick: TickData) -> None:
        """
        Callback of new tick data update.
        """
        pass

    @virtual
    def on_bar(self, bar: BarData) -> None:
        """
        Callback of new bar data update.
        """
        pass

    @virtual
    def on_trade(self, trade: TradeData) -> None:
        """
        Callback of new trade data update.
        """
        pass

    @virtual
    def on_order(self, order: OrderData) -> None:
        """
        Callback of new order data update.
        """
        pass

    @virtual
    def on_stop_order(self, stop_order: StopOrder) -> None:
        """
        Callback of stop order update.
        """
        pass

    def buy(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ) -> list:
        """
        Send buy order to open a long position.
        """
        return self.send_order(
            Direction.LONG,
            Offset.OPEN,
            price,
            volume,
            stop,
            lock,
            net
        )

    def sell(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ) -> list:
        """
        Send sell order to close a long position.
        """
        return self.send_order(
            Direction.SHORT,
            Offset.CLOSE,
            price,
            volume,
            stop,
            lock,
            net
        )

    def short(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ) -> list:
        """
        Send short order to open as short position.
        """
        return self.send_order(
            Direction.SHORT,
            Offset.OPEN,
            price,
            volume,
            stop,
            lock,
            net
        )

    def cover(
        self,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ) -> list:
        """
        Send cover order to close a short position.
        """
        return self.send_order(
            Direction.LONG,
            Offset.CLOSE,
            price,
            volume,
            stop,
            lock,
            net
        )

    def send_order(
        self,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        stop: bool = False,
        lock: bool = False,
        net: bool = False
    ) -> list:
        """
        Send a new order.
        """
        if self.trading:
            vt_orderids: list = self.cta_engine.send_order(
                self, direction, offset, price, volume, stop, lock, net
            )
            return vt_orderids
        else:
            return []

    def cancel_order(self, vt_orderid: str) -> None:
        """
        Cancel an existing order.
        """
        if self.trading:
            self.cta_engine.cancel_order(self, vt_orderid)

    def cancel_all(self) -> None:
        """
        Cancel all orders sent by strategy.
        """
        if self.trading:
            self.cta_engine.cancel_all(self)

    def write_log(self, msg: str) -> None:
        """
        Write a log message.
        """
        self.cta_engine.write_log(msg, self)

    def get_engine_type(self) -> EngineType:
        """
        Return whether the cta_engine is backtesting or live trading.
        """
        return self.cta_engine.get_engine_type()

    def get_pricetick(self) -> float:
        """
        Return pricetick data of trading contract.
        """
        return self.cta_engine.get_pricetick(self)

    def get_size(self) -> int:
        """
        Return size data of trading contract.
        """
        return self.cta_engine.get_size(self)

    def load_bar(
        self,
        days: int,
        interval: Interval = Interval.MINUTE,
        callback: Callable = None,
        use_database: bool = False
    ) -> None:
        """
        Load historical bar data for initializing strategy.
        """
        if not callback:
            callback: Callable = self.on_bar

        bars: List[BarData] = self.cta_engine.load_bar(
            self.vt_symbol,
            days,
            interval,
            callback,
            use_database
        )

        for bar in bars:
            callback(bar)
    @classmethod
    def setQtSp(cls):
        """启动 QT 界面"""
        if cls.t is None:
            cls.t = Thread(target=cls.StartGui)
            cls.t.setDaemon(True)
            cls.t.start()
    @classmethod
    def StartGui(cls):
        # 设置Qt的皮肤
        try:
            import qdarkstyle
            app = QApplication([''])
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            basePath = os.path.split(os.path.realpath(__file__))[0]
            cfgfile = QtCore.QFile(os.path.join(basePath, 'css.qss'))
            cfgfile.open(QtCore.QFile.ReadOnly)
            styleSheet = bytes(cfgfile.readAll()).decode('utf-8')
            app.setStyleSheet(styleSheet)
            # 界面设置
            cls.qtsp = QtGuiSupport()
            # 在主线程中启动Qt事件循环
            print("s")
            sys.exit(app.exec_())
            
        except:
            print("ssss")
        cls.t = None

    def load_tick(self, days: int) -> None:
        """
        Load historical tick data for initializing strategy.
        """
        ticks: List[TickData] = self.cta_engine.load_tick(self.vt_symbol, days, self.on_tick)

        for tick in ticks:
            self.on_tick(tick)

    def put_event(self) -> None:
        """
        Put an strategy data event for ui update.
        """
        if self.inited:
            self.cta_engine.put_strategy_event(self)

    def send_email(self, msg) -> None:
        """
        Send email to default receiver.
        """
        if self.inited:
            self.cta_engine.send_email(msg, self)

    def sync_data(self) -> None:
        """
        Sync strategy variables value into disk storage.
        """
        if self.trading:
            self.cta_engine.sync_strategy_data(self)



class TargetPosTemplate(CtaTemplate):
    """"""
    tick_add = 1

    last_tick: TickData = None
    last_bar: BarData = None
    target_pos = 0

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting) -> None:
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.active_orderids: list = []
        self.cancel_orderids: list = []

        self.variables.append("target_pos")

    @virtual
    def on_tick(self, tick: TickData) -> None:
        """
        Callback of new tick data update.
        """
        self.last_tick = tick

    @virtual
    def on_bar(self, bar: BarData) -> None:
        """
        Callback of new bar data update.
        """
        self.last_bar = bar

    @virtual
    def on_order(self, order: OrderData) -> None:
        """
        Callback of new order data update.
        """
        vt_orderid: str = order.vt_orderid

        if not order.is_active():
            if vt_orderid in self.active_orderids:
                self.active_orderids.remove(vt_orderid)

            if vt_orderid in self.cancel_orderids:
                self.cancel_orderids.remove(vt_orderid)

    def check_order_finished(self) -> bool:
        """"""
        if self.active_orderids:
            return False
        else:
            return True

    def set_target_pos(self, target_pos) -> None:
        """"""
        self.target_pos = target_pos
        self.trade()

    def trade(self) -> None:
        """"""
        if not self.check_order_finished():
            self.cancel_old_order()
        else:
            self.send_new_order()

    def cancel_old_order(self) -> None:
        """"""
        for vt_orderid in self.active_orderids:
            if vt_orderid not in self.cancel_orderids:
                self.cancel_order(vt_orderid)
                self.cancel_orderids.append(vt_orderid)

    def send_new_order(self) -> None:
        """"""
        pos_change = self.target_pos - self.pos
        if not pos_change:
            return

        long_price = 0
        short_price = 0

        if self.last_tick:
            if pos_change > 0:
                long_price = self.last_tick.ask_price_1 + self.tick_add
                if self.last_tick.limit_up:
                    long_price = min(long_price, self.last_tick.limit_up)
            else:
                short_price = self.last_tick.bid_price_1 - self.tick_add
                if self.last_tick.limit_down:
                    short_price = max(short_price, self.last_tick.limit_down)

        else:
            if pos_change > 0:
                long_price = self.last_bar.close_price + self.tick_add
            else:
                short_price = self.last_bar.close_price - self.tick_add

        if self.get_engine_type() == EngineType.BACKTESTING:
            if pos_change > 0:
                vt_orderids: list = self.buy(long_price, abs(pos_change))
            else:
                vt_orderids: list = self.short(short_price, abs(pos_change))
            self.active_orderids.extend(vt_orderids)

        else:
            if self.active_orderids:
                return

            if pos_change > 0:
                if self.pos < 0:
                    if pos_change < abs(self.pos):
                        vt_orderids: list = self.cover(long_price, pos_change)
                    else:
                        vt_orderids: list = self.cover(long_price, abs(self.pos))
                else:
                    vt_orderids: list = self.buy(long_price, abs(pos_change))
            else:
                if self.pos > 0:
                    if abs(pos_change) < self.pos:
                        vt_orderids: list = self.sell(short_price, abs(pos_change))
                    else:
                        vt_orderids: list = self.sell(short_price, abs(self.pos))
                else:
                    vt_orderids: list = self.short(short_price, abs(pos_change))
            self.active_orderids.extend(vt_orderids)
from PyQt5 import QtCore
from PyQt5.QtGui import QCloseEvent, QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QVBoxLayout, QWidget
import numpy as np
from .vtObject import (KLineData,OrderData, TickData, TradeData)
import os
from collections import OrderedDict, defaultdict
class CtaSignal(ABC):
    """"""

    def __init__(self) -> None:
        """"""
        self.signal_pos = 0

    @virtual
    def on_tick(self, tick: TickData) -> None:
        """
        Callback of new tick data update.
        """
        pass

    @virtual
    def on_bar(self, bar: BarData) -> None:
        """
        Callback of new bar data update.
        """
        pass

    def set_signal_pos(self, pos) -> None:
        """"""
        self.signal_pos = pos

    def get_signal_pos(self) -> Any:
        """"""
        return self.signal_pos

class QtGuiSupport(QtCore.QObject):
    """支持 QT 的对象类"""
    init_widget_signal = QtCore.pyqtSignal(object)
    hide_signal = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.widgetDict: Dict[str, QWidget] = {}
        self.init_widget_signal.connect(self.init_strategy_widget)
        self.hide_signal.connect(self.hide_strategy_widget)

    def init_strategy_widget(self, s: CtaTemplate):
        """初始化 widget 或对策略类的 widget 重新赋值"""
        try:
            if s.widgetClass is not None:
                if self.widgetDict.get(s.name) is None:
                    s.widget = s.widgetClass(s)
                    self.widgetDict[s.name] = s.widget
                else:
                    s.widget= self.widgetDict[s.name]
                    self.widgetDict[s.name].strategy = s

                if uiKLine := getattr(self.widgetDict[s.name], "uiKLine", None):
                    uiKLine.layout_title.setText(s.vtSymbol, bold=True, color="w")
        except:
            print("ssss")

    def hide_strategy_widget(self, s: CtaTemplate):
        """隐藏 widget"""
        if s.widgetClass and self.widgetDict.get(s.name):
            self.widgetDict[s.name].hide()


class KLWidget(QWidget):
    """简单交易组件"""
    update_kline_signal = QtCore.pyqtSignal(dict)
    load_data_signal = QtCore.pyqtSignal()
    set_xrange_event_signal = QtCore.pyqtSignal()

    def __init__(self, strategy, parent=None):
        super().__init__(parent)
        self.strategy = strategy # 策略实例 CTATemplate
        self.started = True
        self.init_ui()
        self.klines: List[dict] = []
        self.state_data = defaultdict(list)

        self.update_kline_signal.connect(self.update_kline)
        self.load_data_signal.connect(self.load_kline_data)
        self.set_xrange_event_signal.connect(self.uiKLine.set_xrange_event)

        self._first_add = True

    @property
    def main_indicator(self) -> List[str]:
        """主图指标"""
        return self.strategy.mainSigs

    @property
    def sub_indicator(self) -> List[str]:
        """副图指标"""
        return self.strategy.subSigs

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"策略-{self.strategy.name}")
        self.uiKLine = KLineWidget(self)

        # 整合布局
        vbox = QVBoxLayout()
        vbox.addWidget(self.uiKLine)
        self.setLayout(vbox)
        self.resize(750, 850)

        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image")
        if os.path.exists(image_path):
            for image_file in os.listdir(image_path):
                if image_path.endswith(".ico"):
                    self.setWindowIcon(QIcon(os.path.join(image_path, image_file)))

    #@utils.deprecated("recv_kline", ctaEngine.writeLog)
    def addBar(self, data):
        """弃用, 仅做兼容"""
        self.recv_kline(data)

    def recv_kline(self, data: dict) -> None:
        """接受 K 线"""
        
        if self.strategy.trading:
            self.update_kline_signal.emit(data)
        else:
            if self._first_add:
                self.clear()
            self.klines.append(data["bar"].__dict__)
            #print(data["bar"].__dict__)
            for s in (self.main_indicator + self.sub_indicator):
                self.state_data[s].append(data[s])

        self.update_bs_signal(data["sig"])
        self._first_add = False

    def update_kline(self, data: dict):
        """更新 K 线"""
        kline: BarData = data["bar"]

        if (
            len(self.klines) >= 2
            and (self.klines[-2]["datetime"] < kline.datetime < self.klines[-1]["datetime"])
        ):
            """丢数据"""
            self.klines.insert(-1, kline.__dict__)
            self.uiKLine.insert_kline(kline)

            for indicator_name in self.main_indicator + self.sub_indicator:
                self.state_data[indicator_name].insert(-1, data[indicator_name])

            self.update_indicator_data(new_data=True)

            return

        is_new_kline = self.uiKLine.update_kline(kline)

        if is_new_kline:
            self.klines.append(kline.__dict__)
        else:
            self.klines[-1] = kline.__dict__

        self.update_indicator_data(data, new_data=is_new_kline)

        self.uiKLine.update_candle_signal.emit()

        self.plot_main()
        self.plot_sub()

    def update_bs_signal(self, price: float):
        """设置买卖信号的坐标"""
        if price:
            index = len(self.klines) - 1
            self.uiKLine.buy_sell_signals[index] = price

            if self.strategy.trading:
                self.uiKLine.add_buy_sell_signal.emit(index)

    def load_kline_data(self):
        """载入历史 K 线数据"""
        if self._first_add is False:
            """只有调用了 recv_kline 才需要重新载入数据"""
            print(self.klines)
            pdData = pd.DataFrame(self.klines).set_index("datetime")
            pdData["open_interest"] = pdData["open_interest"].astype(float)
            self.uiKLine.load_data(pdData)
            self.uiKLine.plotMark()
            self.update_indicator_data()
            self.uiKLine.plot_all()
            self.plot_main()
            self.plot_sub()

        self._first_add = True
        self.show()

    def clear(self):
        """清空数据"""
        self.klines.clear()
        self.state_data.clear()
        self.uiKLine.clear_data()
        self.uiKLine.clear_buy_sell_signals()
        self.uiKLine.plot_all()
        self.started = False

    def update_indicator_data(self, data: dict = None, new_data: bool = True):
        """更新指标数组中的数据"""
        if data:
            for s in self.main_indicator + self.sub_indicator:
                if new_data:
                    self.state_data[s].append(data[s])
                else:
                    self.state_data[s][-1] = data[s]

        for s in self.main_indicator:
            if s in self.uiKLine.indicator_data:
                _indicator_data: np.ndarray = (
                    np.array(self.state_data[s])
                    if new_data
                    else np.append(self.uiKLine.indicator_data[s][:-1], data[s])
                )
                self.uiKLine.indicator_data[s] = _indicator_data

        for s in self.sub_indicator:
            self.uiKLine.sub_indicator_data[s] = np.array(self.state_data[s])

    def plot_main(self):
        """输出信号到主图"""
        for indicator_name in self.main_indicator:
            _indicator_data: np.ndarray = np.array(self.state_data[indicator_name])
            if indicator_name in self.uiKLine.indicator_data:
                self.uiKLine.indicator_plot_items[indicator_name].setData(
                    _indicator_data,
                    pen=self.uiKLine.indicator_color_map[indicator_name],
                    name=indicator_name
                )
            else:
                self.uiKLine.showSig({indicator_name: _indicator_data})

    def plot_sub(self):
        """输出信号到副图"""
        for indicator_name in self.sub_indicator:
            self.uiKLine.showSig(
                datas={indicator_name: np.array(self.state_data[indicator_name])},
                main_plot=False
            )

    def closeEvent(self, evt: QCloseEvent) -> None:
        """继承关闭事件"""
        if self.strategy.trading:
            QMessageBox.warning(None, "警告", "策略启动时无法关闭，暂停时会自动关闭！")
        else:
            self.hide()
        evt.ignore()
