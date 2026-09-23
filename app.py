from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)

app.secret_key = "smart-fire-alert-secret-key"

DATABASE = "database.db"

# Demo admin number
ADMIN_PHONE = "9876543210"


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            description TEXT,
            map_link TEXT,
            alert_time TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            call_status TEXT DEFAULT 'Ready to Call'
        )
    """)

    admin = db.execute(
        "SELECT id FROM admin WHERE username = ?",
        ("admin",)
    ).fetchone()

    if not admin:
        db.execute(
            """
            INSERT INTO admin (username, password)
            VALUES (?, ?)
            """,
            ("admin", "1234")
        )

    db.commit()
    db.close()


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db()

        user = db.execute(
            """
            SELECT * FROM admin
            WHERE username = ? AND password = ?
            """,
            (username, password)
        ).fetchone()

        db.close()

        if user:
            session["admin"] = username
            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/")

    db = get_db()

    total_alerts = db.execute(
        "SELECT COUNT(*) FROM alerts"
    ).fetchone()[0]

    active_alerts = db.execute(
        "SELECT COUNT(*) FROM alerts WHERE status = 'Active'"
    ).fetchone()[0]

    resolved_alerts = db.execute(
        "SELECT COUNT(*) FROM alerts WHERE status = 'Resolved'"
    ).fetchone()[0]

    total_contacts = db.execute(
        "SELECT COUNT(*) FROM emergency_contacts"
    ).fetchone()[0]

    alerts = db.execute(
        """
        SELECT * FROM alerts
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()

    db.close()

    return render_template(
        "dashboard.html",
        total_alerts=total_alerts,
        active_alerts=active_alerts,
        resolved_alerts=resolved_alerts,
        contacts=total_contacts,
        alerts=alerts
    )


@app.route("/alert", methods=["GET", "POST"])
def create_alert():

    if "admin" not in session:
        return redirect("/")

    if request.method == "POST":

        location = request.form["location"]
        description = request.form["description"]
        map_link = request.form["map_link"]

        alert_time = datetime.now().strftime(
            "%d-%m-%Y %I:%M:%S %p"
        )

        db = get_db()

        db.execute(
            """
            INSERT INTO alerts
            (location, description, map_link, alert_time)
            VALUES (?, ?, ?, ?)
            """,
            (
                location,
                description,
                map_link,
                alert_time
            )
        )

        db.commit()

        alert_id = db.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        db.close()

        return render_template(
            "call_admin.html",
            alert_id=alert_id,
            phone=ADMIN_PHONE,
            location=location
        )

    return render_template("alert.html")


@app.route("/mark_called/<int:alert_id>")
def mark_called(alert_id):

    if "admin" not in session:
        return redirect("/")

    db = get_db()

    db.execute(
        """
        UPDATE alerts
        SET call_status = 'Call Initiated'
        WHERE id = ?
        """,
        (alert_id,)
    )

    db.commit()
    db.close()

    return redirect("/dashboard")


@app.route("/resolve/<int:alert_id>")
def resolve_alert(alert_id):

    if "admin" not in session:
        return redirect("/")

    db = get_db()

    db.execute(
        """
        UPDATE alerts
        SET status = 'Resolved'
        WHERE id = ?
        """,
        (alert_id,)
    )

    db.commit()
    db.close()

    return redirect("/dashboard")


@app.route("/contacts", methods=["GET", "POST"])
def contacts():

    if "admin" not in session:
        return redirect("/")

    db = get_db()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]

        db.execute(
            """
            INSERT INTO emergency_contacts
            (name, phone)
            VALUES (?, ?)
            """,
            (name, phone)
        )

        db.commit()

    contact_list = db.execute(
        """
        SELECT * FROM emergency_contacts
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "contacts.html",
        contacts=contact_list,
        admin_phone=ADMIN_PHONE
    )


@app.route("/delete_contact/<int:contact_id>")
def delete_contact(contact_id):

    if "admin" not in session:
        return redirect("/")

    db = get_db()

    db.execute(
        """
        DELETE FROM emergency_contacts
        WHERE id = ?
        """,
        (contact_id,)
    )

    db.commit()
    db.close()

    return redirect("/contacts")


@app.route("/history")
def history():

    if "admin" not in session:
        return redirect("/")

    db = get_db()

    alerts = db.execute(
        """
        SELECT * FROM alerts
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "history.html",
        alerts=alerts
    )


if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
  )
