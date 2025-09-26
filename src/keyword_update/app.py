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


from database import init_db
from utils import (
    add_keywords,
    get_all_keywords,
    get_confirmed_words,
    get_pending_words,
    remove_from_db,
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


@app.route("/add_confirmed_keywords", methods=["GET", "POST"])
@login_manager.user_loader
def add_confirmed_keywords():
    if request.method == "POST":
        add_keywords(request.form, "confirmed")
        return redirect(url_for("add_confirmed_keywords"))
    else:
        return render_template(
            "add_keywords.html",
            destination_url="add_confirmed_keywords",
            page_title="Add Keywords (Confirmed)",
        )


@app.route("/add_pending_keywords", methods=["GET", "POST"])
@login_manager.user_loader
def add_pending_keywords():
    if request.method == "POST":
        add_keywords(request.form, "pending")
        return redirect(url_for("add_pending_keywords"))
    else:
        return render_template(
            "add_keywords.html",
            destination_url="add_pending_keywords",
            page_title="Add Keywords (Pending)",
        )


@app.route("/remove_keywords", methods=["GET", "POST"])
@login_manager.user_loader
def remove_keywords():
    if request.method == "POST":
        remove_from_db(request.form)
        return redirect(url_for("remove_keywords"))
    else:
        return render_template(
            "remove_keywords.html",
            keywords=get_all_keywords(),
        )


if __name__ == "__main__":
    # For local dev only. Behind a real server, use gunicorn/uwsgi.
    app.run(host="0.0.0.0", port=PORT, debug=True)
