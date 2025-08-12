import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
from flask import jsonify
import html2text
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
import re
from sqlalchemy import text
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

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

last_result = None  # stores last parsed email result for display


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
    
class MXWorks(db.Model):
    __tablename__ = 'mx_works'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    work_id = db.Column(db.Integer, primary_key=True)
    work_name = db.Column(db.Text, nullable=False)
    old_work_id = db.Column(db.String(20))
    work_level = db.Column(db.String(20))
    work_filename = db.Column(db.String(120))
    work_link = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100))
    subtopic = db.Column(db.String(200))
    work_comments = db.Column(db.Text)

class MXWorkPacks(db.Model):
    __tablename__ = 'mx_work_packs'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    pack_id = db.Column(db.Integer, primary_key=True)
    pack_desc = db.Column(db.Text)
    pack_contents = db.Column(db.Text)
    broad_area = db.Column(db.String(200))
    is_deleted = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime)

class UserWorks(db.Model):
    __tablename__ = 'user_works'
    __table_args__ = {'schema': CURRENT_SCHEMA}

    username = db.Column(db.String(20), primary_key=True)
    pack_id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, primary_key=True)

    work_level = db.Column(db.Text)
    work_name = db.Column(db.Text)
    work_link = db.Column(db.Text)
    work_rank = db.Column(db.Integer)
    pack_desc = db.Column(db.Text)
    work_score = db.Column(db.String(20))
    incorrect = db.Column(db.String(100))
    work_views = db.Column(db.Integer)
    work_status = db.Column(db.String(100), default='future', nullable=False)
    last_updated = db.Column(db.DateTime)

class EmailMessage(db.Model):
    __tablename__ = 'emails'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String)
    subject = db.Column(db.String)
    body = db.Column(db.Text)
    parsed = db.Column(JSON) 

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
        username = request.form['username'].strip().lower()
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

# ******************** STUDENT HOME **** ****************************** #
@app.route('/studenthome')
@login_required
def student_home():
    results = db.session.query(
        UserWorks.pack_id,
        UserWorks.pack_desc,
        UserWorks.work_name,
        UserWorks.work_link,
        UserWorks.username,
        UserWorks.work_id,
        UserWorks.work_views
    ).filter(
        UserWorks.username == current_user.username,
        UserWorks.work_status == 'Assigned'  # <-- Fix here
    ).order_by(UserWorks.pack_id, UserWorks.work_rank).all()

    data = []
    pack_map = {}
    for pack_id, pack_desc, work_name, work_link, username, work_id, work_views in results:
        if pack_id not in pack_map:
            pack_entry = {"pack_id": pack_id, "pack_desc": pack_desc, "works": []}
            pack_map[pack_id] = pack_entry
            data.append(pack_entry)

        pack_map[pack_id]["works"].append({
            "work_name": work_name,
            "work_link": work_link,
            "username": username,
            "work_id": work_id,
            "work_views": work_views
        })

    # filter out packs where all work_names start with 'V' to avoid empty packs
    filtered_data = []
    for pack in data:
        work_names = [w["work_name"] for w in pack["works"]]
        if not all(name.startswith("V") for name in work_names):
            filtered_data.append(pack)

    return render_template(
        'student_home.html',
        full_name=current_user.full_name,
        grouped=filtered_data
    )

# ------------------- STUDENT HOME - Click Counts ------------------- #
@app.route('/log_click', methods=['POST'])
def log_click():
    data = request.json
    username = data['username']
    pack_id = data['pack_id']
    work_id = data['work_id']

    db.session.execute(text("""
        UPDATE prod.user_works
        SET work_views = COALESCE(work_views, 0) + 1,
            last_updated = CURRENT_TIMESTAMP
        WHERE username = :u
          AND pack_id = :p
          AND work_id = :w
    """), {'u': username, 'p': int(pack_id), 'w': int(work_id)})

    db.session.commit()
    return jsonify(success=True)


   
# ------------------- TEACHER HOME ------------------- #
@app.route("/teacherhome")
@login_required
def teacher_home():
    return render_template("teacher_home.html", name=current_user.full_name)


