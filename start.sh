#!/bin/sh

echo "Waiting for DB to be ready..."
sleep 3

echo "Starting Uvicorn..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

sleep 2

echo "Running tests..."
pytest | tee test_output.log

wait $UVICORN_PID