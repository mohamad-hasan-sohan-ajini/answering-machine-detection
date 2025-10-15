# app.py
import sys
from pathlib import Path

file_path = Path(__file__).resolve()
parent_dir = file_path.parent
sys.path.insert(0, str(parent_dir))

from database import db_session, init_db
from models import User

init_db()


def register_user():
    # try: TODO uncomment
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
