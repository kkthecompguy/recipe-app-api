#!/bin/sh

set -e # any command that fails in the next commands that we add to the script is gonna fail the whole script,, any portions fails it crashes and know about the failure and fix it instead of just running other commands

python manage.py wait_for_db
python manage.py collectstatic --noinput
python manage.py migrate

uwsgi --socket :9000 --workers 4 --master --enable-threads --module app.wsgi
