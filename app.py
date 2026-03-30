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
                "%m-%d-%Y", "%d %b %Y", "%B %d, %Y", "%Y-%m-%d %H:%M:%S"):
        try: return datetime.strptime(str(val).strip().split(" ")[0] if "00:00:00" in str(val) else str(val).strip(), fmt).date()
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
    ).order_by(LogRecord.expiry_date).all()
    return render_template("dashboard.html",
        total=total, active=active, due_soon=due_soon,
        overdue=overdue, recent=recent, urgent=urgent)

# ─── Records ──────────────────────────────────────────────────────────────────

@app.route("/records")
def records():
    query = LogRecord.query
    search         = request.args.get("search", "").strip()
    status_filter  = request.args.get("status", "")
    vis_filter     = request.args.get("visibility", "")
    sort_by        = request.args.get("sort", "expiry_date")

    if search:
        query = query.filter(
            LogRecord.product_number.ilike(f"%{search}%") |
            LogRecord.version.ilike(f"%{search}%")        |
            LogRecord.initials.ilike(f"%{search}%")       |
            LogRecord.cabinet_label.ilike(f"%{search}%")  |
            LogRecord.shelf_label.ilike(f"%{search}%")    |
            LogRecord.visibility.ilike(f"%{search}%")
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    if vis_filter:
        query = query.filter_by(visibility=vis_filter)

    sort_map = {
        "expiry_date": LogRecord.expiry_date,
        "input_date":  LogRecord.input_date,
        "product_number": LogRecord.product_number,
        "status":      LogRecord.status,
        "updated_at":  LogRecord.updated_at.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, LogRecord.expiry_date))

    all_records  = query.all()
    visibilities = db.session.query(LogRecord.visibility).distinct().all()
    visibilities = sorted([v[0] for v in visibilities if v[0]])

    return render_template("records.html",
        records=all_records, search=search,
        status_filter=status_filter, vis_filter=vis_filter,
        sort_by=sort_by, visibilities=visibilities)

@app.route("/records/new", methods=["GET", "POST"])
def new_record():
    if request.method == "POST":
        record = LogRecord(
            input_date     = request.form.get("input_date","").strip() or None,
            product_number = request.form.get("product_number","").strip() or None,
            version        = request.form.get("version","").strip() or None,
            visibility     = request.form.get("visibility","").strip() or None,
            cabinet_label  = request.form.get("cabinet_label","").strip() or None,
            shelf_label    = request.form.get("shelf_label","").strip() or None,
            expiry_date    = parse_date(request.form.get("expiry_date","")),
            initials       = request.form.get("initials","").strip() or None,
            notes          = request.form.get("notes","").strip() or None,
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
        record.input_date     = request.form.get("input_date","").strip() or None
        record.product_number = request.form.get("product_number","").strip() or None
        record.version        = request.form.get("version","").strip() or None
        record.visibility     = request.form.get("visibility","").strip() or None
        record.cabinet_label  = request.form.get("cabinet_label","").strip() or None
        record.shelf_label    = request.form.get("shelf_label","").strip() or None
        record.expiry_date    = parse_date(request.form.get("expiry_date",""))
        record.initials       = request.form.get("initials","").strip() or None
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

# ─── CSV / Excel Import ───────────────────────────────────────────────────────

FIELD_MAP_OPTIONS = [
    ("input_date",     "Input Date"),
    ("product_number", "Product Number"),
    ("version",        "Version"),
    ("visibility",     "Visibility"),
    ("cabinet_label",  "Cabinet Label"),
    ("shelf_label",    "Shelf Label"),
    ("expiry_date",    "Expiry Date"),
    ("initials",       "Initials"),
    ("notes",          "Notes"),
    ("__skip__",       "— Skip this column —"),
]

GUESSES = {
    "input_date":     ["input_date","input date","date","inputdate","sample_date","sample date"],
    "product_number": ["product_number","product number","product_num","product num",
                       "productnumber","product_no","product no","file_num","file num",
                       "file_number","file number"],
    "version":        ["version","ver","version_","sample_num","sample num","sample_number"],
    "visibility":     ["visibility","visibility  ","visible","condition","state","status"],
    "cabinet_label":  ["cabinet_label","cabinet label","cabinet","cabinet_num",
                       "cabinet num","cabinet_number","cabinet number"],
    "shelf_label":    ["shelf_label","shelf label","shelf","shelf_num",
                       "shelf num","shelf_number","shelf number"],
    "expiry_date":    ["expiry_date","expiry date","expiry","expiration","expires",
                       "due_date","due date","valid_until","valid until"],
    "initials":       ["initials","initials ","tech_initials","tech initials",
                       "tech","worker","assigned_to"],
    "notes":          ["notes","note","comments","remarks","description"],
}

@app.route("/import", methods=["GET", "POST"])
def import_csv():
    if request.method == "POST" and "csv_file" in request.files:
        f = request.files["csv_file"]
        fname = f.filename.lower()

        # Support both CSV and Excel
        if fname.endswith(".xlsx") or fname.endswith(".xls"):
            import pandas as pd
            df = pd.read_excel(f)
            # Clean column names (strip whitespace)
            df.columns = [str(c).strip() for c in df.columns]
            # Drop unnamed index columns
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
            headers = df.columns.tolist()
            rows = df.astype(str).replace("nan","").to_dict(orient="records")
        elif fname.endswith(".csv"):
            content = f.read().decode("utf-8-sig", errors="replace")
            reader  = csv.DictReader(io.StringIO(content))
            headers = [h.strip() for h in (reader.fieldnames or [])]
            rows    = [{k.strip(): v for k,v in row.items()} for row in reader]
        else:
            flash("Please upload a .csv or .xlsx file.", "danger")
            return redirect(url_for("import_csv"))

        if not headers:
            flash("File appears empty or has no headers.", "danger")
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
        flash("No import data. Please upload your file again.", "warning")
        return redirect(url_for("import_csv"))
    mapping = {h: request.form.get(f"map_{h}","__skip__") for h in headers}
    mapping = {h: f for h, f in mapping.items() if f != "__skip__"}

    created, updated, skipped = 0, 0, 0
    for row in rows:
        data = {field: str(row.get(col,"")).strip() for col, field in mapping.items()}

        if not data.get("product_number") and not data.get("version"):
            skipped += 1; continue

        prod = data.get("product_number") or None
        ver  = data.get("version") or None
        record = None
        if prod and ver:
            record = LogRecord.query.filter_by(product_number=prod, version=ver).first()
        elif prod:
            record = LogRecord.query.filter_by(product_number=prod).first()

        if record is None:
            record = LogRecord(); db.session.add(record); created += 1
        else:
            updated += 1

        record.input_date     = data.get("input_date") or None
        record.product_number = prod
        record.version        = ver
        record.visibility     = data.get("visibility") or None
        record.cabinet_label  = data.get("cabinet_label") or None
        record.shelf_label    = data.get("shelf_label") or None
        record.expiry_date    = parse_date(data.get("expiry_date",""))
        record.initials       = data.get("initials") or None
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
