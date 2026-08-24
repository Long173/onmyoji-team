# onmyoji_team — crawler dữ liệu阵容 từ yysrank.win

Crawl bảng xếp hạng阵容 (team) của <https://yysrank.win/#/query/team> ra JSON + CSV.
Chỉ dùng Python stdlib, không cần cài dependency.

## Endpoint được dùng

Site là SPA (Vue + Vite), toàn bộ dữ liệu đến từ REST API cùng domain, **không cần đăng nhập**:

| Endpoint | Dùng để |
|---|---|
| `GET /api/team/rank` | bảng阵容 của trang `#/query/team` |
| `GET /api/shishen/rank` | xếp hạng 式神: tier, chọn/ban/thắng, ngự hồn thường dùng, counter |
| `GET /api/shishen/detail` | `trend` 33 ngày + `summary.teams`; thêm ngự hồn/ghép cặp/vị trí nếu có hội viên |
| `GET /api/team/detail` | thứ tự BP, âm dương sư, đội hình đối đầu — **cần hội viên `basic`** |
| `GET /api/team/yuhun` | ngự hồn của cả đội theo tổ hợp — **cần `basic`**, phải gộp lại mới dùng được |
| `GET /api/asset/shishen` | map `shishen_id` → tên 式神 |
| `GET /api/asset/shishen_stats` | chỉ số gốc của 273 式神 |
| `GET /api/asset/yuhun` | 79 ngự hồn: tên, icon, hiệu ứng bộ |
| `GET /api/asset/server` | map `server_id` → tên server |

Envelope trả về: `{"success": bool, "data": ..., "error": str}`.

### Tham số của `/api/team/rank`

Suy ra từ bundle `static/js/team-DAhxa0C1.js` + component filter `index.vue_...-a4p3D99D.js`:

| Param | Ý nghĩa | Mặc định trên web |
|---|---|---|
| `start_date`, `end_date` | khoảng ngày `YYYY-MM-DD` | version hiện hành |
| `min_level`, `max_level` | mốc đoạn/điểm (10 = 名仕, 9999 = không giới hạn) | theo cấu hình user |
| `include`, `exclude` | JSON array id 式神 buộc có / loại trừ | `[]` |
| `ban` | JSON array id 式神 ở ô ban, tối đa 2 | `[]` |
| `thres` | số trận tối thiểu của một阵容 | `100` |
| `first_n` | độ dài阵容 | `5` |
| `page`, `page_size` | phân trang (không bị chặn số trang) | `1`, `20` |
| `order` | `win_rate` \| `total` \| `duration` | `win_rate` |
| `desc` | `1` giảm dần, `0` tăng dần | `1` |

Mỗi dòng kết quả: `team` (list id 式神), `win_rate`, `pick_rate`, `total`, `duration` (giây).

## Chạy

```bash
# toàn bộ阵容 của version hiện tại (thres=100)
python3 crawl_team_rank.py

# hạ ngưỡng số trận -> nhiều阵容 hơn (thres=10 cho ~5.3k dòng)
python3 crawl_team_rank.py --thres 10 --slug team-rank-thres10

# sắp theo số lần chọn, chỉ 5 trang đầu
python3 crawl_team_rank.py --order total --max-pages 5

# lọc阵容 có 荒骷髅 (585) và không có 葛叶 (597)
python3 crawl_team_rank.py --include 585 --exclude 597

# khoảng thời gian tùy ý
python3 crawl_team_rank.py --start 2026-06-24 --end 2026-07-21 --slug binh-sa-mon
```

`python3 crawl_team_rank.py --help` để xem đủ cờ.

Kết quả ghi vào `out/<slug>.json` (kèm metadata: params đã gửi, `server_last_update`)
và `out/<slug>.csv` (UTF-8 BOM, mở Excel không lỗi font).

## Dịch tên 式神 & báo cáo có avatar

```bash
python3 build_report.py --version-label "Phiên bản Bất Tương Hồ Thiền · 22/07 → nay" --version-cn "不相狐禅"
```

Sinh `report/meta-dau-ky.html` — một file HTML tự chứa (~0.6 MB): 81 avatar nhúng sẵn
dạng data URI, lọc theo 式神, sắp theo 4 chỉ số, bảng xếp hạng 式神 và bảng đối chiếu tên.

