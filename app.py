import os
import threading
from typing import Any, Optional

from dash import Dash, Input, Output, State, dcc, html

import registers as REG
from config import load_config
from modbus_driver import VSensorDriver

# ---- Globale Treiberinstanz ----
CFG = load_config()
DRV = VSensorDriver.from_cfg(CFG)
DRV_LOCK = threading.Lock()

# Gemeinsame Daten zwischen Polling-Thread und UI
shared: dict[str, Any] = {
    "pressure_pa": None,
    "output_pct": None,
    "auto_sp": None,
    "mode": None,
    "hb": None,
    "status": "init",
}

stop_event = threading.Event()
start_guard = threading.Event()
poll_thread: Optional[threading.Thread] = None


def poller() -> None:
    """Hintergrundthread zum zyklischen Auslesen der Messwerte."""
    while not stop_event.is_set():
        try:
            with DRV_LOCK:
                shared["pressure_pa"] = DRV.get_pressure_pa()
                shared["output_pct"] = DRV.get_output_percent()
                shared["auto_sp"] = DRV.get_auto_setpoint()
                shared["mode"] = DRV.get_mode()
                shared["hb"] = DRV.read_u16(REG.HEARTBEAT)
            shared["status"] = "ok"
        except TimeoutError:
            shared["status"] = "timeout"
        except Exception as exc:  # pragma: no cover - debugging
            shared["status"] = f"err: {exc}"  # pragma: no cover
        stop_event.wait(CFG["POLL_INTERVAL_SEC"])

