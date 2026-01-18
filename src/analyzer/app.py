from flask import Flask, request, jsonify, Response
import requests
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from urllib.parse import urlparse

app = Flask(__name__)

# Конфигурация
MANAGER_URL = "http://localhost:5002"

# Метрики Prometheus
ANALYSIS_REQUESTS = Counter('analyzer_requests_total',
                            'Total analysis requests')
BLOCKED_ANALYSIS = Counter('analyzer_blocked_total',
                           'Blocked requests analysis')
ANALYSIS_DURATION = Histogram('analyzer_duration_seconds', 'Analysis duration')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_domain_from_url(url):
    """Извлекает домен из URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return url


@app.route('/analyze', methods=['POST'])
def analyze():
    """Анализирует запрос на безопасность"""
    start_time = time.time()

    data = request.json
    target_url = data.get('target_url', '')
    urls_in_payload = data.get('urls_in_payload', [])
    source_ip = data.get('source_ip', '')

    # Собираем все URL для проверки
    all_urls = [target_url] + urls_in_payload

    blocked_urls = []
    allowed_urls = []

    # Проверяем каждый URL через менеджер
    for url in all_urls:
        if not url:
            continue

        try:
            # Отправляем запрос в менеджер для проверки
            response = requests.post(f"{MANAGER_URL}/check-url",
                                     json={'url': url},
                                     timeout=3)

            if response.status_code == 200:
                result = response.json()
                if not result['allowed']:
                    blocked_urls.append(url)
                else:
                    allowed_urls.append(url)
            else:
                logger.error(f"Manager error: {response.status_code}")
                # При ошибке считаем URL запрещенным (fail-safe)
                blocked_urls.append(url)

        except requests.exceptions.RequestException as e:
            logger.error(f"Connection to manager failed: {e}")
            blocked_urls.append(url)

    # Определяем результат анализа
    is_allowed = len(blocked_urls) == 0

    # Логируем инцидент, если есть блокировки
    if not is_allowed and blocked_urls:
        try:
            requests.post(f"{MANAGER_URL}/log-incident",
                          json={
                              'source_ip': source_ip,
                              'destination_url': target_url,
                              'action': 'BLOCKED',
                              'description':
                              f'Blocked URLs: {", ".join(blocked_urls[:3])}',
                              'severity': 'high'
                          },
                          timeout=2)
        except:
            pass  # Не прерываем выполнение при ошибке логирования

    ANALYSIS_REQUESTS.inc()
    if not is_allowed:
        BLOCKED_ANALYSIS.inc()

    duration = time.time() - start_time
    ANALYSIS_DURATION.observe(duration)

    return jsonify({
        'allowed': is_allowed,
        'blocked_urls': blocked_urls,
        'allowed_urls': allowed_urls,
        'analysis_time': duration,
        'source_ip': source_ip
    }), 200 if is_allowed else 403


@app.route('/metrics')
def metrics():
    """Endpoint для Prometheus"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/health')
def health():
    #"""Health check endpoint"""
    #try:
    #    # Проверяем доступность менеджера
    #    response = requests.get(f"{MANAGER_URL}/health", timeout=2)
    #    manager_status = response.status_code == 200
    #
    #    return jsonify({
    #        'status': 'healthy' if manager_status else 'degraded',
    #        'manager': 'up' if manager_status else 'down'
    #    })
    #except:
    #    return jsonify({'status': 'unhealthy'}), 500

    #"""Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'manager'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
