# app.py
import os
from datetime import datetime
from typing import List, Optional

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import update


from database import db_session, init_db
from models import Keyword, Status
from utils import (
    add_to_confirmed_keywords,
    get_confirmed_words,
    get_pending_words,
    sync_keywords_with_form,
)

PORT = int(os.environ.get("PORT", 8000))
app = Flask(__name__)
app.secret_key = "9bee2f6c48c942a39461e688397e5346"
init_db()
login_manager = LoginManager(app)
login_manager.login_view = "login"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/get_keywords", methods=["GET"])
def get_keywords():
    return jsonify(get_confirmed_words())


@app.route("/update_keywords", methods=["GET", "POST"])
@login_manager.user_loader
def update_keywords():
    if request.method == "POST":
        sync_keywords_with_form(request.form)
        return redirect(url_for("update_keywords"))
    else:
        return render_template(
            "update_keywords.html",
            confirmed_keywords=get_confirmed_words(),
            pending_keywords=get_pending_words(),
        )


@app.route("/add_keywords", methods=["GET", "POST"])
@login_manager.user_loader
def add_keywords():
    if request.method == "POST":
        add_to_confirmed_keywords(request.form)
        return redirect(url_for("add_keywords"))
    else:
        return render_template("add_keywords.html")


@app.route("/remove_keywords", methods=["GET", "POST"])
@login_manager.user_loader
def remove_keywords():
    if request.method == "POST":
        ...
    else:
        ...


if __name__ == "__main__":
    # For local dev only. Behind a real server, use gunicorn/uwsgi.
    app.run(host="0.0.0.0", port=PORT, debug=True)
