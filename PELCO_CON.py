import serial

global COLOR


class COLOR():
    HINT = "\33[90m"
    ERROR = "\33[91m"
    OK = "\33[92m"
    PROMPT = "\33[93m"
    DEBUG = "\33[94m"
    CLEAR = "\33[0m"


class PELCOD_CONTROLLER():
    ADDR = 0x01
    HSPD = 0xFF
    VSPD = 0xFF
    HPOS = 0
    VPOS = 0
    COM_PORT = "COM4"
    DEBUG = True

    COLOR = COLOR()

    def SET_SERIAL(self, COM):
        self.COM_PORT = COM
        try:
            self.SERIAL = serial.Serial(self.COM_PORT, 9600, timeout=2)
        except:
            return "COM OPEN FAILED"
        self.CLOSE_COM()
        return "COM OPEN OK"

    def MOVE(self, ACTION):
        match ACTION:
            case "STOP": INST = 0x00
            case "UP": INST = 0x08
            case "DN": INST = 0x10
            case "RT": INST = 0x02
            case "LT": INST = 0x04
            case "UPRT": INST = 0x0A
            case "UPLT": INST = 0x0C
            case "DNRT": INST = 0x12
            case "DNLT": INST = 0x14
            case "": INST = 0x00
            case _: return "INVALID COMMAND"
        return self.SEND_CMD(self.ADDR, INST, self.HSPD, self.VSPD)

    def SET_ANGLE(self, DIR, ANGLE):
        if ANGLE < 0x00:
            ANGLE = 0x00
        match DIR:
            case "H":
                if ANGLE > 0x863E:
                    ANGLE = 0x863E
                H_POS = [int(ANGLE % 0x100), int(ANGLE / 0x100)]
                self.HPOS = ANGLE
                return self.SEND_CMD(self.ADDR, 0x4B, H_POS[1], H_POS[0])
            case "V":
                if ANGLE > 0x863E:
                    ANGLE = 0x863E
                V_POS = [int(ANGLE % 0x100), int(ANGLE / 0x100)]
                self.VPOS = ANGLE
                return self.SEND_CMD(self.ADDR, 0x4D, V_POS[1], V_POS[0])
            case _: return "INVALID COMMAND"

    ### DO NOT USE 'QUERY_ANGLE' DIRECTLY IN YOUR PROGRAM ###
    ### USE 'QUERY_ANGLE_WRAPPED' INSTEAD ###
    def QUERY_ANGLE(self, DIR):
        match DIR:
            case "H": RET = self.SEND_CMD(self.ADDR, 0x51, ONESHOT=False)
            case "V": RET = self.SEND_CMD(self.ADDR, 0x53, ONESHOT=False)
            case _: RET = "INVALID COMMAND"
        if RET != 0:
            return RET
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

    def QUERY_ANGLE_WRAPPED(self, DIR):
        RET = self.OPEN_COM()
        if (RET != 0):
            return RET
        RET = self.QUERY_ANGLE(DIR)
        self.CLOSE_COM()
        return RET

    def SEND_CMD(self, ADDR, VERB, PAR1=0x00, PAR2=0x00, ONESHOT=True):
        if ONESHOT:
            RET = self.OPEN_COM()
            if (RET != 0):
                return RET

        self.FRAME = [0xFF, ADDR, 0x00, VERB, PAR1, PAR2, 0x00]
        self.FRAME[6] = sum(self.FRAME, -0xFF) % 0x100

        if self.DEBUG:
            print(COLOR.DEBUG + f"{self.COM_PORT} TX [", end=' ')
            for BYTE in self.FRAME:
                print('{:0>2X}'.format(BYTE), end=' ')
            print("]" + COLOR.CLEAR)

        for BYTE in self.FRAME:
            self.SERIAL.write(BYTE.to_bytes(1, 'big'))
        if ONESHOT:
            self.CLOSE_COM()
        return 0

    def OPEN_COM(self):
        try:
            if not self.SERIAL.is_open:
                self.SERIAL.open()
                return 0
        except:
            return "COM OPEN FAILED"

    def CLOSE_COM(self):
        try:
            self.SERIAL.close()
        except:
            pass


if __name__ == '__main__':
    ### EXAMPLE OF USAGE ###
    ### YOU HAVE TO MONITOR ALL THE RETURN STATUS ###
    PELCO = PELCOD_CONTROLLER()
    print(PELCO.SET_SERIAL(PELCO.COM_PORT))
    print(PELCO.MOVE('STOP'))
    print(PELCO.SET_ANGLE('H', 0x0000))
    print(PELCO.QUERY_ANGLE_WRAPPED('H'))
