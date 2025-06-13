from app.crawlers.base_crawler import BaseCrawler

class CrawlerB(BaseCrawler):
    """法律网站B的爬虫实现"""
    
    def __init__(self):
        super().__init__(base_url=settings.CRAWLER_B_URL)

    async def crawl(self):
        # 具体爬取逻辑
        print("Crawling from website B...")