.PHONY: build rebuild up down restart migrate create-admin test coverage web/shell db/shell logs backup restore create-app-user

include .env
export $(shell sed 's/=.*//' .env)

build:
	docker compose build

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up

up:
	docker compose up -d

down:
	docker compose down

restart: down up

migrate:
	docker compose run --rm web python manage.py migrate

create-admin:
	docker compose run --rm web python manage.py createsuperuser

test:
	docker compose run --rm web python manage.py test

coverage:
	docker compose run --rm web coverage run --source='.' manage.py test
	docker compose run --rm web coverage report
	docker compose run --rm web coverage html

web/shell:
	docker compose run --rm web /bin/bash

db/shell:
	docker compose run --rm db /bin/bash

logs:
	docker compose logs -f

backup:
	docker exec -t aieye-db pg_dump -U $(DB_USER) -d $(DB_NAME) > backups/backup_`date +%Y%m%d_%H%M%S`.sql

restore:
	bash restore-db.sh $(DB_USER) $(DB_NAME) $(file)

create-app-user:
	docker compose run --rm web python manage.py create_app_user $(EMAIL) $(PASSWORD) $(FIRST_NAME) $(LAST_NAME)

create-app-admin:
	docker compose run --rm web python manage.py create_app_admin $(EMAIL) $(PASSWORD) $(FIRST_NAME) $(LAST_NAME)
