#!/usr/bin/env bash

set -e errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate