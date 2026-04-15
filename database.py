import sqlite3
import os
import csv
from config import DB_FILE

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS minifig_map
                     (rb_id TEXT PRIMARY KEY, ext_id TEXT, name TEXT, img TEXT, year TEXT, parts INTEGER)''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Init Error: {e}")

def get_fig_from_db(query):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT rb_id, ext_id, name, img, year, parts FROM minifig_map WHERE rb_id=? OR ext_id=?", (query, query))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                'set_num': row[0],
                'display_id': row[1] if row[1] else row[0],
                'name': row[2],
                'set_img_url': row[3],
                'year': row[4],
                'num_parts': row[5]
            }
        return None
    except: return None

def save_fig_to_db(rb_id, ext_id, name, img, year, parts):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO minifig_map (rb_id, ext_id, name, img, year, parts) VALUES (?, ?, ?, ?, ?, ?)",
                  (rb_id, ext_id, name, img, year, parts))
        conn.commit()
        conn.close()
    except: pass

def get_real_max_fig_id():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT rb_id FROM minifig_map WHERE rb_id LIKE 'fig-%'")
        max_id = 0
        for row in c.fetchall():
            try:
                curr = int(row[0].replace('fig-', ''))
                if curr > max_id: max_id = curr
            except: pass
        conn.close()
        return max_id
    except: return 0

def get_valid_count():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM minifig_map WHERE ext_id IS NOT NULL AND ext_id != ''")
        cnt = c.fetchone()[0]
        conn.close()
        return cnt
    except: return 0

def update_crawler_progress(current, total):
    pass

def export_db_to_csv():
    try:
        csv_file = "/downloads/lego_export.csv"
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM minifig_map")
        rows = c.fetchall()
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['rb_id', 'ext_id', 'name', 'img', 'year', 'parts'])
            writer.writerows(rows)
        conn.close()
        return csv_file
    except: return None

def normalize_query_id(q):
    return q.strip()
