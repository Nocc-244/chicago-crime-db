import sqlite3
import pandas as pd
import glob
import time
import os

DB_PATH = "chicago_crime_m1.db"
CSV_FILES = glob.glob("data/*.csv")

def init_db(conn):
    cursor = conn.cursor()
    # Tạo 3 bảng có khóa chính, khóa ngoại đúng chuẩn CSDL quan hệ
    cursor.executescript("""
        DROP TABLE IF EXISTS incidents;
        DROP TABLE IF EXISTS crime_types;
        DROP TABLE IF EXISTS locations;

        CREATE TABLE crime_types (
            iucr TEXT PRIMARY KEY,
            primary_type TEXT,
            description TEXT
        );

        CREATE TABLE locations (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            block TEXT,
            location_description TEXT,
            district TEXT,
            UNIQUE(block, location_description, district)
        );

        CREATE TABLE incidents (
            id INTEGER PRIMARY KEY,
            case_number TEXT,
            incident_date TEXT,
            arrest INTEGER,
            domestic INTEGER,
            year INTEGER,
            iucr TEXT,
            location_id INTEGER,
            FOREIGN KEY (iucr) REFERENCES crime_types(iucr),
            FOREIGN KEY (location_id) REFERENCES locations(location_id)
        );
    """)
    conn.commit()

def run_method_1():
    if not CSV_FILES:
        print("Không tìm thấy file CSV nào trong thư mục data/!")
        return

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cursor = conn.cursor()

    start_time = time.time()
    total_rows = 0

    for file_path in CSV_FILES:
        print(f"[Cách 1] Đang đọc file: {file_path}...")
        # Đọc toàn bộ file vào RAM
        df = pd.read_csv(file_path, on_bad_lines='skip', low_memory=False)
        
        # Nạp bảng phụ 1: crime_types
        types_df = df[['IUCR', 'Primary Type', 'Description']].drop_duplicates(subset=['IUCR']).dropna(subset=['IUCR'])
        for _, row in types_df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO crime_types (iucr, primary_type, description) VALUES (?, ?, ?)",
                (str(row['IUCR']), str(row['Primary Type']), str(row['Description']))
            )

        # Nạp bảng phụ 2: locations
        locs_df = df[['Block', 'Location Description', 'District']].drop_duplicates().fillna("UNKNOWN")
        for _, row in locs_df.iterrows():
            cursor.execute(
                "INSERT OR IGNORE INTO locations (block, location_description, district) VALUES (?, ?, ?)",
                (str(row['Block']), str(row['Location Description']), str(row['District']))
            )
        conn.commit()

        # Lấy map location_id để gán khóa ngoại
        cursor.execute("SELECT location_id, block, location_description, district FROM locations")
        loc_map = {(r[1], r[2], r[3]): r[0] for r in cursor.fetchall()}

        # Nạp bảng chính: incidents
        df['Block'] = df['Block'].fillna("UNKNOWN")
        df['Location Description'] = df['Location Description'].fillna("UNKNOWN")
        df['District'] = df['District'].fillna("UNKNOWN")

        records = []
        for row in df[['ID', 'Case Number', 'Date', 'Arrest', 'Domestic', 'Year', 'IUCR', 'Block', 'Location Description', 'District']].itertuples(index=False):
            loc_id = loc_map.get((str(row[7]), str(row[8]), str(row[9])))
            records.append((
                row[0], str(row[1]), str(row[2]), int(bool(row[3])), int(bool(row[4])),
                row[5], str(row[6]), loc_id
            ))

        cursor.executemany(
            "INSERT OR IGNORE INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            records
        )
        conn.commit()
        total_rows += len(df)
        print(f" -> Đã nạp xong {len(df):,} dòng từ {os.path.basename(file_path)}")

    elapsed = time.time() - start_time
    conn.close()
    print(f"\n[HOÀN THÀNH CÁCH 1] Tổng số dòng: {total_rows:,} | Thời gian: {elapsed:.2f} giây")

if __name__ == "__main__":
    run_method_1()