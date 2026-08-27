import csv
import io
import json
import re
import unicodedata


ADDRESS_HEADERS = (
    "address",
    "modbus address",
    "register",
    "register address",
    "modbus register",
    "reg",
    "offset",
    "reg base",
    "endereco",
    "endereço",
)
NAME_HEADERS = (
    "name",
    "parameter",
    "description",
    "object",
    "signal",
    "nome",
    "parametro",
    "parâmetro",
    "descricao",
    "descrição",
)
TYPE_HEADERS = ("datatype", "data type", "type", "tipo de dado")
ACCESS_HEADERS = ("access", "r/w", "rw", "acesso")
FUNCTION_HEADERS = ("function", "modbus function", "fc", "funcao", "função")
SCALE_HEADERS = ("scale", "multiplier", "resolution", "factor", "fator", "resolucao", "resolução")
UNIT_HEADERS = ("unit", "units", "unidade")
COUNT_HEADERS = ("count", "register count", "length", "comprimento", "registros")


def _ascii(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(c for c in text if not unicodedata.combining(c))


def _norm(value):
    return " ".join(
        _ascii(value).lower().replace("_", " ").replace("-", " ").split()
    )


def _field(row, aliases):
    normalized = {_norm(k): v for k, v in row.items()}
    for alias in aliases:
        needle = _norm(alias)
        for key, value in normalized.items():
            if key == needle or needle in key:
                if str(value or "").strip():
                    return value, key
    return "", ""


def _decode(data):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível decodificar o arquivo")


def _slug(name):
    text = re.sub(r"[^a-z0-9]+", "_", _ascii(name).lower()).strip("_")
    return text[:80] or "point"


def _canonical_key(name):
    n = _norm(name)

    tests = [
        (("battery", "voltage"), "battery_voltage"),
        (("ubat",), "battery_voltage"),
        (("oil", "pressure"), "oil_pressure"),
        (("pressao", "oleo"), "oil_pressure"),
        (("coolant", "temperature"), "coolant_temperature"),
        (("engine", "temperature"), "coolant_temperature"),
        (("temperatura", "motor"), "coolant_temperature"),
        (("fuel", "level"), "fuel_level"),
        (("combustivel",), "fuel_level"),
        (("generator", "frequency"), "frequency"),
        (("frequencia", "gerador"), "frequency"),
        (("rpm",), "rpm"),
        (("engine", "speed"), "rpm"),
        (("run", "hours"), "run_hours"),
        (("engine", "hours"), "run_hours"),
        (("horas", "operacao"), "run_hours"),
        (("active", "power"), "power_kw"),
        (("potencia", "ativa"), "power_kw"),
        (("controller", "mode"), "controller_mode_raw"),
        (("modo", "control"), "controller_mode_raw"),
        (("engine", "state"), "engine_state_raw"),
        (("estado", "motor"), "engine_state_raw"),
    ]
    for words, key in tests:
        if all(w in n for w in words):
            return key

    phase_patterns = [
        (("voltage", "l1", "n"), "voltage_l1"),
        (("voltage", "l2", "n"), "voltage_l2"),
        (("voltage", "l3", "n"), "voltage_l3"),
        (("tensao", "l1", "n"), "voltage_l1"),
        (("tensao", "l2", "n"), "voltage_l2"),
        (("tensao", "l3", "n"), "voltage_l3"),
        (("voltage", "l1", "l2"), "voltage_l1_l2"),
        (("voltage", "l2", "l3"), "voltage_l2_l3"),
        (("voltage", "l3", "l1"), "voltage_l3_l1"),
        (("current", "l1"), "current_l1"),
        (("current", "l2"), "current_l2"),
        (("current", "l3"), "current_l3"),
        (("corrente", "l1"), "current_l1"),
        (("corrente", "l2"), "current_l2"),
        (("corrente", "l3"), "current_l3"),
    ]
    for words, key in phase_patterns:
        if all(w in n for w in words):
            return key

    return _slug(name)


def _parse_number(text):
    raw = str(text or "").strip().replace(" ", "")
    if not raw:
        return None
    raw = raw.replace(",", ".")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", raw)
    return float(m.group(0)) if m else None


def _parse_address(value, header_name="", function_hint=3):
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("endereço vazio")
    if "-" in raw and not raw.lower().startswith("0x"):
        nums = re.findall(r"\d+", raw)
        if len(nums) > 1:
            raise ValueError("faixa de registradores não suportada; exporte pontos individuais")

    if raw.lower().startswith("0x"):
        return int(raw, 16), function_hint

    nums = re.findall(r"\d+", raw.replace(".", ""))
    if not nums:
        raise ValueError(f"endereço inválido: {raw}")
    n = int(nums[0])
    h = _norm(header_name)

    if "offset" in h or "reg base" in h:
        return n, function_hint

    if 40001 <= n <= 49999:
        return n - 40001, 3
    if 30001 <= n <= 39999:
        return n - 30001, 4
    return n, function_hint


def _parse_function(value, address_function=3):
    text = _norm(value)
    if not text:
        return address_function
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if 3 in nums:
        return 3
    if 4 in nums:
        return 4
    raise ValueError("somente funções de leitura 03/04 são aceitas")


def _datatype_and_count(type_value, count_value):
    t = _norm(type_value)
    count_num = _parse_number(count_value)
    if count_num:
        count = max(1, min(64, int(count_num)))
    elif any(x in t for x in ("uint32", "int32", "float32", "dword", "double word")):
        count = 2
    else:
        count = 1

    if "float" in t:
        dtype = "float32" if count == 2 else "uint16"
    elif "int32" in t:
        dtype = "int32"
    elif "uint32" in t or "dword" in t:
        dtype = "uint32"
    elif "uint16" in t or "unsigned" in t:
        dtype = "uint16"
    elif "int16" in t or ("signed" in t and count == 1):
        dtype = "int16"
    else:
        dtype = "uint16" if count == 1 else "uint32"
    return dtype, count


def _scale(value, name, unit):
    num = _parse_number(value)
    if num is not None and 0 < abs(num) <= 1000000:
        return float(num)

    text = _norm(f"{value} {name} {unit}")
    for token, factor in (
        ("0.001", 0.001),
        ("0,001", 0.001),
        ("0.01", 0.01),
        ("0,01", 0.01),
        ("0.1", 0.1),
        ("0,1", 0.1),
    ):
        if token in str(value) or token in str(unit):
            return factor
    if "mv" in text:
        return 0.001
    return 1.0


def _readable(access):
    text = _norm(access)
    if not text:
        return True
    if "write only" in text or "somente escrita" in text:
        return False
    return True


def _rows_from_text(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    sample = "\n".join(lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        counts = {d: lines[0].count(d) for d in (";", "\t", ",", "|")}
        delimiter = max(counts, key=counts.get)

    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    if not reader.fieldnames:
        return []
    return [dict(row) for row in reader]


def _rows_from_json(text):
    obj = json.loads(text)
    if isinstance(obj, dict):
        obj = obj.get("points") or obj.get("registers") or obj.get("data") or []
    if not isinstance(obj, list):
        raise ValueError("JSON deve conter uma lista de registradores")
    return [x for x in obj if isinstance(x, dict)]


def parse_profile_upload(filename, data):
    """Retorna (points, warnings).

    O importador nunca cria comandos de escrita. Ele aceita somente FC03/FC04.
    Pontos reconhecidos como telemetria essencial ficam ativos; demais são
    armazenados desativados para revisão e futura seleção.
    """
    text = _decode(data)
    if filename.lower().endswith(".json"):
        rows = _rows_from_json(text)
    else:
        rows = _rows_from_text(text)

    if not rows:
        raise ValueError("arquivo sem tabela/registradores reconhecíveis")

    points = []
    warnings = []
    seen_keys = set()

    for idx, row in enumerate(rows, start=2):
        try:
            address_value, address_header = _field(row, ADDRESS_HEADERS)
            name, _ = _field(row, NAME_HEADERS)
            if not address_value or not name:
                continue

            access, _ = _field(row, ACCESS_HEADERS)
            if not _readable(access):
                continue

            function_value, _ = _field(row, FUNCTION_HEADERS)
            function_hint = 4 if str(address_value).strip().startswith("3") and len(re.findall(r"\d", str(address_value))) >= 5 else 3
            address, address_function = _parse_address(address_value, address_header, function_hint)
            function = _parse_function(function_value, address_function)

            type_value, _ = _field(row, TYPE_HEADERS)
            count_value, _ = _field(row, COUNT_HEADERS)
            datatype, count = _datatype_and_count(type_value, count_value)

            scale_value, _ = _field(row, SCALE_HEADERS)
            unit_value, _ = _field(row, UNIT_HEADERS)
            scale = _scale(scale_value, name, unit_value)

            key = _canonical_key(name)
            base_key = key
            suffix = 2
            while key in seen_keys:
                key = f"{base_key}_{suffix}"
                suffix += 1
            seen_keys.add(key)

            canonical = base_key in {
                "battery_voltage",
                "oil_pressure",
                "coolant_temperature",
                "fuel_level",
                "frequency",
                "rpm",
                "run_hours",
                "power_kw",
                "controller_mode_raw",
                "engine_state_raw",
                "voltage_l1",
                "voltage_l2",
                "voltage_l3",
                "voltage_l1_l2",
                "voltage_l2_l3",
                "voltage_l3_l1",
                "current_l1",
                "current_l2",
                "current_l3",
            }

            points.append(
                {
                    "key": key,
                    "label": str(name).strip(),
                    "address": int(address),
                    "count": int(count),
                    "function": int(function),
                    "datatype": datatype,
                    "scale": float(scale),
                    "unit": str(unit_value or "").strip(),
                    "access": str(access or "").strip(),
                    "enabled": bool(canonical),
                    "comment": "Importado do mapa da controladora; polling somente leitura.",
                }
            )
        except Exception as e:
            warnings.append(f"linha {idx}: {e}")

    if not points:
        raise ValueError("nenhum registrador legível foi reconhecido")

    if len(points) > 2000:
        raise ValueError("mapa muito grande; limite de 2000 registradores")

    return points, warnings[:100]
