# app.py
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import LoginManager, login_required, login_user

file_path = Path(__file__).resolve()
parent_dir = file_path.parent
sys.path.insert(0, str(parent_dir))


from database import init_db
from models import User
from utils import (
    add_keywords,
    get_all_keywords,
    get_confirmed_words,
    get_pending_words,
    remove_from_db,
    sync_keywords_with_form,
)

PORT = int(os.environ.get("PORT", 8000))
timeout = int(os.environ.get("timeout", 5))
app = Flask(__name__)
app.secret_key = "9bee2f6c48c942a39461e688397e5346"
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(minutes=timeout)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=timeout)
init_db()
login_manager = LoginManager(app)
login_manager.login_view = "login"


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
            if not next_page:
                next_page = url_for("show_routes")

            return redirect(next_page)
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for("login"))

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
    excluded_endpoints = ["show_routes", "login", "api_pending_keywords", "health"]
    routes = []
    for rule in app.url_map.iter_rules():
        # Skip static route
        if rule.endpoint == "static" or rule.endpoint in excluded_endpoints:
            continue

        # Build the URL for the route
        url = url_for(rule.endpoint, **{arg: f"<{arg}>" for arg in rule.arguments})
        routes.append((rule.endpoint, url, list(rule.methods)))

    # Sort alphabetically by endpoint
    routes.sort(key=lambda x: x[0])

    return render_template("routes.html", routes=routes)


if __name__ == "__main__":
    # For local dev only. Behind a real server, use gunicorn/uwsgi.
    app.run(host="0.0.0.0", port=PORT, debug=True)
