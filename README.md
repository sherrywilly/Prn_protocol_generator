# PRN Protocol Generator

A Django web application for care homes to manage residents and generate PRN (Pro Re Nata / As Required) medication protocol documents as professional PDFs.

## Features

- 📋 **Resident Management** — Add, edit, and manage care home residents
- 💊 **PRN Protocols** — Create detailed medication protocols per resident
- 📄 **PDF Generation** — Download professional A4 protocol documents matching care home standards
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

## Usage

1. **Add a Resident** — Click "Add Resident" and fill in name, room number, and date of birth
2. **Add a PRN Protocol** — Open a resident's profile and click "Add PRN Protocol"
3. **AI Assist** — Enter the medicine name and click "AI Assist" to auto-populate clinical fields (requires `OPENAI_API_KEY` in `.env`)
4. **Download PDF** — Click the "PDF" button on any protocol to download a formatted A4 document

## Admin Panel

Visit **http://127.0.0.1:8000/admin/** (requires superuser account created above).

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes (production) | Django secret key |
| `DEBUG` | No | `True` for development, `False` for production |
| `OPENAI_API_KEY` | No | Enables AI Assist feature (GPT-4o-mini) |

## Tech Stack

- **Backend**: Django 4.2 (LTS)
- **Database**: SQLite (default) — switchable to PostgreSQL
- **PDF**: WeasyPrint (HTML/CSS → PDF)
- **AI**: OpenAI GPT-4o-mini
- **Frontend**: Bootstrap 5