# Optional container deploy. Render can also deploy this with its native Python runtime
# via render.yaml (no Docker needed) - this is here for Fly.io / Cloud Run / local parity.
FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py solution_app.py stitch.py ./

EXPOSE 8000
ENV PORT=8000
ENV APP_MODULE=solution_app
CMD ["sh", "-c", "uvicorn ${APP_MODULE}:app --host 0.0.0.0 --port ${PORT}"]
