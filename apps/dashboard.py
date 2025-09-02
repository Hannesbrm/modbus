import os
import threading
from dataclasses import asdict
from typing import Any, Optional

from dash import Dash, Input, Output, State, dcc, html

from vsensor import registers as REG
from vsensor.client import VSensorClient
from vsensor.config import Config

# ---- Globale Treiberinstanz ----
CFG = asdict(Config.from_env())
DRV = VSensorClient(Config(**CFG))

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
            shared["pressure_pa"] = DRV.read_pressure()
            shared["output_pct"] = DRV.read_output()
            shared["auto_sp"] = DRV.read_auto_setpoint()
            shared["mode"] = DRV.read_mode()
            shared["hb"] = DRV.read_u16(REG.HEARTBEAT)
            shared["status"] = "ok"
        except TimeoutError:
            shared["status"] = "timeout"
        except Exception as exc:  # pragma: no cover - debugging
            shared["status"] = f"err: {exc}"  # pragma: no cover
        stop_event.wait(CFG["POLL_INTERVAL_SEC"])

app = Dash(__name__)
app.layout = html.Div(
    className="container",
    children=[
        dcc.Loading(
            type="circle",
            children=html.Div(
                className="card connection",
                children=[
                    html.Div(
                        className="conn-fields",
                        children=[
                            html.Div(
                                [
                                    html.Label(
                                        "Port",
                                        htmlFor="cfg_port",
                                        title="Serieller Port, z.B. /dev/ttyUSB0",
                                    ),
                                    dcc.Input(
                                        id="cfg_port",
                                        type="text",
                                        value=CFG["PORT"],
                                        placeholder="/dev/ttyUSB0",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Slave-ID",
                                        htmlFor="cfg_slave",
                                        title="Adresse des V-Sensors, Standard 1–247",
                                    ),
                                    dcc.Input(
                                        id="cfg_slave",
                                        type="number",
                                        value=CFG["SLAVE_ID"],
                                        min=1,
                                        max=247,
                                        placeholder="1–247",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Baudrate",
                                        htmlFor="cfg_baud",
                                        title="Übertragungsgeschwindigkeit",
                                    ),
                                    dcc.Input(
                                        id="cfg_baud",
                                        type="number",
                                        value=CFG["BAUD"],
                                        min=1200,
                                        placeholder="9600",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Parität",
                                        htmlFor="cfg_parity",
                                        title="N = none, E = even, O = odd",
                                    ),
                                    dcc.Dropdown(
                                        id="cfg_parity",
                                        options=[{"label": p, "value": p} for p in ["N", "E", "O"]],
                                        value=CFG["PARITY"],
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Stopbits",
                                        htmlFor="cfg_stopbits",
                                        title="Anzahl Stopbits",
                                    ),
                                    dcc.Input(
                                        id="cfg_stopbits",
                                        type="number",
                                        value=CFG["STOPBITS"],
                                        min=1,
                                        max=2,
                                        placeholder="1",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Float-Format",
                                        htmlFor="cfg_ff",
                                        title="0–3, Byte-Reihenfolge des Sensors",
                                    ),
                                    dcc.Dropdown(
                                        id="cfg_ff",
                                        options=[{"label": str(i), "value": i} for i in range(4)],
                                        value=CFG["FLOAT_FORMAT"],
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Button("Verbinden/Übernehmen", id="btn_connect", className="btn"),
                        ],
                    ),
                    html.Span(id="status", className="badge disconnected"),
                ],
            ),
        ),
        html.Div(
            className="main-grid",
            children=[
                html.Div(
                    className="card",
                    children=[
                        html.H3("Live-Werte"),
                        html.Div(
                            className="live-grid",
                            children=[
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="auto_sp", className="value"),
                                        html.Div("Displaywert", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="pressure", className="value"),
                                        html.Div("Druck [Pa]", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="output", className="value"),
                                        html.Div("Ausgang [%]", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="mode", className="value"),
                                        html.Div("Modus", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="hb", className="value"),
                                        html.Div("Heartbeat", className="label"),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="card",
                    children=[
                        html.H3("Steuerung"),
                        html.Div(
                            className="ctrl-field",
                            children=[
                                html.Label(
                                    "Auto-Sollwert",
                                    htmlFor="new_sp",
                                    title="Sollwert im Automatikmodus",
                                ),
                                dcc.Input(
                                    id="new_sp",
                                    type="number",
                                    min=0,
                                    max=5000,
                                    placeholder="0–5000",
                                ),
                                html.Button("Setze Auto-Sollwert", id="btn_set_sp", className="btn"),
                            ],
                        ),
                        html.Div(
                            className="ctrl-field",
                            children=[
                                html.Label(
                                    "Hand-Soll [%]",
                                    htmlFor="new_sp_hand",
                                    title="Sollwert im Handbetrieb",
                                ),
                                dcc.Input(
                                    id="new_sp_hand",
                                    type="number",
                                    min=0,
                                    max=100,
                                    placeholder="0–100",
                                ),
                                html.Button("Setze Hand-Sollwert", id="btn_set_hand", className="btn"),
                            ],
                        ),
                        html.Div(
                            className="ctrl-field",
                            children=[
                                dcc.Dropdown(
                                    id="mode_dd",
                                    options=[
                                        {"label": "AUTO", "value": 1},
                                        {"label": "HAND@SP", "value": 2},
                                        {"label": "OFF", "value": 3},
                                        {"label": "HAND@Output", "value": 4},
                                    ],
                                    value=1,
                                    clearable=False,
                                ),
                                html.Button("Setze Modus", id="btn_set_mode", className="btn"),
                            ],
                        ),
                        html.Div(id="msg", className="msg"),
                    ],
                ),
            ],
        ),
        html.Div(
            "9600 8N1, RS-485 2-Draht; Float-Format 0–3 siehe Handbuch",
            className="hint",
        ),
        dcc.Interval(id="tick", interval=1000, n_intervals=0),
        html.Div(id="toast", className="toast"),
    ],
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

    mode_map = {1: "AUTO", 2: "HAND@SP", 3: "OFF", 4: "HAND@Output"}
    stat = shared.get("status")
    if stat == "ok":
        status_txt = "Verbunden"
    elif stat == "connecting":
        status_txt = "Verbinden…"
    elif stat in {"init"}:
        status_txt = "Getrennt"
    else:
        status_txt = f"Fehler ({stat})"
    params = f"{CFG['PORT']}, ID {CFG['SLAVE_ID']}, FF {CFG['FLOAT_FORMAT']}"
    status_full = f"{status_txt} – {params}"
    return (
        fmt(shared["pressure_pa"], "{:.1f}"),
        (fmt(shared["output_pct"], "{:.1f}") + " %")
        if isinstance(shared["output_pct"], (int, float))
        else "—",
        fmt(shared["auto_sp"], "{:.1f}"),
        mode_map.get(shared["mode"], "—"),
        shared["hb"] if isinstance(shared["hb"], int) else "—",
        status_full,
    )


@app.callback(
    Output("btn_set_sp", "n_clicks"),
    Input("btn_set_sp", "n_clicks"),
    State("new_sp", "value"),
    prevent_initial_call=True,
)
def set_sp(_, val):
    if val is None or not (0 <= float(val) <= 5000):
        shared["status"] = "invalid"
        return 0
    try:
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
    if val is None or not (0 <= float(val) <= 100):
        shared["status"] = "invalid"
        return 0
    try:
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
    shared["status"] = "connecting"
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

    DRV.close()
    DRV = VSensorClient(Config(**cfg))
    try:
        DRV.transport  # ensure connection is opened on init
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
    if val is None or int(val) not in {1, 2, 3, 4}:
        shared["status"] = "invalid"
        return 0
    try:
        DRV.set_mode(int(val))
        shared["status"] = "write ok"
    except TimeoutError:
        shared["status"] = "timeout"
    except Exception as exc:  # pragma: no cover - debugging
        shared["status"] = f"err: {exc}"  # pragma: no cover
    return 0


@app.callback(
    Output("new_sp", "disabled"),
    Output("btn_set_sp", "disabled"),
    Output("new_sp_hand", "disabled"),
    Output("btn_set_hand", "disabled"),
    Output("mode_dd", "disabled"),
    Output("btn_set_mode", "disabled"),
    Input("tick", "n_intervals"),
)
def toggle_controls(_):
    connected = shared.get("status") == "ok"
    disabled = [not connected] * 6
    return disabled


@app.callback(
    Output("status", "className"),
    Input("tick", "n_intervals"),
)
def status_class(_):
    return "badge connected" if shared.get("status") == "ok" else "badge disconnected"


@app.callback(
    Output("toast", "children"),
    Output("toast", "className"),
    Output("msg", "children"),
    Input("tick", "n_intervals"),
)
def feedback(_):
    stat = shared.get("status")
    if stat == "write ok":
        shared["status"] = "ok"
        return "Wert geschrieben", "toast show", ""
    if stat in {"timeout", "invalid"} or str(stat).startswith("err"):
        return "", "toast", f"Fehler: {stat}"
    return "", "toast", ""


if __name__ == "__main__":
    if start_guard.is_set():
        raise RuntimeError("already started")
    start_guard.set()
    try:
        try:
            DRV.transport  # already connected
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
        DRV.close()
