# -*- coding: utf-8 -*-
import e32
import appuifw
from random import randint
import sys
import os
import time
import XYsms
import contacts
import e32db
from inbox import Inbox
from key_codes import *
import uikludges
from db import db
import parse
from graphics import Image
import fgimage
import urllib
import httplib

#短信酷版本号
Ver = 86

#标志是模拟器还是真机(1-模拟器，0-真机)
if e32.in_emulator():
    IsEmulator = 1
else:
    IsEmulator = 0

#获取Python版本号(判断是否第二版手机)
if e32.pys60_version_info[1] == 4:
    IsTwoVer = 1
else:
    IsTwoVer = 0

#获取手机版本号(判断是否fp3手机)
if e32.s60_version_info[1] == 8:
    IsFP3 = 1
else:
    IsFP3 = 0

#数据库目录
if IsEmulator == 1:
    SMSPath = u'c:\\SMS\\'
    HelpPath = SMSPath + u'help\\'
else:
    SystemPath = appuifw.app.full_name()[0]
    SMSPath = SystemPath + u':\\SMS\\'
    HelpPath = SystemPath + u':\\System\\Apps\\SMSStore\\help\\'

#数据库名称
DBName = u'SMSData'

#配置文件名称
ConfigPathBySend = SMSPath + u'SendConfig.cfg'
ConfigPathBySystem = SMSPath + u'SystemConfig.cfg'

#名片夹中所有的姓名与电话对应的字典
Contact = {}

#名片夹中的所有姓名
Contact_Name = []

#收件箱中所有短信（不包括发件人姓名）
#Message_Content_Add = []

#收件箱中所有短信（包括发件人姓名）
Message_Content_Re = []

#用于导出的类别名称
ExportSMSTypeName = ''

#用于导入的类别ID
ImportTypeID = -1

#用于显示信息
GlobalCanvas = None
GlobalImage = None

#检测数据库目录是否存在
def CheckSMSPath():
    global SMSPath
    if not os.path.isdir(SMSPath):
        os.makedirs(SMSPath)

def U(s):
    return unicode(s)

def U8(s):
    return s.decode('utf8')

def UN8(s):
    return s.encode('utf8')

def Str2(t):
    t2 = str(t)
    if len(t2) == 1:
        t2 = "0" + t2
    return t2

def Msg(s, GlobalFlag=0):
    appuifw.note(s, 'info', GlobalFlag)

def Query(s, QueryType='query', InitialValue=None):
    return appuifw.query(s, QueryType, InitialValue)

def ViewLongInfo(title, msg):
    if title == None or title == '':
        title = ' '
    if msg == None or msg == '':
        msg = ' '
    ListMsg = msg.split(',')
    return appuifw.popup_menu(ListMsg, title)


#短信数据库操作类，用于对短信数据库增、删、改短信和类别
class SMSDataBase:
    #打开短信数据库，如果不存在则选建立短信数据库再打开
    def __init__(self):
        global SMSPath
        global DBName
        
        CheckSMSPath()
        sys.path.append(SMSPath)
        self.DBPath = SMSPath + DBName + '.db'
        self.strSql = ''
        if not os.path.isfile(self.DBPath):
            self.SMSDB = db(self.DBPath)
            self.SMSDB.query("CREATE TABLE tb_e_SMSInfo (SMSInfoID COUNTER, SMSTypeID INTEGER, SMSContent VARCHAR)")
            self.SMSDB.query("CREATE TABLE tb_e_SMSType (SMSTypeID COUNTER, SMSTypeName VARCHAR(30), SMSTypeOrder INTEGER)")
            self.SMSDB.query("CREATE TABLE tb_e_SendedNumbers (SendedID COUNTER, SendedName VARCHAR(100), SendedNumbers LONG VARCHAR, SendedOrder INTEGER)")
        else:
            self.SMSDB = db(self.DBPath)

        
    #检测短信是否存在
    def SMSIsExist(self, iSMSTypeID, strSMSContent):
        self.strSql = "SELECT SMSInfoID FROM tb_e_SMSInfo WHERE SMSTypeID=" + str(iSMSTypeID) + " AND SMSContent='" + U8(strSMSContent) + "'"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            if self.SMSRow[0] != "":
                return 1
            else:
                return 0
        else:
            return 0

    #添加短信，相同的短信不添加
    def InsertSMS(self, objSMSInfo):
        self.mySMS = objSMSInfo
        self.strFilterContent = self.mySMS.SMSContent.replace("'", "''")
        if self.SMSIsExist(self.mySMS.SMSTypeID, self.strFilterContent) == 1:
            return -101
        else:
            self.strSql = "INSERT INTO tb_e_SMSInfo (SMSTypeID,SMSContent) VALUES("+str(self.mySMS.SMSTypeID)+",'"+U8(self.strFilterContent)+"')"
            #print self.strSql
            self.SMSDB.query(self.strSql)
            return 1

    #导入短信（导入、导出时用）
    def ImportSMS(self, objSMSInfo, Mode=1, iTypeOrder=999):
        global ImportTypeID
        #print objSMSInfo.SMSContent, objSMSInfo.SMSTypeName
        self.mySMS = objSMSInfo
        self.strFilterContent = self.mySMS.SMSContent.replace("'", "''")
        if self.SMSIsExist(self.mySMS.SMSTypeID, self.strFilterContent) == 1:
            return -101

        #print Mode,ImportTypeID,U8(ExportSMSTypeName)
        if ImportTypeID == -1 or Mode == 1:
            self.SMSTypeID = self.GetCreateTypeID(U8(self.mySMS.SMSTypeName),iTypeOrder)
            ImportTypeID = self.SMSTypeID
        else:
            self.SMSTypeID = ImportTypeID
        
        self.strSql = "INSERT INTO tb_e_SMSInfo (SMSTypeID,SMSContent) VALUES("+str(self.SMSTypeID)+",'"+U8(self.strFilterContent)+"')"
        #print self.strSql
        self.SMSDB.query(self.strSql)
        return 1

    #修改短信
    def UpdateSMS(self, objSMSInfo):
        self.mySMS = objSMSInfo
        self.strFilterContent = self.mySMS.SMSContent.replace("'", "''")
        self.strSql = "UPDATE tb_e_SMSInfo SET SMSTypeID="+str(self.mySMS.SMSTypeID)+",SMSContent='"+U8(self.strFilterContent)+"' WHERE SMSInfoID="+str(self.mySMS.SMSInfoID)
        #print self.strSql
        self.SMSDB.query(self.strSql)

    #读取某个类别的短信到短信实体中（短信列表）
    def LoadSMS(self, strCondition):
        self.MySMSList = SMSList()
        self.strSql = "SELECT SMSInfoID,SMSTypeID,SMSContent FROM tb_e_SMSInfo " + strCondition + " ORDER BY SMSInfoID DESC"
        #print self.strSql
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            self.MySMSList.AppendSMS(SMSInfo(), 0)
            self.MySMSList[-1].SMSInfoID = self.SMSRow[0]
            self.MySMSList[-1].SMSTypeID = self.SMSRow[1]
            self.MySMSList[-1].SMSContent = self.SMSRow[2]

        return self.MySMSList.SMSList

    #加载全部短信（导入、导出时用）
    def LoadAllSMS(self):
        self.MySMSList = SMSList()
        self.MyTypeList = SMSTypeList()
        self.MyTypeList.LoadType()
        self.strTypeName = ''
        self.strSql = "SELECT SMSTypeID,SMSContent FROM tb_e_SMSInfo ORDER BY SMSTypeID,SMSInfoID DESC"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            self.strTypeName = self.MyTypeList.FindTypeName(self.SMSRow[0])
            self.MySMSList.AppendSMS(SMSExInfo(), 0)
            self.MySMSList[-1].SMSTypeName = self.strTypeName
            self.MySMSList[-1].SMSContent = self.SMSRow[1]

        return self.MySMSList.SMSList

    #删除一条短信
    def DeleteSMS(self, iSMSInfoID):
        self.strSql = "DELETE FROM tb_e_SMSInfo WHERE SMSInfoID=" + str(iSMSInfoID)
        self.SMSDB.query(self.strSql)


    #判断一个类别名称是否存在    
    def TypeIsExist(self, strTypeName):
        self.strSql = "SELECT SMSTypeID FROM tb_e_SMSType WHERE SMSTypeName='" + strTypeName + "'"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            if self.SMSRow[0] != "":
                return 1
            else:
                return 0
        else:
            return 0

    #获取指定名称的类别ID，如果类别不存在则建立（导入、导出时用）
    def GetCreateTypeID(self, strTypeName, iTypeOrder=999):
        self.iTypeID = 0
        self.strSql = "SELECT SMSTypeID FROM tb_e_SMSType WHERE SMSTypeName='" + strTypeName + "'"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            if self.SMSRow[0] != "":
                self.iTypeID = self.SMSRow[0]
                break
            else:
                self.InsertType(strTypeName, iTypeOrder)
                self.iTypeID = self.GetMaxTypeID()
        else:
            self.InsertType(strTypeName, iTypeOrder)
            self.iTypeID = self.GetMaxTypeID()
        return self.iTypeID

    #获取最新添加的类别ID（导入、导出时用）
    def GetMaxTypeID(self):
        self.strSql = "SELECT SMSTypeID FROM tb_e_SMSType ORDER BY SMSTypeID DESC"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            if self.SMSRow[0] != "":
                return self.SMSRow[0]
                break
            else:
                return 0
        else:
            return 0

    #添加类别    
    def InsertType(self, strTypeName, iTypeOrder=999):
        self.strFilterTypeName = strTypeName.replace("'", "''")
        if self.TypeIsExist(self.strFilterTypeName) == 1:
            return -101
        else:
            self.strSql = "INSERT INTO tb_e_SMSType (SMSTypeName,SMSTypeOrder) VALUES('"+self.strFilterTypeName+"',"+str(iTypeOrder)+")"
            self.SMSDB.query(self.strSql)
            return 1

    #修改类别
    def UpdateType(self, objSMSType):
        self.myType = objSMSType
        self.strFilterTypeName = self.myType.SMSTypeName.replace("'", "''")
        if self.TypeIsExist(self.strFilterTypeName) == 1:
            return -101
        else:
            self.strSql = "UPDATE tb_e_SMSType SET SMSTypeName='"+self.strFilterTypeName+"' WHERE SMSTypeID="+str(self.myType.SMSTypeID)
            self.SMSDB.query(self.strSql)
            return 1

    #修改类别顺序
    def ModifyOrder(self, iTypeID, iTypeOrder):
        self.strSql = "UPDATE tb_e_SMSType SET SMSTypeOrder=" + str(iTypeOrder) + " WHERE SMSTypeID=" + str(iTypeID)
        #print self.strSql
        self.SMSDB.query(self.strSql)
        
    #读取类别到类别实体中（类别列表）
    def LoadType(self):
        self.MySMSTypeList = SMSTypeList()
        self.strSql = "SELECT SMSTypeID,SMSTypeName,SMSTypeOrder FROM tb_e_SMSType ORDER BY SMSTypeOrder,SMSTypeID DESC"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            #print self.SMSRow[0],self.SMSRow[1]
            self.MySMSTypeList.AppendType(SMSTypeInfo(), 0)
            self.MySMSTypeList[-1].SMSTypeID = self.SMSRow[0]
            self.MySMSTypeList[-1].SMSTypeName = self.SMSRow[1]
            self.MySMSTypeList[-1].SMSTypeOrder = self.SMSRow[2]

        return self.MySMSTypeList.TypeList

    #删除短信类别
    def DeleteSMSType(self, iSMSTypeID):
        self.strSql = "DELETE FROM tb_e_SMSType WHERE SMSTypeID=" + str(iSMSTypeID)
        self.SMSDB.query(self.strSql)
        self.strSql = "DELETE FROM tb_e_SMSInfo WHERE SMSTypeID=" + str(iSMSTypeID)
        self.SMSDB.query(self.strSql)

    #通过类别名称获取类别ID
    def GetTypeID(self, strTypeName):
        self.strSql = "SELECT SMSTypeID FROM tb_e_SMSType WHERE SMSTypeName='" + strTypeName + "'"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            return self.SMSRow[0]
        else:
            return -100

        
    #检测号码组的名称是否存在
    def SendedNameIsExist(self, strSendedName):
        self.strSql = "SELECT SendedID FROM tb_e_SendedNumbers WHERE SendedName='" + strSendedName + "'"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            if self.SMSRow[0] != "":
                return 1
            else:
                return 0
        else:
            return 0

    #添加号码组，相同的名称不添加
    def InsertSendedNumbers(self, objSendedNumbers):
        self.mySendedNumbers = objSendedNumbers
        self.strSendedName = self.mySendedNumbers.SendedName.replace("'", "''")
        self.strSendedNumbers = self.mySendedNumbers.SendedNumbers.replace("'", "''")
        if self.SendedNameIsExist(self.strSendedName) == 1:
            return -101
        else:
            self.strSql = "INSERT INTO tb_e_SendedNumbers (SendedName,SendedNumbers,SendedOrder) VALUES('"+self.strSendedName+"','"+self.strSendedNumbers+"',"+str(self.mySendedNumbers.SendedOrder)+")"
            #print self.strSql
            self.SMSDB.query(self.strSql)
            return 1

    #修改号码组(收件人号码)
    def UpdateSendedNumbers(self, objSendedNumbers):
        self.mySendedNumbers = objSendedNumbers
        self.strSendedNumbers = self.mySendedNumbers.SendedNumbers.replace("'", "''")
        self.strSql = "UPDATE tb_e_SendedNumbers SET SendedNumbers='"+self.strSendedNumbers+"' WHERE SendedID="+str(self.mySendedNumbers.SendedID)
        #print self.strSql
        self.SMSDB.query(self.strSql)

    #修改号码组(号码组名称)
    def UpdateSendedName(self, objSendedNumbers):
        self.mySendedNumbers = objSendedNumbers
        self.strSendedName = self.mySendedNumbers.SendedName.replace("'", "''")
        if self.SendedNameIsExist(self.strSendedName) == 1:
            return -101
        else:
            self.strSql = "UPDATE tb_e_SendedNumbers SET SendedName='"+self.strSendedName+"' WHERE SendedID="+str(self.mySendedNumbers.SendedID)
            self.SMSDB.query(self.strSql)
            return 1

    #修改号码组顺序
    def UpdateOrderBySended(self, objSendedNumbers):
        self.mySendedNumbers = objSendedNumbers
        self.strSql = "UPDATE tb_e_SendedNumbers SET SendedOrder=" + str(self.mySendedNumbers.SendedOrder) + " WHERE SendedID=" + str(self.mySendedNumbers.SendedID)
        #print self.strSql
        self.SMSDB.query(self.strSql)

    #删除一条号码组
    def DeleteSendedNumbers(self, iSendedID):
        self.strSql = "DELETE FROM tb_e_SendedNumbers WHERE SendedID=" + str(iSendedID)
        self.SMSDB.query(self.strSql)

    #读取号码组到号码组实体中（号码组列表）
    def LoadSendedNumbers(self):
        self.MySendedNumbersList = SendedNumbersList()
        self.strSql = "SELECT SendedID,SendedName,SendedNumbers,SendedOrder FROM tb_e_SendedNumbers ORDER BY SendedOrder,SendedID DESC"
        self.SMSDB.query(self.strSql)
        for self.SMSRow in self.SMSDB:
            self.MySendedNumbersList.AppendSended(SendedNumbersInfo(), 0)
            self.MySendedNumbersList[-1].SendedID = self.SMSRow[0]
            self.MySendedNumbersList[-1].SendedName = self.SMSRow[1]
            self.MySendedNumbersList[-1].SendedNumbers = self.SMSRow[2]
            self.MySendedNumbersList[-1].SendedOrder = self.SMSRow[3]

        return self.MySendedNumbersList.SendedList

        
#打开短信数据库
MySMSDB = SMSDataBase()


#文件操作类（导入、导出时用）
class MyPickle:
    def __init__(self):
        self.objList = []
        self.MySMSList = SMSList()
        self.FLine = ''
        self.ReadContent = ''
        
    #加载文件（导入）
    def load(self, file):
        global ExportSMSTypeName
        self.file = file

        self.posLast = -1
        self.posCur = 0
        self.file.seek(0)
        
        while self.posLast != self.posCur:
            self.posLast = self.file.tell()
            self.FLine = self.file.readline()
            self.posCur = self.file.tell()

            if self.FLine.endswith('\r\n'):
                self.FLine = self.FLine[:-2]
            elif self.FLine.endswith('\n'):
                self.FLine = self.FLine[:-1]
            elif self.FLine.endswith('\r'):
                self.FLine = self.FLine[:-1]

            if self.posLast == 0:
                if self.FLine.lower().find('smsdata') == -1:
                    return ''
                else:
                    continue

            if self.FLine.strip() == '':
                continue
            
            if self.FLine.endswith('|||'):
                ExportSMSTypeName = self.FLine[:-3]
            else:
                if ExportSMSTypeName.strip() == '':
                    continue
                self.FLine = self.FLine.replace('|n', '\n')
                self.MySMSList.AppendSMS(SMSExInfo(), 0)
                self.MySMSList[-1].SMSTypeName = ExportSMSTypeName
                self.MySMSList[-1].SMSContent = self.FLine

        return self.MySMSList

    #写入文件（导出）
    def dump(self, mySMSList, file):
        global ExportSMSTypeName
        self.MySMSList = mySMSList
        self.file = file

        if len(self.MySMSList) > 0:
            ExportSMSTypeName = ''
            for self.mySMS in self.MySMSList:
                if ExportSMSTypeName == '':
                    self.FLine = 'SMSData\r\n'
                else:
                    self.FLine = ''
                if ExportSMSTypeName != self.mySMS.SMSTypeName:
                    ExportSMSTypeName = self.mySMS.SMSTypeName
                    self.FLine += self.mySMS.SMSTypeName + '|||\r\n'
                self.FLine += self.mySMS.SMSContent.replace(u'\n', u'|n') + '\r\n'
                self.file.write(UN8(self.FLine))

    #读取文件内容（帮助文档）
    def Read(self, FilePath):
        self.file = open(FilePath, 'r')
        try:
            self.ReadContent = U8(self.file.read())
        finally:
            self.file.close()
        return self.ReadContent


