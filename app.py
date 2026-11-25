from flask import Flask, render_template, request, jsonify
import mysql.connector
import os
import secrets

from flask import session, redirect, url_for
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from mysql.connector import IntegrityError
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = (
    os.environ.get("FLASK_SECRET_KEY")
    or secrets.token_hex(32)
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

def get_db_connection():
    # Local XAMPP defaults; change these values if your database differs.
    return mysql.connector.connect(
        host="localhost", user="root", password="",
        database="smart_fish_db", port=3306
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/waste", methods=["GET"])
def get_waste():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT waste_id, supplier_name, location, quantity_kg, status FROM fish_waste ORDER BY waste_id DESC")
        rows = cursor.fetchall()
        for row in rows:
            row["quantity_kg"] = float(row["quantity_kg"])
        return jsonify(rows)
    finally:
        cursor.close()
        conn.close()


@app.route("/api/waste", methods=["POST"])
def add_waste():
    data = request.get_json(silent=True) or {}
    supplier = str(data.get("supplier_name", "")).strip()
    location = str(data.get("location", "")).strip()
    try:
        quantity = Decimal(str(data.get("quantity_kg", "")))
    except InvalidOperation:
        return jsonify(error="Invalid quantity"), 400
    if not supplier or not location or len(supplier) > 100 or len(location) > 150 or not quantity.is_finite() or quantity <= 0:
        return jsonify(error="Please enter valid details"), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO fish_waste (supplier_name, location, quantity_kg) VALUES (%s, %s, %s)", (supplier, location, quantity))
        conn.commit()
        return jsonify(message="Fish waste added successfully"), 201
    finally:
        cursor.close()
        conn.close()


@app.route("/api/fertilizers", methods=["GET"])
def get_fertilizers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT fertilizer_id, fertilizer_name, price, stock_kg FROM fertilizers")
        rows = cursor.fetchall()
        for row in rows:
            row["price"] = float(row["price"])
            row["stock_kg"] = float(row["stock_kg"])
        return jsonify(rows)
    finally:
        cursor.close()
        conn.close()


@app.route("/api/orders", methods=["POST"])
def add_order():
    data = request.get_json(silent=True) or {}
    farmer = str(data.get("farmer_name", "")).strip()
    try:
        fertilizer_id = int(data.get("fertilizer_id"))
        quantity = Decimal(str(data.get("quantity_kg", "")))
    except (ValueError, TypeError, InvalidOperation):
        return jsonify(error="Invalid order details"), 400
    if not farmer or len(farmer) > 100 or not quantity.is_finite() or quantity <= 0:
        return jsonify(error="Invalid order details"), 400
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("SELECT stock_kg FROM fertilizers WHERE fertilizer_id = %s FOR UPDATE", (fertilizer_id,))
        product = cursor.fetchone()
        if product is None:
            conn.rollback()
            return jsonify(error="Fertilizer not found"), 404
        if quantity > product["stock_kg"]:
            conn.rollback()
            return jsonify(error="Not enough stock"), 400
        cursor.execute("INSERT INTO fertilizer_orders (farmer_name, fertilizer_id, quantity_kg) VALUES (%s, %s, %s)", (farmer, fertilizer_id, quantity))
        cursor.execute("UPDATE fertilizers SET stock_kg = stock_kg - %s WHERE fertilizer_id = %s", (quantity, fertilizer_id))
        conn.commit()
        return jsonify(message="Order placed successfully"), 201
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# Roles allowed to register themselves
PUBLIC_ROLES = {
    "fish_supplier",
    "compost_producer",
    "farmer"
}


# Registration
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if (
            not name
            or len(name) > 100
            or not email
            or len(email) > 150
            or "@" not in email
            or not (8 <= len(password) <= 128)
            or role not in PUBLIC_ROLES
        ):
            return "Invalid registration details", 400

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users
                (full_name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
            """, (name, email, hashed_password, role))

            conn.commit()

        except IntegrityError:
            conn.rollback()
            return "Email already registered", 409

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT user_id, full_name, password_hash, role
                FROM users
                WHERE email = %s
            """, (email,))

            user = cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

       
        if user and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()

            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            # Redirect based on user role
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            
            if user["role"] == "fish_supplier":
                return redirect(url_for("supplier_dashboard"))

            if user["role"] == "farmer":
                return redirect(url_for("farmer_dashboard"))
            
            if user["role"] == "waste_collector":
                 return redirect(url_for("collector_dashboard"))

            if user["role"] == "compost_producer":
                return redirect(url_for("producer_dashboard"))

            return redirect(url_for("dashboard"))

        return "Invalid email or password", 401

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        name=session["full_name"],
        role=session["role"]
    )


# Logout
@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return redirect(url_for("login"))
@app.route("/farmer/dashboard")
def farmer_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access Denied", 403

    return render_template(
        "farmer_dashboard.html",
        name=session["full_name"]
    )

# Fish Supplier Dashboard
@app.route("/supplier/dashboard")
def supplier_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "fish_supplier":
        return "Access Denied", 403

    return render_template(
        "fish_supplier_dashboard.html",
        name=session["full_name"]
    )


# Get supplier's fish waste records
@app.route("/api/supplier/waste", methods=["GET"])
def supplier_waste_records():

    if session.get("role") != "fish_supplier":
        return jsonify({"error": "Access Denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT waste_id, location, quantity_kg, status
            FROM fish_waste
            WHERE supplier_id = %s
            ORDER BY waste_id DESC
        """, (session["user_id"],))

        records = cursor.fetchall()

        for record in records:
            record["quantity_kg"] = float(record["quantity_kg"])

        return jsonify(records)

    finally:
        cursor.close()
        conn.close()


# Register new fish waste
@app.route("/api/supplier/waste", methods=["POST"])
def register_supplier_waste():

    if session.get("role") != "fish_supplier":
        return jsonify({"error": "Access Denied"}), 403

    data = request.get_json(silent=True) or {}

    location = str(data.get("location", "")).strip()

    try:
        quantity = Decimal(str(data.get("quantity_kg", "")))
    except InvalidOperation:
        return jsonify({"error": "Invalid quantity"}), 400

    if (
        not location
        or len(location) > 150
        or not quantity.is_finite()
        or quantity <= 0
        or quantity > Decimal("99999999.99")
    ):
        return jsonify({"error": "Invalid details"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO fish_waste
            (supplier_id, supplier_name, location, quantity_kg)
            VALUES (%s, %s, %s, %s)
        """, (
            session["user_id"],
            session["full_name"],
            location,
            quantity
        ))

        conn.commit()

        return jsonify({
            "message": "Fish waste registered successfully"
        }), 201

    finally:
        cursor.close()
        conn.close()

from datetime import date

# Supplier Collection Requests
@app.route("/api/supplier/collections", methods=["GET", "POST"])
def supplier_collections():

    if session.get("role") != "fish_supplier":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if request.method == "GET":
            cursor.execute("""
                SELECT request_id, waste_id,
                       requested_date, status
                FROM collection_requests
                WHERE supplier_id = %s
                ORDER BY request_id DESC
            """, (session["user_id"],))

            records = cursor.fetchall()

            for row in records:
                row["requested_date"] = row[
                    "requested_date"
                ].isoformat()

            return jsonify(records)

        data = request.get_json(silent=True) or {}

        try:
            waste_id = int(data.get("waste_id"))
            requested_date = date.fromisoformat(
                data.get("requested_date", "")
            )
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid request"}), 400

        if requested_date < date.today():
            return jsonify({
                "error": "Select today or a future date"
            }), 400

        cursor.execute("""
            SELECT waste_id
            FROM fish_waste
            WHERE waste_id = %s
              AND supplier_id = %s
              AND status = 'Available'
        """, (waste_id, session["user_id"]))

        if cursor.fetchone() is None:
            return jsonify({
                "error": "Waste record unavailable"
            }), 404

        try:
            cursor.execute("""
                INSERT INTO collection_requests
                (waste_id, supplier_id, requested_date)
                VALUES (%s, %s, %s)
            """, (
                waste_id,
                session["user_id"],
                requested_date
            ))

            conn.commit()

        except IntegrityError:
            conn.rollback()
            return jsonify({
                "error": "Collection already requested"
            }), 409

        return jsonify({
            "message": "Collection request submitted"
        }), 201

    finally:
        cursor.close()
        conn.close()
     
# ADMIN DASHBOARD
@app.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access Denied", 403

    return render_template(
        "admin_dashboard.html",
        name=session["full_name"]
    )


# GET ALL COLLECTION REQUESTS
@app.route("/api/admin/collections", methods=["GET"])
def admin_collections():
    if session.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                cr.request_id,
                u.full_name AS supplier_name,
                fw.location,
                fw.quantity_kg,
                cr.requested_date,
                cr.status
            FROM collection_requests cr
            JOIN users u
                ON cr.supplier_id = u.user_id
            JOIN fish_waste fw
                ON cr.waste_id = fw.waste_id
            ORDER BY cr.request_id DESC
        """)

        records = cursor.fetchall()

        for record in records:
            record["quantity_kg"] = float(
                record["quantity_kg"]
            )
            record["requested_date"] = (
                record["requested_date"].isoformat()
            )

        return jsonify(records)
    finally:
        cursor.close()
        conn.close()


# GET WASTE COLLECTORS
@app.route("/api/admin/collectors", methods=["GET"])
def admin_collectors():
    if session.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT user_id, full_name
            FROM users
            WHERE role = 'waste_collector'
            ORDER BY full_name
        """)

        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()


# ASSIGN COLLECTION TO COLLECTOR
@app.route(
    "/api/admin/collections/<int:request_id>/assign",
    methods=["POST"]
)
def admin_assign_collector(request_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}

    try:
        collector_id = int(data.get("collector_id"))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid collector"}), 400

    if collector_id <= 0:
        return jsonify({"error": "Invalid collector"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT user_id FROM users
            WHERE user_id = %s
              AND role = 'waste_collector'
        """, (collector_id,))

        if cursor.fetchone() is None:
            return jsonify({
                "error": "Waste Collector not found"
            }), 404

        # Assign only a request still in Pending state
        cursor.execute("""
            UPDATE collection_requests
            SET collector_id = %s,
                status = 'Assigned'
            WHERE request_id = %s
              AND status = 'Pending'
        """, (collector_id, request_id))

        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify({
                "error": "Request is not pending or does not exist"
            }), 409

        conn.commit()

        return jsonify({
            "message": "Collector assigned successfully"
        })

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

# WASTE COLLECTOR DASHBOARD
@app.route("/collector/dashboard")
def collector_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "waste_collector":
        return "Access Denied", 403

    return render_template(
        "waste_collector_dashboard.html",
        name=session["full_name"]
    )


# GET ASSIGNED COLLECTIONS
@app.route("/api/collector/assignments", methods=["GET"])
def collector_assignments():

    if session.get("role") != "waste_collector":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                cr.request_id,
                cr.waste_id,
                u.full_name AS supplier_name,
                fw.location,
                fw.quantity_kg,
                cr.requested_date,
                cr.status
            FROM collection_requests cr
            JOIN fish_waste fw
                ON cr.waste_id = fw.waste_id
            JOIN users u
                ON cr.supplier_id = u.user_id
            WHERE cr.collector_id = %s
              AND cr.status IN ('Assigned', 'Collected')
            ORDER BY cr.request_id DESC
        """, (session["user_id"],))

        records = cursor.fetchall()

        for record in records:
            record["quantity_kg"] = float(
                record["quantity_kg"]
            )
            record["requested_date"] = (
                record["requested_date"].isoformat()
            )

        return jsonify(records)

    finally:
        cursor.close()
        conn.close()


# COMPLETE COLLECTION
@app.route(
    "/api/collector/collections/<int:request_id>/complete",
    methods=["POST"]
)
def complete_collection(request_id):

    if session.get("role") != "waste_collector":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Update only the logged-in collector's assignment
        cursor.execute("""
            UPDATE collection_requests
            SET status = 'Collected'
            WHERE request_id = %s
              AND collector_id = %s
              AND status = 'Assigned'
        """, (
            request_id,
            session["user_id"]
        ))

        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify({
                "error": "Assignment not found or already completed"
            }), 409

        # Update the related fish waste record
        cursor.execute("""
            UPDATE fish_waste fw
            JOIN collection_requests cr
                ON fw.waste_id = cr.waste_id
            SET fw.status = 'Collected'
            WHERE cr.request_id = %s
              AND cr.collector_id = %s
        """, (
            request_id,
            session["user_id"]
        ))

        conn.commit()

        return jsonify({
            "message": "Collection completed successfully"
        })

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# COMPOST PRODUCER DASHBOARD
@app.route("/producer/dashboard")
def producer_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "compost_producer":
        return "Access Denied", 403

    return render_template(
        "compost_producer_dashboard.html",
        name=session["full_name"]
    )


# AVAILABLE COLLECTED WASTE
@app.route("/api/producer/waste", methods=["GET"])
def producer_waste():
    if session.get("role") != "compost_producer":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT DISTINCT
                fw.waste_id,
                fw.location,
                fw.quantity_kg,
                fw.supplier_name
            FROM fish_waste fw
            JOIN collection_requests cr
                ON fw.waste_id = cr.waste_id
            WHERE cr.status = 'Collected'
              AND fw.status = 'Collected'
              AND NOT EXISTS (
                  SELECT 1
                  FROM waste_receipts wr
                  WHERE wr.waste_id = fw.waste_id
              )
            ORDER BY fw.waste_id DESC
        """)

        records = cursor.fetchall()

        for record in records:
            record["quantity_kg"] = float(
                record["quantity_kg"]
            )

        return jsonify(records)

    finally:
        cursor.close()
        conn.close()


# RECEIVE FISH WASTE
@app.route("/api/producer/receive", methods=["POST"])
def receive_waste():
    if session.get("role") != "compost_producer":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}

    try:
        waste_id = int(data.get("waste_id"))
        if waste_id <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid waste ID"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO waste_receipts
                (waste_id, producer_id)
            SELECT fw.waste_id, %s
            FROM fish_waste fw
            WHERE fw.waste_id = %s
              AND fw.status = 'Collected'
              AND EXISTS (
                  SELECT 1
                  FROM collection_requests cr
                  WHERE cr.waste_id = fw.waste_id
                    AND cr.status = 'Collected'
              )
        """, (session["user_id"], waste_id))

        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify({
                "error": "Collected waste not found"
            }), 404

        conn.commit()

        return jsonify({
            "message": "Fish waste received successfully"
        }), 201

    except IntegrityError:
        conn.rollback()
        return jsonify({
            "error": "Waste already received"
        }), 409

    finally:
        cursor.close()
        conn.close()


# RECEIVED WASTE RECORDS
@app.route("/api/producer/receipts", methods=["GET"])
def producer_receipts():
    if session.get("role") != "compost_producer":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                wr.receipt_id,
                fw.waste_id,
                fw.quantity_kg,
                fw.location
            FROM waste_receipts wr
            JOIN fish_waste fw
                ON wr.waste_id = fw.waste_id
            WHERE wr.producer_id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM fertilizer_production fp
                  WHERE fp.receipt_id = wr.receipt_id
              )
            ORDER BY wr.receipt_id DESC
        """, (session["user_id"],))

        records = cursor.fetchall()

        for record in records:
            record["quantity_kg"] = float(
                record["quantity_kg"]
            )

        return jsonify(records)

    finally:
        cursor.close()
        conn.close()


# FERTILIZER INVENTORY
@app.route("/api/producer/fertilizers", methods=["GET"])
def producer_fertilizers():
    if session.get("role") != "compost_producer":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT fertilizer_id, fertilizer_name,
                   price, stock_kg
            FROM fertilizers
            ORDER BY fertilizer_name
        """)

        records = cursor.fetchall()

        for record in records:
            record["price"] = float(record["price"])
            record["stock_kg"] = float(record["stock_kg"])

        return jsonify(records)

    finally:
        cursor.close()
        conn.close()


