#!/bin/bash

echo "🚀 Starting LC-Scanner Server..."
echo "================================="

# Check if PostgreSQL is running
if ! nc -z localhost 5432; then
    echo "❌ PostgreSQL is not running!"
    echo "   Start with: docker compose up -d postgres"
    exit 1
fi

# Navigate to API directory and start server
cd api
echo "✅ Starting FastAPI server on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload