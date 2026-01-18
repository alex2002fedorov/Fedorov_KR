from flask import Flask, request, jsonify
import sqlite3
from database import SecurityDatabase
import logging
from prometheus_client import generate_latest, Counter, Histogram, Gauge
import time

app = Flask(__name__)
db = SecurityDatabase()

# Метрики Prometheus
REQUEST_COUNT = Counter('manager_requests_total', 'Total requests to manager')
REQUEST_LATENCY = Histogram('manager_request_latency_seconds',
                            'Request latency')
ACTIVE_REQUESTS = Gauge('manager_active_requests', 'Active requests')
INCIDENTS_COUNT = Counter('security_incidents_total',
                          'Total security incidents', ['severity'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.before_request
def before_request():
    request.start_time = time.time()
    ACTIVE_REQUESTS.inc()


@app.after_request
def after_request(response):
    ACTIVE_REQUESTS.dec()
    latency = time.time() - request.start_time
    REQUEST_LATENCY.observe(latency)
    REQUEST_COUNT.inc()
    return response


@app.route('/check-url', methods=['POST'])
def check_url():
    """Проверяет URL на разрешение"""
    data = request.json
    url = data.get('url', '')
    source_ip = request.remote_addr

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    is_allowed = db.is_url_allowed(url)

    if not is_allowed:
        db.log_incident(source_ip=source_ip,
                        destination_url=url,
                        action="BLOCKED",
                        description="Attempt to access blocked service",
                        severity="high")
        INCIDENTS_COUNT.labels(severity='high').inc()

    return jsonify({
        'url': url,
        'allowed': is_allowed,
        'timestamp': time.time()
    })


@app.route('/log-incident', methods=['POST'])
def log_incident():
    """Логирует инцидент безопасности"""
    data = request.json
    db.log_incident(source_ip=data.get('source_ip', request.remote_addr),
                    destination_url=data.get('destination_url', ''),
                    action=data.get('action', 'UNKNOWN'),
                    description=data.get('description', ''),
                    severity=data.get('severity', 'medium'))

    INCIDENTS_COUNT.labels(severity=data.get('severity', 'medium')).inc()
    return jsonify({'status': 'incident logged'})


@app.route('/incidents', methods=['GET'])
def get_incidents():
    """Получает последние инциденты"""
    limit = request.args.get('limit', 50, type=int)
    incidents = db.get_incidents(limit)

    # Форматируем результат
    result = []
    for inc in incidents:
        result.append({
            'id': inc[0],
            'timestamp': inc[1],
            'source_ip': inc[2],
            'destination_url': inc[3],
            'action': inc[4],
            'severity': inc[5],
            'description': inc[6]
        })

    return jsonify({'incidents': result})


@app.route('/metrics')
def metrics():
    """Endpoint для Prometheus"""
    return generate_latest()


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'manager'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
