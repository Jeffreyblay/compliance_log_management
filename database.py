"""
Database model for ComplianceLog — matched to latest field structure
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
import os

db = SQLAlchemy()

def init_db(app):
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'compliance.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()

class LogRecord(db.Model):
    __tablename__ = "log_records"

    id             = db.Column(db.Integer, primary_key=True)
    input_date     = db.Column(db.String(50),  nullable=True)   # Input Date
    product_number = db.Column(db.String(100), nullable=True)   # Product Number
    version        = db.Column(db.String(100), nullable=True)   # Version
    visibility     = db.Column(db.String(100), nullable=True)   # Visibility (condition/state)
    cabinet_label  = db.Column(db.String(100), nullable=True)   # Cabinet Label
    shelf_label    = db.Column(db.String(100), nullable=True)   # Shelf Label
    expiry_date    = db.Column(db.Date,        nullable=True)   # Expiry Date
    initials       = db.Column(db.String(50),  nullable=True)   # Initials
    notes          = db.Column(db.Text,        nullable=True)

    # status: active | due_soon | overdue | no_expiry
    status             = db.Column(db.String(30), default="active")
    notify_days_before = db.Column(db.Integer, default=30)
    last_notified_at   = db.Column(db.DateTime, nullable=True)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def refresh_status(self):
        if not self.expiry_date:
            self.status = "no_expiry"; return
        notify = self.notify_days_before or 30
        delta  = (self.expiry_date - date.today()).days
        if delta < 0:         self.status = "overdue"
        elif delta <= notify: self.status = "due_soon"
        else:                 self.status = "active"

    @property
    def days_until_expiry(self):
        if not self.expiry_date: return None
        return (self.expiry_date - date.today()).days

    @property
    def status_label(self):
        return {
            "active":   "Active",
            "due_soon": "Due Soon",
            "overdue":  "Overdue",
            "no_expiry":"No Expiry",
        }.get(self.status, self.status)

    @property
    def display_name(self):
        parts = [x for x in [self.product_number, self.version] if x]
        return " / ".join(parts) if parts else f"Record #{self.id}"
