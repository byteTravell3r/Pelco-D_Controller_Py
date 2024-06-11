#!/usr/bin/python3

import sys, warnings, time
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QThread, QObject, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PELCO_QT import Ui_MainWindow
from PELCO_CMD import PELCOD_CMD

warnings.filterwarnings("ignore", category=DeprecationWarning)

class GET_POS_THREAD(QThread):
    HPOS_TRIGGER = pyqtSignal()
    VPOS_TRIGGER = pyqtSignal()
    UPDATE_TRIGGER = pyqtSignal()

    def run(self):
        while True:
            self.HPOS_TRIGGER.emit()
            time.sleep(0.02)
            self.VPOS_TRIGGER.emit()
            time.sleep(0.02)
            self.UPDATE_TRIGGER.emit()
            time.sleep(0.02)

class PELCO_FOR_GUI(PELCOD_CMD, QObject):
    FRAME = [0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    RFRAME = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    COM_BUSY_SIGNAL = pyqtSignal()

    def SEND_CMD(self, ADDR, VERB, PAR1=0x00, PAR2=0x00, ONESHOT=False):
        self.FRAME = [0xFF, ADDR, 0x00, VERB, PAR1, PAR2, 0x00]
        self.FRAME[6] = sum(self.FRAME, -0xFF) % 0x100
        return 0
    
    def SEND_TO_COM(self):
        if (self.FRAME != [0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]):
            self.COM_BUSY_SIGNAL.emit()
            for BYTE in self.FRAME:
                self.SERIAL.write(BYTE.to_bytes(1, 'big'))
            if self.DEBUG:
                print(self.COLOR.DEBUG + f"{self.COM_PORT} [", end='')
                for BYTE in self.FRAME:
                    print('{:0>2X}'.format(BYTE), end='')
                print("]" + self.COLOR.CLEAR)
            self.FRAME = [0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        return 0

    def QUERY_ANGLE(self, DIR):
        FRAME_TMP = self.FRAME
        match DIR:
            case "H": self.SEND_CMD(self.ADDR, 0x51, ONESHOT=False)
            case "V": self.SEND_CMD(self.ADDR, 0x53, ONESHOT=False)
        self.SEND_TO_COM()
        self.FRAME = FRAME_TMP
        try:
            self.RFRAME = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            self.RFRAME[0] = int(self.SERIAL.read().hex(), 16)
            if (self.RFRAME[0] != 0xFF):
                print("READ FAIL")
                return 1
            self.RFRAME[1] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[2] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[3] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[4] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[5] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[6] = int(self.SERIAL.read().hex(), 16)
            if self.RFRAME[6] != (sum(self.RFRAME) - 0xFF - self.RFRAME[6]) % 0x100:
                print("CHECKSUM FAIL")
                return 1
            HEX_STRING = '{:0>2X}'.format(self.RFRAME[4]) + '{:0>2X}'.format(self.RFRAME[5])
            if DIR == "H": self.HPOS = int(HEX_STRING, 16)
            if DIR == "V": self.VPOS = int(HEX_STRING, 16)
        except:
            print(f"{self.COM_PORT} READ TIMEOUT")

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.PELCO = PELCO_FOR_GUI()
        if (self.PELCO.SET_SERIAL(self.PELCO.COM_PORT) != "COM OPEN OK"):
            self.PELCO.OPEN_COM_INTERACTIVE()
        self.PELCO.OPEN_COM()
        
        self.PELCO.USE_CMD = False
        
        self.DPAD_SIGNALS_CONNECT()
        self.COM_SIGNAL_CONNECT()
        self.AUX_SIGNAL_CONNECT()
        self.SET_STYLE()

        self.PELCO.QUERY_ANGLE("V")
        self.SLIDER_V_POS.setValue(self.PELCO.VPOS)
        self.PELCO.QUERY_ANGLE("H")
        self.SLIDER_H_POS.setValue(self.PELCO.HPOS)

    def DPAD_SIGNALS_CONNECT(self):
        def MV_UP(): self.PELCO.MOVE("UP")
        def MV_DN(): self.PELCO.MOVE("DN")
        def MV_LT(): self.PELCO.MOVE("LT")
        def MV_RT(): self.PELCO.MOVE("RT")
        def MV_UPLT(): self.PELCO.MOVE("UPLT")
        def MV_UPRT(): self.PELCO.MOVE("UPRT")
        def MV_DNLT(): self.PELCO.MOVE("DNLT")
        def MV_DNRT(): self.PELCO.MOVE("DNRT")
        def MV_STOP(): self.PELCO.MOVE("STOP")
        self.BTN_UP.clicked.connect(MV_UP)
        self.BTN_DN.clicked.connect(MV_DN)
        self.BTN_LT.clicked.connect(MV_LT)
        self.BTN_RT.clicked.connect(MV_RT)
        self.BTN_UPLT.clicked.connect(MV_UPLT)
        self.BTN_UPRT.clicked.connect(MV_UPRT)
        self.BTN_DNLT.clicked.connect(MV_DNLT)
        self.BTN_DNRT.clicked.connect(MV_DNRT)
        self.BTN_STOP.clicked.connect(MV_STOP)

    def COM_SIGNAL_CONNECT(self):
        def GET_VPOS():
            if not (self.BTN_STOP.isChecked()):
                self.PELCO.QUERY_ANGLE("V")
                self.SLIDER_V_POS.setValue(self.PELCO.VPOS)
        def GET_HPOS():
            if not (self.BTN_STOP.isChecked()):
                self.PELCO.QUERY_ANGLE("H")
                self.SLIDER_H_POS.setValue(self.PELCO.HPOS)

        def SET_H_POS():
            self.PELCO.SET_ANGLE("H", self.SLIDER_H_POS.value())
            # self.BTN_STOP.click()
        def SET_V_POS():
            self.PELCO.SET_ANGLE("V", self.SLIDER_V_POS.value())
            # self.BTN_STOP.click()

        self.BTN_SET_V_POS.clicked.connect(SET_V_POS)
        self.BTN_SET_H_POS.clicked.connect(SET_H_POS)

        self.SYNCIO = GET_POS_THREAD()
        self.SYNCIO.start()
        self.SYNCIO.UPDATE_TRIGGER.connect(self.PELCO.SEND_TO_COM)
        self.SYNCIO.VPOS_TRIGGER.connect(GET_VPOS)
        self.SYNCIO.HPOS_TRIGGER.connect(GET_HPOS)

    def closeEvent(self, event):
        self.PELCO.MOVE("STOP")
        self.PELCO.SEND_TO_COM()

    def AUX_SIGNAL_CONNECT(self):
        def UPDATE_FRAME():
            self.FRAME_0.display('{:0>2X}'.format(self.PELCO.FRAME[0]))
            self.FRAME_1.display('{:0>2X}'.format(self.PELCO.FRAME[1]))
            self.FRAME_2.display('{:0>2X}'.format(self.PELCO.FRAME[2]))
            self.FRAME_3.display('{:0>2X}'.format(self.PELCO.FRAME[3]))
            self.FRAME_4.display('{:0>2X}'.format(self.PELCO.FRAME[4]))
            self.FRAME_5.display('{:0>2X}'.format(self.PELCO.FRAME[5]))
            self.FRAME_6.display('{:0>2X}'.format(self.PELCO.FRAME[6]))

            self.RFRAME_0.display('{:0>2X}'.format(self.PELCO.RFRAME[0]))
            self.RFRAME_1.display('{:0>2X}'.format(self.PELCO.RFRAME[1]))
            self.RFRAME_2.display('{:0>2X}'.format(self.PELCO.RFRAME[2]))
            self.RFRAME_3.display('{:0>2X}'.format(self.PELCO.RFRAME[3]))
            self.RFRAME_4.display('{:0>2X}'.format(self.PELCO.RFRAME[4]))
            self.RFRAME_5.display('{:0>2X}'.format(self.PELCO.RFRAME[5]))
            self.RFRAME_6.display('{:0>2X}'.format(self.PELCO.RFRAME[6]))
                
        self.PELCO.COM_BUSY_SIGNAL.connect(UPDATE_FRAME)
        pass
        
    def SAVE_COM_PORT(self):
        LINE_COMPORT = "    COM_PORT = \""
        
        with open("./PELCO_CON.py", 'r') as CODE:
            CODE_LIST = CODE.readlines()
        for LINE in CODE_LIST:
            print(LINE, end='')
            if LINE_COMPORT in LINE:
                LINE_NUM = CODE_LIST.index(LINE)
                pass
                break

    def SET_STYLE(self):
        def addShadowEffect(widget, offset, opacity):
            SHADOW = QGraphicsDropShadowEffect()
            SHADOW.setColor(QColor(0, 0, 0, opacity))
            SHADOW.setBlurRadius(0)
            SHADOW.setOffset(offset, offset)
            widget.setGraphicsEffect(SHADOW)

        for OBJECT in self.findChildren(QtWidgets.QLCDNumber):
            addShadowEffect(OBJECT, 3, 128)
        
        for OBJECT in self.findChildren(QtWidgets.QSlider) + self.findChildren(QtWidgets.QGroupBox):
            addShadowEffect(OBJECT, 2, 96)

        addShadowEffect(self.LBL_COM, 1, 128)
        addShadowEffect(self.LBL_PELCO, 1, 128)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    # window.SAVE_COM_PORT()
    window.show()
    app.exec()

