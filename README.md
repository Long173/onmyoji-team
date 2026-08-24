# onmyoji_team — crawler dữ liệu阵容 từ yysrank.win

Crawl bảng xếp hạng阵容 (team) của <https://yysrank.win/#/query/team> ra JSON + CSV.
Chỉ dùng Python stdlib, không cần cài dependency.

## Endpoint được dùng

Site là SPA (Vue + Vite), toàn bộ dữ liệu đến từ REST API cùng domain, **không cần đăng nhập**:

| Endpoint | Dùng để |
|---|---|
| `GET /api/team/rank` | bảng阵容 của trang `#/query/team` |
| `GET /api/shishen/rank` | xếp hạng 式神: tier, chọn/ban/thắng, ngự hồn thường dùng, counter |
| `GET /api/shishen/detail` | `trend` 33 ngày + `summary.teams` (100 đội hình, **không áp ngưỡng**) |
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
| Phân bố ngự hồn đầy đủ | `/api/shishen/detail` → `summary.yuhuns` | trả rỗng — cần hội viên `basic` |
| Ngự hồn theo từng đội hình | `/api/team/yuhun` | cần `basic` |
| Chi tiết đội hình | `/api/team/detail` | cần `basic` |
| Counter chi tiết, advance rank, team-counter | `/api/shishen/counter_detail`, `/api/advance/rank`, `/api/team-counter/*` | `401` |

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
build_report.py         # CLI dựng báo cáo HTML
onmyoji/http.py         # GET JSON + retry + validate envelope
onmyoji/assets.py       # map id -> tên 式神 / server
onmyoji/team_rank.py    # TeamRankQuery (immutable) + phân trang
onmyoji/shishen_rank.py # ShishenRankQuery + nhãn cột/tier/hiệu ứng bộ
onmyoji/shishen_detail.py # ShishenDetailQuery: trend + teams
onmyoji/team_detail.py  # /api/team/detail (cần basic)
onmyoji/auth.py         # đọc token từ ONMYOJI_TOKEN hoặc .token, không bao giờ log
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
