#!/usr/bin/env python3
"""
Простой нагрузочный тест для текущей системы безопасности
"""
import sys
import requests
import time
import statistics


def test_direct_manager():
    """Тест прямых запросов к Manager"""
    print("\n" + "=" * 60)
    print("ПРЯМОЙ ТЕСТ MANAGER API")
    print("=" * 60)

    # Тестовые данные
    test_cases = [
        ("https://github.com/test/Test_KR", False, "Запрещенный GitHub"),
        ("https://github.com/test/Test_KR_2", True, "Разрешенный GitHub"),
        ("https://api.twitter.com/v2/tweets", False, "Twitter API"),
        ("https://api.trusted-service.com/v1/data", True, "Доверенный сервис"),
        ("https://api.telegram.org/bot123/send", False, "Telegram API"),
        ("https://internal-api.local/users", True, "Внутренний API"),
    ]

    print("\nПроверка отдельных URL:")
    results = []

    for url, expected_allowed, description in test_cases:
        try:
            start_time = time.time()
            response = requests.post("http://localhost:5002/check-url",
                                     json={"url": url},
                                     timeout=5)
            end_time = time.time()
            duration = end_time - start_time

            if response.status_code == 200:
                data = response.json()
                actual_allowed = data.get('allowed', False)
                is_correct = (actual_allowed == expected_allowed)

                status = "✓" if is_correct else "✗"
                result_text = "РАЗРЕШЕНО" if actual_allowed else "ЗАБЛОКИРОВАНО"

                print(f"  {status} {description}")
                print(f"    URL: {url[:50]}...")
                print(f"    Статус: {result_text}")
                print(f"    Время: {duration:.3f} сек")

                results.append({
                    'url': url,
                    'success': True,
                    'correct': is_correct,
                    'duration': duration,
                    'allowed': actual_allowed
                })
            else:
                print(f"  ✗ {description}")
                print(f"    Ошибка: HTTP {response.status_code}")
                results.append({
                    'url': url,
                    'success': False,
                    'error_code': response.status_code,
                    'duration': duration
                })

        except Exception as e:
            print(f"  ✗ {description}")
            print(f"    Исключение: {str(e)[:50]}")
            results.append({'url': url, 'success': False, 'error': str(e)})

    return results


def run_load_test(num_requests=50):
    """Запускает нагрузочный тест"""
    print("\n" + "=" * 60)
    print(f"НАГРУЗОЧНЫЙ ТЕСТ ({num_requests} запросов)")
    print("=" * 60)

    # Список тестовых URL (со смешанными разрешенными/запрещенными)
    test_urls = [
        "https://github.com/test/Test_KR",
        "https://github.com/test/Test_KR_2",
        "https://api.trusted-service.com/v1/data",
        "https://api.twitter.com/v2/tweets",
        "https://internal-api.local/users",
        "https://api.telegram.org/bot123/send",
    ]

    print(f"\nОтправка {num_requests} запросов к Manager API...")

    all_results = []
    start_total = time.time()

    for i in range(num_requests):
        # Выбираем случайный URL
        import random
        url = random.choice(test_urls)

        try:
            # Измеряем время выполнения
            start = time.time()
            response = requests.post("http://localhost:5002/check-url",
                                     json={"url": url},
                                     timeout=3)
            end = time.time()
            duration = end - start

            # Анализируем результат
            if response.status_code == 200:
                data = response.json()
                success = True
                allowed = data.get('allowed', False)
            else:
                success = False
                allowed = False

            result = {
                'index': i + 1,
                'url': url,
                'success': success,
                'status_code': response.status_code,
                'duration': duration,
                'allowed': allowed,
                'timestamp': time.time()
            }

            all_results.append(result)

            # Прогресс каждые 10 запросов
            if (i + 1) % 10 == 0:
                print(f"  Отправлено: {i + 1}/{num_requests}")

        except Exception as e:
            result = {
                'index': i + 1,
                'url': url,
                'success': False,
                'error': str(e),
                'duration': 3,
                'timestamp': time.time()
            }
            all_results.append(result)

    end_total = time.time()
    total_time = end_total - start_total

    return all_results, total_time


