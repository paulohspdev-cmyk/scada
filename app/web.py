import os
import sqlite3
from flask import Flask, jsonify, render_template, request
from . import db
from .profiles import load_points

app = Flask(__name__)
db.init_db()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "rc-scada-web"}


@app.get("/api/dashboard")
def api_dashboard():
    return jsonify(db.dashboard())


@app.get("/api/generators")
def api_generators():
    return jsonify(db.list_generators())


@app.post("/api/generators")
def api_create_generator():
    data = request.get_json(force=True) or {}
    required = ["code", "name", "controller_type"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"error": "Campos obrigatórios: " + ", ".join(missing)}), 400
    if data["controller_type"].upper() not in ("COMAP", "DSE"):
        return jsonify({"error": "controller_type deve ser COMAP ou DSE"}), 400
    try:
        obj = db.create_generator(data)
        return jsonify(obj), 201
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
    return (jsonify(obj), 200) if obj else (jsonify({"error": "não encontrado"}), 404)


@app.patch("/api/generators/<int:gid>")
def api_update_generator(gid):
    try:
        obj = db.update_generator(gid, request.get_json(force=True) or {})
        return (jsonify(obj), 200) if obj else (jsonify({"error": "não encontrado"}), 404)
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
        return jsonify(load_points(obj["controller_type"], obj.get("controller_model")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/events")
def api_events():
    return jsonify(db.recent_events(100))


if __name__ == "__main__":
    app.run(
        host=os.environ.get("RC_BIND", "127.0.0.1"),
        port=int(os.environ.get("RC_WEB_PORT", "8088")),
    )
