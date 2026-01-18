#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов системы безопасности
"""
import sys
import os
import json
import time
import subprocess
import requests
import unittest
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

def wait_for_service(url, timeout=30, interval=1):
    """Ожидает доступности сервиса"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(interval)
    return False

class TestSecuritySystem(unittest.TestCase):
    """Тесты системы безопасности"""

    @classmethod
    def setUpClass(cls):
        """Настройка тестовой среды"""
        print("\n" + "="*60)
        print("НАСТРОЙКА ТЕСТОВОЙ СРЕДЫ")
        print("="*60)

        # Ждем запуска сервисов
        print("\nОжидание запуска сервисов...")
        services = [
            ("Gateway", "http://localhost:5000/health"),
            ("Analyzer", "http://localhost:5001/health"),
            ("Manager", "http://localhost:5002/health")
        ]

        for name, url in services:
            if wait_for_service(url):
                print(f"✓ {name} запущен")
            else:
                print(f"✗ {name} не запущен")
                # Попробуем запустить локально
                print(f"Попытка запустить {name} локально...")

    def test_1_manager_health(self):
        """Тест здоровья менеджера"""
        print("\n[Тест 1] Проверка здоровья Manager...")
        response = requests.get("http://localhost:5002/health", timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        print(f"  ✓ Manager status: {data['status']}")

    def test_2_url_checking(self):
        """Тест проверки URL"""
        print("\n[Тест 2] Проверка системы контроля URL...")

        # Тестовые URL (из базы данных)
        test_cases = [
            ("https://github.com/test/Test_KR", False, "Запрещенный GitHub репозиторий"),
            ("https://github.com/test/Test_KR_2", True, "Разрешенный GitHub репозиторий"),
            ("https://api.twitter.com/v2/tweets", False, "Twitter API"),
            ("https://api.trusted-service.com/v1/data", True, "Доверенный сервис"),
            ("https://vk.com/api/messages", False, "VK API"),
            ("https://internal-api.local/users", True, "Внутренний API"),
        ]

        for url, expected_allowed, description in test_cases:
            response = requests.post(
                "http://localhost:5002/check-url",
                json={"url": url},
                timeout=5
            )

            data = response.json()
            actual_allowed = data['allowed']
            status = "✓" if actual_allowed == expected_allowed else "✗"

            print(f"  {status} {description}")
            print(f"    URL: {url}")
            print(f"    Ожидалось: {'Разрешено' if expected_allowed else 'Запрещено'}")
            print(f"    Получено: {'Разрешено' if actual_allowed else 'Запрещено'}")

            self.assertEqual(actual_allowed, expected_allowed, 
                           f"Ошибка проверки URL: {url}")

    def test_3_gateway_blocking(self):
        """Тест блокировки запросов через шлюз"""
        print("\n[Тест 3] Проверка блокировки запросов через Gateway...")

        # Запрещенный URL (должен быть заблокирован)
        headers = {"X-Target-Url": "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage"}

        response = requests.post(
            "http://localhost:5000/proxy",
            headers=headers,
            json={"chat_id": "12345", "text": "Test message"},
            timeout=10
        )

        # Должен вернуть 403 (Forbidden)
        self.assertEqual(response.status_code, 403)
        print(f"  ✓ Запрос к запрещенному сервису заблокирован (HTTP {response.status_code})")

        # Проверяем сообщение об ошибке
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Request blocked by security policy')
        print(f"  ✓ Получено корректное сообщение об ошибке")

    def test_4_metrics_collection(self):
        """Тест сбора метрик"""
        print("\n[Тест 4] Проверка сбора метрик...")

        services = [
            ("Gateway", "http://localhost:5000/metrics"),
            ("Analyzer", "http://localhost:5001/metrics"),
            ("Manager", "http://localhost:5002/metrics"),
        ]

        for name, url in services:
            response = requests.get(url, timeout=5)
            self.assertEqual(response.status_code, 200)

            # Проверяем, что метрики содержат нужные данные
            content = response.text
            self.assertIn('# TYPE', content)
            print(f"  ✓ {name} метрики доступны")

    def test_5_incident_logging(self):
        """Тест логирования инцидентов"""
        print("\n[Тест 5] Проверка логирования инцидентов...")

        # Сначала получаем текущие инциденты
        response = requests.get("http://localhost:5002/incidents?limit=1", timeout=5)
        initial_count = len(response.json()['incidents']) if response.status_code == 200 else 0

        # Создаем тестовый инцидент
        incident_data = {
            "source_ip": "192.168.1.100",
            "destination_url": "https://malicious-site.com/exploit",
            "action": "BLOCKED",
            "description": "Тестовый инцидент безопасности",
            "severity": "high"
        }

        response = requests.post(
            "http://localhost:5002/log-incident",
            json=incident_data,
            timeout=5
        )

        self.assertEqual(response.status_code, 200)
        print(f"  ✓ Инцидент успешно залогирован")

        # Проверяем, что инцидент добавился
        response = requests.get("http://localhost:5002/incidents?limit=10", timeout=5)
        data = response.json()

        self.assertGreater(len(data['incidents']), initial_count)
        print(f"  ✓ В базе данных теперь {len(data['incidents'])} инцидентов")

        # Проверяем данные последнего инцидента
        last_incident = data['incidents'][0]
        self.assertEqual(last_incident['source_ip'], incident_data['source_ip'])
        self.assertEqual(last_incident['destination_url'], incident_data['destination_url'])
        self.assertEqual(last_incident['action'], incident_data['action'])
        print(f"  ✓ Данные инцидента корректны")

    def test_6_analyzer_functionality(self):
        """Тест функциональности анализатора"""
        print("\n[Тест 6] Проверка работы Analyzer...")

        # Отправляем запрос на анализ
        test_data = {
            "target_url": "https://github.com/test/Test_KR",
            "urls_in_payload": [
                "https://cloudstorage.com/files/secret.txt",
                "https://api.trusted-service.com/v1/auth"
            ],
            "source_ip": "10.0.0.1",
            "method": "POST"
        }

        response = requests.post(
            "http://localhost:5001/analyze",
            json=test_data,
            timeout=10
        )

        self.assertEqual(response.status_code, 403)  # Должен быть заблокирован
        data = response.json()

        print(f"  ✓ Analyzer вернул результат анализа")
        print(f"    Статус: {'Разрешено' if data['allowed'] else 'Заблокировано'}")
        print(f"    Заблокированные URL: {len(data['blocked_urls'])}")
        print(f"    Разрешенные URL: {len(data['allowed_urls'])}")

        # Проверяем, что наш запрещенный URL в списке заблокированных
        self.assertIn("https://github.com/test/Test_KR", data['blocked_urls'])
        self.assertIn("https://cloudstorage.com/files/secret.txt", data['blocked_urls'])
        self.assertIn("https://api.trusted-service.com/v1/auth", data['allowed_urls'])

    def test_7_wildcard_patterns(self):
        """Тест wildcard-паттернов в правилах"""
        print("\n[Тест 7] Проверка wildcard-паттернов...")

        # Добавляем wildcard правило
        response = requests.post(
            "http://localhost:5002/check-url",
            json={"url": "https://any-subdomain.cloudstorage.com/file.txt"},
            timeout=5
        )

        data = response.json()
        # Должен быть заблокирован по правилу https://*.cloudstorage.com/
        self.assertFalse(data['allowed'])
        print(f"  ✓ Wildcard паттерн работает: *.cloudstorage.com")

    def test_8_performance(self):
        """Тест производительности"""
        print("\n[Тест 8] Проверка производительности...")

        test_urls = [
            "https://github.com/test/Test_KR_2",
            "https://api.trusted-service.com/v1/data",
            "https://internal-api.local/users"
        ]

        times = []
        for url in test_urls:
            start_time = time.time()
            response = requests.post(
                "http://localhost:5002/check-url",
                json={"url": url},
                timeout=5
            )
            end_time = time.time()
            times.append(end_time - start_time)

            self.assertEqual(response.status_code, 200)

        avg_time = sum(times) / len(times)
        print(f"  ✓ Среднее время проверки URL: {avg_time:.3f} секунд")
        self.assertLess(avg_time, 0.5, "Время проверки слишком велико")

def run_integration_tests():
    """Запуск интеграционных тестов"""
    print("\n" + "="*60)
    print("ЗАПУСК ИНТЕГРАЦИОННЫХ ТЕСТОВ")
    print("="*60)

    # Проверяем, запущены ли сервисы
    try:
        # Запускаем юнит-тесты
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestSecuritySystem)

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        # Выводим итоговую статистику
        print("\n" + "="*60)
        print("ИТОГОВАЯ СТАТИСТИКА ТЕСТОВ")
        print("="*60)
        print(f"Всего тестов: {result.testsRun}")
        print(f"Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"Провалено: {len(result.failures)}")
        print(f"Ошибок: {len(result.errors)}")

        if result.failures:
            print("\nПроваленные тесты:")
            for test, traceback in result.failures:
                print(f"  - {test}")

        if result.errors:
            print("\nТесты с ошибками:")
            for test, traceback in result.errors:
                print(f"  - {test}")

        return result.wasSuccessful()

    except Exception as e:
        print(f"\nОшибка при запуске тестов: {e}")
        return False

def run_unit_tests():
    """Запуск модульных тестов"""
    print("\n" + "="*60)
    print("ЗАПУСК МОДУЛЬНЫХ ТЕСТОВ")
    print("="*60)

    # Создаем тестовую базу данных
    test_db_path = "data/test_security.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # Импортируем и запускаем модульные тесты
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

    # Запускаем тесты через unittest discover
    result = subprocess.run([
        sys.executable, "-m", "unittest", "discover",
        "-s", "tests",
        "-p", "test_*.py",
        "-v"
    ])

    return result.returncode == 0

def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ БЕЗОПАСНОСТИ")
    print("="*60)

    # Создаем необходимые директории
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Проверяем наличие зависимостей
    try:
        import requests
        import unittest
    except ImportError as e:
        print(f"Ошибка: отсутствуют зависимости: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return 1

    # Запускаем тесты
    print("\n1. Запуск модульных тестов...")
    unit_success = run_unit_tests()

    print("\n2. Запуск интеграционных тестов...")
    integration_success = run_integration_tests()

    # Итоговый результат
    print("\n" + "="*60)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("="*60)

    if unit_success and integration_success:
        print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        print("✗ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        if not unit_success:
            print("  - Модульные тесты провалены")
        if not integration_success:
            print("  - Интеграционные тесты провалены")
        return 1

if __name__ == "__main__":
    sys.exit(main())