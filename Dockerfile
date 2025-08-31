FROM python:3.11-slim
WORKDIR /app
COPY ./vpn_api /app/vpn_api
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
EXPOSE 8000
CMD ["uvicorn", "vpn_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
