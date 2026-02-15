#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple API test script."""

import urllib.request
import json


def test_health() -> bool:
    """Test the health check endpoint."""
    try:
        url = "http://localhost:8002/api/health"
        with urllib.request.urlopen(url, timeout=10) as f:
            data = f.read().decode("utf-8")
            result = json.loads(data)

        if result.get("status") == "ok":
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {result}")
            return False

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_fetch_list() -> bool:
    """Test fetch article list endpoint."""
    try:
        url = "http://localhost:8002/api/articles/fetch-list"
        payload = json.dumps({"name": "人民日报"}).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            data = f.read().decode("utf-8")
            result = json.loads(data)

        if result.get("code") == 0:
            print("✅ Fetch list passed")
            data = result.get("data")
            if data:
                print(f"   Found {data['article_count']} articles")
                for idx, article in enumerate(data["articles"], 1):
                    print(f"   {idx}. {article['title']}")
            return True
        else:
            print(f"❌ Fetch list failed: {result.get('msg')}")
            return False

    except Exception as e:
        print(f"❌ Fetch list failed: {e}")
        return False


def main():
    """Main test function."""
    print("Testing API endpoints...")

    print("\n1. Health check:")
    health_ok = test_health()

    print("\n2. Fetch article list:")
    fetch_ok = test_fetch_list()

    print("\nSummary:")
    if health_ok and fetch_ok:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    import sys
    sys.exit(0 if success else 1)
