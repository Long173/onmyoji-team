#!/usr/bin/env bash
# Lưu access token yysrank.win từ clipboard vào .token (đã gitignored).
#
# Cách dùng: copy token vào clipboard, rồi TỰ GÕ (đừng copy) lệnh:  ./save-token.sh
# Copy lệnh sẽ ghi đè token trong clipboard — đó là lý do file này tồn tại.

set -euo pipefail

TOKEN="$(pbpaste | tr -d '\r\n"'"'"' ')"

if [ ${#TOKEN} -lt 20 ]; then
  echo "✗ Clipboard chỉ có ${#TOKEN} ký tự — quá ngắn, không phải token." >&2
  echo "  Copy lại token rồi gõ tay ./save-token.sh" >&2
  exit 1
fi

case "$TOKEN" in
  *'!'*|*'|'*|*'&'*|*'$'*|*'>'*|*'<'*|*'('*)
    echo "✗ Clipboard trông như một câu lệnh shell, không phải token." >&2
    echo "  Có phải bạn vừa copy câu lệnh? Copy lại token rồi gõ tay ./save-token.sh" >&2
    exit 1 ;;
esac

printf '%s' "$TOKEN" > .token
chmod 600 .token
echo "✓ Đã lưu .token — ${#TOKEN} ký tự, không có khoảng trắng."
echo "  Kiểm tra: python3 crawl_team_detail.py --team 330,390,575,578,585"
