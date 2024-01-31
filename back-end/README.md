# Run dev
`docker compose up` add --build and -d if you want
`docker exec -it publishgpt-back-end-1 /bin/bash`
`./manage.py runserver 0.0.0.0:8000`

# Load tasks
`./manage.py loaddata tasks`

# Wipe database and make migrations
`docker rm -v publishgpt-db-1`, then start up the container again and don't forget
`./manage.py makemigrations & ./manage.py migrate`