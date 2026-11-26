# QYA: foro de dudas

Foro de preguntas y respuestas para estudiantes. Incluye votos positivos/negativos,
respuesta aceptada por el autor de la pregunta y respuestas generadas por IA.

## Stack

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Flask + Jinja2
- SQLAlchemy + Flask-Migrate (Alembic)
- Google Gemini (opcional, con fallback local)
- pytest
- Ruff

## Requisitos

- Python 3.12 o superior
- uv

## Instalación

```bash
uv sync
cp .env.example .env
```

Completá `GEMINI_API_KEY` en `.env` si querés respuestas reales de Gemini.
Sin clave, la aplicación usa una respuesta de respaldo local.

## Base de datos

La base de desarrollo es SQLite y se crea/actualiza con migraciones:

```bash
uv run flask --app taller db upgrade
```

Para generar una migración nueva después de cambiar los modelos:

```bash
uv run flask --app taller db migrate -m "descripcion del cambio"
uv run flask --app taller db upgrade
```

## Ejecutar

```bash
uv run flask --app taller run --debug
```

La aplicación queda disponible en <http://localhost:5000>.

## Tests

```bash
uv run pytest
```

## Lint y formato

```bash
uv run ruff check .
uv run ruff format .
```

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `SECRET_KEY` | Clave para firmar la cookie de sesión | `development-only-key` |
| `DATABASE_URL` | URL de SQLAlchemy | `sqlite:///app.db` |
| `GEMINI_API_KEY` | Clave de Google Gemini (opcional) | vacío |

## Estructura

```text
src/taller/
├── __init__.py          # application factory
├── extensions.py        # db, migrate
├── models/              # modelos SQLAlchemy
├── routes/              # auth, questions, answers, votes, health
├── services/            # integración con IA
└── templates/           # Jinja2

tests/                   # tests de auth, preguntas, respuestas, votos y health
migrations/              # migraciones de Alembic
```

## Endpoints principales

### Autenticación

```text
GET  /auth/register
POST /auth/register
GET  /auth/login
POST /auth/login
GET  /auth/logout
```

### Preguntas

```text
POST /questions/
POST /questions/ia/pendientes
GET  /foro
```

### Respuestas

```text
POST   /answers/
GET    /answers/question/<id>
PATCH  /answers/<id>/accept
DELETE /answers/<id>/accept
```

### Votos

```text
POST /votes/questions/<id>
POST /votes/answers/<id>
```

### Salud

```text
GET /health
```
