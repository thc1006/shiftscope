FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir '.[full]'

RUN useradd --create-home appuser
USER appuser

ENTRYPOINT ["shiftscope"]
CMD ["--help"]