Avatar lấy từ `https://yysrank.win/imgs/shishen/<id>.webp`, cache trong `assets/avatars/`.

### Cách dịch tên

Tên dịch theo **âm Hán-Việt từng ký tự** (`onmyoji/hanviet.py`, 412 ký tự — phủ 100%
tên của cả 277 式神). Cách này deterministic, nhất quán, và tự phủ được 式神 mới:
ký tự nào chưa có trong bảng sẽ được giữ nguyên và CLI in cảnh báo.

`onmyoji/translate.py` thêm bảng `COMMON_NAMES` cho tên romaji/quốc tế đã quen
(vd. 荒骷髅 → "Hoang Khô Lâu (Gashadokuro)").

| Tên gốc | Hán-Việt | Thông dụng |
|---|---|---|
| 荒骷髅 | Hoang Khô Lâu | Gashadokuro |
| 一目连 | Nhất Mục Liên | Ichimokuren |
| 鬼王酒吞童子 | Quỷ Vương Tửu Thôn Đồng Tử | Shuten-doji Onikiri |
| 大夜摩天阎魔 | Đại Dạ Ma Thiên Diêm Ma | Enma Yama |
| 不知火 | Bất Tri Hỏa | Shiranui |
| 神启荒 | Thần Khải Hoang | Susanoo Kagura |
| 不相狐禅 | Bất Tương Hồ Thiền | — |

## Bảng xếp hạng 式神 (tier, chỉ số, ngự hồn)

```bash
python3 crawl_shishen_rank.py --slug shishen-rank-current
```

`/api/shishen/rank` **không phân trang** — trả toàn bộ 式神 đạt ngưỡng trong một lần gọi;
field `total` là *số trận phân tích*, không phải số dòng. Tham số: `start_date`, `end_date`,
`min_level`, `max_level`, `tag`, `ban`.

Mỗi dòng: `tier` (0 mạnh nhất → 3), `tier_score`, `win_rate` (外战胜率), `pick_rate` (选用率),
`ban_rate` (禁用率), `external_rate` (外战比例), `duration`, `avg_position` (选取次序),
`most_used_yuhuns` (常用御魂 — 3 bộ hay dùng), `counter` (克制), `countered_by` (受制于).

### Giới hạn quyền truy cập

Đã kiểm tra thực tế từng endpoint:

| Dữ liệu | Endpoint | Trạng thái |
|---|---|---|
| Chỉ số gốc 式神 | `/api/asset/shishen_stats` | mở |
| Tên + icon ngự hồn | `/api/asset/yuhun` | mở |
| 3 ngự hồn hay dùng / 式神 | `/api/shishen/rank` | mở |
| Phân bố ngự hồn đầy đủ | `/api/shishen/detail` → `summary.yuhuns` | **`basic`** — đã xác minh |
| Đi cùng / đối đầu / vị trí BP | `/api/shishen/detail` → `synergies`/`counters`/`positions` | **`basic`** |
| Thứ tự BP, âm dương sư, đội hình đối đầu | `/api/team/detail` → `order`/`yys`/`counter` | **`basic`** |
| `ban_stats` / `ban_conditions` | `/api/team/detail`, `/api/shishen/detail` | vẫn rỗng ở `basic` → cần `pro` |
| Chiến báo công khai | `/api/team/public-records` | `请升级到高级版(Pro)` |
| Counter chi tiết, advance rank, team-counter, recommend, team/yuhun | nhiều endpoint | mở ở `basic` nhưng còn `400 请求参数解析错误` — chưa tra đúng tham số |

**Tài khoản free không mở thêm dữ liệu nào.** Đã kiểm bằng token thật: route
`/query/team/detail` khai `accessTier: "free"` nhưng đó chỉ là quyền *mở trang* — API bên
dưới trả `请升级到基础版或高级版(Pro)以解锁本功能`. So sánh `/api/shishen/detail` có token
free vs không token cho kết quả giống hệt. Free chỉ thêm `/api/user/*` (thông tin tài khoản
của chính bạn).