# ------------------- RECENT SUBMISSIONS ------------------- #
@app.route('/recent')
@login_required
def recent_submissions():
    page = request.args.get('page', 1, type=int)
    per_page = 20  # <-- set page size to 20

    query = UserWorks.query.filter_by(
        username=current_user.username,
        work_status='Done'
    ).order_by(UserWorks.last_updated.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'recent_submissions.html',
        full_name=current_user.full_name,
        submissions=pagination.items,
        pagination=pagination
    )

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
    item_list = db.session.query(
        UserWorks.pack_id,
        UserWorks.pack_desc,
        UserWorks.work_name,
        UserWorks.work_link,
        UserWorks.username,
        UserWorks.work_id,
        UserWorks.work_views  # <-- Add this line
    ).filter(
        UserWorks.username == current_user.username,
        UserWorks.work_status == 'Assigned'
    ).order_by(UserWorks.pack_id, UserWorks.work_rank).all()

    data = []
    pack_map = {}

    for pack_id, pack_desc, work_name, work_link, username, work_id, work_views in item_list:  # <-- Add work_views here
        if pack_id not in pack_map:
            pack_map[pack_id] = {"pack_id": pack_id, "pack_desc": pack_desc, "works": []}
            data.append(pack_map[pack_id])
        pack_map[pack_id]["works"].append({
            "work_name": work_name,
            "work_link": work_link,
            "username": username,
            "work_id": work_id,
            "work_views": work_views  # <-- Add this line
        })

    # filter out packs where all work_names start with 'V'
    filtered_data = []
    for pack in data:
        work_names = [w["work_name"] for w in pack["works"]]
        if not all(name.startswith("V") for name in work_names):
            filtered_data.append(pack)
    return render_template('_cards.html', grouped=filtered_data)


# ------------------- Mailgun Webhook ------------------- #
@app.route('/mailgun_webhook', methods=['POST'])
def mailgun_webhook():
    global last_result

    sender = request.form.get('sender', 'Unknown Sender')
    subject = request.form.get('subject', '(No Subject)')
    html_body = request.form.get('body-html', '')
    plain_body = request.form.get('body-plain', '(No Body)')

    # ✅ Parse email to build result
    result = parse_email_content(subject, html_body or plain_body)
    last_result = result  # ✅ store latest parsed object for display

    # ✅ Option to log email
    LOG_EMAILS = True  # set to False to disable logging
    if LOG_EMAILS:
        email = EmailMessage(sender=sender, subject=subject, body=plain_body, parsed=result)
        db.session.add(email)
        db.session.commit()

    # ✅ Update user_works table
    update_work_with_result(result)

    return "Email processed", 200


# ------------------- Email page (temp) ------------------- #
@app.route('/emails')
@login_required
def emails():
    messages = EmailMessage.query.order_by(EmailMessage.id.desc()).limit(20).all()
    global last_result
    return render_template('emails.html', messages=messages, last_result=last_result)


# -------------------- PARSE EMAIL -------------------- #
def parse_email_content(subject, html_body):
    txt = html2text.html2text(html_body)
    result = {}

    # Extract ID & user
    parts = subject.split("\"")
    if len(parts) > 3:
        extracted_id = parts[1]
        if extracted_id == "%TITLE%":
            result["id"] = "INVALID"
            return result
        result["id"] = extracted_id
        result["user"] = parts[3]
    else:
        result["id"] = "INVALID"
        return result

    incorrect_numbers = []

    for line in txt.splitlines():
        if line.startswith("Date/Time:"):
            result["time"] = line.replace("Date/Time:", "").strip()

        if line.startswith("Answered:"):
            raw_score = line.replace("Answered:", "").strip()
            clean_score = raw_score.replace("**", "").replace("|", "").strip()
            match = re.match(r'(\d+)\s*/\s*(\d+)', clean_score)
            result["score"] = f"{match.group(1)} out of {match.group(2)}" if match else clean_score

        if "Incorrect" in line:
            m = re.search(r'Question\s*(\d+)', line, re.IGNORECASE)
            if m:
                incorrect_numbers.append(m.group(1))

    result["incorrect"] = "All correct!" if not incorrect_numbers else "Q: " + ", ".join(incorrect_numbers)
    return result


# -------------------- UPDATE WORKS WITH RESULTS -------------------- #
def update_work_with_result(result):
    if "user" not in result:
        logger.warning(f"Missing 'user' in result: {result}")
        return

    if "id" not in result:
        logger.warning(f"Missing 'id' in result: {result}")
        return

    if result["id"] == "INVALID":
        logger.warning(f"Result 'id' is INVALID: {result}")
        return


    work_id_value = result["id"]

    # UserWorks.work_id is int in database, so always use int for query
    if str(work_id_value).isdigit():
        work_id_int = int(work_id_value)
    else:
        mx_work = MXWorks.query.filter_by(old_work_id=work_id_value).first()
        if not mx_work:
            logger.warning(f"No matching work_id found for old_work_id={work_id_value}")
            return
        work_id_int = mx_work.work_id

    updated_rows = UserWorks.query.filter(
        UserWorks.username == result["user"],
        UserWorks.work_id == work_id_int
    ).all()

    if not updated_rows:
        logger.warning(f"No matching work found for user={result['user']} id={work_id_int}")
        return

    for row in updated_rows:
        row.work_status = "Done"
        row.work_score = result.get("score")

        incorrect_value = result.get("incorrect", "")
        if incorrect_value and len(incorrect_value) > 100:
            incorrect_value = incorrect_value[:97] + "..."
        row.incorrect = incorrect_value

    db.session.commit()
    logger.warning(f"Updated {len(updated_rows)} rows with result={result}")

