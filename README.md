# CampusHire Backend

CampusHire Backend is a Dockerized FastAPI microservices backend for a campus hiring platform. It is composed of four domain services behind an Nginx API gateway, with PostgreSQL for persistence, Redis for token/session support, RabbitMQ for domain events, and shared Python packages for common auth, logging, storage, and event schemas.

## Architecture

```text
Frontend
   |
   | /api/v1/*
   v
Nginx API Gateway :8080
   |
   |-- identity-service       :8001
   |-- opportunity-service    :8002
   |-- application-service    :8003
   |-- communications-service :8004
   |
   |-- PostgreSQL :5432
   |-- Redis      :6379
   |-- RabbitMQ   :5672
```

The API gateway is the only service that should be exposed publicly in a VM deployment. PostgreSQL, Redis, RabbitMQ, and the internal FastAPI services should stay on the private Docker network.

## Services

| Service | Path | Port | Responsibility |
| --- | --- | --- | --- |
| API Gateway | `nginx/nginx.conf` | `8080 -> 80` | Routes public API requests to the correct internal service and performs auth checks for protected routes. |
| Identity Service | `services/identity-service` | `8001` | User registration, login, refresh tokens, logout, token validation, and student profiles. |
| Opportunity Service | `services/opportunity-service` | `8002` | Placement drives/opportunities, registrations, file uploads, deadline processing, and Excel exports. |
| Application Service | `services/application-service` | `8003` | Student applications, resume upload, application status updates, withdrawal, and timelines. |
| Communications Service | `services/communications-service` | `8004` | Student queries, coordinator replies, notifications, and event-driven communication handling. |

## Infrastructure

| Component | Image | Purpose |
| --- | --- | --- |
| PostgreSQL | `postgres:16-alpine` | Stores service databases: `auth_db`, `opportunity_db`, `application_db`, and `communications_db`. |
| Redis | `redis:7-alpine` | Used by the identity service for auth-related caching/token support. |
| RabbitMQ | `rabbitmq:3-management-alpine` | Carries domain events between services. |
| Nginx | `nginx:1.27-alpine` | Public API gateway and reverse proxy. |

Databases are initialized from `scripts/init-databases.sql`.

## Shared Packages

The `shared/` directory contains local Python packages installed into service images:

| Package | Purpose |
| --- | --- |
| `campushire-common` | JWT helpers, auth dependencies, logging, enums, and shared security utilities. |
| `campushire-events` | Event publisher/consumer logic and domain event schemas. |
| `campushire-storage` | Storage backend abstractions for local or Azure-backed file storage. |

## Main API Areas

All external requests should go through the gateway:

```text
http://localhost:8080
```

Main route groups:

| Route Prefix | Service |
| --- | --- |
| `/api/v1/auth/*` | Identity Service |
| `/api/v1/opportunities/*` | Opportunity Service |
| `/api/v1/applications/*` | Application Service |
| `/api/v1/queries/*` | Communications Service |
| `/api/v1/notifications/*` | Communications Service |
| `/api/v1/files/*` | File serving through application/opportunity services |

Gateway health check:

```bash
curl http://localhost:8080/health
```

## Environment Variables

Copy the example file before running:

```bash
cp .env.example .env
```

Important variables:

| Variable | Description |
| --- | --- |
| `POSTGRES_USER` | PostgreSQL user. |
| `POSTGRES_PASSWORD` | PostgreSQL password. Use URL-safe characters when used in compose URLs. |
| `JWT_SECRET_KEY` | Secret used to sign JWT tokens. Generate a strong value for production. |
| `RABBITMQ_USER` | RabbitMQ user. |
| `RABBITMQ_PASSWORD` | RabbitMQ password. Use URL-safe characters when used in compose URLs. |
| `CORS_ORIGINS` | Comma-separated frontend origins allowed by the backend. Do not include trailing slashes. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | SMTP settings for outgoing communication. |
| `STORAGE_BACKEND` | `local` by default. |
| `LOCAL_STORAGE_PATH` | Path used by containers for uploaded files. |
| `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER` | Azure storage settings when using Azure-backed storage. |

Generate a JWT secret:

```bash
openssl rand -hex 32
```

Example production CORS value:

```env
CORS_ORIGINS=https://campus-hr-f.vercel.app,http://localhost:5173,http://127.0.0.1:5173
```

## Local Development

Build and start everything:

```bash
docker compose up -d --build
```

Check service status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Stop services:

```bash
docker compose down
```

Reset containers and named volumes:

```bash
docker compose down -v
```

## Azure VM Deployment Notes

For the current VM deployment, the backend is served at:

```text
http://20.219.9.65:8080
```

Recommended VM setup:

1. Install Docker and Docker Compose.
2. Clone this repository.
3. Create `.env` from `.env.example`.
4. Set strong values for database, RabbitMQ, JWT, SMTP, and CORS.
5. Start the stack with Docker Compose.
6. Open only required Azure NSG ports.

Required public inbound ports:

| Port | Purpose |
| --- | --- |
| `22` | SSH. Restrict this to your own IP whenever possible. |
| `8080` | Public backend API gateway. |

Do not expose these publicly in production:

| Port | Component |
| --- | --- |
| `5432` | PostgreSQL |
| `6379` | Redis |
| `5672` | RabbitMQ AMQP |
| `15672` | RabbitMQ Management UI |

On small VMs, RabbitMQ and the service containers may need swap memory:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Frontend Deployment Note

If the frontend is served over HTTPS, browsers will block direct calls to an HTTP backend because of mixed content rules. The deployed frontend should either:

1. Proxy `/api/*` from the frontend host to the backend gateway, or
2. Use an HTTPS backend domain such as `https://api.example.com`.

For Vercel, a rewrite can proxy API requests:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "http://20.219.9.65:8080/api/:path*"
    }
  ]
}
```

With this approach, the browser calls same-origin paths such as:

```text
https://campus-hr-f.vercel.app/api/v1/auth/login
```

Vercel forwards those requests to the backend VM.

## Useful Commands

Check gateway health:

```bash
curl http://localhost:8080/health
```

Check all containers:

```bash
docker compose ps
```

Restart after environment changes:

```bash
docker compose down
docker compose up -d
```

Inspect a service log:

```bash
docker compose logs --tail=150 identity-service
docker compose logs --tail=150 opportunity-service
docker compose logs --tail=150 application-service
docker compose logs --tail=150 communications-service
docker compose logs --tail=150 api-gateway
```

Validate compose syntax:

```bash
docker compose config
```

## API Documentation

Each FastAPI service serves OpenAPI docs internally:

| Service | Internal Docs |
| --- | --- |
| Identity | `http://localhost:8001/docs` |
| Opportunity | `http://localhost:8002/docs` |
| Application | `http://localhost:8003/docs` |
| Communications | `http://localhost:8004/docs` |

When running through Docker Compose, these service ports are intended for internal access. Public API traffic should use the Nginx gateway.
