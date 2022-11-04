psql -c "drop database mira;" nassim
psql -c "create database mira;" nassim
psql -c "grant all privileges on database mira to mirauser;" nassim

find . -path "*/migrations/*.py" -not -name "__init__.py" -and -not -path "./venv/*" -delete
find . -path "*/migrations/*.pyc"  -delete
python manage.py makemigrations
python manage.py migrate
python3 manage.py createsuperuser --email root@example.com
python manage.py runserver

