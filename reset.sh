psql -c "drop database asf;" postgres
psql -c "create database asf;" postgres
psql -c "grant all privileges on database asf to asfuser;" postgres

find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete
python manage.py makemigrations
python manage.py migrate
python3 manage.py createsuperuser
python manage.py runserver

