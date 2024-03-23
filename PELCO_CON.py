import serial, signal, sys, time

class PelcoD_Controller():
    
    def __init__(self):
        self.ADDR = 0x01
        self.INST = 0x00
        self.HSPD = 0xFF
        self.VSPD = 0xFF
        self.HPOS = [0x00, 0x00]
        self.VPOS = [0x00, 0x00]
        self.COM_PORT = "COM6"
        self.USE_CMD = False

    def SET_SERIAL(self, COM):
        self.COM_PORT = COM
        try: self.SERIAL = serial.Serial(self.COM_PORT, 9600, timeout=0.05)
        except: return "COM OPEN FAILED"
        self.CLOSE_COM()
        return "COM OPEN OK"

    def MOVE(self, ACTION):
        match ACTION:
            case "STOP": self.INST = 0x00
            case "UP"  : self.INST = 0x08
            case "DN"  : self.INST = 0x10
            case "RT"  : self.INST = 0x02
            case "LT"  : self.INST = 0x04
            case "UPRT": self.INST = 0x0A
            case "UPLT": self.INST = 0x0C
            case "DNRT": self.INST = 0x12
            case "DNLT": self.INST = 0x14
            case ""    : self.INST = 0x00
            case _     : return "INVALID COMMAND"

        return self.SEND_CMD(self.ADDR, self.INST, self.HSPD, self.VSPD)
    
    def GOTO(self, DIR, ANGLE):
        if ANGLE < 0x00: ANGLE = 0x00
        match DIR:
            case "H": 
                if ANGLE > 0x863E: ANGLE = 0x863E
                self.HPOS = [int(ANGLE % 0x100), int(ANGLE / 0x100)]
                return self.SEND_CMD(self.ADDR, 0x4B, self.HPOS[0], self.HPOS[1])
            case "V":
                if ANGLE > 0x863E: ANGLE = 0x863E
                self.VPOS = [int(ANGLE % 0x100), int(ANGLE / 0x100)]
                return self.SEND_CMD(self.ADDR, 0x4D, self.VPOS[0], self.VPOS[1])
            case _  : return "INVALID COMMAND"

    def QUERY_ANGLE(self, DIR):
        match DIR:
            case "H": RET = self.SEND_CMD(self.ADDR, 0x51, ONESHOT=False)
            case "V": RET = self.SEND_CMD(self.ADDR, 0x53, ONESHOT=False)
            case _  :
                return "INVALID COMMAND"
        if RET != 0:
            return RET
        
        try:
            RX_HEAD = int(self.SERIAL.read().hex(), 16)
            if (RX_HEAD != 0xFF):
                return "READ FAIL"
            RFRAME = [0x00, 0x00, 0x00, 0x00, 0x00]
            RFRAME[0] = int(self.SERIAL.read().hex(), 16)
            RFRAME[1] = int(self.SERIAL.read().hex(), 16)
            RFRAME[2] = int(self.SERIAL.read().hex(), 16)
            RFRAME[3] = int(self.SERIAL.read().hex(), 16)
            RFRAME[4] = int(self.SERIAL.read().hex(), 16)
            RX_CSUM   = int(self.SERIAL.read().hex(), 16)
            if RX_CSUM != sum(self.RFRAME) % 0x100:
                return "CHECKSUM FAIL"
        except:
            return "READ TIMEOUT"

        if DIR == "H": self.HPOS = [RFRAME[3], RFRAME[4]]
        if DIR == "V": self.VPOS = [RFRAME[3], RFRAME[4]]

        if self.USE_CMD:
            print(f"{DIR}_POSITION:", '{:0>2X}'.format(RFRAME[3]), '{:0>2X}'.format(RFRAME[5]) )
        return 0
    
    def QUERY_ANGLE_WRAPPED(self, DIR):
        self.OPEN_COM()
        RET = self.QUERY_ANGLE(DIR)
        self.CLOSE_COM()
        return RET

    def SEND_CMD(self, ADDR, VERB, PAR1=0x00, PAR2=0x00, ONESHOT=True):
        if ONESHOT: self.OPEN_COM()
        FRAME = [0xFF, ADDR, 0x00, VERB, PAR1, PAR2, 0x00]
        FRAME[6] = sum(FRAME, -0xFF) % 0x100
        for BYTE in FRAME: self.SERIAL.write(BYTE.to_bytes())
        if ONESHOT: self.CLOSE_COM()
        return 0

    def OPEN_COM(self):
        try:
            if not self.SERIAL.is_open:
                self.SERIAL.open()
        except:
            if self.USE_CMD:
                print(f"OPEN COM PORT '{self.COM_PORT}' FAILED")
                print("SET COM PORT:> ", end='', flush=True)
                for LINE in sys.stdin:
                    CMD = LINE.strip().upper()
                    if (CMD == ''): CMD = self.COM_PORT
                    RET = self.SET_SERIAL(CMD)
                    print(RET, flush=True)
                    if RET == "COM OPEN OK":
                        self.SERIAL.open()
                        return RET
                    print("SET COM PORT:> ", end='', flush=True)

    def CLOSE_COM(self):
        if(self.SERIAL.is_open): self.SERIAL.close()

    def SHOW_HELP(self):
        print("\n>>> PELCO-D INTERACTIVE COMMAND SHELL <<<\n")
        print("\t  [ AVAILABLE COMMAND LIST ]")
        print("---------------------\tHELP: SHOW THIS MESSAGE")
        print("|UPLT\tUP\tUPRT|\tQV, QH: GET CURRENT ANGLE")
        print("|LT\tSTOP\tRT  |\tGV, GH: GOTO ANGLE\t(1 ARGUMENT)")
        print("|DNLT\tDN\tDNRT|\tVSPD, HSPD: SET SPEED\t(1 ARGUMENT)")
        print("---------------------\tADDR: SET ADDRESS\t(1 ARGUMENT)")
        print("\n>>>  CTRL + C OR TYPE 'EXIT' TO QUIT  <<<\n")
        return 0

    def INTERPRETER(self, INPUT):
        CMD = INPUT.strip().upper().split(" ")
        try:
            match CMD[0]:
                case "GV":
                    RET = self.GOTO("V", int(CMD[1], 10))
                case "GH":
                    RET = self.GOTO("H", int(CMD[1], 10))
                case "VSPD":
                    self.VSPD = int(CMD[1], 10)
                    RET = 0
                case "HSPD":
                    self.HSPD = int(CMD[1], 10)
                    RET = 0
                case "QV":
                    RET = self.QUERY_ANGLE_WRAPPED("V")
                case "QH":
                    RET = self.QUERY_ANGLE_WRAPPED("H")
                case "ADDR":
                    self.ADDR = int(CMD[1])
                    RET = 0
                case "COM":
                    RET = self.SET_SERIAL(CMD[1])
                    if(RET == "COM OPEN OK"): RET = 0
                case "WAIT":
                    time.sleep(CMD[1])
                    return 0
                case "HELP":
                    RET = self.SHOW_HELP()
                case "EXIT":
                    print("EXIT")
                    exit()
                case "#":
                    pass
                case _:
                    RET = self.MOVE(CMD[0])
        except(IndexError, ValueError):
            RET = "INVALID COMMAND"
        return RET

    def RUN_FILE(self, FILEPATH):
        print(f">>>   PELCO-D CONTROLLER   <<<")
        print(f">>> EXECUTING SCRIPT: '' <<<")

        for LINE in sys.stdin:
            RET = self.INTERPRETER(LINE)
            if (RET != 0): print(RET, "[TYPE 'HELP' FOR MORE MESSAGE]")

    def CMD_SHELL(self):
        self.USE_CMD = True
        def SIG_HANDLER(SIG, FRAME):
            print("\nEXIT")
            exit()
        signal.signal(signal.SIGINT, SIG_HANDLER)

        if ( self.SET_SERIAL(self.COM_PORT) != "COM OPEN OK" ):
            self.OPEN_COM()
        self.CLOSE_COM()
        self.SHOW_HELP()
        
        print(f"PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> ", end='', flush=True)
        for LINE in sys.stdin:
            RET = self.INTERPRETER(LINE)
            if (RET != 0): print(RET, "[TYPE 'HELP' FOR MORE MESSAGE]")
            print(f"PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> ", end='', flush=True)

        self.USE_CMD = False

if __name__ == '__main__' :
    PELCO = PelcoD_Controller()
    PELCO.CMD_SHELL()

