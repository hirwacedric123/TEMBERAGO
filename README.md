# TemberaGo

Premium tourism, executive transportation, and destination management in Rwanda.

## Features

- Responsive landing page with custom hero imagery
- **Booking form** — full quote requests saved to SQLite
- **Contact form** — inquiries with email notification (optional)
- **Quick quote strip** — hero booking bar with auto-prefill to full form
- Flask REST API for all form submissions

## Quick Start

### 1. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment (optional)

```bash
copy .env.example .env
```

Edit `.env` with your phone, email, and SMTP settings for email alerts.

### 3. Run the server

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Landing page |
| POST | `/api/booking` | Full booking / quote request |
| POST | `/api/contact` | Contact form message |
| POST | `/api/quick-quote` | Hero quick quote strip |
| GET | `/api/health` | Health check |

Form data is stored in `data/temberago.db`.

## Project Structure

```
├── app.py              # Flask application
├── templates/
│   └── index.html      # Main landing page
├── static/
│   ├── images/         # Hero & assets
│   └── js/app.js       # Form handling & UI
├── data/               # SQLite database (created on first run)
├── requirements.txt
└── .env.example
```

## Legacy

The original standalone `temberago.html` is kept for reference. Use the Flask app for production.
