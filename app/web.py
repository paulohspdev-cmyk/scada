import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from . import db
from .controller_catalog import find_controller_model, list_controller_models
from .profile_importer import parse_profile_upload
from .profiles import load_points, profile_info
from .rapid_scada import dashboard_from_generators, overlay_generators

app = Flask(__name__)
db.init_db()


def _with_profile(obj):
    if not obj:
        return obj
    out = dict(obj)
    out["profile"] = profile_info(out)
    return out


def _current_generators():
    return overlay_generators([_with_profile(g) for g in db.list_generators()])


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "rc-scada-web"}


@app.get("/api/controller-models")
def api_controller_models():
    controller_type = request.args.get("type")
    return jsonify(list_controller_models(controller_type))


@app.get("/api/dashboard")
def api_dashboard():
    generators = _current_generators()
    return jsonify(dashboard_from_generators(generators))


@app.get("/api/generators")
def api_generators():
    return jsonify(_current_generators())


@app.post("/api/generators")
def api_create_generator():
    data = request.get_json(force=True) or {}
    required = ["code", "name", "controller_type", "controller_model"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"error": "Campos obrigatórios: " + ", ".join(missing)}), 400

    ctype = data["controller_type"].upper()
    if ctype not in ("COMAP", "DSE"):
        return jsonify({"error": "controller_type deve ser COMAP ou DSE"}), 400

    if not find_controller_model(ctype, data.get("controller_model")):
        return jsonify({"error": "Selecione um modelo disponível no catálogo"}), 400

    try:
        obj = db.create_generator(data)
        return jsonify(_with_profile(obj)), 201
    except sqlite3.IntegrityError as e:
        return (
            jsonify(
                {
                    "error": "Código já cadastrado ou já existe este Modbus Unit ID nesta porta TCP",
                    "detail": str(e),
                }
            ),
            409,
        )


@app.get("/api/generators/<int:gid>")
def api_generator(gid):
    obj = db.get_generator(gid)
    if not obj:
        return jsonify({"error": "não encontrado"}), 404
    current = overlay_generators([_with_profile(obj)])[0]
    return jsonify(current), 200


@app.patch("/api/generators/<int:gid>")
def api_update_generator(gid):
    data = request.get_json(force=True) or {}
    if "controller_type" in data or "controller_model" in data:
        current = db.get_generator(gid)
        if not current:
            return jsonify({"error": "não encontrado"}), 404
        ctype = str(data.get("controller_type", current["controller_type"])).upper()
        model = data.get("controller_model", current["controller_model"])
        if not find_controller_model(ctype, model):
            return jsonify({"error": "Selecione um modelo disponível no catálogo"}), 400

    try:
        obj = db.update_generator(gid, data)
        return (jsonify(_with_profile(obj)), 200) if obj else (jsonify({"error": "não encontrado"}), 404)
    except sqlite3.IntegrityError as e:
        return (
            jsonify(
                {
                    "error": "Código já cadastrado ou já existe este Modbus Unit ID nesta porta TCP",
                    "detail": str(e),
                }
            ),
            409,
        )


@app.delete("/api/generators/<int:gid>")
def api_delete_generator(gid):
    if not db.get_generator(gid):
        return jsonify({"error": "não encontrado"}), 404
    db.delete_generator(gid)
    return "", 204


@app.get("/api/generators/<int:gid>/profile")
def api_profile(gid):
    obj = db.get_generator(gid)
    if not obj:
        return jsonify({"error": "não encontrado"}), 404
    try:
        return jsonify(load_points(obj))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/generators/<int:gid>/profile/meta")
def api_profile_meta(gid):
    obj = db.get_generator(gid)
    if not obj:
        return jsonify({"error": "não encontrado"}), 404
    return jsonify(profile_info(obj))


@app.post("/api/generators/<int:gid>/profile/import")
def api_profile_import(gid):
    obj = db.get_generator(gid)
    if not obj:
        return jsonify({"error": "não encontrado"}), 404

    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "Envie um arquivo CSV, TXT, TSV ou JSON"}), 400

    data = upload.read()
    if len(data) > 2 * 1024 * 1024:
        return jsonify({"error": "Arquivo maior que 2 MB"}), 413

    try:
        points, warnings = parse_profile_upload(upload.filename, data)
    except (ValueError, UnicodeError) as e:
        return jsonify({"error": str(e)}), 400

    active_points = sum(1 for p in points if p.get("enabled", True))
    source_name = Path(upload.filename).name
    db.save_generator_profile(
        gid,
        source_name=source_name,
        source_type="controller_export",
        points=points,
        status="active" if active_points else "review",
    )

    updated = db.get_generator(gid)
    return jsonify(
        {
            "ok": True,
            "detected_points": len(points),
            "active_points": active_points,
            "review_points": len(points) - active_points,
            "warnings": warnings,
            "profile": profile_info(updated),
        }
    )


@app.delete("/api/generators/<int:gid>/profile/import")
def api_profile_delete(gid):
    obj = db.get_generator(gid)
    if not obj:
        return jsonify({"error": "não encontrado"}), 404
    db.delete_generator_profile(gid)
    return jsonify({"ok": True, "profile": profile_info(db.get_generator(gid))})


@app.get("/api/events")
def api_events():
    return jsonify(db.recent_events(100))


if __name__ == "__main__":
    app.run(
        host=os.environ.get("RC_BIND", "127.0.0.1"),
        port=int(os.environ.get("RC_WEB_PORT", "8088")),
    )