# -------------------- ADMIN HOME -------------------- #
@app.route('/adminhome')
@login_required
def admin_home():
    broad_areas = db.session.execute(
        text("SELECT DISTINCT broad_area FROM prod.mx_work_packs WHERE broad_area IS NOT NULL AND broad_area <> ''")
    ).scalars().all()
    students = UserTable.query.filter_by(user_role='student').all()
    recent_packs = db.session.execute(text("""
        SELECT pack_id, pack_desc, broad_area 
        FROM prod.mx_work_packs 
        WHERE is_deleted = false 
        ORDER BY last_updated DESC
    """)).mappings().all()
    return render_template(
        "admin_home.html",
        students=students,
        broad_areas=broad_areas,
        recent_packs=recent_packs
    )


@app.route("/packdetails/<int:pack_id>")
def pack_details(pack_id):
    sql = text("""
        SELECT p.pack_id, p.pack_desc, w.work_id, w.work_name, w.work_link
        FROM prod.mx_work_packs p
        JOIN LATERAL unnest(string_to_array(p.pack_contents, '|')) WITH ORDINALITY AS wid(work_id_text, ord) ON true
        JOIN prod.mx_works w ON w.work_id = wid.work_id_text::int
        WHERE p.pack_id = :pid
        ORDER BY wid.ord
    """)
    rows = db.session.execute(sql, {"pid": pack_id}).mappings().all()

    if not rows:
        return jsonify({"error": "Pack not found"}), 404

    return jsonify({
        "pack_id": rows[0]["pack_id"],
        "pack_desc": rows[0]["pack_desc"],
        "works": [
            {
                "work_id": r["work_id"],
                "work_name": r["work_name"],
                "work_link": r["work_link"]
            } for r in rows
        ]
    })




# -------------------- ADMIN - CREATE PACK -------------------- #
@app.route("/createpack", methods=["POST"])
def create_pack():
    pack_id = int(request.form["pack_id"])
    pack_desc = request.form["pack_desc"]
    broad_area = request.form.get("broad_area") or request.form.get("broad_area_select")
    raw_ids = request.form["work_ids"]

    lines = [line.strip() for line in raw_ids.splitlines() if line.strip()]
    numeric_ids = []
    old_ids = []

    for item in lines:
        if item.isdigit():
            numeric_ids.append(int(item))
        else:
            old_ids.append(item)

    with db.engine.begin() as conn:
        # Fetch mapping from old_work_id to work_id
        result = conn.execute(
            text("SELECT old_work_id, work_id FROM prod.mx_works WHERE old_work_id = ANY(:oids)"),
            {"oids": old_ids}
        ).mappings().all()
        mapping = {row["old_work_id"]: row["work_id"] for row in result}

        # Validate missing
        missing = [oid for oid in old_ids if oid not in mapping]
        if missing:
            return f"❌ Missing old_work_ids: {', '.join(missing)}", 400

        # Maintain order
        ordered_work_ids = [
            int(item) if item.isdigit() else mapping[item]
            for item in lines
        ]
        pack_contents = "|".join(str(wid) for wid in ordered_work_ids)

        # Upsert (insert or update)
        result = conn.execute(
            text("""
                INSERT INTO prod.mx_work_packs (pack_id, pack_desc, broad_area, pack_contents, last_updated)
                VALUES (:id, :desc, :area, :contents, CURRENT_TIMESTAMP)
                ON CONFLICT (pack_id) DO UPDATE SET
                    pack_desc = EXCLUDED.pack_desc,
                    broad_area = EXCLUDED.broad_area,
                    pack_contents = EXCLUDED.pack_contents,
                    last_updated = CURRENT_TIMESTAMP
                RETURNING xmax = 0 AS inserted, pack_id, pack_desc
            """),
            {"id": pack_id, "desc": pack_desc, "area": broad_area, "contents": pack_contents}
        ).mappings().first()

        action = "INSERTED" if result["inserted"] else "UPDATED"
        logger.info(f"✅ {action} pack_id={result['pack_id']} | {result['pack_desc']}")

    return redirect(url_for("admin_home"))





