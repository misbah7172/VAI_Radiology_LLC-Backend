# 🩺 VAI Radiology LLC — Backend (Django)

> REST API backend for the 404 Project Not Found application.

## Tech Stack

| Technology | Version |
|------------|---------|
| Python | 3.12+ |
| Django | 5.1 |
| Django REST Framework | 3.15 |
| Database | SQLite (dev) / PostgreSQL (production) |
| Auth | JWT (djangorestframework-simplejwt) |
| Hosting | Render |

## Setup Instructions

### 1. Clone & navigate
```bash
git clone <your-backend-repo-url>
cd backend
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Seed demo user
```bash
python manage.py seed_demo_user
```

### 6. Start the dev server
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`.

## Demo Credentials

| Field | Value |
|-------|-------|
| Email | demo@vai.com |
| Password | demo1234 |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login/` | Login with email + password |
| POST | `/api/auth/refresh/` | Refresh JWT token |
| GET | `/api/auth/me/` | Current user profile |
| GET | `/api/tasks/` | List tasks (filter: `?date=YYYY-MM-DD`) |
| POST | `/api/tasks/` | Create a task |
| PUT/PATCH | `/api/tasks/{id}/` | Update a task |
| DELETE | `/api/tasks/{id}/` | Delete a task |
| POST | `/api/tasks/reorder/` | Bulk reorder/status update |
| GET | `/api/annotations/images/` | List uploaded images |
| POST | `/api/annotations/images/` | Upload image(s) |
| DELETE | `/api/annotations/images/{id}/` | Delete an image |
| GET | `/api/annotations/polygons/` | List annotations |
| POST | `/api/annotations/polygons/` | Create polygon annotation |
| DELETE | `/api/annotations/polygons/{id}/` | Delete an annotation |

## Difficulties & How I Overcame Them

*(To be filled after development)*

## Deployment

This backend is configured for **Render** deployment. See `render.yaml` for the infrastructure-as-code configuration.

Environment variables needed on Render:
- `DATABASE_URL` — auto-set by Render PostgreSQL addon
- `DJANGO_SECRET_KEY` — auto-generated
- `CORS_ALLOWED_ORIGINS` — your frontend Vercel URL
- `ALLOWED_HOSTS` — `.onrender.com`
