# MAR Resident Portal

A Django web application for UK care homes to maintain MAR (Medication Administration Record) resident profiles, generate resident-facing PDFs and editable DOCX documents, and keep an auditable workflow for staff review.

## Features

- 🔐 **Secure login and role-based access** — only authorised users with assigned portal roles can access the system
- 🧾 **Resident MAR profiles** — structured resident records covering identification, clinical needs, contacts, monitoring, preferences, and safeguarding notes
- 🤖 **AI-assisted drafting** — staff-reviewed wording suggestions, missing-information prompts, inconsistency flags, concise summaries, and MAR front-page text
- 🎙️ **Voice-to-text support** — browser-based dictation helpers for longer care-home notes
- 📄 **PDF + DOCX + print exports** — generate professional resident MAR documents in multiple formats
- 📋 **PRN Protocols** — maintain linked PRN protocol documents alongside the resident profile
- 🕵️ **Audit logs** — record login, review, edit, export, print, and AI-assist activity
- ✅ **GDPR-aware workflow** — sanitised AI prompts, explicit human approval before saving, and security-focused settings defaults

## Quick Start

### 1. Clone & install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set SECRET_KEY and (optionally) OPENAI_API_KEY
```

### 3. Set up database and roles

```bash
python manage.py migrate
python manage.py createsuperuser
```

Running migrations will create the default role groups:

- `Care Staff`
- `Clinical Reviewer`
- `Portal Admin`

Assign users to one of these groups (or make them superusers) before they can sign in.

### 4. Run the server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and sign in.

## Usage

1. **Create a resident MAR profile** from the dashboard
2. **Complete structured resident sections** for clinical, contact, monitoring, preference, and safeguarding information
3. **Use AI assist** to draft wording and surface gaps — review all generated content before saving
4. **Mark profiles as reviewed** when they are ready for operational use
5. **Export PDF, DOCX, or print views** for care-home workflows
6. **Manage linked PRN protocols** for individual medicines when needed

## Security and privacy notes

- The portal requires authentication and a valid role assignment for access
- Audit events are logged for login, profile updates, review, exports, printing, and AI-assisted drafting
- Resident identifiers remain in the portal; resident AI prompts use sanitised clinical context rather than direct identifiers
- AI output must be approved by staff before a resident profile is saved or exported for use
- Production deployments should run with `DEBUG=False`, a strong `SECRET_KEY`, TLS, and restricted `ALLOWED_HOSTS`

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes (production) | Django secret key |
| `DEBUG` | No | `True` for development, `False` for production |
| `OPENAI_API_KEY` | No | Enables AI assist features |
| `DATABASE_PATH` | No | Absolute path to SQLite file |
| `ALLOWED_HOSTS` | Yes (production) | Comma-separated allowed hosts |

## Tech stack

- **Backend**: Django 4.2 (LTS)
- **Database**: SQLite (default) — switchable to PostgreSQL
- **PDF**: WeasyPrint
- **DOCX**: python-docx
- **AI**: OpenAI GPT-4o-mini with sanitised prompts and fallback guidance
- **Frontend**: Bootstrap 5
