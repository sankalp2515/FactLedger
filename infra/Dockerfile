FROM node:22-bookworm-slim AS web
WORKDIR /web
RUN corepack enable && corepack prepare pnpm@11.0.0 --activate
COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM python:3.12-slim AS python-build
WORKDIR /build
COPY pyproject.toml ./
COPY infra/requirements-runtime.lock ./requirements-runtime.lock
COPY apps/api/ apps/api/
RUN --mount=type=cache,target=/root/.cache/pip pip wheel --constraint requirements-runtime.lock --wheel-dir /wheels .

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 ARTIFACT_DIR=/data/artifacts WEB_DIST=/app/web
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app && mkdir -p /data/artifacts /app/web && chown -R app:app /data /app
COPY --from=python-build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
WORKDIR /app
COPY alembic.ini ./
COPY migrations/ migrations/
COPY scripts/ scripts/
COPY --from=web /web/dist /app/web
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "product_core.main:app", "--host", "0.0.0.0", "--port", "8000"]
