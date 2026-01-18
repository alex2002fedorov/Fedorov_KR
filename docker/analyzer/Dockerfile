FROM python:3.9-slim

WORKDIR /app

COPY src/analyzer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/analyzer/ /app/

EXPOSE 5001

CMD ["python", "app.py"]