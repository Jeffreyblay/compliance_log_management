# ◈ Compliance Log Management System

**Open-source retain log book management system for Windows.**  
Track sample records, due dates, cabinet locations and tech assignments — runs on your office network with no internet or subscriptions required.

---

## Features

- 📋 Full record management — add, edit, view, delete
- 🔍 Search & filter by file number, sample, tank, tech, condition
- ⚠️ Automatic due date tracking — Active / Due Soon / Overdue
- 📧 Daily email alerts at 08:00 for overdue records
- ⇪ CSV import with auto column mapping
- 🏢 Runs on one PC, whole team accesses via office WiFi browser
- 🔓 No login required — open straight to dashboard

## Data Fields

Matches your existing CSV format exactly:

| Field | Description |
|---|---|
| Sample Date | Date the sample was logged |
| File Number | Unique file identifier |
| Sample Number | Sample reference within the file |
| Shore Tank | Associated shore tank |
| Level | Recorded level measurement |
| Movement | Movement description |
| Condition | Current state (e.g. active, dgr) |
| Cabinet Number | Physical cabinet location |
| Shelf Number | Shelf within the cabinet |
| Due Date | Date due for review — drives status |
| Tech Initials | Responsible technician |

## Quick Start

### 1. Install Python
Download from [python.org](https://python.org/downloads) — tick **"Add Python to PATH"** during install.

### 2. Download & extract
Download the latest release zip and extract to `C:\ComplianceLog\`

### 3. Run
Double-click `start.bat` — the app installs dependencies and starts automatically.

### 4. Open in browser
Go to `http://localhost:5000` — your team uses `http://YOUR-IP:5000`

### 5. Import your CSV
Click **Import CSV** in the sidebar, upload your file, confirm the column mapping.

## Files

```
compliance_log/
├── start.bat              ← double-click to start
├── stop.bat               ← double-click to stop
├── create_shortcut.bat    ← run once for desktop shortcut
├── app.py                 ← Flask application
├── database.py            ← SQLite models
├── scheduler.py           ← email notification scheduler
├── requirements.txt
└── templates/             ← HTML pages
```

## Email Notifications

Go to **Email Settings** in the sidebar. Enter your SMTP details.  
Gmail: use host `smtp.gmail.com`, port `587`, and an [App Password](https://support.google.com/accounts/answer/185833).  
Alerts fire daily at **08:00** as long as the host PC is running.

## Requirements

- Windows 10 or 11
- Python 3.12+
- Office WiFi network (for team access)

## License

MIT — free to use, modify and distribute.
