FROM python:3.11-slim

WORKDIR /app

COPY shared/campushire-common /shared/campushire-common
COPY shared/campushire-events /shared/campushire-events
RUN pip install --no-cache-dir /shared/campushire-common /shared/campushire-events

COPY services/communications-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/communications-service/ .

ENV PYTHONPATH=/app
EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
