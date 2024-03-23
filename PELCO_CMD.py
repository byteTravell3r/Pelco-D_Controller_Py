import os, sys, time, signal
from PELCO_CON import PELCOD_CONTROLLER

class PELCOD_CMD(PELCOD_CONTROLLER):
    def __init__(self):
        super().__init__()
        self.USE_CMD = True
        self.COLOR_HELP = "\33[34m"
        self.COLOR_ERROR = "\33[91m"
        self.COLOR_HINT  = "\33[90m"
        self.COLOR_CLEAR = "\33[0m"

    ### REDEFINED 'OPEN_COM' FOR INTERACTIVITY ###
    def OPEN_COM(self):
        try:
            if not self.SERIAL.is_open:
                self.SERIAL.open()
        except:
            if self.USE_CMD:
                print(self.COLOR_ERROR + "[ERROR]" + self.COLOR_CLEAR, f"OPEN COM PORT '{self.COM_PORT}' FAILED")
                print("SET COM PORT:> ", end='', flush=True)
                for LINE in sys.stdin:
                    CMD = LINE.strip().upper()
                    if (CMD == ''): CMD = self.COM_PORT
                    if (CMD == 'EXIT'): exit()
                    RET = self.SET_SERIAL(CMD)
                    print(RET, flush=True)
                    if RET == "COM OPEN OK":
                        self.SERIAL.open()
                        return RET
                    print("SET COM PORT:> ", end='', flush=True)
            else:
               return "COM OPEN FAILED"
            
    ### REDEFINED 'QUERY_ANGLE_WRAPPED' FOR INTERACTIVITY ###
    def QUERY_ANGLE_WRAPPED(self, DIR):
        RET = self.OPEN_COM()
        if (RET != 0): return RET
        RET = self.QUERY_ANGLE(DIR)
        self.CLOSE_COM()
        if self.USE_CMD:
            if DIR == "H": print("H_POSITION:", '{:0>2X}'.format(self.HPOS[0]), '{:0>2X}'.format(self.HPOS[1]) )
            if DIR == "V": print("V_POSITION:", '{:0>2X}'.format(self.VPOS[0]), '{:0>2X}'.format(self.VPOS[1]) )
        return RET
    
    def LIST_DIR(self):
        print("\n[CURRENT DIRECTORY]\n", os.getcwd())
        print("\n[FILES AND DIRS]")
        for NAMES in os.listdir():
            print(NAMES)
        print("")
        return 0

    def CHANGE_DIR(self, CMD):
        try:
            os.chdir(CMD)
            return 0
        except(FileNotFoundError, FileExistsError):
            return "NO SUCH FILE OR DIRECTORY"

    def SHOW_HELP(self):
        print(self.COLOR_HELP, "\n>>> PELCO-D INTERACTIVE COMMAND SHELL <<<\n")
        print("\t  [ AVAILABLE COMMAND LIST ]")
        print("----------------", "HELP: SHOW THIS MESSAGE")
        print("|UPLT  UP  UPRT|", "QV, QH: GET CURRENT ANGLE")
        print("|LT   STOP   RT|", "GV, GH: GOTO ANGLE\t(1 ARGUMENT)")
        print("|DNLT  DN  DNRT|", "VSPD, HSPD: SET SPEED\t(1 ARGUMENT)")
        print("----------------", "ADDR: SET ADDRESS\t(1 ARGUMENT)")
        print("\n>>>  CTRL + C OR TYPE 'EXIT' TO QUIT  <<<\n", self.COLOR_CLEAR)
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
                case "RUN":
                    pass
                case "LS":
                    RET = self.LIST_DIR()
                case "CD":
                    RET = self.CHANGE_DIR(CMD[1])
                case "EXIT":
                    print("EXIT\n")
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
            if (RET != 0): print(RET)

    def CMD_SHELL(self):
        self.USE_CMD = True
        def SIG_HANDLER(SIG, FRAME):
            print("\nEXIT\n")
            exit()
        signal.signal(signal.SIGINT, SIG_HANDLER)

        if ( self.SET_SERIAL(self.COM_PORT) != "COM OPEN OK" ):
            self.OPEN_COM()
        self.CLOSE_COM()
        self.SHOW_HELP()
        
        print(f"PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> ", end='', flush=True)
        for LINE in sys.stdin:
            RET = self.INTERPRETER(LINE)
            if (RET != 0): print(self.COLOR_ERROR + "[ERROR]" + self.COLOR_CLEAR, RET,
                                 self.COLOR_HINT + "[TYPE 'HELP' FOR MORE MESSAGE]" + self.COLOR_CLEAR)
            print(f"PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> ", end='', flush=True)

        self.USE_CMD = False
    pass

if __name__ == '__main__' :
    ### EXAMPLE OF USAGE ###
    PELCO = PELCOD_CMD()
    PELCO.CMD_SHELL()
