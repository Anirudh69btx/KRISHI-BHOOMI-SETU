# Base Rasa image
FROM rasa/rasa:3.6.20 AS base

WORKDIR /app

# Actions stage
FROM rasa/rasa-sdk:3.6.2 AS actions
WORKDIR /app
COPY actions/ /app/actions/
EXPOSE 5055
CMD ["start", "--actions", "actions"]

# Core Rasa development stage
FROM base AS development
USER root
WORKDIR /app
COPY config.yml endpoints.yml domain.yml ./
COPY data/ ./data/
USER 1001
EXPOSE 5005
CMD ["run", "--enable-api", "--cors", "*", "--debug"]
