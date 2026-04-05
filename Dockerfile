FROM python:3.12-slim AS base

WORKDIR /app

# Install shiftscope with all extras from PyPI
RUN pip install --no-cache-dir "shiftscope[full]"

# Non-root user
RUN useradd --create-home appuser
USER appuser

ENTRYPOINT ["shiftscope"]
CMD ["--help"]
