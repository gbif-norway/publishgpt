FROM python:3.11-slim
ENV PYTHONUNBUFFERED 1
WORKDIR /app
# COPY ./secrets /srv/secrets
# RUN pip install --upgrade pip
RUN pip install uv
COPY ./requirements.txt /srv/requirements.txt
RUN uv pip install -r /srv/requirements.txt --system
# RUN python manage.py makemigrations & python manage.py migrate
# RUN python manage.py loaddata tasks
# ./manage.py runserver 0.0.0.0:8000
