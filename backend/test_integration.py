"""
Quick integration test script for TalkSense AI backend.
Tests health endpoint and basic analysis flow.
"""

import os

import requests

BASE_URL = "http://localhost:8000"
SAMPLE_AUDIO_DIR = "../sample_audio"


def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    print(f"✅ Health check passed: {data}")


def test_analyze_meeting():
    """Test analyze endpoint with meeting mode"""
    print("\nTesting /analyze with meeting_short.mp3...")

    audio_file = os.path.join(SAMPLE_AUDIO_DIR, "meeting_short.mp3")
    if not os.path.exists(audio_file):
        print(f"❌ Sample file not found: {audio_file}")
        assert False, f"Sample file not found: {audio_file}"

    with open(audio_file, "rb") as f:
        files = {"file": ("meeting_short.mp3", f, "audio/mpeg")}
        data = {"mode": "meeting"}

        response = requests.post(
            f"{BASE_URL}/analyze", files=files, data=data, timeout=120
        )

    if response.status_code == 200:
        result = response.json()
        print("✅ Meeting analysis successful!")
        print(f"   - Mode: {result.get('mode')}")
        print(f"   - Filename: {result.get('filename')}")
        print(
            f"   - Transcript segments: {len(result.get('transcript', {}).get('segments', []))}"  # noqa: E501
        )
        print(f"   - Insights keys: {list(result.get('insights', {}).keys())}")
    else:
        print(f"❌ Analysis failed with status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        assert False, f"Analysis failed with status {response.status_code}"


def test_analyze_sales():
    """Test analyze endpoint with sales mode"""
    print("\nTesting /analyze with sales_good.mp3...")

    audio_file = os.path.join(SAMPLE_AUDIO_DIR, "sales_good.mp3")
    if not os.path.exists(audio_file):
        print(f"❌ Sample file not found: {audio_file}")
        assert False, f"Sample file not found: {audio_file}"

    with open(audio_file, "rb") as f:
        files = {"file": ("sales_good.mp3", f, "audio/mpeg")}
        data = {"mode": "sales"}

        response = requests.post(
            f"{BASE_URL}/analyze", files=files, data=data, timeout=120
        )

    if response.status_code == 200:
        result = response.json()
        print("✅ Sales analysis successful!")
        print(f"   - Mode: {result.get('mode')}")
        print(f"   - Filename: {result.get('filename')}")
        print(f"   - Insights keys: {list(result.get('insights', {}).keys())}")
    else:
        print(f"❌ Analysis failed with status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        assert False, f"Analysis failed with status {response.status_code}"


if __name__ == "__main__":
    print("=" * 60)
    print("TalkSense AI - Integration Test")
    print("=" * 60)

    try:
        results = []
        def run_test(name, func):
            try:
                func()
                results.append((name, True))
            except AssertionError:
                results.append((name, False))

        run_test("Health Check", test_health)
        run_test("Meeting Analysis", test_analyze_meeting)
        run_test("Sales Analysis", test_analyze_sales)

        print("\n" + "=" * 60)
        print("Test Results Summary:")
        print("=" * 60)
        for name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {name}")

        total = len(results)
        passed = sum(1 for _, p in results if p)
        print(f"\nTotal: {passed}/{total} tests passed")

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback

        traceback.print_exc()
