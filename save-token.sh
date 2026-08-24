#!/usr/bin/env bash
# Lưu credential yysrank.win từ clipboard. Cả hai file đều đã gitignored.
#
# Cách dùng: trong DevTools Console của yysrank.win, chạy
#
#   copy(JSON.stringify({a:JSON.parse(localStorage.getItem('user-info')).accessToken,
#                        r:JSON.parse(localStorage.getItem('user-info')).refreshToken}))
#
# rồi TỰ GÕ (đừng copy) lệnh:  ./save-token.sh
# Copy lệnh sẽ ghi đè clipboard — đó là lý do file này tồn tại.
#
# Vẫn nhận cả trường hợp clipboard chỉ có access token dạng chuỗi trơn.

set -euo pipefail

RAW="$(pbpaste)"

# Dạng JSON {"a":"...","r":"..."} — lấy được cả hai token.
if printf '%s' "$RAW" | grep -q '"a"'; then
  ACCESS="$(printf '%s' "$RAW" | python3 -c 'import json,sys; print(json.load(sys.stdin)["a"])')"
  REFRESH="$(printf '%s' "$RAW" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("r") or "")')"
else
  ACCESS="$(printf '%s' "$RAW" | tr -d '\r\n"'"'"' ')"
  REFRESH=""
fi

if [ ${#ACCESS} -lt 20 ]; then
  echo "✗ Access token chỉ ${#ACCESS} ký tự — quá ngắn." >&2
  echo "  Copy lại rồi gõ tay ./save-token.sh" >&2
  exit 1
fi

case "$ACCESS" in
  *'!'*|*'|'*|*'&'*|*'$'*|*'>'*|*'<'*|*'('*)
    echo "✗ Clipboard trông như câu lệnh shell, không phải token." >&2
    exit 1 ;;
esac

printf '%s' "$ACCESS" > .token
chmod 600 .token
echo "✓ .token — ${#ACCESS} ký tự"

if [ ${#REFRESH} -ge 20 ]; then
  printf '%s' "$REFRESH" > .refresh-token
  chmod 600 .refresh-token
  echo "✓ .refresh-token — ${#REFRESH} ký tự (dùng để tự lấy access token mới)"
else
  echo "· Không có refresh token trong clipboard — access token sẽ hết hạn sau ~1 giờ."
  echo "  Muốn có: dùng lệnh copy(JSON.stringify(...)) ở đầu file này."
fi
