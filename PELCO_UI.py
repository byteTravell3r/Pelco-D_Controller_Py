import sys, warnings, time
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from PELCO_QT import Ui_MainWindow
from PELCO_CMD import PELCOD_CMD

warnings.filterwarnings("ignore", category=DeprecationWarning)

class GET_POS_THREAD(QThread):
    HPOS_TRIGGER = pyqtSignal()
    VPOS_TRIGGER = pyqtSignal()
    UPDATE_TRIGGER = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setTerminationEnabled(True)

    def run(self):
        while True:
            self.UPDATE_TRIGGER.emit()
            time.sleep(0.02)
            self.HPOS_TRIGGER.emit()
            time.sleep(0.02)
            self.VPOS_TRIGGER.emit()
            time.sleep(0.02)

class PELCO_FOR_GUI(PELCOD_CMD):
    FRAME = [0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    RFRAME = [0x00, 0x00, 0x00, 0x00, 0x00]

    def SEND_CMD(self, ADDR, VERB, PAR1=0x00, PAR2=0x00, ONESHOT=False):
        self.FRAME = [0xFF, ADDR, 0x00, VERB, PAR1, PAR2, 0x00]
        self.FRAME[6] = sum(self.FRAME, -0xFF) % 0x100
        return 0
    
    def SEND_TO_COM(self):
        if self.FRAME != [0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] :
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
            self.RFRAME = [0x00, 0x00, 0x00, 0x00, 0x00]
            RX_HEAD = int(self.SERIAL.read().hex(), 16)
            if (RX_HEAD != 0xFF):
                return "READ FAIL"

            self.RFRAME[0] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[1] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[2] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[3] = int(self.SERIAL.read().hex(), 16)
            self.RFRAME[4] = int(self.SERIAL.read().hex(), 16)
            RX_CSUM = int(self.SERIAL.read().hex(), 16)
            if RX_CSUM != sum(self.RFRAME) % 0x100:
                return "CHECKSUM FAIL"
            
        except:
            return f"{self.COM_PORT} READ TIMEOUT"

        HEX_STRING = '{:0>2X}'.format(
            self.RFRAME[3]) + '{:0>2X}'.format(self.RFRAME[4])

        if DIR == "H":
            self.HPOS = int(HEX_STRING, 16)
        if DIR == "V":
            self.VPOS = int(HEX_STRING, 16)
        return 0



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
        self.POS_SIGNAL_CONNECT()
        self.AUX_SIGNAL_CONNECT()
        self.SYNCIO.start()

    def DPAD_SIGNALS_CONNECT(self):
        def RELEASE_DPAD_BTNS():
            for BTN in self.DPAD_GRID.findChildren(QtWidgets.QPushButton):
                BTN.setChecked(False)

        MV = self.PELCO.MOVE

        def MV_UP():
            MV("UP")
            RELEASE_DPAD_BTNS()
            self.BTN_UP.setChecked(True)
        def MV_DN():
            MV("DN")
            RELEASE_DPAD_BTNS()
            self.BTN_DN.setChecked(True)
        def MV_LT():
            MV("LT")
            RELEASE_DPAD_BTNS()
            self.BTN_LT.setChecked(True)
        def MV_RT():
            RELEASE_DPAD_BTNS()
            self.BTN_RT.setChecked(True)
            MV("RT")
        def MV_UPLT():
            RELEASE_DPAD_BTNS()
            self.BTN_UPLT.setChecked(True)
            MV("UPLT")
        def MV_UPRT():
            RELEASE_DPAD_BTNS()
            self.BTN_UPRT.setChecked(True)
            MV("UPRT")
        def MV_DNLT():
            RELEASE_DPAD_BTNS()
            self.BTN_DNLT.setChecked(True)
            MV("DNLT")
        def MV_DNRT():
            RELEASE_DPAD_BTNS()
            self.BTN_DNRT.setChecked(True)
            MV("DNRT")
        def MV_STOP():
            RELEASE_DPAD_BTNS()
            self.BTN_STOP.setChecked(True)
            MV("STOP")

        self.BTN_UP.clicked.connect(MV_UP)
        self.BTN_DN.clicked.connect(MV_DN)
        self.BTN_LT.clicked.connect(MV_LT)
        self.BTN_RT.clicked.connect(MV_RT)
        self.BTN_UPLT.clicked.connect(MV_UPLT)
        self.BTN_UPRT.clicked.connect(MV_UPRT)
        self.BTN_DNLT.clicked.connect(MV_DNLT)
        self.BTN_DNRT.clicked.connect(MV_DNRT)
        self.BTN_STOP.clicked.connect(MV_STOP)

    def POS_SIGNAL_CONNECT(self):
        def GET_VPOS():
            if not (self.BTN_STOP.isChecked()):
                self.PELCO.QUERY_ANGLE("V")
                self.BAR_V_POS.setValue(self.PELCO.VPOS)
        def GET_HPOS():
            if not (self.BTN_STOP.isChecked()):
                self.PELCO.QUERY_ANGLE("H")
                self.BAR_H_POS.setValue(self.PELCO.HPOS)
        def SET_H_POS():
            self.PELCO.SET_ANGLE("H", self.SLIDER_H_POS.value())
            self.BAR_H_POS.setValue(self.SLIDER_H_POS.value())
        def SET_V_POS():
            self.PELCO.SET_ANGLE("V", self.SLIDER_V_POS.value())
            self.BAR_V_POS.setValue(self.SLIDER_V_POS.value())

        self.BTN_SET_V_POS.clicked.connect(SET_V_POS)
        self.BTN_SET_H_POS.clicked.connect(SET_H_POS)

        self.SYNCIO = GET_POS_THREAD()
        
        self.SYNCIO.UPDATE_TRIGGER.connect(self.PELCO.SEND_TO_COM)
        self.SYNCIO.VPOS_TRIGGER.connect(GET_VPOS)
        self.SYNCIO.HPOS_TRIGGER.connect(GET_HPOS)

    def closeEvent(self, event):
        self.PELCO.MOVE("STOP")
        self.PELCO.SEND_TO_COM()

    def AUX_SIGNAL_CONNECT(self):
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

