import cmd
import db
import asyncio

class SearchCLI(cmd.Cmd):
    intro = 'Welcome to "Goat Crawler". Type "help" or "?" to list commands.\n'
    prompt = '(search) '

    def __init__(self, crawler):
        super().__init__()
        self.crawler = crawler

    def do_index(self, arg):
        """index <url> <depth>\nAdds a new URL and maximum depth to the crawler queue."""
        args = arg.split()
        if len(args) != 2:
            print("Usage: index <url> <depth>")
            return
            
        url, depth_str = args
        try:
            depth = int(depth_str)
        except ValueError:
            print("Depth must be an integer.")
            return
            
        if hasattr(self.crawler, 'loop') and self.crawler.loop:
            asyncio.run_coroutine_threadsafe(self.crawler.add_seed(url, depth), self.crawler.loop)
            print(f"Added {url} with max depth {depth} to index queue.")
        else:
            print("Crawler loop not running yet.")

    def do_search(self, arg):
        """search <query>\nSearches the indexed pages using keyword frequency relevancy."""
        if not arg:
            print("Usage: search <query>")
            return
            
        results = db.run_search(arg)
        if not results:
            print("No results found.")
            return
            
        print(f"Found {len(results)} results:")
        for r in results:
            print(f"URL: {r[0]} | Origin: {r[1]} | Depth: {r[2]}")

    def do_status(self, arg):
        """status\nPrints the current indexing status counts."""
        stats = db.get_stats()
        if not stats:
            print("No pages in database.")
            return
            
        for status, count in stats.items():
            print(f"{status.capitalize()}: {count}")

    def do_exit(self, arg):
        """exit\nExit the CLI and stop the crawler."""
        print("Shutting down...")
        return True
        
    def default(self, line):
        if line == 'EOF':
            print("Shutting down...")
            return True
        super().default(line)