#短信实体类（短信列表）
class SMSInfo:
    def __init__(self, SMSContent='', SMSTypeID=0, SMSInfoID=0):
        self.SMSInfoID = SMSInfoID
        self.SMSTypeID = SMSTypeID
        self.SMSContent = SMSContent

    #显示短信内容
    def DisplaySMS(self):
        Msg(self.SMSContent)

#短信实体扩展类，多加了类别名称（导入、导出时用）
class SMSExInfo(SMSInfo):
    def __init__(self, SMSContent='', SMSTypeName='', SMSTypeID=0, SMSInfoID=0):
        SMSInfo.__init__(self, SMSContent, SMSTypeID, SMSInfoID)
        self.SMSTypeName = SMSTypeName

#短信实体扩展类（短信基地用）
class SMSInfoByHome(SMSInfo):
    def __init__(self, SMSContent='', SMSTypeID=0, SMSInfoID=0, UserName='', UserLevelName='', UserScore=0, AddSMSNumber=0, UserID=0, BgColor=0):
        SMSInfo.__init__(self, SMSContent, SMSTypeID, SMSInfoID)
        self.UserName = UserName
        self.UserLevelName = UserLevelName
        self.UserScore = UserScore
        self.AddSMSNumber = AddSMSNumber
        self.UserLevelID = UserLevelID
        self.UserID = UserID
        self.BgColor = BgColor

#短信实体操作类（操作短信列表）
class SMSList:
    def __init__(self):
        global MySMSDB
        self.SMSList = []
 
    def __getitem__(self, index):
        return self.SMSList[index]
        
    def __len__(self):
        return len(self.SMSList)
        
    def LoadSMS(self, strCondition):
        self.SMSList = MySMSDB.LoadSMS(strCondition)

    def LoadAllSMS(self):
        self.SMSList = MySMSDB.LoadAllSMS()
        
    #导入短信（导入、导出时用）
    def ImportSMS(self, objSMSInfo, Mode=1, iTypeOrder=999):
        return MySMSDB.ImportSMS(objSMSInfo, Mode, iTypeOrder)

    #添加短信（Mode：0-数据库不添加，1-正常添加，2-不提示添加）
    def AppendSMS(self, objSMSInfo, Mode=1):
        self.SMSList.append(objSMSInfo)
        if Mode != 0:
            self.iVar = MySMSDB.InsertSMS(objSMSInfo)
            if Mode == 1:
                if self.iVar == -101:
                    Msg(U8('此短信已经存在！'))
                else:
                    Msg(U8('短信添加成功！'))
        
    def ModifySMS(self, strSMSContent, iSMSIndex, Mode=1):
        self.SMSList[iSMSIndex].SMSContent = strSMSContent
        MySMSDB.UpdateSMS(self.SMSList[iSMSIndex])
        if Mode == 1:
            Msg(U8('短信修改成功！'))

    def RemoveSMS(self, objSMSInfo):
        self.SMSList.remove(objSMSInfo)
        MySMSDB.DeleteSMS(objSMSInfo.SMSInfoID)
        Msg(U8('短信删除成功！'))
    
    def ListSMS(self):
        for self.mySMS in self.SMSList:
            self.mySMS.DisplaySMS()

    def RandomSMS(self):
        return self.SMSList[randint(0, len(self.SMSList)-1)]

    def GetSMSContentList(self):
        self.objList = []
        for self.tSMS in self.SMSList:
            self.objList.append(self.tSMS.SMSContent)
        return self.objList


#短信实体操作类（短信基地用）
class SMSListByHome(SMSList):
    def LoadSMS(self, ReturnValue):
        SMSAllDB = ReturnValue.split('||')
        self.MaxPage = int(SMSAllDB[0])
        SMSDB = SMSAllDB[1].split('##')
        
        for SMSRow in SMSDB:
            SMSColumns = SMSRow.split('$$')
            tSMS = SMSInfo()
            tSMS.SMSInfoID = int(SMSColumns[0])
            tSMS.SMSTypeID = int(SMSColumns[1])
            tSMS.SMSContent = SMSColumns[2]
            tSMS.UserName = SMSColumns[3]
            tSMS.UserLevelName = SMSColumns[4]
            tSMS.UserScore = int(SMSColumns[5])
            tSMS.AddSMSNumber = int(SMSColumns[6])
            tSMS.UserID = int(SMSColumns[7])
            tSMS.BgColor = int(SMSColumns[8])            
            self.SMSList.append(tSMS)

    def LoadAllSMS(self, ReturnValue):
        self.LoadSMS(ReturnValue)

    #添加短信（Mode：0-服务器不添加，1-正常添加，2-不提示添加）
    def AppendSMS(self, objSMSInfo, Mode=1):
        self.SMSList.append(objSMSInfo)
        if Mode != 0:
            self.iVar = MySMSDB.InsertSMS(objSMSInfo)
            if Mode == 1:
                if self.iVar == -101:
                    Msg(U8('此短信已经存在！'))
                else:
                    Msg(U8('短信添加成功！'))
        
    def ModifySMS(self, strSMSContent, iSMSIndex, Mode=1):
        self.SMSList[iSMSIndex].SMSContent = strSMSContent
        MySMSDB.UpdateSMS(self.SMSList[iSMSIndex])
        if Mode == 1:
            Msg(U8('短信修改成功！'))

    def RemoveSMS(self, objSMSInfo, aUserID, aUserCheckCode, aSMSInfoID):
        Conn = ConnServer()
        Conn.GetConnString()

        strQuery = u'/DeleteSMS.asp?UserID=' + aUserID + u'&CheckCode=' + aUserCheckCode + u'&SMSInfoID=' + str(aSMSInfoID)
        #print strQuery
        Conn.BeginConnect()
        iRet = Conn.RequestConn('GET', Conn.Server + strQuery)
        if iRet == -1:
            Msg(U8('连接服务器失败'))
            self.Back()
        
        RetValue = Conn.ReadRequest()
        iRet = Conn.CheckReturnValue(RetValue)
        if(iRet < 0):
            Msg(Conn.ErrorInfo)
        else:
            self.SMSList.remove(objSMSInfo)
            Msg(U8('短信删除成功！'))

        Conn.CloseConnect()
        
        
#类别实体类（类别列表）
class SMSTypeInfo:
    def __init__(self, SMSTypeName='', SMSTypeID=0, SMSTypeOrder=999):
        self.SMSTypeID = SMSTypeID
        self.SMSTypeName = SMSTypeName
        self.SMSTypeOrder = SMSTypeOrder


#类别实体操作类（操作类别列表）
class SMSTypeList:
    def __init__(self):
        global MySMSDB
        self.TypeList = []

    def __getitem__(self, index):
        return self.TypeList[index]
        
    def __len__(self):
        return len(self.TypeList)

    def FindTypeName(self, iTypeID):
        self.tTypeName = ''
        for self.tType in self.TypeList:
            if self.tType.SMSTypeID == iTypeID:
                self.tTypeName = self.tType.SMSTypeName
                break
        return self.tTypeName
  
    def AppendType(self, objTypeInfo, Mode=1):
        self.TypeList.append(objTypeInfo)
        if Mode == 1:
            self.iRet = MySMSDB.InsertType(objTypeInfo.SMSTypeName)
            if self.iRet == -101:
                Msg(objTypeInfo.SMSTypeName + U8('此类别短信已经存在！'))
            elif self.iRet >= 0:
                Msg(objTypeInfo.SMSTypeName + U8('类别添加成功！'))
            else:
                Msg(objTypeInfo.SMSTypeName + U8('类别添加失败！'))
        
    def ModifyType(self, strTypeName, iTypeIndex, Mode=1):
        self.TypeList[iTypeIndex].SMSTypeName = strTypeName
        self.iRet = MySMSDB.UpdateType(self.TypeList[iTypeIndex])
        if Mode == 1:
            if self.iRet == -101:
                Msg(strTypeName + U8('此类别短信已经存在！'))
            elif self.iRet >= 0:
                Msg(U8('修改成功！'))
            else:
                Msg(U8('修改失败！'))

    def ModifyOrder(self, iTypeOrder, iTypeIndex, Mode=1):
        MySMSDB.ModifyOrder(self.TypeList[iTypeIndex].SMSTypeID, iTypeOrder)
        if Mode == 1:
            Msg(U8('类别顺序修改成功！'))

    def LoadType(self):
        self.TypeList = MySMSDB.LoadType()

    def RemoveType(self, objSMSType):
        self.TypeList.remove(objSMSType)
        MySMSDB.DeleteSMSType(objSMSType.SMSTypeID)
        Msg(U8('类别删除成功！'))

    def GetTypeNameList(self):
        self.objList = []
        for self.tType in self.TypeList:
            self.objList.append(self.tType.SMSTypeName)
        return self.objList

        
#号码组实体类（号码组列表）
class SendedNumbersInfo:
    def __init__(self, SendedName='', SendedNumbers='', SendedID=0, SendedOrder=999):
        self.SendedID = SendedID
        self.SendedName = SendedName
        self.SendedNumbers = SendedNumbers
        self.SendedOrder = SendedOrder


#号码组实体操作类（操作号码组列表）
class SendedNumbersList:
    def __init__(self):
        global MySMSDB
        self.SendedList = []

    def __getitem__(self, index):
        return self.SendedList[index]
        
    def __len__(self):
        return len(self.SendedList)
  
    def AppendSended(self, objSendedInfo, Mode=1):
        self.SendedList.append(objSendedInfo)
        if Mode == 1:
            self.iRet = MySMSDB.InsertSendedNumbers(objSendedInfo)
            if self.iRet == -101:
                Msg(objSendedInfo.SendedName + U8('此名称已经存在！'))
            elif self.iRet >= 0:
                Msg(U8('号码组保存成功！'))
            else:
                Msg(U8('号码组保存失败！'))
        
    #修改号码组(号码)
    def ModifySendedNumbers(self, strSendedNumbers, iSendedIndex, Mode=1):
        self.SendedList[iSendedIndex].SendedNumbers = strSendedNumbers
        MySMSDB.UpdateSendedNumbers(self.SendedList[iSendedIndex])
        if Mode == 1:
            Msg(U8('修改成功！'))


    #修改号码组(名称)
    def ModifySendedName(self, strSendedName, iSendedIndex, Mode=1):
        self.SendedList[iSendedIndex].SendedName = strSendedName
        self.iRet = MySMSDB.UpdateSendedName(self.SendedList[iSendedIndex])
        if Mode == 1:
            if self.iRet == -101:
                Msg(strSendedName + U8('此名称已经存在！'))
            elif self.iRet >= 0:
                Msg(U8('修改成功！'))
            else:
                Msg(U8('修改失败！'))

    #修改号码组顺序
    def ModifyOrderBySended(self, iSendedOrder, iSendedIndex, Mode=1):
        self.SendedList[iSendedIndex].SendedOrder = iSendedOrder
        MySMSDB.UpdateOrderBySended(self.SendedList[iSendedIndex])
        if Mode == 1:
            Msg(U8('号码组顺序修改成功！'))

    def LoadSended(self):
        self.SendedList = MySMSDB.LoadSendedNumbers()

    def RemoveSended(self, objSendedInfo):
        self.SendedList.remove(objSendedInfo)
        MySMSDB.DeleteSendedNumbers(objSendedInfo.SendedID)
        Msg(U8('删除成功！'))

    def GetSendedNameList(self):
        self.objList = []
        for self.tSended in self.SendedList:
            self.objList.append(self.tSended.SendedName)
        return self.objList


#设置文件类
class Settings:
    def __init__( self ):
        (yr, mo, da, h, m, s, wd, jd, ds) = time.localtime(time.time())
        m += 60*h
        s += 60*m
        self._CurrentDate = time.time() - s
        self._CurrentTime = s

    #获取发送设置
    def LoadConfig(self, conf, aType):
	self.conffile=conf
	self.config=parse.Parser(self.conffile)
	if os.path.exists(self.conffile):
	    temp=self.config.parse()
	else:
	    exec('self._New' + aType + 'Config()')

    #获取高级发送设置
    def LoadSendConfig(self, conf):
	self.LoadConfig(conf, 'Send')

    #新的发送设置
    def _NewSendConfig(self):
	self.config.contents=\
	{\
	    'SendMode':[0],\
	    'SendType':[0],\
	    'Receiver':[0],\
	    'SendDate':[self._CurrentDate],\
	    'SendTime':[self._CurrentTime],\
	    'IsSaveNumbers':[0],\
            'ReceiveNumber':[u'0'],\
            'IsReceiveReport':[0],\
	}
	self.SaveConfig()


    #获取系统设置
    def LoadSystemConfig(self, conf):
	self.LoadConfig(conf, 'System')

    #新的系统设置
    def _NewSystemConfig(self):
	self.config.contents=\
	{\
	    'ViewOrModify':[0],\
	    'IsExitQuery':[0],\
	    'LinkMode':[0],\
	    'IsAutoLogin':[1],\
	    'DefaultUserID':[u''],\
	    'DefaultPassword':[u''],\
            'TimeOut':[120],\
            'IsFirst':[0],\
	}
	self.SaveConfig()

    #保存设置
    def SaveConfig(self):
	#try:
	self.config.write()
	#except:
	#    appuifw.note(U8('保存设置出错！'), 'error')

#发送表单类
class SendForm:
    global ConfigPathBySend
    
    #初使化表单
    def __init__( self ):
        #保存状态
        self._iIsSaved = False

        self.settings = Settings()
        self.settings.LoadSendConfig(ConfigPathBySend)
        
        try:
            self._SendMode = int(U(self.settings.config.contents['SendMode'][0]))
        except:
            self._SendMode = 0
        try:
            self._SendType = int(U(self.settings.config.contents['SendType'][0]))
        except:
            self._SendType = 0
        try:
            self._Receiver = int(U(self.settings.config.contents['Receiver'][0]))
        except:
            self._Receiver = 0
        try:
            self._SendDate = float(U(self.settings.config.contents['SendDate'][0]))
        except:
            self._SendDate = float(self.settings._CurrentDate)
        try:
            self._SendTime = float(U(self.settings.config.contents['SendTime'][0]))
        except:
            self._SendTime = float(self.settings._CurrentTime)
        try:
            self._IsSaveNumbers = int(U(self.settings.config.contents['IsSaveNumbers'][0]))
        except:
            self._IsSaveNumbers = 0
        try:
            self._ReceiveNumber = U(self.settings.config.contents['ReceiveNumber'][0]).replace(u'.0', u'')
        except:
            self._ReceiveNumber = u'0'
        try:
            self._IsReceiveReport = int(U(self.settings.config.contents['IsReceiveReport'][0]))
        except:
            self._IsReceiveReport = 0
        self._CurrentDate = float(self.settings._CurrentDate)

        #表单项
        self._iFields = [( U8('方送方式'), 'combo', ( [U8('直接发送'), U8('定时发送')], self._SendMode )),
                         ( U8('方送类型'), 'combo', ( [U8('普通短信'), U8('闪信')], self._SendType )),
                         ( U8('收件人'), 'combo', ( [U8('从名片夹选择'), U8('从号码组选择'), U8('直接输入号码')], self._Receiver )),
                         ( U8('发送日期'), 'date', self._SendDate),
                         ( U8('发送时间'), 'time', self._SendTime),
                         ( U8('提示保存已发送号码'), 'combo', ( [U8('提示'), U8('不提示')], self._IsSaveNumbers )),
                         ( U8('收件人号码'), 'text', self._ReceiveNumber),
                         ( U8('接收报告'), 'combo', ( [U8('否'), U8('是')], self._IsReceiveReport )),
                         ( U8('当前日期'), 'date', self._CurrentDate)]
 
    #显示表单
    def SetActive( self ):
        self._iIsSaved = False
        self._iForm = appuifw.Form(self._iFields, appuifw.FFormEditModeOnly+appuifw.FFormDoubleSpaced)
        #self._iForm.menu([(U8('保存状态'), self.GetSaveStatus),(U8('保存状态'), self.GetSaveStatus)])
        self._iForm.save_hook = self._MarkSaved
        self._iForm.flags = appuifw.FFormEditModeOnly+appuifw.FFormDoubleSpaced
        self._iForm.execute()
  
    #记录保存状态
    def _MarkSaved( self, aBool ):
        self._iIsSaved = aBool
 
    #获取保存状态
    def IsSaved( self ):
        return self._iIsSaved

    def GetSendMode( self ):
        return self._iForm[0][2][1]
 
    def GetSendType( self ):
        return self._iForm[1][2][1]
 
    def GetReceiver( self ):
        return self._iForm[2][2][1]
 
    def GetSendDate( self ):
        return self._iForm[3][2]    
 
    def GetSendTime( self ):
        return self._iForm[4][2]    
 
    def GetIsSaveNumbers( self ):
        return self._iForm[5][2][1]
 
    def GetReceiveNumber( self ):
        return self._iForm[6][2]
 
    def GetIsReceiveReport( self ):
        return self._iForm[7][2][1]
 
    #保存状态到配置文件
    def SaveStatus(self):
        self.settings.config.contents['SendMode'][0] = self.GetSendMode()
        self.settings.config.contents['SendType'][0] = self.GetSendType()
        self.settings.config.contents['Receiver'][0] = self.GetReceiver()
        self.settings.config.contents['SendDate'][0] = self.GetSendDate()
        self.settings.config.contents['SendTime'][0] = self.GetSendTime()
        self.settings.config.contents['IsSaveNumbers'][0] = self.GetIsSaveNumbers()
        if self.GetReceiveNumber() != '':
            try:
                self.settings.config.contents['ReceiveNumber'][0] = self.GetReceiveNumber()
            except:
                self.settings.config.contents['ReceiveNumber'].append(u'0')
        else:
            self.settings.config.contents['ReceiveNumber'][0] = u'0'
        self.settings.config.contents['IsReceiveReport'][0] = self.GetIsReceiveReport()
        self.settings.SaveConfig()