⚠️ **Icon ngự hồn nằm trên CDN NetEase** (`ok.166.net`) và CDN đó trả `403` nếu request
mang `Referer` trỏ về yysrank.win — vì vậy site đặt `referrerpolicy="no-referrer"` trên
thẻ `<img>`. `onmyoji/avatars.py` bỏ header `Referer` cho URL ngoài (`EXTERNAL_HEADERS`).

### Dịch tên ngự hồn

Bảng Hán-Việt đã mở rộng lên **507 ký tự**, phủ 100% tên của cả 277 式神 và 79 ngự hồn:
轮入道 → Luân Nhập Đạo, 火灵 → Hỏa Linh, 招财猫 → Chiêu Tài Miêu, 魍魉之匣 → Vọng Lượng Chi Hạp.
Hiệu ứng bộ cũng dịch sang tiếng Việt (`AttackRate` → Tấn công, `CritPower` → Bạo sát…).

## Trend và đội hình dưới ngưỡng

```bash
python3 crawl_shishen_detail.py          # 42 request, nghỉ 0.8s
```

`/api/shishen/detail?id=<shishen_id>` (chú ý: `id`, **không** phải `shishen_id`) trả về:

| Mục | Trạng thái |
|---|---|
| `trend` — mỗi ngày một điểm `win_rate` / `pick_rate` / `ban_rate` | mở |
| `summary.teams` — tối đa 100 đội hình chứa 式神 đó, **không áp ngưỡng số trận** | mở |
| `summary.yuhuns` / `positions` / `counters` / `synergies`, `ban_stats` | rỗng — cần hội viên `basic` |

### Quy đổi `pick_rate` sang số trận

`summary.teams` không có field `total`, nhưng ở bảng xếp hạng đội hình tỉ số
`total / pick_rate` **bằng nhau tuyệt đối** trên cả 676 dòng (lệch 0,00%) — nó chính là
tổng lượt chọn trong khoảng lọc (453.810 ở phiên bản hiện tại). Nên:

```
số trận = pick_rate × (total / pick_rate của bất kỳ đội hình đã xếp hạng)
```

`onmyoji/report.py::derive_pick_base()` tính hằng số này từ dữ liệu mỗi lần build thay vì
hardcode, vì nó thay đổi theo khoảng thời gian lọc. Nhờ vậy 827 đội hình ngoài bảng xếp hạng
có số trận thật, và lọc được nhiễu mẫu nhỏ.

⚠️ Đội hình dưới ngưỡng có mẫu nhỏ nên tỉ lệ thắng dao động mạnh. Báo cáo mặc định
lọc từ 50 trận và ghi rõ cảnh báo này trên trang.

### Sparkline

Một series duy nhất (`win_rate`), **không tô area fill** vì trục y bị zoom — tô fill trên
baseline khác 0 là gây hiểu sai. Thang y dùng chung cho cả 42 sparkline nên so sánh được
giữa các 式神; có mốc 50% (ngưỡng thắng/thua ngang bằng) và điểm cuối được nhấn.

Màu mark được kiểm bằng `validate_palette.js` của skill `dataviz` thay vì chọn bằng mắt:
light `#00805F`, dark `#2FA588` — cả hai pass lightness band, chroma floor và contrast.
Màu accent UI cũ (`#1C6B58` / `#4EC0A0`) không đạt chroma floor khi làm mark biểu đồ nên
biểu đồ dùng token riêng (`--chart-line`).

## Dữ liệu hội viên `basic`

```bash
./save-token.sh                    # copy token vào clipboard trước, rồi TỰ GÕ lệnh này
python3 crawl_shishen_detail.py    # tự dùng .token nếu có
python3 build_report.py --include-paid --output report/meta-dau-ky-full.html
```

Với token `basic`, `/api/shishen/detail` trả thêm 4 mục mà tài khoản free nhận array rỗng:

| Mục | Nội dung | Ví dụ (荒骷髅) |
|---|---|---|
| `summary.yuhuns` | mỗi bộ ngự hồn: `yuhun_id`, `total`, `win_rate` | 29 bộ; 木魅 62,5% qua 1.858 trận |
| `summary.synergies` | 式神 đi cùng: `shishen_id`, `total`, `win_rate` | 162 dòng |
| `summary.counters` | 式神 gặp phải | 157 dòng |
| `summary.positions` | hiệu quả theo lượt chọn BP | 6 lượt |