app = Dash(__name__)
app.layout = html.Div(
    [
        html.H2("V-Sensor Dashboard"),
        html.Div(
            [
                dcc.Input(id="cfg_port", type="text", value=CFG["PORT"], placeholder="Port"),
                dcc.Input(
                    id="cfg_slave",
                    type="number",
                    value=CFG["SLAVE_ID"],
                    placeholder="Slave-ID",
                    min=1,
                ),
                dcc.Input(
                    id="cfg_baud",
                    type="number",
                    value=CFG["BAUD"],
                    placeholder="Baud",
                    min=1200,
                ),
                dcc.Dropdown(
                    id="cfg_parity",
                    options=[{"label": p, "value": p} for p in ["N", "E", "O"]],
                    value=CFG["PARITY"],
                    clearable=False,
                ),
                dcc.Input(
                    id="cfg_stopbits",
                    type="number",
                    value=CFG["STOPBITS"],
                    placeholder="Stopbits",
                    min=1,
                    max=2,
                ),
                dcc.Dropdown(
                    id="cfg_ff",
                    options=[{"label": str(i), "value": i} for i in range(4)],
                    value=CFG["FLOAT_FORMAT"],
                    clearable=False,
                ),
                html.Button("Verbinden/Übernehmen", id="btn_connect"),
            ]
        ),
        html.Div(["Status: ", html.Span(id="status")]),
        html.Div(["Druck [Pa]: ", html.Span(id="pressure")]),
        html.Div(["Ausgang [%]: ", html.Span(id="output")]),
        html.Div(["Auto-Sollwert: ", html.Span(id="auto_sp")]),
        html.Div(["Modus: ", html.Span(id="mode")]),
        html.Div(["Heartbeat: ", html.Span(id="hb")]),
        html.Hr(),
        html.Div(
            [
                dcc.Input(
                    id="new_sp",
                    type="number",
                    placeholder="Auto-Sollwert",
                    min=0,
                ),
                html.Button("Setze Auto-Sollwert", id="btn_set_sp"),
            ]
        ),
        html.Div(
            [
                dcc.Input(
                    id="new_sp_hand",
                    type="number",
                    placeholder="Hand-Sollwert",
                    min=0,
                    max=100,
                ),
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
                    value=1,  # Default: AUTO
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
    status_map = {"ok": "verbunden"}
    status_txt = status_map.get(shared["status"], shared["status"])
    return (
        fmt(shared["pressure_pa"], "{:.1f}"),
        (fmt(shared["output_pct"], "{:.1f}") + " %")
        if isinstance(shared["output_pct"], (int, float))
        else "—",
        fmt(shared["auto_sp"], "{:.1f}"),
        mode_map.get(shared["mode"], "—"),
        shared["hb"] if isinstance(shared["hb"], int) else "—",
        status_txt,
    )


@app.callback(
    Output("btn_set_sp", "n_clicks"),
    Input("btn_set_sp", "n_clicks"),
    State("new_sp", "value"),
    prevent_initial_call=True,
)
def set_sp(_, val):
    if val is None:
        return 0
    try:
        with DRV_LOCK:
            DRV.set_auto_setpoint(float(val))
        shared["status"] = "write ok"
    except TimeoutError:
        shared["status"] = "timeout"
    except Exception as exc:  # pragma: no cover - debugging
        shared["status"] = f"err: {exc}"  # pragma: no cover
    return 0


@app.callback(
    Output("btn_set_hand", "n_clicks"),
    Input("btn_set_hand", "n_clicks"),
    State("new_sp_hand", "value"),
    prevent_initial_call=True,
)
def set_hand(_, val):
    if val is None:
        return 0
    try:
        with DRV_LOCK:
            DRV.write_float(REG.HAND_SETPOINT_PERCENT, float(val))
        shared["status"] = "write ok"
    except TimeoutError:
        shared["status"] = "timeout"
    except Exception as exc:  # pragma: no cover - debugging
        shared["status"] = f"err: {exc}"  # pragma: no cover
    return 0


@app.callback(
    Output("btn_connect", "n_clicks"),
    Input("btn_connect", "n_clicks"),
    State("cfg_port", "value"),
    State("cfg_slave", "value"),
    State("cfg_baud", "value"),
    State("cfg_parity", "value"),
    State("cfg_stopbits", "value"),
    State("cfg_ff", "value"),
    prevent_initial_call=True,
)
def reconnect(_, port, slave, baud, parity, stopbits, ff):
    global DRV, CFG, poll_thread, stop_event
    cfg = {
        "PORT": port or CFG["PORT"],
        "SLAVE_ID": int(slave) if slave is not None else CFG["SLAVE_ID"],
        "BAUD": int(baud) if baud is not None else CFG["BAUD"],
        "PARITY": parity or CFG["PARITY"],
        "STOPBITS": int(stopbits) if stopbits is not None else CFG["STOPBITS"],
        "BYTESIZE": CFG["BYTESIZE"],
        "TIMEOUT": CFG["TIMEOUT"],
        "FLOAT_FORMAT": int(ff) if ff is not None else CFG["FLOAT_FORMAT"],
    }

    stop_event.set()
    if poll_thread is not None:
        poll_thread.join()

    with DRV_LOCK:
        DRV.close()
        DRV = VSensorDriver.from_cfg(cfg)
        try:
            DRV.connect()
        except (PermissionError, FileNotFoundError) as exc:
            shared["status"] = f"port err: {exc}"
            poll_thread = None
            stop_event = threading.Event()
            return 0
        except Exception as exc:  # pragma: no cover - init failure
            shared["status"] = f"init err: {exc}"  # pragma: no cover
            poll_thread = None
            stop_event = threading.Event()
            return 0

    stop_event = threading.Event()
    poll_thread = threading.Thread(target=poller, daemon=True)
    poll_thread.start()
    CFG.update(cfg)
    shared["status"] = "ok"
    return 0


@app.callback(
    Output("btn_set_mode", "n_clicks"),
    Input("btn_set_mode", "n_clicks"),
    State("mode_dd", "value"),
    prevent_initial_call=True,
)
def set_mode(_, val):
    if val is None:
        return 0
    try:
        with DRV_LOCK:
            DRV.set_mode(int(val))
        shared["status"] = "write ok"
    except TimeoutError:
        shared["status"] = "timeout"
    except Exception as exc:  # pragma: no cover - debugging
        shared["status"] = f"err: {exc}"  # pragma: no cover
    return 0


if __name__ == "__main__":
    if start_guard.is_set():
        raise RuntimeError("already started")
    start_guard.set()
    try:
        try:
            with DRV_LOCK:
                DRV.connect()
        except (PermissionError, FileNotFoundError) as exc:
            shared["status"] = f"port err: {exc}"
        except Exception as exc:  # pragma: no cover - init failure
            shared["status"] = f"init err: {exc}"  # pragma: no cover
        else:
            shared["status"] = "ok"
            poll_thread = threading.Thread(target=poller, daemon=True)
            poll_thread.start()

        app.run_server(
            debug=False,
            use_reloader=False,
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT_HTTP", "8050")),
        )
    finally:
        stop_event.set()
        if poll_thread is not None:
            poll_thread.join()
        with DRV_LOCK:
            DRV.close()
