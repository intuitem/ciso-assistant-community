psql -c "drop database mira;" $POSTGRES_DBLOGIN
psql -c "create database mira;" $POSTGRES_DBLOGIN
psql -c "grant all privileges on database mira to mirauser;" $POSTGRES_DBLOGIN

find . -path "*/migrations/*.py" -not -name "__init__.py" -and -not -path "./venv/*" -delete
find . -path "*/migrations/*.pyc"  -delete
python manage.py makemigrations
python manage.py migrate
python manage.py makemessages -i venv -l fr
python manage.py compilemessages -i venv -l fr
python manage.py createsuperuser --email root@example.com
echo python manage.py runserver

