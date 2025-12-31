from DrissionPage import ChromiumPage, ChromiumOptions
import time
import logging
from cleaner import standardize_job
from config import Config

logger = logging.getLogger(__name__)

class BossScraper:
    def __init__(self):
        co = ChromiumOptions()
        # Take over existing browser on port 9222
        co.set_argument(f'--remote-debugging-port={Config.CHROME_PORT}')
        try:
            self.page = ChromiumPage(co)
            logger.info("Successfully connected to ChromiumPage")
        except Exception as e:
            logger.error(f"Failed to connect to ChromiumPage: {e}")
            raise

    def scrape_keyword(self, keyword, pages=3):
        """
        Scrapes job data using infinite scroll.
        'pages' here essentially means how many times to scroll/load more.
        """
        results = []
        target_url_substring = 'wapi/zpgeek/search/joblist.json'
        
        try:
            # Start listening for network packets
            self.page.listen.start(target_url_substring)
            logger.info(f"Started listening for {target_url_substring}")
            
            # Navigate to initial Page
            # We assume the first page loads automatically upon visit
            search_url = f'https://www.zhipin.com/web/geek/job?query={keyword}&city=101210700'
            logger.info(f"Navigating to {search_url}")
            self.page.get(search_url)
            
            # Loop for the number of "pages" requested
            for i in range(1, pages + 1):
                logger.info(f"Processing batch {i}...")

                # For the first page, we might just wait.
                # For subsequent pages, we need to scroll.
                if i > 1:
                    logger.info("Scrolling to bottom to trigger load...")
                    self.page.scroll.to_bottom()
                
                # Wait for the data packet
                res = self.page.listen.wait(timeout=15)
                
                if not res:
                    logger.warning(f"Timeout waiting for response packet on batch {i}.")
                    # Attempt to scroll again if it failed? Or just break?
                    # Let's break to avoid infinite loops of nothingness.
                    break
                
                # Check response
                if res.response.status != 200:
                    logger.warning(f"Response status {res.response.status} on batch {i}")
                    continue

                json_data = res.response.body
                
                if json_data and isinstance(json_data, dict):
                    zp_data = json_data.get('zpData')
                    if zp_data and isinstance(zp_data, dict):
                        job_list = zp_data.get('jobList', [])
                        logger.info(f"Found {len(job_list)} jobs in batch {i}")
                        
                        if not job_list:
                            has_more = zp_data.get('hasMore')
                            if has_more is False:
                                logger.info("Server indicates no more jobs (hasMore=False). Ending scrape.")
                                break
                        
                        page_jobs = []
                        for job in job_list:
                            raw_job = {
                                'encryptJobId': job.get('encryptJobId'),
                                'jobName': job.get('jobName'),
                                'brandName': job.get('brandName'),
                                'cityName': job.get('cityName'),
                                'areaDistrict': job.get('areaDistrict'),
                                'salaryDesc': job.get('salaryDesc'),
                                'jobExperience': job.get('jobExperience'),
                                'jobDegree': job.get('jobDegree'),
                                'skills': job.get('skills', []),
                            }
                            
                            standardized_job = standardize_job(raw_job)
                            page_jobs.append(standardized_job)
                        
                        if page_jobs:
                            yield page_jobs
                            
                    else:
                        logger.warning(f"zpData not found or invalid format on batch {i}.")
                else:
                    logger.warning(f"Invalid JSON response on batch {i}.")
                
                # Small random delay to let the page settle
                time.sleep(2)
        
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            self.page.listen.stop()
