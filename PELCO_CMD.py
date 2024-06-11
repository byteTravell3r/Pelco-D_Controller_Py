import os, sys, time, signal
import serial.tools.list_ports
from PELCO_CON import PELCOD_CONTROLLER

global COLOR

class COLOR():
    HINT = "\33[90m"
    ERROR = "\33[91m"
    OK = "\33[92m"
    PROMPT = "\33[93m"
    DEBUG = "\33[94m"
    CLEAR = "\33[0m"

class PELCOD_CMD(PELCOD_CONTROLLER):

    USE_CMD = True
    RUN_FILE_DEPTH = 0
    RUN_FILE_MAX_DEPTH = 3
    SIG_INT = False

    def OPEN_COM_INTERACTIVE(self):
        try:
            if not self.SERIAL.is_open:
                self.SERIAL.open()
                return 0
        except:
            if self.USE_CMD:
                print(COLOR.ERROR + "[ERROR]" + COLOR.CLEAR,
                      f"OPEN COM PORT '{self.COM_PORT}' FAILED")

                print(COLOR.DEBUG + "\t[ AVAILABLE COM PORTS ]")
                for port in serial.tools.list_ports.comports():
                    # print("  " + "[" + str(serial.tools.list_ports.comports().index(port)) + "]", end=' ')
                    print(port)
                print(COLOR.CLEAR, end='')

                print(COLOR.PROMPT + "SET COM PORT:> " +
                      COLOR.CLEAR, end='', flush=True)
                for LINE in sys.stdin:
                    CMD = LINE.strip()
                    if (os.name == 'nt'):
                        CMD = CMD.upper()
                    if (CMD == ''):
                        CMD = self.COM_PORT
                    if (CMD == 'EXIT'):
                        exit()
                    RET = self.SET_SERIAL(CMD)
                    print(RET, flush=True)
                    if RET == "COM OPEN OK":
                        self.SERIAL.close()
                        return RET
                    print(COLOR.PROMPT + "SET COM PORT:> " +
                          COLOR.CLEAR, end='', flush=True)
            else:
                return "COM OPEN FAILED"

    ### REDEFINED 'QUERY_ANGLE_WRAPPED' FOR INTERACTIVITY ###
    def QUERY_ANGLE_WRAPPED(self, DIR):
        RET = self.OPEN_COM_INTERACTIVE()
        if (RET != 0):
            return RET
        RET = self.QUERY_ANGLE(DIR)
        self.CLOSE_COM()
        if (self.USE_CMD and RET == 0):
            if DIR == "H":
                print("H_POSITION:", self.HPOS)
            if DIR == "V":
                print("V_POSITION:", self.VPOS)
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
        except (FileNotFoundError, FileExistsError):
            return "NO SUCH FILE OR DIRECTORY"

    def SHOW_HELP(self):
        print(COLOR.HINT, "\n>>> PELCO-D INTERACTIVE COMMAND SHELL <<<\n")
        print("\t     [ AVAILABLE COMMAND LIST ]\n")
        print("   [MOVEMENT]   ", "\tHELP: SHOW THIS MESSAGE")
        print("----------------", "\tCOM [PORT]: SET COM PORT")
        print("|UPLT  UP  UPRT|", "\tADDR [INT]: SET ADDRESS")
        print("|              |", "\tGET [H,V]: GET CURRENT POSITION")
        print("|LT   STOP   RT|", "\tSET [H,V] [INT]: GOTO POSITION")
        print("|              |", "\tSPD [H,V] [INT]: SET SPEED")
        print("|DNLT  DN  DNRT|", "\tRUN [FILENAME] : RUN PROGRAM")
        print("----------------", "\tLS, CD: USAGE SAME AS SHELL")
        print("\n>>>  CTRL + C OR TYPE 'EXIT' TO QUIT  <<<\n", COLOR.CLEAR)
        return 0

    def INTERPRETER(self, INPUT):
        CMD = INPUT.strip().split(" ")
        CMD[0] = CMD[0].upper()
        RET = 0
        try:
            match CMD[0]:
                case "SET":
                    RET = self.SET_ANGLE(CMD[1].upper(), int(CMD[2], 10))
                case "SPD":
                    match CMD[1]:
                        case "V": self.VSPD = int(CMD[2], 10)
                        case "H": self.HSPD = int(CMD[2], 10)
                        case _: RET = "INVALID COMMAND"
                case "GET":
                    RET = self.QUERY_ANGLE_WRAPPED(CMD[1].upper())
                case "ADDR":
                    self.ADDR = int(CMD[1])
                case "COM":
                    if (os.name == 'nt'):
                        CMD[1] = CMD[1].upper()
                    RET = self.SET_SERIAL(CMD[1].upper())
                    if (RET == "COM OPEN OK"):
                        RET = 0
                case "WAIT":
                    time.sleep(float(CMD[1]))
                case "HELP":
                    RET = self.SHOW_HELP()
                case "RUN":
                    if self.RUN_FILE_DEPTH <= self.RUN_FILE_MAX_DEPTH:
                        if (os.name == 'nt'):
                            CMD[1] = CMD[1].upper()
                        RET = self.RUN_FILE(CMD[1])
                    else:
                        RET = "EXCEED FILE DEPTH LIMIT"
                case "LS":
                    RET = self.LIST_DIR()
                case "CD":
                    RET = self.CHANGE_DIR(CMD[1])
                case "EXIT":
                    if self.RUN_FILE_DEPTH == 0:
                        print(COLOR.HINT + "EXIT\n" + COLOR.CLEAR)
                        exit()
                    self.SIG_INT = True
                case "#":
                    pass
                case _:
                    RET = self.MOVE(CMD[0])
        except (IndexError, ValueError):
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
        while (INDEX < len(FILE)):
            if self.SIG_INT:
                self.SIG_INT = False
                return 0

            LINE = FILE[INDEX]
            if self.DEBUG:
                print(COLOR.DEBUG + f"LINE:{INDEX} ADDR:{self.ADDR}@{self.COM_PORT}> " +
                      LINE + COLOR.CLEAR, end='', flush=True)
            if (LINE == '\n'):
                LINE = '#'
            if (LINE.strip().split()[0] == "GOTO"):
                try:
                    INDEX = int(LINE.strip().split()[1]) - 2
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
            print(COLOR.HINT + "EXIT\n" + COLOR.CLEAR)
            if self.RUN_FILE_DEPTH == 0:
                exit()
            self.SIG_INT = True

        signal.signal(signal.SIGINT, SIG_HANDLER)

        if (self.SET_SERIAL(self.COM_PORT) != "COM OPEN OK"):
            self.OPEN_COM_INTERACTIVE()
        self.CLOSE_COM()
        self.SHOW_HELP()

        print(f"{COLOR.PROMPT}PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> {COLOR.CLEAR}",
              end='', flush=True)
        for LINE in sys.stdin:
            RET = self.INTERPRETER(LINE)
            if (RET != 0) and (RET != "COM OPEN OK"):
                print(COLOR.ERROR + "[ERROR]" + COLOR.CLEAR, RET,
                      COLOR.HINT + "[TYPE 'HELP' FOR MORE MESSAGE]" + COLOR.CLEAR)
            print(
                f"{COLOR.PROMPT}PELCO-D ADDR:{self.ADDR}@{self.COM_PORT}> {COLOR.CLEAR}", end='', flush=True)

        self.USE_CMD = False


if __name__ == '__main__':
    ### EXAMPLE OF USAGE ###
    PELCO = PELCOD_CMD()
    PELCO.CMD_SHELL()
