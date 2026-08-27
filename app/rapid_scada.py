import json
import os
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
BINDINGS_FILE = Path(os.environ.get("RC_RAPID_BINDINGS", BASE_DIR / "rapid" / "bindings.json"))
READER_DLL = Path(os.environ.get("RC_RAPID_READER", BASE_DIR / ".rapid-reader" / "RcRapidReader.dll"))
COMM_CONFIG = Path(os.environ.get("RC_RAPID_COMM_CONFIG", "/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"))
CACHE_TTL = float(os.environ.get("RC_RAPID_CACHE_TTL", "1.5"))

_cache = {"at": 0.0, "channels": {}, "error": ""}


def _load_bindings():
    try:
        data = json.loads(BINDINGS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _binding_for(generator, bindings):
    ctype = str(generator.get("controller_type", "")).upper()
    model = str(generator.get("controller_model", "")).strip().lower()
    port = int(generator.get("listen_port") or 0)
    unit = int(generator.get("modbus_unit") or 0)
    for item in bindings:
        if (
            str(item.get("controller_type", "")).upper() == ctype
            and str(item.get("controller_model", "")).strip().lower() == model
            and int(item.get("listen_port") or 0) == port
            and int(item.get("modbus_unit") or 0) == unit
        ):
            return item
    return None


def _read_channels(channel_nums):
    nums = sorted({int(n) for n in channel_nums})
    if not nums:
        return {}, ""

    now = time.monotonic()
    if now - _cache["at"] < CACHE_TTL and all(n in _cache["channels"] for n in nums):
        return {n: _cache["channels"][n] for n in nums}, _cache["error"]

    if not READER_DLL.exists():
        return {}, f"Leitor Rapid SCADA não instalado: {READER_DLL}"
    if not COMM_CONFIG.exists():
        return {}, f"Configuração Rapid SCADA não encontrada: {COMM_CONFIG}"

    cmd = ["dotnet", str(READER_DLL), str(COMM_CONFIG), *[str(n) for n in nums]]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=4, check=False)
    except Exception as e:
        return {}, f"Falha ao consultar Rapid SCADA: {e}"

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "erro desconhecido").strip()
        return {}, f"Rapid SCADA: {detail[:300]}"

    try:
        payload = json.loads(proc.stdout)
        channels = {
            int(item["cnl"]): {
                "val": item.get("val", 0),
                "stat": int(item.get("stat", 0)),
                "defined": bool(item.get("defined", False)),
            }
            for item in payload.get("channels", [])
        }
    except Exception as e:
        return {}, f"Resposta inválida do Rapid SCADA: {e}"

    _cache["at"] = now
    _cache["channels"] = channels
    _cache["error"] = ""
    return channels, ""


def overlay_generators(generators):
    """Substitui a telemetria de geradores vinculados pelos dados atuais do Rapid SCADA."""
    bindings = _load_bindings()
    matched = []
    all_channels = []

    for generator in generators:
        binding = _binding_for(generator, bindings)
        matched.append(binding)
        if binding:
            for cfg in (binding.get("channels") or {}).values():
                if "cnl" in cfg:
                    all_channels.append(int(cfg["cnl"]))

    channel_data, read_error = _read_channels(all_channels)
    now = int(time.time())
    result = []

    for generator, binding in zip(generators, matched):
        if not binding:
            result.append(generator)
            continue

        out = dict(generator)
        values = {}
        defined_count = 0
        for key, cfg in (binding.get("channels") or {}).items():
            cnl = int(cfg["cnl"])
            item = channel_data.get(cnl)
            if not item or not item.get("defined"):
                continue
            defined_count += 1
            scale = float(cfg.get("scale", 1.0))
            value = float(item.get("val", 0)) * scale
            if abs(value - round(value)) < 1e-9 and key != "frequency":
                value = int(round(value))
            else:
                value = round(value, 3)
            values[key] = value

        if read_error:
            out.update(
                {
                    "connected": False,
                    "poll_ok": False,
                    "last_error": read_error,
                    "status": "fault",
                    "values": {},
                    "telemetry_source": "rapid_scada",
                }
            )
        elif defined_count > 0:
            out.update(
                {
                    "connected": True,
                    "poll_ok": True,
                    "peer": "Rapid SCADA Server",
                    "last_seen": now,
                    "last_error": "",
                    "status": "online",
                    "values": values,
                    "telemetry_source": "rapid_scada",
                    "rapid_device_num": binding.get("rapid_device_num"),
                }
            )
        else:
            out.update(
                {
                    "connected": True,
                    "poll_ok": False,
                    "peer": "Rapid SCADA Server",
                    "last_seen": now,
                    "last_error": "Rapid SCADA conectado, canais ainda sem dados definidos",
                    "status": "connected",
                    "values": {},
                    "telemetry_source": "rapid_scada",
                    "rapid_device_num": binding.get("rapid_device_num"),
                }
            )

        result.append(out)

    return result


def dashboard_from_generators(generators):
    online = connected = operating = alarm = offline = 0
    for g in generators:
        status = g.get("status", "offline")
        if status == "online":
            online += 1
        elif status == "connected":
            connected += 1
        elif status == "fault":
            alarm += 1
        else:
            offline += 1

        rpm = (g.get("values") or {}).get("rpm")
        if isinstance(rpm, (int, float)) and rpm > 300:
            operating += 1

    return {
        "total": len(generators),
        "online": online,
        "connected": connected,
        "offline": offline,
        "operating": operating,
        "alarm": alarm,
    }
