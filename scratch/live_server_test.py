import subprocess
import time
import urllib.request
import json
import sys
import os

PORT = 5501
URL_BASE = f"http://127.0.0.1:{PORT}"

print(f"Starting AgroTrack AI backend test server on port {PORT}...")

env = os.environ.copy()
env["PORT"] = str(PORT)
env["HOST"] = "127.0.0.1"

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
    text=True
)

try:
    # Polling wait for server to boot up
    connected = False
    for attempt in range(25):
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            print("Process terminated early!")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            sys.exit(1)
        try:
            req = urllib.request.Request(f"{URL_BASE}/api/v1/auth/roles")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    connected = True
                    print(f"Server ready after {attempt + 1}s!")
                    break
        except Exception:
            time.sleep(1)

    if not connected:
        print("Failed to connect after timeout!")
        proc.terminate()
        stdout, stderr = proc.communicate()
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        sys.exit(1)

    # 1. Test root GET /
    print("\n1. Testing GET / ...")
    req = urllib.request.Request(f"{URL_BASE}/")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f" [OK] GET / status: {resp.status}")
        body = resp.read().decode('utf-8', errors='ignore')
        assert "html" in body.lower()
        print(" [OK] Root endpoint delivered frontend shell")

    # 2. Test GET /overview.html
    print("\n2. Testing GET /overview.html ...")
    req = urllib.request.Request(f"{URL_BASE}/overview.html")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f" [OK] GET /overview.html status: {resp.status}")
        body = resp.read().decode('utf-8', errors='ignore')
        assert "AgroTrack AI" in body
        assert "Executive Command Overview" in body
        print(" [OK] Overview page served successfully")

    # 3. Test GET /api/v1/auth/roles
    print("\n3. Testing GET /api/v1/auth/roles ...")
    req = urllib.request.Request(f"{URL_BASE}/api/v1/auth/roles")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f" [OK] GET /api/v1/auth/roles status: {resp.status}")
        data = json.loads(resp.read().decode('utf-8'))
        assert "roles" in data
        assert len(data["roles"]) == 5
        print(f" [OK] Roles contract verified (5 roles defined)")

    # 4. Test GET /api/v1/platform/overview (Bearer Auth)
    print("\n4. Testing GET /api/v1/platform/overview with Bearer mock-token-admin ...")
    req = urllib.request.Request(
        f"{URL_BASE}/api/v1/platform/overview",
        headers={"Authorization": "Bearer mock-token-admin"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f" [OK] GET /api/v1/platform/overview status: {resp.status}")
        data = json.loads(resp.read().decode('utf-8'))
        assert data["organisation"]["name"] == "GreenValley AgTech Cooperative"
        assert data["metrics"]["activeFarms"] == 48
        print(f" [OK] Overview API delivered live organisation metrics")

    # 5. Test 401 Unauthorized
    print("\n5. Testing 401 Unauthorized on protected endpoint without token ...")
    try:
        req = urllib.request.Request(f"{URL_BASE}/api/v1/platform/overview")
        urllib.request.urlopen(req, timeout=5)
        print(" [FAIL] Expected 401, but succeeded!")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        assert e.code == 401
        print(" [OK] 401 Unauthorized correctly enforced by backend middleware")

    # 6. Test 403 Forbidden for Viewer role on admin endpoint
    print("\n6. Testing 403 Forbidden for Viewer role on member management ...")
    try:
        req = urllib.request.Request(
            f"{URL_BASE}/api/v1/organisations/members",
            headers={"Authorization": "Bearer mock-token-viewer"}
        )
        urllib.request.urlopen(req, timeout=5)
        print(" [FAIL] Expected 403, but succeeded!")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        assert e.code == 403
        print(" [OK] 403 Forbidden correctly enforced by backend RBAC")

    print("\n>>> ALL LIVE HTTP & FRONTEND CHECKS PASSED SUCCESSFULLY! <<<")

finally:
    proc.terminate()
    proc.wait()
    print("Test server stopped.")
