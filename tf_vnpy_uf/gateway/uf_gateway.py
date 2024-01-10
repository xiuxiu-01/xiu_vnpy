import sys
import os
# 获取当前脚本的目录
script_dir = os.path.dirname(os.path.realpath(__file__))

# 将该目录添加到sys.path中
sys.path.append(script_dir)
# from ..api import (
#     LICENSE,
# )#C:\Users\liyou\Desktop\vnpy-3.3.0\tf_o32_vnpy\vnpy_uf1\gateway\
import ama
LICENSE=script_dir+r"\license.dat"
t2sdkini=script_dir+r'\t2sdk.ini'
subscriberini=script_dir+r'\subscriber.ini'
cfgusername =  "ZY_test01"
cfgpassword = "ZY_test01"
cfgums_server_cnt = 2

#item.local_ip = "10.45.75.48"
itemlocal_ip = "0.0.0.0"
itemserver_ip = "192.168.64.148"
itemserver_port = 8200
item1local_ip = "10.240.64.10"
item1server_ip = "10.16.131.47"
item1server_port = 4321
from typing import Any, Callable, Dict, List, Set
from datetime import datetime
from pytz import timezone
from copy import copy
from threading import Thread
from time import sleep

import tushare as ts
from tushare.pro.client import DataApi
from pandas import DataFrame
import sys
import signal
import argparse
import time
import json
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.engine import EventEngine
from vnpy.trader.event import EVENT_TIMER
from vnpy.trader.event import EVENT_TRADE
from vnpy.trader.event import EVENT_ORDER
from vnpy.trader.constant import (
    Direction,
    Offset,
    Exchange,
    Product,
    Status,
    OrderType,
    OptionType
)
from vnpy.trader.object import (
    OrderData,
    TradeData,
    TickData,
    PositionData,
    AccountData,
    ContractData,
    OrderRequest,
    OrdersRequest,
    CancelRequest,
    SubscribeRequest
)
from vnpy.trader.setting import SETTINGS
import sys
import os
def Subscription(req,n):
    '''
    订阅信息设置:
    market_inform_dict
        1. 订阅信息分三个维度 market:市场, flag:数据类型(比如现货快照, 逐笔成交, 指数快照等), 证券代码
        2. 订阅操作有三种:
            kSet 设置订阅, 以市场为单位覆盖订阅信息
            kAdd 增加订阅, 在前一个基础上增加订阅信息(ps: 现阶段接口如果之前订阅了某个类型(如kSnapshot)的全部代码,不支持其余类型(如kTickOrder)的部分代码增加)
            kDel 删除订阅, 在前一个基础上删除订阅信息(ps: 现阶段接口如果之前订阅了某个类型的全部代码,不支持删除其中部分代码)
            kCancelAll 取消所有订阅信息
    '''
    item = ama.Tools_CreateSubscribeItem(1)

    if req.exchange == Exchange.SZSE:
        item.market = ama.MarketType.kSZSE          #订阅深圳市场
    elif req.exchange == Exchange.SSE:
        item.market = ama.MarketType.kSSE          #订阅上海市场
    elif req.exchange == Exchange.CFFEX:
        item.market = ama.MarketType.kCFFEX          #订阅上海市场
    elif req.exchange == Exchange.DCE:
        item.market = ama.MarketType.kDCE          #订阅上海市场
    elif req.exchange == Exchange.CZCE:
        item.market = ama.MarketType.kCZCE        #订阅上海市场
    elif req.exchange== Exchange.INE:
        item.market = ama.MarketType.kINE        #订阅上海市场
    else:
        item.market = ama.MarketType.kNone

    item.flag = ama.SubscribeDataType.kNone     #kNone 代表订阅全部类型
    item.security_code = req.symbol                     #"" 代表订阅所有代码
    if n == 0:
        ama.IAMDApi_SubscribeData(ama.SubscribeType.kSet, item, 1)
    else:
        ama.IAMDApi_SubscribeData(ama.SubscribeType.kAdd, item, 1)

    ama.Tools_DestroySubscribeItem(item)
def Init(spi,cfg):

    '''
    通道模式设置及各个通道说明:
    cfg.channel_mode = ama.ChannelMode.kTCP   #TCP 方式计入上游行情系统
    cfg.channel_mode = ama.ChannelMode.kAMI   #AMI 组播方式接入上游行情系统
    cfg.channel_mode = ama.ChannelMode.kRDMA  #开启硬件加速RDMA通道,抓取网卡数据包数据
    cfg.channel_mode = ama.ChannelMode.kEXA   #开启硬件加速EXA通道,抓取网卡数据包数据
    cfg.channel_mode = ama.ChannelMode.kPCAP  #开启硬件加速PCAP通道,抓取网卡数据包数据
    cfg.channel_mode = ama.ChannelMode.kMDDP  #直接接入交易所网关组播数据，现在只有深圳交易所开通了此服务
    cfg.channel_mode = ama.ChannelMode.kTCP | ama.ChannelMode.kAMI #同时通过TCP方式和AMI组播方式接入上游，通过cfg.ha_mode 设置对应的高可用设置模式
    '''
    cfg.channel_mode = ama.ChannelMode.kTCP #TCP 方式计入上游行情系统

    cfg.tcp_compress_mode = 0               #TCP传输数据方式: 0 不压缩 1 华锐自定义压缩 2 zstd压缩(仅TCP模式有效)

    '''
        通道高可用模式设置
        1. cfg.channel_mode 为单通道时,建议设置值为kMasterSlaveA / kMasterSlaveB
        2. cfg.channel_mode 混合开启多个通道时,根据需求设置不同的值
            1) 如果需要多个通道为多活模式接入,请设置kRegularDataFilter值
            2) 如果需要多个通道互为主备接入，请设置值为kMasterSlaveA / kMasterSlaveB,kMasterSlaveA / kMasterSlaveB 差别请参看注释说明
               通道优先级从高到低依次为 kRDMA/kEXA/kMDDP/kAMI/kTCP/kPCAP
    '''
    cfg.ha_mode = ama.HighAvailableMode.kMasterSlaveA

    cfg.min_log_level = ama.LogLevel.kInfo #设置日志最小级别：Info级, AMA内部日志通过 OnLog 回调函数返回

    '''
    设置是否输出监控数据: true(是), false(否), 监控数据通过OnIndicator 回调函数返回
    监控数据格式为json, 主要监控数据包括订阅信息，数据接收数量统计
    数据量统计:包括接收数量和成功下发的数量统计,两者差值为过滤的数据量统计
    eg: "RecvSnapshot": "5926", "SuccessSnapshot": "5925",表示接收了快照数据5926个,成功下发5925个，过滤数据为 5926 - 5925 = 1 个
        过滤的数据有可能为重复数据或者非订阅数据
    '''
    cfg.is_output_mon_data = False

    '''
    设置逐笔保序开关: true(开启保序功能) , false(关闭保序功能)
    主要校验逐笔成交数据和逐笔委托数据是否有丢失,如果丢失会有告警日志,缓存逐笔数据并等待keep_order_timeout_ms(单位ms)时间等待上游数据重传,
    如果超过此时间,直接下发缓存数据,默认数据已经丢失,如果之后丢失数据过来也会丢弃。
    同时由于深圳和上海交易所都是通道内序号连续,如果打开了保序开关,必须订阅全部代码的逐笔数据,否则一部分序号会被订阅过滤,导致数据超时等待以及丢失告警。
    '''
    cfg.keep_order = False
    cfg.keep_order_timeout_ms = 3000

    cfg.is_subscribe_full = False #设置默认订阅: True 代表默认全部订阅, False 代表默认全部不订阅

    '''
    配置UMS信息:
    username/password 账户名/密码, 一个账户只能保持一个连接接入 （注意: 如果需要使用委托簿功能，注意账号需要有委托簿功能权限）
    ums地址配置:
        1) ums地址可以配置1-8个 建议值为2 互为主备, ums_server_cnt 为此次配置UMS地址的个数
        2) ums_servers 为UMS地址信息数据结构:
            local_ip 为本地地址,填0.0.0.0 或者本机ip
            server_ip 为ums服务端地址
            server_port 为ums服务端端口
    '''
    cfg.username =  cfgusername
    cfg.password = cfgpassword
    cfg.ums_server_cnt = cfgums_server_cnt
    item = ama.UMSItem()
    #item.local_ip = "10.45.75.48"
    item.local_ip = itemlocal_ip
    item.server_ip = itemserver_ip
    item.server_port = itemserver_port
    ama.Tools_SetUMSServers(cfg.ums_servers, 0, item)
    item1 = ama.UMSItem()

    # cfg.username =  "ama_u_p2"
    # cfg.password = "1"
    # cfg.ums_server_cnt = 2
    # item = ama.UMSItem()
    # item.local_ip = "0.0.0.0"
    # item.server_ip = "10.16.131.47"
    # item.server_port = 4321
    # ama.Tools_SetUMSServers(cfg.ums_servers, 0, item)
    # item1 = ama.UMSItem()
    item1.local_ip =item1local_ip
    item1.server_ip =item1server_ip
    item1.server_port = item1server_port 
    ama.Tools_SetUMSServers(cfg.ums_servers, 1, item1)

    '''
    业务数据回调接口(不包括 OnIndicator/OnLog等功能数据回调)的线程安全模式设置:
        true: 所有的业务数据接口为接口集线程安全
        false: 业务接口单接口为线程安全,接口集非线程安全
    '''
    cfg.is_thread_safe = True
    
    '''
    是否开启委托簿计算功能
    '''
    cfg.enable_order_book = ama.OrderBookType.kNone

    '''
    初始化回调以及配置信息,此函数为异步函数, 
    如果通道初始化以及登陆出现问题会通过onLog / onEvent 返回初始化结果信息
    '''
    return ama.IAMDApi_Init(spi, cfg)
def subscribe():
    # 读取配置文件
    config = py_t2sdk.pyCConfigInterface()
    config.Load(subscriberini)
    # 获取连接
    ret, errMsg, subConnection = ufx_connect(config)
    if ret != 0:
        print("获取连接失败:%s" % errMsg)
        exit()
    else:
        print("获取连接成功")
    # 读取订阅者名称
    bizName = config.GetString('subscribe', 'biz_name', 'user1')
    # 读取要订阅的主题
    topicName = config.GetString('subscribe', 'topic_name', 'ufx_topic')
    # 读取过滤字段名1
    filterName1 = config.GetString('subscribe', 'filter_name1', '')
    # 读取过滤字段值1
    filterValue1 = config.GetString('subscribe', 'filter_value1', '')
    is_rebuild = config.GetInt('subscribe', 'is_rebulid', 0)
    is_replace = config.GetInt('subscribe', 'is_replace', 0)
    send_interval = config.GetInt('subscribe', 'send_interval', 0)

    # 订阅子回调的接口
    subCallBack = py_t2sdk.pySubCallBack(
            "tf_vnpy_uf.gateway.uf_gateway",
            "TdsubCallback" # 在该类中需要实现回调方法OnReceived
        )
    subCallBack.initInstance()
    iRet, lpSubscribe = subConnection.NewSubscriber(subCallBack, str(bizName, encoding="gbk"), 5000)
    if iRet != 0:
        print(str(subConnection.GetMCLastError(), encoding="gbk"))
        exit()
    subParam = py_t2sdk.pySubscribeParamInterface()
    subParam.SetTopicName(str(topicName, encoding="gbk"))
    # 设置是否补缺
    subParam.SetFromNow(is_rebuild)
    # 设置是否覆盖
    subParam.SetReplace(is_replace)
    # 设置发送间隔
    if send_interval > 0:
        subParam.SetSendInterval(send_interval)
    subParam.SetFilter(str(filterName1, encoding="gbk"), str(filterValue1, encoding="gbk"))
    # 打订阅包 需要传入用户名和密码进行身份校验
    lpCheckPack = py_t2sdk.pyIF2Packer()
    lpCheckPack.BeginPack()
    lpCheckPack.AddField('login_operator_no', 'S', 32, 0)
    lpCheckPack.AddField('password', 'S', 16, 0)
    lpCheckPack.AddStr(common.gOperatorNo)
    lpCheckPack.AddStr(common.gOperatorPwd)
    lpCheckPack.EndPack()
    lpCheckUnpack = py_t2sdk.pyIF2UnPacker()
    # 发起订阅
    result = lpSubscribe.SubscribeTopic(subParam, 5000, lpCheckUnpack, lpCheckPack)
    if result <= 0:
        print('订阅失败,', subConnection.GetErrorMsg(result))
        strERRMSG = lpCheckUnpack.GetStrByIndex(3)
        print(strERRMSG)
    else:
        print('订阅成功')
    lpCheckPack.FreeMem()
    lpCheckPack.Release()
    lpCheckUnpack.Release()
    subParam.Release()
    return subConnection

def ufx_connect(config):

    connection = py_t2sdk.pyConnectionInterface(config)
    pCallBack = py_t2sdk.pyCallbackInterface(
            "tf_vnpy_uf.gateway.uf_gateway",
            "TdAsyncCallback"
        )#py_t2sdk.pyCallbackInterface('pyCallBack', 'pyCallBack')
    pCallBack.InitInstance()
    errMsg = ''
    ret = connection.Create2BizMsg(pCallBack)
    if ret != 0:
        print('creat faild!!')
        errMsg = 'creat faild!!'
        return ret, errMsg, connection
    ret = connection.Connect(3000)
    if ret != 0:
        print('connect faild:')
        errMsg = connection.GetErrorMsg(ret)
        print(errMsg)
    return ret, errMsg, connection
def getBizMsg(lpPack, funId, packetType=0):
    pyMsg = py_t2sdk.pyIBizMessage()
    pyMsg.SetFunction(funId)
    pyMsg.SetPacketType(packetType)
    pyMsg.SetContent(lpPack.GetPackBuf(), lpPack.GetPackLen())
    return pyMsg



import py_t2sdk
from array import array
from time import ctime, sleep
import _thread
from threading import Thread, Lock
import time
import common
import ctypes
import os
# import global_test

