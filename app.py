import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# ✅ Load environment variables (.env for local)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "devsecret")  # required for sessions

# ✅ Read database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Configure it in .env or Render environment.")

# ✅ Force psycopg2 driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# ✅ Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ✅ Use prod schema for now
CURRENT_SCHEMA = os.getenv("APP_SCHEMA", "prod")

# ✅ User model
class User(db.Model):
    __tablename__ = "user_table"
    __table_args__ = {"schema": CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    password_hash = db.Column(db.String(255), nullable=False)  # stores cleartext password
    role = db.Column(db.String(50), nullable=False)  # student / teacher / admin
    name = db.Column(db.String(150))
    level_code = db.Column(db.String(50))
    hint = db.Column(db.String(255))

# -------------------- ROUTES --------------------

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username, enabled=True).first()

        if user and user.password_hash == password:
            session["user_id"] = user.id
            session["role"] = user.role
            flash("Login successful!", "success")

            if user.role == "student":
                return redirect(url_for("student_home"))
            elif user.role == "teacher":
                return redirect(url_for("teacher_home"))
            elif user.role == "admin":
                return redirect(url_for("admin_home"))
            else:
                flash("Unknown role. Contact admin.", "danger")
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/studenthome")
def student_home():
    return render_template("student_home.html")

@app.route("/teacherhome")
def teacher_home():
    return render_template("teacher_home.html")

@app.route("/adminhome")
def admin_home():
    return render_template("admin_home.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(debug=True)
