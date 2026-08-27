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

# Perfil inicial da ComAp InteliGen 200 validado em campo via Modbus TCP.
IG200_POINTS = [
    {"key": "rpm", "label": "RPM", "address": 1000, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo: ~1800 rpm"},
    {"key": "voltage_l1", "label": "Generator Voltage L1-N", "address": 1036, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l2", "label": "Generator Voltage L2-N", "address": 1037, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l3", "label": "Generator Voltage L3-N", "address": 1038, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l1_l2", "label": "Generator Voltage L1-L2", "address": 1039, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l2_l3", "label": "Generator Voltage L2-L3", "address": 1040, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l3_l1", "label": "Generator Voltage L3-L1", "address": 1041, "count": 1, "function": 3, "datatype": "uint16", "scale": 1.0, "comment": "Validado em campo"},
    {"key": "frequency", "label": "Generator Frequency", "address": 1045, "count": 1, "function": 3, "datatype": "uint16", "scale": 0.01, "comment": "Validado em campo: valor bruto 6003 = 60.03 Hz"},
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
    """Carrega o perfil ativo.

    Aceita tanto os argumentos antigos (tipo, modelo, id) quanto um dicionário
    completo de gerador. Um perfil importado por gerador sempre tem prioridade.
    """
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
        # Demais ComAp só entram em polling depois de mapa oficial/exportado
        # importado. Isso evita aplicar um mapa de outra aplicação/firmware.
        return []

    if ctype == "DSE":
        return _genmon_points(ctype)

    raise ValueError(f"Controladora não suportada: {ctype}")


def profile_info(generator):
    """Resumo de perfil para API/UI, sem iniciar qualquer escrita Modbus."""
    ctype = str(generator.get("controller_type", "")).upper()
    model = generator.get("controller_model", "")
    gid = generator.get("id")
    catalog = find_controller_model(ctype, model) or {
        "model": model,
        "profile_key": None,
        "map_mode": "unknown",
        "profile_status": "unknown",
        "profile_label": "SEM PERFIL",
        "requires_import": True,
        "hint": "Modelo sem perfil catalogado.",
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
            "label": "MAPA IMPORTADO" if active_points else "MAPA SEM PONTOS ATIVOS",
            "active": bool(active_points),
            "requires_import": not bool(active_points),
            "source_name": imported.get("source_name", ""),
            "source_type": imported.get("source_type", "import"),
            "updated_at": imported.get("imported_at"),
            "points": len(all_points),
            "active_points": len(active_points),
            "catalog": catalog,
        }

    if catalog.get("profile_key") == "ig200":
        return {
            "state": "active_builtin",
            "label": "PERFIL RC VALIDADO",
            "active": True,
            "requires_import": False,
            "source_name": "RC Geradores / validação de campo",
            "source_type": "builtin",
            "updated_at": None,
            "points": len(IG200_POINTS),
            "active_points": len(IG200_POINTS),
            "catalog": catalog,
        }

    if ctype == "DSE":
        try:
            count = len(_genmon_points(ctype))
        except Exception:
            count = 0
        return {
            "state": "reference",
            "label": "PERFIL DE REFERÊNCIA",
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
        "state": "awaiting_import",
        "label": catalog.get("profile_label", "IMPORTAR MAPA"),
        "active": False,
        "requires_import": True,
        "source_name": "",
        "source_type": "",
        "updated_at": None,
        "points": 0,
        "active_points": 0,
        "catalog": catalog,
    }
