import os
import threading
from typing import Any

from dash import Dash, Input, Output, State, dcc, html

import registers as REG
from config import load_config
from modbus_driver import VSensorDriver

CFG = load_config()

shared: dict[str, Any] = {
    "pressure_pa": None,
    "output_pct": None,
    "auto_sp": None,
    "mode": None,
    "hb": None,
    "status": "init",
}

stop_event = threading.Event()


def poller() -> None:
    drv = VSensorDriver.from_cfg(CFG)
    try:
        drv.connect()
        while not stop_event.is_set():
            try:
                shared["pressure_pa"] = drv.get_pressure_pa()
                shared["output_pct"] = drv.get_output_percent()
                shared["auto_sp"] = drv.get_auto_setpoint()
                shared["mode"] = drv.get_mode()
                shared["hb"] = drv.read_u16(REG.HEARTBEAT)
                shared["status"] = "ok"
            except TimeoutError:
                shared["status"] = "timeout"
            except Exception as exc:  # pragma: no cover - debugging
                shared["status"] = f"err: {exc}"  # pragma: no cover
            stop_event.wait(CFG["POLL_INTERVAL_SEC"])
    finally:
        drv.close()


poll_thread = threading.Thread(target=poller, daemon=True)
poll_thread.start()

app = Dash(__name__)
app.layout = html.Div(
    [
        html.H2("V-Sensor Dashboard"),
        html.Div(["Druck [Pa]: ", html.Span(id="pressure")]),
        html.Div(["Ausgang [%]: ", html.Span(id="output")]),
        html.Div(["Auto-Sollwert: ", html.Span(id="auto_sp")]),
        html.Div(["Modus: ", html.Span(id="mode")]),
        html.Div(["Heartbeat: ", html.Span(id="hb")]),
        html.Div(["Status: ", html.Span(id="status")]),
        html.Hr(),
        html.Div(
            [
                dcc.Input(id="new_sp", type="number", placeholder="Auto-Sollwert"),
                html.Button("Setze Auto-Sollwert", id="btn_set_sp"),
            ]
        ),
        html.Div(
            [
                dcc.Input(id="new_sp_hand", type="number", placeholder="Hand-Sollwert"),
                html.Button("Setze Hand-Sollwert", id="btn_set_hand"),
            ]
        ),
        html.Div(
            [
                dcc.Dropdown(
                    id="mode_dd",
                    options=[
                        {"label": "AUTO", "value": 1},
                        {"label": "HAND @SP", "value": 2},
                        {"label": "OFF", "value": 3},
                        {"label": "HAND @Output", "value": 4},
                    ],
                    placeholder="Modus wählen",
                ),
                html.Button("Setze Modus", id="btn_set_mode"),
            ]
        ),
        dcc.Interval(id="tick", interval=1000, n_intervals=0),
    ]
)


@app.callback(
    Output("pressure", "children"),
    Output("output", "children"),
    Output("auto_sp", "children"),
    Output("mode", "children"),
    Output("hb", "children"),
    Output("status", "children"),
    Input("tick", "n_intervals"),
)
def update_view(_):
    def fmt(v, f="{:.2f}"):
        return f.format(v) if isinstance(v, (int, float)) else "—"

    mode_map = {1: "AUTO", 2: "HAND @SP", 3: "OFF", 4: "HAND @Output"}
    return (
        fmt(shared["pressure_pa"], "{:.1f}"),
        (fmt(shared["output_pct"], "{:.1f}") + " %")
        if isinstance(shared["output_pct"], (int, float))
        else "—",
        fmt(shared["auto_sp"], "{:.1f}"),
        mode_map.get(shared["mode"], "—"),
        shared["hb"] if isinstance(shared["hb"], int) else "—",
        shared["status"],
    )


@app.callback(
    Output("btn_set_sp", "n_clicks"),
    Input("btn_set_sp", "n_clicks"),
    State("new_sp", "value"),
    prevent_initial_call=True,
)
def set_sp(_, val):
    drv = VSensorDriver.from_cfg(CFG)
    try:
        drv.connect()
        drv.set_auto_setpoint(float(val))
    finally:
        drv.close()
    return 0


@app.callback(
    Output("btn_set_hand", "n_clicks"),
    Input("btn_set_hand", "n_clicks"),
    State("new_sp_hand", "value"),
    prevent_initial_call=True,
)
def set_hand(_, val):
    drv = VSensorDriver.from_cfg(CFG)
    try:
        drv.connect()
        drv.write_float(REG.HAND_SETPOINT_PERCENT, float(val))
    finally:
        drv.close()
    return 0


@app.callback(
    Output("btn_set_mode", "n_clicks"),
    Input("btn_set_mode", "n_clicks"),
    State("mode_dd", "value"),
    prevent_initial_call=True,
)
def set_mode(_, val):
    drv = VSensorDriver.from_cfg(CFG)
    try:
        drv.connect()
        drv.set_mode(int(val))
    finally:
        drv.close()
    return 0


if __name__ == "__main__":
    try:
        app.run_server(
            debug=True,
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT_HTTP", "8050")),
        )
    finally:
        stop_event.set()
        poll_thread.join()