def analyze_results(results, total_time):
    """Анализирует результаты тестирования"""
    print("\n" + "=" * 60)
    print("АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 60)

    if not results:
        print("Нет результатов для анализа")
        return

    # Основная статистика
    total = len(results)
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    blocked = [
        r for r in results
        if r.get('success', False) and not r.get('allowed', True)
    ]
    allowed = [
        r for r in results
        if r.get('success', False) and r.get('allowed', False)
    ]

    # Статистика по кодам ответа
    status_codes = {}
    for r in results:
        code = r.get('status_code', 'error')
        status_codes[code] = status_codes.get(code, 0) + 1

    # Время выполнения
    durations = [r['duration'] for r in results if 'duration' in r]

    print(f"\n📊 Общая статистика:")
    print(f"  • Всего запросов: {total}")
    print(
        f"  • Успешных: {len(successful)} ({len(successful)/total*100:.1f}%)")
    print(f"  • Неуспешных: {len(failed)} ({len(failed)/total*100:.1f}%)")
    print(f"  • Общее время: {total_time:.2f} сек")
    print(f"  • RPS: {total/total_time:.2f} запр/сек")

    print(f"\n🛡️  Статистика безопасности:")
    print(f"  • Разрешено: {len(allowed)}")
    print(f"  • Заблокировано: {len(blocked)}")
    if len(successful) > 0:
        print(
            f"  • Процент блокировки: {len(blocked)/len(successful)*100:.1f}%")

    print(f"\n📈 Статистика времени ответа:")
    if durations:
        print(f"  • Минимальное: {min(durations):.3f} сек")
        print(f"  • Максимальное: {max(durations):.3f} сек")
        print(f"  • Среднее: {statistics.mean(durations):.3f} сек")
        print(f"  • Медиана: {statistics.median(durations):.3f} сек")

        # Процентили
        sorted_durations = sorted(durations)
        percentiles = [50, 75, 90, 95, 99]
        print(f"  • Процентили:")
        for p in percentiles:
            idx = int(p / 100 * len(sorted_durations))
            if idx < len(sorted_durations):
                print(f"    - {p}% быстрее: {sorted_durations[idx]:.3f} сек")

    print(f"\n🔧 Коды ответа:")
    for code, count in sorted(status_codes.items(),
                              key=lambda x: x[1],
                              reverse=True):
        percentage = count / total * 100
        print(f"  • {code}: {count} ({percentage:.1f}%)")

    # Рекомендации
    print(f"\n💡 Рекомендации:")

    error_rate = len(failed) / total * 100
    if error_rate > 10:
        print(f"  ⚠️  Высокий процент ошибок ({error_rate:.1f}%)")
        print(f"    Проверьте: 1) Запущены ли сервисы? 2) Доступна ли БД?")

    if durations:
        avg_duration = statistics.mean(durations)
        if avg_duration > 1.0:
            print(f"  ⚠️  Высокое время ответа ({avg_duration:.3f} сек)")
            print(f"    Возможны проблемы с производительностью")

    if len(successful) == total:
        print(f"  ✅ Все запросы успешны!")

    # Проверка работы безопасности
    test_urls = [
        ("https://github.com/test/Test_KR", False),
        ("https://github.com/test/Test_KR_2", True),
    ]

    print(f"\n🧪 Проверка корректности блокировки:")
    for url, should_be_allowed in test_urls:
        for result in results[:20]:  # Проверяем первые 20 результатов
            if result.get('url') == url:
                actual = result.get('allowed', False)
                if actual == should_be_allowed:
                    status = "✓"
                else:
                    status = "✗"
                print(
                    f"  {status} {url[:30]}...: ожидалось {'РАЗРЕШЕНО' if should_be_allowed else 'ЗАБЛОКИРОВАНО'}, получено {'РАЗРЕШЕНО' if actual else 'ЗАБЛОКИРОВАНО'}"
                )
                break


def check_services():
    """Проверяет доступность сервисов"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ДОСТУПНОСТИ СЕРВИСОВ")
    print("=" * 60)

    services = [
        ("Manager", "http://localhost:5002/health", "POST /check-url"),
        ("Analyzer", "http://localhost:5001/health", "POST /analyze"),
        ("Gateway", "http://localhost:5000/health", "POST /proxy"),
    ]

    all_healthy = True

    for name, health_url, api_desc in services:
        try:
            response = requests.get(health_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                if status == 'healthy':
                    print(f"  ✅ {name}: ЗДОРОВ ({health_url})")
                else:
                    print(f"  ⚠️  {name}: {status.upper()}")
                    all_healthy = False
            else:
                print(f"  ❌ {name}: HTTP {response.status_code}")
                all_healthy = False
        except requests.exceptions.ConnectionError:
            print(f"  ❌ {name}: НЕДОСТУПЕН")
            all_healthy = False
        except Exception as e:
            print(f"  ❌ {name}: ОШИБКА - {str(e)[:50]}")
            all_healthy = False

    return all_healthy


def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ БЕЗОПАСНОСТИ")
    print("=" * 60)

    # Проверяем доступность сервисов
    if not check_services():
        print("\n⚠️  ВНИМАНИЕ: Некоторые сервисы недоступны!")
        print(
            "Сначала запустите сервисы через: python main.py (выберите опцию 1)"
        )
        print("Затем в новом окне терминала запустите этот тест.")
        return 1

    print("\n" + "=" * 60)
    print("МЕНЮ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print("1. Быстрая проверка API Manager")
    print("2. Нагрузочный тест (50 запросов)")
    print("3. Расширенный нагрузочный тест (200 запросов)")
    print("4. Выход")

    try:
        choice = input("\nВыберите тест (1-4): ").strip()

        if choice == "1":
            print("\nЗапуск быстрой проверки...")
            results = test_direct_manager()

        elif choice == "2":
            print("\nЗапуск нагрузочного теста...")
            results, total_time = run_load_test(50)
            analyze_results(results, total_time)

        elif choice == "3":
            print("\nЗапуск расширенного нагрузочного теста...")
            results, total_time = run_load_test(200)
            analyze_results(results, total_time)

        elif choice == "4":
            print("Выход...")
            return 0

        else:
            print("Неверный выбор")
            return 1

    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
        return 1
    except Exception as e:
        print(f"\nОшибка: {e}")
        return 1

    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
