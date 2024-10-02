FROM python:3.11-slim
ENV PYTHONUNBUFFERED 1
WORKDIR /app
RUN pip install uv
COPY ./requirements.txt /srv/requirements.txt
RUN uv pip install -r /srv/requirements.txt --system
# Change the CMD to use Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app.wsgi:application"]
