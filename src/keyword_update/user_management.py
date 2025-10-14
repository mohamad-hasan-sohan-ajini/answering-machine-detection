# app.py
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_login import UserMixin
from sqlalchemy import update, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

from werkzeug.security import check_password_hash

file_path = Path(__file__).resolve()
parent_dir = file_path.parent
sys.path.insert(0, str(parent_dir))

from database import init_db, db_session, Base
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
app = Flask(__name__)
app.secret_key = "9bee2f6c48c942a39461e688397e5346"
init_db()
login_manager = LoginManager(app)
login_manager.login_view = "login"


def register_user():
    #try:
        username = input("User Name:\n")
        new_user = User(user_name=username)
        new_user.set_password(input("Password\n"))  # hashes automatically
        db_session.add(new_user)
        db_session.commit()
        return f"✅ User '{username}' registered successfully."

    # except IntegrityError:
    #     db_session.rollback()
    #     return f"⚠️ Username '{username}' already exists. Please choose another."

    # except Exception as e:
    #     db_session.rollback()
    #     return f"❌ An unexpected error occurred: {str(e)}"

if __name__ == "__main__":
    register_user()

