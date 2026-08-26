import json
import os
from pathlib import Path

GENMON_ROOT = Path(os.environ.get("GENMON_ROOT", "/opt/rc-scada/vendor/genmon"))
PROFILE_FILES = {
    "COMAP": "data/controller/ComAp.json",
    "DSE": "data/controller/Deepsea_controller.json",
}
WANTED = {
    "COMAP": {
        "Battery Voltage":"battery_voltage",
        "Oil Pressure":"oil_pressure",
        "Coolant Temperature":"coolant_temperature",
        "Fuel Level":"fuel_level",
        "Generator Frequency":"frequency",
        "Generator Voltage L1-N":"voltage_l1",
        "Generator Voltage L2-N":"voltage_l2",
        "Generator Voltage L3-N":"voltage_l3",
        "Generator Current L1":"current_l1",
        "Generator Current L2":"current_l2",
        "Generator Current L3":"current_l3",
        "Actual Power":"power_kw",
        "RPM":"rpm",
        "Run Hours":"run_hours",
        "Engine State":"engine_state_raw",
        "Controller Mode":"controller_mode_raw",
    },
    "DSE": {
        "Oil Pressure":"oil_pressure_raw",
        "Coolant Temperature":"coolant_temperature_raw",
        "Fuel Level":"fuel_level_raw",
        "Battery Voltage":"battery_voltage_raw",
        "RPM":"rpm_raw",
        "Frequency":"frequency_raw",
        "Output Voltage":"voltage_l1_raw",
        "Output Voltage L2":"voltage_l2_raw",
        "Output Voltage L3":"voltage_l3_raw",
        "Output Current":"current_l1_raw",
        "Output Current L2":"current_l2_raw",
        "Output Current L3":"current_l3_raw",
        "Output Power":"power_raw",
        "Run Hours":"run_hours_raw",
        "Switch State":"switch_state_raw",
        "Engine Operating State":"engine_state_raw",
    }
}

def _scale(comment):
    c=(comment or "").lower()
    if "tenths" in c:
        return 0.1
    if "hundredths" in c:
        return 0.01
    if "watts" in c:
        return 0.001
    if "mv" in c:
        return 0.001
    return 1.0

def load_points(controller_type):
    ctype=controller_type.upper()
    rel=PROFILE_FILES.get(ctype)
    if not rel:
        raise ValueError(f"Controladora não suportada: {ctype}")
    p=GENMON_ROOT / rel
    if not p.exists():
        raise FileNotFoundError(f"Perfil GenMon não encontrado: {p}")
    data=json.loads(p.read_text(encoding="utf-8"))
    wanted=WANTED[ctype]
    points=[]
    for addr, item in data.get("holding_registers",{}).items():
        text=item.get("text","")
        if text not in wanted:
            continue
        length=int(item.get("length",2))
        count=max(1, length//2)
        points.append({
            "key":wanted[text],
            "label":text,
            "address":int(addr,16),
            "count":count,
            "scale":_scale(item.get("comment","")),
            "comment":item.get("comment","")
        })
    return points
