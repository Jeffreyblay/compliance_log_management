"""
ComplianceLog — Log Record Management System
Flask + SQLite · no login required
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from database import db, LogRecord, init_db
from scheduler import start_scheduler
from datetime import datetime
import os, csv, io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-offline-use-only")
init_db(app)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def parse_date(val):
    if not val or not str(val).strip(): return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                "%m-%d-%Y", "%d %b %Y", "%B %d, %Y", "%-m/%-d/%Y"):
        try: return datetime.strptime(str(val).strip(), fmt).date()
        except: continue
    return None

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    total    = LogRecord.query.count()
    active   = LogRecord.query.filter_by(status="active").count()
    due_soon = LogRecord.query.filter_by(status="due_soon").count()
    overdue  = LogRecord.query.filter_by(status="overdue").count()
    recent   = LogRecord.query.order_by(LogRecord.updated_at.desc()).limit(8).all()
    urgent   = LogRecord.query.filter(
        LogRecord.status.in_(["due_soon","overdue"])
    ).order_by(LogRecord.due_date).all()
    return render_template("dashboard.html",
        total=total, active=active, due_soon=due_soon,
        overdue=overdue, recent=recent, urgent=urgent)

# ─── Records ──────────────────────────────────────────────────────────────────

@app.route("/records")
def records():
    query = LogRecord.query

    search        = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "")
    cond_filter   = request.args.get("condition", "")
    sort_by       = request.args.get("sort", "due_date")

    if search:
        query = query.filter(
            LogRecord.file_num.ilike(f"%{search}%")      |
            LogRecord.sample_num.ilike(f"%{search}%")    |
            LogRecord.shore_tank.ilike(f"%{search}%")    |
            LogRecord.tech_initials.ilike(f"%{search}%") |
            LogRecord.cabinet_num.ilike(f"%{search}%")   |
            LogRecord.movement.ilike(f"%{search}%")
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    if cond_filter:
        query = query.filter_by(condition=cond_filter)

    sort_map = {
        "due_date":   LogRecord.due_date,
        "sample_date":LogRecord.sample_date,
        "file_num":   LogRecord.file_num,
        "status":     LogRecord.status,
        "updated_at": LogRecord.updated_at.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, LogRecord.due_date))

    all_records = query.all()
    conditions  = db.session.query(LogRecord.condition).distinct().all()
    conditions  = sorted([c[0] for c in conditions if c[0]])

    return render_template("records.html",
        records=all_records, search=search,
        status_filter=status_filter, cond_filter=cond_filter,
        sort_by=sort_by, conditions=conditions)

@app.route("/records/new", methods=["GET", "POST"])
def new_record():
    if request.method == "POST":
        record = LogRecord(
            sample_date   = request.form.get("sample_date","").strip() or None,
            file_num      = request.form.get("file_num","").strip() or None,
            sample_num    = request.form.get("sample_num","").strip() or None,
            shore_tank    = request.form.get("shore_tank","").strip() or None,
            level         = request.form.get("level","").strip() or None,
            movement      = request.form.get("movement","").strip() or None,
            condition     = request.form.get("condition","").strip() or None,
            cabinet_num   = request.form.get("cabinet_num","").strip() or None,
            shelf_num     = request.form.get("shelf_num","").strip() or None,
            due_date      = parse_date(request.form.get("due_date","")),
            tech_initials = request.form.get("tech_initials","").strip() or None,
            notes         = request.form.get("notes","").strip() or None,
            notify_days_before = int(request.form.get("notify_days_before", 30) or 30),
        )
        record.refresh_status()
        db.session.add(record)
        db.session.commit()
        flash("Record added successfully.", "success")
        return redirect(url_for("records"))
    return render_template("record_form.html", record=None, action="Add")

@app.route("/records/<int:record_id>")
def view_record(record_id):
    record = LogRecord.query.get_or_404(record_id)
    return render_template("record_detail.html", record=record)

@app.route("/records/<int:record_id>/edit", methods=["GET", "POST"])
def edit_record(record_id):
    record = LogRecord.query.get_or_404(record_id)
    if request.method == "POST":
        record.sample_date    = request.form.get("sample_date","").strip() or None
        record.file_num       = request.form.get("file_num","").strip() or None
        record.sample_num     = request.form.get("sample_num","").strip() or None
        record.shore_tank     = request.form.get("shore_tank","").strip() or None
        record.level          = request.form.get("level","").strip() or None
        record.movement       = request.form.get("movement","").strip() or None
        record.condition      = request.form.get("condition","").strip() or None
        record.cabinet_num    = request.form.get("cabinet_num","").strip() or None
        record.shelf_num      = request.form.get("shelf_num","").strip() or None
        record.due_date       = parse_date(request.form.get("due_date",""))
        record.tech_initials  = request.form.get("tech_initials","").strip() or None
        record.notes          = request.form.get("notes","").strip() or None
        record.notify_days_before = int(request.form.get("notify_days_before", 30) or 30)
        record.refresh_status()
        db.session.commit()
        flash("Record updated.", "success")
        return redirect(url_for("view_record", record_id=record.id))
    return render_template("record_form.html", record=record, action="Update")

@app.route("/records/<int:record_id>/delete", methods=["POST"])
def delete_record(record_id):
    record = LogRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    flash("Record deleted.", "info")
    return redirect(url_for("records"))

# ─── Email Settings ───────────────────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
def settings():
    config_path = "email_config.ini"
    import configparser
    config = configparser.ConfigParser()
    config.read(config_path)
    if "email" not in config:
        config["email"] = {
            "smtp_host":"smtp.gmail.com","smtp_port":"587",
            "smtp_user":"","smtp_password":"",
            "from_address":"","enabled":"false",
        }
    if request.method == "POST":
        config["email"]["smtp_host"]     = request.form.get("smtp_host","")
        config["email"]["smtp_port"]     = request.form.get("smtp_port","587")
        config["email"]["smtp_user"]     = request.form.get("smtp_user","")
        config["email"]["smtp_password"] = request.form.get("smtp_password","")
        config["email"]["from_address"]  = request.form.get("from_address","")
        config["email"]["enabled"]       = "true" if request.form.get("enabled") else "false"
        with open(config_path,"w") as f: config.write(f)
        flash("Email settings saved.", "success")
    return render_template("settings.html", config=config["email"])

# ─── API ──────────────────────────────────────────────────────────────────────

@app.route("/api/refresh-statuses", methods=["POST"])
def refresh_statuses():
    all_records = LogRecord.query.all()
    for r in all_records: r.refresh_status()
    db.session.commit()
    return jsonify({"updated": len(all_records)})

# ─── CSV Import ───────────────────────────────────────────────────────────────

FIELD_MAP_OPTIONS = [
    ("sample_date",   "Sample Date"),
    ("file_num",      "File Number"),
    ("sample_num",    "Sample Number"),
    ("shore_tank",    "Shore Tank"),
    ("level",         "Level"),
    ("movement",      "Movement"),
    ("condition",     "Condition"),
    ("cabinet_num",   "Cabinet Number"),
    ("shelf_num",     "Shelf Number"),
    ("due_date",      "Due Date"),
    ("tech_initials", "Tech Initials"),
    ("notes",         "Notes"),
    ("__skip__",      "— Skip this column —"),
]

# Auto-guess mapping from common header variants
GUESSES = {
    "sample_date":   ["sample_date","sample date","date","sampledate"],
    "file_num":      ["file_num","file _num","file num","filenum","file_number","file number","file no"],
    "sample_num":    ["sample_num","sample _num","sample num","samplenum","sample_number","sample number","sample no"],
    "shore_tank":    ["shoretank","shore_tank","shore tank","tank"],
    "level":         ["level","lvl"],
    "movement":      ["movement","move"],
    "condition":     ["condition","cond","state"],
    "cabinet_num":   ["cabinet_num","cabinet _num","cabinet num","cabinetnum","cabinet","cabinet number","cabinet no"],
    "shelf_num":     ["shelf_num","shelf _num","shelf num","shelfnum","shelf","shelf number","shelf no"],
    "due_date":      ["due_date","due date","duedate","due","expiry","expiry_date","expiration","expires"],
    "tech_initials": ["tech_initials","tech initials","tech","initials","technician"],
    "notes":         ["notes","note","comments","remarks"],
}

@app.route("/import", methods=["GET", "POST"])
def import_csv():
    if request.method == "POST" and "csv_file" in request.files:
        f = request.files["csv_file"]
        if not f.filename.lower().endswith(".csv"):
            flash("Please upload a .csv file.", "danger")
            return redirect(url_for("import_csv"))
        content = f.read().decode("utf-8-sig", errors="replace")
        reader  = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames or []
        rows    = list(reader)
        if not headers:
            flash("CSV appears empty or has no headers.", "danger")
            return redirect(url_for("import_csv"))
        auto_map = {}
        for h in headers:
            hl = h.lower().strip().replace(" ","_").replace("-","_")
            matched = "__skip__"
            for field, kws in GUESSES.items():
                if hl in kws: matched = field; break
            auto_map[h] = matched
        session["import_rows"]    = rows
        session["import_headers"] = headers
        session["import_auto_map"]= auto_map
        return render_template("import_map.html",
            headers=headers, rows=rows[:3],
            auto_map=auto_map, field_options=FIELD_MAP_OPTIONS)
    return render_template("import_upload.html")

@app.route("/import/confirm", methods=["POST"])
def import_confirm():
    rows    = session.get("import_rows", [])
    headers = session.get("import_headers", [])
    if not rows:
        flash("No import data. Please upload your CSV again.", "warning")
        return redirect(url_for("import_csv"))
    mapping = {h: request.form.get(f"map_{h}","__skip__") for h in headers}
    mapping = {h: f for h, f in mapping.items() if f != "__skip__"}

    created, updated, skipped = 0, 0, 0
    for row in rows:
        data = {field: str(row.get(col,"")).strip() for col, field in mapping.items()}

        # Need at least a file_num or sample_num to be meaningful
        if not data.get("file_num") and not data.get("sample_num"):
            skipped += 1; continue

        # Match existing record by file_num + sample_num
        file_num   = data.get("file_num") or None
        sample_num = data.get("sample_num") or None
        record = None
        if file_num and sample_num:
            record = LogRecord.query.filter_by(
                file_num=file_num, sample_num=sample_num).first()
        elif file_num:
            record = LogRecord.query.filter_by(file_num=file_num).first()

        if record is None:
            record = LogRecord(); db.session.add(record); created += 1
        else:
            updated += 1

        record.sample_date    = data.get("sample_date") or None
        record.file_num       = file_num
        record.sample_num     = sample_num
        record.shore_tank     = data.get("shore_tank") or None
        record.level          = data.get("level") or None
        record.movement       = data.get("movement") or None
        record.condition      = data.get("condition") or None
        record.cabinet_num    = data.get("cabinet_num") or None
        record.shelf_num      = data.get("shelf_num") or None
        record.due_date       = parse_date(data.get("due_date",""))
        record.tech_initials  = data.get("tech_initials") or None
        record.notes          = data.get("notes") or None
        record.refresh_status()

    db.session.commit()
    session.pop("import_rows",None)
    session.pop("import_headers",None)
    session.pop("import_auto_map",None)
    flash(f"Import complete — {created} added, {updated} updated, {skipped} skipped.", "success")
    return redirect(url_for("records"))

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    start_scheduler(app)
    app.run(host="0.0.0.0", debug=False, port=5000)
