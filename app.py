import os
)
def update_view(_):
def fmt(v, f="{:.2f}"):
return (f.format(v) if isinstance(v, (int, float)) else "—")
mode_map = {1:"AUTO", 2:"HAND @SP", 3:"OFF", 4:"HAND @aktueller Output"}
return (
fmt(shared["display"]),
fmt(shared["pressure_pa"], "{:.1f}"),
(fmt(shared["output_pct"], "{:.1f}") + " %") if isinstance(shared["output_pct"], (int,float)) else "—",
shared["hb"] if isinstance(shared["hb"], int) else "—",
mode_map.get(shared["mode"], "—"),
shared["status"],
)


@app.callback(Output("btn_set_sp","n_clicks"), Input("btn_set_sp","n_clicks"), State("new_sp","value"), prevent_initial_call=True)
def set_sp(_, val):
drv = VSensorDriver.from_cfg(CFG)
try:
drv.connect()
drv.write_float(REG.AUTO_SETPOINT, float(val))
finally:
drv.close()
return 0


@app.callback(Output("btn_set_hand","n_clicks"), Input("btn_set_hand","n_clicks"), State("new_sp_hand","value"), prevent_initial_call=True)
def set_hand(_, val):
drv = VSensorDriver.from_cfg(CFG)
try:
drv.connect()
drv.write_float(REG.HAND_SETPOINT_PERCENT, float(val))
finally:
drv.close()
return 0


@app.callback(Output("btn_set_mode","n_clicks"), Input("btn_set_mode","n_clicks"), State("mode_dd","value"), prevent_initial_call=True)
def set_mode(_, val):
drv = VSensorDriver.from_cfg(CFG)
try:
drv.connect()
drv.write_u16(REG.MODE, int(val))
finally:
drv.close()
return 0


if __name__ == "__main__":
try:
app.run_server(debug=True, host=os.getenv("HOST","127.0.0.1"), port=int(os.getenv("PORT_HTTP", "8050")))
finally:
stop_event.set()
