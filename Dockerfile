FROM python:3.13-slim

RUN useradd --create-home --uid 1001 app

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

# Create output dir and hand it to the non-root user before switching
RUN mkdir /reports && chown app:app /reports

# CT_OUTPUT tells the CLI where to write reports; mount /reports to retrieve them.
# Other env vars (CT_REGION, CT_DAYS, CT_FORMAT, CT_NO_CACHE, etc.) override CLI defaults.
ENV CT_OUTPUT=/reports

USER app

VOLUME ["/reports"]

# Verifies the binary and package are intact; not a liveness check for a server.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=1 \
    CMD ct-report --help > /dev/null

ENTRYPOINT ["ct-report"]
CMD ["run"]
