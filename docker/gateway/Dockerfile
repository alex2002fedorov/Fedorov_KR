FROM python:3.9-slim

WORKDIR /app

COPY src/gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/gateway/ /app/
COPY src/manager/database.py /app/database.py

EXPOSE 5000

CMD ["python", "app.py"]