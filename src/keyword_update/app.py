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
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_login import LoginManager, current_user, login_required, login_user

file_path = Path(__file__).resolve()
parent_dir = file_path.parent
sys.path.insert(0, str(parent_dir))


from database import init_db
from models import User
from utils import (
    add_keywords,
    get_all_keywords,
    get_confirmed_words,
    get_deleted_words,
    get_pending_words,
    recycle_keywords_to_pending,
    remove_from_db,
    sync_keywords_with_form,
)

PORT = int(os.environ.get("PORT", 8000))
FULLCHAIN = os.environ.get(
    "FULLCHAIN", "/etc/letsencrypt/live/badenbpo.info/fullchain.pem"
)
PRIVKEY = os.environ.get("PRIVKEY", "/etc/letsencrypt/live/badenbpo.info/privkey.pem")

timeout = int(os.environ.get("timeout", 5))
tokentimeout = int(os.environ.get("timeout", 0))
if not tokentimeout:
    tokentimeout = False

app = Flask(__name__)
app.secret_key = "9bee2f6c48c942a39461e688397e5346"
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(minutes=timeout)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=timeout)
app.config["JWT_SECRET_KEY"] = "super-secret"
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=tokentimeout)

jwt = JWTManager(app)
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


@app.route("/access_token", methods=["GET"])
@login_required
def access_token():
    # Use Flask-Login's current_user object
    username = (
        current_user.user_name
    )  # or current_user.username depending on your model
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/update_keywords", methods=["GET", "POST"])
@login_required
def update_keywords():
    if request.method == "POST":
        updated_info = sync_keywords_with_form(request.form)
        flash({"items": updated_info}, "updated")
        return redirect(url_for("update_keywords"))
    else:
        return render_template(
            "update_keywords.html",
            confirmed_keywords=get_confirmed_words(),
            pending_keywords=get_pending_words(),
        )


@app.route("/recycle_keywords", methods=["GET", "POST"])
@login_required
def recycle_keywords():
    if request.method == "POST":
        recycle_keys = recycle_keywords_to_pending(request.form)
        flash({"items": recycle_keys}, "recycled")
        return redirect(url_for("recycle_keywords"))
    else:
        return render_template(
            "recycle_keywords.html",
            removed_keywords=get_deleted_words(),
        )


@app.route("/add_confirmed_keywords", methods=["GET", "POST"])
@login_required
def add_confirmed_keywords():
    if request.method == "POST":
        add_info = add_keywords(request.form, "confirmed")
        flash(add_info, "added")
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
        add_info = add_keywords(request.form, "pending")
        flash(add_info, "added")
        return redirect(url_for("add_pending_keywords"))
    else:
        return render_template(
            "add_keywords.html",
            destination_url="add_pending_keywords",
            page_title="Add Keywords (Pending)",
        )


@app.route("/api/get_keywords", methods=["GET"])
@jwt_required()
def api_get_keywords():
    return jsonify(get_confirmed_words())


@app.route("/api/add_pending_keywords", methods=["POST"])
@jwt_required()
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
        removed_keys = remove_from_db(request.form)
        flash({"items": removed_keys}, "removed")
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
        removed_keys = remove_from_db(request.form)
        flash({"items": removed_keys}, "removed")
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
        removed_keys = remove_from_db(request.form)
        flash({"items": removed_keys}, "removed")
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
    excluded_endpoints = [
        "show_routes",
        "login",
        "api_get_keywords",
        "api_pending_keywords",
        "health",
    ]
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
    if PORT == 443:
        app.run(
            host="0.0.0.0", port=PORT, ssl_context=(FULLCHAIN, PRIVKEY), debug=False
        )
    else:
        app.run(host="0.0.0.0", port=PORT, debug=False)
