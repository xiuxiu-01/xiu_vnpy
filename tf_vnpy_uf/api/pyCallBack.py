import py_t2sdk
import ufx_demo_asyn_lyh_v3 as ufx
import global_test


def PrintUnpack(lpUnpack):
    iDataSetCount = lpUnpack.GetDatasetCount()
    index = 0
    while index < iDataSetCount:
        lpUnpack.SetCurrentDatasetByIndex(index)
        iRowCount = lpUnpack.GetRowCount()
        RowIndex = 0
        while RowIndex < iRowCount:
            iColCount = lpUnpack.GetColCount()
            iColIndex = 0
            while iColIndex < iColCount:
                ColType = lpUnpack.GetColType(iColIndex)
                if ColType == 'S':
                    print(lpUnpack.GetColName(iColIndex) + ':' + lpUnpack.GetStrByIndex(iColIndex))
                elif ColType == 'I':
                    print(lpUnpack.GetColName(iColIndex) + ':' + str(lpUnpack.GetIntByIndex(iColIndex)))
                elif ColType == 'C':
                    print(lpUnpack.GetColName(iColIndex) + ':' + lpUnpack.GetCharByIndex(iColIndex))
                elif ColType == 'D':
                    print(lpUnpack.GetColName(iColIndex) + ':' + str(lpUnpack.GetDoubleByIndex(iColIndex)))
                iColIndex += 1
            lpUnpack.Next()
            RowIndex += 1
        index += 1


class pyCallBack:
    def __init__(self):
        print('init')

    def OnRegister(self):
        print('OnRegister')

    def OnClose(self):
        print('OnClose')

    def OnReceivedBizMsg(self, hSend, sBuff, iLenght):
        lpBizMsg = py_t2sdk.pyIBizMessage()
        iRet = lpBizMsg.SetBuff(sBuff, iLenght)
        iRet = lpBizMsg.GetErrorNo()
        print(iRet)
        if iRet == 0:
            ufx.handleResponse(lpBizMsg)
            # buf, len = lpBizMsg.GetContent()
            # LoginUnPack = py_t2sdk.pyIF2UnPacker()
            # LoginUnPack.Open(buf, len)
            # PrintUnpack(LoginUnPack)
            # LoginUnPack.Release()
        else:
            print(iRet)
            print(str(lpBizMsg.GetErrorInfo(), encoding="gbk"))
        lpBizMsg.Release()