`/api/team/detail` cũng mở ở `basic`: `order` (16 thứ tự BP kèm win/pick/total),
`yys` (âm dương sư dẫn dắt), `counter` (50 đội hình đối đầu). Riêng `yuhun` và
`ban_stats` trong đó vẫn rỗng — cần `pro`.

### Lọc nhiễu là bắt buộc

Median toàn bộ dòng ngự hồn chỉ **7 trận**. Trong 884 dòng, chỉ 141 dòng đạt ≥100 trận.
Nên `onmyoji/report.py` lọc ngự hồn từ 100 trận, ghép cặp từ 300 trận, vị trí từ 50 trận,
và tính **chênh lệch so với tỉ lệ thắng chung của chính 式神 đó** — đó mới là tín hiệu
dùng được ("bộ này hơn trung bình +11,2 điểm"), chứ không phải con số tuyệt đối.

### Session của yysrank.win: một phiên, refresh dùng một lần

Ba điều đã kiểm chứng bằng thực nghiệm, quyết định toàn bộ kiến trúc auth:

| Điều | Bằng chứng |
|---|---|
| Access token sống **12 giờ** | claim `exp` − `iat` = 43.200s |
| Refresh token sống **7 ngày** nhưng **dùng một lần** | gọi `/api/auth/refresh-token` lần hai → `409` |
| Site chỉ cho **một session** | body của 409 là `重复登录` (đăng nhập trùng) |

⇒ **CI không thể tự crawl dữ liệu hội viên.** Refresh trong CI sẽ tạo session mới và
đăng xuất bạn khỏi browser; bạn đăng nhập lại thì token của CI chết. Hai bên loại trừ nhau.

Vì vậy `resolve_token()` **ưu tiên access token đang có** và chỉ refresh khi `exp` đã qua,
rồi ghi ngay cặp token mới xuống file. Refresh bừa bãi là đăng xuất chính mình.

Lỗi `409` được xếp vào `AUTH_FAILURE_CODES` cùng 401/403 (bundle của site cũng coi
`401||409` là auth failure) và không retry.

### Một trang duy nhất, dữ liệu hội viên trộn từ file đã commit

CI crawl được dữ liệu mở nhưng không crawl được dữ liệu hội viên. Để trang vẫn là
**một bản duy nhất** mà vẫn tự cập nhật hằng ngày, khối dữ liệu hội viên được build tại
máy, commit thành `prebuilt/paid.json` (109 KB), rồi `build_report.py` tự trộn vào mỗi
lần build — kể cả trên CI, nơi không có token.

```bash
./save-token.sh                                  # sau khi đăng nhập lại yysrank.win
python3 crawl_shishen_detail.py                  # dùng .token nếu có
python3 crawl_team_detail.py --top 40 --by total
python3 crawl_team_yuhun.py --top 40 --by total
python3 export_paid.py                           # -> prebuilt/paid.json
git add prebuilt/paid.json && git commit -m "chore: cập nhật dữ liệu hội viên" && git push
```

| Phần dữ liệu | Nguồn | Cập nhật |
|---|---|---|
| Đội hình, xếp hạng 式神, trend, đội hình dưới ngưỡng | CI crawl | tự động 01:00 UTC mỗi ngày |
| Ngự hồn chi tiết, ghép cặp, vị trí BP, thứ tự pick | `prebuilt/paid.json` đã commit | thủ công, khi chạy khối lệnh trên |

Muốn dựng bản không có dữ liệu hội viên: `build_report.py --no-paid-input`.

`.token`, `.refresh-token`, `out/`, `report/`, `site/` gitignored — chỉ
`prebuilt/paid.json` được commit.

### `/api/team/yuhun`: phải gộp mới dùng được

Endpoint trả tối đa **50 tổ hợp ngự hồn hoàn chỉnh** cho cả đội (mỗi 式神 một bộ),
kèm `win_rate` + `total`. Tham số: `team1`, `team2` (để `[]` — có team2 cụ thể thì
gần như luôn trả 0 dòng), `all_suits`, cùng bộ filter thời gian/đoạn.