# RECORD FERTILIZER PRODUCTION
@app.route("/api/producer/production", methods=["POST"])
def producer_production():
    if session.get("role") != "compost_producer":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}

    try:
        receipt_id = int(data.get("receipt_id"))
        fertilizer_id = int(data.get("fertilizer_id"))
        quantity = Decimal(str(data.get("quantity_kg")))

        if (
            receipt_id <= 0
            or fertilizer_id <= 0
            or not quantity.is_finite()
            or quantity <= 0
            or quantity.as_tuple().exponent < -2
        ):
            raise ValueError()

    except (ValueError, TypeError, InvalidOperation):
        return jsonify({
            "error": "Invalid production details"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT wr.receipt_id, fw.quantity_kg
            FROM waste_receipts wr
            JOIN fish_waste fw
                ON wr.waste_id = fw.waste_id
            WHERE wr.receipt_id = %s
              AND wr.producer_id = %s
            FOR UPDATE
        """, (receipt_id, session["user_id"]))

        receipt = cursor.fetchone()

        if receipt is None:
            return jsonify({
                "error": "Received waste not found"
            }), 404

        # Simplified demo: one batch per waste receipt
        if quantity > receipt["quantity_kg"]:
            return jsonify({
                "error": "Quantity exceeds received waste"
            }), 400

        cursor.execute("""
            SELECT batch_id
            FROM fertilizer_production
            WHERE receipt_id = %s
        """, (receipt_id,))

        if cursor.fetchone():
            return jsonify({
                "error": "Receipt already used for production"
            }), 409

        cursor.execute("""
            UPDATE fertilizers
            SET stock_kg = stock_kg + %s
            WHERE fertilizer_id = %s
        """, (quantity, fertilizer_id))

        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify({
                "error": "Fertilizer product not found"
            }), 404

        cursor.execute("""
            INSERT INTO fertilizer_production
                (receipt_id, fertilizer_id, produced_kg)
            VALUES (%s, %s, %s)
        """, (receipt_id, fertilizer_id, quantity))

        conn.commit()

        return jsonify({
            "message": "Production recorded successfully"
        }), 201

    except IntegrityError:
        conn.rollback()
        return jsonify({
            "error": "Production already recorded"
        }), 409

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# FARMER - PLACE FERTILIZER ORDER

@app.route("/api/farmer/orders", methods=["POST"])
def place_farmer_order():

    if session.get("role") != "farmer":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}

    try:
        fertilizer_id = int(data.get("fertilizer_id"))
        quantity = Decimal(str(data.get("quantity_kg")))

        if (
            fertilizer_id <= 0
            or not quantity.is_finite()
            or quantity <= 0
            or quantity > Decimal("99999999.99")
            or quantity.as_tuple().exponent < -2
        ):
            raise ValueError()

    except (ValueError, TypeError, InvalidOperation):
        return jsonify({
            "error": "Invalid fertilizer or quantity"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check product and reserve stock atomically
        cursor.execute("""
            UPDATE fertilizers
            SET stock_kg = stock_kg - %s
            WHERE fertilizer_id = %s
              AND stock_kg >= %s
        """, (quantity, fertilizer_id, quantity))

        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify({
                "error": "Product unavailable or insufficient stock"
            }), 400
        
        
        cursor.execute("""
            INSERT INTO fertilizer_orders
                (farmer_name, fertilizer_id,
                 quantity_kg, status)
            VALUES (%s, %s, %s, 'Pending')
        """, (
            session["full_name"],
            fertilizer_id,
            quantity
        ))

        order_id = cursor.lastrowid

        conn.commit()

        return jsonify({
            "message": "Order placed successfully",
            "order_id": order_id,
            "status": "Pending"
        }), 201

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

@app.route("/api/farmer/my-orders", methods=["GET"])
def farmer_my_orders():

    if session.get("role") != "farmer":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                fo.order_id,
                f.fertilizer_name,
                fo.quantity_kg,
                f.price,
                fo.status,
                fo.created_at
            FROM fertilizer_orders fo
            JOIN fertilizers f
                ON fo.fertilizer_id = f.fertilizer_id
            WHERE fo.farmer_id = %s
            ORDER BY fo.order_id DESC
        """, (session["user_id"],))

        orders = cursor.fetchall()

        for order in orders:
            order["quantity_kg"] = float(order["quantity_kg"])
            order["price"] = float(order["price"])
            order["created_at"] = order["created_at"].isoformat()

        return jsonify(orders)

    finally:
        cursor.close()
        conn.close()

# ADMIN - VIEW FARMER ORDERS

@app.route("/api/admin/farmer-orders", methods=["GET"])
def admin_farmer_orders():
    if session.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT fo.order_id, fo.farmer_name,
                   f.fertilizer_name, fo.quantity_kg,
                   fo.status, fo.created_at
            FROM fertilizer_orders fo
            JOIN fertilizers f
                ON fo.fertilizer_id = f.fertilizer_id
            ORDER BY fo.order_id DESC
        """)
        orders = cursor.fetchall()

        for order in orders:
            order["quantity_kg"] = float(order["quantity_kg"])
            order["created_at"] = (
                order["created_at"].isoformat()
            )

        return jsonify(orders)

    finally:
        cursor.close()
        conn.close()


# ADMIN - UPDATE ORDER STATUS

@app.route("/api/admin/farmer-orders/<int:order_id>/status",
           methods=["POST"])
def admin_update_farmer_order(order_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in ("Processing", "Delivered"):
        return jsonify({"error": "Invalid status"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Allow only forward status transitions
        if new_status == "Processing":
            old_status = "Pending"
        else:
            old_status = "Processing"

        cursor.execute("""
            UPDATE fertilizer_orders
            SET status = %s
            WHERE order_id = %s AND status = %s
        """, (new_status, order_id, old_status))

        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify({
                "error": "Order not found or invalid transition"
            }), 409

        conn.commit()
        return jsonify({
            "message": "Order status updated",
            "status": new_status
        })

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)  # Use only for local development.