#系统表单类
class SystemForm:
    global ConfigPathBySystem
    
    #初使化表单
    def __init__( self ):
        #保存状态
        self._iIsSaved = False

        self.settings = Settings()
        self.settings.LoadSystemConfig(ConfigPathBySystem)
        
        self._ViewOrModify = int(U(self.settings.config.contents['ViewOrModify'][0]))
        self._IsExitQuery = int(U(self.settings.config.contents['IsExitQuery'][0]))
        self._LinkMode = int(U(self.settings.config.contents['LinkMode'][0]))
        self._IsAutoLogin = int(U(self.settings.config.contents['IsAutoLogin'][0]))

        #表单项
        self._iFields = [( U8('进入短信时'), 'combo', ( [U8('默认查看'), U8('默认编辑')], self._ViewOrModify )),
                         ( U8('退出系统时提示'), 'combo', ( [U8('是'), U8('否')], self._IsExitQuery )),
                         ( U8('联网方式'), 'combo', ( [U8('移动梦网'), U8('直连互联网')], self._LinkMode )),
                         ( U8('登录方式'), 'combo', ( [U8('直接登录'), U8('手动登录')], self._IsAutoLogin ))]
 
    #显示表单
    def SetActive( self ):
        self._iIsSaved = False
        self._iForm = appuifw.Form(self._iFields, appuifw.FFormEditModeOnly+appuifw.FFormDoubleSpaced)
        #self._iForm.menu([(U8('保存状态'), self.GetSaveStatus),(U8('保存状态'), self.GetSaveStatus)])
        self._iForm.save_hook = self._MarkSaved
        self._iForm.flags = appuifw.FFormEditModeOnly+appuifw.FFormDoubleSpaced
        self._iForm.execute()
  
    #记录保存状态
    def _MarkSaved( self, aBool ):
        self._iIsSaved = aBool
 
    #获取保存状态
    def IsSaved( self ):
        return self._iIsSaved

    def GetViewOrModify( self ):
        self._ViewOrModify = self._iForm[0][2][1]
        return self._ViewOrModify
 
    def GetIsExitQuery( self ):
        self._IsExitQuery = self._iForm[1][2][1]
        return self._IsExitQuery
 
    def GetLinkMode( self ):
        self._LinkMode = self._iForm[2][2][1]
        return self._LinkMode
 
    def GetIsAutoLogin( self ):
        self._IsAutoLogin = self._iForm[3][2][1]
        return self._IsAutoLogin

    #保存状态到配置文件
    def SaveStatus(self):
        self.settings.config.contents['ViewOrModify'][0] = self.GetViewOrModify()
        self.settings.config.contents['IsExitQuery'][0] = self.GetIsExitQuery()
        self.settings.config.contents['LinkMode'][0] = self.GetLinkMode()
        self.settings.config.contents['IsAutoLogin'][0] = self.GetIsAutoLogin()
        self.settings.SaveConfig()


#列表类
class ScreenList:
    def __init__(self, aList=[], aClickListBoxHandler=None, aRemoveHandler=None, aYesHandler=None, aRetractHandler=None, aLeftHandler=None, aRightHandler=None, a0Handler=None, a2Handler=None, a4Handler=None, a5Handler=None, a6Handler=None, a8Handler=None, aStarHandler=None, aHashHandler=None):
        self.MyList = aList
        self.iListLength = len(self.MyList)
        if self.iListLength == 0:
            self.MyList.append(u' ')
        self.MyListBox = appuifw.Listbox(self.MyList, aClickListBoxHandler)

        #绑定列表按键事件
        if aLeftHandler == None:
            self.MyListBox.bind(EKeyLeftArrow, self.MyListBox_GoPervPage)
        else:
            self.MyListBox.bind(EKeyLeftArrow, aLeftHandler)
        if aRightHandler == None:
            self.MyListBox.bind(EKeyRightArrow, self.MyListBox_GoNextPage)
        else:
            self.MyListBox.bind(EKeyRightArrow, aRightHandler)

        self.MyListBox.bind(EKeyDownArrow, self.MyListBox_DownKey)
        self.MyListBox.bind(EKeyUpArrow, self.MyListBox_UpKey)
        self.MyListBox.bind(EKey3, self.MyListBox_GoPervPage)
        self.MyListBox.bind(EKey9, self.MyListBox_GoNextPage)
        self.MyListBox.bind(EKey1, self.MyListBox_GoFirst)
        self.MyListBox.bind(EKey7, self.MyListBox_GoLast)
        self.MyListBox.bind(EKeyBackspace, aRemoveHandler)
        self.MyListBox.bind(EKeyYes, aYesHandler)

        if aRetractHandler != None:
            self.MyRetractHandler = aRetractHandler
        else:
            self.MyRetractHandler = lambda None:None

        if a5Handler != None:
            self.MyListBox.bind(EKey5, a5Handler)
        else:
            self.MyListBox.bind(EKey5, aClickListBoxHandler)

        if a0Handler != None:
            self.MyListBox.bind(EKey0, a0Handler)

        if a2Handler != None:
            self.MyListBox.bind(EKey2, a2Handler)

        if a4Handler != None:
            self.MyListBox.bind(EKey4, a4Handler)

        if a6Handler != None:
            self.MyListBox.bind(EKey6, a6Handler)

        if a8Handler != None:
            self.MyListBox.bind(EKey8, a8Handler)

        if aStarHandler != None:
            self.MyListBox.bind(EKeyStar, aStarHandler)

        if aHashHandler != None:
            self.MyListBox.bind(EKeyHash, aHashHandler)

    #在列表中，按3键可以向上翻页
    def MyListBox_GoPervPage(self):
        if self.iListLength == 0:
            return
        self.SelectedListHanderIndex = self.MyListBox.current()
        if self.SelectedListHanderIndex - 6 <= 0:
            self.SelectedListHanderIndex = 0
        else:
            self.SelectedListHanderIndex -= 6
        self.MyListBox.set_list(self.MyList, self.SelectedListHanderIndex)
        self.MyRetractHandler(self.MyList[self.SelectedListHanderIndex])
        self.SelectedListHanderIndex = None

    #在列表中，按9键可以向下翻页
    def MyListBox_GoNextPage(self):
        if self.iListLength == 0:
            return
        self.SelectedListHanderIndex = self.MyListBox.current()
        if self.SelectedListHanderIndex + 6 >= self.iListLength:
            self.SelectedListHanderIndex = self.iListLength - 1
        else:
            self.SelectedListHanderIndex += 6
        self.MyListBox.set_list(self.MyList, self.SelectedListHanderIndex)
        self.MyRetractHandler(self.MyList[self.SelectedListHanderIndex])
        self.SelectedListHanderIndex = None

    #在列表中，按1键可以转到第一条
    def MyListBox_GoFirst(self):
        if self.iListLength == 0:
            return
        self.SelectedListHanderIndex = 0
        self.MyListBox.set_list(self.MyList, self.SelectedListHanderIndex)
        self.MyRetractHandler(self.MyList[self.SelectedListHanderIndex])
        self.SelectedListHanderIndex = None

    #在列表中，按7键可以转到最后一条
    def MyListBox_GoLast(self):
        if self.iListLength == 0:
            return
        self.SelectedListHanderIndex = self.iListLength - 1
        self.MyListBox.set_list(self.MyList, self.SelectedListHanderIndex)
        self.MyRetractHandler(self.MyList[self.SelectedListHanderIndex])
        self.SelectedListHanderIndex = None
        
    #在列表中，当光标在最后一条，按下导航键可以转到第一条
    def MyListBox_DownKey(self):
        global IsTwoVer
        if self.iListLength == 0:
            return
        self.SelectedListHanderIndex = self.MyListBox.current()
        if self.SelectedListHanderIndex == self.iListLength - 1:
            if IsTwoVer == 1:
                self.MyRetractHandler(self.MyList[0])
            else:
                self.tTimer = e32.Ao_timer()
                self.tTimer.after(0.1, self.MyListBoxGoTop)
        elif self.iListLength > 1:
            self.SelectedListHanderIndex += 1
            self.MyRetractHandler(self.MyList[self.SelectedListHanderIndex])
        self.SelectedListHanderIndex = None

    #在列表中，当光标在第一条，按上导航键可以转到最后一条
    def MyListBox_UpKey(self):
        global IsTwoVer
        if self.iListLength == 0:
            return
        self.SelectedListHanderIndex = self.MyListBox.current()
        if self.SelectedListHanderIndex == 0:
            if IsTwoVer == 1:
                self.MyRetractHandler(self.MyList[self.iListLength - 1])
            else:
                self.tTimer = e32.Ao_timer()
                self.tTimer.after(0.1, self.MyListBoxGoBottom)
        elif self.iListLength > 1:
            self.SelectedListHanderIndex -= 1
            self.MyRetractHandler(self.MyList[self.SelectedListHanderIndex])
        self.SelectedListHanderIndex = None
    
    #列表光标转到最后一条
    def MyListBoxGoTop(self):
        self.MyListBox.set_list(self.MyList, 0)
        self.MyRetractHandler(self.MyList[0])

    #列表光标转到第一条
    def MyListBoxGoBottom(self):
        self.MyListBox.set_list(self.MyList, self.iListLength - 1)
        self.MyRetractHandler(self.MyList[self.iListLength - 1])


#连接服务器类
class ConnServer:
    def __init__(self):
        self.Host = None
        self.conn = None
    
    #建立连接
    def BeginConnect(self):
        self.GetConnString()
        if self.conn == None:
            self.conn = httplib.HTTPConnection(self.Host, self.Port)
            #self.conn.set_debuglevel(1)

    #请求服务器
    def RequestConn(self, aRequestMethod, aRequestUrl, aRequestBody=None, aHeaders={}):
        try:
            self.conn.request(aRequestMethod, aRequestUrl, aRequestBody, aHeaders)
            return 1
        except:
            return -1
            #print 1,aRequestUrl

    #获取请求的返回内容
    def ReadRequest(self):
        try:
            return self.conn.getresponse().read()
        except:
            return -100
 
    #关闭连接
    def CloseConnect(self):
        if self.conn != None:
            self.conn.close()
            self.conn = None

    #获取代理和连接服务器地址
    def GetConnString(self, IsReGet = 0):
        global IsEmulator
        global ConfigPathBySystem

        if self.Host == None or self.Host == '' or IsReGet == 1:
            self.settings = Settings()
            self.settings.LoadSystemConfig(ConfigPathBySystem)
            
            _LinkMode = int(U(self.settings.config.contents['LinkMode'][0]))
            _IsAutoLogin = int(U(self.settings.config.contents['IsAutoLogin'][0]))
            try:
                _DefaultUserID = U(self.settings.config.contents['DefaultUserID'][0])
            except:
                _DefaultUserID = u''
            try:
                _DefaultPassword = U(self.settings.config.contents['DefaultPassword'][0])
            except:
                _DefaultPassword = u''

            if IsEmulator == 1:
                self.Host = u'192.168.1.6'
                self.Server = u'http://192.168.1.6/smsstore'
            else:
                if _LinkMode == 0:
                    self.Host = u'10.0.0.172'
                else:
                    self.Host = u'www.kerchin.com'
                self.Server = u'http://www.kerchin.com/bbs/smsstore'

            self.Port = 80
            #是否自动登录
            self.IsAutoLogin = _IsAutoLogin
            #默认用户
            self.DefaultUserID = _DefaultUserID
            self.DefaultPassword = _DefaultPassword
            #print self.DefaultUserID, self.DefaultPassword

    #验证返回值
    def CheckReturnValue(self, RetValue):
        if(RetValue == '1'):
            self.ErrorInfo = ''
            return 1
        elif(RetValue == '-1'):
            self.ErrorInfo = U8('连接服务器失败')
            return -1
        elif(RetValue == '-2'):
            self.ErrorInfo = U8('服务器执行失败')
            return -2
        elif(RetValue == '-99'):
            self.ErrorInfo = U8('服务器正在更新，请稍后再试')
            return -99
        elif(RetValue == '-999'):
            self.ErrorInfo = U8('未知错误')
            return -999
        elif(RetValue == '-100'):
            self.ErrorInfo = U8('注册时出错')
            return -100
        elif(RetValue == '-101'):
            self.ErrorInfo = U8('昵称不能小于2个字或大于10个字')
            return -101
        elif(RetValue == '-102'):
            self.ErrorInfo = U8('此昵称已经存在，请更换昵称')
            return -102
        elif(RetValue == '-103'):
            self.ErrorInfo = U8('每30分钟只能注册一个用户')
            return -103
        elif(RetValue == '-110'):
            self.ErrorInfo = U8('用户ID错误')
            return -110
        elif(RetValue == '-111'):
            self.ErrorInfo = U8('用户ID不存在或密码错误')
            return -111
        elif(RetValue == '-112'):
            self.ErrorInfo = U8('您没有登录或登录超时')
            return -112
        elif(RetValue == '-120'):
            self.ErrorInfo = U8('获取基地版块出错')
            return -120
        elif(RetValue == '-121'):
            self.ErrorInfo = U8('类别ID错误')
            return -121
        elif(RetValue == '-130'):
            self.ErrorInfo = U8('该版块暂时没有信息')
            return -130
        elif(RetValue == '-131'):
            self.ErrorInfo = U8('当前版块没有找到该短信')
            return -131
        elif(RetValue == '-140'):
            self.ErrorInfo = U8('错误的参数信息')
            return -140
        elif(RetValue == '-141'):
            self.ErrorInfo = U8('添加短信时出错')
            return -141
        elif(RetValue == '-142'):
            self.ErrorInfo = U8('信息长度不能大于255个字')
            return -142
        elif(RetValue == '-150'):
            self.ErrorInfo = U8('短信ID错误')
            return -150
        elif(RetValue == '-151'):
            self.ErrorInfo = U8('删除短信时出错')
            return -151
        elif(RetValue == '-152'):
            self.ErrorInfo = U8('您没有操作权限或该短信已经被删除')
            return -152
        else:
            self.ErrorInfo = ''
            return 1


