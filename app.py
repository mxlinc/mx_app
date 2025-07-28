import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Get DATABASE_URL from environment or use SQLite locally
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///mx_app.db")

# ✅ Force SQLAlchemy to use psycopg3 driver when using PostgreSQL on Render
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Example User table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# Routes
@app.route("/")
def home():
    users = User.query.all()
    return render_template("index.html", users=users)

@app.route("/add", methods=["POST"])
def add_user():
    name = request.form.get("name")
    if name:
        db.session.add(User(name=name))
        db.session.commit()
    return redirect(url_for("home"))

# Run locally
if __name__ == "__main__":
    app.run(debug=True)