# -------------------- ADMIN - WORK MANAGEMENT -------------------- #
@app.route('/assignwork', methods=['POST'])
@login_required
def assign_work():
    from sqlalchemy import text, bindparam

    student = request.form['student']
    pack_id = int(request.form['package_id'])
    force = (request.form.get('force') == 'true')

    logger.info(f"Assigning pack_id={pack_id} to student={student}")

    # 1) Get all work_ids in the package
    fetch_ids_sql = text("""
        SELECT unnest(string_to_array(pack_contents, '|')) AS work_id
        FROM prod.mx_work_packs
        WHERE pack_id = :pack_id
    """)
    work_ids_raw = db.session.execute(fetch_ids_sql, {"pack_id": pack_id}).mappings().all()
    work_ids = []
    for r in work_ids_raw:
        s = (r['work_id'] or '').strip()
        if not s:
            continue
        try:
            work_ids.append(int(s))
        except ValueError:
            logger.warning(f"Non-integer work_id in pack {pack_id}: {s} (skipped)")
    work_ids = list(dict.fromkeys(work_ids))  # de-dupe preserve order

    logger.info(f"Fetched work_ids for pack_id={pack_id}: {work_ids}")
    if not work_ids:
        return jsonify({"success": False, "message": f"❌ No valid work_ids found for package {pack_id}."})

    # 2) Find conflicts (same work already assigned to this student in other packs, exclude videos)
    conflict_sql = text("""
        SELECT work_id, pack_id, work_name
        FROM prod.user_works
        WHERE username = :username
          AND work_id IN :work_ids
          AND pack_id != :pack_id
          AND COALESCE(work_name,'') NOT LIKE 'V%%'
    """).bindparams(bindparam("work_ids", expanding=True))

    conflicts = db.session.execute(
        conflict_sql, {"username": student, "work_ids": work_ids, "pack_id": pack_id}
    ).mappings().all()

    if conflicts and not force:
        conflict_items = [{"id": str(row['work_id']), "name": row['work_name']} for row in conflicts]
        return jsonify({
            "conflict": True,
            "conflict_items": conflict_items,
            "student": student,
            "pack_id": pack_id
        })

    # 3) Fetch full work details for the pack
    fetch_sql = text("""
        SELECT 
            m.pack_id,
            m.pack_desc,
            r.work_id,
            r.work_level,
            r.work_name,
            r.work_link,
            ROW_NUMBER() OVER () AS work_rank
        FROM prod.mx_works r
        JOIN (
            SELECT pack_id, pack_desc, unnest(string_to_array(pack_contents, '|')) AS work_id
            FROM prod.mx_work_packs
            WHERE pack_id = :pack_id
        ) m ON r.work_id = m.work_id::int
    """)
    works = db.session.execute(fetch_sql, {"pack_id": pack_id}).mappings().all()
    if not works:
        return jsonify({"success": False, "message": f"❌ No works found for package {pack_id}."})

    conflict_ids = {int(c['work_id']) for c in conflicts} if conflicts else set()

    # 4) Insert rows (do writes on a fresh connection-level txn to avoid nested Session txn errors)
    insert_sql = text("""
        INSERT INTO prod.user_works (
            username, pack_id, work_id,
            work_level, work_name, work_link,
            work_rank, pack_desc,
            work_score, incorrect, work_views, work_status, last_updated
        ) VALUES (
            :username, :pack_id, :work_id,
            :work_level, :work_name, :work_link,
            :work_rank, :pack_desc,
            NULL, NULL, NULL, :work_status, CURRENT_TIMESTAMP
        )
        ON CONFLICT (username, pack_id, work_id) DO NOTHING;
    """)

    try:
        # fresh transaction independent of the request-scoped Session state (Render-safe)
        with db.engine.begin() as conn:
            for w in works:
                status = 'Past' if int(w["work_id"]) in conflict_ids else 'Future'
                conn.execute(insert_sql, {
                    "username": student,
                    "pack_id": int(w["pack_id"]),
                    "work_id": int(w["work_id"]),
                    "work_level": w["work_level"],
                    "work_name": w["work_name"],
                    "work_link": w["work_link"],
                    "work_rank": int(w["work_rank"]),
                    "pack_desc": w["pack_desc"],
                    "work_status": status
                })
    except Exception as e:
        logger.exception("Assign failed")
        return jsonify({"success": False, "message": f"❌ Assign failed: {e}"}), 500

    return jsonify({
        "success": True,
        "message": f"✅ Assigned package {pack_id} to {student} "
                   f"({len(works)} works added; {len(conflict_ids)} Past, "
                   f"{len(works) - len(conflict_ids)} Future)"
    })



