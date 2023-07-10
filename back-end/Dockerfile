FROM python:3.11-slim
ENV PYTHONUNBUFFERED 1
WORKDIR /app
COPY ./secrets /srv/secrets
RUN pip install --upgrade pip
COPY ./requirements.txt /srv/requirements.txt
RUN pip install -r /srv/requirements.txt

# manage.py loaddata tasks
# manage.py runserver 0.0.0.0:80