# app.py
import os
from datetime import datetime
from typing import List, Optional

from flask import Flask, jsonify, render_template, request
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
    keywords = [k.word for k in db_session.query(Keyword).all()]
    return jsonify(keywords)


@app.route("/update_keywords", methods=["GET", "POST"])
@login_manager.user_loader
def update_keywords():
    # list confirmed and pending keywords
    confirmed_keywords = [
        k.word
        for k in db_session.query(Keyword)
        .join(Status)
        .filter(Status.status == "confirmed")
        .all()
    ]
    pending_keywords = [
        k.word
        for k in db_session.query(Keyword)
        .join(Status)
        .filter(Status.status == "pending")
        .all()
    ]
    # methods
    if request.method == "POST":
        return "NO ANSWER"
    else:
        try:
            text = render_template(
                "update_keywords.html",
                confirmed_keywords=confirmed_keywords,
                pending_keywords=pending_keywords,
            )
        except Exception as e:
            text = f"Error rendering template: {e}"
        return text


if __name__ == "__main__":
    # For local dev only. Behind a real server, use gunicorn/uwsgi.
    app.run(host="0.0.0.0", port=PORT, debug=True)
