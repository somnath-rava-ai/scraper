from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
import asyncio
import time
import uuid
# Define the input payload model
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher
from crawl4ai import CrawlerMonitor, DisplayMode, RateLimiter
from contextlib import asynccontextmanager
from bs4 import BeautifulSoup
crawler = None
monitor = None
pattern = r"!?\[.*?\]\(.*?\)"
import re
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic here (runs once at app startup)
    global crawler
    global monitor
    browser_conf = BrowserConfig(
        text_mode=True
    )
    crawler = AsyncWebCrawler(config=browser_conf)
    await crawler.start()
    monitor = CrawlerMonitor(
    )
    
    yield  # This allows the app to run
    # await crawler.close()


app = FastAPI(lifespan=lifespan)


@app.post("/crawl")
async def crawl_endpoint(payload: dict):
    urls = payload.get("urls")
    results = []
    # coros =[]
    try:
        results = await run_crawler(urls)
        # print(results[0])
        return {"status": 200, "number_of_pages":len(results),  "results": results}
    except:
        return {"status": 400, "message": "unable_to_scrape"}


async def run_crawler(urls):
    global monitor
    global crawler
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=80.0,  # Pause if memory exceeds this
        check_interval=1.0,             # How often to check memory
        max_session_permit=20,          # Maximum concurrent tasks
        monitor= monitor
    )
    config1 = CrawlerRunConfig(
        wait_for= 20000,
        scan_full_page=True,
        session_id=str(uuid.uuid4()),
        magic=True,
        verbose=False
        )
    start  = time.time()
    # async with AsyncWebCrawler(config = browser_conf)  as crawler:
        # pattern = r"!?\[.*?\]\(.*?\)"
        # for url in urls:
        #     coros.append(asyncio.create_task(crawler.arun(url = url)))
        # # url = urls[0]
        # # try:
        # #     content = await crawler.arun(url = url)
        # #     results.append({
        # #         "url": url,
        # #         "content": content
        # #     })
        # # except Exception as e:
        # #     print(f"Unable to scrape {url} ")
        # # results  =asyncio.gather(*coros)
        
        # for coro in coros:
        #     scrape = await coro
        # 
    results = await crawler.arun_many(
    
                urls=urls,
                dispatcher=dispatcher
            )
    # results.append(scrape)
    # print(type(results))
    md_results = []
    
    for result in results:
        if result.success:
            md = result.markdown
            html  = result.html
            clean_md = re.sub(pattern, '', md)
            texts = clean_md.strip("\n")
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.find('title').text
            md_results.append({"url": result.url, "title": title, "page_content": texts})
        else:
            print(f"Failed to crawl {result.url}: {result.error_message}")
    print(time.time() - start)
    return md_results