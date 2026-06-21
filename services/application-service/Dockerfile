FROM python:3.11-slim

WORKDIR /app

COPY shared/campushire-common /shared/campushire-common
COPY shared/campushire-events /shared/campushire-events
COPY shared/campushire-storage /shared/campushire-storage
RUN pip install --no-cache-dir /shared/campushire-common /shared/campushire-events /shared/campushire-storage

COPY services/application-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/application-service/ .

ENV PYTHONPATH=/app
EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
