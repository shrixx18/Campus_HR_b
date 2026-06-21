FROM python:3.11-slim

WORKDIR /app

COPY shared/campushire-common /shared/campushire-common
RUN pip install --no-cache-dir /shared/campushire-common

COPY services/identity-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/identity-service/ .

ENV PYTHONPATH=/app
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
