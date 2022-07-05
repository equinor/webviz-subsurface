######################
# Installation image #
######################

FROM python:3.6-slim AS builder

# Install git and ssh, in order to install Python
# packages not available from PyPI.
RUN apt-get update && \
    apt-get install -y git 

# Changing to non-root user early
RUN useradd --create-home appuser
WORKDIR /home/appuser
USER appuser

# Set environment variables
ENV PATH="${PATH}:/home/appuser/.local/bin"

# Install relevant Python packages
COPY --chown=appuser requirements.txt requirements.txt
RUN pip install -r requirements.txt

###############
# Final image #
###############

FROM python:3.6-slim

# Changing to non-root user early
RUN useradd --create-home --uid 1234 appuser
USER 1234
WORKDIR /home/appuser

# Set environment variables
ENV PATH="${PATH}:/home/appuser/.local/bin" \
    PYTHONFAULTHANDLER=1

# Copy over appuser installed Python packages
COPY --chown=appuser --from=builder /home/appuser/.local /home/appuser/.local

# Copy over the created Webviz application
COPY --chown=appuser . dash_app

EXPOSE 5000

# Define startup command of container image
CMD gunicorn \
        --access-logfile "-" \
        --bind 0.0.0.0:5000 \
        --keep-alive 120 \
        --max-requests 40 \
        --preload \
        --workers 2 \
        --worker-class gthread \
        --worker-tmp-dir /dev/shm \
        --threads 2 \
        --timeout 100000 \
        "dash_app.webviz_app:server"