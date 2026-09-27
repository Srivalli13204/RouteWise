#!/usr/bin/env bash

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

python manage.py loaddata mobility/fixtures/initial_data.json

python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = 'Srivalli'
password = 'Srivalli@13'
email = 'isiri1320@gmail.com'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print('Superuser created successfully.')
else:
    print('Superuser already exists.')
"