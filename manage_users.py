# manage_users.py
# Simple CLI tool to view and delete entries from the `users` table
# in climate_users.db

import sqlite3
from textwrap import dedent

DB_PATH = "climate_users.db"


def connect_db():
    return sqlite3.connect(DB_PATH)


def list_users():
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, email, district, rain_threshold, tmax_threshold, humidity_threshold FROM users ORDER BY id;")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("\nNo users found.\n")
        return

    print("\nCurrent users in database:\n")
    print(f"{'ID':<4} {'Email':<35} {'District':<15} {'Rain%':<7} {'Tmax':<7} {'Hum%':<7}")
    print("-" * 80)
    for r in rows:
        print(
            f"{r['id']:<4} {r['email']:<35} {r['district']:<15} "
            f"{r['rain_threshold']:<7} {r['tmax_threshold']:<7} {r['humidity_threshold']:<7}"
        )
    print()


def delete_by_id(user_id: int):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email, district FROM users WHERE id = ?;", (user_id,))
    row = cur.fetchone()

    if not row:
        print(f"\nNo user found with id = {user_id}\n")
        conn.close()
        return

    print(f"\nAbout to delete: ID={row[0]}, Email={row[1]}, District={row[2]}")
    confirm = input("Are you sure? (y/N): ").strip().lower()
    if confirm == "y":
        cur.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        conn.commit()
        print("User deleted.\n")
    else:
        print("Cancelled.\n")

    conn.close()


def delete_by_email(email: str):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email, district FROM users WHERE email = ?;", (email,))
    rows = cur.fetchall()

    if not rows:
        print(f"\nNo users found with email = {email}\n")
        conn.close()
        return

    print("\nThe following entries will be deleted:")
    for r in rows:
        print(f"  ID={r[0]}, Email={r[1]}, District={r[2]}")

    confirm = input("Are you sure? (y/N): ").strip().lower()
    if confirm == "y":
        cur.execute("DELETE FROM users WHERE email = ?;", (email,))
        conn.commit()
        print("User(s) deleted.\n")
    else:
        print("Cancelled.\n")

    conn.close()


def main_menu():
    menu = dedent(
        """
        ========= User Management =========
        1) List all users
        2) Delete user by ID
        3) Delete user(s) by email
        4) Exit
        -----------------------------------
        Enter choice: """
    )

    while True:
        choice = input(menu).strip()

        if choice == "1":
            list_users()
        elif choice == "2":
            try:
                uid = int(input("Enter ID to delete: ").strip())
                delete_by_id(uid)
            except ValueError:
                print("Invalid ID.\n")
        elif choice == "3":
            email = input("Enter email to delete: ").strip()
            if email:
                delete_by_email(email)
            else:
                print("Email cannot be empty.\n")
        elif choice == "4":
            print("Goodbye.")
            break
        else:
            print("Invalid choice, try again.\n")


if __name__ == "__main__":
    main_menu()
