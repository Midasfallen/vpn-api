FROM python:3.11-slim
WORKDIR /app
# Update OS packages to pick up security fixes in the base image
# running apt-get upgrade inside the image reduces exposure to known OS CVEs
RUN apt-get update && apt-get upgrade -y \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*
COPY ./vpn_api /app/vpn_api
COPY vpn_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
EXPOSE 8000
CMD ["uvicorn", "vpn_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
