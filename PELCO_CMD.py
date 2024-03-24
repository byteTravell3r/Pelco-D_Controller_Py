import os, sys, time, signal
from PELCO_CON import PELCOD_CONTROLLER

global COLOR
class COLOR():
    HINT   = "\33[90m"
    ERROR  = "\33[91m"
    OK     = "\33[92m"
    PROMPT = "\33[93m"
    DEBUG  = "\33[94m"
    CLEAR  = "\33[0m"

class PELCOD_CMD(PELCOD_CONTROLLER):
    
    USE_CMD = True
    RUN_FILE_DEPTH = 0
    RUN_FILE_MAX_DEPTH = 3

    ### REDEFINED 'OPEN_COM' FOR INTERACTIVITY ###
    def OPEN_COM(self):
        try:
            if not self.SERIAL.is_open:
                self.SERIAL.open()
                return 0
        except:
            if self.USE_CMD:
                print(COLOR.ERROR + "[ERROR]" + COLOR.CLEAR, f"OPEN COM PORT '{self.COM_PORT}' FAILED")
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
        print(COLOR.HINT)
        print("[CURRENT DIRECTORY]\n", os.getcwd())
        print("\n[FILES AND DIRS]")
        for NAMES in os.listdir():
            print(NAMES)
        print(COLOR.CLEAR)
        return 0

    def CHANGE_DIR(self, CMD):
        try:
            os.chdir(CMD)
            return 0
        except(FileNotFoundError, FileExistsError):
            return "NO SUCH FILE OR DIRECTORY"

    def SHOW_HELP(self):
        print(COLOR.HINT, "\n>>> PELCO-D INTERACTIVE COMMAND SHELL <<<\n")
        print("\t  [ AVAILABLE COMMAND LIST ]")
        print("----------------", "HELP: SHOW THIS MESSAGE")
        print("|UPLT  UP  UPRT|", "GET  [H,V]: GET CURRENT POSITION")
        print("|LT   STOP   RT|", "SET [H,V]: GOTO ANGLE\t(2 ARGUMENT)")
        print("|DNLT  DN  DNRT|", "SPDV, SPDH: SET SPEED\t(1 ARGUMENT)")
        print("----------------", "ADDR: SET ADDRESS\t(1 ARGUMENT)")
        print("\n>>>  CTRL + C OR TYPE 'EXIT' TO QUIT  <<<\n", COLOR.CLEAR)
        return 0

    def INTERPRETER(self, INPUT):
        CMD = INPUT.strip().split(" ")
        CMD[0] = CMD[0].upper()
        RET = 0
        try:
            match CMD[0]:
                case "SET":
                    RET = self.GOTO(CMD[1], int(CMD[2], 10))
                case "SPDV":
                    self.VSPD = int(CMD[1], 10)
                case "SPDH":
                    self.HSPD = int(CMD[1], 10)
                case "GET":
                    RET = self.QUERY_ANGLE_WRAPPED(CMD[1])
                case "ADDR":
                    self.ADDR = int(CMD[1])
                case "COM":
                    RET = self.SET_SERIAL(CMD[1].upper())
                    if(RET == "COM OPEN OK"): RET = 0
                case "WAIT":
                    time.sleep(int(CMD[1]))
                case "HELP":
                    RET = self.SHOW_HELP()
                case "RUN":
                    if self.RUN_FILE_DEPTH <= self.RUN_FILE_MAX_DEPTH:
                        RET = self.RUN_FILE(CMD[1])
                    else:
                        RET = "EXCEED FILE DEPTH LIMIT"
                case "LS":
                    RET = self.LIST_DIR()
                case "CD":
                    RET = self.CHANGE_DIR(CMD[1])
                case "EXIT":
                    print(COLOR.HINT + "EXIT\n" + COLOR.CLEAR)
                    exit()
                case "#":
                    pass
                case _:
                    RET = self.MOVE(CMD[0])
        except(IndexError, ValueError):
            RET = "INVALID COMMAND"
        return RET

    def RUN_FILE(self, FILEPATH):
        try:
            F = open(FILEPATH, 'r', encoding='utf-8')
            FILE = F.readlines()
            F.close()
        except:
            return "NO SUCH FILE OR DIRECTORY"

        if not (FILE[0].strip() == "# PELCO CONTROL PROGRAM #"):
            return "INVALID PROGRAM FILE"
        
        print(f">>> EXECUTING PROGRAM: {FILEPATH} <<<")
        
        self.RUN_FILE_DEPTH += 1

        INDEX = 0
        while(INDEX < len(FILE)):
            LINE = FILE[INDEX]

            if self.DEBUG:
                print(COLOR.DEBUG + '> ' + LINE + COLOR.CLEAR, end='', flush=True)

            if (LINE == '\n'): LINE = '#'
            if (LINE.strip().split()[0] == "GOTO"):
                try:
                    INDEX = int(LINE.strip().split()[1])
                    LINE = FILE[INDEX]
                except:
                    RET = "GOTO LINE ERROR"
            else:
                RET = self.INTERPRETER(LINE)
            
            if (RET == 0):
                INDEX += 1
            else:
                self.RUN_FILE_DEPTH -= 1
                return RET

    def CMD_SHELL(self):
        self.USE_CMD = True
        def SIG_HANDLER(SIG, FRAME):
            print(COLOR.HINT + "\nEXIT\n" + COLOR.CLEAR)
            exit()
        signal.signal(signal.SIGINT, SIG_HANDLER)

        if ( self.SET_SERIAL(self.COM_PORT) != "COM OPEN OK" ):
            self.OPEN_COM()
        self.CLOSE_COM()
        self.SHOW_HELP()

        print(f"{COLOR.PROMPT}PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> {COLOR.CLEAR}", end='', flush=True)
        for LINE in sys.stdin:
            RET = self.INTERPRETER(LINE)
            if (RET != 0): print(COLOR.ERROR + "[ERROR]" + COLOR.CLEAR, RET,
                                 COLOR.HINT + "[TYPE 'HELP' FOR MORE MESSAGE]" + COLOR.CLEAR)
            print(f"{COLOR.PROMPT}PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> {COLOR.CLEAR}", end='', flush=True)

        self.USE_CMD = False

if __name__ == '__main__' :
    ### EXAMPLE OF USAGE ###
    PELCO = PELCOD_CMD()
    PELCO.CMD_SHELL()
