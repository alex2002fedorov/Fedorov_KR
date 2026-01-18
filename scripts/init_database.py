#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src/manager'))

from database import SecurityDatabase

if __name__ == '__main__':
    db = SecurityDatabase()
    print("Database initialized successfully!")

    # Тестируем
    test_urls = [
        "https://github.com/test/Test_KR",
        "https://github.com/test/Test_KR_2",
        "https://api.twitter.com/v2/tweets",
        "https://api.trusted-service.com/v1/data"
    ]

    print("\nTesting URL checks:")
    for url in test_urls:
        allowed = db.is_url_allowed(url)
        status = "ALLOWED" if allowed else "BLOCKED"
        print(f"{url}: {status}")