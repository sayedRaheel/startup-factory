#!/usr/bin/env sh
# demo.sh — generate a throwaway HS256 token and run jwtpeek on it.
set -e
cd "$(dirname "$0")"

TOKEN=$(python3 - <<'EOF'
import base64, hashlib, hmac, json, time
b = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=").decode()
h = b(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
p = b(json.dumps({"sub": "demo-user", "role": "admin",
                  "iat": int(time.time()),
                  "exp": int(time.time()) + 3600}).encode())
sig = hmac.new(b"demo-secret", f"{h}.{p}".encode(), hashlib.sha256).digest()
print(f"{h}.{p}.{b(sig)}")
EOF
)

echo "== pretty print =="
python3 jwtpeek.py "$TOKEN"

echo
echo "== JSON output =="
python3 jwtpeek.py --json "$TOKEN"

echo
echo "== signature verification =="
python3 jwtpeek.py --verify demo-secret "$TOKEN" >/dev/null
