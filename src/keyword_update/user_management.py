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
    try:
        while True:
            username = input("Enter a user name (\033[91m0\033[0m to exit):\n")
            if not username:
                print("⚠️ Username cannot be empty")
                continue
            if username == "0":
                return False
            existing = db_session.query(User).filter_by(user_name=username).first()
            if existing:
                print(
                    f"⚠️ Username \033[91m'{username}'\033[0m is already taken, enter a different User."
                )
                continue
            break

        new_user = User(user_name=username)
        password = input("Password\n")
        if not password:
            print("⚠️ Password cannot be empty.\n❌ Aborted")
            return False
        new_user.set_password(password)  # hashes automatically
        db_session.add(new_user)
        db_session.commit()
        print(f"✅ User \033[92m'{username}'\033[0m registered successfully.")
        return True

    except Exception as e:
        db_session.rollback()
        print(f"❌ An unexpected error occurred: {str(e)}")
        return False


def edit_user():
    try:
        while True:
            username = input(
                "Enter the username of the user to edit (\033[91m0\033[0m to exit):\n"
            )
            if username == "0":
                return False
            user = db_session.query(User).filter_by(user_name=username).first()
            if not user:
                print(f"❌ No user found with username \033[91m'{username}'\033[0m.")
                continue
            break

        print("Leave fields blank if you don't want to change them.")

        # Optionally change username
        while True:
            new_username = input(
                "New username (press Enter to keep current):\n"
            ).strip()
            # Check for duplicate username
            existing = db_session.query(User).filter_by(user_name=new_username).first()
            if existing and existing.id != user.id:
                print(f"⚠️ Username \033[91m'{new_username}'\033[0m is already taken.")
                continue
            if new_username:
                user.user_name = new_username
            break

        # Optionally change password
        new_password = input("New password (press Enter to keep current):\n").strip()
        if new_password:
            user.set_password(new_password)

        choice = input(
            f"Are you sure you want to change \nuser \033[93m'{username}'\033[0m to \033[92m'{new_username}'\033[0m and set \npassword \033[91m{new_password}\033[0m y/n: "
        )
        if choice == "y":
            db_session.commit()
            print(f"✅ User \033[92m'{user.user_name}'\033[0m updated successfully.")
            return True
        else:
            print(f"❌ Aborted.")
            return False

    except Exception as e:
        db_session.rollback()
        print(f"❌ An unexpected error occurred: {str(e)}")
        return False


def remove_user():
    """Remove an existing user from the database."""
    try:
        while True:
            username = input(
                "Enter the username of the user to remove (\033[91m0\033[0m to exit):\n"
            ).strip()
            if username == "0":
                return False
            user = db_session.query(User).filter_by(user_name=username).first()
            if not user:
                print(f"❌ No user found with username \033[93m'{username}'\033[0m.")
                continue
            break

        confirm = input(
            f"⚠️ Are you sure you want to delete user "
            f"\033[91m{user.user_name}\033[0m? (y/n): "
        ).lower()

        if confirm != "y":
            print("❎ Deletion canceled.")
            return True

        db_session.delete(user)
        db_session.commit()
        print(f"🗑️ User '\033[92m{username}\033[0m' removed successfully.")
        return True
    except Exception as e:
        db_session.rollback()
        print(f"❌ An unexpected error occurred: {str(e)}")
        return False


if __name__ == "__main__":
    while True:
        decision = input(
            "Enter \033[1;91mr\033[0m to register, \033[1;91me\033[0m to edit, \033[1;91md\033[0m to delete a user: "
        )
        match decision:
            case "r":
                register_user()
            case "e":
                edit_user()
            case "d":
                remove_user()
            case _:
                print(f"\033[91mWrong choice {decision}\033[0m")
