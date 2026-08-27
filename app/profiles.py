import json
import os
from pathlib import Path

from . import db
from .controller_catalog import find_controller_model, profile_key_for_model

GENMON_ROOT = Path(os.environ.get("GENMON_ROOT", "/opt/rc-scada/vendor/genmon"))
PROFILE_FILES = {
    "COMAP": "data/controller/ComAp.json",
    "DSE": "data/controller/Deepsea_controller.json",
}

# ComAp InteliGen 200 - pontos confirmados em campo neste projeto.
IG200_POINTS = [
    {"key": "rpm", "label": "RPM", "address": 1000, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l1", "label": "Tensão gerador L1-N", "address": 1036, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l2", "label": "Tensão gerador L2-N", "address": 1037, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l3", "label": "Tensão gerador L3-N", "address": 1038, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l1_l2", "label": "Tensão gerador L1-L2", "address": 1039, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l2_l3", "label": "Tensão gerador L2-L3", "address": 1040, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l3_l1", "label": "Tensão gerador L3-L1", "address": 1041, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "frequency", "label": "Frequência gerador", "address": 1045, "count": 1, "function": 3, "datatype": "uint16", "scale": 0.01, "comment": "Validado em campo"},
]

# ComAp InteliCompact NT - somente leitura, conforme IL-NT / IA-NT / IC-NT
# Communication Guide. Os endereços abaixo são offsets Modbus (registro 4xxxx
# menos 40001). Nenhum comando de escrita é usado.
ICNT_POINTS = [
    {"key": "battery_voltage", "label": "Tensão bateria", "address": 57, "count": 1, "function": 3, "datatype": "int16", "scale": 0.1, "unit": "V", "comment": "IC-NT: registro 40058"},
    {"key": "oil_pressure", "label": "Pressão óleo", "address": 60, "count": 1, "function": 3, "datatype": "int16", "scale": 0.1, "unit": "bar", "comment": "IC-NT: registro 40061"},
    {"key": "coolant_temperature", "label": "Temperatura motor", "address": 61, "count": 1, "function": 3, "datatype": "int16", "scale": 1.0, "unit": "°C", "comment": "IC-NT: registro 40062"},
    {"key": "fuel_level", "label": "Nível combustível", "address": 62, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "unit": "%", "comment": "IC-NT: registro 40063"},
    {"key": "binary_inputs_raw", "label": "Entradas digitais", "address": 68, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "IC-NT: registro 40069"},
    {"key": "controller_mode_raw", "label": "Modo controladora", "address": 79, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "IC-NT: registro 40080"},
]

WANTED = {
    "COMAP": {
        "Battery Voltage": "battery_voltage",
        "Oil Pressure": "oil_pressure",
        "Coolant Temperature": "coolant_temperature",
        "Fuel Level": "fuel_level",
        "Generator Frequency": "frequency",
        "Generator Voltage L1-N": "voltage_l1",
        "Generator Voltage L2-N": "voltage_l2",
        "Generator Voltage L3-N": "voltage_l3",
        "Generator Current L1": "current_l1",
        "Generator Current L2": "current_l2",
        "Generator Current L3": "current_l3",
        "Actual Power": "power_kw",
        "RPM": "rpm",
        "Run Hours": "run_hours",
        "Engine State": "engine_state_raw",
        "Controller Mode": "controller_mode_raw",
    },
    "DSE": {
        "Oil Pressure": "oil_pressure_raw",
        "Coolant Temperature": "coolant_temperature_raw",
        "Fuel Level": "fuel_level_raw",
        "Battery Voltage": "battery_voltage_raw",
        "RPM": "rpm_raw",
        "Frequency": "frequency_raw",
        "Output Voltage": "voltage_l1_raw",
        "Output Voltage L2": "voltage_l2_raw",
        "Output Voltage L3": "voltage_l3_raw",
        "Output Current": "current_l1_raw",
        "Output Current L2": "current_l2_raw",
        "Output Current L3": "current_l3_raw",
        "Output Power": "power_raw",
        "Run Hours": "run_hours_raw",
        "Switch State": "switch_state_raw",
        "Engine Operating State": "engine_state_raw",
    },
}


def _scale(comment):
    c = (comment or "").lower()
    if "tenths" in c:
        return 0.1
    if "hundredths" in c:
        return 0.01
    if "watts" in c:
        return 0.001
    if "mv" in c:
        return 0.001
    return 1.0


