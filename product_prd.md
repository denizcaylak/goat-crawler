# Product Requirements Document (PRD): GOAT Crawler

## 1. Technical Requirements (Indexer)

### Recursive Crawling
- The crawler must initiate from an origin URL and recursively traverse discovered links up to a maximum user-defined depth `k`.

### Uniqueness
- The system must explicitly implement a `Visited` set architecture to mathematically guarantee that absolutely no URL page is crawled twice within the same job cycle.

### Back Pressure
- The system must natively manage its own traffic scale and memory footprint.
- Built-in mechanisms must throttle the maximum rate of work, enforce limits on enqueue depths, and allow for dynamically assigned temporal Hit Rate delays.

### Native Focus Constraint
- The application environment requires strict adherence to language-native functionalities exclusively (e.g., utilizing `urllib`, `html.parser`, `sqlite3`, `http.server`, and `asyncio`).
- Third-party web scraping and networking suites such as Scrapy, Beautiful Soup, or Requests are strictly forbidden.

## 2. Technical Requirements (Searcher)

### Query Engine
- The integrated search API must resolve search requests and return an array of mappings specifically containing at least three core variables: `(relevant_url, origin_url, depth)`.

### Live Indexing
- Database configurations must explicitly allow the Search Engine to execute user queries successfully concurrently while the Indexer actively writes newly discovered pages to the data tables. 

### Concurrency
- The system must be designed leveraging intrinsically thread-safe data structures.
- It must explicitly deploy Mutex locks (e.g., `asyncio.Lock`), thread-safe asynchronous channels/queues, and connection-isolated database cursors to absolutely prevent memory corruption and race conditions under heavy loads.

### Relevancy
- The search subsystem must define a computational heuristic mapping (such as evaluating explicit keyword frequencies and multiplying weights for explicit Title matches) to natively rank and sort the URL query results.

## 3. UI / CLI Requirements

### Real-Time Dashboard
- The application must generate a frontend user interface dashboard serving as a control panel to monitor the live operational status of the cluster in real-time.

### Mandatory Tracking Metrics
The dashboard visualizers must actively poll and accurately report the following internal vectors:
1. **Current Indexing Progress**: Total URLs successfully processed vs. natively queued pages.
2. **Current Queue Depth**: Aggregate memory backlog sizes.
3. **Back-pressure / Throttling Status**: A visual reflection of live semaphore slots or internal worker allocations actively pulling memory against their limits.

## 4. Persistence (Bonus Requirements)

### Interruption Resumability
- The architectural design must natively ensure that the system can be violently interrupted (crashes, terminal shut-downs) and later safely restarted without arbitrarily forcing the operator to restart all deep crawl jobs from scratch. 
- It must silently persist states to memory layers capable of successfully re-building queue states natively upon reboot.