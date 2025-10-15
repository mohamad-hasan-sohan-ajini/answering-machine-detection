# app.py
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional


from flask import Flask, jsonify, redirect, render_template, request, url_for, session
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_login import UserMixin
from sqlalchemy import update, Column, String
from sqlalchemy.ext.declarative import declarative_base

from werkzeug.security import check_password_hash

from datetime import timedelta


file_path = Path(__file__).resolve()
parent_dir = file_path.parent
sys.path.insert(0, str(parent_dir))


from models import User
from database import init_db, Base
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
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(minutes=5)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=5)
init_db()
login_manager = LoginManager(app)
login_manager.login_view = "login"


# @app.context_processor
# def inject_routes_link():
#     return {'routes_link': url_for('/')}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(user_name=username).first()

        if user and user.check_password(password):
            login_user(user)
            session.permanent = True
            next_page = request.args.get("next")
            print(next_page)
            if not next_page:
                next_page = url_for("index")

            return redirect(next_page)
        else:
            return "Invalid username or password", 401

    return render_template("login.html")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/get_keywords", methods=["GET"])
@login_required
def get_keywords():
    return jsonify(get_confirmed_words())


@app.route("/update_keywords", methods=["GET", "POST"])
@login_required
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
@login_required
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
@login_required
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


@app.route("/api/add_pending_keywords", methods=["POST"])
def api_pending_keywords():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return (
            jsonify({"error": "Invalid or missing JSON data", "status": "failed"}),
            400,
        )

    valid = all(isinstance(value, str) for key, value in data.items())

    if not valid:
        return jsonify({"error": "Invalid data format", "status": "failed"}), 400

    try:
        description = add_keywords(data, "pending")
        return (
            jsonify(
                {
                    "message": f"{len(data)} Keywords added successfully",
                    "description": description,
                    "status": "success",
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/remove_keywords", methods=["GET", "POST"])
@login_required
def remove_keywords():
    if request.method == "POST":
        remove_from_db(request.form)
        return redirect(url_for("remove_keywords"))
    else:
        return render_template(
            "remove_keywords.html",
            keywords=get_all_keywords(),
            destination_url="remove_keywords",
        )


@app.route("/remove_pending_keywords", methods=["GET", "POST"])
@login_required
def remove_pending_keywords():
    if request.method == "POST":
        remove_from_db(request.form)
        return redirect(url_for("remove_pending_keywords"))
    else:
        return render_template(
            "remove_keywords.html",
            keywords=get_pending_words(),
            destination_url="remove_pending_keywords",
        )


@app.route("/remove_confirmed_keywords", methods=["GET", "POST"])
@login_required
def remove_confirmed_keywords():
    if request.method == "POST":
        remove_from_db(request.form)
        return redirect(url_for("remove_confirmed_keywords"))
    else:
        return render_template(
            "remove_keywords.html",
            keywords=get_confirmed_words(),
            destination_url="remove_confirmed_keywords",
        )


@app.route("/")
@login_required
def show_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        # Skip static route
        if rule.endpoint == "static":
            continue

        # Build the URL for the route
        url = url_for(rule.endpoint, **{arg: f"<{arg}>" for arg in rule.arguments})
        routes.append((rule.endpoint, url, list(rule.methods)))

    # Sort alphabetically by endpoint
    routes.sort(key=lambda x: x[0])

    html = """
    <html>
    <head>
        <title>Available Routes</title>
        <style>
            body {
                font-family: 'Poppins', sans-serif;
                background: #f5f7fa;
                padding: 2rem;
            }
            h1 {
                color: #333;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                border-radius: 8px;
                overflow: hidden;
            }
            th, td {
                padding: 1rem;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            tr:hover {
                background-color: #f1f5fb;
            }
            a {
                color: #4f46e5;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            th {
                background: #4f46e5;
                color: white;
            }
        </style>
    </head>
    <body>
        <h1>Available Flask Routes</h1>
        <table>
            <thead>
                <tr>
                    <th>Endpoint</th>
                    <th>URL</th>
                </tr>
            </thead>
            <tbody>
    """

    for endpoint, url, methods in routes:
        html += f"""
        <tr>
            <td>{endpoint}</td>
            <td><a href="{url}">{url}</a></td>
        </tr>
        """

    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    # For local dev only. Behind a real server, use gunicorn/uwsgi.
    app.run(host="0.0.0.0", port=PORT, debug=True)

