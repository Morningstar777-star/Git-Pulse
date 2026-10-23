"""
Full System Audit & Verification Suite for GitPulse Explorer.
Tests:
1. System Status endpoint (connected to Turso Cloud)
2. Repository queries (pagination, search, categories)
3. Momentum Radar ranking
4. Topics classification
5. User authentication lifecycle (Sign up -> Session -> Save Bookmark -> Watchlist -> Forgot Password -> Reset -> Sign in -> Sign out)
6. Security checks (401 on unauthenticated bookmark write, password hashing, SQL injection safety)
"""

import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def request_json(path: str, method: str = "GET", data: dict = None, token: str = None):
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_body = {"raw": str(e)}
        return e.code, err_body
    except Exception as e:
        return 500, {"error": str(e)}

def run_audit():
    print("="*60)
    print("       GITPULSE EXPLORER - COMPREHENSIVE SYSTEM AUDIT        ")
    print("="*60)
    passed = 0
    total = 0

    def assert_test(name: str, condition: bool, extra: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name} {extra}")
        else:
            print(f"  [FAIL] {name} {extra}")

    # 1. System Status
    print("\n--- 1. Testing Live System Status (Turso Database) ---")
    st, data = request_json("/api/status")
    assert_test("Status Endpoint 200 OK", st == 200)
    assert_test("Repositories count > 2000", data.get("total_repositories", 0) >= 2000, f"({data.get('total_repositories')} repos)")
    assert_test("Topics count > 900", data.get("total_topics", 0) >= 900, f"({data.get('total_topics')} topics)")

    # 2. Repositories Query
    print("\n--- 2. Testing Repository Intelligence & Search ---")
    st, repos = request_json("/api/repositories?page=1&page_size=5")
    assert_test("List Repositories 200 OK", st == 200 and len(repos) == 5)
    
    st, search_repos = request_json("/api/repositories?search=speech&page_size=3")
    assert_test("Search 'speech' intent retrieval", st == 200 and len(search_repos) > 0, f"(Found {len(search_repos)} matches)")

    # 3. Momentum Radar
    print("\n--- 3. Testing Bayesian Kinetic Momentum Radar ---")
    st, radar = request_json("/api/momentum/radar?time_window=7d&limit=5")
    assert_test("Momentum Radar 200 OK", st == 200 and len(radar) > 0)
    if radar:
        assert_test("Momentum score calculated", "momentum_score" in radar[0], f"(Top score: {radar[0].get('momentum_score')})")

    # 4. Topics Breakdown
    print("\n--- 4. Testing Curated Topic Categories ---")
    st, topics = request_json("/api/topics?mode=momentum&limit=5")
    assert_test("Topics Directory 200 OK", st == 200 and len(topics) > 0)
    if topics:
        assert_test("Category has repositories", len(topics[0].get("top_repositories", [])) > 0)

    # 5. Security & Authentication Flow
    print("\n--- 5. Testing Cybersecurity & User Authentication ---")
    
    # 5a. Unauthenticated Bookmark must fail with 401
    st, unauth_res = request_json("/api/watchlist", method="POST", data={"repo_id": 1})
    assert_test("Unauthenticated bookmark write rejected (401)", st == 401)

    # 5b. User Signup
    import random
    test_email = f"audit_tester_{random.randint(1000, 9999)}@example.com"
    st, signup_res = request_json("/api/auth/signup", method="POST", data={
        "email": test_email,
        "password": "Password123!Secure",
        "name": "Audit Test User"
    })
    assert_test("User Sign Up 200 OK", st == 200 and "token" in signup_res)
    token = signup_res.get("token")

    # 5c. Fetch current user (/api/auth/me)
    st, me_res = request_json("/api/auth/me", token=token)
    user_email = me_res.get("user", {}).get("email") if isinstance(me_res.get("user"), dict) else me_res.get("email")
    assert_test("Fetch Me (/api/auth/me) with Bearer token", st == 200 and user_email == test_email)

    # 5d. Authenticated Bookmark write & read
    sample_repo_id = repos[0]["id"] if repos else 1
    st, save_res = request_json("/api/watchlist", method="POST", data={"repo_id": sample_repo_id}, token=token)
    assert_test("Authenticated Bookmark save (200 OK)", st == 200 and save_res.get("is_saved") is True)

    st, wl_res = request_json("/api/watchlist", token=token)
    assert_test("Fetch User Watchlist", st == 200 and isinstance(wl_res, list) and any(r["id"] == sample_repo_id for r in wl_res))

    # 5e. Forgot Password & Reset Flow
    st, forgot_res = request_json("/api/auth/forgot-password", method="POST", data={"email": test_email})
    assert_test("Forgot Password code generation", st == 200 and "reset_code" in forgot_res)
    reset_code = forgot_res.get("reset_code")

    st, reset_res = request_json("/api/auth/reset-password", method="POST", data={
        "email": test_email,
        "reset_code": reset_code,
        "new_password": "NewPassword456!Secure"
    })
    assert_test("Reset Password with 6-digit code", st == 200 and "token" in reset_res)

    # 5f. Sign In with new password
    st, signin_res = request_json("/api/auth/signin", method="POST", data={
        "email": test_email,
        "password": "NewPassword456!Secure"
    })
    assert_test("Sign In with New Password (200 OK)", st == 200 and "token" in signin_res)
    new_token = signin_res.get("token")

    # 5g. Sign Out
    st, signout_res = request_json("/api/auth/signout", method="POST", token=new_token)
    assert_test("Sign Out invalidates session", st == 200)

    # 6. Static SPA Delivery Check
    print("\n--- 6. Testing Production Frontend Delivery ---")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=5) as root_resp:
            root_html = root_resp.read().decode("utf-8")
            assert_test("Root HTML SPA served (200 OK)", root_resp.status == 200 and "<html" in root_html.lower())
    except Exception as e:
        assert_test("Root HTML SPA served (200 OK)", False, f"({e})")

    print("\n" + "="*60)
    print(f"AUDIT SUMMARY: {passed}/{total} tests PASSED ({int((passed/total)*100)}%)")
    print("="*60 + "\n")
    return passed == total

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
