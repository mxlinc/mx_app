"""LMS (Learning Management System) routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
import os
from db import db
from models import UserTable, UserWorks, MXWorks, MXWorkPacks, EmailMessage, DonePacks, ContactSubmission
from lms.utils import parse_email_content, update_work_with_result

logger = logging.getLogger(__name__)

lms_bp = Blueprint("lms", __name__)


# ==================== AUTHENTICATION ==================== #

@lms_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username'].strip().lower()
        password = request.form.get("password")
        # only allow login for users marked active
        user = UserTable.query.filter_by(username=username, is_active=True).first()

        if user and user.password_hash == password:
            login_user(user)
            flash("Login successful!", "success")

            if user.user_role == "student":
                return redirect(url_for("lms.student_home"))
            elif user.user_role == "teacher":
                return redirect(url_for("lms.teacher_home"))
            elif user.user_role == "admin":
                return redirect(url_for("lms.admin_home"))
            else:
                flash("Unknown role. Contact admin.", "danger")
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")


@lms_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("lms.login"))


# ==================== INDEX ==================== #

@lms_bp.route("/")
def index():
    return redirect(url_for("lms.login"))


# ==================== STUDENT HOME ==================== #

@lms_bp.route('/studenthome')
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
        UserWorks.work_status == 'Assigned'
    ).order_by(UserWorks.pack_desc, UserWorks.pack_id, UserWorks.work_rank).all()

    data = []
    pack_map = {}
    for pack_id, pack_desc, work_name, work_link, username, work_id, work_views in results:
        if pack_id not in pack_map:
            # Extract display name (substring after _ if present)
            display_desc = pack_desc.split('_', 1)[1] if '_' in pack_desc else pack_desc
            pack_entry = {
                "pack_id": pack_id, 
                "pack_desc": pack_desc,
                "display_desc": display_desc,
                "works": []
            }
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


@lms_bp.route('/log_click', methods=['POST'])
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


@lms_bp.route('/refresh_all')
@login_required
def refresh_all():
    item_list = db.session.query(
        UserWorks.pack_id,
        UserWorks.pack_desc,
        UserWorks.work_name,
        UserWorks.work_link,
        UserWorks.username,
        UserWorks.work_id,
        UserWorks.work_views
    ).filter(
        UserWorks.username == current_user.username,
        UserWorks.work_status == 'Assigned'
    ).order_by(UserWorks.pack_desc, UserWorks.pack_id, UserWorks.work_rank).all()

    data = []
    pack_map = {}

    for pack_id, pack_desc, work_name, work_link, username, work_id, work_views in item_list:
        if pack_id not in pack_map:
            display_desc = pack_desc.split('_', 1)[1] if '_' in pack_desc else pack_desc
            pack_entry = {
                "pack_id": pack_id, 
                "pack_desc": pack_desc,
                "display_desc": display_desc,
                "works": []
            }
            pack_map[pack_id] = pack_entry
            data.append(pack_entry)
        pack_map[pack_id]["works"].append({
            "work_name": work_name,
            "work_link": work_link,
            "username": username,
            "work_id": work_id,
            "work_views": work_views
        })

    filtered_data = []
    for pack in data:
        work_names = [w["work_name"] for w in pack["works"]]
        if not all(name.startswith("V") for name in work_names):
            filtered_data.append(pack)
    return render_template('_cards.html', grouped=filtered_data)


@lms_bp.route('/student_cards')
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
    ).order_by(UserWorks.pack_desc, UserWorks.pack_id, UserWorks.work_rank).all()

    data = []
    pack_map = {}
    for pack_id, pack_desc, work_name, work_link, username, work_id, work_views in results:
        if pack_id not in pack_map:
            display_desc = pack_desc.split('_', 1)[1] if '_' in pack_desc else pack_desc
            pack_entry = {
                "pack_id": pack_id, 
                "pack_desc": pack_desc,
                "display_desc": display_desc,
                "works": []
            }
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


@lms_bp.route('/recent')
@login_required
def recent_submissions():
    page = request.args.get('page', 1, type=int)
    per_page = 20

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


# ==================== TEACHER HOME ==================== #

@lms_bp.route("/teacherhome")
@login_required
def teacher_home():
    return render_template("teacher_home.html", name=current_user.full_name)


# ==================== ADMIN HOME & PACK MANAGEMENT ==================== #

@lms_bp.route('/admin_home')
@login_required
def admin_home():
    if current_user.user_role != 'admin':
        return "Forbidden", 403

    students = UserTable.query.filter_by(user_role='student', can_assign_work=True).all()

    broad_areas = db.session.query(MXWorkPacks.broad_area)\
                           .filter(MXWorkPacks.broad_area.isnot(None))\
                           .distinct()\
                           .order_by(MXWorkPacks.broad_area)\
                           .all()
    broad_areas = [area[0] for area in broad_areas if area[0]]

    all_packs = MXWorkPacks.query\
                          .filter(MXWorkPacks.broad_area.isnot(None))\
                          .order_by(MXWorkPacks.broad_area, MXWorkPacks.pack_desc)\
                          .all()

    return render_template(
        'admin_home.html',
        students=students,
        broad_areas=broad_areas,
        all_packs=all_packs
    )


@lms_bp.route("/packdetails/<int:pack_id>")
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


@lms_bp.route("/createpack", methods=["POST"])
def create_pack():
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
        result = conn.execute(
            text("SELECT old_work_id, work_id FROM prod.mx_works WHERE old_work_id = ANY(:oids)"),
            {"oids": old_ids}
        ).mappings().all()
        mapping = {row["old_work_id"]: row["work_id"] for row in result}

        missing = [oid for oid in old_ids if oid not in mapping]
        if missing:
            return f"❌ Missing old_work_ids: {', '.join(missing)}", 400

        ordered_work_ids = [
            int(item) if item.isdigit() else mapping[item]
            for item in lines
        ]
        pack_contents = "|".join(str(wid) for wid in ordered_work_ids)

        result = conn.execute(
            text("""
                INSERT INTO prod.mx_work_packs (pack_desc, broad_area, pack_contents, last_updated)
                VALUES (:desc, :area, :contents, CURRENT_TIMESTAMP)
                RETURNING pack_id, pack_desc
            """),
            {"desc": pack_desc, "area": broad_area, "contents": pack_contents}
        ).mappings().first()

        logger.info(f"✅ CREATED pack_id={result['pack_id']} | {result['pack_desc']}")

    return redirect(url_for("lms.admin_home"))


@lms_bp.route('/update_pack_works/<int:pack_id>', methods=['POST'])
@login_required
def update_pack_works(pack_id):
    data = request.get_json()
    work_ids = data.get('work_ids', [])
    pack_desc = data.get('pack_desc', '').strip()
    
    if not work_ids:
        return "No work IDs provided.", 400
    if not pack_desc:
        return "Pack description is required.", 400

    with db.engine.begin() as conn:
        old_ids = [wid for wid in work_ids if not str(wid).isdigit()]
        mapping = {}
        if old_ids:
            result = conn.execute(
                text("SELECT old_work_id, work_id FROM prod.mx_works WHERE old_work_id = ANY(:oids)"),
                {"oids": old_ids}
            ).mappings().all()
            mapping = {row["old_work_id"]: row["work_id"] for row in result}
            missing = [oid for oid in old_ids if oid not in mapping]
            if missing:
                return f"❌ Missing old_work_ids: {', '.join(missing)}", 400

        ordered_work_ids = [
            int(wid) if str(wid).isdigit() else mapping[wid]
            for wid in work_ids
        ]
        pack_contents = "|".join(str(wid) for wid in ordered_work_ids)

        conn.execute(
            text("""
                UPDATE prod.mx_work_packs
                SET pack_contents = :contents, pack_desc = :pack_desc, last_updated = CURRENT_TIMESTAMP
                WHERE pack_id = :pack_id
            """),
            {"contents": pack_contents, "pack_desc": pack_desc, "pack_id": pack_id}
        )
    return "OK"


@lms_bp.route('/assignwork', methods=['POST'])
@login_required
def assign_work():
    from sqlalchemy.sql import bindparam
    
    students = request.form.getlist('student')
    pack_id = int(request.form['package_id'])
    force = (request.form.get('force') == 'true')
    results = []

    for student in students:
        logger.info(f"Assigning pack_id={pack_id} to student={student}")

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
        work_ids = list(dict.fromkeys(work_ids))

        logger.info(f"Fetched work_ids for pack_id={pack_id}: {work_ids}")
        if not work_ids:
            results.append({
                "student": student,
                "conflict": True,
                "conflict_items": [],
                "can_assign": False,
                "message": f"❌ No valid work_ids found for package {pack_id}."
            })
            continue

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

        conflict_items = [{"id": str(row['work_id']), "name": row['work_name']} for row in conflicts]

        if conflicts and not force:
            results.append({
                "student": student,
                "conflict": True,
                "conflict_items": conflict_items,
                "can_assign": False,
                "message": f"Student {student}: {len(conflicts)} conflicts"
            })
            continue

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
            results.append({
                "student": student,
                "conflict": True,
                "conflict_items": [],
                "can_assign": False,
                "message": f"❌ No works found for package {pack_id}."
            })
            continue

        conflict_ids = {int(c['work_id']) for c in conflicts} if conflicts else set()

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
            results.append({
                "student": student,
                "conflict": False,
                "conflict_items": [],
                "can_assign": True,
                "message": f"✅ Assigned package {pack_id} to {student} "
                           f"({len(works)} works added; {len(conflict_ids)} Past, "
                           f"{len(works) - len(conflict_ids)} Future)"
            })
        except Exception as e:
            logger.exception("Assign failed")
            results.append({
                "student": student,
                "conflict": True,
                "conflict_items": [],
                "can_assign": False,
                "message": f"❌ Assign failed: {e}"
            })

    return jsonify(results=results)


@lms_bp.route('/mark_complete', methods=['POST'])
@login_required
def mark_complete():
    data = request.get_json()
    username = data.get('username')
    work_id = data.get('work_id')
    row = UserWorks.query.filter_by(username=username, work_id=int(work_id)).first()
    if row:
        row.work_status = "Done"
        row.work_score = "Complete"
        row.incorrect = "-"
        row.last_updated = datetime.utcnow()
        db.session.commit()
        return "OK"
    return "Not found", 404


@lms_bp.route('/mark_pack_done', methods=['POST'])
@login_required
def mark_pack_done():
    data = request.get_json()
    username = data.get('username')
    pack_id = int(data.get('pack_id'))
    
    existing = DonePacks.query.filter_by(username=username, pack_id=pack_id).first()
    if not existing:
        done_pack = DonePacks(username=username, pack_id=pack_id)
        db.session.add(done_pack)
        db.session.commit()
        return jsonify(success=True, message=f"Pack {pack_id} marked as done for {username}")
    else:
        return jsonify(success=True, message=f"Pack {pack_id} already marked as done for {username}")


@lms_bp.route('/restore_pack', methods=['POST'])
@login_required
def restore_pack():
    data = request.get_json()
    username = data.get('username')
    pack_id = int(data.get('pack_id'))
    
    done_pack = DonePacks.query.filter_by(username=username, pack_id=pack_id).first()
    if done_pack:
        db.session.delete(done_pack)
        db.session.commit()
        return jsonify(success=True, message=f"Pack {pack_id} restored for {username}")
    else:
        return jsonify(success=False, message=f"Pack {pack_id} was not found in done list for {username}")


@lms_bp.route('/update_work_status', methods=['POST'])
@login_required
def update_work_status():
    data = request.get_json()
    username = data.get('username')
    pack_id = int(data.get('pack_id'))
    work_id = int(data.get('work_id'))
    status = data.get('status')
    row = UserWorks.query.filter_by(username=username, pack_id=pack_id, work_id=work_id).first()
    if row:
        row.work_status = status
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False, message="Work not found"), 404


@lms_bp.route('/check_pack_id/<int:pack_id>')
@login_required
def check_pack_id(pack_id):
    exists = db.session.query(MXWorkPacks.pack_id).filter_by(pack_id=pack_id).first() is not None
    return jsonify({'exists': exists})


@lms_bp.route('/fine_tune', methods=['GET'])
@login_required
def fine_tune():
    students = UserTable.query.filter_by(user_role='student', can_assign_work=True).all()
    selected_student = request.args.get('student')
    selected_status = request.args.getlist('status')
    if not selected_status:
        selected_status = ['Future', 'Assigned', 'Done', 'Past', 'X-Delete']

    logger.info(f"Selected student: {selected_student}")
    logger.info(f"Selected statuses: {selected_status}")

    packs = []
    done_packs = []
    results = []
    
    if selected_student:
        completed_pack_ids_query = db.session.query(DonePacks.pack_id).filter_by(username=selected_student)
        completed_pack_ids = completed_pack_ids_query.subquery()
        
        done_packs_info = db.session.query(
            DonePacks.pack_id,
            UserWorks.pack_desc
        ).join(
            UserWorks, DonePacks.pack_id == UserWorks.pack_id
        ).filter(
            DonePacks.username == selected_student
        ).distinct().all()
        
        done_packs = [{"pack_id": pack_id, "pack_desc": pack_desc} for pack_id, pack_desc in done_packs_info]
        
        results = db.session.query(
            UserWorks.pack_id,
            UserWorks.pack_desc,
            UserWorks.work_name,
            UserWorks.work_link,
            UserWorks.username,
            UserWorks.work_id,
            UserWorks.work_views,
            UserWorks.work_status,
            UserWorks.work_score
        ).filter(
            UserWorks.username == selected_student,
            UserWorks.work_status.in_(selected_status),
            ~UserWorks.pack_id.in_(completed_pack_ids)
        ).order_by(UserWorks.pack_id, UserWorks.work_rank).all()
        logger.info(f"Results found: {len(results)}")

        pack_map = {}
        for pack_id, pack_desc, work_name, work_link, username, work_id, work_views, work_status, work_score in results:
            if pack_id not in pack_map:
                pack_entry = {"pack_id": pack_id, "pack_desc": pack_desc, "works": []}
                pack_map[pack_id] = pack_entry
                packs.append(pack_entry)
            pack_map[pack_id]["works"].append({
                "work_name": work_name,
                "work_link": work_link,
                "username": username,
                "work_id": work_id,
                "work_views": work_views,
                "work_status": work_status,
                "pack_id": pack_id,
                "work_score": work_score
            })

    return render_template(
        'fine_tune.html',
        students=students,
        selected_student=selected_student,
        selected_status=selected_status,
        packs=packs,
        done_packs=done_packs
    )


@lms_bp.route('/pack_report')
@login_required
def pack_report():
    if current_user.user_role != 'admin':
        return "Forbidden", 403

    rows = db.session.execute(text("""
        SELECT pack_id, pack_desc, broad_area, work_rank, work_id, work_name, work_filename, work_link
        FROM prod.packs
        ORDER BY broad_area, pack_desc, pack_id, work_rank
    """)).mappings().all()

    area_map = {}
    for r in rows:
        area = r['broad_area'] or 'Uncategorized'
        pack_key = f"{r['pack_id']}-{r['pack_desc']}"
        if area not in area_map:
            area_map[area] = {}
        if pack_key not in area_map[area]:
            area_map[area][pack_key] = []
        area_map[area][pack_key].append({
            "work_id": r["work_id"],
            "work_name": r["work_name"],
            "work_filename": r["work_filename"],
            "work_link": r["work_link"],
            "work_rank": r["work_rank"]
        })

    return render_template('pack_report.html', area_map=area_map)


# ==================== EMAIL & CONTACT ==================== #

@lms_bp.route('/mailgun_webhook', methods=['POST'])
def mailgun_webhook():
    global last_result

    sender = request.form.get('sender', 'Unknown Sender')
    subject = request.form.get('subject', '(No Subject)')
    html_body = request.form.get('body-html', '')
    plain_body = request.form.get('body-plain', '(No Body)')

    result = parse_email_content(subject, html_body or plain_body)

    LOG_EMAILS = True
    if LOG_EMAILS:
        email = EmailMessage(sender=sender, subject=subject, body=plain_body, parsed=result)
        db.session.add(email)
        db.session.commit()

    update_work_with_result(result)

    return "Email processed", 200


@lms_bp.route('/emails')
@login_required
def emails():
    messages = EmailMessage.query.order_by(EmailMessage.id.desc()).limit(20).all()
    return render_template('emails.html', messages=messages, last_result=None)


@lms_bp.route('/contact', methods=['GET'])
def contact():
    return render_template('contact.html')


@lms_bp.route('/contact_submit', methods=['POST'])
def contact_submit():
    data = request.get_json(silent=True) or request.form or {}
    your_name = (data.get('your_name') or '').strip()
    phone = (data.get('phone') or '').strip()
    email = (data.get('email') or '').strip()
    child_name = (data.get('child_name') or '').strip()
    grade = (data.get('grade') or '').strip()
    subject = (data.get('subject') or '').strip()
    about = (data.get('about') or '').strip()

    safe = lambda s: (s or '').replace('|', ' ')
    parts = [safe(your_name), safe(phone), safe(email), safe(child_name), safe(grade), safe(subject), safe(about)]
    content = '|'.join(parts)

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    cs = ContactSubmission(content=content, ip_address=ip)
    db.session.add(cs)
    db.session.commit()

    cutoff = datetime.utcnow() - timedelta(hours=1)
    recent_count = ContactSubmission.query.filter(
        ContactSubmission.ip_address == ip,
        ContactSubmission.created_at >= cutoff
    ).count()

    if recent_count > 3:
        logger.info(f"Rate limit reached for IP={ip} recent_count={recent_count}")
        return jsonify(success=True, sms_sent=False, message='Rate limit reached; submission saved.')

    TW_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TW_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TW_FROM = os.getenv('TWILIO_FROM_NUMBER')
    TO_NUMBER = os.getenv('CONTACT_TARGET_NUMBER', '+14165600611')

    if not (TW_SID and TW_TOKEN and TW_FROM):
        logger.warning('Twilio credentials not configured; skipping SMS send')
        return jsonify(success=True, sms_sent=False, message='Submission saved; SMS not sent (no credentials).')

    try:
        from twilio.rest import Client
        preview = content if len(content) <= 300 else content[:300] + '...'
        logger.info(f"Attempting to send contact SMS from={TW_FROM} to={TO_NUMBER} ip={ip} content_preview={preview}")
        client = Client(TW_SID, TW_TOKEN)
        sms = client.messages.create(body=content, from_=TW_FROM, to=TO_NUMBER)
        cs.sms_sent = True
        cs.sms_sent_at = datetime.utcnow()
        db.session.commit()
        try:
            sid = getattr(sms, 'sid', None)
            status = getattr(sms, 'status', None)
            logger.info(f"Sent contact SMS sid={sid} status={status} for ip={ip}")
        except Exception:
            logger.info(f"Sent contact SMS (no response attributes) for ip={ip}")
        return jsonify(success=True, sms_sent=True)
    except Exception as e:
        try:
            from twilio.base.exceptions import TwilioRestException
            if isinstance(e, TwilioRestException):
                logger.error(f"Twilio error when sending SMS: status={getattr(e, 'status', None)} code={getattr(e, 'code', None)} msg={str(e)}")
            else:
                logger.exception('Failed to send contact SMS')
        except Exception:
            logger.exception('Failed to send contact SMS (error inspecting exception)')
        return jsonify(success=True, sms_sent=False, error=str(e))


@lms_bp.route('/_debug/twilio_status', methods=['GET'])
def _debug_twilio_status():
    keys = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER', 'CONTACT_TARGET_NUMBER']
    missing = [k for k in keys if not os.getenv(k)]
    return jsonify(twilio_configured=(len(missing) == 0), missing=missing)


@lms_bp.route('/check_assignment_conflicts', methods=['POST'])
@login_required
def check_assignment_conflicts():
    data = request.get_json()
    student = data.get('student')
    pack_id = int(data.get('pack_id'))
    
    pack_works = db.session.execute(
        text("""
            SELECT mw.work_id, mw.work_name 
            FROM prod.mx_works mw
            JOIN (
                SELECT UNNEST(string_to_array(pack_contents, '|'))::int as work_id 
                FROM prod.mx_work_packs 
                WHERE pack_id = :pack_id
            ) pw ON mw.work_id = pw.work_id
        """), 
        {"pack_id": pack_id}
    ).mappings().all()
    
    conflicts = []
    
    for work in pack_works:
        if work['work_name'].startswith('V-'):
            continue
            
        existing = db.session.execute(
            text("""
                SELECT pack_id FROM prod.user_works 
                WHERE username = :student 
                AND work_id = :work_id 
                AND pack_id != :pack_id
            """),
            {"student": student, "work_id": work['work_id'], "pack_id": pack_id}
        ).mappings().first()
        
        if existing:
            conflicts.append({
                "work_id": work['work_id'],
                "work_name": work['work_name'],
                "existing_pack_id": existing['pack_id']
            })
    
    return jsonify({"conflicts": conflicts})


@lms_bp.route('/process_assignment', methods=['POST'])
@login_required
def process_assignment():
    import json
    
    student = request.form.get('student')
    pack_id = int(request.form.get('package_id'))
    mode = request.form.get('assignment_mode', 'normal')
    conflicts_json = request.form.get('conflicts', '[]')
    
    try:
        conflicts = json.loads(conflicts_json) if conflicts_json else []
        conflict_work_ids = [c['workId'] for c in conflicts]
        
        pack_info = db.session.execute(
            text("""
                SELECT pack_desc FROM prod.mx_work_packs 
                WHERE pack_id = :pack_id
            """),
            {"pack_id": pack_id}
        ).mappings().first()
        
        if not pack_info:
            return jsonify({
                "success": False,
                "message": f"❌ Pack {pack_id} not found"
            })
        
        pack_works = db.session.execute(
            text("""
                SELECT mw.work_id, mw.work_name, mw.work_link, mw.work_level,
                       ROW_NUMBER() OVER() as work_rank
                FROM prod.mx_works mw
                JOIN (
                    SELECT UNNEST(string_to_array(pack_contents, '|'))::int as work_id
                    FROM prod.mx_work_packs 
                    WHERE pack_id = :pack_id
                ) pw ON mw.work_id = pw.work_id
            """), 
            {"pack_id": pack_id}
        ).mappings().all()
        
        existing_works = db.session.execute(
            text("""
                SELECT work_id FROM prod.user_works 
                WHERE username = :student AND pack_id = :pack_id
            """),
            {"student": student, "pack_id": pack_id}
        ).mappings().all()
        
        existing_work_ids = [w['work_id'] for w in existing_works]
        
        for work in pack_works:
            work_id = work['work_id']
            
            if work_id in existing_work_ids:
                continue
                
            if mode == 'accept_dupes' and work_id in conflict_work_ids:
                status = 'Past'
            elif mode == 'reject_dupes' and work_id in conflict_work_ids:
                continue
            else:
                status = 'Future'
            
            db.session.execute(
                text("""
                    INSERT INTO prod.user_works 
                    (username, pack_id, work_id, work_level, work_name, work_link, 
                     work_rank, pack_desc, work_score, incorrect, work_views, 
                     work_status, last_updated)
                    VALUES (:username, :pack_id, :work_id, :work_level, :work_name, 
                            :work_link, :work_rank, :pack_desc, NULL, NULL, NULL, 
                            :status, CURRENT_TIMESTAMP)
                """),
                {
                    "username": student,
                    "pack_id": pack_id,
                    "work_id": work_id,
                    "work_level": work['work_level'],
                    "work_name": work['work_name'],
                    "work_link": work['work_link'],
                    "work_rank": work['work_rank'],
                    "pack_desc": pack_info['pack_desc'],
                    "status": status
                }
            )
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"✅ Pack {pack_id} processed for {student} (mode: {mode})"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing assignment: {e}")
        return jsonify({
            "success": False,
            "message": f"❌ Error processing pack {pack_id} for {student}: {str(e)}"
        })
