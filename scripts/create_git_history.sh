#!/usr/bin/env bash
set -euo pipefail

git add config sql retail_forecast scripts tests
git commit -m "Build retail forecasting pipeline"
git add dashboard docs README.md Makefile docker-compose.yml Dockerfile requirements.txt pyproject.toml
git commit -m "Add dashboard documentation and automation"
git add artifacts data/processed models || true
git commit -m "Record local demo artifacts" || true
