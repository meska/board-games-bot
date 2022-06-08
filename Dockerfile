FROM python:3.10

WORKDIR /app
COPY pyproject.toml poetry.lock /app/

RUN pip install -U pip \
    && pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . /app
CMD ["python", "manage.py", "runserver"]