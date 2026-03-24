import os
import db

def generate():
    os.makedirs('data/storage', exist_ok=True)
    conn = db.get_connection()
    cursor = conn.execute('SELECT url, content, origin_url, depth FROM pages')
    
    with open('data/storage/p.data', 'w', encoding='utf-8') as f:
        for row in cursor.fetchall():
            url, content, origin_url, depth = row
            if not origin_url:
                origin_url = "None"
            words = (content or "").lower().split()
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            for word, freq in word_freq.items():
                f.write(f"{word} {url} {origin_url} {depth} {freq}\n")
    conn.close()

if __name__ == '__main__':
    generate()
    print("Generated data/storage/p.data")
