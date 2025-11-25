#!/bin/bash

echo "Stopping old process"
pkill -f "python app/main.py" 2>/dev/null
while pgrep -f "python app/main.py" > /dev/null; do
    echo "Waiting for old process to stop..."
    sleep 1
done

echo "Initializing database"
rm -f data/chat.db
sqlite3 data/chat.db < data/chat.sql

echo "Starting backend"
python app/main.py