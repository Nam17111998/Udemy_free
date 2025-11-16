# udemy_free – Udemy Free Coupons (Static Site)

Thư mục `udemy_free` tận dụng lại các scraper có sẵn trong project `udemy_enroller` để:

- Thu thập danh sách khóa học Udemy đang miễn phí qua coupon.
- Sinh ra API tĩnh `udemy_free/api/courses.json`.
- Render một web tĩnh (`index.html`) để xem và tìm kiếm các khóa học.
- Tự động cập nhật dữ liệu mỗi giờ bằng GitHub Actions và có thể deploy lên GitHub Pages.

---

## Cấu trúc thư mục

- `udemy_free/build_courses_json.py`  
  Script Python dùng các scraper (`ScraperManager`) để crawl link coupon và sinh file JSON tĩnh.

- `udemy_free/api/courses.json`  
  File JSON tĩnh chứa dữ liệu được sinh ra.  
  Cấu trúc:
  ```json
  {
    "updated_at": "2025-01-01T00:00:00Z",
    "count": 123,
    "courses": [
      {
        "url": "https://www.udemy.com/course/.../?couponCode=...",
        "coupon_code": "..."
      }
    ]
  }
  ```

- `udemy_free/index.html`  
  Trang HTML tĩnh, đọc dữ liệu từ `./api/courses.json` và hiển thị danh sách khóa học.

- `udemy_free/app.js`  
  JavaScript cho frontend: fetch JSON, hiển thị danh sách, hỗ trợ tìm kiếm (filter).

- `udemy_free/styles.css`  
  CSS cho giao diện.

- `.github/workflows/udemy_free_update.yml`  
  Workflow GitHub Actions chạy mỗi giờ để rebuild `udemy_free/api/courses.json` và commit lên repo nếu có thay đổi.

---

## Chạy cục bộ (local)

### 1. Tạo và kích hoạt virtualenv

**Windows (PowerShell):**

```powershell
cd Automatic-Udemy-Course-Enroller-GET-PAID-UDEMY-COURSES-for-FREE-master

python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS (bash/zsh):**

```bash
cd Automatic-Udemy-Course-Enroller-GET-PAID-UDEMY-COURSES-for-FREE-master

python -m venv .venv
source .venv/bin/activate
```

> Lưu ý: Nên dùng Python 3.10+ (hoặc theo version mà repo đang sử dụng).

### 2. Cài đặt dependencies

Sau khi đã kích hoạt virtualenv:

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install .
```

### 3. Sinh dữ liệu JSON (courses.json)

**Windows (PowerShell):**

```powershell
# Tùy chọn: giới hạn số trang để chạy nhanh hơn
$env:UDEMY_FREE_MAX_PAGES = "3"
python udemy_free/build_courses_json.py
```

**Linux / macOS:**

```bash
export UDEMY_FREE_MAX_PAGES=3   # tùy chọn
python udemy_free/build_courses_json.py
```

Nếu không cần giới hạn trang, có thể bỏ thiết lập `UDEMY_FREE_MAX_PAGES`:

```bash
python udemy_free/build_courses_json.py
```

Sau khi chạy xong, file `udemy_free/api/courses.json` sẽ được cập nhật với dữ liệu mới (trong đó `count` > 0 và có danh sách `courses`).

### 4. Chạy web tĩnh để xem danh sách

Để tránh lỗi CORS khi dùng `fetch` trên file local, hãy chạy một HTTP server đơn giản trỏ vào thư mục `udemy_free`:

```bash
python -m http.server -d udemy_free 8000
```

Sau đó mở trình duyệt và truy cập:

```text
http://localhost:8000/
```

Trang web sẽ:

- Đọc dữ liệu từ `./api/courses.json`.
- Hiển thị “Lần build gần nhất” từ trường `updated_at`.
- Liệt kê danh sách các khóa học và coupon code, có ô tìm kiếm.

---

## Hướng dẫn deploy lên GitHub & cài giờ chạy tự động

### Bước 0: Tạo repo Git và kết nối GitHub (từ `git init`)

