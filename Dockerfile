FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# copy requirements first so Docker cache is effective
COPY vpn_api/requirements.txt /app/requirements.txt

# install system build deps, install python deps, then remove build deps to keep image small
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		gcc \
		libpq-dev \
		build-essential \
		curl \
		openssh-client \
	&& pip install --no-cache-dir -r /app/requirements.txt \
	&& apt-get purge -y --auto-remove gcc build-essential \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# copy project source and alembic config so alembic works inside container
COPY vpn_api /app/vpn_api
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY scripts /app/scripts
COPY .env.example /app/.env.example
COPY README.md /app/README.md

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

EXPOSE 8000

CMD ["uvicorn", "vpn_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
