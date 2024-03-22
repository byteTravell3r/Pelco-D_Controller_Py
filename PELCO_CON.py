import serial, signal, sys

class PelcoD_Controller():
    def __init__(self):
        self.ADDR = 0x01
        self.INST = 0x00
        self.HSPD = 0xFF
        self.VSPD = 0xFF
        self.HPOS = [0x00, 0x00]
        self.VPOS = [0x00, 0x00]
        self.FRAME  = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self.RFRAME = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self.COM_PORT = "COM6"
        self.USE_CMD = False

    def SET_SERIAL(self, COM):
        self.COM_PORT = COM
        try:
            self.SERIAL = serial.Serial(self.COM_PORT, 9600, timeout=0.05)
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
        
        self.FRAME = [0xFF, self.ADDR, 0x00, self.INST, self.HSPD, self.VSPD, 0x00]
        return self.SEND_CMD()
    
    def GOTO(self, DIR, ANGLE):
        if ANGLE < 0x0   : ANGLE = 0x0
        match DIR:
            case "H": 
                if ANGLE > 0x863E: ANGLE = 0x863E
                self.HPOS[0] = int(ANGLE % 0x100)
                self.HPOS[1] = int(ANGLE / 0x100)
                self.FRAME = [0xFF, self.ADDR, 0x00, 0x4B, self.HPOS[0], self.HPOS[1], 0x00]
            case "V":
                self.VPOS[0] = int(ANGLE % 0x100)
                self.VPOS[1] = int(ANGLE / 0x100)
                self.FRAME = [0xFF, self.ADDR, 0x00, 0x4D, self.VPOS[0], self.VPOS[1], 0x00]
            case _  : return "INVALID COMMAND"

        return self.SEND_CMD()

    def QUERY_ANGLE(self, DIR):
        match DIR:
            case "H": self.INST = 0x51
            case "V": self.INST = 0x53
            case _  : return "INVALID COMMAND"
        
        self.FRAME = [0xFF, self.ADDR, 0x00, self.INST, 0x00, 0x00, 0x00]

        self.OPEN_COM()
        SUM = -0xFF
        for BYTE in self.FRAME: SUM += BYTE
        self.FRAME[6] = SUM % 0x100
        self.INST = 0x00

        for BYTE in self.FRAME:
            self.SERIAL.write(BYTE.to_bytes())

        try:
            self.RFRAME[0] = int(self.SERIAL.read().hex(), 16)
            if (self.RFRAME[0] == 0xFF):
                self.RFRAME[1] = int(self.SERIAL.read().hex(), 16)
                self.RFRAME[2] = int(self.SERIAL.read().hex(), 16)
                self.RFRAME[3] = int(self.SERIAL.read().hex(), 16)
                self.RFRAME[4] = int(self.SERIAL.read().hex(), 16)
                self.RFRAME[5] = int(self.SERIAL.read().hex(), 16)
                self.RFRAME[6] = int(self.SERIAL.read().hex(), 16)
            else:
                self.SERIAL.read_all()
                return "READ FAIL"
        except:
            self.CLOSE_COM()
            return "READ TIMEOUT"

        SUM = -0xFF
        for BYTE in self.RFRAME: SUM += BYTE
        SUM -= self.RFRAME[6]

        if self.RFRAME[6] == (SUM % 0x100):
            if self.USE_CMD:
                print(f"{DIR} POSITION:", '{:0>2X}'.format(self.RFRAME[4]), '{:0>2X}'.format(self.RFRAME[5]) )
            match DIR:
                case "H": self.HPOS = [ self.RFRAME[4], self.RFRAME[5] ]
                case "V": self.VPOS = [ self.RFRAME[4], self.RFRAME[5] ]
            return 0
        else:
            self.SERIAL.read_all()
            return "CHECKSUM FAIL"
        
    def SEND_CMD(self):
        self.OPEN_COM()
        SUM = -0xFF
        for BYTE in self.FRAME: SUM += BYTE
        self.FRAME[6] = SUM % 0x100
        self.INST = 0x00

        for BYTE in self.FRAME:
            self.SERIAL.write(BYTE.to_bytes())
        self.CLOSE_COM()
        return 0

    def OPEN_COM(self):
        if(not self.SERIAL.is_open) and self.USE_CMD:
            try:
                self.SERIAL.open()
            except(serial.SerialException):
                print(f"OPEN COM PORT({self.COM_PORT}) FAILED.")
                print("SET COM PORT:", end='', flush=True)
                for LINE in sys.stdin:
                    CMD = LINE.strip().upper()
                    if (CMD == ''): CMD = self.COM_PORT
                    RET = self.SET_SERIAL(CMD)
                    print(RET, flush=True)
                    if RET == "COM OPEN OK":
                        self.SERIAL.open()
                        break
                    print("SET COM PORT:", end='', flush=True)

    def CLOSE_COM(self):
        if(self.SERIAL.is_open):
            self.SERIAL.close()

    def SHOW_HELP(self):
        print("")
        print(">>> PELCO-D INTERACTIVE COMMAND SHELL <<<\n")
        print("\t  [ AVAILABLE COMMAND LIST ]")
        print("---------------------\tHELP: SHOW THIS MESSAGE")
        print("|UPLT\tUP\tUPRT|\tQV, QH: GET CURRENT ANGLE")
        print("|LT\tSTOP\tRT  |\tGV, GH: GOTO ANGLE (1 ARGUMENT)")
        print("|DNLT\tDN\tDNRT|\tVS, HS: SET SPEED  (1 ARGUMENT)")
        print("---------------------\tADDR: SET ADDRESS  (1 ARGUMENT)\n")
        print(">>>  CTRL + C OR TYPE 'EXIT' TO QUIT  <<<")
        print("")
        return 0

    def CMD_SHELL(self):
        self.USE_CMD = True

        def SIG_HANDLER(SIG, FRAME):
            print("\nEXIT")
            exit()
        signal.signal(signal.SIGINT, SIG_HANDLER)

        if ( self.SET_SERIAL(self.COM_PORT) != "COM OPEN OK" ):
            print(f"OPEN DEFAULT COM PORT({self.COM_PORT}) FAILED.")
            print("SET COM PORT:", end='', flush=True)
            for LINE in sys.stdin:
                CMD = LINE.strip().upper()
                if (CMD == ''): CMD = self.COM_PORT
                RET = self.SET_SERIAL(CMD)
                print(RET, flush=True)
                if RET == "COM OPEN OK": break

        self.SHOW_HELP()

        print(f"PELCO-D ADDR={self.ADDR}:> ", end='', flush=True)

        for LINE in sys.stdin:
            CMD = LINE.strip().upper().split(" ")
            try:
                match CMD[0]:
                    case "GV":
                        RET = self.GOTO("V", int(CMD[1], 10))
                    case "GH":
                        RET = self.GOTO("H", int(CMD[1], 10))
                    case "VS":
                        self.VSPD = int(CMD[1], 10)
                        RET = 0
                    case "HS":
                        self.HSPD = int(CMD[1], 10)
                        RET = 0
                    case "QV":
                        RET = self.QUERY_ANGLE("V")
                    case "QH":
                        RET = self.QUERY_ANGLE("H")
                    case "ADDR":
                        self.ADDR = int(CMD[1])
                        RET = 0
                    case "COM":
                        RET = self.SET_SERIAL(CMD[1])
                    case "HELP":
                        RET = self.SHOW_HELP()
                    case "EXIT":
                        break
                    case _:
                        RET = self.MOVE(CMD[0])
            except(IndexError, ValueError):
                RET = "INVALID COMMAND"
    
            if (RET != 0):
                print(RET, "[TYPE 'HELP' FOR MORE MESSAGE]")

            print(f"PELCO-D ADDR={self.ADDR}:> ", end='', flush=True)

        self.USE_CMD = False

if __name__ == '__main__' :
    PELCO = PelcoD_Controller()
    PELCO.CMD_SHELL()

