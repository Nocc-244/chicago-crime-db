import sqlite3
import pandas as pd
import glob
import time
import os

DB_PATH = "chicago_crime_m2.db"
CSV_FILES = glob.glob("data/*.csv")
CHUNK_SIZE = 100_000

def init_db(conn):
    cursor = conn.cursor()
    # Tối ưu hóa hiệu năng ghi của SQLite
    cursor.executescript("""
        PRAGMA synchronous = OFF;
        PRAGMA journal_mode = MEMORY;
        PRAGMA cache_size = 100000;
        PRAGMA temp_store = MEMORY;

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

def run_method_2():
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
    loc_map = {}

    for file_path in CSV_FILES:
        print(f"[Cách 2 - Tối ưu] Đang xử lý theo lô file: {file_path}...")
        
        # Đọc cuốn chiếu từng chunk 100,000 dòng
        for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE, on_bad_lines='skip', low_memory=False):
            # 1. Nạp nhanh bảng crime_types
            types_records = list(
                chunk[['IUCR', 'Primary Type', 'Description']]
                .drop_duplicates(subset=['IUCR'])
                .dropna(subset=['IUCR'])
                .astype(str)
                .itertuples(index=False, name=None)
            )
            cursor.executemany("INSERT OR IGNORE INTO crime_types VALUES (?, ?, ?)", types_records)

            # 2. Nạp nhanh bảng locations
            chunk['Block'] = chunk['Block'].fillna("UNKNOWN").astype(str)
            chunk['Location Description'] = chunk['Location Description'].fillna("UNKNOWN").astype(str)
            chunk['District'] = chunk['District'].fillna("UNKNOWN").astype(str)

            unique_locs = chunk[['Block', 'Location Description', 'District']].drop_duplicates()
            new_locs = [
                (r[0], r[1], r[2]) 
                for r in unique_locs.itertuples(index=False, name=None) 
                if (r[0], r[1], r[2]) not in loc_map
            ]
            if new_locs:
                cursor.executemany(
                    "INSERT OR IGNORE INTO locations (block, location_description, district) VALUES (?, ?, ?)",
                    new_locs
                )
                cursor.execute("SELECT location_id, block, location_description, district FROM locations")
                loc_map = {(r[1], r[2], r[3]): r[0] for r in cursor.fetchall()}

            # 3. Nạp hàng loạt bảng incidents
            incident_records = [
                (
                    r[0], str(r[1]), str(r[2]), int(bool(r[3])), int(bool(r[4])),
                    r[5], str(r[6]), loc_map.get((r[7], r[8], r[9]))
                )
                for r in chunk[['ID', 'Case Number', 'Date', 'Arrest', 'Domestic', 'Year', 'IUCR', 'Block', 'Location Description', 'District']].itertuples(index=False, name=None)
            ]
            cursor.executemany(
                "INSERT OR IGNORE INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                incident_records
            )
            conn.commit()
            total_rows += len(chunk)

        print(f" -> Hoàn tất file {os.path.basename(file_path)} (Tổng lũy kế: {total_rows:,} dòng)")

    elapsed = time.time() - start_time
    conn.close()
    print(f"\n[HOÀN THÀNH CÁCH 2] Tổng số dòng: {total_rows:,} | Thời gian: {elapsed:.2f} giây")

if __name__ == "__main__":
    run_method_2()