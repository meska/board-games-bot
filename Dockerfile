FROM python:3.10

WORKDIR /app
RUN pip3 install pipenv
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN pipenv install --system --deploy --ignore-pipfile
COPY . /app