FROM python:3.12

# Install Google Chrome (full image has all dependencies)
RUN apt-get update && apt-get install -y wget gnupg && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/chrome-key.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/chrome-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
ENV HOST=0.0.0.0

RUN echo "name,email,password,exam_level,city,booking_datetime,passport,cnic,dob,phone,gender,nationality,address" > config.csv && \
    echo "Student1,email1@test.com,pass1,A1,Karachi,2026-07-03T11:24:00,AB123456,42101-1234567-8,15/08/2000,+923001234567,Male,Pakistani,Address1" >> config.csv

EXPOSE 5000

CMD ["python", "webapp.py"]