Dùng trực tiếp thì vô nghĩa: **median 3 trận/tổ hợp**, cao nhất 24. Cách dùng được là
gộp theo cặp (式神, ngự hồn), cộng dồn `total` và tính tỉ lệ thắng gia quyền — khi gộp,
các lựa chọn phổ biến đạt 100–354 trận.

Đo trên 40 đội hình:

| | |
|---|---|
| Lựa chọn đạt ngưỡng 30 trận | 182 (median 5/đội, 8 đội không có gì) |
| Số trận mỗi lựa chọn | median 54, max 354 |
| Đủ mẫu để hiện tỉ lệ thắng (≥50) | 103/182 — 79 cái hiện dấu `—` |
| Độ phủ so với tổng trận của đội | median **4,1%** (API cắt ở top 50 tổ hợp) |

⚠️ Hai giới hạn phải nêu kèm khi trình bày, và trang có ghi:
1. Chỉ phủ ~4% số trận của đội.
2. Mẫu **lệch về tổ hợp phổ biến** — một bộ hay dùng trong nhiều tổ hợp hiếm sẽ bị
   đếm thiếu. Đây là chỉ dấu "bộ hay dùng", không phải tỉ lệ tuyệt đối.

Đối chiếu với ngự hồn meta-wide ở tab 式神 (mẫu hàng nghìn trận): 3/5 vị trí khớp,
2 vị trí khác — phần khác nhau mới là thứ đáng xem, nhưng cũng có thể là do mẫu lệch.

### Lọc nhiều 式神: chọn từ gợi ý, áp dụng bằng nút

Bảng đội hình có 676 dòng × 5 avatar (~925 KB HTML mỗi lần render), nên **lọc theo
từng ký tự gõ là không dùng được** — mỗi keystroke dựng lại toàn bộ chuỗi HTML.
Debounce chỉ giảm bớt. Cách xử lý:

- Gõ vào ô → hiện **popup gợi ý** (tối đa 8 式神, kèm avatar, tên Trung, và số đội
  hình chứa nó). Điều hướng bằng ↑/↓, chọn bằng Enter hoặc chuột, Esc để đóng,
  Backspace ở ô trống để bỏ chip cuối.
- Mỗi lựa chọn thành một **chip** có nút ×. **Không render gì trong lúc này.**
- Bấm **Lọc** mới lọc. Nút sáng viền vàng kèm chữ "có thay đổi chưa áp dụng" khi
  bộ lọc trên ô khác với bộ đang áp dụng.
- Enter khi không có gợi ý nào được chọn = áp dụng luôn.

Đo bằng test DOM: gõ 3 ký tự → **0 lần render**; chọn 3 chip → **0 lần render**;
bấm Lọc → **1 lần render**.

Lọc theo **id 式神** (chính xác, không có bất ngờ kiểu chuỗi con). Chữ còn sót trong
ô lúc bấm Lọc được dùng như từ khoá chuỗi con, nên vẫn gõ nhanh rồi Enter được.
Gợi ý khớp không dấu (`đ`→`d`, bỏ dấu phụ NFD) trên tên Hán-Việt, tên Trung, tên
thông dụng và id — `cat`, `Cát`, `葛叶` đều ra Cát Diệp.

Tab 式神 vẫn dùng ô text thường: chỉ 42 dòng nên render mỗi keystroke không hề chậm.

⚠️ Một bug đã bắt được nhờ test: cả picker và listener "Enter để áp dụng" đều gắn
`keydown` trên cùng ô. Picker đóng popup trước, listener sau thấy popup đã đóng nên
bấm nút Lọc → render mỗi lần thêm chip. Fix bằng cờ `event.pickerCommitted`.

### Màu thanh chênh lệch

Cặp đối cực đã validate bằng `dataviz/validate_palette.js`:
light `#00805F` / `#A65A18`, dark `#2FA588` / `#C97A3C`.

Ban đầu mình dùng jade + hồng, nhưng **hồng càng đậm thì separation deutan càng tệ**
(xanh↔đỏ là cặp mù màu kinh điển): ở dark mode mọi tông hồng đều ra ΔE 0,3–3,9, dưới cả
floor 6 nên không hợp lệ kể cả khi có encoding phụ. Đổi cực âm sang cam thì ΔE lên 9,2
(light, protan) và 10,4 (dark, deutan) — vượt mốc 8, pass không WARN. Dấu còn được mã hoá
bằng **hướng thanh** và **nhãn số có dấu**, không phụ thuộc màu.

