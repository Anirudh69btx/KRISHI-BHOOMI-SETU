# ============================================================
# FLIP v3.0 — Makefile Wrapper for Just
# ============================================================

.PHONY: all up down clean nuke test lint format typecheck build segment-00 help

all: up

up:
	just up

down:
	just down

clean:
	just clean

nuke:
	just nuke

test:
	just test

test-api:
	just test-api

test-web:
	just test-web

test-e2e:
	just test-e2e

migrate:
	just db-migrate

seed:
	just db-seed

lint:
	just lint

format:
	just format

typecheck:
	just typecheck

build:
	just build

segment-00:
	just segment-00

segment-01:
	@echo "Segment 01: IAM - Keycloak OIDC PKCE + SMS OTP SPI + JWT Validation"

help:
	just --list
