import sqlite3
import os

DB_PATH = 'crawler.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def init_db():
    conn = get_connection()
    try:
        conn.execute('ALTER TABLE pages ADD COLUMN job_id INTEGER')
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute('ALTER TABLE crawl_jobs ADD COLUMN hit_rate REAL DEFAULT 0')
    except sqlite3.OperationalError:
        pass
        
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            url TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            origin_url TEXT,
            depth INTEGER,
            status TEXT,
            job_id INTEGER
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS crawl_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seed_url TEXT,
            max_depth INTEGER,
            hit_rate REAL DEFAULT 0,
            status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            level TEXT,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def clear_all():
    conn = get_connection()
    conn.execute('DELETE FROM pages')
    conn.execute('DELETE FROM crawl_jobs')
    conn.execute('DELETE FROM logs')
    try:
        conn.execute('DELETE FROM sqlite_sequence WHERE name IN ("crawl_jobs", "logs")')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def get_active_page_count(job_id):
    conn = get_connection()
    cursor = conn.execute("SELECT count(*) FROM pages WHERE job_id = ? AND status IN ('queued', 'crawling')", (job_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_job_crawled_count(job_id):
    conn = get_connection()
    cursor = conn.execute("SELECT count(*) FROM pages WHERE job_id = ? AND status = 'crawled'", (job_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def insert_job(conn, seed_url, max_depth, hit_rate=0):
    cursor = conn.execute('INSERT INTO crawl_jobs (seed_url, max_depth, hit_rate, status) VALUES (?, ?, ?, ?)', (seed_url, max_depth, hit_rate, 'running'))
    conn.commit()
    return cursor.lastrowid

def get_jobs():
    conn = get_connection()
    cursor = conn.execute('SELECT id, seed_url, max_depth, status, created_at, hit_rate FROM crawl_jobs ORDER BY id DESC LIMIT 20')
    jobs = [{'id': row[0], 'seed_url': row[1], 'max_depth': row[2], 'status': row[3], 'created_at': row[4], 'hit_rate': row[5]} for row in cursor.fetchall()]
    conn.close()
    return jobs

def get_job_details(job_id):
    conn = get_connection()
    cursor = conn.execute('SELECT seed_url, max_depth, hit_rate, status, created_at FROM crawl_jobs WHERE id = ?', (job_id,))
    job_row = cursor.fetchone()
    if not job_row:
        conn.close()
        return {}
    
    meta = {
        'seed_url': job_row[0], 'max_depth': job_row[1], 'hit_rate': job_row[2],
        'status': job_row[3], 'created_at': job_row[4]
    }
    
    cursor = conn.execute('SELECT url, status, depth FROM pages WHERE job_id = ? ORDER BY depth ASC, url ASC', (job_id,))
    all_pages = [{'url': row[0], 'status': row[1], 'depth': row[2]} for row in cursor.fetchall()]
    
    cursor = conn.execute('SELECT level, message, created_at FROM logs WHERE job_id = ? ORDER BY id DESC LIMIT 300', (job_id,))
    logs = [{'level': row[0], 'message': row[1], 'created_at': row[2]} for row in cursor.fetchall()]
    
    urls_visited = sum(1 for p in all_pages if p['status'] == 'crawled')
    queue_size = sum(1 for p in all_pages if p['status'] == 'queued')
    last_update = logs[0]['created_at'] if logs else meta['created_at']
    
    conn.close()
    return {'meta': meta, 'pages': all_pages, 'logs': logs, 'urls_visited': urls_visited, 'queue_size': queue_size, 'last_update': last_update}

def get_job_status(job_id):
    conn = get_connection()
    cursor = conn.execute('SELECT status FROM crawl_jobs WHERE id = ?', (job_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 'stopped'

def update_job_status(job_id, status):
    conn = get_connection()
    conn.execute('UPDATE crawl_jobs SET status = ? WHERE id = ?', (status, job_id))
    conn.commit()
    conn.close()

def insert_log(conn, job_id, level, message):
    if job_id:
        conn.execute('INSERT INTO logs (job_id, level, message) VALUES (?, ?, ?)', (job_id, level, message))
        conn.commit()

def insert_page(conn, url, title, content, origin_url, depth, status, job_id=None):
    conn.execute('''
        INSERT OR REPLACE INTO pages (url, title, content, origin_url, depth, status, job_id)
        VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, (SELECT job_id FROM pages WHERE url = ?)))
    ''', (url, title, content, origin_url, depth, status, job_id, url))
    conn.commit()

def update_status(conn, url, status):
    conn.execute('''
        UPDATE pages SET status = ? WHERE url = ?
    ''', (status, url))
    conn.commit()

def load_visited():
    conn = get_connection()
    cursor = conn.execute('SELECT url FROM pages')
    visited = {row[0] for row in cursor.fetchall()}
    conn.close()
    return visited

def load_queue():
    conn = get_connection()
    cursor = conn.execute('SELECT url, origin_url, depth, job_id FROM pages WHERE status = ?', ('queued',))
    queued = [{'url': row[0], 'origin': row[1], 'depth': row[2], 'job_id': row[3]} for row in cursor.fetchall()]
    conn.close()
    return queued

def get_stats():
    conn = get_connection()
    cursor = conn.execute("SELECT status, count(*) FROM pages GROUP BY status")
    stats = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return stats

def run_search(query, hw_mode=False):
    conn = get_connection()
    q = query.lower()
    cursor = conn.execute('''
        SELECT url, title, content, origin_url, depth FROM pages
        WHERE lower(title) LIKE ? OR lower(content) LIKE ?
    ''', (f'%{q}%', f'%{q}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    ranked = []
    for row in results:
        url, title, content, origin_url, depth = row
        words = (content or "").lower().split()
        frequency = words.count(q)
        
        if hw_mode:
            score = (frequency * 10) + 1000 - (depth * 5)
            if frequency > 0:
                ranked.append((score, {"url": url, "origin": origin_url, "depth": depth, "frequency": frequency, "relevance_score": score}))
        else:
            title_count = (title or "").lower().count(q)
            content_count = (content or "").lower().count(q)
            score = (title_count * 5) + content_count
            if score > 0:
                ranked.append((score, {"url": url, "origin": origin_url, "depth": depth, "frequency": score}))
            
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in ranked]
