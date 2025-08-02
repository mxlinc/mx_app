import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
from flask import jsonify

# ✅ Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "devsecret")

# ✅ Database URL from .env or Render
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

# ✅ Force psycopg2 driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# ✅ Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ✅ Schema
CURRENT_SCHEMA = os.getenv("APP_SCHEMA", "prod")

# ------------------- MODELS ------------------- #
class UserTable(db.Model, UserMixin):
    __tablename__ = 'user_table'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    full_name = db.Column(db.String)
    user_role = db.Column(db.String)   # admin / teacher / student
    password_hash = db.Column(db.String)  # for demo only, use hashing in prod
    is_active = db.Column(db.Boolean, default=True)

    def get_id(self):
        return str(self.id)

class UserWorks(db.Model):
    __tablename__ = 'user_works'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    username = db.Column(db.String, primary_key=True)
    pack_id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, primary_key=True)
    pack_desc = db.Column(db.String)
    work_name = db.Column(db.String)
    work_link = db.Column(db.String)
    work_status = db.Column(db.String)
    work_rank = db.Column(db.Integer)

class EmailMessage(db.Model):
    __tablename__ = 'emails'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String)
    subject = db.Column(db.String)
    body = db.Column(db.Text)


# -------------------- FLASK-LOGIN SETUP -------------------- #
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(UserTable, int(user_id))  


# -------------------- ROUTES -------------------- #
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = UserTable.query.filter_by(username=username, is_active=True).first()

        if user and user.password_hash == password:
            login_user(user)
            flash("Login successful!", "success")

            if user.user_role == "student":
                return redirect(url_for("student_home"))
            elif user.user_role == "teacher":
                return redirect(url_for("teacher_home"))
            elif user.user_role == "admin":
                return redirect(url_for("admin_home"))
            else:
                flash("Unknown role. Contact admin.", "danger")
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

# ------------------- STUDENT HOME ------------------- #
@app.route('/studenthome')
@login_required
def student_home():
    results = db.session.query(
        UserWorks.pack_id,
        UserWorks.pack_desc,
        UserWorks.work_name,
        UserWorks.work_link,
        UserWorks.username,
        UserWorks.work_id
    ).filter(
        UserWorks.username == current_user.username,
        UserWorks.work_status == 'assigned'
    ).order_by(UserWorks.pack_id, UserWorks.work_rank).all()

    data = []
    pack_map = {}
    for pack_id, pack_desc, work_name, work_link, username, work_id in results:
        if pack_id not in pack_map:
            pack_entry = {"pack_id": pack_id, "pack_desc": pack_desc, "works": []}
            pack_map[pack_id] = pack_entry
            data.append(pack_entry)


        # ✅ include username and work_id in works list
        pack_map[pack_id]["works"].append({
            "work_name": work_name,
            "work_link": work_link,
            "username": username,
            "work_id": work_id
        })

    return render_template(
        'student_home.html',
        full_name=current_user.full_name,
        grouped=data
    )


# ------------------- TEACHER HOME ------------------- #
@app.route("/teacherhome")
@login_required
def teacher_home():
    return render_template("teacher_home.html", name=current_user.full_name)

# ------------------- ADMIN HOME ------------------- #
@app.route("/adminhome")
@login_required
def admin_home():
    return render_template("admin_home.html", name=current_user.full_name)

# ------------------- RECENT SUBMISSIONS ------------------- #
@app.route('/recent')
@login_required
def recent_submissions():
    return render_template('recent_submissions.html', full_name=current_user.full_name)

# ------------------- LOG OUT ------------------- #
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ------------------- REFRESH CARD ------------------- #
@app.route('/refresh_all')
@login_required
def refresh_all():
    results = db.session.query(
        UserWorks.pack_id,
        UserWorks.pack_desc,
        UserWorks.work_name,
        UserWorks.work_link,
        UserWorks.username,
        UserWorks.work_id
    ).filter(
        UserWorks.username == current_user.username,
        UserWorks.work_status == 'assigned'
    ).order_by(UserWorks.pack_id, UserWorks.work_rank).all()

    data = []
    pack_map = {}
    for pack_id, pack_desc, work_name, work_link, username, work_id in results:
        if pack_id not in pack_map:
            pack_entry = {"pack_id": pack_id, "pack_desc": pack_desc, "works": []}
            pack_map[pack_id] = pack_entry
            data.append(pack_entry)
        pack_map[pack_id]["works"].append({
            "work_name": work_name,
            "work_link": work_link,
            "username": username,
            "work_id": work_id
        })

    return render_template('_cards.html', grouped=data)


# ------------------- Mailgun Webhook ------------------- #
@app.route('/mailgun_webhook', methods=['POST'])
def mailgun_webhook():
    sender = request.form.get('sender', 'Unknown Sender')
    subject = request.form.get('subject', '(No Subject)')
    body = request.form.get('body-plain', '(No Body)')

    # ✅ Store in DB (for persistence)
    email = EmailMessage(sender=sender, subject=subject, body=body)
    db.session.add(email)
    db.session.commit()

    return "Email received", 200

# ------------------- Email page (temp) ------------------- #
@app.route('/emails')
@login_required
def emails():
    messages = EmailMessage.query.order_by(EmailMessage.id.desc()).limit(20).all()
    return render_template('emails.html', messages=messages)


# -------------------- RUN -------------------- #
if __name__ == "__main__":
    app.run(debug=True)
