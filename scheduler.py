"""
Scheduler — daily expiry email notifications at 08:00
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import smtplib, configparser, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

def load_email_config():
    config = configparser.ConfigParser()
    config.read("email_config.ini")
    if "email" not in config: return None
    cfg = config["email"]
    if cfg.get("enabled","false").lower() != "true": return None
    return cfg

def send_email(cfg, to_address, subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = cfg["from_address"]
        msg["To"]   = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"])) as server:
            server.ehlo(); server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(cfg["from_address"], to_address, msg.as_string())
        logger.info(f"Email sent to {to_address}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_address}: {e}")
        return False

def check_and_notify(app):
    cfg = load_email_config()
    if not cfg:
        logger.info("Email notifications disabled or not configured.")
        return

    with app.app_context():
        from database import db, LogRecord

        records = LogRecord.query.filter(
            LogRecord.expiry_date.isnot(None),
        ).all()

        notified = 0
        for record in records:
            record.refresh_status()
            days = record.days_until_expiry

            should_notify = (
                record.status in ("due_soon", "overdue") and
                (
                    record.last_notified_at is None or
                    (datetime.utcnow() - record.last_notified_at).days >= 1
                )
            )
            if not should_notify:
                continue

            to_addr = cfg.get("from_address","")
            if not to_addr:
                continue

            if days is not None and days < 0:
                subject = f"⚠️ OVERDUE: Product {record.product_number} / Version {record.version}"
                urgency = f"<strong style='color:#c0392b'>OVERDUE — {abs(days)} day(s) ago</strong>"
            else:
                subject = f"🔔 Expiring Soon: Product {record.product_number} / Version {record.version}"
                urgency = f"<strong style='color:#e67e22'>Expires in {days} day(s) — {record.expiry_date}</strong>"

            html_body = f"""
            <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
              <div style="background:#1a2332;padding:24px;border-radius:8px 8px 0 0">
                <h2 style="color:#fff;margin:0">ComplianceLog — Expiry Alert</h2>
              </div>
              <div style="border:1px solid #ddd;padding:24px;border-radius:0 0 8px 8px">
                <p>A log record requires attention:</p>
                <table style="width:100%;border-collapse:collapse;margin:16px 0">
                  <tr style="background:#f8f9fa"><td style="padding:8px;font-weight:bold">Product #</td><td style="padding:8px">{record.product_number or '—'}</td></tr>
                  <tr><td style="padding:8px;font-weight:bold">Version</td><td style="padding:8px">{record.version or '—'}</td></tr>
                  <tr style="background:#f8f9fa"><td style="padding:8px;font-weight:bold">Visibility</td><td style="padding:8px">{record.visibility or '—'}</td></tr>
                  <tr><td style="padding:8px;font-weight:bold">Cabinet / Shelf</td><td style="padding:8px">{record.cabinet_label or '—'} / {record.shelf_label or '—'}</td></tr>
                  <tr style="background:#f8f9fa"><td style="padding:8px;font-weight:bold">Initials</td><td style="padding:8px">{record.initials or '—'}</td></tr>
                  <tr><td style="padding:8px;font-weight:bold">Status</td><td style="padding:8px">{urgency}</td></tr>
                </table>
                <p style="color:#888;font-size:12px">Automated notification from ComplianceLog.</p>
              </div>
            </html></body>
            """

            if send_email(cfg, to_addr, subject, html_body):
                record.last_notified_at = datetime.utcnow()
                notified += 1

        db.session.commit()
        logger.info(f"Notification run complete. Notified: {notified}.")

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: check_and_notify(app),
        trigger="cron", hour=8, minute=0,
        id="expiry_notifications", replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — expiry checks run daily at 08:00.")
    return scheduler
