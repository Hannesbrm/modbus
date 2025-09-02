# vsensor

Wiederverwendbare Kommunikationsbibliothek für den CMR Controls V‑Sensor.

## Installation

```bash
pip install -e .
```

## CLI

```bash
vsensor read telemetry
vsensor set mode 1
```

## Migration

| Alt                              | Neu                               |
|---------------------------------|-----------------------------------|
| `registers`                     | `vsensor.registers`               |
| `config.load_config()`          | `vsensor.config.Config.from_env()`|
| `modbus_driver.VSensorDriver`   | `vsensor.VSensorClient`           |

Die alte Oberfläche bleibt als Wrapper (`registers.py`, `config.py`, `modbus_driver.py`) erhalten, ist aber veraltet.

Weitere Beispiele und die Dash‑App finden sich im Verzeichnis `apps/`.