#记录模块
import logging
# 交易所映射
EXCHANGE_UF2VT: Dict[str, Exchange] = {
    "1": Exchange.SSE,
    "2": Exchange.SZSE,
    "7": Exchange.CFFEX,
    "3": Exchange.SHFE,
    "4": Exchange.CZCE,
    "9": Exchange.DCE,
    "k": Exchange.INE,
    # HS_EI_GFEX: Exchange.GFEX,
}
# 买卖方向映射
OFFSET_UF2VT: Dict[str, Offset] = {
    "1": Offset.OPEN,
    "2": Offset.CLOSE,
    "7": Offset.CLOSETODAY,
    "3": Offset.CLOSEYESTERDAY,
}
# 交易品种映射
STOCK_TYPE_UF2VT: Dict[str,Product] = {
    "01": Product.EQUITY,
    "02": Product.FUND,
    "03": Product.BOND,
    "04": Product.BOND,
    "05": Product.BOND, 
    "06": Product.BOND, 
    "0w": Product.INDEX,
    "0v": Product.FUTURES, 
    "0W": Product.FUTURES,
    "0F": Product.ETF, 
    "0(": Product.OPTION, 
    "0)": Product.OPTION, 
    # HS_EI_GFEX: Exchange.GFEX,
}
# 交易所反向映射
EXCHANGE_VT2UF: Dict[Exchange, str] = {v: k for k, v in EXCHANGE_UF2VT.items()}
# 方向映射
DIRECTION_VT2UF: Dict[Direction, str] = {
    Direction.LONG: "1",
    Direction.SHORT: "2"
}
# 方向反相映射
DIRECTION_UF2VT: Dict[str, Direction] = {v: k for k, v in DIRECTION_VT2UF.items()}

# 委托类型映射
ORDERTYPE_VT2UF: Dict[OrderType, str] = {
    OrderType.LIMIT: "0",
    OrderType.MARKET: "U"
}
ORDERTYPE_UF2VT: Dict[str, OrderType] = {v: k for k, v in ORDERTYPE_VT2UF.items()}

# 状态映射
STATUS_UF2VT={
        
    '9':Status.CANCELLED,
    '8':Status.NOTTRADED,
    '7':Status.ALLTRADED,
    '6':Status.PARTTRADED,
    '5':Status.REJECTED,
    '4':Status.NOTTRADED,
    '3':Status.SUBMITTING,
    '2':Status.NOTTRADED,
    '1':Status.NOTTRADED,

    'A':Status.NOTTRADED,
    'B':Status.NOTTRADED,
    'C':Status.NOTTRADED,
    'D':Status.NOTTRADED,
    'E':Status.NOTTRADED,
    'a':Status.NOTTRADED,
    'b':Status.NOTTRADED,
    'c':Status.NOTTRADED,
    'd':Status.NOTTRADED,
    'e':Status.NOTTRADED,
    'f':Status.NOTTRADED,
    
}
CHINA_TZ = timezone("Asia/Shanghai")       # 中国时区
		
symbol_contract_map: Dict[str, ContractData] = {} # 设置合约代码和合约数据映射
symbol_contract_index_map: Dict[str, ContractData] = {} # 设置指数合约代码和合约数据映射
exchange_market_status: Dict[Exchange, int] = {v: 0 for k, v in EXCHANGE_UF2VT.items()} # 设置交易所的连接状态
exchange_market_is_ex: Dict[Exchange, int] = {v: 1 for k, v in EXCHANGE_UF2VT.items()} # 设置交易所的交易状态
class UfGateway(BaseGateway):
    """UF证券接口"""
    default_name: str = "UF"
    default_setting: Dict[str, Any] = { # 这里定义需要输入的账号信息，前面一个账号是现货单元，后面一个账号是期货
        "UF账号": "",
        "UF密码": "",
        "account_code": "",
        "asset_no": "",
        "combi_no": "",
        "account_code2": "",
        "asset_no2": "",
        "combi_no2": "",
        "sleeptime": "",
    }
    exchanges: List[str] = list(EXCHANGE_UF2VT.values()) # 定义所有可用的交易所
    def __init__(self, event_engine: EventEngine, gateway_name: str = "UF") -> None:
        """构造函数"""
        # 调用父类的构造函数
        super().__init__(event_engine, gateway_name) 
        # 创建类内的两个成员变量，td_api（交易api）和md_api（交易api）
        self.td_api: "TdApi" = TdApi(self)
        self.md_api: "MdApi" = MdApi(self)
        # 设置睡眠时间
        self.sleeptime=15
        self.count2=0 # process_exchange_market_status_event的计时器
        self.count3=0 # 计数器
        self.nsubscribe=0#订阅的数量
        self.uf_account= ''
        self.uf_password= ''
        self.account_code=''
        self.asset_no=''
        self.combi_no=''
        self.account_code2=''
        self.asset_no2=''
        self.combi_no2=''
        cfg = ama.Cfg()
        # 对AMD API进行初始化
        Init(self.md_api,cfg)
        self.AllSubContracts={} # 所有订阅的合约和其交易所的映射
        self.contracts: Dict[str, ContractData] = {} # 所有订阅的合约
    def connect(self, setting: dict) -> None:
        """连接服务器（连接恒生O32系统）"""

        # 连接UF交易服务器
        self.uf_account= setting["UF账号"] # 变量初始化定义
        self.uf_password= setting["UF密码"]
        self.account_code=setting["account_code"]
        self.asset_no=setting["asset_no"]
        self.combi_no=setting["combi_no"]
        self.account_code2=setting["account_code2"]
        self.asset_no2=setting["asset_no2"]
        self.combi_no2=setting["combi_no2"]
        self.sleeptime=int(setting["sleeptime"])

        self.td_api.connect( # 交易端口连接
            self.uf_account,
            self.uf_password,
            self.account_code,
            self.asset_no,
            self.combi_no,
            self.account_code2,
            self.asset_no2,
            self.combi_no2
        )

        self.init_query() # 初始化查询，查询持仓
    

    def get_order_num(self):
        return self.td_api.equity_count # 获得权益的下单函数执行数量
    def subscribe(self, req: SubscribeRequest) -> None:
        '''
        SubscribeRequest中有三个变量 代码、交易所、代码.交易所
        '''
        
        """订阅行情"""
        self.AllSubContracts[req.symbol]=req.exchange

        # 通过AMD接口，对行情完成订阅
        Subscription(req,self.nsubscribe)
        self.nsubscribe += 1#获得订阅的数量


    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        return self.td_api.send_order(req)
    def send_risk_test(self, req: OrderRequest) -> str:
        """委托下单"""
        return self.td_api.send_risk_test(req)
    def send_orders(self, req) -> str:
        """委托下单"""
        return self.td_api.send_orders(req)
    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        self.td_api.cancel_order(req)

    def query_account(self) -> None:
        """查询账户"""
        self.td_api.query_account()

    def query_position(self) -> None:
        """查询持仓"""
        self.td_api.query_position(self.account_code,self.asset_no,31001) # 查询现货持仓
        self.td_api.query_position(self.account_code2,self.asset_no2,31003) # 查询期权持仓
        self.td_api.query_position(self.account_code2,self.asset_no2,31004) # 查询期货持仓


    def query_order(self) -> None: # 查询现货，期货，期权委托
        """查询委托"""
        self.td_api.query_order(self.account_code,self.asset_no,32001) # 证券委托查询
        self.td_api.query_order(self.account_code2,self.asset_no2,32003) # 期货委托查询
        self.td_api.query_order(self.account_code2,self.asset_no2,32004) # 期权委托查询

    def query_trade(self) -> None: # 查询现货,期货，期权成交
        """查询成交"""
        self.td_api.query_trade(self.account_code,self.asset_no,33001) # 证券成交查询
        self.td_api.query_trade(self.account_code2,self.asset_no2,33003) # 期货成交查询
        self.td_api.query_trade(self.account_code2,self.asset_no2,33004) # 期权成交查询

    def close(self) -> None:
        """关闭连接"""
        self.td_api.close() # 断开交易连接
        ama.IAMDApi_Release() # 彻底关闭AMA

    def process_timer_event(self, event) -> None:
        """处理定时事件"""
        self.count += 1
        if self.count <2:
            return
        self.count = 0

        func = self.query_functions.pop(0)
        func()
        self.query_functions.append(func)


    def init_query(self) -> None:#
        """初始化时间事件注册"""

        self.count: list = 0
        self.query_functions: list = [self.query_account, self.query_position] # 每两秒查询一次资金和仓位
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)      # 注册定时查询事件（每次从query_functions里取出函数去执行）
        self.event_engine.register(EVENT_TIMER, self.process_exchange_market_status_event) # 注册查询交易所行情状态的事件
        #self.event_engine.register(EVENT_TIMER, self.process_ssss)


    def process_heartBeat_event(self) -> None:
        """定时事件处理"""
        self.td_api.heartBeat()
    def process_exchange_market_status_event(self, event) -> None:
        self.count2 += 1
        if self.count2 <self.sleeptime:
            return
        self.count2 =0
        self.process_heartBeat_event() # 发送心脏跳动
        for k, v in EXCHANGE_UF2VT.items(): # 判断15秒内有交易所有无合约的tick数据更新
            if exchange_market_status[v]==0 and exchange_market_is_ex[v]==1:
                self.write_log(f"交易所{v.value}断开连接")
                exchange_market_is_ex[v]=0
                for orderid in self.td_api.orders.keys(): # 判断断开，全部撤单
                    order=self.td_api.orders[orderid]
                    if order.exchange==v and (order.status==Status.SUBMITTING or order.status==Status.NOTTRADED or order.status==Status.PARTTRADED):
                        self.write_log(f"由于{v.value}断开连接，订单{order.orderid}撤单")
                        self.cancel_order(CancelRequest(orderid,order.symbol,order.exchange))
                
            exchange_market_status[v]=0

    def get_orders_status(self,orderid): # 获取合约的状态
        """获取组合合约的状态"""
        if self.td_api.orders[orderid].status==Status.REJECTED:
            return 0
        else:
            return 1
    def get_orders_remain(self,orderid): # 获取组合下单合约订单的全部剩余状态
        """获取组合合约的未成交的部分"""
        if orderid in self.td_api.remain.keys():
            return self.td_api.remain[orderid]
        else:
            return {}
