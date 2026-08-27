"""Catálogo de controladoras e estratégia de perfil Modbus.

A seleção do modelo é separada do mapa de registradores. Perfis de fábrica só
entram em polling quando foram validados neste projeto. Para controladoras cujo
mapa é configurável, o RC SCADA importa o CSV/TXT/JSON exportado do
InteliConfig/LiteEdit e cria um perfil por gerador.
"""


def _m(
    family,
    model,
    profile_key,
    map_mode,
    profile_status,
    profile_label,
    hint,
    aliases=(),
):
    return {
        "brand": "COMAP",
        "family": family,
        "model": model,
        "profile_key": profile_key,
        "map_mode": map_mode,
        "profile_status": profile_status,
        "profile_label": profile_label,
        "requires_import": profile_status in ("import_required", "guide_required"),
        "hint": hint,
        "aliases": list(aliases),
    }


DYNAMIC = (
    "Mapa configurável por aplicação. Exporte o mapa do InteliConfig e importe "
    "no RC SCADA; o arquivo vira o perfil Modbus deste gerador."
)
LEGACY = (
    "Família legada. Importe o mapa exportado pelo LiteEdit/GenConfig ou um mapa "
    "validado do Communication Guide para este modelo/firmware."
)
FIELD = (
    "Perfil RC validado em campo. O modelo já carrega automaticamente os pontos "
    "homologados; um mapa importado pode complementar/substituir esse perfil."
)
NO_DIRECT = (
    "A disponibilidade de Modbus depende da versão/interface instalada. O RC "
    "SCADA mantém o modelo no catálogo, mas exige mapa/integração validada."
)

COMAP_MODELS = [
    _m("InteliLite", "InteliLite 4 AMF 25", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliLite", "InteliLite 4 AMF 20", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliLite", "InteliLite 4 MRS 16", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliLite", "InteliLite 4 MRS 11", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliLite", "InteliLite 4 AMF 9", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliLite", "InteliNano AMF 5", "no_profile", "interface_dependent", "guide_required", "VALIDAR INTERFACE", NO_DIRECT),
    _m("InteliLite", "InteliNano MRS 3", "no_profile", "interface_dependent", "guide_required", "VALIDAR INTERFACE", NO_DIRECT),

    _m("InteliLite NT", "InteliLite NT AMF 25", "legacy_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY, ("IL-NT AMF25",)),
    _m("InteliLite NT", "InteliLite NT AMF 20", "legacy_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY, ("IL-NT AMF20",)),
    _m("InteliLite NT", "InteliLite NT MRS 16", "legacy_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY, ("IL-NT MRS16",)),
    _m("InteliLite NT", "InteliLite NT MRS 10", "legacy_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY),
    _m("InteliLite NT", "InteliLite NT MRS 3", "legacy_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY),

    _m("InteliGen", "InteliGen 1000", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliGen", "InteliGen 1000 SC", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliGen", "InteliGen 500 G2", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliGen", "InteliGen4 200", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC, ("InteliGen 4 200", "IG4 200")),
    _m("InteliGen", "InteliGen 200", "ig200", "field_validated", "validated", "PERFIL RC", FIELD, ("IG200", "IG 200")),

    _m("InteliGen NT", "InteliGen NT", "legacy_export", "legacy_export", "guide_required", "MAPA LEGADO", LEGACY, ("IG-NT",)),
    _m("InteliCompact NT", "InteliCompact NT MINT", "icnt_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY, ("IC-NT MINT", "ICNT MINT")),
    _m("InteliCompact NT", "InteliCompact NT SPtM", "icnt_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY, ("IC-NT SPTM", "ICNT SPTM")),
    _m("InteliCompact NT", "InteliCompact NT", "icnt_nt", "legacy_guide", "guide_required", "MAPA LEGADO", LEGACY, ("ICNT", "IC NT")),

    _m("InteliSys", "InteliSys 2000", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliSys", "InteliSys Gas", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliSys", "InteliSys NTC BaseBox", "legacy_export", "legacy_export", "guide_required", "MAPA LEGADO", LEGACY),

    _m("InteliATS", "InteliATS2 70", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliATS", "InteliATS2 50", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),

    _m("InteliNeo", "InteliNeo 6000", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliNeo", "InteliNeo 5500", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliNeo", "InteliNeo 530 BESS", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),

    _m("InteliDrive", "InteliDrive 700 Marine", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliDrive", "InteliDrive DCU Marine", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliDrive", "InteliDrive DCU Industrial", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
    _m("InteliDrive", "InteliDrive Industrial 600", "dynamic_export", "dynamic_export", "import_required", "IMPORTAR MAPA", DYNAMIC),
]

DSE_MODELS = [
    {
        "brand": "DSE",
        "family": "Deep Sea Electronics",
        "model": "DSE 7320 MKII",
        "profile_key": "genmon_dse",
        "map_mode": "reference_profile",
        "profile_status": "reference",
        "profile_label": "REFERÊNCIA",
        "requires_import": False,
        "hint": "Perfil GenMon de referência; validar registradores no equipamento real.",
        "aliases": ["7320 MKII"],
    }
]


def _norm(value):
    return " ".join(
        str(value or "").upper().replace("-", " ").replace("_", " ").split()
    )


def list_controller_models(controller_type=None):
    ctype = _norm(controller_type)
    if ctype == "COMAP":
        return [dict(x) for x in COMAP_MODELS]
    if ctype == "DSE":
        return [dict(x) for x in DSE_MODELS]
    return [dict(x) for x in COMAP_MODELS + DSE_MODELS]


def find_controller_model(controller_type, model):
    wanted = _norm(model)
    if not wanted:
        return None
    for item in list_controller_models(controller_type):
        names = [item["model"], *item.get("aliases", [])]
        if wanted in {_norm(name) for name in names}:
            return item
    return None


def profile_key_for_model(controller_type, model):
    item = find_controller_model(controller_type, model)
    return item["profile_key"] if item else None
