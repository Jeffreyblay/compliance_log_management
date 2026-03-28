"""
Database model for ComplianceLog — matched to actual CSV structure
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
    sample_date    = db.Column(db.String(50),  nullable=True)
    file_num       = db.Column(db.String(100), nullable=True)
    sample_num     = db.Column(db.String(100), nullable=True)
    shore_tank     = db.Column(db.String(100), nullable=True)
    level          = db.Column(db.String(100), nullable=True)
    movement       = db.Column(db.String(200), nullable=True)
    condition      = db.Column(db.String(100), nullable=True)
    cabinet_num    = db.Column(db.String(100), nullable=True)
    shelf_num      = db.Column(db.String(100), nullable=True)
    due_date       = db.Column(db.Date,        nullable=True)
    tech_initials  = db.Column(db.String(50),  nullable=True)
    notes          = db.Column(db.Text,        nullable=True)

    # status: active | due_soon | overdue | no_due_date
    status         = db.Column(db.String(30), default="active")
    notify_days_before = db.Column(db.Integer, default=30)
    last_notified_at   = db.Column(db.DateTime, nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def refresh_status(self):
        if not self.due_date:
            self.status = "no_due_date"; return
        notify = self.notify_days_before or 30
        delta  = (self.due_date - date.today()).days
        if delta < 0:          self.status = "overdue"
        elif delta <= notify:  self.status = "due_soon"
        else:                  self.status = "active"

    @property
    def days_until_due(self):
        if not self.due_date: return None
        return (self.due_date - date.today()).days

    @property
    def status_label(self):
        return {
            "active":      "Active",
            "due_soon":    "Due Soon",
            "overdue":     "Overdue",
            "no_due_date": "No Due Date",
        }.get(self.status, self.status)

    @property
    def display_name(self):
        """A short human-readable identifier for this record."""
        parts = [x for x in [self.file_num, self.sample_num] if x]
        return " / ".join(parts) if parts else f"Record #{self.id}"
