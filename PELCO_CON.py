import serial

class PELCOD_CONTROLLER():
    
    def __init__(self):
        self.ADDR = 0x01
        self.HSPD = 0xFF
        self.VSPD = 0xFF
        self.HPOS = [0x00, 0x00]
        self.VPOS = [0x00, 0x00]
        self.COM_PORT = "COM6"

    def SET_SERIAL(self, COM):
        self.COM_PORT = COM
        try: self.SERIAL = serial.Serial(self.COM_PORT, 9600, timeout=0.05)
        except: return "COM OPEN FAILED"
        self.CLOSE_COM()
        return "COM OPEN OK"

    def MOVE(self, ACTION):
        match ACTION:
            case "STOP": INST = 0x00
            case "UP"  : INST = 0x08
            case "DN"  : INST = 0x10
            case "RT"  : INST = 0x02
            case "LT"  : INST = 0x04
            case "UPRT": INST = 0x0A
            case "UPLT": INST = 0x0C
            case "DNRT": INST = 0x12
            case "DNLT": INST = 0x14
            case ""    : INST = 0x00
            case _     : return "INVALID COMMAND"
        return self.SEND_CMD(self.ADDR, INST, self.HSPD, self.VSPD)
    
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

    ### DO NOT USE 'QUERY_ANGLE' DIRECTLY IN YOUR PROGRAM ###
    ### USE 'QUERY_ANGLE_WRAPPED' INSTEAD ###
    def QUERY_ANGLE(self, DIR):
        match DIR:
            case "H": RET = self.SEND_CMD(self.ADDR, 0x51, ONESHOT=False)
            case "V": RET = self.SEND_CMD(self.ADDR, 0x53, ONESHOT=False)
            case _  : RET = "INVALID COMMAND"
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
            return f"{self.COM_PORT} READ TIMEOUT"

        if DIR == "H": self.HPOS = [RFRAME[3], RFRAME[4]]
        if DIR == "V": self.VPOS = [RFRAME[3], RFRAME[4]]
        return 0
    
    def QUERY_ANGLE_WRAPPED(self, DIR):
        RET = self.OPEN_COM()
        if (RET != 0): return RET
        RET = self.QUERY_ANGLE(DIR)
        self.CLOSE_COM()
        return RET

    def SEND_CMD(self, ADDR, VERB, PAR1=0x00, PAR2=0x00, ONESHOT=True):
        if ONESHOT: RET = self.OPEN_COM()
        if (RET != 0): return RET
        FRAME = [0xFF, ADDR, 0x00, VERB, PAR1, PAR2, 0x00]
        FRAME[6] = sum(FRAME, -0xFF) % 0x100
        for BYTE in FRAME: self.SERIAL.write(BYTE.to_bytes())
        if ONESHOT: self.CLOSE_COM()
        return 0

    def OPEN_COM(self):
        try:
            if not self.SERIAL.is_open:
                self.SERIAL.open()
            return 0
        except:
            return "COM OPEN FAILED"

    def CLOSE_COM(self):
        try: self.SERIAL.close()
        except: pass

if __name__ == '__main__' :
    ### EXAMPLE OF USAGE ###
    ### YOU HAVE TO MONITOR ALL THE RETURN STATUS ###
    PELCO = PELCOD_CONTROLLER()
    print( PELCO.SET_SERIAL(PELCO.COM_PORT) )
    print( PELCO.MOVE('STOP') )
    print( PELCO.GOTO('H', 0x0000) )
    print( PELCO.QUERY_ANGLE_WRAPPED('H') )
