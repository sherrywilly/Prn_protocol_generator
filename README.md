# PRN Protocol Generator

A Django web application for care homes to manage residents and generate PRN (Pro Re Nata / As Required) medication protocol documents as professional PDFs and editable DOCX files.

## Features

- 📋 **Resident Management** — Add, edit, and manage care home residents
- 💊 **PRN Protocols** — Create detailed medication protocols per resident
- 📄 **PDF + DOCX Export** — Download professional A4 protocol documents as PDF or editable Word files
- 🤖 **AI Assist** — Auto-fill clinical fields using ChatGPT (requires OpenAI API key)
- 🗄️ **Database Storage** — All data persisted in SQLite (easily swappable to PostgreSQL)
- ✅ **GP Reporting Checklist** — Tick-box circumstances for reporting to GP

## Quick Start

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/sherrywilly/Prn_protocol_generator.git
cd Prn_protocol_generator
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set a SECRET_KEY and (optionally) your OPENAI_API_KEY
```

### 3. Set Up Database

```bash
python manage.py migrate
python manage.py createsuperuser   # optional: for admin panel access
```

### 4. Run the Server

```bash
python manage.py runserver
```

Open your browser at **http://127.0.0.1:8000/**

## Desktop App Mode (Data-Safe)

You can run the same app as a desktop window while keeping data outside the app install folder.

### 1. Install Desktop Dependencies

```bash
pip install -r requirements.txt
```

### 2. Launch Desktop App

```bash
python desktop_app.py
```

If you see `ModuleNotFoundError: No module named 'qtpy'`, run:

```bash
pip install -r requirements.txt
```

If your Linux environment still complains about GUI backend modules, run:

```bash
pip install qtpy PyQt5
```

If Qt/GTK bindings are still unavailable, `python desktop_app.py` will now automatically
fall back to browser mode and print the local URL. Data safety is unchanged because it still
uses the same persistent `DATABASE_PATH` location.

What this does:
- Creates a persistent user data folder (platform-specific AppData/Application Support location)
- Uses `DATABASE_PATH` pointing to that folder's `db.sqlite3`
- Copies your existing project `db.sqlite3` into that folder on first run
- Runs migrations automatically before opening the window

This means app updates won’t overwrite resident/protocol data.

## Usage

1. **Add a Resident** — Click "Add Resident" and fill in name, room number, and date of birth
2. **Add a PRN Protocol** — Open a resident's profile and click "Add PRN Protocol"
3. **AI Assist** — Enter the medicine name and click "AI Assist" to auto-populate clinical fields (requires `OPENAI_API_KEY` in `.env`)
4. **Download PDF or DOCX** — Click the export buttons on any protocol to download a formatted PDF or editable Word document

## Admin Panel

Visit **http://127.0.0.1:8000/admin/** (requires superuser account created above).

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes (production) | Django secret key |
| `DEBUG` | No | `True` for development, `False` for production |
| `OPENAI_API_KEY` | No | Enables AI Assist feature (GPT-4o-mini) |
| `DATABASE_PATH` | No | Absolute path to SQLite file (desktop mode uses this automatically) |

## Tech Stack

- **Backend**: Django 4.2 (LTS)
- **Database**: SQLite (default) — switchable to PostgreSQL
- **PDF**: WeasyPrint (HTML/CSS → PDF)
- **DOCX**: python-docx
- **AI**: OpenAI GPT-4o-mini
- **Frontend**: Bootstrap 5