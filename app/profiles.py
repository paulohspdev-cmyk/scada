import json
import os
from pathlib import Path

GENMON_ROOT = Path(os.environ.get("GENMON_ROOT", "/opt/rc-scada/vendor/genmon"))
PROFILE_FILES = {
    "COMAP": "data/controller/ComAp.json",
    "DSE": "data/controller/Deepsea_controller.json",
}

# Perfil inicial da ComAp InteliGen 200 validado em campo via Modbus TCP.
# Mantemos somente pontos de alta confiança por enquanto. Outros pontos serão
# adicionados conforme forem confirmados contra o display/configuração da IG200.
IG200_POINTS = [
    {"key": "rpm", "label": "RPM", "address": 1000, "count": 1, "scale": 1.0, "comment": "Validado em campo: ~1800 rpm"},
    {"key": "voltage_l1", "label": "Generator Voltage L1-N", "address": 1036, "count": 1, "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l2", "label": "Generator Voltage L2-N", "address": 1037, "count": 1, "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l3", "label": "Generator Voltage L3-N", "address": 1038, "count": 1, "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l1_l2", "label": "Generator Voltage L1-L2", "address": 1039, "count": 1, "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l2_l3", "label": "Generator Voltage L2-L3", "address": 1040, "count": 1, "scale": 1.0, "comment": "Validado em campo"},
    {"key": "voltage_l3_l1", "label": "Generator Voltage L3-L1", "address": 1041, "count": 1, "scale": 1.0, "comment": "Validado em campo"},
    {"key": "frequency", "label": "Generator Frequency", "address": 1045, "count": 1, "scale": 0.01, "comment": "Validado em campo: valor bruto 6003 = 60.03 Hz"},
]

# A InteliCompact NT do site está na mesma rede RS485 da IG200, mas seu mapa
# ainda não foi validado. Não usamos o perfil ComAp genérico aqui porque pontos
# incorretos podem gerar timeouts/respostas tardias e atrapalhar os outros Unit
# IDs da mesma conexão TCP. Ela fica cadastrada e online, porém sem polling de
# registradores até concluirmos o mapeamento read-only.
ICNT_POINTS = []

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


def load_points(controller_type, controller_model=None):
    ctype = controller_type.upper()
    model = (controller_model or "").upper().replace("-", " ")

    if ctype == "COMAP" and (
        "INTELIGEN 200" in model or "IG200" in model or "IG 200" in model
    ):
        return [dict(p) for p in IG200_POINTS]

    if ctype == "COMAP" and (
        "INTELICOMPACT NT" in model
        or "INTELICOMPACT" in model
        or "ICNT" in model
        or "IC NT" in model
    ):
        return [dict(p) for p in ICNT_POINTS]

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
                "scale": _scale(item.get("comment", "")),
                "comment": item.get("comment", ""),
            }
        )

    return points
