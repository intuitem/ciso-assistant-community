psql -c "drop database mira;" $POSTGRES_DBLOGIN
psql -c "create database mira;" $POSTGRES_DBLOGIN
psql -c "grant all privileges on database mira to mirauser;" $POSTGRES_DBLOGIN
rm -f db/mira.sqlite3
find . -path "*/migrations/*.py" -not -name "__init__.py" -and -not -path "./venv/*" -delete
find . -path "*/migrations/*.pyc"  -delete
python manage.py makemigrations cal core iam
python manage.py migrate
python manage.py makemessages -i venv -l fr
python manage.py compilemessages -i venv -l fr
python manage.py createsuperuser --email root@example.com --noinput
echo python manage.py runserver

