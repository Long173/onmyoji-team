# onmyoji_team — crawler dữ liệu阵容 từ yysrank.win

Crawl bảng xếp hạng阵容 (team) của <https://yysrank.win/#/query/team> ra JSON + CSV.
Chỉ dùng Python stdlib, không cần cài dependency.

## Endpoint được dùng

Site là SPA (Vue + Vite), toàn bộ dữ liệu đến từ REST API cùng domain, **không cần đăng nhập**:

| Endpoint | Dùng để |
|---|---|
| `GET /api/team/rank` | bảng阵容 của trang `#/query/team` |
| `GET /api/asset/shishen` | map `shishen_id` → tên 式神 |
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
python3 build_report.py --data-links --output site/index.html
cp out/team-rank-current.json out/team-rank-current.csv site/
python3 -m http.server -d site 8000        # mở http://localhost:8000
```

## Cấu trúc

```
crawl_team_rank.py      # CLI crawl
build_report.py         # CLI dựng báo cáo HTML
onmyoji/http.py         # GET JSON + retry + validate envelope
onmyoji/assets.py       # map id -> tên 式神 / server
onmyoji/team_rank.py    # TeamRankQuery (immutable) + phân trang
onmyoji/output.py       # chuẩn hoá bản ghi, ghi JSON/CSV
onmyoji/hanviet.py      # bảng ký tự Hán -> âm Hán-Việt (412 ký tự)
onmyoji/translate.py    # dịch tên + bảng tên thông dụng
onmyoji/avatars.py      # tải & cache avatar
onmyoji/report.py       # gộp thống kê, nhúng avatar, render template
templates/report.html   # template báo cáo (CSS + JS render phía client)
```

## Lưu ý

- Crawler nghỉ 0.4s giữa các request; giữ nguyên hoặc tăng nếu crawl nhiều.
- Field `total` trong response là số ước lượng tại thời điểm request nên có thể lệch
  vài dòng so với số dòng thực nhận về; crawler dừng khi trang trả về rỗng.
- Các endpoint `/api/shishen/rank`, `/api/team/detail`, `/api/team-counter/*`,
  `/api/advance/rank` cùng dạng tham số — có thể mở rộng thêm module tương tự.
