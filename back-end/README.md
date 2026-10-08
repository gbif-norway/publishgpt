# Run server
`docker compose up` add --build and -d if you want
`docker exec -it chatipt-back-end-1 /bin/bash`
`./manage.py runserver 0.0.0.0:8000`
Check http://localhost:8000/api

# Load tasks
`./manage.py loaddata tasks`

# Wipe database and make migrations
`docker rm -v chatipt-db-1`, then start up the container again and don't forget
`./manage.py makemigrations && ./manage.py migrate && ./manage.py loaddata tasks`

# Run frontend
`docker exec -it chatipt-front-end-1 /bin/bash`
`npm run dev`
Check http://localhost:3000

## Dataset metadata roles

`SetEML(users=[...])` sets dataset creators. Use `contacts=[...]` and
`metadata_providers=[...]` to assign source contacts and people who supplied the
metadata separately. Each person has `first_name`, `last_name`, `email`, and an
optional `orcid`. The same people can be supplied in all three lists when the
source identifies them in all three roles.

A nonempty contact or metadata provider list replaces the account holder in that
EML role without editing their account. Omitting the list or passing `null`
preserves the saved value; `[]` clears that override and restores the account
holder default. These settings also work with `creators_unknown=true`. Save them
before rebuilding the publication artifacts; metadata edits invalidate earlier
exports.
