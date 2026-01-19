#!/usr/bin/env python3
import subprocess
import sys
import os
import time
from pathlib import Path


def init_database():
    """Инициализирует базу данных"""
    print("Инициализация базы данных...")
    db_path = Path("data/security.db")
    if not db_path.exists():
        subprocess.run([sys.executable, "scripts/init_database.py"],
                       check=True)
    else:
        print("База данных уже существует")


def start_services():
    """Запускает все микросервисы"""
    print("\n" + "=" * 60)
    print("ЗАПУСК СИСТЕМЫ БЕЗОПАСНОСТИ")
    print("=" * 60)

    # Создаем необходимые директории
    Path("data").mkdir(exist_ok=True)

    # Инициализируем БД
    init_database()

    print("\nЗапуск микросервисов:")
    print("\n1. Manager (порт 5002)...")
    manager_proc = subprocess.Popen([sys.executable, "src/manager/app.py"])
    time.sleep(2)

    print("2. Analyzer (порт 5001)...")
    analyzer_proc = subprocess.Popen([sys.executable, "src/analyzer/app.py"])
    time.sleep(2)

    print("3. Gateway (порт 5000)...")
    gateway_proc = subprocess.Popen([sys.executable, "src/gateway/app.py"])
    time.sleep(2)

    print("\n" + "=" * 60)
    print("СИСТЕМА БЕЗОПАСНОСТИ УСПЕШНО ЗАПУЩЕНА!")
    print("=" * 60)
    print("\nСервисы:")
    print("• Gateway:     http://localhost:5000")
    print("• Analyzer:    http://localhost:5001")
    print("• Manager:     http://localhost:5002")

    print("\nДля остановки нажмите Ctrl+C")


def run_tests():
    """Запускает тесты системы"""
    print("\n" + "=" * 60)
    print("ЗАПУСК ТЕСТОВ СИСТЕМЫ БЕЗОПАСНОСТИ")
    print("=" * 60)

    print("\nЗапуск тестов...")
    result = subprocess.run([sys.executable, "scripts/run_tests.py"],
                            capture_output=True,
                            text=True)

    print(result.stdout)
    if result.stderr:
        print("\nОшибки:")
        print(result.stderr)

    print(f"\nКод завершения тестов: {result.returncode}")


def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("СИСТЕМА БЕЗОПАСНОСТИ")
    print("=" * 60)

    print("\nВыберите действие:")
    print("1. Запустить все сервисы")
    print("2. Запустить тесты")
    print("3. Выход")

    try:
        choice = input("\nВаш выбор (1-3): ").strip()

        if choice == "1":
            start_services()
            # Ожидаем завершения (или Ctrl+C)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nОстановка системы...")
        elif choice == "2":
            run_tests()
        elif choice == "3":
            print("Выход...")
        else:
            print("Неверный выбор")

    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")


if __name__ == "__main__":
    main()
