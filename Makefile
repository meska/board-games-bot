translations:
	@docker-compose run --rm web python manage.py makemessages --locale it --locale de --locale es --locale fr; \
	docker-compose run --rm web python manage.py compilemessages

migrate:
	@docker-compose run --rm web python manage.py makemigrations;\
	docker-compose run --rm web python manage.py migrate

rqstats:
	@docker-compose run --rm web python manage.py rqstats


remote = root@bgbot
deploy:
	@echo "Deploying to $(remote)";\
	rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.idea' --exclude='.vscode'  ./ $(remote):/opt/board-games-bot/ --delete;\
	scp .env.prod $(remote):/opt/board-games-bot/.env;\
	ssh $(remote) "cd /opt/board-games-bot/ && poetry install --no-root";\
	ssh $(remote) "cd /opt/board-games-bot/ && poetry run python manage.py migrate && poetry run python manage.py compilemessages";\
	ssh $(remote) "cd /opt/board-games-bot/ && rc-service bgbot-web restart";\
	ssh $(remote) "cd /opt/board-games-bot/ && rc-service bgbot-bot restart";\
	ssh $(remote) "cd /opt/board-games-bot/ && rc-service bgbot-worker restart";
