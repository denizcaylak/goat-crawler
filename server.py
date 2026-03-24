import http.server
import json
import urllib.parse
import threading
import db

class APIHandler(http.server.BaseHTTPRequestHandler):
    crawler = None 
    
    def log_message(self, format, *args):
        pass
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/':
            try:
                with open('index.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_json({"error": "index.html not found"}, 404)
                
        elif path.startswith('/api/status'):
            stats = db.get_stats()
            queue_size = self.crawler.queue.qsize() if self.crawler else 0
            active_workers = 10 - self.crawler.semaphore._value if hasattr(self.crawler, 'semaphore') else 0
            
            self._send_json({
                "stats": stats,
                "queue_size": queue_size,
                "active_workers": max(0, active_workers)
            })
            
        elif path.startswith('/search') or path.startswith('/api/search'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            q = query.get('query', query.get('q', ['']))[0]
            if not q:
                self._send_json({"error": "Empty query"}, 400)
                return
            
            hw_mode = 'sortBy' in query or path.startswith('/search')
            results = db.run_search(q, hw_mode=hw_mode)
            self._send_json({"results": results})
            
        elif path.startswith('/api/jobs/'):
            try:
                job_id = int(path.split('/')[-1])
                details = db.get_job_details(job_id)
                self._send_json(details)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
                
        elif path.startswith('/api/jobs'):
            jobs = db.get_jobs()
            self._send_json({"jobs": jobs})
            
        else:
            self._send_json({"error": "Not found"}, 404)
            
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/api/clear':
            import asyncio
            if hasattr(self.crawler, 'loop') and self.crawler.loop:
                async def safe_clear():
                    await self.crawler.clear()
                    db.clear_all()
                asyncio.run_coroutine_threadsafe(safe_clear(), self.crawler.loop)
            self._send_json({"message": "Database and state cleared synchronously"})
            
        elif path.startswith('/api/jobs/') and '/action' in path:
            try:
                job_id = int(path.split('/')[3])
                content_length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(content_length).decode('utf-8'))
                action = data.get('action')
                
                if action == 'pause':
                    db.update_job_status(job_id, 'paused')
                elif action == 'resume':
                    db.update_job_status(job_id, 'running')
                elif action == 'stop':
                    db.update_job_status(job_id, 'stopped')
                    
                self._send_json({"message": f"Job {job_id} {action}ed"})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
                
        elif path == '/api/index':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json({"error": "Empty body"}, 400)
                return
                
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url')
                depth = int(data.get('depth', 1))
                hit_rate = float(data.get('hit_rate', 0))
                max_urls = int(data.get('max_urls', 0))
                capacity = int(data.get('capacity', 100))
                if not url:
                    self._send_json({"error": "URL required"}, 400)
                    return
                    
                import asyncio
                if hasattr(self.crawler, 'loop') and self.crawler.loop:
                    future = asyncio.run_coroutine_threadsafe(self.crawler.add_seed(url, depth, None, hit_rate, max_urls, capacity), self.crawler.loop)
                    job_id = future.result(timeout=5)
                    self._send_json({"message": f"Added {url} to queue", "job_id": job_id})
                else:
                    self._send_json({"error": "Crawler not ready"}, 503)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Not found"}, 404)

def run_server(crawler, port=8000):
    APIHandler.crawler = crawler
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, APIHandler)
    print(f"\n[Web UI] Dashboard available at http://localhost:{port}")
    httpd.serve_forever()

def start_server_in_thread(crawler, port=8000):
    t = threading.Thread(target=run_server, args=(crawler, port), daemon=True)
    t.start()
    return t
