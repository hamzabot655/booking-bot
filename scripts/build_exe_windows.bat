@echo off
cd /d "%~dp0.."
echo Building goethe-booker.exe...

pyinstaller --onefile --name goethe-booker ^
  --paths . ^
  --hidden-import curl_cffi ^
  --hidden-import undetected_chromedriver ^
  --hidden-import plyer ^
  --hidden-import bcrypt ^
  --hidden-import cryptography ^
  --hidden-import sqlalchemy ^
  --hidden-import gspread ^
  --hidden-import pydantic ^
  --hidden-import bs4 ^
  scripts\book_one.py

echo.
echo Build complete!
echo File: dist\goethe-booker.exe
pause
