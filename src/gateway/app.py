from flask import Flask, request, jsonify, Response
import requests
import json
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
import re

app = Flask(__name__)

# Конфигурация
ANALYZER_URL = "http://localhost:5001/analyze"
MANAGER_URL = "http://localhost:5002"

# Метрики Prometheus
REQUESTS_TOTAL = Counter('gateway_requests_total', 'Total requests',
                         ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('gateway_request_duration_seconds',
                             'Request duration')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_url_from_payload(payload):
    """Извлекает URL из различных форматов данных"""
    urls = []

    if isinstance(payload, dict):
        # Рекурсивно ищем URL в словаре
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                urls.extend(extract_url_from_payload(value))
            elif isinstance(value, str) and value.startswith(
                ('http://', 'https://')):
                urls.append(value)
    elif isinstance(payload, list):
        for item in payload:
            urls.extend(extract_url_from_payload(item))
    elif isinstance(payload, str):
        # Ищем URL в тексте
        url_pattern = r'https?://[^\s<>"\']+'
        urls.extend(re.findall(url_pattern, payload))

    return urls


@app.before_request
def before_request():
    request.start_time = time.time()


@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    REQUEST_DURATION.observe(duration)

    # Логируем метрику
    endpoint = request.path
    method = request.method
    status = response.status_code

    REQUESTS_TOTAL.labels(method=method, endpoint=endpoint,
                          status=status).inc()

    return response


@app.route('/proxy', methods=['POST'])
def proxy():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        target_url = data.get('target_url') or request.headers.get(
            'X-Target-Url')
        if not target_url:
            return jsonify({'error': 'target_url is required'}), 400

        try:
            check_response = requests.post(f"{MANAGER_URL}/check-url",
                                           json={'url': target_url},
                                           timeout=3)

            if check_response.status_code == 200:
                check_data = check_response.json()

                if not check_data.get('allowed', False):
                    return jsonify({
                        'error': 'Access denied by security policy',
                        'url': target_url,
                        'blocked': True
                    }), 403

                return jsonify({
                    'success': True,
                    'url': target_url,
                    'message': 'Access would be allowed (demo mode)'
                })
            else:
                return jsonify({
                    'error': f'Manager error: {check_response.status_code}',
                    'url': target_url
                }), 500

        except requests.exceptions.RequestException as e:
            return jsonify({
                'error': f'Cannot connect to security services: {e}',
                'url': target_url
            }), 503

    except Exception as e:
        logger.error(f"Gateway error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/check', methods=['POST'])
def check():
    data = request.json
    url = data.get('url', '')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        response = requests.post(f"{MANAGER_URL}/check-url",
                                 json={'url': url},
                                 timeout=5)

        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({
                'error': f'Manager returned {response.status_code}',
                'status': 'error'
            }), 500

    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/metrics')
def metrics():
    """Endpoint для Prometheus"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/health')
def health():
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'gateway',
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'service': 'gateway'
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,
            debug=False)
