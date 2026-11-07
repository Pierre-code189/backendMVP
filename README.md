# MVP Backend (FastAPI + PostgreSQL)

Esqueleto base del MVP. Sin lógica de negocio, modelos ni scraping (fase posterior).

## Stack

- Python 3.12 + FastAPI + Uvicorn
- SQLAlchemy 2.x + psycopg2-binary
- PostgreSQL 16
- Playwright (async) + Chromium
- pydantic v2 + pydantic-settings
- Docker + docker-compose

## Estructura

```
.
├── app/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── config/              # Settings (pydantic-settings)
│   ├── api/routes/          # Endpoints (placeholder)
│   ├── domain/              # Entidades/dominio (placeholder)
│   ├── infrastructure/      # Acceso a datos, repositorios (placeholder)
│   ├── usecases/            # Casos de uso (placeholder)
│   ├── services/            # Servicios externos (placeholder)
│   └── scraping/            # Playwright (fase posterior)
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── .dockerignore
```

## Requisitos (WSL)

- WSL2 con Docker Engine instalado y corriendo
- El proyecto debe estar en el filesystem Linux de WSL (no bajo `/mnt/c/...`)

```bash
# Verificar
docker --version
docker compose version
pwd   # debe ser un path tipo /home/... o /home/user/proyectos/...
```

## Levantar

```bash
# 1. Copiar variables
cp .env.example .env

# 2. Levantar (api + db)
docker compose up --build

# 3. Verificar
curl http://localhost:8000/docs
```

## Detener

```bash
docker compose down        # detener
docker compose down -v     # detener y borrar volumen de Postgres
```

## Notas

- Servicios en red bridge; `api` se conecta a `db` por nombre de servicio (`POSTGRES_HOST=db`), sin `network_mode: host`.
- Volumen persistente `pgdata` para los datos de PostgreSQL.
- Chromium de Playwright se instala en el build de la imagen `api`.
