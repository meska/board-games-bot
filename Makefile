translations:
	@python manage.py makemessages --locale it; \
	python manage.py compilemessages

migrate:
	@docker-compose run --rm web python manage.py makemigrations;\
	docker-compose run --rm web python manage.py migrate