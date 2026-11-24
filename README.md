# Báo cáo Thực hành CSDL: Nạp dữ liệu lớn (4.56 triệu dòng) vào SQLite

**Thông tin sinh viên:**
- **Họ và tên:** Nguyễn Thị Hà
- **Mã sinh viên:** 23001602
- **Lớp:** K68 EEI
## 1. Giới thiệu bài toán & Dữ liệu đầu vào
Dự án thực hiện bài toán trích xuất, chuẩn hóa và nạp dữ liệu quy mô lớn từ nhiều tệp CSV vào hệ quản trị cơ sở dữ liệu quan hệ (SQLite) có cấu trúc nhiều bảng, đồng thời đo lường và so sánh hiệu năng giữa hai phương pháp xử lý khác nhau.

* **Nguồn dữ liệu:** Bộ dữ liệu *Crimes in Chicago* (Kaggle).
* **Các tệp dữ liệu sử dụng:**
  1. `Chicago_Crimes_2005_to_2007.csv`: **1,872,343** dòng.
  2. `Chicago_Crimes_2008_to_2011.csv`: **2,688,710** dòng.
* **Tổng quy mô dữ liệu:** **4,561,053** bản ghi.

---

## 2. Thiết kế Cơ sở dữ liệu (Mô hình quan hệ 3 bảng)
Dữ liệu phẳng từ các tệp CSV được chuẩn hóa và tách thành 3 bảng có khóa chính (`PRIMARY KEY`) và khóa ngoại (`FOREIGN KEY`) chặt chẽ để tránh dư thừa dữ liệu:

1. **`crime_types` (Danh mục loại tội phạm):**
   * `iucr` (TEXT, PK): Mã phân loại tội phạm.
   * `primary_type` (TEXT): Nhóm tội phạm chính.
   * `description` (TEXT): Mô tả chi tiết hành vi.
2. **`locations` (Danh mục địa điểm):**
   * `location_id` (INTEGER, PK, AUTOINCREMENT): Mã định danh địa điểm.
   * `block` (TEXT): Khu vực/tuyến phố.
   * `location_description` (TEXT): Loại địa điểm cụ thể (đường phố, nhà riêng, cửa hàng...).
   * `district` (TEXT): Mã quận cảnh sát (`UNIQUE(block, location_description, district)`).
3. **`incidents` (Bảng sự việc chính):**
   * `id` (INTEGER, PK): Mã định danh vụ việc.
   * `case_number` (TEXT): Số hồ sơ vụ án.
   * `incident_date` (TEXT): Thời gian xảy ra.
   * `arrest` (INTEGER): Trạng thái bắt giữ (0/1).
   * `domestic` (INTEGER): Tội phạm gia đình (0/1).
   * `year` (INTEGER): Năm xảy ra.
   * `iucr` (TEXT, FK -> `crime_types.iucr`).
   * `location_id` (INTEGER, FK -> `locations.location_id`).

---

## 3. So sánh 2 phương pháp nạp dữ liệu

| Tiêu chí | Cách 1: Nạp theo lô toàn tệp (`method1_standard.py`) | Cách 2: Nạp cuốn chiếu theo Chunk (`method2_optimized.py`) |
| :--- | :--- | :--- |
| **Chiến lược đọc dữ liệu** | Đọc toàn bộ từng tệp CSV vào RAM (`pd.read_csv`), xử lý danh mục và ánh xạ khóa ngoại một lần cho mỗi tệp. | Đọc cuốn chiếu từng lô nhỏ `100,000` dòng (`chunksize=100_000`), cập nhật danh mục liên tục qua từng lô. |
| **Cấu hình SQLite** | Cấu hình mặc định (`synchronous = FULL`, `journal_mode = DELETE`). | Tắt ghi nhật ký đĩa tạm thời (`PRAGMA synchronous = OFF`, `journal_mode = MEMORY`). |
| **Tổng số dòng đã nạp** | **4,561,053 dòng** | **4,561,053 dòng** |
| **Thời gian thực thi** | **116.82 giây** | **155.29 giây** |

