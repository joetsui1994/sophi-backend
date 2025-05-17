# sophi-backend

REST API backend for [SOPHI](https://sophi-oxf.io)  
**Sandbox for Optimising genomic sampling for PHylogeographic Inference**

This project powers the server-side of SOPHI, providing endpoints for managing simulated outbreak data, handling inference requests, and supporting user authentication.

---

## Features

- Retrieval of simulated outbreak data
- Processing of new inference requests
- Retrieval of inference outputs
- User login and authentication system
- Retrieval of user data

---

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- Redis (for Celery task queue)
- pip (with virtualenv)
- (Production) gunicorn, nginx

### Setup Instructions

1. **Clone the repository**

    ```bash
    git clone https://github.com/yourusername/sophi-backend.git
    cd sophi-backend
    ```

2. **Create & activate a virtual environment**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment variables**

    Copy the `.env.example` file to `.env` and edit values as needed:

    - `SECRET_KEY`
    - `DEBUG`
    - `ALLOWED_HOSTS`
    - `DB_NAME`
    - `DB_USER`
    - `DB_PASSWORD`
    - `DB_HOST`
    - `DB_PORT`

5. **Set up the database**

    ```bash
    python manage.py migrate
    ```

6. **Start Redis and Celery (for background tasks)**

    Make sure Redis server is running:
    ```bash
    redis-server
    ```

    Then start Celery in a new terminal:
    ```bash
    celery -A sophi_backend worker -l info
    ```

7. **Run the Django development server**

    ```bash
    python manage.py runserver
    ```

---

## Environment Variables

All sensitive/project-specific settings are managed via environment variables. Key variables:

- `SECRET_KEY` — Django secret key
- `DEBUG` — Set to `True` for development, `False` for production
- `ALLOWED_HOSTS` — List of allowed hosts
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — PostgreSQL connection details

You can see sample development/production settings in `settings/dev.py` and `settings/prod.py`.

---

## Deployment Notes

- For production, use **gunicorn** (or another WSGI server) behind **nginx**.
- Make sure to run `python manage.py collectstatic` before deployment.
- For CORS and CSRF configuration, refer to `settings/prod.py`.
- Celery and Redis must be running for background processing.

---

## Testing

```bash
python manage.py test
