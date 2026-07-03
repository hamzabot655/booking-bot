#!/bin/bash
echo "=== Goethe Booking Bot - Mac Install ==="
echo "Installing dependencies (one time only)..."
cd "$(dirname "$0")/.."
pip3 install -r requirements.txt
echo ""
echo "Done! You can now double-click 'mac_run.command' to book."
echo ""
read -p "Press Enter to exit..."
