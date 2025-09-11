"""Simple dashboard for VSensor with lazy client initialisation."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Optional

from dash import Dash, Input, Output, State, dcc, html, ctx

from vsensor import registers as REG
from vsensor.client import VSensorClient
from vsensor.config import Config
from vsensor.errors import TimeoutError, TransportError, VSensorError


logger = logging.getLogger(__name__)


@dataclass
class _Ctx:
    cfg: dict[str, Any]
    client: Optional[VSensorClient] = None


CTX = _Ctx(cfg={k.upper(): v for k, v in asdict(Config.from_env()).items()})


def _try_connect(cfg: dict[str, Any]) -> tuple[Optional[VSensorClient], str]:
    """Try to create a client with retries."""
    err = ""
    for delay in (0.0, 0.2, 0.5):
        try:
            client = VSensorClient(Config(**cfg))
            client.connect()
            return client, ""
        except Exception as exc:  # pragma: no cover - hardware specific
            err = str(exc)
            logger.info("connect failed: %s", err)
            time.sleep(delay)
    return None, err


def _call(
    state: dict[str, Any], func: Callable[[VSensorClient], Any]
) -> tuple[Any | None, dict[str, Any]]:
    """Call *func* with active client and handle errors."""
    client = CTX.client
    if not state.get("connected") or client is None:
        return None, {**state, "connected": False, "error": "Keine Verbindung"}
    try:
        result = func(client)
        return result, {**state, "error": ""}
    except (TimeoutError, TransportError, VSensorError) as exc:
        logger.info("client error: %s", exc)
        try:
            client.close()
        finally:
            CTX.client = None
        return None, {"connected": False, "error": str(exc)}


app = Dash(__name__)
app.layout = html.Div(
    className="container",
    children=[
        dcc.Store(id="state", data={"connected": False, "error": ""}),
        html.Div(
            id="alert",
            className="alert-banner",
            children=[
                html.Span(id="alert_msg"),
                html.Button("Erneut verbinden", id="btn_reconnect", className="btn"),
            ],
        ),
        html.Div(
            className="card connection",
            children=[
                html.Div(
                    className="conn-fields",
                    children=[
                        html.Div(
                            [
                                html.Label("Port", htmlFor="cfg_port"),
                                dcc.Input(
                                    id="cfg_port",
                                    type="text",
                                    value=CTX.cfg["PORT"],
                                    placeholder="/dev/ttyUSB0",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Slave-ID", htmlFor="cfg_slave"),
                                dcc.Input(
                                    id="cfg_slave",
                                    type="number",
                                    value=CTX.cfg["SLAVE_ID"],
                                    min=1,
                                    max=247,
                                    placeholder="1–247",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Baudrate", htmlFor="cfg_baud"),
                                dcc.Input(
                                    id="cfg_baud",
                                    type="number",
                                    value=CTX.cfg["BAUDRATE"],
                                    min=1200,
                                    placeholder="9600",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Parität", htmlFor="cfg_parity"),
                                dcc.Dropdown(
                                    id="cfg_parity",
                                    options=[{"label": p, "value": p} for p in ["N", "E", "O"]],
                                    value=CTX.cfg["PARITY"],
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Stopbits", htmlFor="cfg_stopbits"),
                                dcc.Input(
                                    id="cfg_stopbits",
                                    type="number",
                                    value=CTX.cfg["STOPBITS"],
                                    min=1,
                                    max=2,
                                    placeholder="1",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Float-Format", htmlFor="cfg_ff"),
                                dcc.Dropdown(
                                    id="cfg_ff",
                                    options=[{"label": str(i), "value": i} for i in range(4)],
                                    value=CTX.cfg["FLOAT_FORMAT"],
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Button("Verbinden", id="btn_connect", className="btn"),
                    ],
                ),
                html.Span(id="status", className="badge disconnected"),
            ],
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
                                        html.Div(id="auto_sp", className="value skeleton"),
                                        html.Div("Displaywert", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="pressure", className="value skeleton"),
                                        html.Div("Druck [Pa]", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="output", className="value skeleton"),
                                        html.Div("Ausgang [%]", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="mode", className="value skeleton"),
                                        html.Div("Modus", className="label"),
                                    ],
                                ),
                                html.Div(
                                    className="mini-card",
                                    children=[
                                        html.Div(id="hb", className="value skeleton"),
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
                                html.Label("Auto-Sollwert", htmlFor="new_sp"),
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
                                html.Label("Hand-Soll [%]", htmlFor="new_sp_hand"),
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
        dcc.Interval(id="tick", interval=1000, n_intervals=0, disabled=True),
    ],
)


@app.callback(
    Output("state", "data"),
    Output("tick", "disabled"),
    Output("btn_connect", "n_clicks"),
    Output("btn_reconnect", "n_clicks"),
    Input("btn_connect", "n_clicks"),
    Input("btn_reconnect", "n_clicks"),
    State("cfg_port", "value"),
    State("cfg_slave", "value"),
    State("cfg_baud", "value"),
    State("cfg_parity", "value"),
    State("cfg_stopbits", "value"),
    State("cfg_ff", "value"),
    State("state", "data"),
    prevent_initial_call=True,
)
def connect(_, __, port, slave, baud, parity, stopbits, ff, state):
    if not ctx.triggered_id:
        return state, True, 0, 0
    cfg = {
        "PORT": port or CTX.cfg["PORT"],
        "SLAVE_ID": int(slave) if slave is not None else CTX.cfg["SLAVE_ID"],
        "BAUDRATE": int(baud) if baud is not None else CTX.cfg["BAUDRATE"],
        "PARITY": parity or CTX.cfg["PARITY"],
        "STOPBITS": int(stopbits) if stopbits is not None else CTX.cfg["STOPBITS"],
        "BYTESIZE": CTX.cfg["BYTESIZE"],
        "TIMEOUT": CTX.cfg["TIMEOUT"],
        "FLOAT_FORMAT": int(ff) if ff is not None else CTX.cfg["FLOAT_FORMAT"],
    }
    client, err = _try_connect(cfg)
    if client is None:
        state = {"connected": False, "error": err}
        return state, True, 0, 0
    CTX.client = client
    CTX.cfg.update(cfg)
    state = {"connected": True, "error": ""}
    return state, False, 0, 0


@app.callback(
    Output("pressure", "children"),
    Output("output", "children"),
    Output("auto_sp", "children"),
    Output("mode", "children"),
    Output("hb", "children"),
    Output("status", "children"),
    Output("state", "data"),
    Input("tick", "n_intervals"),
    State("state", "data"),
)
def update_view(_, state):
    def read_all(c: VSensorClient):
        return (
            c.read_pressure(),
            c.read_output(),
            c.read_auto_setpoint(),
            c.read_mode().name,
            c.read_u16(REG.HEARTBEAT),
        )

    values, state = _call(state, read_all)
    if values is None:
        vals = ["—", "—", "—", "—", "—"]
    else:
        p, o, sp, mode, hb = values
        vals = [f"{p:.1f}", f"{o:.1f} %", f"{sp:.1f}", mode, hb]
    status = (
        f"Verbunden – {CTX.cfg['PORT']}, ID {CTX.cfg['SLAVE_ID']}, FF {CTX.cfg['FLOAT_FORMAT']}"
        if state.get("connected")
        else "Getrennt"
    )
    return vals[0], vals[1], vals[2], vals[3], vals[4], status, state


@app.callback(
    Output("state", "data"),
    Output("btn_set_sp", "n_clicks"),
    Input("btn_set_sp", "n_clicks"),
    State("new_sp", "value"),
    State("state", "data"),
    prevent_initial_call=True,
)
def set_sp(_, val, state):
    if val is None or not (0 <= float(val) <= 5000):
        state["error"] = "ungültiger Wert"
        return state, 0

    def do(c: VSensorClient) -> None:
        c.set_auto_setpoint(float(val))

    _, state = _call(state, do)
    return state, 0


@app.callback(
    Output("state", "data"),
    Output("btn_set_hand", "n_clicks"),
    Input("btn_set_hand", "n_clicks"),
    State("new_sp_hand", "value"),
    State("state", "data"),
    prevent_initial_call=True,
)
def set_hand(_, val, state):
    if val is None or not (0 <= float(val) <= 100):
        state["error"] = "ungültiger Wert"
        return state, 0

    def do(c: VSensorClient) -> None:
        c.write_float(REG.HAND_SETPOINT_PERCENT, float(val))

    _, state = _call(state, do)
    return state, 0


@app.callback(
    Output("state", "data"),
    Output("btn_set_mode", "n_clicks"),
    Input("btn_set_mode", "n_clicks"),
    State("mode_dd", "value"),
    State("state", "data"),
    prevent_initial_call=True,
)
def set_mode(_, val, state):
    if val is None or int(val) not in {1, 2, 3, 4}:
        state["error"] = "ungültiger Wert"
        return state, 0

    def do(c: VSensorClient) -> None:
        c.set_mode(int(val))

    _, state = _call(state, do)
    return state, 0


@app.callback(
    Output("new_sp", "disabled"),
    Output("btn_set_sp", "disabled"),
    Output("new_sp_hand", "disabled"),
    Output("btn_set_hand", "disabled"),
    Output("mode_dd", "disabled"),
    Output("btn_set_mode", "disabled"),
    Input("state", "data"),
)
def toggle_controls(state):
    disabled = [not state.get("connected")] * 6
    return disabled


@app.callback(Output("status", "className"), Input("state", "data"))
def status_class(state):
    return "badge connected" if state.get("connected") else "badge disconnected"


@app.callback(
    Output("alert", "className"),
    Output("alert_msg", "children"),
    Input("state", "data"),
)
def show_alert(state):
    err = state.get("error")
    if err:
        return "alert-banner show", err
    return "alert-banner", ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG if os.getenv("VSENSOR_DEBUG") else logging.INFO)
    app.run(
        debug=False,
        use_reloader=False,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT_HTTP", "8050")),
    )