## Deploy lên GitHub Pages

Workflow `.github/workflows/publish.yml` tự crawl lại rồi publish, chạy khi push vào `main`,
theo lịch **01:00 UTC mỗi ngày** (08:00 giờ VN), và khi bấm *Run workflow* thủ công.

Site xuất ra gồm `index.html` (báo cáo) cùng `team-rank-current.json` / `.csv` để tải về —
footer báo cáo tự hiện link khi build với cờ `--data-links`.

Lần đầu, cần đăng nhập `gh` rồi tạo repo:

```bash
gh auth login                                    # tương tác — tự chạy
gh repo create onmyoji-team --public --source=. --remote=origin --push
gh api -X POST repos/:owner/onmyoji-team/pages -f build_type=workflow
```

Nếu `gh api` báo repo đã bật Pages thì đổi `-X POST` thành `-X PUT`. Sau đó:

```bash
gh workflow run publish.yml
gh run watch
```

Ảnh avatar **không** được commit — workflow tải lúc build và cache lại qua `actions/cache`,
nên repo không mang theo tài nguyên của yysrank.win.

Build thử y như CI ở local:

```bash
python3 crawl_team_rank.py --slug team-rank-current
python3 crawl_shishen_rank.py --slug shishen-rank-current
python3 crawl_shishen_detail.py
python3 build_report.py --data-links --output site/index.html
cp out/*.json out/*.csv site/
python3 -m http.server -d site 8000        # mở http://localhost:8000
```

## Cấu trúc

```
crawl_team_rank.py      # CLI crawl bảng đội hình
crawl_shishen_rank.py   # CLI crawl bảng xếp hạng 式神
crawl_shishen_detail.py # CLI crawl trend + đội hình theo 式神
crawl_team_detail.py    # CLI chi tiết đội hình — CẦN hội viên basic
crawl_team_yuhun.py     # CLI ngự hồn theo đội hình — CẦN basic, gộp ngay khi crawl
export_paid.py          # gom dữ liệu hội viên -> prebuilt/paid.json để commit
save-token.sh           # lưu token từ clipboard, có kiểm tra định dạng
build_report.py         # CLI dựng báo cáo HTML
onmyoji/http.py         # GET JSON + retry + validate envelope
onmyoji/assets.py       # map id -> tên 式神 / server
onmyoji/team_rank.py    # TeamRankQuery (immutable) + phân trang
onmyoji/shishen_rank.py # ShishenRankQuery + nhãn cột/tier/hiệu ứng bộ
onmyoji/shishen_detail.py # ShishenDetailQuery: trend + teams
onmyoji/team_detail.py  # /api/team/detail (cần basic)
onmyoji/team_yuhun.py   # /api/team/yuhun + gộp theo cặp (式神, ngự hồn)
onmyoji/auth.py         # đọc token từ ONMYOJI_TOKEN hoặc .token, không bao giờ log
onmyoji/yys.py          # 6 âm dương sư (yys_id 1-6 và 10-16 cùng trỏ về 6 nhân vật)
onmyoji/output.py       # chuẩn hoá bản ghi, ghi JSON/CSV
onmyoji/hanviet.py      # bảng ký tự Hán -> âm Hán-Việt (412 ký tự)
onmyoji/translate.py    # dịch tên + bảng tên thông dụng
onmyoji/avatars.py      # tải & cache avatar 式神 + icon ngự hồn
onmyoji/report.py       # gộp thống kê, nhúng avatar, render template
templates/report.html   # template báo cáo (CSS + JS render phía client)
```

## Lưu ý

- Crawler nghỉ 0.4s giữa các request; giữ nguyên hoặc tăng nếu crawl nhiều.
- Field `total` trong response là số ước lượng tại thời điểm request nên có thể lệch
  vài dòng so với số dòng thực nhận về; crawler dừng khi trang trả về rỗng.
- Các endpoint `/api/shishen/rank`, `/api/team/detail`, `/api/team-counter/*`,
  `/api/advance/rank` cùng dạng tham số — có thể mở rộng thêm module tương tự.
