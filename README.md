# 🐐 GOAT Crawler

A high-performance, fully concurrent web crawling platform and search engine built entirely with **Python's Standard Library**. Featuring real-time monitoring, intelligent search scoring, and a beautiful glassmorphic web interface. Created by **Remzi Deniz Çaylak**.

## 🌟 Features

- **Asynchronous Web Crawler** with configurable depth, hit rate limiting, and queue capacities.
- **Zero External Dependencies** - Built purely with `asyncio`, `sqlite3`, and `http.server`.
- **Real-time Status Dashboard** with live metric updates, tracking network utilization and errors.
- **Advanced Search Engine** with keyword relevance ranking, frequency heuristics, and JS pagination.
- **SQLite WAL Storage** providing absolute concurrency without thread-locking corruption.
- **Pause/Resume/Stop** native task controls directly embedded within the Job tracking modals.
- **Automatic Resume States** natively reconstructing crawler structures seamlessly upon terminal restarts.
- **Native Rate Limiting & Semaphore Back-pressure** preventing network socket overflowing.

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Any modern Web browser

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/denizcaylak/goat-crawler.git
   cd goat-crawler
   ```

2. **Verify Dependencies:**
   ```bash
   # Note: No external library installation needed!
   cat requirements.txt
   ```

3. **Start the GOAT Crawler Server:**
   ```bash
   python main.py
   ```
   
   The server daemon will automatically bind and start on `http://localhost:3600`.

4. **Access the Dashboard:**
   Open `http://localhost:3600/` in any web browser.

## 📖 Usage Guide

### Deploying a Crawl Job

1. Navigate to the **Deploy Crawl Job** section.
2. Fill in the network parameters:
   - **Target Root URL** (*Required*): Starting coordinate for crawling (e.g., `https://example.com/`)
   - **Max Depth** (*Required*): Absolute depth limit (1-10)
   - **Hit Rate (s)**: Artificial temporal delay between fetch loops (e.g., `0.5` seconds)
   - **Max URLs**: Absolute limit on links visited per job
   - **Queue Capacity**: Memory backlog cap preventing payload explosion.
3. Click **"Queue Network Thread"** to fire the asynchronous engine!

### Monitoring Crawls

- **Live System Status**: The top UI metrics automatically calculate queued, actively crawling, crawled, error, and backlog states.
- **See Details Window**: Click on any running historical trace below to view intensive metrics (Origin URL, Score tracking, Visited sizes, Live task queues, and Trace Execution logs).
- **Task Constraints**: While a job is assigned, safely press **Pause**, **Resume**, or **Stop** natively from inside the modal!

### Search Engine

1. Let the engine index content dynamically into the backing SQLite memory space.
2. Scroll to the **Search Engine** header.
3. Search target keywords. Output is mathematically paginated strictly into exactly 10-result blocks.
4. Each Result lists the targeted URL, recursive Depth origin, matched Search criteria, and mathematical Frequency hit rates. The search relevance scoring uses the homework formula: `(frequency x 10) + 1000 - (depth x 5)`.

### Exporting the Inverted Index

To export the final inverted index data for your assignment, run:

```bash
python generate_pdata.py
```

This reads the crawled pages from the database and writes the text index to `data/storage/p.data`.

## 📁 System Architecture

```text
goat-crawler/
├── main.py          # 🚀 Main Entry Point Daemon
├── server.py        # 🕸️ Native http.server API implementation
├── indexer.py       # 🕷️ Asyncio Core Crawler Engine
├── db.py            # 💾 SQLite WAL transactional abstractions
├── generate_pdata.py# 🗃️ Script to export p.data inverted index
├── index.html       # 🎨 Front-End Interface (CSS/JS natively baked)
├── requirements.txt # 📋 Dependency Log
└── README.md        # 📖 Documentation
```

## ⚙️ Configuration & Concurrency Details

### Core Sub-systems

1. **Crawler Engine**: Thread-safe `asyncio.Queue` passing links into exact arrays of `Semaphore(10)` bound network fetching workers, inherently guaranteeing 10 socket caps natively.
2. **Hit Search Algorithm**: Calculates heuristic values relying rigorously against combined title (`x5`) multiplier against organic text body references.
3. **Database Architecture**: Operates `check_same_thread=False` unlocking `sqlite3` PRAGMA `WAL` properties ensuring the Dashboard reading actions never intercept background crawler writes!

## 🚨 Troubleshooting & Interruption

**Network Overwhelming/Bans:**
If target servers block your host, actively increase the **Hit Rate (s)** when deploying your URLs explicitly to `0.5` or `1.5` delays per fetch loop to throttle explicitly organic bot behaviors!

**Erase States:**
If your queue becomes impossibly saturated across jobs, click the red **Erase System State** button. The engine strictly `cancels()` all running coroutine threads synchronously, safely obliterating SQL sequences, and starting clean at Job `#1`.

## 📜 License

This project operates openly. Modify it exclusively for rapid indexing solutions effectively.
