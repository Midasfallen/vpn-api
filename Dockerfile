FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# system deps for psycopg2 and build
RUN apt-get update \
	&& apt-get install -y --no-install-recommends gcc libpq-dev build-essential curl \
	&& apt-get upgrade -y \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# install python deps
COPY vpn_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy project source and alembic config so alembic works inside container
COPY vpn_api /app/vpn_api
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY .env.example /app/.env.example
COPY README.md /app/README.md

EXPOSE 8000

CMD ["uvicorn", "vpn_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
