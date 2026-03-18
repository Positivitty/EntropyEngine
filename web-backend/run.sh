#!/bin/bash
cd "$(dirname "$0")/.."
PYTHONPATH=. uvicorn web-backend.app:app --reload --port 8000
