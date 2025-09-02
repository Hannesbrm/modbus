# vsensor

Wiederverwendbare Kommunikationsbibliothek für den CMR Controls V‑Sensor.

## Installation

```bash
pip install -e .
```

## Getting Started

Auf einem Raspberry Pi sollte der Benutzer zur Gruppe `dialout` gehören und
ggf. eine passende `udev`-Regel für das USB‑Seriell‑Gerät vorhanden sein.
Die Registeradressen in `vsensor.registers` sind 1‑basiert; der Client
konvertiert sie automatisch auf 0‑basierte Modbus‑Adressen.

```bash
export VSENSOR_PORT=/dev/ttyUSB0
vsensor --baud 9600 --slave 1 read telemetry
```

## CLI

```bash
vsensor --port /dev/ttyUSB0 --baud 9600 read telemetry
vsensor --float-format 1 set mode 1
```

## Migration

| Alt                              | Neu                               |
|---------------------------------|-----------------------------------|
| `registers`                     | `vsensor.registers`               |
| `config.load_config()`          | `vsensor.config.Config.from_env()`|
| `modbus_driver.VSensorDriver`   | `vsensor.VSensorClient`           |

Die alte Oberfläche bleibt als Wrapper (`registers.py`, `config.py`, `modbus_driver.py`) erhalten, ist aber veraltet.

Weitere Beispiele und die Dash‑App finden sich im Verzeichnis `apps/`.
