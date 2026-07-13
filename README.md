# ?? VAI Radiology LLC — Backend (Django)

> REST API backend for the **404 Project Not Found** full-stack submission.
> GitHub: https://github.com/misbah7172/VAI_Radiology_LLC

---

## Tech Stack

| Technology | Version |
|---|---|
| Python | **3.13.14** (tested & recommended) |
| Django | 5.1 |
| Django REST Framework | 3.15 |
| djangorestframework-simplejwt | 5.x |
| django-cors-headers | 4.x |
| Pillow | 10.x |
| pydicom | 2.x |
| SimpleITK | 2.x |
| Gunicorn | 22.x |
| WhiteNoise | 6.x |
| Database | SQLite (dev) / PostgreSQL (production via Render) |
| Hosting | Render |

---

## Setup Instructions

### 1. Clone & navigate
```bash
git clone https://github.com/misbah7172/VAI_Radiology_LLC.git
cd VAI_Radiology_LLC/backend
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

The API will be available at http://localhost:8000.

---

## Demo Credentials

| Field | Value |
|---|---|
| Email | demo@vai.com |
| Password | demo1234 |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/auth/login/ | Login with email + password, returns JWT pair |
| POST | /api/auth/refresh/ | Refresh JWT access token |
| GET | /api/auth/me/ | Current user profile |
| GET | /api/auth/health/ | Public health status check |
| GET | /api/tasks/ | List tasks (filters: ?date=YYYY-MM-DD, ?tag=NAME, ?month=YYYY-MM) |
| POST | /api/tasks/ | Create a task (accepts start_date and due_date as ISO datetimes) |
| PUT/PATCH | /api/tasks/{id}/ | Update a task |
| DELETE | /api/tasks/{id}/ | Delete a task |
| POST | /api/tasks/reorder/ | Bulk reorder / status update |
| GET | /api/annotations/sets/ | List image sets |
| POST | /api/annotations/sets/ | Create an image set |
| GET | /api/annotations/images/ | List uploaded images |
| POST | /api/annotations/images/ | Upload image(s) (multipart/form-data) |
| DELETE | /api/annotations/images/{id}/ | Delete an image |
| GET | /api/annotations/polygons/ | List annotations |
| POST | /api/annotations/polygons/ | Create annotation with optional frame_time for video |
| PATCH | /api/annotations/polygons/{id}/ | Update annotation |
| DELETE | /api/annotations/polygons/{id}/ | Delete an annotation |

---

## Data Models

### Task
- title (CharField), description (TextField)
- status: todo / in_progress / done
- priority: low / medium / high
- start_date, due_date (DateTimeField)
- tags (JSONField — list of strings)
- position (IntegerField — ordering within column)
- user (FK to User)

### ImageSet
- name, created_at, user (FK)

### AnnotationImage
- image_set (FK), file (FileField), original_filename
- uploaded_at, user (FK)

### Annotation (Polygon)
- image (FK to AnnotationImage)
- label, color, shape_type
- points (JSONField — list of {x, y} in 0-1 normalised coords)
- frame_time (FloatField — video frame timestamp, nullable)

---

## Deployment

Configured for **Render** via ender.yaml.

Environment variables required on Render:
- DATABASE_URL — auto-set by Render PostgreSQL add-on
- DJANGO_SECRET_KEY — generate with python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
- CORS_ALLOWED_ORIGINS — your Vercel frontend URL
- ALLOWED_HOSTS — .onrender.com

---

## Difficulties and How I Overcame Them

### 1. Production HTTPS and CORS Blockages
When hosting on Render, Django generated http media URLs instead of https because it did not recognise proxy SSL termination. Images loaded over http on an https frontend triggered mixed-content errors.  
Fix: added SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') and USE_X_FORWARDED_HOST = True in settings.py so that request.build_absolute_uri() and media URLs always match the client origin.

### 2. CORS Restrictions with HTML5 Canvas Drawing
Loading media to draw on HTML5 canvas elements threw cross-origin exceptions at the Vercel/Render boundary.  
Fix: replaced the canvas-based layout with an SVG-overlay coordinate map that stores annotation points as normalised floats (0.0 to 1.0), avoiding CORS canvas restrictions entirely.

### 3. Frame-specific Video Annotation Storage
Storing annotations tied to a specific video frame required a custom model field. Without it, annotations would display throughout the entire video.  
Fix: added a frame_time float field to the Annotation model. The frontend syncs at 60 FPS using requestAnimationFrame and only renders annotations where Math.abs(ann.frame_time - video.currentTime) < 0.05 seconds.

### 4. DICOM and NIfTI Upload Processing
Standard Django ImageField rejects DICOM (.dcm) and NIfTI (.nii/.nii.gz) files because Pillow cannot open them. These formats are mandatory for radiology use cases.  
Fix: switched to a plain FileField with an explicit allowlist of extensions validated in the serializer. Added pydicom and SimpleITK to requirements.txt for server-side conversion when generating image previews.

### 5. Batched Multi-Image Upload to the Same Set
The frontend sends multiple sequential upload batches (15 files each) all targeting the same image set. The second and subsequent batches must attach to the set created by the first batch, not create new ones.  
Fix: the upload endpoint accepts an optional image_set_id parameter. If provided it appends to the existing set; if absent it creates a new one and returns its ID. The frontend stores this ID between batches.
