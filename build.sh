#!/usr/bin/env bash
# Render build script — runs during deployment

set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Seed demo user
python manage.py seed_demo_user
