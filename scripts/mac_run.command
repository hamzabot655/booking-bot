#!/bin/bash
echo "=== Goethe Booking Bot ==="
cd "$(dirname "$0")/.."
python3 scripts/book_one.py
read -p "Press Enter to exit..."
