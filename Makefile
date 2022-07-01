translations:
	@docker-compose run --rm web python manage.py makemessages --locale it --locale de --locale es --locale fr; \
	docker-compose run --rm web python manage.py compilemessages

migrate:
	@docker-compose run --rm web python manage.py makemigrations;\
	docker-compose run --rm web python manage.py migrate

rqstats:
	@docker-compose run --rm web python manage.py rqstats


# cleanup icloud sync duplicates
cleandupes:
	@find . -regex '.* 2\..*' -delete -print;\
	find . -regex '.* 2' -delete -print;
	@find . -regex '.* 3\..*' -delete -print;\
    find . -regex '.* 3' -delete -print;
	@find . -regex '.* 4\..*' -delete -print;\
	find . -regex '.* 4' -delete -print;