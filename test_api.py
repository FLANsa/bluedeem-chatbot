#!/usr/bin/env python3
"""Script to test the BlueDeem Chatbot API."""
import requests
import json
import sys

# API Base URL
BASE_URL = "https://bluedeem-chatbot.onrender.com"

def test_health():
    """Test health endpoint."""
    print("🔍 Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        response.raise_for_status()
        print(f"✅ Health Check: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health Check failed: {e}")
        return False

def test_data_health():
    """Test data health endpoint."""
    print("\n🔍 Testing Data Health...")
    try:
        response = requests.get(f"{BASE_URL}/health/data", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Data Health: {data}")
        return True
    except Exception as e:
        print(f"❌ Data Health failed: {e}")
        return False

def test_chat_api(message="اهلا"):
    """Test chat API endpoint."""
    print(f"\n🔍 Testing Chat API with message: '{message}'...")
    try:
        data = {
            "user_id": "test_user",
            "platform": "web",
            "message": message
        }
        response = requests.post(
            f"{BASE_URL}/chat/api/chat",
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Chat API Response: {result.get('response', 'No response')}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Chat API HTTP Error: {e}")
        if e.response.status_code == 500:
            try:
                error_detail = e.response.json()
                print(f"   Error Detail: {error_detail}")
            except:
                print(f"   Response Text: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Chat API failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 BlueDeem Chatbot API Test")
    print("=" * 70)
    
    results = []
    
    # Test 1: Health Check
    results.append(("Health Check", test_health()))
    
    # Test 2: Data Health
    results.append(("Data Health", test_data_health()))
    
    # Test 3: Chat API - Greeting
    results.append(("Chat API (Greeting)", test_chat_api("اهلا")))
    
    # Test 4: Chat API - Doctors
    results.append(("Chat API (Doctors)", test_chat_api("مين الاطباء")))
    
    # Test 5: Chat API - Branches
    results.append(("Chat API (Branches)", test_chat_api("وين فروعكم")))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