### Phân tích & Đánh giá kết quả thực nghiệm
* **Về tốc độ thực thi:** Trên tập dữ liệu 4.56 triệu dòng với cấu hình máy tính hiện tại đủ bộ nhớ RAM, **Cách 1 nhanh hơn Cách 2 khoảng 38.47 giây (nhanh hơn ~25%)**. Nguyên nhân là do Cách 1 chỉ thực hiện thao tác lọc trùng (`drop_duplicates`) và truy vấn ánh xạ khóa ngoại (`SELECT` từ bảng `locations`) đúng **2 lần** (mỗi tệp 1 lần). Trong khi đó, Cách 2 chia thành **46 lô (chunks)** nên phải thực hiện thao tác đồng bộ và truy vấn lại bảng `locations` tới 46 lần, tạo ra chi phí lặp (overhead) lớn hơn lợi ích từ việc tối ưu `PRAGMA`.
* **Về khả năng mở rộng & An toàn bộ nhớ (RAM):** Mặc dù chậm hơn một chút ở quy mô 4.5 triệu dòng, **Cách 2 vượt trội về mức tiêu thụ bộ nhớ ổn định (O(1) theo kích thước chunk)**. Nếu kích thước dữ liệu tăng lên hàng chục hoặc hàng trăm triệu dòng vượt quá dung lượng RAM vật lý, Cách 1 sẽ gặp lỗi tràn bộ nhớ (`MemoryError`), còn Cách 2 vẫn hoạt động ổn định.

---

## 4. Hướng dẫn chạy chương trình

### Bước 1: Clone mã nguồn và khởi tạo môi trường ảo (khuyên dùng)
Mở Terminal tại thư mục dự án và chạy các lệnh sau để tạo môi trường độc lập, tránh xung đột thư viện:

        git clone https://github.com/Nocc-244/chicago-crime-db.git
        cd chicago-crime-db
        python -m venv .venv
        .venv\Scripts\activate

### Bước 2: Cài đặt thư viện bên thứ ba
Cài đặt `pandas` (lệnh này sẽ tự động cài đặt kèm thư viện tính toán nền `numpy`; các thư viện còn lại như `sqlite3`, `glob`, `os`, `time` đã có sẵn trong Python):

        pip install pandas

### Bước 3: Chuẩn bị thư mục dữ liệu đầu vào
Vì các tệp dữ liệu gốc có dung lượng lớn (~1 GB) nên không được đính kèm trực tiếp trên GitHub. Để chạy thử nghiệm:
1. Tạo một thư mục mới đặt tên chính xác là `data` ngay tại thư mục gốc của dự án (`chicago-crime-db/data/`).
2. Truy cập [Crimes in Chicago trên Kaggle](https://www.kaggle.com/datasets/currie32/crimes-in-chicago/data?select=Chicago_Crimes_2008_to_2011.csv), tải về và giải nén 2 tệp CSV sau vào bên trong thư mục `data/`:
   - `Chicago_Crimes_2005_to_2007.csv`
   - `Chicago_Crimes_2008_to_2011.csv`

Cấu trúc thư mục sau khi chuẩn bị xong sẽ như sau:

        chicago-crime-db/
        ├── data/
        │   ├── Chicago_Crimes_2005_to_2007.csv
        │   └── Chicago_Crimes_2008_to_2011.csv
        ├── method1_standard.py
        ├── method2_optimized.py
        ├── .gitignore
        └── README.md

### Bước 4: Thực thi và kiểm tra kết quả
Chạy lần lượt hai kịch bản bằng Python:

        python method1_standard.py
        python method2_optimized.py

Sau khi chạy hoàn tất, hệ thống sẽ tự động sinh ra 2 tệp cơ sở dữ liệu