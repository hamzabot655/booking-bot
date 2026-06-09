FROM python:3.12

# Install Chromium browser + driver from Debian repos (handles all dependencies)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default port
ENV PORT=5000
ENV HOST=0.0.0.0

# Create a default config if none exists
RUN echo "name,email,password,exam_level,city,booking_datetime,passport,cnic,dob,phone,gender,nationality,address" > config.csv && \
    echo "Student1,email1@test.com,pass1,A1,Karachi,2026-07-03T11:24:00,AB123456,42101-1234567-8,15/08/2000,+923001234567,Male,Pakistani,Address1" >> config.csv

# Expose port
EXPOSE 5000

# Run the web app
CMD ["python", "webapp.py"]
