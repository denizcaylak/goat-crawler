# https://github.com/denizcaylak/goat-crawler
import asyncio
import urllib.request
import urllib.parse
from html.parser import HTMLParser
import db

class LinkExtractor(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self.text_content = []
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.in_title = True
        elif tag == 'a':
            for attr, value in attrs:
                if attr == 'href':
                    full_url = urllib.parse.urljoin(self.base_url, value)
                    full_url, _ = urllib.parse.urldefrag(full_url)
                    if full_url.startswith('http'):
                        self.links.append(full_url)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self.in_title:
            self.title += text + " "
        else:
            self.text_content.append(text)

    def get_links(self):
        return self.links

    def get_content(self):
        return self.title.strip(), " ".join(self.text_content)

class Crawler:
    def __init__(self, max_workers=50):
        self.visited = set()
        self.visited_lock = asyncio.Lock()
        self.queue = asyncio.Queue(maxsize=100)
        self.semaphore = asyncio.Semaphore(10)
        self.conn = db.get_connection()
        self.max_workers = max_workers
        self.workers = []
        
        db.init_db()
        self.load_state()

    def load_state(self):
        self.visited = db.load_visited()
        queued_items = db.load_queue()
        for i, item in enumerate(queued_items):
            if i < self.queue.maxsize:
                self.queue.put_nowait({
                    'url': item['url'],
                    'origin': item['origin'],
                    'depth': item['depth'],
                    'k': item['depth'] + 1,
                    'job_id': item.get('job_id')
                })

    async def clear(self):
        for w in self.workers:
            w.cancel()
        await asyncio.sleep(0.1)
        
        async with self.visited_lock:
            self.visited.clear()
            self.queue = asyncio.Queue(maxsize=100)
                    
        self.workers = [asyncio.create_task(self.worker()) for _ in range(self.max_workers)]

    async def _enqueue(self, item, capacity=100):
        while self.queue.qsize() >= capacity:
            await asyncio.sleep(0.5)
        await self.queue.put(item)

    async def add_seed(self, url, k, job_id=None, hit_rate=0, max_urls=0, capacity=100):
        if not job_id:
            job_id = db.insert_job(self.conn, url, k, hit_rate)
            
        async with self.visited_lock:
            if url not in self.visited:
                self.visited.add(url)
                db.insert_page(self.conn, url, "", "", "", 0, 'queued', job_id)
                db.insert_log(self.conn, job_id, 'INFO', f'Added root seed target >> {url}')
                asyncio.create_task(self._enqueue({
                    'url': url,
                    'origin': "",
                    'depth': 0,
                    'k': k,
                    'job_id': job_id,
                    'hit_rate': hit_rate,
                    'max_urls': max_urls,
                    'capacity': capacity
                }, capacity))
        return job_id

    def fetch_sync(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': 'GoogleInAnAfternoon/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                content_type = response.getheader('Content-Type')
                if content_type and 'text/html' not in content_type:
                    return None
                return response.read().decode('utf-8', errors='ignore')
        except Exception:
            return None

    async def worker(self):
        try:
            while True:
                item = await self.queue.get()
                url = item['url']
                origin = item['origin']
                depth = item['depth']
                k = item['k']
                job_id = item.get('job_id')
                hit_rate = item.get('hit_rate', 0)
                max_urls = item.get('max_urls', 0)
                capacity = item.get('capacity', 100)
                
                if job_id:
                    job_status = db.get_job_status(job_id)
                    if job_status == 'stopped':
                        self.queue.task_done()
                        continue
                    while job_status == 'paused':
                        await asyncio.sleep(1)
                        job_status = db.get_job_status(job_id)
                        if job_status == 'stopped':
                            break
                    if job_status == 'stopped':
                        self.queue.task_done()
                        continue
                
                if max_urls > 0:
                    count = db.get_job_crawled_count(job_id)
                    if count >= max_urls:
                        db.update_status(self.conn, url, 'skipped')
                        db.insert_log(self.conn, job_id, 'WARNING', f'Skipped {url} due to Max URL limit reached')
                        self.queue.task_done()
                        continue
                        
                if hit_rate > 0:
                    await asyncio.sleep(hit_rate)
                
                async with self.semaphore:
                    db.update_status(self.conn, url, 'crawling')
                    db.insert_log(self.conn, job_id, 'INFO', f'Executing fetch on {url} (Depth {depth})')
                    html = await asyncio.to_thread(self.fetch_sync, url)
                    
                if html:
                    extractor = LinkExtractor(url)
                    try:
                        extractor.feed(html)
                        title, content = extractor.get_content()
                        links = extractor.get_links()
                        
                        db.insert_page(self.conn, url, title, content, origin, depth, 'crawled', job_id)
                        db.insert_log(self.conn, job_id, 'SUCCESS', f'Crawled {url}! Found {len(links)} links')
                        
                        if depth < k:
                            for link in links:
                                async with self.visited_lock:
                                    if link not in self.visited:
                                        self.visited.add(link)
                                        db.insert_page(self.conn, link, "", "", url, depth+1, 'queued', job_id)
                                    else:
                                        continue
                                
                                asyncio.create_task(self._enqueue({
                                    'url': link,
                                    'origin': url,
                                    'depth': depth + 1,
                                    'k': k,
                                    'job_id': job_id,
                                    'hit_rate': hit_rate,
                                    'max_urls': max_urls,
                                    'capacity': capacity
                                }, capacity))
                                
                    except Exception as e:
                        db.update_status(self.conn, url, 'error')
                        db.insert_log(self.conn, job_id, 'ERROR', f'Parse error on {url} | {str(e)}')
                else:
                    db.update_status(self.conn, url, 'error')
                    db.insert_log(self.conn, job_id, 'ERROR', f'Failed network trace for {url}')
                    
                self.queue.task_done()
        except asyncio.CancelledError:
            raise

    async def monitor_jobs(self):
        while True:
            await asyncio.sleep(2)
            try:
                jobs = db.get_jobs()
                for job in jobs:
                    if job['status'] == 'running':
                        count = db.get_active_page_count(job['id'])
                        if count == 0:
                            db.update_job_status(job['id'], 'completed')
            except Exception:
                pass

    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.workers = [asyncio.create_task(self.worker()) for _ in range(self.max_workers)]
        asyncio.create_task(self.monitor_jobs())
        while True:
            await asyncio.sleep(3600)
