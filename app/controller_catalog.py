"""Catálogo de controladoras e estratégia de perfil Modbus.

O catálogo separa a seleção do modelo do mapa de registradores. Em várias
famílias ComAp modernas o mapa é configurável pela aplicação e deve ser
exportado do InteliConfig/LiteEdit; nesses casos o sistema seleciona o driver
correto, mas não inventa endereços.
"""


def _m(family, model, profile_key, map_mode, hint, aliases=()):
    return {
        "brand": "COMAP",
        "family": family,
        "model": model,
        "profile_key": profile_key,
        "map_mode": map_mode,
        "hint": hint,
        "aliases": list(aliases),
    }


DYNAMIC = "Mapa configurável: use exportação do InteliConfig para carregar os endereços exatos desta aplicação."
LEGACY = "Família legada com guia de comunicação; usar perfil oficial validado para o modelo/firmware antes de ativar polling."
FIELD = "Perfil inicial validado em campo neste projeto; novos pontos podem ser adicionados após conferência com o display/exportação."

COMAP_MODELS = [
    _m("InteliLite", "InteliLite 4 AMF 25", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliLite", "InteliLite 4 AMF 20", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliLite", "InteliLite 4 MRS 16", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliLite", "InteliLite 4 MRS 11", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliLite", "InteliLite 4 AMF 9", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliLite", "InteliNano AMF 5", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliLite", "InteliNano MRS 3", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliLite NT", "InteliLite NT AMF 25", "legacy_nt", "legacy_guide", LEGACY, ("IL-NT AMF25",)),
    _m("InteliLite NT", "InteliLite NT AMF 20", "legacy_nt", "legacy_guide", LEGACY, ("IL-NT AMF20",)),
    _m("InteliLite NT", "InteliLite NT MRS 16", "legacy_nt", "legacy_guide", LEGACY, ("IL-NT MRS16",)),
    _m("InteliLite NT", "InteliLite NT MRS 10", "legacy_nt", "legacy_guide", LEGACY),
    _m("InteliLite NT", "InteliLite NT MRS 3", "legacy_nt", "legacy_guide", LEGACY),
    _m("InteliGen", "InteliGen 1000", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliGen", "InteliGen 1000 SC", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliGen", "InteliGen 500 G2", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliGen", "InteliGen4 200", "dynamic_export", "dynamic_export", DYNAMIC, ("InteliGen 4 200", "IG4 200")),
    _m("InteliGen", "InteliGen 200", "ig200", "field_validated", FIELD, ("IG200", "IG 200")),
    _m("InteliGen NT", "InteliGen NT", "legacy_export", "legacy_export", LEGACY, ("IG-NT",)),
    _m("InteliCompact NT", "InteliCompact NT MINT", "icnt_nt", "legacy_guide", LEGACY, ("IC-NT MINT", "ICNT MINT")),
    _m("InteliCompact NT", "InteliCompact NT SPtM", "icnt_nt", "legacy_guide", LEGACY, ("IC-NT SPTM", "ICNT SPTM")),
    _m("InteliCompact NT", "InteliCompact NT", "icnt_nt", "legacy_guide", LEGACY, ("ICNT", "IC NT")),
    _m("InteliSys", "InteliSys 2000", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliSys", "InteliSys Gas", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliSys", "InteliSys NTC BaseBox", "legacy_export", "legacy_export", LEGACY),
    _m("InteliATS", "InteliATS2 70", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliATS", "InteliATS2 50", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliNeo", "InteliNeo 6000", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliNeo", "InteliNeo 5500", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliNeo", "InteliNeo 530 BESS", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliDrive", "InteliDrive 700 Marine", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliDrive", "InteliDrive DCU Marine", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliDrive", "InteliDrive DCU Industrial", "dynamic_export", "dynamic_export", DYNAMIC),
    _m("InteliDrive", "InteliDrive Industrial 600", "dynamic_export", "dynamic_export", DYNAMIC),
]

DSE_MODELS = [
    {
        "brand": "DSE",
        "family": "Deep Sea Electronics",
        "model": "DSE 7320 MKII",
        "profile_key": "genmon_dse",
        "map_mode": "reference_profile",
        "hint": "Perfil de referência existente; validar registradores no equipamento real.",
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