#短信酷的界面操作
class SMSScreen:
    def __init__(self):
        global MySMSDB
        global SMSPath
        global DBName
        
        self.Title = U8('短信酷')
        self.Screen = 'normal'
        self.Font = u'CombinedChinesePlain16'
        self.Color = 0x000000
        self._index = 0
        self._back = False
        self.DataFile = SMSPath + DBName + '.txt'

        self.myType = SMSTypeList()
        self.mySMS = SMSList()
        self.mySended = SendedNumbersList()
        self.SelectedSMSIndex = None
        self.SelectedSendedIndex = None
        self.SelectedTypeIndex = -1
        self.SelectedContactIndex = -1
        self.dbContacts = None
        self.ReceiveNumbers = ''
        self.IsBreak = 0
        self.IsManageSended = 0
        
        self._CurrentAction = ''
        self._CurParAction = ''
        self._CurParMode = 1
        self._CurParNumbers = ''
        self._PreviousAction = ''
        self._PreParAction = ''
        self._PreParMode = 1
        self._PreParNumbers = ''
        
        self._strAction = 'Main'
        self.Conn = None
        self._GetCurrentOption(CurrentAction='Back')

        self.TabIndex = 1
        #超时时间
        self.TimeOut = 120
        self.IsLogined = 0
        self.HomeName = U8('短信基地')

        self.app_lock = e32.Ao_lock()
        appuifw.app.title = self.Title
        appuifw.app.exit_key_handler = self.Exit
        appuifw.app.screen = self.Screen

        #查询短信
        self.SearchSMSMenu = (U8('查询短信'), ((U8('全部类别'),self.SearchSMSByAllType), (U8('当前类别'), self.SearchSMSByCurrentType)))

        #插入联系人菜单
        self.InsertContactMenu = (U8('插入联系人'), ((U8('姓名和电话'),self.InsertContactNamePhone), (U8('插入姓名'), self.InsertContactName), (U8('插入电话'),self.InsertContactPhone)))

        #导入导出菜单
        self.ImportExportMenu = (U8('导入导出'), ((U8('导入短信'), self.ImportData), (U8('导出短信'), self.ExportData)))

        #其它操作菜单
        self.OtherMenu = (U8('其它功能'), ((U8('更改系统设置'), self.ModifySystemConfig), (U8('查询联系人'), self.SearchNameByNumber), (U8('查询号码'), self.SearchNumberByName), (U8('下载UCWEB'), self.DownloadUcweb), (U8('关于系统'), self.About)))

        #退出系统菜单
        self.ExitMenu = (U8('退出系统'), self.Exit)

        #帮助菜单
        self.HelpMenu = (U8('导入/导出短信'), self.Help), \
                        (U8('默认/高级发送'), lambda: self.Help(u'DefaultAdvanced')), \

        #短信基地菜单
        self.SMSHome = (self.HomeName, ((U8('登录基地'), self.Login), (U8('手动注册'), self.SelfRegister), (U8('自动注册'), self.AutoRegister)))

        #收件箱菜单
        self.InBoxMenu = [ \
            (U8('随机回复'), self.ReRandomSend), \
            (U8('选择回复'), self.ReSelectSend), \
            (U8('自建回复'), self.ReAppendSend), \
            self.ImportExportMenu, \
            (U8('帮助'), (self.HelpMenu)), \
            self.OtherMenu, \
            self.ExitMenu, \
        ]

        #类别菜单
        self.TypeMenu = [ \
            (U8('随机发送'), ( \
                (U8('默认发送'), self.RandomSend), \
                (U8('高级发送'), lambda: self.SendSMSAdvancedReady(Source=2)), \
            )), \
            self.SMSHome, \
            (U8('添加短信'), self.AppendSMSReady), \
            (U8('类别管理'), ( \
                (U8('添加类别'), self.AddType), \
                (U8('删除类别'), self.RemoveType), \
                (U8('修改类别'), self.ModifyType), \
                (U8('修改类别顺序'), self.ModifyOrder), \
            )), \
            (U8('号码组管理'), self.ManageSended), \
            self.SearchSMSMenu, \
            self.ImportExportMenu, \
            (U8('帮助'), (self.HelpMenu)), \
            self.OtherMenu, \
            self.ExitMenu, \
        ]

        #短信菜单
        self.SMSMenu = [ \
            (U8('默认发送'), lambda: self.SendSMSReady(2)), \
            (U8('高级发送'), self.SendSMSAdvancedReady), \
            (U8('添加'), self.AppendSMSReady), \
            (U8('删除'), self.RemoveCurrentSMS_Menu), \
            (U8('查看'), self.SelectSMSHandler), \
            (U8('返回主菜单'), self.Back), \
            self.ExitMenu, \
        ]

        #号码组菜单
        self.SendedMenu_Send = [ \
            (U8('查看'), self.ViewSended), \
            (U8('选择'), self.SendedHandler), \
            (U8('删除'), self.RemoveSended), \
            (U8('返回主菜单'), self.Back), \
            self.ExitMenu, \
        ]

        #号码组菜单
        self.SendedMenu_Manage = [ \
            (U8('查看'), self.ViewSended), \
            (U8('添加'), self.AddSended), \
            (U8('删除'), self.RemoveSended), \
            (U8('修改号码组名称'), self.ModifySendedName), \
            (U8('修改号码组顺序'), self.ModifyOrderBySended), \
            (U8('返回主菜单'), self.Back), \
            self.ExitMenu, \
        ]
            

        appuifw.app.menu = self.TypeMenu

        #self.SMSInBoxList()
        self.SMSTypeList()
        
        appuifw.app.set_tabs([U8('类别'), U8('收��箱')], self.HandleTab)
        appuifw.app.body = self.TypeList
        #self._GetCurrentOption('Main')

        self.__menuMain = appuifw.app.menu
        self.__bgMain = appuifw.app.body
        self.__titleMain = appuifw.app.title

        self.GetSystemConfig()
        self.IsFirstRun()
        
        self.app_lock.wait()

    #获取系统设置
    def GetSystemConfig(self):
        global ConfigPathBySystem
        
        self.settings = Settings()
        self.settings.LoadSystemConfig(ConfigPathBySystem)
        
        self.ViewOrModify = int(U(self.settings.config.contents['ViewOrModify'][0]))
        self.IsExitQuery = int(U(self.settings.config.contents['IsExitQuery'][0]))
        self.TimeOut = int(U(self.settings.config.contents['TimeOut'][0]))
        self.IsFirst = int(U(self.settings.config.contents['IsFirst'][0]))
        #print 1,self.ViewOrModify, self.IsExitQuery

    #判断程序是否第一次运行
    def IsFirstRun(self):
        global ConfigPathBySystem
        if self.IsFirst < 2 and Query(U8('安装UCWEB，让您上网更轻松！\n是否安装？')):
            self.DownloadUcweb()

        self.settings = Settings()
        self.settings.LoadSystemConfig(ConfigPathBySystem)
        try:
            self.settings.config.contents['IsFirst'][0] = u'2'
        except:
            self.settings.config.contents['IsFirst'].append(u'0')
        self.settings.SaveConfig()

    #下载UCWEB
    def DownloadUcweb(self):
        url = u'http://down2.ucweb.com/download.asp?f=client@xyao&url=&title='
        try:
            e32.start_exe(u'z:\\system\\programs\\apprun.exe', u'z:\\system\\apps\\browser\\browser.app "' + url + '"')
            return 1
        except:
            return -1

    #更改系统设置
    def ModifySystemConfig(self):
        self.myForm = SystemForm()
        self.myForm.SetActive()
        if self.myForm.IsSaved():
            self.myForm.SaveStatus()
            self.ViewOrModify = self.myForm._ViewOrModify
            self.IsExitQuery = self.myForm._IsExitQuery
            #print 2,self.ViewOrModify, self.IsExitQuery
            self.myForm = None

    #随机发送短信    
    def RandomSend(self, Mode=1, ReceiveNumbers=''):
        #self._GetCurrentOption('RandomSend', Mode, '', ReceiveNumbers)
        
        self.strAction = ''
        if Mode == 0:
            self.strAction = 'Revert'
        
        if self._SelectType(self.strAction) > 0:
                    
            self.strCondition = " WHERE SMSTypeID=" + str(self.myType.TypeList[self.SelectedTypeIndex].SMSTypeID)
            self.mySMS.LoadSMS(self.strCondition)

            if len(self.mySMS) == 0:
                Msg(U8('该类别没有短信！'))
                return
            else:
                self.SendSMSContent = self.mySMS.RandomSMS().SMSContent
                if not Query(self.SendSMSContent[:20] + U8('...\n发送这条短信吗')):
                    if Query(U8('换一条短信吗？')):
                        self.RandomSend(Mode, ReceiveNumbers)
                        return
                    else:
                        return
                if Mode == 1:
                    self.tReceiveNumbers = ''
                    self.tIsConfig = 1
                    
                    self.settings = Settings()
                    self.settings.LoadSendConfig(ConfigPathBySend)
                    self.IsSend = int(U(self.settings.config.contents['SendMode'][0]))
                    self.IsFlash = int(U(self.settings.config.contents['SendType'][0]))
                    self.ReceiverType = int(U(self.settings.config.contents['Receiver'][0]))
                    self.SendDate = float(U(self.settings.config.contents['SendDate'][0]))
                    self.SendTime = float(U(self.settings.config.contents['SendTime'][0]))
                    self.IsSaveNumbers = U(self.settings.config.contents['IsSaveNumbers'][0])
                    self.IsReceiveReport = int(U(self.settings.config.contents['IsReceiveReport'][0]))
                    if self.ReceiverType == 2:
                        self.tReceiveNumbers = U(self.settings.config.contents['ReceiveNumber'][0]).replace(u'.0', u'')
                    elif self.ReceiverType == 1:
                        self.IsManageSended = 0
                        self.GetSendedList()
                        return
                        #self.tReceiveNumbers = self.mySended.SendedList[self.SendedList.current()].SendedNumbers
                    
                    if self.ReceiverType != 0:
                        if self.tReceiveNumbers != None and self.tReceiveNumbers != '' and self.tReceiveNumbers != '0':
                            Mode = 0
                        else:
                            return
                else:
                    self.tReceiveNumbers = ReceiveNumbers
                    self.tIsConfig = 0
                    self.IsSaveNumbers = 1
                    self.IsNotFlash = Query(U8('发送普��短信吗?\n点击取消则发送闪信.'))
                    if self.IsNotFlash:
                        self.IsFlash = 0
                    else:
                        self.IsFlash = 1
                    
                self._SendSMS(Mode, self.tReceiveNumbers, self.IsFlash, self.tIsConfig, self.IsSaveNumbers, IsReceiveReport=self.IsReceiveReport)


    #选择发送短信
    def SelectSend(self):
        #self._GetCurrentOption('SelectSend')
        self.ListSMS('SendSMS')

    #回复时随机发送短信
    def ReRandomSend(self):
        #self._GetCurrentOption('ReRandomSend')

        if Message_Content_Re[self.InBoxList.current()] == '' or Message_Content_Re[self.InBoxList.current()] == ' ':
            return
        
        self.ReceiveNumbers = self._GetReceiveNumber()
        #Msg(self.ReceiveNumbers)
        if self.ReceiveNumbers == '' or self.ReceiveNumbers == '0':
            return
        else:
            self.SelectedTypeIndex = -1 ##
            self.RandomSend(0, self.ReceiveNumbers)

    #回复时选择发送短信
    def ReSelectSend(self):
        #self._GetCurrentOption('ReSelectSend')
        if Message_Content_Re[self.InBoxList.current()] == '' or Message_Content_Re[self.InBoxList.current()] == ' ':
            return
        
        self.ReceiveNumbers = self._GetReceiveNumber()
        if self.ReceiveNumbers == '':
            return
        else:
            self.SelectedTypeIndex = -1 ##
            self.ListSMS('Revert')

    #回复时新建短信回复
    def ReAppendSend(self):
        #self._GetCurrentOption('ReAppendSMS')
        if Message_Content_Re[self.InBoxList.current()] == '' or Message_Content_Re[self.InBoxList.current()] == ' ':
            return

        self.ReceiveNumbers = self._GetReceiveNumber()
        if self.ReceiveNumbers == '' or self.ReceiveNumbers == '0':
            return
        
        self.text = appuifw.Text()
        self.text.color = self.Color
        self.text.font = self.Font
        self.text.set('')
        self.text.set_pos(0)
        appuifw.app.set_tabs([],None)
        #self.text.focus = True
        appuifw.app.title = U8('自建回复')
        appuifw.app.body = self.text
        appuifw.app.menu = [(U8('发送'), self.ReSendSMSReady), (U8('发送并保存'), self.ReSendSaveSMS), (U8('从收件箱获取'), self.GetInboxSMS), self.InsertContactMenu, (U8('返回主菜单'), self.Back)]
        uikludges.set_right_softkey_text(U8("主菜单"))
        appuifw.app.exit_key_handler = self.Back

    #自建回复时发送并保存短信
    def ReSendSaveSMS(self):
        self.SelectedTypeIndex = -1
        self.SaveSMS('Revert', 2)
        self.ReSendSMSReady()
        
    #回复时获取要发送的内容
    def ReSendSMSReady(self):
        #self._GetCurrentOption('ReSendSMSReady')
        self.SendSMSContent = self.text.get().replace(u'\u2029', u'\n')
        self.IsNotFlash = Query(U8('发送普通短信吗?\n点击取消则发送闪信.'))
        if self.IsNotFlash:
            self.IsFlash = 0
        else:
            self.IsFlash = 1
        self._SendSMS(0, self.ReceiveNumbers, self.IsFlash)
        self.Back()

    #回复时保存修改后的短信并发送
    def ReSendModifySMS(self):
        #self._GetCurrentOption('ReSendModifySMS')
        self.ModifySMS(0)
        self.ReSendSMSReady()
  
    #默认发送，获取发送短信的内容(Mode=1表示获取的是文本框中的短信内容，Mode=2表示获取的是菜单中选中的短信)
    def SendSMSReady(self, Mode = 1, aList=None):
        #self._GetCurrentOption('SendSMSReady')
        global ConfigPathBySend
        if aList == None:
            aList = self.mySMS
            
        self.IsBreak = 1
        if Mode == 1:
            self.SendSMSContent = self.text.get().replace(u'\u2029', u'\n')
        else:
            self.SendSMSContent = aList.SMSList[self.SMSList.current()].SMSContent

        self.tMode = 1
        self.tReceiveNumbers = ''
        self.tIsConfig = 1
        
        self.settings = Settings()
        self.settings.LoadSendConfig(ConfigPathBySend)
        self.IsSend = int(U(self.settings.config.contents['SendMode'][0]))
        self.IsFlash = int(U(self.settings.config.contents['SendType'][0]))
        self.ReceiverType = int(U(self.settings.config.contents['Receiver'][0]))
        self.SendDate = float(U(self.settings.config.contents['SendDate'][0]))
        self.SendTime = float(U(self.settings.config.contents['SendTime'][0]))
        self.IsSaveNumbers = U(self.settings.config.contents['IsSaveNumbers'][0])        
        self.IsReceiveReport = int(U(self.settings.config.contents['IsReceiveReport'][0]))
        if self.ReceiverType == 2:
            self.tReceiveNumbers = U(self.settings.config.contents['ReceiveNumber'][0]).replace(u'.0', u'')
        elif self.ReceiverType == 1:
            self.IsManageSended = 0
            self.GetSendedList()
            return
        
        if self.ReceiverType != 0:
            if self.tReceiveNumbers != None and self.tReceiveNumbers != '' and self.tReceiveNumbers != '0':
                self.tMode = 0
            else:
                return
        
        self._SendSMS(self.tMode, self.tReceiveNumbers, self.IsFlash, self.tIsConfig, self.IsSaveNumbers, IsReceiveReport=self.IsReceiveReport)
        #self.Back()

    #高级发送（设置发送选项. source为1表示选择发送，为2表示随机发送，为3表示添加时发送）
    def SendSMSAdvancedReady(self, Source = 1, aList=None):
        if aList == None:
            aList = self.mySMS
            
        self.IsBreak = 1
        self.myForm = SendForm()
        self.myForm.SetActive()
        if self.myForm.IsSaved():
            self.myForm.SaveStatus()
        self.myForm = None
        if Source == 1:
            self.SendSMSReady(Mode=2, aList=aList)
        elif Source == 3:
            self.SendSMSReady(Mode=1, aList=aList)
        elif Source == 2:
            self.RandomSend()

    #发送并保存修改后的短信
    def SendModifySMS(self):
        #self._GetCurrentOption('SendModifySMS')

        self.ModifySMS(0)
        self.SendSMSReady()

    #添加类别
    def AddType(self):
        #self._GetCurrentOption('AddType')

        self.TypeName = Query(U8('请输入类别名称'), 'text')
        if self.TypeName != None:
            self.myType.AppendType(SMSTypeInfo(self.TypeName))
            self.RefreshTypeTab()

    #删除类别
    def RemoveType(self):
        #self._GetCurrentOption('RemoveType')

        if self._SelectType() > 0:
            if Query(U8('确定删除') + self.myType.TypeList[self.SelectedTypeIndex].SMSTypeName + U8('类别吗？')):
                self.myType.RemoveType(self.myType.TypeList[self.SelectedTypeIndex])
                self.RefreshTypeTab()

    #修改类别
    def ModifyType(self):
        #self._GetCurrentOption('ModifyType')

        if self._SelectType() > 0:
            self.TypeName = Query(U8('请输入要修改的类别名称'), 'text', self.myType.TypeList[self.SelectedTypeIndex].SMSTypeName)
            if self.TypeName != None:
                self.myType.ModifyType(self.TypeName, self.SelectedTypeIndex)
                self.RefreshTypeTab()
            #self.ModifyType()
            #return

    #修改类别顺序
    def ModifyOrder(self):
        if self._SelectType() > 0:
            self.TypeOrder = Query(U8('请输入当前类别顺序号'), 'number', self.myType.TypeList[self.SelectedTypeIndex].SMSTypeOrder)
            if self.TypeOrder != None:
                self.myType.ModifyOrder(int(self.TypeOrder), self.SelectedTypeIndex)
                self.RefreshTypeTab()
            
    #为短信酷添加短信
    def AppendSMSReady(self):
        self._strAction = "InsertSMS"
        self.AppendSMS()
    
    #添加短信  
    def AppendSMS(self):
        #self._GetCurrentOption('AppendSMS')

        self.text = appuifw.Text()
        self.text.color = self.Color
        self.text.font = self.Font
        self.text.clear()
        self.text.set_pos(0)
        appuifw.app.set_tabs([],None)
        #self.text.focus = True
        appuifw.app.title = U8('添加短信')
        self.InsertSMS_Menu()
        self.tTimer = e32.Ao_timer()
        self.tTimer.after(0.1, self.CheckKeyForText)

    def CheckKeyForText(self):
        if self.text.get_pos() > 0:
            txt = self.text.get(self.text.get_pos()-1, 1)
            if txt == "0" or txt == "5":
                self.text.delete(self.text.get_pos()-1, 1)

    #保存添加的短信
    def SaveSMS(self, strAction = '', Mode = 1, IsMenu = 0):
        #self._GetCurrentOption('SaveSMS')

        if IsMenu == 0:
            self.SMSContent = UN8(self.text.get().replace(u'\u2029', u'\n'))
        else:
            if strAction == 'SMSHome':
                self.SelectedSMSIndex = self.SMSList.current()
                self.SMSContent = UN8(self.mySMSByHome.SMSList[self.SelectedSMSIndex].SMSContent)
            else:
                self.SMSContent = ''

        if self.SMSContent != '' and self.SMSContent != ' ':
            if self._SelectType(strAction) > 0:
                self.mySMS.AppendSMS(SMSInfo(self.SMSContent, self.myType.TypeList[self.SelectedTypeIndex].SMSTypeID), Mode)
                if strAction != 'SMSHome':
                    self.Back()
                else:
                    self._PreviousOption()

    #发送并添加短信
    def SendSaveSMS(self):
        #self._GetCurrentOption('SendModifySMS')

        self.SaveSMS(Mode=2)
        self.SendSMSReady()

    #存入短信酷（从收件箱）
    def SaveRevertSMS(self):
        self.SelectedTypeIndex = -1
        self.SaveSMS('Revert')
        
    #在添加短信时插入已有短信
    def InsertSMS(self):
        #self._GetCurrentOption('InsertSMS')
        self.SelectedTypeIndex = -1 ##
        self.strAction = 'Revert'
        if self._SelectType(self.strAction) > 0:
            appuifw.app.menu = [(U8('确认'), self.SelectSMSHandler), (U8('返回类别'), self.InsertSMS), (U8('返回主菜单'), self.Back)]
            appuifw.app.exit_key_handler = self.InsertSMS_Menu
            uikludges.set_right_softkey_text(U8("取消"))
            self.SelectedSMSIndex = None
            self.SelectSMS()
            self.DisplaySMS(self.tSMSList[self.tCurrentSMSIndex])

    def InsertSMS_Menu(self):
        self._GetCurrentOption('InsertSMS_Menu')
        appuifw.app.body = self.text
        appuifw.app.title = U8('添加短信')

        if self._strAction != 'InsertSMSHome':
            appuifw.app.menu = [(U8('保存'), self.SaveSMS), (U8('发送'), self.SendSMSReady), (U8('高级发送'), lambda: self.SendSMSAdvancedReady(Source=3)), (U8('发送并保存'), self.SendSaveSMS), (U8('插入短信'), self.InsertSMS), (U8('从收件箱获取'), self.GetInboxSMS), self.InsertContactMenu, (U8('返回主菜单'), self.Back)]
        else:
            appuifw.app.menu = [(U8('保存'), self.SaveSMSHome), (U8('插入短信'), self.InsertSMS), (U8('从收件箱获取'), self.GetInboxSMS), self.InsertContactMenu, (U8('返回主菜单'), self.Back)]
            
        uikludges.set_right_softkey_text(U8("返回"))
        if self._strAction == "InsertSMSHome" and self.mySMSByHome != None:
            appuifw.app.exit_key_handler = self.ListSMSByHome
        else:
            appuifw.app.exit_key_handler = self.Back
        #appuifw.app.exit_key_handler = self.Back
        #appuifw.app.exit_key_handler = self._PreviousOption

    #当选中插入短信时
    def InsertSMS_Click(self):
        self.IsBreak = 1
        self.InsertSMS_Menu()
        self.text.set(self.text.get() + self.mySMS.SMSList[self.SelectedSMSIndex].SMSContent)        
        self.SelectedSMSIndex = None
        
    def GetInboxSMS(self):
        #self._GetCurrentOption('GetInboxSMS')
        
        global Message_Content_Re
        if len(Message_Content_Re) == 0:
            self.SMSInBoxList()
        if Message_Content_Re[self.InBoxList.current()] == '' or Message_Content_Re[self.InBoxList.current()] == ' ':
            return
            
        self.Message_Content_Add = []
        for self.i in range(len(Message_Content_Re)):
            self.Message_Content_Add.append(Message_Content_Re[self.i][1])

        self.SelectedSMSIndex = appuifw.selection_list(choices=self.Message_Content_Add, search_field=0)
        if self.SelectedSMSIndex != None:
            self.text.set(self.text.get() + self.Message_Content_Add[self.SelectedSMSIndex])
        self.Message_Content_Add = []

    #插入联系人的姓名和电话
    def InsertContactNamePhone(self):
        global Contact_Name
        global Contact
        if self._SelectContact('GetPhone') == 1:
            if self.SelectedContactIndex != None:
                self.SelectName = Contact_Name[self.SelectedContactIndex]
                self.SelectNumber = Contact[self.SelectName][:-1].split(',')
                if len(self.SelectNumber) == 1:
                    self.text.set(self.text.get() + self.SelectName + ':' + self.SelectNumber[0])
                else:
                    self.SelectedContactIndex = appuifw.popup_menu(self.SelectNumber, self.SelectName) 
                    if self.SelectedContactIndex >=0:
                        self.text.set(self.text.get() + self.SelectName + ':' + self.SelectNumber[self.SelectedContactIndex])

    #插入联系人的姓名
    def InsertContactName(self):
        global Contact_Name
        if self._SelectContact('GetName') == 1:
            if self.SelectedContactIndex != None:
                self.text.set(self.text.get() + Contact_Name[self.SelectedContactIndex])

    #插入联系人的电话
    def InsertContactPhone(self):
        global Contact_Name
        global Contact
        if self._SelectContact('GetPhone') == 1:
            if self.SelectedContactIndex != None:
                self.SelectName = Contact_Name[self.SelectedContactIndex]
                self.SelectNumber = Contact[self.SelectName][:-1].split(',')
                if len(self.SelectNumber) == 1:
                    self.text.set(self.text.get() + self.SelectNumber[0])
                else:
                    self.SelectedContactIndex = appuifw.popup_menu(self.SelectNumber, self.SelectName) 
                    if self.SelectedContactIndex >=0:
                        self.text.set(self.text.get() + self.SelectNumber[self.SelectedContactIndex])
        
    def ListSMS(self, strAction = u'DisplaySMS', iTypeID=0, strSearchKey=''):
        self._GetCurrentOption(CurrentAction = 'ListSMS', CurParAction = strAction, CurParMode=iTypeID, CurParNumbers=strSearchKey)

        appuifw.app.set_tabs([],None)
        if self._SelectType(strAction) > 0:
            self._strAction = strAction
            if self.SelectSMS(iTypeID=iTypeID, strSearchKey=strSearchKey, strAction=strAction) == 0:
                return
            appuifw.app.menu = self.SMSMenu
            uikludges.set_right_softkey_text(U8("主菜单"))
            appuifw.app.exit_key_handler = self.Back
            
            self.DisplaySMS(self.tSMSList[self.tCurrentSMSIndex])

    def ViewListSMS(self):
        self._ViewListSMS(CurrentSMSIndex=self.SelectedSMSIndex, IsModify=self.ViewOrModify)

    #显示短信内容(查看短信)
    def _ViewListSMS(self, CurrentSMSIndex, IsModify=1):
        self.IsBreak = 1
        self.text = appuifw.Text()
        if self._strAction != u'ListSMSByHome':
            aList = self.mySMS
        else:
            aList = self.mySMSByHome

        if IsModify == 0:
            #绑定右键(查看下一条短信)
            self.text.bind(EKeyLeftArrow, self.ViewPrevSMS)
            #绑定左键(查看上一条短信)
            self.text.bind(EKeyRightArrow, self.ViewNextSMS)
            #绑定C键(删除当前短信)
            self.text.bind(EKeyBackspace, self.RemoveCurrentSMS)
            #绑定OK键(转到编辑模式)
            self.text.bind(EKeySelect, lambda: self._ViewListSMS(CurrentSMSIndex, IsModify=1))
            if self._strAction == u'SendSMS':
                self.text.bind(EKeyYes, lambda: self.SendSMSAdvancedReady(Source=3))
            self._DisplayModifyMenu = (U8('编辑'), lambda: self._ViewListSMS(CurrentSMSIndex, IsModify=1))          
        else:
            #绑定OK键(转到查看模式)
            self.text.bind(EKeySelect, lambda: self._ViewListSMS(CurrentSMSIndex, IsModify=0))
            self._DisplayModifyMenu = (U8('查看'), lambda: self._ViewListSMS(CurrentSMSIndex, IsModify=0))

        tSMSContent = aList.SMSList[CurrentSMSIndex].SMSContent
        tSMSContent = tSMSContent.replace(U8('[顶]'),'')
        tSMSContent = tSMSContent.replace(U8('[精]'),'')        
        self.text.font = self.Font
        self.text.color = self.Color
        self.text.set(tSMSContent)
        #appuifw.app.set_tabs([],None)
        self._back = True
        #self.text.focus = False
        self.text.set_pos(2)
        self.tTimer = e32.Ao_timer()
        self.tTimer.after(0.1, self.CheckKeyForText)
        appuifw.app.body = self.text
        uikludges.set_right_softkey_text(U8("返回"))
        appuifw.app.exit_key_handler = self._PreviousOption
        if self._strAction == u'SendSMS':
            appuifw.app.title = U8('发送短信')
            appuifw.app.menu = [(U8('默认发送'), self.SendSMSReady), (U8('高级发送'), lambda: self.SendSMSAdvancedReady(Source=3)), self._DisplayModifyMenu, (U8('上一条'), self.ViewPrevSMS), (U8('下一条'), self.ViewNextSMS), (U8('保存'), self.ModifySMS), (U8('发送并保存'), self.SendModifySMS), (U8('删除'), self.RemoveCurrentSMS), self.InsertContactMenu, (U8('返回主菜单'), self.Back), self.ExitMenu]
        elif self._strAction == u'Revert':
            appuifw.app.title = U8('回复短信')
            appuifw.app.menu = [(U8('发送'), self.ReSendSMSReady), (U8('发送并保存'), self.ReSendModifySMS), self._DisplayModifyMenu, self.InsertContactMenu, (U8('返回主菜单'), self.Back)]
        elif self._strAction == u'DisplaySMS':
            appuifw.app.title = U8('查看短信')
            appuifw.app.menu = [(U8('保存修改'), self.ModifySMS), self._DisplayModifyMenu, (U8('返回主菜单'), self.Back)]
        elif self._strAction == u'ListSMSByHome':
            appuifw.app.title = U8('发送短信')
            appuifw.app.menu = [(U8('默认发送'), lambda: self.SendSMSReady(aList=self.mySMSByHome)), (U8('高级发送'), lambda: self.SendSMSAdvancedReady(Source=3,aList=self.mySMSByHome)), self._DisplayModifyMenu, (U8('存入短信酷'), self.SaveSMSByHome), (U8('删除'), self.RemoveCurrentSMS_Menu), self.InsertContactMenu, (U8('上一条'), self.ViewPrevSMS), (U8('下一条'), self.ViewNextSMS), (U8('返回主菜单'), self.Back), self.ExitMenu]

    #显示上一条短信
    def ViewPrevSMS(self):
        if self.SelectedSMSIndex > 0:
            self.SelectedSMSIndex -= 1
        self.ViewListSMS()

    #显示下一条短信
    def ViewNextSMS(self):
        if self.SelectedSMSIndex < self.iSMSListLength - 1:
            self.SelectedSMSIndex += 1
        self.ViewListSMS()
        
    #删除当前查看的短信
    def RemoveCurrentSMS(self):
        if self.SelectedSMSIndex != None:
            if Query(U8('确定删除该短信吗？')):
                if self._strAction != u'ListSMSByHome':
                    self.mySMS.RemoveSMS(self.mySMS.SMSList[self.SelectedSMSIndex])
                else:
                    self.Running(U8('正在删除，请稍后...'))
                    self.mySMSByHome.RemoveSMS(self.mySMSByHome.SMSList[self.SelectedSMSIndex], aUserID=self.UserID, aUserCheckCode=self.UserCheckCode, aSMSInfoID=self.mySMSByHome.SMSList[self.SMSList.current()].SMSInfoID)
                    self.IsFinish = 1
                
                self._PreviousOption()

    #从短信列表中删除选中的短信
    def RemoveCurrentSMS_Menu(self):
        self.SelectedSMSIndex = self.SMSList.current()
        self.RemoveCurrentSMS()
        self.SelectedSMSIndex = None
        
    #修改当前查看的短信
    def ModifySMS(self, Mode=1):
        #self._GetCurrentOption('ModifySMS', Mode)

        self.SMSContent = UN8(self.text.get().replace(u'\u2029', u'\n'))
        if self.SMSContent != '':
            self.mySMS.ModifySMS(self.SMSContent, self.SelectedSMSIndex, Mode)
            if Mode == 1:
                self._PreviousOption()
    

    #列出类别并获取当前选中的类别
    def _SelectType(self, strAction = ''):
        #self._GetCurrentOption('_SelectType', CurParAction=strAction)

        if strAction == 'Revert' or strAction == 'SMSHome':
            if not self.SelectedTypeIndex >= 0:
                appuifw.app.title = U8('选择类别')
                self.myType.LoadType()
                self.SelectedTypeIndex = appuifw.selection_list(choices=self.myType.GetTypeNameList(), search_field=1)
                if self.SelectedTypeIndex == None:
                    if strAction != 'SMSHome':
                        self.Back()
                    else:
                        self._PreviousOption()
                #uikludges.set_right_softkey_text(U8("主菜单"))
                #appuifw.app.exit_key_handler = self.Back
        else:    
            self.SelectedTypeIndex = self.TypeList.current()
            
        if self.SelectedTypeIndex >= 0:
            return 1
        else:
            return 0



    #列出选中类别的短信并获取当前选中的短信
    def SelectSMS(self, iTypeID=0, strSearchKey='', strAction = u'DisplaySMS'):
        self.strCondition = ""
        strSearchKey =strSearchKey.replace("'", "''")
        #print iTypeID,',',strSearchKey
        if iTypeID != -1 and self.SelectedTypeIndex != None and self.SelectedTypeIndex >= 0:
            self.strCondition += " WHERE SMSTypeID=" + str(self.myType.TypeList[self.SelectedTypeIndex].SMSTypeID)
            if strSearchKey != "":
                self.strCondition += " AND SMSContent LIKE '*" + strSearchKey + "*'"
        else:
            if strSearchKey != "":
                self.strCondition += " WHERE SMSContent LIKE '*" + strSearchKey + "*'"

        self.mySMS = SMSList()
        self.mySMS.LoadSMS(self.strCondition)
        appuifw.app.title = self.myType.TypeList[self.SelectedTypeIndex].SMSTypeName
        return self._SelectSMS(strAction=strAction, iTypeID=iTypeID, strSearchKey=strSearchKey, a0Handler=self.AppendSMSReady)

    #显示短信列表
    def _SelectSMS(self, aList=None, aLeftHandler=None, aRightHandler=None, a0Handler=None, a2Handler=None, a4Handler=None, a6Handler=None, a8Handler=None, aStarHandler=None, aHashHandler=None, strAction = u'DisplaySMS', iTypeID=0, strSearchKey=''):
        #self._GetCurrentOption('_SelectSMS')
        if aList == None:
            self._GetCurrentOption(CurrentAction = '_SelectSMS', CurParAction = strAction, CurParMode=iTypeID, CurParNumbers=strSearchKey)
        else:
            self._GetCurrentOption(CurrentAction = 'ListSMSByHome')

        if aList == None:
            aList = self.mySMS
            
        tList = aList.GetSMSContentList()
        tListBox = ScreenList(aList=tList, aClickListBoxHandler=self.SelectSMSHandler, aRemoveHandler=self.RemoveCurrentSMS_Menu, aYesHandler=self.SendSMSAdvancedReady, aRetractHandler=self.DisplaySMS, aLeftHandler=aLeftHandler, aRightHandler=aRightHandler, a0Handler=a0Handler, a2Handler=a2Handler, a4Handler=a4Handler, a6Handler=a6Handler, a8Handler=a8Handler, aStarHandler=aStarHandler, aHashHandler=aHashHandler)
        self.SMSList = tListBox.MyListBox
        self.iSMSListLength = tListBox.iListLength
        self.tSMSList = tList

        if self.iSMSListLength == 0:
            Msg(U8('没有短信'))
            if self._strAction == "InsertSMS" or self._strAction == "InsertSMSHome":
                self.InsertSMS()
            else:
                self.Back()
            return 0
        
        self.tCurrentSMSIndex = 0
        if self.SelectedSMSIndex != 0 and self.SelectedSMSIndex != None:
            self.SMSList.set_list(self.tSMSList, self.SelectedSMSIndex)
            self.tCurrentSMSIndex = self.SelectedSMSIndex
        
        appuifw.app.body = self.SMSList

        try:
            self.text.focus = False
        except:
            pass

        return self.iSMSListLength

    #点击短信菜单时
    def SelectSMSHandler(self):
        self.SelectedSMSIndex = self.SMSList.current()
        if self._strAction == "InsertSMS" or self._strAction == "InsertSMSHome":
            self.InsertSMS_Click()
        else:
            self.ViewListSMS()


    #列出名片夹中的所有联系人并获取选中联系人的电话
    def _SelectContact(self, strAction = '', IsView = 1):
        #self._GetCurrentOption('_SelectContact')

        global Contact
        global Contact_Name
        self.SelectName = ''
        self.SelectNumber = []
        self.ReceiveNumbers = ''
        
        if len(Contact) == 0:
            Msg(U8('正在读取名片夹，请稍后...'))
            if self.dbContacts == None:
                self.dbContacts = contacts.open()

            for self.i in self.dbContacts:
                self.objContact = self.dbContacts[self.i]
                self.ContactName = ''
                self.ContactNumber = ''
                self.ContactName = self.objContact.title
                self.fields = self.objContact.find(type='mobile_number')
                if len(self.fields) > 0:
                    #print self.fields[0].value
                    for self.i in self.fields:
                        if self.i.value != '': 
                            self.ContactNumber += self.i.value + ','
                self.fields = self.objContact.find(type='phone_number')
                if len(self.fields) > 0:
                    #print self.fields[0].value
                    for self.i in self.fields:
                        if self.i.value != '': 
                            self.ContactNumber += self.i.value + ','
                if self.ContactNumber != '':
                    if not Contact.has_key(self.ContactName):
                        Contact[self.ContactName] = self.ContactNumber
                        Contact_Name.append(self.ContactName)
                    else:
                        Contact[self.ContactName+'('+self.ContactNumber+')'] = self.ContactNumber
                        Contact_Name.append(self.ContactName+'('+self.ContactNumber+')')

        if len(Contact) == 0:
            Msg(U8('您的名片夹没有联系人！'))
            return ''

        #如果IsView为0则表示不显示联系人选择列表
        if IsView == 0:
            return

        if strAction != '':
            self.SelectedContactIndex = appuifw.selection_list(choices=Contact_Name, search_field=1)
            return 1
            
        self.SelectedContactIndex = appuifw.multi_selection_list(choices=Contact_Name, style='checkbox', search_field=1)
        if len(self.SelectedContactIndex) > 0:
            for self.k in self.SelectedContactIndex:
                self.SelectName = Contact_Name[self.k]
                self.SelectNumber = Contact[self.SelectName][:-1].split(',')
                if len(self.SelectNumber) == 1:
                    self.ReceiveNumbers += self.SelectNumber[0] + ','
                else:
                    self.SelectedContactIndex = appuifw.popup_menu(self.SelectNumber, self.SelectName) 
                    if self.SelectedContactIndex >=0:
                        self.ReceiveNumbers += self.SelectNumber[self.SelectedContactIndex] + ','

        return self.ReceiveNumbers[:-1]

    #获取指定号码的联系人姓名
    def _FindNameByContact(self, strNumber):
        global Contact
        self.strFindName = strNumber
        if len(Contact) != 0:
            try:
                for self.i in range(len(Contact.values())):
                    if (','+str(Contact.values()[self.i])).find(','+str(strNumber)+',') != -1:
                        self.strFindName =  Contact.keys()[self.i]
                    elif (','+str(Contact.values()[self.i])).find(',+86'+str(strNumber)+',') != -1:
                        self.strFindName =  Contact.keys()[self.i]
            except:
                None
        return self.strFindName

    #查找联系人
    def SearchNameByNumber(self):
        strNumber = Query(U8('请输入联系人号码：'), 'text')
        self._SelectContact(IsView = 0)
        strGetName = self._FindNameByContact(strNumber)
        if strGetName == strNumber:
            Msg(U8('没有找到该联系人'), 1)
        else:
            #ViewLongInfo(U8('找到的联系人：\n'), strGetName)
            Query(U8('找到的联系人：\n'), 'text', strGetName)

    #查找电话号码
    def SearchNumberByName(self):
        global Contact
        strName = Query(U8('请输入联系人姓名：'), 'text')
        self._SelectContact(IsView = 0)
        if Contact.has_key(strName):
            strNumber = Contact[strName]
            if strNumber.endswith(','):
                strNumber = strNumber[:-1]
        else:
            strNumber = None
        if strNumber == None:
            Msg(U8('没有找到该联系人'), 1)
        else:
            #ViewLongInfo(U8('找到的号码：\n'), strNumber)
            Query(U8('找到的号码：\n'), 'text', strNumber)


    #发送短信
    def _SendSMS(self, Mode=1, ReceiveNumbers='', IsFlash=0, IsConfig=0, IsSaveNumbers=1, IsSendedNumbers='0', IsReceiveReport=0):
        global IsFP3
        #self._GetCurrentOption('_SendSMS', Mode, '' ,ReceiveNumbers)
        if Mode == 1:
            self.ReceiveNumbers = self._SelectContact()
        else:
            self.ReceiveNumbers = ReceiveNumbers

        if self.ReceiveNumbers.endswith(','):
            self.ReceiveNumbers = self.ReceiveNumbers[:-1]
        if self.ReceiveNumbers == '' or self.ReceiveNumbers == '0':
            return
        self.ReceiveNumberList = self.ReceiveNumbers.split(',')
        self.CountReceiveNumber = len(self.ReceiveNumberList)
        #self.Back()
        if self.CountReceiveNumber > 0:
            if Query(U8('确认后开始发送短信！')):
                Msg(U8('正在发送，请稍后...'))
                
                self.SendSMSContent = self.SendSMSContent.replace(U8('[顶]'),'')
                self.SendSMSContent = self.SendSMSContent.replace(U8('[精]'),'')        

                #如果不是定时短信
                if IsConfig == 0 or self.IsSend == 0:
                    for self.RNumber in self.ReceiveNumberList:
                        if len(self.SendSMSContent) > 130:
                            XYsms.chg_sms_send(self._FindNameByContact(self.RNumber), self.RNumber, self.SendSMSContent[:130], IsFlash, u'', IsReceiveReport)
                            XYsms.chg_sms_send(self._FindNameByContact(self.RNumber), self.RNumber, self.SendSMSContent[131:], IsFlash, u'', IsReceiveReport)
                        else:
                            XYsms.chg_sms_send(self._FindNameByContact(self.RNumber), self.RNumber, self.SendSMSContent, IsFlash, u'', IsReceiveReport)
                        #e32.ao_sleep(0.05)
                else:
                    if IsFP3 == 0:
                        self.tDate = time.localtime(self.SendDate + 1*24*60*60)
                    else:
                        self.tDate = time.localtime(self.SendDate - 1*8*60*60)
                    self.tTime = time.localtime(self.SendTime)
                    self.tDateTime = str(self.tDate.tm_year) + Str2(self.tDate.tm_mon-1) + Str2(self.tDate.tm_mday-1) + ":" + Str2(self.tTime.tm_hour) + Str2(self.tTime.tm_min) + Str2(self.tTime.tm_sec)
                    #print self.tDateTime
                    for self.RNumber in self.ReceiveNumberList:
                        if len(self.SendSMSContent) > 130:
                            XYsms.chg_sms_send(self._FindNameByContact(self.RNumber), self.RNumber, self.SendSMSContent[:130], IsFlash, U(self.tDateTime), IsReceiveReport)
                            XYsms.chg_sms_send(self._FindNameByContact(self.RNumber), self.RNumber, self.SendSMSContent[131:], IsFlash, U(self.tDateTime), IsReceiveReport)
                        else:
                            XYsms.chg_sms_send(self._FindNameByContact(self.RNumber), self.RNumber, self.SendSMSContent, IsFlash, U(self.tDateTime), IsReceiveReport)
                        #e32.ao_sleep(0.05)
                        
                Msg(U8('短信已经加入发件箱，系统会自动发送！'), 1)
        else:
            Msg(U8('发送失败！'), 1)

        #保存号码组（0表示提示保存号码组）
        if IsSaveNumbers == 0 and IsSendedNumbers == '0' and self.CountReceiveNumber > 1:
            if Query(U8('是否保存已发送的号码到号码组？')):
                self.strSendedName = Query(U8('请给该号码组启一个名称'), 'text')
                if self.strSendedName != None:
                    self.mySended.AppendSended(SendedNumbersInfo(self.strSendedName, self.ReceiveNumbers))

    #获取收件箱中的短信
    def _GetMessage(self, Mode=1):
        #self._GetCurrentOption('_GetMessage', Mode)
        Msg(U8('正在读取收件箱的短信，请稍后...'))
        #global Message_Content_Add
        global Message_Content_Re
            
        self.iIndex = -1
        
        if len(Message_Content_Re) == 0:
            self.Messages = Inbox()
            self.MessageIDs = self.Messages.sms_messages()
            for self.mID in self.MessageIDs:
                try:
                    self.t = (self.Messages.address(self.mID), self.Messages.content(self.mID))
                    Message_Content_Re.append(self.t)
                except:
                    pass
                    
                #Message_Content_Add.append(self.Messages.content(self.mID))

        if len(Message_Content_Re) == 0:
            Message_Content_Re.append(u' ')
            #Message_Content_Re = [(u'test1',u'This is Test1 Content!'),(u'test2',u'This is Test2 Content!'),(u'test3',u'This is Test3 Content!')]

        return len(Message_Content_Re)

    #加载主菜单收件箱的短信列表
    def SMSInBoxList(self):
        #self._GetCurrentOption('SMSInBoxList')
        self._GetMessage()
        tList = Message_Content_Re
        tListBox = ScreenList(tList, self.InBoxHandler)
        self.InBoxList = tListBox.MyListBox
        self.iInBoxListLength = tListBox.iListLength

    #当点击收件箱的短信时
    def InBoxHandler(self):
        if Message_Content_Re[self.InBoxList.current()] == '' or Message_Content_Re[self.InBoxList.current()] == ' ':
            return
        
        self.text = appuifw.Text()
        self.text.color = self.Color
        self.text.font = self.Font
        self.text.set(Message_Content_Re[self.InBoxList.current()][1])
        self.text.set_pos(0)
        appuifw.app.set_tabs([],None)
        #self.text.focus = True
        appuifw.app.title = U8('查看短信')
        appuifw.app.body = self.text
        appuifw.app.menu = [(U8('随机回复'), self.ReRandomSend), (U8('选择回复'), self.ReSelectSend), (U8('自建回复'), self.ReAppendSend), (U8('存入短信酷'), self.SaveRevertSMS), (U8('返回'), self._PreviousOption)]
        uikludges.set_right_softkey_text(U8("主菜单"))
        appuifw.app.exit_key_handler = self.Back


    #加载主菜单类别列表
    def SMSTypeList(self):
        #self._GetCurrentOption('SMSTypeList')

        self.myType.LoadType()
        tList = self.myType.GetTypeNameList()
        tListBox = ScreenList(tList, self.SMSTypeHandler, self.RemoveType, a0Handler=self.AppendSMSReady)
        self.TypeList = tListBox.MyListBox
        self.iTypeListLength = tListBox.iListLength

    #刷新类别标签
    def RefreshTypeTab(self):
        self.SMSTypeList()
        appuifw.app.body = self.TypeList
        self.__bgMain = appuifw.app.body
        #self._GetCurrentOption('Main')

    #点击类别列表时
    def SMSTypeHandler(self):
        #Msg(u'Current Type='+str(self.TypeList.current()))
        if self.iTypeListLength == 0:
            return 
        #appuifw.app.set_tabs([],None)
        self.SelectSend()


    #显示号码组列表
    def GetSendedList(self):
        self._GetCurrentOption('GetSendedList')
        self._SendedList()
        appuifw.app.set_tabs([],None)
        appuifw.app.body = self.SendedList
        if self.IsManageSended != 1:
            appuifw.app.title = U8("选择号码组")
            appuifw.app.menu = self.SendedMenu_Send
        else:
            appuifw.app.title = U8("管理号码组")
            appuifw.app.menu = self.SendedMenu_Manage            
        uikludges.set_right_softkey_text(U8("主菜单"))
        appuifw.app.exit_key_handler = self.Back


    #加载号码组列表
    def _SendedList(self):
        self.mySended.LoadSended()
        tList = self.mySended.GetSendedNameList()
        tListBox = ScreenList(tList, self.SendedHandler, self.RemoveSended)
        self.SendedList = tListBox.MyListBox
        self.iSendedListLength = tListBox.iListLength

    #点击号码组列表时
    def SendedHandler(self):
        if self.IsManageSended != 1:
            self.SendSendedNumbers()
        else:
            self.ViewSended()

    #删除号码组
    def RemoveSended(self):
        if self.iSendedListLength == 0:
            return
        if self.SendedList.current() >= 0:
            if Query(U8('确定删除') + self.mySended.SendedList[self.SendedList.current()].SendedName + U8('吗？')):
                self.mySended.RemoveSended(self.mySended.SendedList[self.SendedList.current()])
                self.RefreshSendedList()

    #查看号码组
    def ViewSended(self):
        if self.iSendedListLength == 0:
            return
        self._GetCurrentOption('ViewSended')
        self.SelectedSendedIndex = self.SendedList.current()
        self.text = appuifw.Text()
        self.text.set(self.mySended.SendedList[self.SelectedSendedIndex].SendedNumbers)
        appuifw.app.title = self.mySended.SendedList[self.SelectedSendedIndex].SendedName
        appuifw.app.body = self.text
        uikludges.set_right_softkey_text(U8("返回"))
        appuifw.app.exit_key_handler = self._PreviousOption
        if self.IsManageSended != 1:
            appuifw.app.menu = [(U8('发送'), self.SendAndSaveSended), (U8('删除'), self.RemoveSended), (U8('返回主菜单'), self.Back)]
        else:
            appuifw.app.menu = [(U8('保存'), self.ModifySendedNumbers), (U8('删除'), self.RemoveSended), (U8('返回主菜单'), self.Back)]

    #添加号码组
    def AddSended(self):
        self.ReceiveNumbers = self._SelectContact()
        self.strSendedName = Query(U8('请给该号码组起一个名称'), 'text')
        if self.strSendedName != None:
            self.mySended.AppendSended(SendedNumbersInfo(self.strSendedName, self.ReceiveNumbers))
            self.RefreshSendedList()
        
    
    #刷新号码组列表
    def RefreshSendedList(self):
        self._SendedList()
        appuifw.app.body = self.SendedList

    #发送选中的号码组(Mode为1是发送选中的号码组，为2是发送修改后的号码组）
    def SendSendedNumbers(self, Mode=1):
        if self.iSendedListLength == 0:
            return
        if Mode == 1:
            self.tReceiveNumbers = self.mySended.SendedList[self.SendedList.current()].SendedNumbers
        else:
            self.tReceiveNumbers = self.text.get().replace(u'\u2029', u'')
        Mode = 0
        #print 1,self.IsReceiveReport
        self._SendSMS(Mode, self.tReceiveNumbers, self.IsFlash, self.tIsConfig, self.IsSaveNumbers, IsSendedNumbers='1', IsReceiveReport=self.IsReceiveReport)
        self.SelectedSendedIndex = None

    #发送并保存修改后的号码组
    def SendAndSaveSended(self):
        self.SendSendedNumbers(Mode=2)
        self.ModifySendedNumbers(Mode=2)
        
    #修改号码组(号码)
    def ModifySendedNumbers(self, Mode=1):
        if self.iSendedListLength == 0:
            return
        self.SendedNumbers = self.text.get().replace(u'\u2029', u'')
        if self.SendedNumbers != '':
            self.mySended.ModifySendedNumbers(self.SendedNumbers, self.SendedList.current(), Mode)
            if Mode == 1:
                self._PreviousOption()

    #修改号码组(名称)
    def ModifySendedName(self, Mode=1):
        if self.iSendedListLength == 0:
            return
        if self.SendedList.current() >= 0:
            self.SendedName = Query(U8('请输入要修改的号码组名称'), 'text', self.mySended.SendedList[self.SendedList.current()].SendedName)
            if self.SendedName != None:
                self.mySended.ModifySendedName(self.SendedName, self.SendedList.current())
                self.RefreshSendedList()


    #修改号码组顺序
    def ModifyOrderBySended(self, Mode=1):
        if self.iSendedListLength == 0:
            return
        if self.SendedList.current() >= 0:
            self.SendedOrder = Query(U8('请输入当前号码组顺序号'), 'number', self.mySended.SendedList[self.SendedList.current()].SendedOrder)
            if self.SendedOrder != None:
                self.mySended.ModifyOrderBySended(int(self.SendedOrder), self.SendedList.current())
                self.RefreshSendedList()

    #号码组管理
    def ManageSended(self):
        self.IsManageSended = 1
        self.GetSendedList()


    #切换选项卡
    def HandleTab(self, index):
        if self.IsLogined == 0:
            if index == 0:
                self.TabIndex = 1
            if index == 1:
                self.TabIndex = 2
        else:
            if index == 0:
                self.TabIndex = 3
            if index == 1:
                self.TabIndex = 1
            if index == 2:
                self.TabIndex = 2

        if self.TabIndex == 1:
            appuifw.app.menu = self.TypeMenu
            appuifw.app.body = self.TypeList
        elif self.TabIndex == 2:
            if len(Message_Content_Re) == 0:
                self.SMSInBoxList()
            appuifw.app.menu = self.InBoxMenu
            appuifw.app.body = self.InBoxList
        elif self.TabIndex == 3:
            appuifw.app.menu = self.HomeTypeMenu
            appuifw.app.body = self.HomeTypeList
            
        self.__menuMain = appuifw.app.menu
        self.__bgMain = appuifw.app.body
        #self._GetCurrentOption('Main')
        self._index = index
        self.SelectedSMSIndex = None
        
    #获取回复人的手机号
    def _GetReceiveNumber(self):
        #self._GetCurrentOption('_GetReceiveNumber')

        global Message_Content_Re
       
        self.ReceiveName = Message_Content_Re[self.InBoxList.current()][0]
        #self.ReceiveName = u'chg'
        if self.ReceiveName == '':
            return ''
        #Msg(U8('收件人：') + self.ReceiveName)
        self.ReceiveNumbers = ''
        self.ContactName = ''
        self.ContactNumber = ''
        
        if self.dbContacts == None:
            self.dbContacts = contacts.open()
        self.foundContact = self.dbContacts.find(self.ReceiveName)
        if len(self.foundContact) <= 0:
            #Msg(self.ReceiveName)
            self.ReceiveNumbers = self.ReceiveName
            if self.ReceiveNumbers != None:
                return self.ReceiveNumbers
            else:
                return ''
        elif len(self.foundContact) > 1:
            #self.SelectedContactIndex = 0
            self.tName = []
            for self.i in self.foundContact:
                self.tNumber = ''
                if len(self.i.find(type='mobile_number')) > 0:
                    self.tNumber += self.i.find(type='mobile_number')[0].value + ','
                if len(self.i.find(type='phone_number')) > 0:
                    self.tNumber += self.i.find(type='phone_number')[0].value + ','
                self.tName.append(self.ReceiveName + '(' + self.tNumber + ')')
            self.SelectedContactIndex = appuifw.popup_menu(self.tName, U8('请选择收件人'))
        elif len(self.foundContact) == 1:
            self.SelectedContactIndex = 0

        if self.SelectedContactIndex >= 0:
            self.fields = self.foundContact[self.SelectedContactIndex].find(type='mobile_number')
            if len(self.fields) > 0:
                for self.i in self.fields:
                    if self.i.value != '': 
                        self.ContactNumber += self.i.value + ','
            self.fields = self.foundContact[self.SelectedContactIndex].find(type='phone_number')
            if len(self.fields) > 0:
                for self.i in self.fields:
                    if self.i.value != '': 
                        self.ContactNumber += self.i.value + ','

            #Msg(U8('收件人号码为：')+self.ContactNumber)
            self.SelectNumber = self.ContactNumber[:-1].split(',')
            if len(self.SelectNumber) == 1:
                self.ReceiveNumbers = self.SelectNumber[0] + ','
            else:
                self.SelectedContactIndex = appuifw.popup_menu(self.SelectNumber, self.ReceiveName) 
                if self.SelectedContactIndex >=0:
                    self.ReceiveNumbers = self.SelectNumber[self.SelectedContactIndex] + ','

            return self.ReceiveNumbers[:-1]
        else:
            return ''

    #记录当前操作
    def _GetCurrentOption(self, CurrentAction='', CurParMode=1, CurParAction='', CurParNumbers=''):
        self._PreviousAction = self._CurrentAction
        self._PreParMode = self._CurParMode
        self._PreParAction = self._CurParAction
        self._PreParNumbers = self._CurParNumbers
        self._CurrentAction = CurrentAction
        self._CurParMode = CurParMode
        self._CurParAction = CurParAction
        self._CurParNumbers = CurParNumbers
        """
        p = u'1 - PreviousAction='+self._PreviousAction+u', PreParMode='+str(self._PreParMode)+u', PreParAction='+self._PreParAction+u', PreParNumbers='+str(self._PreParNumbers)
        c = u'1 - CurrentAction='+CurrentAction+u', CurParMode='+str(CurParMode)+u', CurParAction='+CurParAction+u', CurParNumbers='+str(CurParNumbers)
        Query(u'Pre', 'text', p);
        Query(u'Cur', 'text', c);
        """

    #返回前一个操作
    def _PreviousOption(self):
        """
        p = u'2 - PreviousAction='+self._PreviousAction+u', PreParMode='+str(self._PreParMode)+u', PreParAction='+self._PreParAction+u', PreParNumbers='+str(self._PreParNumbers)
        c = u'2 - CurrentAction='+self._CurrentAction+u', CurParMode='+str(self._CurParMode)+u', CurParAction='+self._CurParAction+u', CurParNumbers='+str(self._CurParNumbers)
        Query(u'Pre', 'text', p);
        Query(u'Cur', 'text', c);
        """
        if self._PreviousAction == '':
            return
        elif self._PreviousAction == 'ListSMS':
            self.ListSMS(strAction=self._PreParAction, iTypeID=self._PreParMode, strSearchKey=self._PreParNumbers)
        elif self._PreviousAction == 'ListSMSByHome':
            self.ListSMSByHome()
        elif self._PreviousAction == '_SelectType':
            self._SelectType(self._PreParAction)
        elif self._PreviousAction == '_SelectSMS':
            #self._SelectSMS()
            self.ListSMS(strAction=self._PreParAction, iTypeID=self._PreParMode, strSearchKey=self._PreParNumbers)
        elif self._PreviousAction == 'Back':
            self.Back()
        elif self._PreviousAction == 'GetSendedList':
            self.GetSendedList()


    #返回主菜单
    def Back(self):
        self._GetCurrentOption(CurrentAction='Back')
        
        appuifw.app.menu = self.__menuMain
        appuifw.app.body = self.__bgMain
        appuifw.app.title = self.__titleMain
        try:
            uikludges.set_right_softkey_text(U8("退出"))
        except:
            pass
        appuifw.app.exit_key_handler = self.Exit
        if self.IsLogined == 0:
            appuifw.app.set_tabs([U8('类别'), U8('收件箱')], self.HandleTab)
        else:
            appuifw.app.set_tabs([U8('基地'), U8('类别'), U8('收件箱')], self.HandleTab)

        if self.IsLogined == 1:
            if self.TabIndex == 1:
                self._index = 1
            if self.TabIndex == 2:
                self._index = 2
            if self.TabIndex == 3:
                self._index = 0
        appuifw.app.activate_tab(self._index)
        self._back = False
        self.SelectedSMSIndex = None
        self.IsBreak = 1
        self.IsManageSended = 0
        self.IsFinish = 1
        try:
            self.text.focus = False
        except:
            pass

    #导入短信
    def ImportData(self):
        global ExportSMSTypeName
        self.tSMS = []
        self.iMode = 0
        self.iTypeOrder = 0
        if os.path.isfile(self.DataFile):
            #Msg(self.DataFile)
            self.f = open(self.DataFile, 'r')
            try:
                self.tSMS = MyPickle().load(self.f)
            finally:
                self.f.close()
            #print len(self.tSMS)
            if len(self.tSMS) > 0:
                Msg(U8('正在导入短信，时间可能较长，请稍后...'))
                ExportSMSTypeName = ''
                for self.i in self.tSMS:
                    #print U8(ExportSMSTypeName), U8(self.i.SMSTypeName)
                    if ExportSMSTypeName != self.i.SMSTypeName:
                        ExportSMSTypeName = self.i.SMSTypeName
                        self.iMode = 1
                        self.iTypeOrder += 1
                    else:
                        self.iMode = 2
                    self.iVar = self.mySMS.ImportSMS(SMSExInfo(self.i.SMSContent, self.i.SMSTypeName), self.iMode, self.iTypeOrder)
                    if self.iVar == -101:
                        ExportSMSTypeName = ''

                self.RefreshTypeTab()
                Msg(U8('导入成功！'))
                self.tSMS = None
            else:
                Msg(U8('没有可以导入的短信！'))
        else:
            Msg(U8('SMSData.txt不存在！'))

    #导出短信
    def ExportData(self):
        Msg(U8('正在导出短信，请稍后...'))
        self.f = open(self.DataFile, 'w')
        self.mySMS.LoadAllSMS()
        #print self.mySMS
        MyPickle().dump(self.mySMS, self.f)
        self.f.close()
        Msg(U8('导出成功！'))


    #查询短信（全部类别）
    def SearchSMSByAllType(self):
        strSearchKey = Query(U8('请输入要查询短信的关键词'), 'text')
        if strSearchKey != None:
            self.ListSMS(iTypeID=-1, strSearchKey=strSearchKey)

    #查询短信（当前类别）
    def SearchSMSByCurrentType(self):
        strSearchKey = Query(U8('请输入要查询短信的关键词'), 'text')
        if strSearchKey != None:
            self.ListSMS(iTypeID=0, strSearchKey=strSearchKey)

    #滚动显示短信内容
    def DisplaySMS(self, SMSContent):
        self.IsBreak = 1
        self.tTimer = e32.Ao_timer()
        self.tTimer.after(0.2, lambda:self._DisplaySMS(SMSContent))

    def _DisplaySMS(self, SMSContent):
        self.IsBreak = 0
        DisplaySMSInfo = u'      ' + SMSContent + u'  '
        img = Image.new((180, 16))
        fg = fgimage.FGImage()

        i = 0
        while i < len(DisplaySMSInfo):
            img.clear((0, 0, 0))
            img.text((0, 14), DisplaySMSInfo[i:], 0xffffff, 'dense')
            fg.set(0, 28, img._bitmapapi())
            e32.ao_sleep(0.2)
            if self.IsBreak == 1:
                break
            i += 1
        fg.unset()


    def handle_redraw(rect1=None, rect2=None):
        if GlobalImage != None:
            GlobalCanvas.blit(GlobalImage)

    #程序运行中
    def Running(self, ViewInfo=None):
        global GlobalCanvas
        global GlobalImage
        if ViewInfo == None:
            ViewInfo = U8('运行中！请稍后...')
        appuifw.app.set_tabs([],None)
        appuifw.app.menu = [(U8('返回主菜单'), self.Back)]
        try:
            uikludges.set_right_softkey_text(U8("取消"))
        except:
            pass
        appuifw.app.exit_key_handler = self.Cancel
        self.IsFinish = 0
        strFontColor = 0x0000ff
        appuifw.app.body = GlobalCanvas = appuifw.Canvas(redraw_callback = self.handle_redraw)
        GlobalImage = Image.new((176,144))
        GlobalImage.clear()
        GlobalImage.text((40,60), ViewInfo, strFontColor, 'dense')
        GlobalCanvas.blit(GlobalImage)
        self.rTimer = e32.Ao_timer()
        self.rTimer.after(self.TimeOut, self.Stop)


    #取消
    def Cancel(self, IsViewInfo=1):
        self.IsFinish = 1
        self.Conn.CloseConnect()
        self.Back()

    #停止
    def Stop(self, IsViewInfo=1):
        if self.IsFinish == 0:
            self.IsFinish = 1
            self.Conn.CloseConnect()
            if IsViewInfo == 1:
                Msg(U8('程序超时！'))
            self.Back()

    #显示帮助文档
    def Help(self, HelpName=u'ImportExport'):
        if HelpName == '' or HelpName == None:
            return
        global HelpPath
        self.HelpPath = HelpPath + HelpName + u'.txt'
        self.HelpContent = MyPickle().Read(self.HelpPath)
        #Msg(self.HelpContent)
        self.text = appuifw.Text()
        self.text.bind(EKeyLeftArrow, self.Help_GoPervPage)
        self.text.bind(EKeyRightArrow, self.Help_GoNextPage)
        self.text.color = self.Color
        #self.text.font = self.Font
        self.text.set(self.HelpContent)
        self.text.set_pos(0)
        appuifw.app.set_tabs([],None)
        #self.text.focus = False
        appuifw.app.title = U8('查看帮助')
        appuifw.app.body = self.text
        appuifw.app.menu = [(U8('导入/导出短信'), self.Help), (U8('默认/高级发送'), lambda: self.Help(u'DefaultAdvanced'))]
        uikludges.set_right_softkey_text(U8("主菜单"))
        appuifw.app.exit_key_handler = self.Back
        self.HelpContent = None

    def Help_GoNextPage(self):
        self.article_length = self.text.len()
        self.cursor_pos = self.text.get_pos()
        if self.cursor_pos < self.article_length:
            self.text.set_pos(min(self.cursor_pos+100, self.article_length))

    def Help_GoPervPage(self):
        self.article_length = self.text.len()
        self.cursor_pos = self.text.get_pos()
        if self.cursor_pos > 0:
            self.text.set_pos(max(self.cursor_pos-100, 0))


    #登录基地
    def Login(self):
        global Ver
        if self.Conn == None:
            self.Conn = ConnServer()
        self.Conn.GetConnString(IsReGet=1)
        if self.Conn.IsAutoLogin != 0:
            try:
                UserID,Password = appuifw.multi_query(U8('用户ID:'),U8('密码:'))
            except:
                return
        else:
            UserID = self.Conn.DefaultUserID
            Password = self.Conn.DefaultPassword
        if UserID != None:
            #Msg(UserID + ',' + Password)
            re = 2
            while re > 0:
                self.Running(U8('正在登录，请稍后...'))
                query = urllib.urlencode({'UserID':UN8(UserID), 'UserPassword':UN8(Password), 'Ver':UN8(str(Ver))})
                headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
                self.Conn.BeginConnect()
                iRet = self.Conn.RequestConn('POST', self.Conn.Server + u'/Login.asp', query, headers)
                if iRet == -1:
                    Msg(U8('连接服务器失败'))
                    self.Back()
                    
                RetValue = self.Conn.ReadRequest()
                iRet = self.Conn.CheckReturnValue(RetValue)
                self.IsFinish = 1
                if(iRet < 0):
                    Msg(self.Conn.ErrorInfo)
                    self.Conn.CloseConnect()
                    self.Back()
                    break
                else:
                    try:
                        if len(RetValue) > 60:
                            re = re - 1
                            self.Conn.CloseConnect()
                            if re < 1:
                                Msg(U8('登录失败，稍后请重试.'))
                                self.Back()
                            else:
                                e32.ao_sleep(1)
                                continue
                        else:
                            self.Running(U8('正在获取基地版块'))
                            self.UserID = UserID
                            val = RetValue.split("_")
                            self.UserCheckCode = val[0]
                            self.UserType = int(val[1])
                            self.GetSMSHomeType()
                            break
                    except:
                        self.Conn.CloseConnect()
                        Msg(U8('登录失败，稍后请重试..'))
                        self.Back()
                        break

    #手动注册
    def SelfRegister(self):
        if self.Conn == None:
            self.Conn = ConnServer()
        UserName,Password = appuifw.multi_query(U8('昵称:'),U8('密码:'))
        if UserName != None:
            re = 2
            while re > 0:
                self.Running(U8('正在注册，请稍后...'))
                query = urllib.urlencode({'UserName':UN8(UserName), 'UserPassword':UN8(Password)})
                headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
                self.Conn.BeginConnect()
                iRet = self.Conn.RequestConn('POST', self.Conn.Server + u'/register.asp', query, headers)
                if iRet == -1:
                    Msg(U8('连接服务器失败'))
                    self.Back()
                RetValue = self.Conn.ReadRequest()
                iRet = self.Conn.CheckReturnValue(RetValue)
                self.IsFinish = 1
                if(iRet < 0):
                    re = 0
                    Msg(self.Conn.ErrorInfo)
                    self.Conn.CloseConnect()
                    try:
                        self.SelfRegister()
                    except:
                        pass
                    self.Back()
                    break
                else:
                    try:
                        if len(RetValue) > 60:
                            re = re - 1
                            self.Conn.CloseConnect()
                            if re < 1:
                                Msg(U8('注册失败，稍后请重试'))
                                self.Back()
                            else:
                                e32.ao_sleep(1)
                                continue
                        else:
                            #显示注册信息
                            self.DisplayRegisterInfo(RetValue)
                            self.Conn.CloseConnect()
                            break
                    except:
                        self.Conn.CloseConnect()
                        Msg(U8('注册失败，稍后请重试'))
                        self.Back()
                        break
       
    #自动注册
    def AutoRegister(self):
        if self.Conn == None:
            self.Conn = ConnServer()
            
        re = 2
        while re > 0:
            self.Running(U8('正在注册，请稍后...'))
            self.Conn.BeginConnect()
            iRet = self.Conn.RequestConn('GET', self.Conn.Server + u'/register.asp')
            if iRet == -1:
                Msg(U8('连接服务器失败'))
                self.Back()
            RetValue = self.Conn.ReadRequest()
            iRet = self.Conn.CheckReturnValue(RetValue)
            self.IsFinish = 1
            #print RetValue;
            if(iRet < 0):
                Msg(self.Conn.ErrorInfo)
                self.Conn.CloseConnect()
                self.Back()
                break
            else:
                try:
                    if len(RetValue) > 60:
                        re = re - 1
                        self.Conn.CloseConnect()
                        if re < 1:
                            Msg(U8('注册失败，稍后请重试'))
                            self.Back()
                        else:
                            e32.ao_sleep(1)
                            continue
                    else:
                        #显示注册信息
                        self.DisplayRegisterInfo(RetValue)
                        self.Conn.CloseConnect()
                        break
                except:
                    self.Conn.CloseConnect()
                    Msg(U8('注册失败，稍后请重试'))
                    self.Back()
                    break

    #显示注册信息
    def DisplayRegisterInfo(self, RetValue):
        global ConfigPathBySystem
        
        UserInfo = RetValue.split('|')
        if len(UserInfo) != 4:
            Msg(U8('注册失败:') + UserInfo)
            self.Conn.CloseConnect()
            self.Back()
        else:
            self.UserID = UserInfo[0]
            self.UserName = UserInfo[1]
            self.UserPassword = UserInfo[2]
            self.UserCheckCode = UserInfo[3]

        #保存用户ID和密码
        self.settings = Settings()
        self.settings.LoadSystemConfig(ConfigPathBySystem)
        try:
            self.settings.config.contents['DefaultUserID'][0] = self.UserID
        except:
            self.settings.config.contents['DefaultUserID'].append(self.UserID)
        try:
            self.settings.config.contents['DefaultPassword'][0] = self.UserPassword
        except:
            self.settings.config.contents['DefaultPassword'].append(self.UserPassword)
        self.settings.SaveConfig()
            
        strFontColor = 0x0000ff
        appuifw.app.body = canvas = appuifw.Canvas()
        ImageInfo = Image.new((176,144))
        ImageInfo.clear()
        ImageInfo.text((60,30),U8('注册成功！'), strFontColor, 'dense')
        ImageInfo.text((55,60),U8('用户ID: ' + self.UserID), strFontColor, 'dense')
        ImageInfo.text((55,90),U8('密  码: ' + self.UserPassword), strFontColor, 'dense')
        ImageInfo.text((55,120),U8('昵  称: ' + self.UserName), strFontColor, 'dense')
        canvas.blit(ImageInfo)
        appuifw.app.title = self.HomeName
        appuifw.app.set_tabs([],None)
        uikludges.set_right_softkey_text(U8("登录"))
        appuifw.app.exit_key_handler = self.GetSMSHomeType
        appuifw.app.menu = [(U8('登录基地'), self.GetSMSHomeType), (U8('返回主菜单'), self.Back)]
    
    #获取短信基地类别
    def GetSMSHomeType(self):
        self.Conn.BeginConnect()
        iRet = self.Conn.RequestConn('GET', self.Conn.Server + u'/GetSMSType.asp?UserID=' + self.UserID + '&CheckCode=' + self.UserCheckCode)
        if iRet == -1:
            Msg(U8('连接服务器失败'))
            self.Back()
        
        RetValue = self.Conn.ReadRequest()
        iRet = self.Conn.CheckReturnValue(RetValue)
        if(iRet < 0):
            Msg(self.Conn.ErrorInfo)
            self.IsFinish = 1
            self.Conn.CloseConnect()
        else:
            #基地版块菜单
            self.HomeTypeMenu = [ \
                (U8('添加短信'), self.AddSMSByHome), \
                (U8('精华短信'), lambda:self.GetSMSByHome(aIsGood=1)), \
                (U8('个人短信'), lambda:self.GetSMSByHome(aIsUser=1)), \
                (U8('当前版块查询'), self.SearchHomeByCurrent), \
                (U8('修改昵称'), self.ModifyUserName), \
                (U8('帮助'), (self.HelpMenu)), \
                self.OtherMenu, \
                self.ExitMenu, \
            ]
            self.ListHomeType(U8(RetValue))
            self.__menuMain = self.HomeTypeMenu
            self.__bgMain = self.HomeTypeList
            self.TabIndex = 3
            self.IsLogined = 1
            self.IsFinish = 1
            self.mySMSByHome = None
            self.Conn.CloseConnect()
            self.Back()

    #点击基地列表时
    def SMSHomeHandler(self):
        if self.iHomeTypeListLength == 0:
            return 
        self.GetSMSByHome()

    #获取基地版块列表
    def ListHomeType(self, RetValue):
        #Msg(RetValue)
        tList = RetValue.split(',')
        tListBox = ScreenList(aList=tList, aClickListBoxHandler=self.SMSHomeHandler, aRemoveHandler=self.RemoveSMSHome, a0Handler=self.AddSMSByHome, a2Handler=self.SearchHomeByCurrent, aStarHandler=lambda:self.GetSMSByHome(aIsGood=1), aHashHandler=lambda:self.GetSMSByHome(aIsUser=1))
        self.HomeTypeList = tListBox.MyListBox
        self.tHomeTypeList = tList
        self.iHomeTypeListLength = tListBox.iListLength

    #修改昵称
    def ModifyUserName(self):
        strUserName = Query(U8('请输入要修改的昵称'), 'text')
        if strUserName != None:
            self.Running(U8('正在修改，请稍后...'))

            query = urllib.urlencode({'UserID':UN8(self.UserID), 'CheckCode':UN8(self.UserCheckCode), 'UserName':UN8(strUserName), 'Action':u'UserName'})
            headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
            self.Conn.BeginConnect()
            iRet = self.Conn.RequestConn('POST', self.Conn.Server + u'/UpdateUser.asp', query, headers)
            if iRet == -1:
                Msg(U8('连接服务器失败'))
                self.Back()
            
            RetValue = self.Conn.ReadRequest()
            iRet = self.Conn.CheckReturnValue(RetValue)
            self.IsFinish = 1
            if(iRet < 0):
                Msg(self.Conn.ErrorInfo)
            else:
                Msg(U8('修改成功！'))
                self.UserName = strUserName
                
            self.Conn.CloseConnect()
            self.Back()
        

    #删除选中的基地版块
    def RemoveSMSHome(self):
        pass

    #查询当前版块的短信
    def SearchHomeByCurrent(self):
        strSearchKey = Query(U8('请输入要查询短信的关键词'), 'text')
        if strSearchKey != None:
            self.PageByHome = 1
            self.SearchKey = strSearchKey
            self.GetSMSByPage(aPage=self.PageByHome, aSearchKey=self.SearchKey, aIsGood=self.IsGood, aIsUser=self.IsUser)

    #获取基地版块指定页的短信
    def GetSMSByPage(self, aPage=1, aSearchKey=None, aIsGood=0, aIsUser=0):
        global Ver
        self.IsBreak = 1
        self.Conn.BeginConnect()
        if aSearchKey != None:
            strSearch = u'&SearchKey=' + aSearchKey
        else:
            strSearch = u''

        tTypeID = str(int(self.tHomeTypeList[self.HomeTypeList.current()][:2]))

        strQuery = u'?Page=' + str(aPage) + u'&UserID=' + self.UserID + u'&CheckCode=' + self.UserCheckCode + u'&TypeID=' + tTypeID + u'&IsGood=' + str(aIsGood) + u'&IsUser=' + str(aIsUser) + '&Ver=' + str(Ver) + strSearch
        self.Running(U8('正在获取，请稍后...'))
        iRet = self.Conn.RequestConn('GET', UN8(self.Conn.Server + u'/ListSMS.asp' + strQuery))
        if iRet == -1:
            Msg(U8('连接服务器失败'))
            self.Back()
        
        RetValue = self.Conn.ReadRequest()
        self.Conn.CloseConnect()
        iRet = self.Conn.CheckReturnValue(RetValue)
        self.IsFinish = 1
        if(iRet < 0):
            Msg(self.Conn.ErrorInfo)
            self.Cancel()
            return
        else:
            self.mySMSByHome = SMSListByHome()
            self.mySMSByHome.LoadSMS(U8(RetValue))
            
            self.ListSMSByHome()
        

    #获取选中基地版块的短信
    def GetSMSByHome(self, aIsGood=0, aIsUser=0):
        self.PageByHome = 1
        self.SearchKey = None
        self.IsGood = aIsGood
        self.IsUser = aIsUser
        self.GetSMSByPage(aPage=self.PageByHome, aSearchKey=self.SearchKey, aIsGood=self.IsGood, aIsUser=self.IsUser)

    #获取下一页的短信
    def GetNextSMSByHome(self):
        if self.PageByHome >= self.mySMSByHome.MaxPage:
            self.PageByHome = self.mySMSByHome.MaxPage
            return
        self.GetSMSByPage(aPage=self.PageByHome + 1, aSearchKey=self.SearchKey, aIsGood=self.IsGood, aIsUser=self.IsUser)
        self.PageByHome = self.PageByHome + 1

    #获取上一页的短信
    def GetPervSMSByHome(self):
        if self.PageByHome <= 1:
            self.PageByHome = 1
            return
        self.GetSMSByPage(aPage=self.PageByHome - 1, aSearchKey=self.SearchKey, aIsGood=self.IsGood, aIsUser=self.IsUser)
        self.PageByHome = self.PageByHome - 1

    #转到某页
    def GoPageByHome(self):
        page = Query(U8('请输入要转到的页号'), 'number', 1)
        if page != None:
            if page < 1:
                self.PageByHome = 1
            elif page > self.mySMSByHome.MaxPage:
                self.PageByHome = self.mySMSByHome.MaxPage
            else:
                self.PageByHome = page
                
            self.GetSMSByPage(aPage=self.PageByHome, aSearchKey=self.SearchKey, aIsGood=self.IsGood, aIsUser=self.IsUser)
        

    #列出短信基地的短信
    def ListSMSByHome(self):
        self._GetCurrentOption(CurrentAction = 'ListSMSByHome')

        if self.UserType > 1:
            t4Handler = lambda: self.OptionSMS(Action='Good')
            t6Handler = lambda: self.OptionSMS(Action='Top')
        else:
            t4Handler = lambda: None
            t6Handler = lambda: None

        #基地短信菜单
        self.HomeSMSMenu = [ \
            (U8('默认发送'), lambda: self.SendSMSReady(Mode=2, aList=self.mySMSByHome)), \
            (U8('高级发送'), lambda: self.SendSMSAdvancedReady(Source=1,aList=self.mySMSByHome)), \
            (U8('管理短信'), ( \
                (U8('加精'), t4Handler), \
                (U8('置顶'), t6Handler), \
                (U8('删除'), self.RemoveCurrentSMS_Menu), \
            )), \
            (U8('添加短信'), self.AddSMSByHome), \
            (U8('存入短信酷'), lambda:self.SaveSMSByHome(IsMenu=1)), \
            (U8('上一页'), self.GetPervSMSByHome), \
            (U8('下一页'), self.GetNextSMSByHome), \
            (U8('转到某页'), self.GoPageByHome), \
            (U8('短信信息'), self.ViewSMSInfoByHome), \
            (U8('返回主菜单'), self.Back), \
            self.ExitMenu, \
        ]

        self._strAction = u'ListSMSByHome'
        appuifw.app.set_tabs([],None)
        appuifw.app.menu = self.HomeSMSMenu
        appuifw.app.title = self.tHomeTypeList[self.HomeTypeList.current()][3:]
        uikludges.set_right_softkey_text(U8("主菜单"))
        appuifw.app.exit_key_handler = self.Back
            
        self._SelectSMS(aList=self.mySMSByHome, aLeftHandler=self.GetPervSMSByHome, aRightHandler=self.GetNextSMSByHome, a0Handler=self.AddSMSByHome, a2Handler=self.GetSMSByHome, a4Handler=t4Handler, a6Handler=t6Handler, a8Handler=self.GoPageByHome, aStarHandler=self.ViewSMSInfoByHome, aHashHandler=lambda:self.SaveSMSByHome(IsMenu=1))
        tSMS = self.mySMSByHome.SMSList[self.tCurrentSMSIndex]
        tSMSContent = U8('')
        tSMSContent = tSMSContent + self.tSMSList[self.tCurrentSMSIndex]
        #self.DisplaySMS('[' + self.mySMSByHome.SMSList[self.tCurrentSMSIndex].UserName + ']' + self.tSMSList[self.tCurrentSMSIndex])
        self.DisplaySMS(tSMSContent)
        
    #加精(Action=Good - 加精，Action=Top - 置顶)
    def OptionSMS(self, Action):
        self.Running(U8('正在操作，请稍后...'))

        SMSInfoID = str(self.mySMSByHome.SMSList[self.SMSList.current()].SMSInfoID)
        query = urllib.urlencode({'UserID':UN8(self.UserID), 'CheckCode':UN8(self.UserCheckCode), 'SMSInfoID':UN8(SMSInfoID), 'Action':UN8(Action)})
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
        self.Conn.BeginConnect()
        iRet = self.Conn.RequestConn('POST', self.Conn.Server + u'/OptionSMS.asp', query, headers)
        if iRet == -1:
            Msg(U8('连接服务器失败'))
            self.Back()
        
        RetValue = self.Conn.ReadRequest()
        iRet = self.Conn.CheckReturnValue(RetValue)
        self.IsFinish = 1
        if(iRet < 0):
            Msg(self.Conn.ErrorInfo)
        else:
            Msg(U8('操作成功！'))
            
        self.Conn.CloseConnect()
        self._PreviousOption()

    #给短信基地添加短信
    def AddSMSByHome(self):
        self._strAction = u'InsertSMSHome'
        self.AppendSMS()

    #把添加的短信存入短信基地
    def SaveSMSHome(self):
        self.Running(U8('正在提交，请稍后...'))
        
        TypeID = str(int(self.tHomeTypeList[self.HomeTypeList.current()][:2]))
        SMSContent = self.text.get().replace(u'\u2029', u'\n')
        
        query = urllib.urlencode({'UserID':UN8(self.UserID), 'CheckCode':UN8(self.UserCheckCode), 'TypeID':UN8(TypeID), 'SMSContent':UN8(SMSContent)})
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
        self.Conn.BeginConnect()
        iRet = self.Conn.RequestConn('POST', self.Conn.Server + u'/AddSMS.asp', query, headers)
        if iRet == -1:
            Msg(U8('连接服务器失败'))
            self.Back()
        
        RetValue = self.Conn.ReadRequest()
        iRet = self.Conn.CheckReturnValue(RetValue)
        self.IsFinish = 1
        if(iRet < 0):
            Msg(self.Conn.ErrorInfo)
        else:
            Msg(U8('添加成功！'))
            
        self.Conn.CloseConnect()
        if self.mySMSByHome != None:
            self.ListSMSByHome()
        else:
            self.Back()
        
    #把当前短信基地的短信存入短信酷(是否从菜单存入短信酷)
    def SaveSMSByHome(self, IsMenu=0):
        self.SelectedTypeIndex = -1
        self.SaveSMS(strAction='SMSHome', Mode=1, IsMenu=IsMenu)
        
    #查看选中短信的相关信息
    def ViewSMSInfoByHome(self):
        tSMS = self.mySMSByHome.SMSList[self.SMSList.current()]
        title = U8('短信信息')
        msg = U8('用户：') + tSMS.UserName + ','
        msg = msg + U8('ID：') + str(tSMS.UserID) + ','
        msg = msg + U8('位置：') + str(self.PageByHome) + U8('页 ') + str(self.SMSList.current() + 1) + U8('条,')
        msg = msg + U8('总数：') + str(self.mySMSByHome.MaxPage) + U8('页 ') + str(12 * self.mySMSByHome.MaxPage) + U8('条,')
        msg = msg + U8('职称：') + tSMS.UserLevelName + ','
        msg = msg + U8('积分：') + str(tSMS.UserScore) + ','
        msg = msg + U8('添加短信：') + str(tSMS.AddSMSNumber) + U8('条')
        ViewLongInfo(title, msg)
        
    #保存修改后的短信（短信基��）
    def ModifySMSByHome(self):
        pass

    
    #退出
    def Exit(self):
        global IsEmulator
        
        if self.IsExitQuery == 1 or Query(U8('退出系统？')):
            appuifw.app.set_tabs([],None)
            self.IsBreak = 1
            self.app_lock.signal()
            if not IsEmulator == 1:
                pass
                #appuifw.app.set_exit()

    #关于
    def About(self):
        self.AboutInfo = [U8('作者：逍遥(SMSStore)'),U8('合作伙伴：ZNTX、UCWEB'),u'http://hi.baidu.com/SMSStore/',u'http://wap.8zntx.com/',u'          2008-4-7 4:19']
        self.AboutIndex = appuifw.popup_menu(self.AboutInfo, U8('短信酷_v0.86'))
        
if __name__ == '__main__':
    SMSScreen()

        
