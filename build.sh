#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e errexit

# Install dependencies
pip install -r requirements.txt

# Make migrations
python manage.py collectstatic --no-input
python manage.py migrate

# Seed initial data
python manage.py seed_users
python manage.py seed_groups
python manage.py seed_prefs