class MdApi(ama.IAMDSpi):
    def __init__(self, gateway: UfGateway) -> None:
        """构造函数"""
        super().__init__()
        self.gateway: UfGateway = gateway
    def OnLog(self, level, log, length):
        level_string = "None"
        # if(level == ama.LogLevel.kTrace):
        #     level_string = "Trace"
        # elif(level == ama.LogLevel.kDebug):
        #     level_string = "Debug"
        # elif(level == ama.LogLevel.kInfo):
        #     level_string = "Info"
        # elif(level == ama.LogLevel.kWarn):
        #     level_string = "Warn"
        if(level == ama.LogLevel.kError):
            level_string = "Error"
        elif(level == ama.LogLevel.kFatal):
            level_string = "Fatal"

        #print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " "+ level_string + " AmaLog " + log)
    def OnIndicator(self, ind, length):
        pass
    def OnMDSnapshot(self, snapshots, cnt): # 股票行情切片
        #部分数据获取使用示例
            # print(cnt)
        for i in range(cnt):
            data = ama.Tools_GetDataByIndex(snapshots, i)                  # 取出第i个数据
            contract: ContractData = symbol_contract_map.get(data.security_code, None)
            # print(data.security_code)
            if not contract:
                return
            
            tick: tick = TickData(
                symbol=data.security_code, # 证券代码
                exchange=contract.exchange, 
                datetime=generate_datetime2(str(data.orig_time)),
                name=contract.name,
                open_price=data.open_price/1e6, # 开盘价
                high_price=data.high_price/1e6, # 最高价
                low_price=data.low_price/1e6,   # 最低价
                pre_close=data.pre_close_price/1e6, # 收盘价
                last_price=data.last_price/1e6,     # 最新价
                volume=data.total_volume_trade,     # 成交总量
                turnover=data.total_value_trade,    # 成交总额
                bid_price_1=ama.Tools_GetInt64DataByIndex(data.bid_price, 0)/1e6, # 买一价
                bid_price_2=ama.Tools_GetInt64DataByIndex(data.bid_price, 1)/1e6, # 买二价
                bid_price_3=ama.Tools_GetInt64DataByIndex(data.bid_price, 2)/1e6, # 买三价
                bid_price_4=ama.Tools_GetInt64DataByIndex(data.bid_price, 3)/1e6, # 买四价
                bid_price_5=ama.Tools_GetInt64DataByIndex(data.bid_price, 4)/1e6, # 买五价
                bid_volume_1=ama.Tools_GetInt64DataByIndex(data.bid_volume, 0) ,  # 买一量
                bid_volume_2=ama.Tools_GetInt64DataByIndex(data.bid_volume, 1) ,  # 买二量
                bid_volume_3=ama.Tools_GetInt64DataByIndex(data.bid_volume, 2) ,  # 买三量
                bid_volume_4=ama.Tools_GetInt64DataByIndex(data.bid_volume, 3) ,  # 买四量
                bid_volume_5=ama.Tools_GetInt64DataByIndex(data.bid_volume, 4) ,  # 买五量
                ask_price_1=ama.Tools_GetInt64DataByIndex(data.offer_price, 0)/1e6,  # 卖一价
                ask_price_2=ama.Tools_GetInt64DataByIndex(data.offer_price, 1)/1e6,  # 卖二价
                ask_price_3=ama.Tools_GetInt64DataByIndex(data.offer_price, 2)/1e6,  # 卖三价
                ask_price_4=ama.Tools_GetInt64DataByIndex(data.offer_price, 3)/1e6,  # 卖四价
                ask_price_5=ama.Tools_GetInt64DataByIndex(data.offer_price, 4)/1e6,  # 卖五价
                ask_volume_1=ama.Tools_GetInt64DataByIndex(data.offer_volume, 0),    # 卖一量
                ask_volume_2=ama.Tools_GetInt64DataByIndex(data.offer_volume, 1),    # 卖二量
                ask_volume_3=ama.Tools_GetInt64DataByIndex(data.offer_volume,2),     # 卖三量
                ask_volume_4=ama.Tools_GetInt64DataByIndex(data.offer_volume,3),     # 卖四量
                ask_volume_5=ama.Tools_GetInt64DataByIndex(data.offer_volume,4),     # 卖五量
                gateway_name="UF"
            )
            self.gateway.on_tick(tick)
            #sleep(10) 
            exchange_market_status[contract.exchange] += 1 # 由于有新的行情到来，更新交易所行情状态
            if exchange_market_is_ex[contract.exchange] == 0:
                self.gateway.write_log(f"交易所{contract.exchange.value}重新连接")
            exchange_market_is_ex[contract.exchange]=1
        ama.Tools_FreeMemory(snapshots)
    def OnMDBondSnapshot(self, snapshots, cnt): # 债券行情切片
        for i in range(cnt):
            data = ama.Tools_GetDataByIndex(snapshots, i)                  #取出第i个数据
            contract: ContractData = symbol_contract_map.get(data.security_code, None)
            # print(data.security_code)
            if not contract:
                return
            # print({'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice,"ooo":data.open_price/1e6})
            # # data_dict[data.security_code]={'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice}
            # print(data.orig_time)
            
            tick: tick = TickData(
                symbol=data.security_code, # 证券代码
                exchange=contract.exchange, # 交易所
                datetime=generate_datetime2(str(data.orig_time)), # 时间
                name=contract.name, # 合约名称
                open_price=data.open_price/1e6, # 开盘价
                high_price=data.high_price/1e6, # 最高价
                low_price=data.low_price/1e6,   # 最低价
                pre_close=data.pre_close_price/1e6, # 作收价
                last_price=data.last_price/1e6,     # 最新价
                volume=data.total_volume_trade,     # 成交总量
                turnover=data.total_value_trade,    # MDBondSnapshot没有换手率，这里给换手率用成交总额站位
                bid_price_1=ama.Tools_GetInt64DataByIndex(data.bid_price, 0)/1e6, # 买一价
                bid_price_2=ama.Tools_GetInt64DataByIndex(data.bid_price, 1)/1e6, # 买二价
                bid_price_3=ama.Tools_GetInt64DataByIndex(data.bid_price, 2)/1e6, # 买三价
                bid_price_4=ama.Tools_GetInt64DataByIndex(data.bid_price, 3)/1e6, # 买四价
                bid_price_5=ama.Tools_GetInt64DataByIndex(data.bid_price, 4)/1e6, # 买五价
                bid_volume_1=ama.Tools_GetInt64DataByIndex(data.bid_volume, 0) ,  # 买一量
                bid_volume_2=ama.Tools_GetInt64DataByIndex(data.bid_volume, 1) ,  # 买二量
                bid_volume_3=ama.Tools_GetInt64DataByIndex(data.bid_volume, 2) ,  # 买三量
                bid_volume_4=ama.Tools_GetInt64DataByIndex(data.bid_volume, 3) ,  # 买四量
                bid_volume_5=ama.Tools_GetInt64DataByIndex(data.bid_volume, 4) ,  # 买五量
                ask_price_1=ama.Tools_GetInt64DataByIndex(data.offer_price, 0)/1e6,  # 卖一价
                ask_price_2=ama.Tools_GetInt64DataByIndex(data.offer_price, 1)/1e6,  # 卖二价
                ask_price_3=ama.Tools_GetInt64DataByIndex(data.offer_price, 2)/1e6,  # 卖三价
                ask_price_4=ama.Tools_GetInt64DataByIndex(data.offer_price, 3)/1e6,  # 卖四价
                ask_price_5=ama.Tools_GetInt64DataByIndex(data.offer_price, 4)/1e6,  # 卖五价
                ask_volume_1=ama.Tools_GetInt64DataByIndex(data.offer_volume, 0),    # 卖一量
                ask_volume_2=ama.Tools_GetInt64DataByIndex(data.offer_volume, 1),    # 卖二量
                ask_volume_3=ama.Tools_GetInt64DataByIndex(data.offer_volume,2),     # 卖三量
                ask_volume_4=ama.Tools_GetInt64DataByIndex(data.offer_volume,3),     # 卖四量
                ask_volume_5=ama.Tools_GetInt64DataByIndex(data.offer_volume,4),     # 卖五量
                gateway_name="UF"
            )
            exchange_market_status[contract.exchange]+=1
            if exchange_market_is_ex[contract.exchange]==0:
                self.gateway.write_log(f"交易所{contract.exchange.value}重新连接")
            exchange_market_is_ex[contract.exchange]=1

        ama.Tools_FreeMemory(snapshots)
    def OnMDFutureSnapshot(self, snapshots, cnt): # 期货行情切片
        # # print(i)
        # print ('This is a test ----------------- ')
        # try:
        for i in range(cnt):
            data = ama.Tools_GetDataByIndex(snapshots, i)  
            #start_time = datetime.now()
            # print (data)
            # print(i)
            # print(data.security_code)               #取出第i个数据
            contract: ContractData = symbol_contract_map.get(data.security_code, None)
            # print(data.security_code)
            if not contract:
                return
            #print({'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice,"ooo":data.open_price/1e6})
            # # data_dict[data.security_code]={'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice}
            # print(data.orig_time)

            tick: tick = TickData(
                symbol=data.security_code,  # 期货代码
                exchange=contract.exchange, # 交易所
                datetime=generate_datetime2(str(data.orig_time)), # 时间
                name=contract.name,  # 合约名称
                open_price=data.open_price/1e6,  # 开盘价
                high_price=data.high_price/1e6,  # 最高价
                low_price=data.low_price/1e6,    # 最低价
                pre_close=data.pre_close_price/1e6,  # 作收价
                last_price=data.last_price/1e6,      # 最新价
                volume=data.open_interest,           # 持仓量
                turnover=data.total_bid_volume_trade,  # 总买入量
                bid_price_1=ama.Tools_GetInt64DataByIndex(data.bid_price, 0)/1e6,  # 买一价
                # bid_price_2=ama.Tools_GetInt64DataByIndex(data.bid_price, 1)/1e6,
                # bid_price_3=ama.Tools_GetInt64DataByIndex(data.bid_price, 2)/1e6,
                # bid_price_4=ama.Tools_GetInt64DataByIndex(data.bid_price, 3)/1e6,
                # bid_price_5=ama.Tools_GetInt64DataByIndex(data.bid_price, 4)/1e6,
                bid_volume_1=ama.Tools_GetInt64DataByIndex(data.bid_volume, 0) ,  # 买一量
                # bid_volume_2=ama.Tools_GetInt64DataByIndex(data.bid_volume, 1) ,
                # bid_volume_3=ama.Tools_GetInt64DataByIndex(data.bid_volume, 2) ,
                # bid_volume_4=ama.Tools_GetInt64DataByIndex(data.bid_volume, 3) ,
                # bid_volume_5=ama.Tools_GetInt64DataByIndex(data.bid_volume, 4) ,
                ask_price_1=ama.Tools_GetInt64DataByIndex(data.offer_price, 0)/1e6,  # 卖一价
                # ask_price_2=ama.Tools_GetInt64DataByIndex(data.offer_price, 1)/1e6,
                # ask_price_3=ama.Tools_GetInt64DataByIndex(data.offer_price, 2)/1e6,
                # ask_price_4=ama.Tools_GetInt64DataByIndex(data.offer_price, 3)/1e6,
                # ask_price_5=ama.Tools_GetInt64DataByIndex(data.offer_price, 4)/1e6,
                ask_volume_1=ama.Tools_GetInt64DataByIndex(data.offer_volume, 0),    # 卖一量
                # ask_volume_2=ama.Tools_GetInt64DataByIndex(data.offer_volume, 1),
                # ask_volume_3=ama.Tools_GetInt64DataByIndex(data.offer_volume,2),
                # ask_volume_4=ama.Tools_GetInt64DataByIndex(data.offer_volume,3),
                # ask_volume_5=ama.Tools_GetInt64DataByIndex(data.offer_volume,4),
                gateway_name="UF"
            )
            #sleep(10) 
            self.gateway.on_tick(tick)
            #sleep(10) 
            exchange_market_status[contract.exchange]+=1
            if exchange_market_is_ex[contract.exchange]==0:
                self.gateway.write_log(f"交易所{contract.exchange.value}重新连接")
            exchange_market_is_ex[contract.exchange]=1
            #end_time = datetime.now()
            #elapsed_time = end_time - start_time
            #print(f"The loop took {elapsed_time} to complete.")
                
        # except Exception as error:
        #     print(error)
        #     pass
        ama.Tools_FreeMemory(snapshots)
    def OnMDOptionSnapshot(self, snapshots, cnt): # 期权行情切片
        for i in range(cnt):
            data = ama.Tools_GetDataByIndex(snapshots, i)   
            # print(data.security_code)               #取出第i个数据
            contract: ContractData = symbol_contract_map.get(data.security_code, None)
            # print(data.security_code)
            if not contract:
                return
            #print({'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice,"ooo":data.open_price/1e6})
            # # data_dict[data.security_code]={'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice}
            # print(data.orig_time)

            tick: tick = TickData(
                symbol=data.security_code,  # 期权代码
                exchange=contract.exchange, # 交易所
                datetime=generate_datetime2(str(data.orig_time)),  # 时间
                name=contract.name,     # 合约名称
                open_price=data.open_price/1e6,   # 开盘价
                high_price=data.high_price/1e6,   # 最高价
                low_price=data.low_price/1e6,     # 最低价
                pre_close=data.pre_close_price/1e6,  # 昨收价
                last_price=data.last_price/1e6,      # 最新价
                # volume=data.open_interest,
                # turnover=data.total_bid_volume_trade,
                bid_price_1=ama.Tools_GetInt64DataByIndex(data.bid_price, 0)/1e6,   # 买一价
                bid_volume_1=ama.Tools_GetInt64DataByIndex(data.bid_volume, 0) ,    # 买一量
                ask_price_1=ama.Tools_GetInt64DataByIndex(data.offer_price, 0)/1e6,  # 卖一价
                ask_volume_1=ama.Tools_GetInt64DataByIndex(data.offer_volume, 0),    # 卖一量
                gateway_name="UF"
            )
            # self.gateway.on_tick(tick)
            exchange_market_status[contract.exchange]+=1
            if exchange_market_is_ex[contract.exchange]==0:
                self.gateway.write_log(f"交易所{contract.exchange.value}重新连接")
            exchange_market_is_ex[contract.exchange]=1
        ama.Tools_FreeMemory(snapshots)
    def OnMDIndexSnapshot(self, snapshots, cnt):  # 指数行情切片
        for i in range(cnt):
            data = ama.Tools_GetDataByIndex(snapshots, i) 
            # print(data)  
            # print(data.security_code)               #取出第i个数据
            # print(data.security_code)
            contract: ContractData = symbol_contract_index_map.get(data.security_code, None)
            # print(data.security_code)
            if not contract:
                return
            #print({'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice,"ooo":data.open_price/1e6})
            # # data_dict[data.security_code]={'orig_time':data.orig_time,'bid_volume':bidVolume,'bid_price':bidPrice,'offer_price':offerPrice}
            # print(data.orig_time)

            tick: tick = TickData(
                symbol=data.security_code,  # 证券代码
                exchange=contract.exchange, # 交易所
                datetime=generate_datetime2(str(data.orig_time)),  # 时间
                name=contract.name,         # 合约名称
                open_price=data.open_index/1e7,  # 开盘价
                high_price=data.high_index/1e7,  # 最高价
                low_price=data.low_index/1e7,    # 最低价
                pre_close=data.pre_close_index/1e7,  # 昨收价
                last_price=data.last_index/1e7,      # 最新价
                volume=data.total_volume_trade,      # 成交量
                turnover=data.total_value_trade,     # 指数没有换手率，这里用成交额占位
                bid_price_1=round(data.last_index/1e7,4),  # 买一价
                bid_volume_1=100,                          # 买一量
                ask_price_1=round(data.last_index/1e7,4),  # 卖一价
                ask_volume_1=100,                          # 卖一量
 
                gateway_name="UF"
            )
            self.gateway.on_tick(tick)
            exchange_market_status[contract.exchange]+=1
            if exchange_market_is_ex[contract.exchange]==0:
                self.gateway.write_log(f"交易所{contract.exchange.value}重新连接")
            exchange_market_is_ex[contract.exchange]=1
                
        ama.Tools_FreeMemory(snapshots)