def _genmon_points(ctype):
    rel = PROFILE_FILES.get(ctype)
    if not rel:
        raise ValueError(f"Controladora não suportada: {ctype}")

    p = GENMON_ROOT / rel
    if not p.exists():
        raise FileNotFoundError(f"Perfil GenMon não encontrado: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))
    wanted = WANTED[ctype]
    points = []

    for addr, item in data.get("holding_registers", {}).items():
        text = item.get("text", "")
        if text not in wanted:
            continue
        length = int(item.get("length", 2))
        count = max(1, length // 2)
        points.append(
            {
                "key": wanted[text],
                "label": text,
                "address": int(addr, 16),
                "count": count,
                "function": 3,
                "datatype": "uint16" if count == 1 else "uint32",
                "scale": _scale(item.get("comment", "")),
                "comment": item.get("comment", ""),
                "enabled": True,
            }
        )
    return points


def _imported_points(generator_id):
    if not generator_id:
        return []
    profile = db.get_generator_profile(generator_id)
    if not profile:
        return []
    return [
        dict(p)
        for p in profile.get("points", [])
        if p.get("enabled", True)
        and int(p.get("function", 3)) in (3, 4)
        and int(p.get("count", 1)) >= 1
    ]


def load_points(controller_type, controller_model=None, generator_id=None):
    if isinstance(controller_type, dict):
        g = controller_type
        ctype = str(g.get("controller_type", "")).upper()
        controller_model = g.get("controller_model")
        generator_id = g.get("id")
    else:
        ctype = str(controller_type or "").upper()

    imported = _imported_points(generator_id)
    if imported:
        return imported

    profile_key = profile_key_for_model(ctype, controller_model)

    if ctype == "COMAP":
        if profile_key == "ig200":
            return [dict(p, enabled=True) for p in IG200_POINTS]
        if profile_key == "icnt_nt":
            return [dict(p, enabled=True) for p in ICNT_POINTS]
        return []

    if ctype == "DSE":
        return _genmon_points(ctype)

    raise ValueError(f"Controladora não suportada: {ctype}")


def profile_info(generator):
    """Metadados internos de comunicação; a interface principal não os exibe."""
    ctype = str(generator.get("controller_type", "")).upper()
    model = generator.get("controller_model", "")
    gid = generator.get("id")
    catalog = find_controller_model(ctype, model) or {
        "model": model,
        "profile_key": None,
        "map_mode": "unknown",
        "profile_status": "unknown",
        "profile_label": "",
        "requires_import": True,
        "hint": "",
    }

    imported = db.get_generator_profile(gid) if gid else None
    if imported:
        all_points = imported.get("points", [])
        active_points = [
            p for p in all_points
            if p.get("enabled", True) and int(p.get("function", 3)) in (3, 4)
        ]
        return {
            "state": "active_imported" if active_points else "imported_no_active_points",
            "active": bool(active_points),
            "requires_import": not bool(active_points),
            "source_name": imported.get("source_name", ""),
            "source_type": imported.get("source_type", "import"),
            "updated_at": imported.get("imported_at"),
            "points": len(all_points),
            "active_points": len(active_points),
            "catalog": catalog,
        }

    builtin = None
    if catalog.get("profile_key") == "ig200":
        builtin = IG200_POINTS
    elif catalog.get("profile_key") == "icnt_nt":
        builtin = ICNT_POINTS

    if builtin is not None:
        return {
            "state": "active_builtin",
            "active": True,
            "requires_import": False,
            "source_name": "builtin",
            "source_type": "builtin",
            "updated_at": None,
            "points": len(builtin),
            "active_points": len(builtin),
            "catalog": catalog,
        }

    if ctype == "DSE":
        try:
            count = len(_genmon_points(ctype))
        except Exception:
            count = 0
        return {
            "state": "reference",
            "active": count > 0,
            "requires_import": False,
            "source_name": "GenMon",
            "source_type": "reference",
            "updated_at": None,
            "points": count,
            "active_points": count,
            "catalog": catalog,
        }

    return {
        "state": "awaiting_data",
        "active": False,
        "requires_import": True,
        "source_name": "",
        "source_type": "",
        "updated_at": None,
        "points": 0,
        "active_points": 0,
        "catalog": catalog,
    }
