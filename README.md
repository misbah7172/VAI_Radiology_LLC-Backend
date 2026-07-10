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
| GET | `/api/auth/health/` | Public health status check |
| GET | `/api/tasks/` | List tasks (filters: `?date=YYYY-MM-DD`, `?tag=NAME`, `?month=YYYY-MM`) |
| POST | `/api/tasks/` | Create a task (accepts `start_date` and `due_date` as ISO datetimes) |
| PUT/PATCH | `/api/tasks/{id}/` | Update a task |
| DELETE | `/api/tasks/{id}/` | Delete a task |
| POST | `/api/tasks/reorder/` | Bulk reorder/status update |
| GET | `/api/annotations/images/` | List uploaded images |
| POST | `/api/annotations/images/` | Upload image(s) or video(s) |
| DELETE | `/api/annotations/images/{id}/` | Delete an image or video |
| GET | `/api/annotations/polygons/` | List annotations |
| POST | `/api/annotations/polygons/` | Create annotation (attaches optional `frame_time` for video frames) |
| DELETE | `/api/annotations/polygons/{id}/` | Delete an annotation |

## Difficulties & How I Overcame Them

1. **Production HTTPS & CORS Blockages**:
   When hosting on Render, Django generated `http` media URLs instead of `https` because it did not recognize proxy SSL termination. We resolved this by adding `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` and `USE_X_FORWARDED_HOST = True` in `settings.py` so that media URLs match the client origin correctly.
   
2. **CORS Restrictions with HTML5 Canvas Drawing**:
   Initially, loading media to draw bounding boxes/points on HTML5 `<canvas>` elements threw cross-origin exceptions because of Vercel/Render hosting boundaries. We replaced the canvas-based drawing layout with an SVG-overlay coordinate map system which cleanly maps percentage points `(0.0 - 1.0)` over images and videos without triggering CORS security blocks.

3. **Frame-specific Video Annotation Display**:
   To prevent video annotations from showing throughout the entire duration of a video, we added a `frame_time` field (float) to the `Annotation` model. The frontend syncs time at 60 FPS using a `requestAnimationFrame` loop and filters elements to only render annotations when `Math.abs(ann.frame_time - video.currentTime) < 0.05` seconds.

## Deployment

This backend is configured for **Render** deployment. See `render.yaml` for the infrastructure-as-code configuration.

Environment variables needed on Render:
- `DATABASE_URL` — auto-set by Render PostgreSQL addon
- `DJANGO_SECRET_KEY` — auto-generated
- `CORS_ALLOWED_ORIGINS` — your frontend Vercel URL
- `ALLOWED_HOSTS` — `.onrender.com`
