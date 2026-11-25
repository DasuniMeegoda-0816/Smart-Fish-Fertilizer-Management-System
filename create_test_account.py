
from getpass import getpass
from app import get_db_connection
from werkzeug.security import generate_password_hash
from mysql.connector import IntegrityError

role = input(
    "Role (admin / waste_collector / compost_producer): "
).strip()

if role not in (
    "admin",
    "waste_collector",
    "compost_producer"
):
    raise SystemExit("Invalid role")

name = input("Full name: ").strip()
email = input("Email: ").strip().lower()
password = getpass("Password: ")

if not name or not email or len(password) < 8:
    raise SystemExit("Enter valid details and a longer password")

conn = get_db_connection()
cursor = conn.cursor()

try:
    cursor.execute("""
        INSERT INTO users
        (full_name, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
    """, (
        name,
        email,
        generate_password_hash(password),
        role
    ))

    conn.commit()
    print("Account created successfully")

except IntegrityError:
    conn.rollback()
    print("Email already exists or invalid account details")

finally:
    cursor.close()
    conn.close()
