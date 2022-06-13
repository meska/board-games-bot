translations:
	@docker-compose run --rm web python manage.py makemessages --locale it; \
	docker-compose run --rm web python manage.py compilemessages

migrate:
	@docker-compose run --rm web python manage.py makemigrations;\
	docker-compose run --rm web python manage.py migrate

rqstats:
	@docker-compose run --rm web python manage.py rqstats