class TdApi:
    """UF交易Api"""
    def __init__(self, gateway: UfGateway) -> None:
        """构造函数"""
        self.user_token=""
        self.ex_orderid={}
        self.gateway: UfGateway = gateway
        self.gateway_name: str = gateway.gateway_name
        self.asset_no=''
        self.equity_count=0
        # 绑定自身实例到全局对象
        global td_api
        if not td_api:
            td_api = self

        # 登录信息
        self.branch_no: int = 0
        self.entrust_way: str = ""
        self.account: str = ""
        self.password: str = ""
        self.license: str = ""
        self.combi_no=''
        # 运行缓存
        self.connect_status: bool = False
        self.login_status: bool = False
        self.user_token: str = ""
        self.client_id: str = ""
        self.session_no: str = ""
        self.order_count: int = 0
        self.account_code=""
        self.orders: Dict[str, OrderData] = {} # 订单
        self.batch_order_id=[]
        self.reqid_orderid_map: Dict[int, str] = {}
        self.orderid_ex={}
        self.fupositions: Dict[str, PositionData] = {}
        self.eqpositions: Dict[str, PositionData] = {}
        self.batch_no_orderid={}
        self.combi_orderlist={} # 组合下单，下面是组合证券的代码索引到下面各个的orderid
        self.date_str: str = datetime.now().strftime("%Y%m%d")
        self.tradeids: Set[str] = set()
        self.remain={}
        self.localid_sysid_map: Dict[str, str] = {}
        self.sysid_localid_map: Dict[str, str] = {}
        self.reqid_sysid_map: Dict[int, str] = {}

        # 连接对象
        self.connection: py_t2sdk.pyConnectionInterface = None
        self.callback: Callable = None
        
        # 初始化回调
        self.init_callbacks()
        self._active=True
    def init_callbacks(self) -> None:
        """初始化回调函数"""
        self.callbacks: dict = {
            10001: self.on_login,          # 登录
            30011: self.on_query_contract, # 证券信息查询
            30010: self.on_query_future,                     # 期货信息查询
            30012:self.on_query_option_contract,# 期权信息查询
            34001: self.on_query_account,   # 账户资金查询
            31001: self.on_query_position, # 证券持仓查询
            31003: self.on_query_future_position, # 查询期货持仓
            31004: self.on_query_option_position, # 查询期货持仓
            32001: self.on_query_order,           # 证券委托查询
            32003: self.on_query_future_order,    # 期货委托查询
            32004: self.on_query_option_order,
            99999:self.on_sub_message,            # 99999 是一个魔数（自己规定的数），处理子回报
            33001: self.on_query_trade,           # 证券成交查询
            33003: self.on_query_future_trade,    # 期货成交查询
            33004: self.on_query_option_trade,
            91090: self.on_send_order, # 篮子委托
            91102:self.on_cancel_order             # 篮子撤单（按委托批号撤单）
        }
    def heartBeat(self):
        pHeartBeatPack = py_t2sdk.pyIF2Packer()
        pHeartBeatPack.BeginPack()
        pHeartBeatPack.AddField('user_token', 'S', 512, 0)
        pHeartBeatPack.AddStr(self.user_token)
        pHeartBeatPack.EndPack()
        pyMsg = getBizMsg(pHeartBeatPack, 10000, 0) # 心跳事件
        pHeartBeatPack.FreeMem()
        pHeartBeatPack.Release()
        self.connection.SendBizMsg(pyMsg, 1)
    def connect(
        self,
        account: str,
        password: str,
        account_code: str,
        asset_no: str,
        combi_no: str,
        account_code2: str,
        asset_no2: str,
        combi_no2: str,
    ) -> None:
        """连接服务器"""
        self.account = account
        self.password = password
        self.account_code=account_code
        self.asset_no=asset_no
        self.combi_no=combi_no
        self.account_code2=account_code2
        self.asset_no2=asset_no2
        self.combi_no2=combi_no2
        # 如果尚未连接，则尝试连接
        if not self.connect_status:
            self.callback=self.init_connection("交易")
            self.connect_status = True
            # tHeartBeat = Thread(target=heartBeat, args=(self.connection,))
            # # 启动维持心跳线程
            # tHeartBeat.start()

        # 连接完成后发起登录请求
        if not self.login_status:
            self.login()
    def init_connection(self, name: str) -> None:
        """初始化连接"""
        py_t2sdk.PyT2sdkInitialize()
        # ufx_start()
        subscribe()
        # print("订阅成功")
        config = py_t2sdk.pyCConfigInterface()
        config.Load(t2sdkini)
        # 获取连接
        ret, errMsg, self.connection = ufx_connect(config)
        if ret != 0:
            self.gateway.write_log(f"订阅失败，错误码{ret}，错误信息{errMsg}")
            print('获取连接失败:', errMsg)
            return
        else:
            print("获取连接成功")
            self.gateway.write_log(f"订阅成功")
        pCallBack = py_t2sdk.pyCallbackInterface(
            "tf_vnpy_uf.gateway.uf_gateway",
            "TdAsyncCallback"
        )
        pCallBack.InitInstance()

        return  pCallBack 

    def close(self) -> None:
        """关闭API"""
        self._active = False

    def check_error(self, data) -> bool:
        """检查报错信息"""
        if not data:
            return False
        error_no= data[0]["ErrorCode"]
        # print(error_no)
        error_INFO=data[0]["ErrorMsg"]
        if error_no:
            if error_no == "0":
                return False
            self.gateway.write_log(f"请求失败，错误代码：{error_no}，错误信息：{error_INFO}")
            return True
        else:
            return False

    def on_login(self, data, reqid: int) -> None:
        """用户登录请求回报"""
        if self.check_error(data):
            self.gateway.write_log("UF证券系统登录失败")
            return
        self.user_token=data[1]['user_token']
        self.gateway.write_log("UF证券系统登录成功")
        self.login_status = True
        self.query_account() # 查询资金
        
        # self.subscribe_trade()
        #self.subscribe_order()
        self.query_contract() # 合约信息查询
        
        self.query_order(self.account_code,self.asset_no,32001) # 证券信息查询
        self.query_order(self.account_code,self.asset_no,32004) # 期权委托查询
        self.query_order(self.account_code2,self.asset_no2,32003) # 期货委托查询
        self.query_order(self.account_code2,self.asset_no2,32004) # 期权委托查询

        self.query_trade(self.account_code,self.asset_no,33001)   # 证券成交查询
        self.query_trade(self.account_code,self.asset_no,33004)   # 期权成交查询
        self.query_trade(self.account_code2,self.asset_no2,33003) # 期货成交查询
        self.query_trade(self.account_code2,self.asset_no2,33004) # 期权成交查询
        #self.query_future_trade()
    def on_query_account(self, data, reqid: int) -> None:
        """资金查询回报"""
        # print( """资金查询回报""")
        if self.check_error(data):
            self.gateway.write_log("资金信息查询失败")
            return
        for d in data[1:]:
            # print("111")
            account: AccountData = AccountData(
                accountid=d["account_code"],
                balance=float(d["current_balance"]),
                frozen=float(d["only_t0_balance"]),
                gateway_name=self.gateway_name
            )
            self.gateway.on_account(account)
    def trader_position(self,order,data):  # 根据订单数据对持仓做处理
        if order.offset==Offset.NONE:
            Position=self.eqpositions[data[0]["stock_code"]+data[0]["market_no"]]
            if data[0]["stock_code"]+data[0]["market_no"] in self.eqpositions.keys():
                if data[0]['entrust_direction']=='1':
                    Position.volume+=float(data[0]['deal_amount'])
                    self.gateway.on_position(Position)
                else:
                    Position.volume-=float(data[0]['deal_amount'])
                    self.gateway.on_position(Position)
            else:
                position: PositionData = PositionData(
                    symbol=data[0]["stock_code"],
                    exchange=EXCHANGE_UF2VT[data[0]["market_no"]],
                    direction=Direction.LONG,
                    volume=0,
                    price=data[0]['deal_price'],
                    frozen=0,
                    yd_volume=0,
                    pnl=0,
                    gateway_name=self.gateway_name
                )
                position.volume+=float(data[0]['deal_amount'])
                position.frozen+=float(data[0]['deal_amount'])
                self.eqpositions[data[0]["stock_code"]+data[0]["market_no"]] = position
                self.gateway.on_position(position)
        else:
            if data[0]['entrust_direction']=='1' and data[0]['futures_direction']=='1':
                if data[0]["stock_code"]+data[0]["market_no"]+'1' in self.fupositions.keys():
                    Position=self.fupositions[data[0]["stock_code"]+data[0]["market_no"]+'1']
                    Position.volume+=float(data[0]['deal_amount'])
                else:
                    Position: PositionData = PositionData(
                        symbol=data[0]["stock_code"],
                        exchange=EXCHANGE_UF2VT[data[0]["market_no"]],
                        direction=Direction.LONG,
                        volume=0,
                        price=data[0]['deal_price'],
                        frozen=0,
                        yd_volume=0,
                        pnl=0,
                        gateway_name=self.gateway_name
                    )
                    Position.volume+=float(data[0]['deal_amount'])
                    Position.frozen+=float(data[0]['deal_amount'])
                    self.fupositions[data[0]["stock_code"]+data[0]["market_no"]+'1'] = Position 
                self.gateway.on_position(Position)
            elif data[0]['entrust_direction']=='1' and data[0]['futures_direction']=='2':
                if data[0]["stock_code"]+data[0]["market_no"]+'1' in self.fupositions.keys():
                    Position=self.fupositions[data[0]["stock_code"]+data[0]["market_no"]+'2']
                    Position.volume-=float(data[0]['deal_amount'])
                self.gateway.on_position(Position)
            elif data[0]['entrust_direction']=='2' and data[0]['futures_direction']=='1':
                if data[0]["stock_code"]+data[0]["market_no"]+'2' in self.fupositions.keys():
                    Position=self.fupositions[data[0]["stock_code"]+data[0]["market_no"]+'2']
                    Position.volume+=float(data[0]['deal_amount'])
                else:
                    Position: PositionData = PositionData(
                        symbol=data[0]["stock_code"],
                        exchange=EXCHANGE_UF2VT[data[0]["market_no"]],
                        direction=Direction.SHORT,
                        volume=0,
                        price=data[0]['deal_price'],
                        frozen=0,
                        yd_volume=0,
                        pnl=0,
                        gateway_name=self.gateway_name
                    )
                    Position.volume+=float(data[0]['deal_amount'])
                    Position.frozen+=float(data[0]['deal_amount'])
                    self.fupositions[data[0]["stock_code"]+data[0]["market_no"]+'2'] = Position 

                self.gateway.on_position(Position)
            elif data[0]['entrust_direction']=='2' and data[0]['futures_direction']=='2':
                Position=self.fupositions[data[0]["stock_code"]+data[0]["market_no"]+'1']
                Position.volume-=float(data[0]['deal_amount'])
                self.gateway.on_position(Position)  
    def on_sub_message(self, data, reqid: int) -> None:##############所有子回报（参考恒生O32文档消息推送部分）
        """委托查询回报"""
        # print( """委托查询回报2222""",reqid)
        # print(data)
        if int(reqid) in self.ex_orderid.keys():
            orderid: str = self.ex_orderid[int(reqid)]
        else:
            orderid=data[0]["entrust_no"]
        self.batch_no_orderid[orderid]=data[0]["batch_no"]
        # print(orderid)
        oorderid=orderid
        if orderid[0]=='*':
            orderid=self.combi_orderlist[orderid][data[0]['stock_code']]
        # print("""委托查询回报222""")
        # print(oorderid,orderid)

            # self.remain[oorderid][order.vt_symbol]=order.volume
            # print(self.remain[oorderid])
            # self.gateway.write_log(f"委托下达{order.symbol},价格：{str(order.price)}")
        order: OrderData = self.orders[orderid]
        # print(data)
        # msgtype == 'a' 表示委托下达
        if data[0]['msgtype']=='a' and order.status==Status.SUBMITTING:
            self.gateway.write_log(f"委托下达{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
            if oorderid[0]=='*':  # 处理组合订单
                self.remain[oorderid][order.vt_symbol]=order.volume
                print(self.remain[oorderid])
                file_name = r"C:\Users\liyou\Desktop\vnpy-3.3.0\tf_o32_vnpy\test.json"
                # 使用json.dump将字典保存为JSON文件
                with open(file_name, "w") as json_file:
                    json.dump(self.remain[oorderid], json_file)
        # msgtype == 'b' 表示委托确认          
        if data[0]['msgtype']=='b' and order.status==Status.SUBMITTING:
            order.status = Status.NOTTRADED # 修改订单状态
            timestamp: str = f"{data[0]['business_date']} {data[0]['business_time']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
            order.datetime=dt
            self.orders[orderid] = order
            self.gateway.on_order(order)
            self.gateway.write_log(f"委托确认{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
            if oorderid[0]=='*':
                self.remain[oorderid][order.vt_symbol]=order.volume
                print(self.remain[oorderid])
                file_name = r"C:\Users\liyou\Desktop\vnpy-3.3.0\tf_o32_vnpy\test.json"
                # 使用json.dump将字典保存为JSON文件
                with open(file_name, "w") as json_file:
                    json.dump(self.remain[oorderid], json_file)
            return
        # msgtype == 'c' 表示委托废单
        if data[0]['msgtype']=='c':
            #order: OrderData = self.orders[orderid]
            order.status =Status.REJECTED # 修改订单状态
            self.orders[orderid] = order
            self.gateway.on_order(order)
            self.gateway.write_log(data[0]['revoke_cause'])
            if oorderid[0]=='*':
                self.remain[oorderid][order.vt_symbol]=order.volume
                file_name = r"C:\Users\liyou\Desktop\vnpy-3.3.0\tf_o32_vnpy\test.json"
                # 使用json.dump将字典保存为JSON文件
                with open(file_name, "w") as json_file:
                    json.dump(self.remain[oorderid], json_file)
                print(self.remain[oorderid])
            return
        
        # msgtype == 'g' 表示委托成交
        if data[0]['msgtype']=='g':
            if data[0]['entrust_state']=='7':  # 如果是已经成交
                #order: OrderData = self.orders[orderid]
                order.status =Status.ALLTRADED
                order.traded=float(data[0]['total_deal_amount'])
                self.orders[orderid] = order
                

                self.gateway.write_log(f"全部成交{order.symbol},{order.offset.value}{order.direction.value},成交价格：{str(data[0]['deal_price'])}")


                timestamp: str = f"{data[0]['deal_date']} {data[0]['deal_time']}"
                dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
                # 组装成交数据
                trade: TradeData = TradeData(
                    symbol=data[0]['stock_code'],
                    exchange=EXCHANGE_UF2VT[str(data[0]["market_no"])],
                    orderid=orderid,
                    tradeid=data[0]["deal_no"],
                    direction=DIRECTION_UF2VT[str(data[0]["entrust_direction"])],
                    offset=order.offset,
                    price=float(data[0]['deal_price']),
                    volume=float(data[0]['total_deal_amount']),
                    datetime=dt,
                    gateway_name=self.gateway_name
                )
                self.gateway.on_trade(trade)
                self.gateway.on_order(order)
                self.trader_position(order,data)           
                if oorderid[0]=='*':
                    self.remain[oorderid][order.vt_symbol]=0
                    self.orders[oorderid].traded+=1
                    if self.orders[oorderid].traded==self.orders[oorderid].volume:

                        self.orders[oorderid].status=Status.ALLTRADED
                        trade: TradeData = TradeData(
                        symbol=oorderid,
                        exchange=EXCHANGE_UF2VT[str(data[0]["market_no"])],
                        orderid=orderid,
                        tradeid=data[0]["deal_no"],
                        direction=DIRECTION_UF2VT[str(data[0]["entrust_direction"])],
                        # offset=order.offset,
                        price=float(data[0]['deal_price']),
                        volume=float(data[0]['total_deal_amount']),
                        datetime=dt,
                        gateway_name=self.gateway_name
                        )
                        self.gateway.write_log(f"组合下的每一笔订单全部成交")
                        self.gateway.on_trade(trade)
                    else:
                        self.orders[oorderid].status=Status.PARTTRADED

                    self.gateway.on_order(self.orders[oorderid])
                    file_name = r"C:\Users\liyou\Desktop\vnpy-3.3.0\tf_o32_vnpy\test.json"
                    # 使用json.dump将字典保存为JSON文件
                    with open(file_name, "w") as json_file:
                        json.dump(self.remain[oorderid], json_file)
                    print(self.remain[oorderid])
            elif data[0]['entrust_state']=='6':  # 如果是部分成交
                #order: OrderData = self.orders[orderid]
                order.status = Status.PARTTRADED
                order.traded=float(data[0]['total_deal_amount'])
                self.orders[orderid] = order
                self.gateway.on_order(order)
                self.gateway.write_log(f"部分成交{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
                self.trader_position(order,data)

                if oorderid[0]=='*':
                    self.remain[oorderid][order.vt_symbol]=order.volume-order.traded
                    file_name = r"C:\Users\liyou\Desktop\vnpy-3.3.0\tf_o32_vnpy\test.json"
                    # 使用json.dump将字典保存为JSON文件
                    with open(file_name, "w") as json_file:
                        json.dump(self.remain[oorderid], json_file)
                    print(self.remain[oorderid])
            return
        # 委托撤成
        if data[0]['msgtype']=='e':
            #order: OrderData = self.orders[orderid]
            order.status = Status.CANCELLED
            self.orders[orderid] = order
            self.gateway.on_order(order)
            self.gateway.write_log(f"{data[0]['business_time'][:-4]}:{data[0]['business_time'][-4:-2]}:{data[0]['business_time'][-2:]}撤单成功{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
            return
        # 委托撤废
        if data[0]['msgtype']=='f':
            #order: OrderData = self.orders[orderid]
            self.gateway.write_log(f"撤单失败{order.symbol},{order.offset.value}{order.direction.value}")
            return
        # 委托撤单
        if data[0]['msgtype']=='d':
            #order: OrderData = self.orders[orderid]
            self.gateway.write_log(f"{data[0]['business_time'][:-4]}:{data[0]['business_time'][-4:-2]}:{data[0]['business_time'][-2:]}撤单提交{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
            return
        # 合笔委托下达
        if data[0]['msgtype']=='h':
            order: OrderData = self.orders[orderid]
            self.gateway.write_log(f"{data[0]['business_time'][:-4]}:{data[0]['business_time'][-4:-2]}:{data[0]['business_time'][-2:]}撤单提交{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
            return
    def on_query_trade(self, data: List[Dict[str, str]], reqid: int) -> None:
        """成交查询回报"""
        # print(data)
        if self.check_error(data):
            self.gateway.write_log("成交信息查询失败")
            return
        for d in data[1:]:
            timestamp: str = f"{d['deal_date']} {d['deal_time']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
            # print(dt)

            orderid: str = d["entrust_no"] # 委托编号作为orderid
            # 组建成交数据
            trade: TradeData = TradeData(
                orderid=orderid,
                tradeid=d["deal_no"],
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[str(d["market_no"])],
                direction=DIRECTION_UF2VT[str(d["entrust_direction"])],
                price=float(d["deal_price"]),
                volume=int(float(d["deal_amount"])),
                datetime=dt,
                gateway_name=self.gateway_name
            )
            # 过滤重复的成交推送
            if trade.tradeid in self.tradeids:
                continue
            self.tradeids.add(trade.tradeid)

            self.gateway.on_trade(trade)
            position_str = d["position_str"]
            account_code = d["account_code"]
            asset_no = d["asset_no"]
        if len(data) <1000:
            self.gateway.write_log("成交信息查询成功")
        else:
            self.query_trade(self,account_code,asset_no,33001, position_str)
    def on_query_future_trade(self, data: List[Dict[str, str]], reqid: int) -> None: # 期货成交回报查询
        """成交查询回报"""
        # print(data)
        if self.check_error(data):
            self.gateway.write_log("成交信息查询失败")
            return
        # print(data)
        for d in data[1:]:
            timestamp: str = f"{d['deal_date']} {d['deal_time']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
            # print(dt)

            orderid: str = d["entrust_no"]
            trade: TradeData = TradeData(
                orderid=orderid,
                tradeid=d["deal_no"],
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[str(d["market_no"])],
                direction=DIRECTION_UF2VT[str(d["entrust_direction"])],
                price=float(d["deal_price"]),
                volume=int(float(d["deal_amount"])),
                datetime=dt,
                gateway_name=self.gateway_name
            )
            # 过滤重复的成交推送
            if trade.tradeid in self.tradeids:
                continue
            self.tradeids.add(trade.tradeid)

            self.gateway.on_trade(trade)
            position_str = d["position_str"]
            account_code = d["account_code"]
            asset_no = d["asset_no"]
        if len(data) <1000:
            self.gateway.write_log("成交信息查询成功")
        else:
            self.query_trade(self,account_code,asset_no,33003, position_str)
    def on_query_option_trade(self, data: List[Dict[str, str]], reqid: int) -> None: # 期权成交查询回调
        """成交查询回报"""
        # print(data)
        if self.check_error(data):
            self.gateway.write_log("成交信息查询失败")
            return
        # print(data)
        for d in data[1:]:
            timestamp: str = f"{d['deal_date']} {d['deal_time']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
            # print(dt)

            orderid: str = d["entrust_no"]
            trade: TradeData = TradeData(
                orderid=orderid,
                tradeid=d["deal_no"],
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[str(d["market_no"])],
                direction=DIRECTION_UF2VT[str(d["entrust_direction"])],
                price=float(d["deal_price"]),
                volume=int(float(d["deal_amount"])),
                datetime=dt,
                gateway_name=self.gateway_name
            )
            # 过滤重复的成交推送
            if trade.tradeid in self.tradeids:
                continue
            self.tradeids.add(trade.tradeid)

            self.gateway.on_trade(trade)
            position_str = d["position_str"]
            account_code = d["account_code"]
            asset_no = d["asset_no"]
        if len(data) <1000:
            self.gateway.write_log("成交信息查询成功")
        else:
            self.query_trade(self,account_code,asset_no,33004, position_str)
    def on_query_option_contract(self, data, reqid: int) -> None: # 期权合约查询
        """合约查询回报"""
        if self.check_error(data):
            self.gateway.write_log("合约信息查询失败")
            return
        # print (data)
        current_date = datetime.now()
        exc=0
        for d in data[1:]:
            exc=EXCHANGE_UF2VT[d['market_no']]
            position_str = d["position_str"]
            marketno=d["market_no"]
            if datetime.strptime(str(d["last_trade_date"]), "%Y%m%d")<current_date:
                continue 

            product=Product.OPTION
            # product=Product.OPTION
            contract= ContractData(
                symbol=str(d["stock_code"]),
                exchange=EXCHANGE_UF2VT[d['market_no']],
                name=d["stock_name"],
                size=1,
                pricetick=float(d["price_interval"]),
                product=product,
                min_volume=float(d["multiple"]),
                pre_close=float(d["pre_settle_price"]),
                gateway_name=self.gateway_name
            )            
            if contract.product == Product.OPTION:
                if d["option_type"]=='C':
                    contract.option_type =  OptionType.CALL
                else:
                    contract.option_type =OptionType.PUT
                #print(d)
                contract.option_strike = float(d["exercise_price"])
                contract.option_expiry = datetime.strptime(str(d["exercise_date"]), "%Y%m%d")

                # ETF期权
                if contract.exchange in {Exchange.SSE, Exchange.SZSE}:
                    contract.option_underlying =str(d["target_stock_code"])+'-'+str(d["exercise_date"])[:-2]
                    contract.option_portfolio =str( d['target_stock_code'])+'_O'

                    # 需要考虑标的分红导致的行权价调整后的索引
                    contract.option_index =d["optcontract_id"][-6:]#get_option_index(contract.option_strike, d["optcontract_id"])# str(contract.option_strike)#d["optcontract_id"][-5:] #
                # 期货期权
                else:
                    #print(d)
                    contract.option_underlying =d["stock_code"][:6]

                    # 移除郑商所期权产品名称带有的C/P后缀
                    if contract.exchange == Exchange.CZCE:
                        contract.option_portfolio = d["optcontract_id"][:-1]
                    else:
                        contract.option_portfolio = d["optcontract_id"]

                    # 直接使用行权价作为索引
                    contract.option_index =str(contract.option_strike)
            self.gateway.on_contract(contract)
            symbol_contract_map[contract.symbol] = contract
            
        
        if len(data) < 1000:
            self.gateway.write_log(f"{EXCHANGE_UF2VT[marketno].value}，{Product.OPTION.value}合约信息查询成功")
        else:
            self.query_stock_future_option_bond_contracts('',marketno,30012,position_str)
            # elif f_type == 'P' and contract.exchange == Exchange.SSE:
            #     self.query_sse_put_option_contracts(position_str)  
    def on_query_contract(self, data, reqid: int) -> None:  # 合约信息查询
        """合约查询回报"""
        if self.check_error(data):
            self.gateway.write_log("合约信息查询失败")
            return
        # print (data)
        for d in data[1:]:
            if d['stock_type'] in STOCK_TYPE_UF2VT.keys():
                product = STOCK_TYPE_UF2VT[d['stock_type']]
            else:
                product=Product.FUTURES
            # product=Product.OPTION
            contract= ContractData(
                symbol=str(d["stock_code"]),
                exchange=EXCHANGE_UF2VT[d['market_no']],
                name=d["stock_name"],
                size=1,
                pricetick=float(d["price_interval"]),
                product=product,
                min_volume=float(d["buy_unit"]),
                pre_close=float(d["yesterday_close_price"]),
                high_limited=float(d['uplimited_price']),
                low_limited=float(d['downlimited_price']),
                gateway_name=self.gateway_name
            )            
            self.gateway.on_contract(contract)
            if contract.product==Product.INDEX:
                symbol_contract_index_map[contract.symbol] = contract
            else:
                symbol_contract_map[contract.symbol] = contract

            position_str = d["position_str"]
            f_type=d["stock_type"]
            marketno=d["market_no"]

        if len(data) < 1000:
            self.gateway.write_log(f"{contract.exchange.value}，{contract.product.value}合约信息查询成功")
            if contract.exchange==Exchange.SSE:
                for i in symbol_contract_map.values():
                    if i.exchange==Exchange.SSE:
                        self.gateway.subscribe(SubscribeRequest(i.symbol,i.exchange))
        else:
            self.query_stock_future_option_bond_contracts(f_type,marketno,30011,position_str) 
    def on_query_future(self, data, reqid: int) -> None: # 期货查询
        """期货查询"""
        if self.check_error(data):
            self.gateway.write_log("期货信息查询失败")
            return
        # print (data)
        for d in data[1:]:
            product=Product.FUTURES
            
            contract= ContractData(
                symbol=str(d["stock_code"]),
                exchange=EXCHANGE_UF2VT[d['market_no']],
                name=d["stock_name"],
                size=1,
                pricetick=float(d["price_interval"]),
                product=product,
                min_volume=float(1.0),
                high_limited=float(d['uplimited_price']),
                low_limited=float(d['downlimited_price']),
                gateway_name=self.gateway_name
            )
            self.gateway.on_contract(contract)
            symbol_contract_map[contract.symbol] = contract
            position_str = d["position_str"]
            marketno=d["market_no"]

        if len(data) < 1000:
            self.gateway.write_log(f"{contract.exchange.value}，{contract.product.value}合约信息查询成功")

        else:
            self.query_stock_future_option_bond_contracts('',marketno,30010,position_str)
    def on_query_order(self, data, reqid: int) -> None: 
        """委托查询回报"""
        if self.check_error(data):
            self.gateway.write_log("委托信息查询失败")
            return
        for d in data[1:]:
            timestamp: str = f"{d['entrust_date']} {d['entrust_time']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
            # dt: datetime = dt.replace(tzinfo=CHINA_TZ)
            # if 'entrust_direction' in d.
            orderid: str = d["entrust_no"]
            order: OrderData = OrderData(
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[d["market_no"]],
                orderid=orderid,
                type=OrderType.LIMIT,
                direction=DIRECTION_UF2VT[d["entrust_direction"]],
                # offset=OFFSET_UF2VT[],
                price=float(d["entrust_price"]),
                volume=int(float(d["entrust_amount"])),
                traded=float(d["deal_amount"]),
                reference="",
                datetime=dt,
                gateway_name="UF",
            )
            order.status=STATUS_UF2VT[d['entrust_state']]

            # 过滤重复的成交推送
            if order.vt_symbol[:3] in ['600', '688', '000', '300','002','601','603']:
                self.equity_count+=1
            self.orders[orderid] = order

            self.batch_no_orderid[orderid]=d['batch_no']
            self.gateway.on_order(order) # 显示订单
            position_str = d["position_str"]
            account_code = d["account_code"]
            asset_no = d["asset_no"]

        if len(data) <1000:
            self.gateway.write_log("委托信息查询成功")
        else:
            self.query_order(self,account_code,asset_no,32001, position_str)
    def on_query_future_order(self, data, reqid: int) -> None: 
        """委托查询回报"""
        if self.check_error(data):
            self.gateway.write_log("委托信息查询失败")
            return
        # print(data)
        for d in data[1:]:
            timestamp: str = f"{d['entrust_date']} {d['entrust_time']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
            # dt: datetime = dt.replace(tzinfo=CHINA_TZ)
            # if 'entrust_direction' in d.
            orderid: str = d["entrust_no"]
            order: OrderData = OrderData(
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[d["market_no"]],
                orderid=orderid,
                type=OrderType.LIMIT,
                direction=DIRECTION_UF2VT[d["entrust_direction"]],
                offset=OFFSET_UF2VT[d["futures_direction"]],
                price=float(d["entrust_price"]),
                volume=int(float(d["entrust_amount"])),
                reference="",
                datetime=dt,
                gateway_name="UF",
            )
            order.status=STATUS_UF2VT[d['entrust_state']]

            # 过滤重复的成交推送
            self.orders[orderid] = order
            self.batch_no_orderid[orderid]=d['batch_no']
            self.gateway.on_order(order)
            position_str = d["position_str"]
            account_code = d["account_code"]
            asset_no = d["asset_no"]

        if len(data) <1000:
            self.gateway.write_log("委托信息查询成功")
        else:
            self.query_order(self,account_code,asset_no,32003, position_str)
    def on_query_option_order(self, data, reqid: int) -> None:
        """委托查询回报"""
        if self.check_error(data):
            self.gateway.write_log("委托信息查询失败")
            return
        # print(data)
        for d in data[1:]:
            timestamp: str = f"{d['entrust_date']} {d['entrust_time']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
            # dt: datetime = dt.replace(tzinfo=CHINA_TZ)
            # if 'entrust_direction' in d.
            orderid: str = d["entrust_no"]
            order: OrderData = OrderData(
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[d["market_no"]],
                orderid=orderid,
                type=OrderType.LIMIT,
                direction=DIRECTION_UF2VT[d["entrust_direction"]],
                offset=OFFSET_UF2VT[d["futures_direction"]],
                price=float(d["entrust_price"]),
                volume=int(float(d["entrust_amount"])),
                reference="",
                datetime=dt,
                gateway_name="UF",
            )
            order.status=STATUS_UF2VT[d['entrust_state']]

            # 过滤重复的成交推送
            self.orders[orderid] = order
            self.batch_no_orderid[orderid]=d['batch_no']
            self.gateway.on_order(order)
            position_str = d["position_str"]
            account_code = d["account_code"]
            asset_no = d["asset_no"]

        if len(data) <1000:
            self.gateway.write_log("委托信息查询成功")
        else:
            self.query_order(self,account_code,asset_no,32004, position_str)
    def on_query_position(self, data: List[Dict[str, str]], reqid: int) -> None:
        """持仓查询回报"""
        if self.check_error(data):
            self.gateway.write_log("持仓信息查询失败")
            return

        for d in data[1:]:
            if d['position_flag'] == '1':
                direct = Direction.LONG
            elif d['position_flag'] == '2':
                direct = Direction.SHORT
            else:
                direct = Direction.NET
            if float(d["current_amount"])==0:
                price=0
            else:
                price=float(d["current_cost"])/float(d["current_amount"])
            key=d["stock_code"]+d["market_no"]
            position: PositionData = PositionData(
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[d["market_no"]],
                direction=direct,
                volume=int(float(d["current_amount"])),
                price=price,
                frozen=int(float(d["current_amount"])-float(d["enable_amount"])),
                yd_volume=int(float(d["enable_amount"])),
                pnl=float(d["accumulate_profit"]),
                gateway_name=self.gateway_name
            )
            self.eqpositions[key] = position
            position_str = d["position_str"]
            acc = d["account_code"]
            ass = d["asset_no"]
        if len(data) <=10001:
            #self.gateway.write_log("证券持倉信息查询成功")
            for position in self.eqpositions.values():
                self.gateway.on_position(position)
            #self.eqpositions.clear()
        else:
            self.query_position(acc,ass,31001,position_str)   
    def on_query_future_position(self, data: List[Dict[str, str]], reqid: int) -> None:
        """持仓查询回报"""
        # print(data)
        if self.check_error(data):
            self.gateway.write_log("持仓信息查询失败")
            return
        # self.gateway.write_log("持仓信息查询")
        for d in data[1:]:
            
            key=d["stock_code"]+d["market_no"]+d['position_flag']
            if d['position_flag'] == '1':
                direct = Direction.LONG
            elif d['position_flag'] == '2':
                direct = Direction.SHORT
            else:
                direct = Direction.NET
            if float(d["current_amount"])==0:
                price=0
            else:
                price=float(d["current_cost"])/float(d["current_amount"])
            position: PositionData = PositionData(
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[d["market_no"]],
                direction=direct,
                volume=float(d["current_amount"]),
                price=price,
                frozen=float(d["current_amount"])-float(d["enable_amount"]),
                yd_volume=float(d["lastday_amount"]),
                pnl=float(d["accumulate_profit"]),
                gateway_name=self.gateway_name
            )
            self.fupositions[key] = position
            # self.gateway.on_position(position)
            position_str = d["position_str"]
            acc = d["account_code"]
            ass = d["asset_no"]
        if len(data) <=10001:
            #self.gateway.write_log("期货持倉信息查询成功")
            for position in self.fupositions.values():
                self.gateway.on_position(position)
            #self.fupositions.clear()
        else:
            self.query_position(acc,ass,31003,position_str)
    def on_query_option_position(self, data: List[Dict[str, str]], reqid: int) -> None:
        """持仓查询回报"""
        # print(data)
        if self.check_error(data):
            self.gateway.write_log("持仓信息查询失败")
            return
        # self.gateway.write_log("持仓信息查询")
        for d in data[1:]:
            
            key=d["stock_code"]+d["market_no"]+d['position_flag']
            if d['position_flag'] == '1':
                direct = Direction.LONG
            elif d['position_flag'] == '2':
                direct = Direction.SHORT
            else:
                direct = Direction.NET
            if float(d["current_amount"])==0:
                price=0
            else:
                price=float(d["current_cost"])/float(d["current_amount"])
            position: PositionData = PositionData(
                symbol=d["stock_code"],
                exchange=EXCHANGE_UF2VT[d["market_no"]],
                direction=direct,
                volume=float(d["current_amount"]),
                price=price,
                frozen=float(d["current_amount"])-float(d["enable_amount"]),
                yd_volume=float(d["lastday_amount"]),
                pnl=float(d["accumulate_profit"]),
                gateway_name=self.gateway_name
            )
            self.fupositions[key] = position
            # self.gateway.on_position(position)
            position_str = d["position_str"]
            acc = d["account_code"]
            ass = d["asset_no"]
        if len(data) <=10001:
            #self.gateway.write_log("期货持倉信息查询成功")
            for position in self.fupositions.values():
                self.gateway.on_position(position)
            #self.fupositions.clear()
        else:
            self.query_position(acc,ass,31004,position_str)
    # 委托下单回报的第一个响应包，在这个函数里处理
    def on_send_order(self, data: List[Dict[str, str]], reqid: int) -> None:#91090
        """委托下单回报"""
        orderid: str = self.reqid_orderid_map[reqid]
        print("11111",data)
        order: OrderData = self.orders[orderid]

        if orderid[0] == '#':
            if self.check_error(data):
                self.gateway.write_log(f"{order.symbol}无法通过事前风控！")

                # 将失败委托标识为拒单
                self.batch_no_orderid[orderid]='0'
                order.datetime=datetime.now()
                order.status = Status.REJECTED
                self.orders[orderid] = order
                self.gateway.on_order(order)
                if orderid in self.batch_order_id:
                    for order11 in self.combi_orderlist[orderid].values():
                        order: OrderData = self.orders[order11]
                        order.datetime=datetime.now()
                        order.status = Status.REJECTED
                        self.orders[order11] = order
                        self.gateway.on_order(order)
                else:
                    for d in data[1:]:
                        s=d['entrust_no']
                        self.gateway.write_log(f"{s}委托失败原因{d['fail_cause']}, 无法通过事前风控！")


                # self.cancel_order(CancelRequest(orderid,order.symbol,order.exchange))
        

            else:
                self.gateway.write_log(f"风险测试通过{order.symbol}")

                

                self.cancel_order(CancelRequest(orderid,order.symbol,order.exchange))
                # if orderid in self.batch_order_id:
                #     # self.gateway.write_log(f"组合下单成功{order.symbol}")
                #     self.gateway.write_log(f"风险测试成功{order.symbol}")
                #     order.datetime=datetime.now()
                #     order.status = Status.NOTTRADED
                #     self.orders[orderid]=order
                #     self.gateway.on_order(order)
                # for d in data[1:]:
                #     s=d['entrust_no']
                #     self.gateway.write_log(f"{s}委托成功{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
                    
                #     self.localid_sysid_map[orderid] = d["entrust_no"]
                #     self.sysid_localid_map[d["entrust_no"]] = orderid
        else:
            if self.check_error(data):
                self.gateway.write_log(f"{orderid}委托失败")

                # 将失败委托标识为拒单
                self.batch_no_orderid[orderid]='0'
                order.datetime=datetime.now()
                order.status = Status.REJECTED
                self.orders[orderid] = order
                self.gateway.on_order(order)
                if orderid in self.batch_order_id:
                    for order11 in self.combi_orderlist[orderid].values():
                        order: OrderData = self.orders[order11]
                        order.datetime=datetime.now()
                        order.status = Status.REJECTED
                        self.orders[order11] = order
                        self.gateway.on_order(order)
                else:
                    for d in data[1:]:
                        s=d['entrust_no']
                        self.gateway.write_log(f"{s}委托失败原因{d['fail_cause']}")
        

            else:
                if orderid in self.batch_order_id:
                    self.gateway.write_log(f"组合下单成功{order.symbol}")
                    order.datetime=datetime.now()
                    order.status = Status.NOTTRADED
                    self.orders[orderid]=order
                    self.gateway.on_order(order)
                for d in data[1:]:
                    s=d['entrust_no']
                    self.gateway.write_log(f"{s}委托成功{order.symbol},{order.offset.value}{order.direction.value},价格：{str(order.price)}")
                    
                    self.localid_sysid_map[orderid] = d["entrust_no"]
                    self.sysid_localid_map[d["entrust_no"]] = orderid
    
    def on_cancel_order(self, data: List[Dict[str, str]], reqid: int) -> None:# 撤单

        if self.check_error(data):
            self.gateway.write_log("撤单委托失败")
            return
        print(self.reqid_orderid_map)
        if reqid in self.reqid_orderid_map.keys():
            orderid: str = self.reqid_orderid_map[reqid]
        else:
            orderid= data[1]['entrust_no']
        print(reqid,orderid,data)
        if "原委托的状态不能撤单(原委托状态:[已撤])" in data[1]['fail_cause'] or '对应的委托不存在或者委托状态不支持撤单' in data[1]['fail_cause']:
            order: OrderData = self.orders[orderid]
            order.status = Status.CANCELLED
            self.orders[orderid] = order
            self.gateway.on_order(order)
        if "批量撤单完成" in data[0]['ErrorMsg']:
# self.orders[req.orderid]
            order: OrderData = self.orders[orderid]
            order.status = Status.CANCELLED
            self.orders[orderid] = order
            self.gateway.on_order(order)
    def login(self) -> int:
        """登录"""
        def GetLoginPack():
            pLoginPack = py_t2sdk.pyIF2Packer()
            pLoginPack.BeginPack()
            pLoginPack.AddField('operator_no', 'S', 16, 0)
            pLoginPack.AddField('password', 'S', 32, 0)
            pLoginPack.AddField('mac_address', 'S', 255, 0)
            pLoginPack.AddField('op_station', 'S', 255, 0)
            pLoginPack.AddField('ip_address', 'S', 36, 0)
            pLoginPack.AddField('authorization_id', 'S', 64, 0)
            pLoginPack.AddStr(self.account)
            pLoginPack.AddStr(self.password)
            pLoginPack.AddStr("2222")
            pLoginPack.AddStr('484D7EC0E5FF')
            pLoginPack.AddStr('1')
            pLoginPack.AddStr('10.45.138.37')
            pLoginPack.AddStr('1')
            pLoginPack.EndPack()
            return pLoginPack

        # print('login in...')
        pLoginPack = GetLoginPack()
        pMsg = getBizMsg(pLoginPack, 10001, 0)
        pLoginPack.FreeMem()
        pLoginPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        pMsg.Release()
        # hs_req = self.generate_req()
        # hs_req["password"] = "1q1q1q"
        # hs_req["password_type"] = "2"
        # hs_req["input_content"] = "1"
        # hs_req["account_content"] = self.account
        # hs_req["content_type"] = "0"
        # hs_req["branch_no"] = self.branch_no
        # self.send_req(FUNCTION_USER_LOGIN, hs_req)
    def on_async_callback(self, function: int, data: dict, reqid: int) -> None:
        """异步回调推送"""
        func = self.callbacks[function]
        # print(func)
        if func:
            # self.gateway.write_log(f"找到对应的异步回调函数，函数编号{function}")
            func(data, reqid)
        else:
            self.gateway.write_log(f"找不到对应的异步回调函数，函数编号{function}")
    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        ret: int = self.connection.Create2BizMsg(self.callback)
        if ret != 0:
            msg: str = self.connection.GetErrorMsg(ret)
            self.gateway.write_log(f"委托失败，错误码{ret}，错误信息{msg}")
            return ""

        if req.exchange not in EXCHANGE_VT2UF or exchange_market_is_ex[req.exchange]==0:
            self.gateway.write_log(f"委托失败，不支持的交易所{req.exchange.value}")
            return ""
        

        if req.type not in ORDERTYPE_VT2UF:
            self.gateway.write_log(f"委托失败，不支持的委托类型{req.type.value}")
            return ""

        # 发送委托
        self.order_count += 1
        reference: str = str(self.order_count).rjust(6, "0")
        orderid: str = "_".join([self.session_no, reference])
        pLoginPack = py_t2sdk.pyIF2Packer()
        pLoginPack.BeginPack()
        pLoginPack.AddField('user_token', 'S', 512, 0)
        pLoginPack.AddField('account_code', 'S', 32, 0)
        pLoginPack.AddField('asset_no', 'S', 32, 0)
        pLoginPack.AddField('combi_no', 'S', 32, 0)
        pLoginPack.AddField('market_no', 'S', 3, 0)
        pLoginPack.AddField('stock_code', 'S', 20, 0)
        pLoginPack.AddField('entrust_direction', 'S', 4, 0)
        pLoginPack.AddField('futures_direction', 'S', 1, 0)
        pLoginPack.AddField('price_type', 'S', 1, 0)
        pLoginPack.AddField('entrust_price', 'F', 11, 4)
        pLoginPack.AddField('entrust_amount', 'F', 12, 0)
        pLoginPack.AddField('extsystem_id', 'I', 12, 0)
        # [['000016', '2', '1', 100, '0', 4.6, '', 'D40003', '40003']]1
        if req.direction==Direction.LONG:
            direction='1'
        elif req.direction==Direction.SHORT:
            direction='2'
        else:
            direction='1'
        
        if req.offset == Offset.OPEN:
            offset='1'
        elif req.offset==Offset.CLOSE:
            offset='2'
        else:
            offset=''
        if symbol_contract_map[req.symbol].product==Product.EQUITY:
            # if req.offset==Offset.CLOSE and req.direction==Direction.LONG:
            #     req.direction=Direction.SHORT
            # if req.offset==Offset.CLOSE and req.direction==Direction.SHORT:
            #     req.direction=Direction.LONG
            offset=''
        if req.asset==None:
            if symbol_contract_map[req.symbol].product==Product.FUTURES:
                asset=[self.account_code2,self.combi_no2]
            else:
                asset=[self.account_code,self.combi_no]
        else:
            asset=req.asset
        order_list = [[req.symbol, EXCHANGE_VT2UF[req.exchange],direction,int(req.volume), '0', float(req.price),offset,asset[0],asset[1], self.order_count]]
        for i_order in order_list:
            pLoginPack.AddStr(self.user_token)
            # 产品代码
            pLoginPack.AddStr(i_order[7])
            # 资产单元
            pLoginPack.AddStr('')
            # 组合编号
            pLoginPack.AddStr(i_order[8])
            # 交易市场 1上交所、2深交所、3上期所、4郑商所、5银行间、6场外、7中金所、9大商所、k能源期货交易所
            pLoginPack.AddStr(i_order[1])
            # 股票代码，不需要市场后缀
            pLoginPack.AddStr(i_order[0])
            #交易方向 1买入、2卖出、3债券买入、4债券卖出、5融资正回购、6融券逆回购、9配股配债认购、10债转股、债回售
            pLoginPack.AddStr(i_order[2])
            #期货方向 1开仓 0平仓 可以’‘？
            pLoginPack.AddStr(i_order[6])
            #价格类型 0限价、其他看表
            pLoginPack.AddStr(i_order[4])
            # 价格
            pLoginPack.AddDouble(i_order[5])
            # 数量
            pLoginPack.AddDouble(i_order[3])
            
            pLoginPack.AddInt(i_order[9])

        pLoginPack.EndPack()

        #股票普通买卖对应的功能号是91001
        pMsg = getBizMsg(pLoginPack, 91090, 0)
        pLoginPack.FreeMem()
        pLoginPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        if ret< 0: 
            self.gateway.write_log(f"委托鏈接失败{ self.connection.GetErrorMsg(ret)}")
        # self.gateway.write_log(f"委托失败，不支持的委托类型{req.type.value}")
        # print(ret)
        # print(orderid)
        
        self.ex_orderid[self.order_count]=orderid
        self.orderid_ex[orderid]=self.order_count
        self.reqid_orderid_map[ret] = orderid
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        self.orders[orderid] = order
        # self.batch_no_orderid[orderid]='0'
        self.gateway.on_order(order)

        return order.vt_orderid
    def send_risk_test(self, req: OrderRequest) -> str:
        """委托下单"""
        ret: int = self.connection.Create2BizMsg(self.callback)
        if ret != 0:
            msg: str = self.connection.GetErrorMsg(ret)
            self.gateway.write_log(f"委托失败，错误码{ret}，错误信息{msg}")
            return ""

        if req.exchange not in EXCHANGE_VT2UF or exchange_market_is_ex[req.exchange]==0:
            self.gateway.write_log(f"委托失败，不支持的交易所{req.exchange.value}")
            return ""
        

        if req.type not in ORDERTYPE_VT2UF:
            self.gateway.write_log(f"委托失败，不支持的委托类型{req.type.value}")
            return ""



        # 发送委托
        self.order_count += 1
        reference: str = str(self.order_count).rjust(6, "0")
        orderid: str = "#".join([self.session_no, reference]) # 以#开头的订单编号代表test_risk
        pLoginPack = py_t2sdk.pyIF2Packer()
        pLoginPack.BeginPack()
        pLoginPack.AddField('user_token', 'S', 512, 0)
        pLoginPack.AddField('account_code', 'S', 32, 0)
        pLoginPack.AddField('asset_no', 'S', 32, 0)
        pLoginPack.AddField('combi_no', 'S', 32, 0)
        pLoginPack.AddField('market_no', 'S', 3, 0)
        pLoginPack.AddField('stock_code', 'S', 20, 0)
        pLoginPack.AddField('entrust_direction', 'S', 4, 0)
        pLoginPack.AddField('futures_direction', 'S', 1, 0)
        pLoginPack.AddField('price_type', 'S', 1, 0)
        pLoginPack.AddField('entrust_price', 'F', 11, 4)
        pLoginPack.AddField('entrust_amount', 'F', 12, 0)
        pLoginPack.AddField('extsystem_id', 'I', 12, 0)
        # [['000016', '2', '1', 100, '0', 4.6, '', 'D40003', '40003']]1
        if req.direction==Direction.LONG:
            direction='1'
        elif req.direction==Direction.SHORT:
            direction='2'
        else:
            direction='1'
        
        if req.offset == Offset.OPEN:
            offset='1'
        elif req.offset==Offset.CLOSE:
            offset='2'
        else:
            offset=''
        if symbol_contract_map[req.symbol].product==Product.EQUITY:
            # if req.offset==Offset.CLOSE and req.direction==Direction.LONG:
            #     req.direction=Direction.SHORT
            # if req.offset==Offset.CLOSE and req.direction==Direction.SHORT:
            #     req.direction=Direction.LONG
            offset=''
        if req.asset==None:
            if symbol_contract_map[req.symbol].product==Product.FUTURES:
                asset=[self.account_code2,self.combi_no2]
            else:
                asset=[self.account_code,self.combi_no]
        else:
            asset=req.asset

        # print(symbol_contract_map[req.symbol].high_limited)# = contract
        # print(symbol_contract_map[req.symbol].low_limited)# = contract

        # print (symbol_contract_map[req.symbol])
        
        if req.direction == Direction.LONG:
            _price = symbol_contract_map[req.symbol].low_limited
        else:
            _price = symbol_contract_map[req.symbol].high_limited
        #[req[i].symbol, EXCHANGE_VT2UF[req[i].exchange],direction,int(req[i].volume), '0', float(req[i].price),offset,req[i].asset[0],req[i].asset[1], self.order_count])

        order_list = [[req.symbol, EXCHANGE_VT2UF[req.exchange],direction,int(symbol_contract_map[req.symbol].min_volume), '0', float(_price),offset,asset[0],asset[1], self.order_count]]
        for i_order in order_list:
            pLoginPack.AddStr(self.user_token)
            # 产品代码
            pLoginPack.AddStr(i_order[7])
            # 资产单元
            pLoginPack.AddStr('')
            # 组合编号
            pLoginPack.AddStr(i_order[8])
            # 交易市场 1上交所、2深交所、3上期所、4郑商所、5银行间、6场外、7中金所、9大商所、k能源期货交易所
            pLoginPack.AddStr(i_order[1])
            # 股票代码，不需要市场后缀
            pLoginPack.AddStr(i_order[0])
            #交易方向 1买入、2卖出、3债券买入、4债券卖出、5融资正回购、6融券逆回购、9配股配债认购、10债转股、债回售
            pLoginPack.AddStr(i_order[2])
            #期货方向 1开仓 0平仓 可以’‘？
            pLoginPack.AddStr(i_order[6])
            #价格类型 0限价、其他看表
            pLoginPack.AddStr(i_order[4])
            # 价格
            pLoginPack.AddDouble(i_order[5])
            # 数量
            pLoginPack.AddDouble(i_order[3])
            
            pLoginPack.AddInt(i_order[9])

        pLoginPack.EndPack()

        #股票普通买卖对应的功能号是91001
        pMsg = getBizMsg(pLoginPack, 91090, 0)
        pLoginPack.FreeMem()
        pLoginPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        if ret< 0: 
            self.gateway.write_log(f"委托鏈接失败{ self.connection.GetErrorMsg(ret)}")
        # self.gateway.write_log(f"委托失败，不支持的委托类型{req.type.value}")
        # print(ret)
        # print(orderid)
        
        self.ex_orderid[self.order_count]=orderid
        self.orderid_ex[orderid]=self.order_count
        self.reqid_orderid_map[ret] = orderid
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        self.orders[orderid] = order
        # self.batch_no_orderid[orderid]='0'
        # self.gateway.on_order(order)

        return order.vt_orderid
    def send_orders(self, req:list) -> str:
        """委托下单"""
        ret: int = self.connection.Create2BizMsg(self.callback)
        if ret != 0:
            msg: str = self.connection.GetErrorMsg(ret)
            self.gateway.write_log(f"委托失败，错误码{ret}，错误信息{msg}")
            return ""

        if req[0].exchange not in EXCHANGE_VT2UF:
            self.gateway.write_log(f"委托失败，不支持的交易所{req[0].exchange.value}")
            return ""

        if req[0].type not in ORDERTYPE_VT2UF:
            self.gateway.write_log(f"委托失败，不支持的委托类型{req[0].type.value}")
            return ""

        # 发送委托
        self.order_count += 1
        reference: str = str(self.order_count).rjust(6, "0")
        orderid: str = "*".join([self.session_no, reference])
        pLoginPack = py_t2sdk.pyIF2Packer()
        pLoginPack.BeginPack()
        pLoginPack.AddField('user_token', 'S', 512, 0)
        pLoginPack.AddField('account_code', 'S', 32, 0)
        pLoginPack.AddField('asset_no', 'S', 32, 0)
        pLoginPack.AddField('combi_no', 'S', 32, 0)
        pLoginPack.AddField('market_no', 'S', 3, 0)
        pLoginPack.AddField('stock_code', 'S', 20, 0)
        pLoginPack.AddField('entrust_direction', 'S', 4, 0)
        pLoginPack.AddField('futures_direction', 'S', 1, 0)
        pLoginPack.AddField('price_type', 'S', 1, 0)
        pLoginPack.AddField('entrust_price', 'F', 11, 4)
        pLoginPack.AddField('entrust_amount', 'F', 12, 0)
        pLoginPack.AddField('extsystem_id', 'I', 12, 0)
        # [['000016', '2', '1', 100, '0', 4.6, '', 'D40003', '40003']]1
        order_list =[]
        for i in range(len(req)):
            if req[i].direction==Direction.LONG:
                direction='1'
            elif req[i].direction==Direction.SHORT:
                direction='2'
            else:
                direction='1'
            
            if req[i].offset == Offset.OPEN:
                offset='1'
            elif req[i].offset==Offset.CLOSE:
                offset='2'
            else:
                offset=''
            if symbol_contract_map[req[i].symbol].product==Product.EQUITY:
                offset=''
            order_list.append([req[i].symbol, EXCHANGE_VT2UF[req[i].exchange],direction,int(req[i].volume), '0', float(req[i].price),offset,req[i].asset[0],req[i].asset[1], self.order_count])
            if exchange_market_is_ex[req[i].exchange]==0:
                self.gateway.write_log(f"委托失败，连接断开{req[i].exchange}")
                return
        for i_order in order_list:
            pLoginPack.AddStr(self.user_token)
            # 产品代码
            pLoginPack.AddStr(i_order[7])
            # 资产单元
            pLoginPack.AddStr('')
            # 组合编号
            pLoginPack.AddStr(i_order[8])
            # 交易市场 1上交所、2深交所、3上期所、4郑商所、5银行间、6场外、7中金所、9大商所、k能源期货交易所
            pLoginPack.AddStr(i_order[1])
            # 股票代码，不需要市场后缀
            pLoginPack.AddStr(i_order[0])
            #交易方向 1买入、2卖出、3债券买入、4债券卖出、5融资正回购、6融券逆回购、9配股配债认购、10债转股、债回售
            pLoginPack.AddStr(i_order[2])
            #期货方向 1开仓 0平仓 可以’‘？
            pLoginPack.AddStr(i_order[6])
            #价格类型 0限价、其他看表
            pLoginPack.AddStr(i_order[4])
            # 价格
            pLoginPack.AddDouble(i_order[5])
            # 数量
            pLoginPack.AddDouble(i_order[3])
            
            pLoginPack.AddInt(i_order[9])

        pLoginPack.EndPack()

        #股票普通买卖对应的功能号是91001
        pMsg = getBizMsg(pLoginPack, 91090, 0)
        pLoginPack.FreeMem()
        pLoginPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        # order_count是人为定义的外部指令编号，外部指令编号和orderid互相映射
        self.ex_orderid[self.order_count]=orderid
        self.orderid_ex[orderid]=self.order_count
        self.reqid_orderid_map[ret] = orderid
        order: OrderData = OrderData(
            symbol=orderid,
            exchange= req[0].exchange,
            orderid=orderid,
            type= req[0].type,
            direction= req[0].direction,
            offset= req[0].offset,
            price= req[0].price,
            volume= len(req),
            reference= req[0].reference,
            gateway_name="UF",
            asset=req[0].asset,
        )
        self.batch_order_id.append(orderid)
        self.orders[orderid] = order
        self.gateway.on_order(order)
        vt=order.vt_orderid
        self.remain[orderid]={}
        self.combi_orderlist[orderid]={}
        for i in range(len(req)):
            self.order_count+=1
            orderid1=orderid+str("_")+str(i)
            self.combi_orderlist[orderid][req[i].symbol]=orderid1
            self.ex_orderid[self.order_count]=orderid1
            self.orderid_ex[orderid1]=self.order_count
            order: OrderData = req[i].create_order_data(orderid1, self.gateway_name)
            # self.batch_no_orderid[orderid1]=order
            if order.vt_symbol[:3] in ['600', '688', '000', '300','002','601','603']:
                self.equity_count+=1
            self.orders[orderid1] = order
            self.gateway.on_order(order)      
        return vt
    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""

        # 如果req.orderid 包含'-'就不处理

        if '*' == req.orderid[0] and '_' in req.orderid[1:]:
            return
        # 发送撤单请求
        if req.orderid not in self.batch_no_orderid.keys():
            self.gateway.write_log(f"等待返回委托号{req.orderid}")
            time.sleep(2)
            if req.orderid not in self.batch_no_orderid.keys():
                self.gateway.write_log(f"委托号未发出，或丢失委托号{req.orderid}，默认标记为拒单")
                # print("11111",data)
                order: OrderData = self.orders[req.orderid]
                # 将失败委托标识为拒单
                self.batch_no_orderid[req.orderid]='0'
                order.datetime=datetime.now()
                order.status = Status.REJECTED
                self.orders[req.orderid] = order
                self.gateway.on_order(order)
            return
        pLoginPack = py_t2sdk.pyIF2Packer()
        pLoginPack.BeginPack()
        pLoginPack.AddField('user_token', 'S', 512, 0)
        pLoginPack.AddField('batch_no', 'S', 32, 0)
        pLoginPack.AddStr(self.user_token)
        pLoginPack.AddStr(self.batch_no_orderid[req.orderid])
        pLoginPack.EndPack()
        pMsg = getBizMsg(pLoginPack, 91102, 0)
        pLoginPack.FreeMem()
        pLoginPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)

        # sysid: str = self.localid_sysid_map.get(req.orderid, "")
        # if sysid:
        self.reqid_orderid_map[ret] = req.orderid
    def query_position(self,account_code,asset_no,Msgnum, position_str: str = "") -> int:
        """查询持仓"""
        if not self.login_status:
            return
        pPack = py_t2sdk.pyIF2Packer()
        pPack.BeginPack()
        pPack.AddField('user_token', 'S', 512, 0)
        pPack.AddField('account_code', 'S', 32, 0)
        pPack.AddField('asset_no', 'S', 32, 0)
        pPack.AddField('position_str', 'S', 32, 0)
        pPack.AddStr(self.user_token)
        pPack.AddStr(account_code)
        pPack.AddStr(asset_no)
        pPack.AddStr(position_str)
        pPack.EndPack()
        # pLoginPack = GetLoginPack()
        pMsg = getBizMsg(pPack,Msgnum, 0) # 证券持仓查询
        pPack.FreeMem()
        pPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        pMsg.Release()
    def query_account(self) -> int:
        """查询资金"""
        # print("""查询资金""")
        if not self.login_status:
            #print("sss")
            return
        pPack = py_t2sdk.pyIF2Packer()
        pPack.BeginPack()
        pPack.AddField('user_token', 'S', 512, 0)
        pPack.AddField('account_code', 'S', 32, 0)
        pPack.AddField('asset_no', 'S', 32, 0)
        pPack.AddStr(self.user_token)
        pPack.AddStr(self.account_code)
        pPack.AddStr(self.asset_no)
        pPack.EndPack()
        # pLoginPack = GetLoginPack()
        pMsg = getBizMsg(pPack, 34001, 0) # 账户资金查询
        pPack.FreeMem()
        pPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        pMsg.Release()
        pPack = py_t2sdk.pyIF2Packer()
        pPack.BeginPack()
        pPack.AddField('user_token', 'S', 512, 0)
        pPack.AddField('account_code', 'S', 32, 0)
        pPack.AddField('asset_no', 'S', 32, 0)
        pPack.AddStr(self.user_token)
        pPack.AddStr(self.account_code2)
        pPack.AddStr(self.asset_no2)
        pPack.EndPack()
        # pLoginPack = GetLoginPack()
        pMsg = getBizMsg(pPack, 34001, 0)
        pPack.FreeMem()
        pPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        pMsg.Release()
    def query_trade(self,account_code,asset_no,Msgnum, position_str: str = "") -> int:
        """查询持仓"""
        if not self.login_status:
            return
        pPack = py_t2sdk.pyIF2Packer()
        pPack.BeginPack()
        pPack.AddField('user_token', 'S', 512, 0)
        pPack.AddField('account_code', 'S', 32, 0)
        pPack.AddField('asset_no', 'S', 32, 0)
        pPack.AddField('position_str', 'S', 32, 0)
        pPack.AddStr(self.user_token)
        pPack.AddStr(account_code)
        pPack.AddStr(asset_no)
        pPack.AddStr(position_str)
        pPack.EndPack()
        # pLoginPack = GetLoginPack()
        pMsg = getBizMsg(pPack,Msgnum, 0) # 证券持仓查询
        pPack.FreeMem()
        pPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        pMsg.Release()
    def query_order(self,account_code,asset_no,Msgnum, position_str: str = "") -> int: # 委托查询
        """查询持仓"""
        if not self.login_status:
            return
        pPack = py_t2sdk.pyIF2Packer()
        pPack.BeginPack()
        pPack.AddField('user_token', 'S', 512, 0)
        pPack.AddField('account_code', 'S', 32, 0)
        pPack.AddField('asset_no', 'S', 32, 0)
        pPack.AddField('position_str', 'S', 32, 0)
        pPack.AddStr(self.user_token)
        pPack.AddStr(account_code)
        pPack.AddStr(asset_no)
        pPack.AddStr(position_str)
        pPack.EndPack()
        # pLoginPack = GetLoginPack()
        pMsg = getBizMsg(pPack,Msgnum, 0) # 证券持仓查询
        pPack.FreeMem()
        pPack.Release()
        ret = self.connection.SendBizMsg(pMsg, 1)
        pMsg.Release()
    def query_contract(self) -> int: # 合约查询
        """查询合约"""
        self.query_stock_future_option_bond_contracts('03','7',30010)# 查询中金所的国债合约
        
        self.query_stock_future_option_bond_contracts('','7',30012) # 中金期权
        self.query_stock_future_option_bond_contracts('','1',30012) # 上交期权
        self.query_stock_future_option_bond_contracts('','2',30012) # 深交期权

        self.query_stock_future_option_bond_contracts('0w','1',30011) # 查询上交所指数合约信息
        self.query_stock_future_option_bond_contracts('05','1',30011) # 查询上交所可转债信息
        self.query_stock_future_option_bond_contracts('05','2',30011) # 查询深交可转债信息
        self.query_stock_future_option_bond_contracts('01','1',30011) # 查询上交所股票合约信息
        self.query_stock_future_option_bond_contracts('01','2',30011) # 查询深交所股票合约信息
        self.query_stock_future_option_bond_contracts('0R','7',30011) # 查询中金所期货合约信息
        # self.query_stock_future_option_bond_contracts('0v','3',30011)#查询shfe期货合约信息
        # self.query_stock_future_option_bond_contracts('0v','4',30011)#查询ine期货合约信息
        # self.query_stock_future_option_bond_contracts('0v','9',30011)#查询czce期货合约信息
        # self.query_stock_future_option_bond_contracts('0v','k',30011)#查询dce期货合约信息
    # 期权 
    def query_stock_future_option_bond_contracts(self,stock_type,market_no,msgnum,position_str: str = "") -> int:
        """查询上交所合约信息"""
        '''
         hs_req: dict = self.generate_req()
        hs_req["fund_account"] = self.account
        hs_req["password"] = self.password
        hs_req["query_type"] = 1
        hs_req["exchange_type"] = 1
        hs_req["stock_type"] = 0
        hs_req["position_str"] = position_str

        '''
        if msgnum!=30012:
            pLoginPack = py_t2sdk.pyIF2Packer()
            pLoginPack.BeginPack()
            pLoginPack.AddField('user_token', 'S', 512, 0)
            pLoginPack.AddField('stock_type', 'S', 4, 0)
            pLoginPack.AddField('market_no', 'S', 4, 0)
            
            pLoginPack.AddField('position_str', 'S', 128, 0)
            pLoginPack.AddStr(self.user_token)
            pLoginPack.AddStr(stock_type)
            pLoginPack.AddStr(market_no)
            pLoginPack.AddStr(position_str)
            pLoginPack.EndPack()

            pMsg = getBizMsg(pLoginPack, msgnum, 0)
            pLoginPack.FreeMem()
            pLoginPack.Release()
            ret = self.connection.SendBizMsg(pMsg, 1)   
        else:
            pLoginPack = py_t2sdk.pyIF2Packer()
            pLoginPack.BeginPack()
            pLoginPack.AddField('user_token', 'S', 512, 0)
            # pLoginPack.AddField('option_type', 'S', 4, 0)
            pLoginPack.AddField('market_no', 'S', 4, 0)
            pLoginPack.AddField('position_str', 'S', 128, 0)
            pLoginPack.AddStr(self.user_token)
            # pLoginPack.AddStr('C')
            pLoginPack.AddStr(market_no)
            pLoginPack.AddStr(position_str)
            pLoginPack.EndPack()
            pMsg = getBizMsg(pLoginPack, msgnum,0)
            pLoginPack.FreeMem()
            pLoginPack.Release()
            ret = self.connection.SendBizMsg(pMsg, 1)
class TdAsyncCallback:
    """异步请求回调类"""

    def __init__(self) -> None:
        """构造函数"""
        global td_api
        self.td_api: TdApi = td_api

    def OnRegister(self) -> None:
        """完成注册回报"""
        pass

    def OnClose(self) -> None:
        """断开连接回报"""
        pass

    def OnReceivedBizMsg(self, hSend, sBuff, iLen) -> None:
        """异步数据推送"""
        biz_msg = py_t2sdk.pyIBizMessage()
        biz_msg.SetBuff(sBuff, iLen)

        function: int = biz_msg.GetFunction()
        # 维护心跳
        if function == 10000:
            biz_msg.ChangeReq2AnsMessage()
            self.td_api.connection.SendBizMsg(biz_msg, 1)
            #print('========================收到应答包，功能号%d========================' % function)
        else:     
            buf, length = biz_msg.GetContent()
            responseUnPack = py_t2sdk.pyIF2UnPacker()
            responseUnPack.Open(buf, length)
            iFuncId = biz_msg.GetFunction()
            #print('========================收到应答包，功能号%d========================' % iFuncId)
            data= unpack_data(responseUnPack)
            # print(data)
            self.td_api.on_async_callback(function, data, hSend)

            responseUnPack.Release()

        biz_msg.Release()

def PrintUnpack(lpUnpack):
    iDataSetCount = lpUnpack.GetDatasetCount()
    index = 0
    result=[]
    while index < iDataSetCount:
        lpUnpack.SetCurrentDatasetByIndex(index)
        iRowCount = lpUnpack.GetRowCount()
        RowIndex = 0
        while RowIndex < iRowCount:
            iColCount = lpUnpack.GetColCount()
            iColIndex = 0
            date={}
            while iColIndex < iColCount:
                ColType = lpUnpack.GetColType(iColIndex)
                if ColType == 'S':
                    date[lpUnpack.GetColName(iColIndex)]=lpUnpack.GetStrByIndex(iColIndex)
                elif ColType == 'I':
                    date[lpUnpack.GetColName(iColIndex)]= str(lpUnpack.GetIntByIndex(iColIndex))
                elif ColType == 'C':
                    date[lpUnpack.GetColName(iColIndex)]=lpUnpack.GetCharByIndex(iColIndex)
                elif ColType == 'D':
                    date[lpUnpack.GetColName(iColIndex)]=str(lpUnpack.GetDoubleByIndex(iColIndex))
                elif ColType == 'F':
                    date[lpUnpack.GetColName(iColIndex)]=str(lpUnpack.GetDoubleByIndex(iColIndex))
                iColIndex += 1
            lpUnpack.Next()
            RowIndex += 1
            result.append(date)
        index += 1
    return result

class TdsubCallback:
    def __init__(self):
        global td_api
        self.td_api: TdApi = td_api

    # 这个回调会在收到发布消息之后回调进去，上层应用在这个函数里面做业务处理。
    # 回调参数里面，还支持当前消息属于哪个订阅，以及过滤条件是什么，附加数据是什么，是什么主题等信息，都返回给了上层函数实现者。
    def OnReceived(self, topic, sBuff, iLen):
        print('========================111111收到应答消息，主题%s========================' % topic)
        lpBizMsg = py_t2sdk.pyIBizMessage()
        iRet = lpBizMsg.SetBuff(sBuff, iLen)
        buf, len = lpBizMsg.GetContent()
        LoginUnPack = py_t2sdk.pyIF2UnPacker()
        LoginUnPack.Open(buf, len)
        result=PrintUnpack(LoginUnPack)
        
        # storeUnpack(LoginUnPack)
        # print(result)
        self.td_api.on_async_callback(99999, result, result[0]['extsystem_id'])
        buf, len = lpBizMsg.GetKeyInfo()
        LoginUnPack.Open(buf, len)


        print ("*************************************")
        PrintUnpack(LoginUnPack)
        
        print ("*************************************")
        LoginUnPack.Release()

def unpack_data(lpUnpack: py_t2sdk.pyIF2UnPacker) -> List[Dict[str, str]]:

    result=[]
    iDataSetCount = lpUnpack.GetDatasetCount()
    index = 0
    while index < iDataSetCount:
        date2=[]
        lpUnpack.SetCurrentDatasetByIndex(index)
        iRowCount = lpUnpack.GetRowCount()
        RowIndex = 0
        while RowIndex < iRowCount:
            iColCount = lpUnpack.GetColCount()
            iColIndex = 0
            date={}
            while iColIndex < iColCount:
                ColType = lpUnpack.GetColType(iColIndex)
                if ColType == 'S':
                    date[lpUnpack.GetColName(iColIndex)]=lpUnpack.GetStrByIndex(iColIndex)
                elif ColType == 'I':
                    date[lpUnpack.GetColName(iColIndex)]= str(lpUnpack.GetIntByIndex(iColIndex))
                elif ColType == 'C':
                    date[lpUnpack.GetColName(iColIndex)]=lpUnpack.GetCharByIndex(iColIndex)
                elif ColType == 'D':
                    date[lpUnpack.GetColName(iColIndex)]=str(lpUnpack.GetDoubleByIndex(iColIndex))
                elif ColType == 'F':
                    date[lpUnpack.GetColName(iColIndex)]=str(lpUnpack.GetDoubleByIndex(iColIndex))
                iColIndex += 1
            result.append(date)
            lpUnpack.Next()
            RowIndex += 1
        # result.append(date2)
        index += 1
    return result
def generate_datetime(timestamp: str) -> datetime:
    """生成时间戳"""
    dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
    dt: datetime = CHINA_TZ.localize(dt)
    return dt
def generate_datetime2(timestamp: str) -> datetime:
    """生成时间戳"""
    dt: datetime = datetime.strptime(timestamp, "%Y%m%d%H%M%S%f")
    dt: datetime = CHINA_TZ.localize(dt)
    return dt
def process_data(data: str) -> float:
    """处理空字符"""
    if data == "":
        d = 0
    else:
        d = float(data)
    return d
# TD API全局对象（用于在回调类中访问）
td_api = None
def adjust_price(price: float) -> float:

    """将异常的浮点数最大值（MAX_FLOAT）数据调整为0"""
    if price > 100000:
        price = 0
    else:
        price=round(price,4)
    return price
def get_option_index(strike_price: float, exchange_instrument_id: str) -> str:
    """获取期权索引"""
    exchange_instrument_id: str = exchange_instrument_id.replace(" ", "")

    if "M" in exchange_instrument_id:
        n: int = exchange_instrument_id.index("M")
    elif "A" in exchange_instrument_id:
        n: int = exchange_instrument_id.index("A")
    elif "B" in exchange_instrument_id:
        n: int = exchange_instrument_id.index("B")
    else:
        return str(strike_price)

    index: str = exchange_instrument_id[n:]
    option_index: str = f"{strike_price:.3f}-{index}"

    return option_index