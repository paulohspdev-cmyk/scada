"""Catálogo simples de controladoras disponíveis para cadastro.

O catálogo não define mapa Modbus. A integração técnica de cada modelo fica em
`rapid/templates/` e `rapid/bindings.json`, depois de validação no Rapid SCADA.
"""


def _m(family, model, aliases=()):
    return {
        "brand": "COMAP",
        "family": family,
        "model": model,
        "aliases": list(aliases),
    }


COMAP_MODELS = [
    _m("InteliLite", "InteliLite 4 AMF 25"),
    _m("InteliLite", "InteliLite 4 AMF 20"),
    _m("InteliLite", "InteliLite 4 MRS 16"),
    _m("InteliLite", "InteliLite 4 MRS 11"),
    _m("InteliLite", "InteliLite 4 AMF 9"),
    _m("InteliLite", "InteliNano AMF 5"),
    _m("InteliLite", "InteliNano MRS 3"),
    _m("InteliLite NT", "InteliLite NT AMF 25", ("IL-NT AMF25",)),
    _m("InteliLite NT", "InteliLite NT AMF 20", ("IL-NT AMF20",)),
    _m("InteliLite NT", "InteliLite NT MRS 16", ("IL-NT MRS16",)),
    _m("InteliLite NT", "InteliLite NT MRS 10"),
    _m("InteliLite NT", "InteliLite NT MRS 3"),
    _m("InteliGen", "InteliGen 1000"),
    _m("InteliGen", "InteliGen 1000 SC"),
    _m("InteliGen", "InteliGen 500 G2"),
    _m("InteliGen", "InteliGen4 200", ("InteliGen 4 200", "IG4 200")),
    _m("InteliGen", "InteliGen 200", ("IG200", "IG 200")),
    _m("InteliGen NT", "InteliGen NT", ("IG-NT",)),
    _m("InteliCompact NT", "InteliCompact NT MINT", ("IC-NT MINT", "ICNT MINT")),
    _m("InteliCompact NT", "InteliCompact NT SPtM", ("IC-NT SPTM", "ICNT SPTM")),
    _m("InteliCompact NT", "InteliCompact NT", ("ICNT", "IC NT")),
    _m("InteliSys", "InteliSys 2000"),
    _m("InteliSys", "InteliSys Gas"),
    _m("InteliSys", "InteliSys NTC BaseBox"),
    _m("InteliATS", "InteliATS2 70"),
    _m("InteliATS", "InteliATS2 50"),
    _m("InteliNeo", "InteliNeo 6000"),
    _m("InteliNeo", "InteliNeo 5500"),
    _m("InteliNeo", "InteliNeo 530 BESS"),
    _m("InteliDrive", "InteliDrive 700 Marine"),
    _m("InteliDrive", "InteliDrive DCU Marine"),
    _m("InteliDrive", "InteliDrive DCU Industrial"),
    _m("InteliDrive", "InteliDrive Industrial 600"),
]

DSE_MODELS = [
    {
        "brand": "DSE",
        "family": "Deep Sea Electronics",
        "model": "DSE 7320 MKII",
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