# ------------------- MARK COMPLETE ------------------- #
@app.route('/mark_complete', methods=['POST'])
@login_required
def mark_complete():
    data = request.get_json()
    username = data.get('username')
    work_id = data.get('work_id')
    row = UserWorks.query.filter_by(username=username, work_id=int(work_id)).first()
    if row:
        row.work_status = "Done"
        row.work_score = "Complete"
        row.incorrect = "-" # <-- update Incorrect to '-'
        row.last_updated = datetime.utcnow()
        db.session.commit()
        return "OK"
    return "Not found", 404

# ------------------- FINE TUNE PAGE ------------------- #
@app.route('/fine_tune', methods=['GET'])
@login_required
def fine_tune():
    students = UserTable.query.filter_by(user_role='student').all()
    selected_student = request.args.get('student')
    selected_status = request.args.getlist('status')
    selected_type = request.args.getlist('type')
    pack_ids = request.args.get('pack_ids', '').replace(' ', '')
    packs = []

    if selected_student:
        query = UserWorks.query.filter_by(username=selected_student)
        if selected_status and "ALL" not in selected_status:
            query = query.filter(UserWorks.work_status.in_(selected_status))
        if selected_type and "ALL" not in selected_type:
            query = query.filter(db.or_(*[UserWorks.work_name.startswith(t) for t in selected_type]))
        if pack_ids:
            id_list = [int(pid) for pid in pack_ids.split(',') if pid]
            query = query.filter(UserWorks.pack_id.in_(id_list))
        works = query.order_by(UserWorks.pack_id, UserWorks.work_rank).all()

        # Group by pack_id
        pack_map = {}
        for w in works:
            if w.pack_id not in pack_map:
                pack_map[w.pack_id] = {
                    "pack_id": w.pack_id,
                    "pack_desc": w.pack_desc,
                    "works": []
                }
            pack_map[w.pack_id]["works"].append({
                "work_id": w.work_id,
                "work_name": w.work_name,
                "work_status": w.work_status,
                "username": w.username,
                "pack_id": w.pack_id,
                "work_link": w.work_link,      # <-- add this
                "work_views": w.work_views     # <-- add this
            })
        packs = list(pack_map.values())

    return render_template(
        'fine_tune.html',
        students=students,
        selected_student=selected_student,
        selected_status=selected_status,
        selected_type=selected_type,
        pack_ids=pack_ids,
        packs=packs
    )

# ------------------- UPDATE WORK STATUS ------------------- #
@app.route('/update_work_status', methods=['POST'])
@login_required
def update_work_status():
    data = request.get_json()
    username = data.get('username')
    pack_id = int(data.get('pack_id'))      # <-- cast to int
    work_id = int(data.get('work_id'))      # <-- cast to int
    status = data.get('status')
    row = UserWorks.query.filter_by(username=username, pack_id=pack_id, work_id=work_id).first()
    if row:
        row.work_status = status
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False, message="Work not found"), 404


@app.route('/student_cards')
@login_required
def student_cards():
    student = request.args.get('student')
    results = db.session.query(
        UserWorks.pack_id,
        UserWorks.pack_desc,
        UserWorks.work_name,
        UserWorks.work_link,
        UserWorks.username,
        UserWorks.work_id,
        UserWorks.work_views
    ).filter(
        UserWorks.username == student,
        UserWorks.work_status == 'Assigned'
    ).order_by(UserWorks.pack_id, UserWorks.work_rank).all()

    # Group by pack_id for cards
    data = []
    pack_map = {}
    for pack_id, pack_desc, work_name, work_link, username, work_id, work_views in results:
        if pack_id not in pack_map:
            pack_entry = {"pack_id": pack_id, "pack_desc": pack_desc, "works": []}
            pack_map[pack_id] = pack_entry
            data.append(pack_entry)
        pack_map[pack_id]["works"].append({
            "work_name": work_name,
            "work_link": work_link,
            "username": username,
            "work_id": work_id,
            "work_views": work_views
        })
    return render_template('_cards.html', grouped=data)





# -------------------- RUN -------------------- #
if __name__ == "__main__":
    app.run(debug=True)




