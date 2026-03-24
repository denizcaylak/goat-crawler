# https://github.com/denizcaylak/goat-crawler
import threading
import asyncio
import time
from indexer import Crawler
from cli import SearchCLI
from server import start_server_in_thread

def run_crawler(crawler):
    asyncio.run(crawler.run())

if __name__ == '__main__':
    # Initialize crawler
    crawler = Crawler(max_workers=10)
    
    # Run asyncio loop in background thread
    t = threading.Thread(target=run_crawler, args=(crawler,), daemon=True)
    t.start()
    
    # Wait for the loop to initialize
    while not hasattr(crawler, 'loop'):
        time.sleep(0.1)
        
    # Start web server
    start_server_in_thread(crawler, port=3600)
    
    try:
        # Start the synchronous CLI REPL on the main thread
        SearchCLI(crawler).cmdloop()
    except KeyboardInterrupt:
        print("\nShutting down...")
