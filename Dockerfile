# Multi-stage build pour optimiser la taille de l'image
FROM python:3.11-slim as builder

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installation des dépendances système pour la compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt pyproject.toml setup.py ./

# Installation des dépendances Python
RUN pip install --user -r requirements.txt

# Stage de production
FROM python:3.11-slim as production

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

# Installation des dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Création d'un utilisateur non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash phonecheck

# Copie des dépendances depuis le stage builder
COPY --from=builder /root/.local /root/.local

# Création du répertoire de travail
WORKDIR /app

# Copie du code source
COPY . .

# Installation du package en mode développement
RUN pip install --user -e .

# Création des répertoires nécessaires
RUN mkdir -p /app/.cache /app/logs && \
    chown -R phonecheck:phonecheck /app

# Changement vers l'utilisateur non-root
USER phonecheck

# Configuration par défaut
ENV PHONE_CHECKER_CACHE_DIR=/app/.cache \
    PHONE_CHECKER_LOG_FILE=/app/logs/phone_checker.log

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m phone_checker stats > /dev/null || exit 1

# Point d'entrée
ENTRYPOINT ["python", "-m", "phone_checker"]

# Commande par défaut (affiche l'aide)
CMD ["--help"]

# Labels pour les métadonnées
LABEL maintainer="nabz0r@gmail.com" \
      version="0.1.0" \
      description="Modern Phone Checker - Vérification éthique de numéros de téléphone" \
      org.opencontainers.image.source="https://github.com/nabz0r/modern-phone-checker"

# Exposition du port pour une éventuelle API web
EXPOSE 8000

# Volume pour persister le cache et les logs
VOLUME ["/app/.cache", "/app/logs"]
