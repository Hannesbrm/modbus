"""Register definitions using 1-based Modbus addresses."""

# 1-basierte Registeradressen gemäß Gerätedoku


# Anzeige/Diagnose
HEARTBEAT = 146
DISPLAY_VALUE = 149 # 2 regs (float)


# Prozesswerte
PRESSURE_PA = 151 # 2 regs (float)
AUTO_SETPOINT = 153 # 2 regs (float)
PID_OUTPUT_RAW = 155 # s16
MODE = 156 # u16


# Hand-Betrieb
HAND_SETPOINT_PERCENT = 165 # 2 regs (float)
OUTPUT_PERCENT = 167 # 2 regs (float)


# Alarme
LOW_ALARM = 216 # 2 regs (float)
HIGH_ALARM = 218 # 2 regs (float)
