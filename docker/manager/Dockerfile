FROM python:3.9-slim

WORKDIR /app

COPY src/manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/manager/ /app/

EXPOSE 5002

CMD ["python", "app.py"]