1. Lên GitHub tạo một repo trống (không cần chọn “Initialize with README” nếu bạn đã có README trong dự án).
2. Ở máy local, trong thư mục dự án:

**Windows (PowerShell) / Linux / macOS:**

```bash
cd Automatic-Udemy-Course-Enroller-GET-PAID-UDEMY-COURSES-for-FREE-master

git init
git branch -M main
git remote add origin https://github.com/<username>/<ten-repo>.git

git add .
git commit -m "Initial commit: Udemy free coupons static site"
git push -u origin main
```

Thay:

- `<username>` bằng username GitHub của bạn.
- `<ten-repo>` bằng tên repo vừa tạo trên GitHub.

Nếu repo đã tồn tại và bạn chỉ sửa thêm `udemy_free`, bạn có thể bỏ qua `git init`, `git branch -M main`, `git remote add origin` và chỉ cần:

```bash
git add udemy_free .github/workflows/udemy_free_update.yml
git commit -m "add udemy_free static site and workflow"
git push
```

### Bước 1: Đảm bảo code `udemy_free` đã có trên GitHub

Trên GitHub (tab **Code**), kiểm tra:

- Thư mục `udemy_free/` đã có đầy đủ các file (HTML/JS/CSS, `build_courses_json.py`, `api/courses.json`).
- File `.github/workflows/udemy_free_update.yml` đã nằm đúng chỗ.

### Bước 2: Cấu hình lịch chạy tự động (cron)

Mở file `.github/workflows/udemy_free_update.yml` trên GitHub, phần:

```yaml
on:
  schedule:
    # Chạy mỗi 1 giờ (UTC)
    - cron: "0 * * * *"
  workflow_dispatch:
```

- `cron: "0 * * * *"` nghĩa là:
  - Mỗi giờ, vào phút thứ 0 (01:00, 02:00, 03:00 UTC, …).
- Bạn có thể chỉnh:
  - 2 giờ/lần: `0 */2 * * *`
  - 1 lần/ngày lúc 00:00 UTC: `0 0 * * *`

Sau khi chỉnh, commit & push để cron mới có hiệu lực.

### Bước 3: Bật GitHub Actions và chạy thử lần đầu

Trên GitHub:

1. Vào repo → tab **Actions**.
2. Nếu thấy nút “Enable Actions” thì bấm để bật.
3. Chọn workflow **Update Udemy Free Courses JSON**.
4. Bấm **Run workflow** → chọn branch → **Run**.

Chờ workflow chạy xong, rồi:

- Xem log:
  - Step `Generate courses JSON` phải chạy OK.
  - Step `Commit and push changes` có thể commit file JSON nếu thay đổi.
- Vào tab **Code** → mở `udemy_free/api/courses.json`:
  - `updated_at` là thời gian mới.
  - `count` > 0, có danh sách `courses`.

Từ sau đó, cron sẽ tự chạy theo cấu hình ở bước 2.

### Bước 4: Bật GitHub Pages để serve web & API

Trên GitHub:

1. Vào repo → **Settings** → **Pages**.
2. Ở phần **Build and deployment**:
   - **Source**: chọn branch bạn dùng (thường là `main` hoặc `master`).
   - **Folder**: `/ (root)`.
3. Bấm **Save**.

Sau khi Pages build xong, bạn sẽ có URL dạng:

```text
https://<username>.github.io/<ten-repo>/udemy_free/
```

Trong đó:

- Web tĩnh:  
  `https://<username>.github.io/<ten-repo>/udemy_free/`
- API tĩnh (JSON):  
  `https://<username>.github.io/<ten-repo>/udemy_free/api/courses.json`

### Bước 5: Tóm tắt luồng tự động

- Mỗi khoảng thời gian theo cron:
  - GitHub Actions chạy workflow `udemy_free_update.yml`.
  - Workflow gọi `python udemy_free/build_courses_json.py`.
  - File `udemy_free/api/courses.json` trên repo được cập nhật nếu có dữ liệu mới.
- GitHub Pages luôn phục vụ bản mới nhất của `index.html` và `api/courses.json`, nên người dùng truy cập URL Pages luôn thấy danh sách khóa học cập nhật tự động.

