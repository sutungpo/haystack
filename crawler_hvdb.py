import os
import re
import time
from playwright.sync_api import sync_playwright
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
# Base URL
base_url = "https://hvdb.me"

def scrape_rj_codes():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        # Start from page 2 based on the image
        current_page = 93
        end_page = 93
        while current_page <= end_page:
            url = f"{base_url}/?page={current_page}&sort=scriptsort&pageSize=50"
            try:
                # 1. Navigate to the RJ code list page
                logging.info(f"Scraping page list {current_page}...")
                page = context.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_load_state("networkidle")
                details_links = page.query_selector_all("a[href^='/Dashboard/Details/']")
                unique_details_links = [link for link in details_links]

                for link in unique_details_links:
                    try:
                        # 2. Navigate to the RJ ocde Details page
                        href = link.get_attribute("href")
                        details_page = context.new_page()
                        details_page.goto(f"{base_url}{href}", timeout=30000)
                        details_page.wait_for_selector("a:has-text('View Scripts')")
                        
                        h2_element = details_page.query_selector('h2')
                        h2_text = h2_element.text_content() if h2_element else ""
                        match = re.search(r'RJ\d+', h2_text)
                        rj_code = match.group(0) if match else "NA"
                        logging.info(f"RJ Code: {rj_code}")
                        rj_code_dir = Path(f"{rj_code}")
                        if rj_code_dir.exists():
                            logging.info(f"Folder {rj_code_dir} already exists, skipping...")
                            details_page.close()
                            continue
                        rj_code_dir.mkdir(parents=True, exist_ok=True)

                        view_scripts_button = details_page.query_selector("a:has-text('View Scripts')")
                        # view_scripts_button = page.query_selector('a.btn.btn-default[href^="/Dashboard/ScriptList/"]')

                        scripts_link = view_scripts_button.get_attribute("href")
                        # 3. Navigate to the scripts list page
                        scripts_list_page = context.new_page()
                        scripts_list_page.goto(f"{base_url}{scripts_link}")
                        scripts_list_page.wait_for_selector("a[href^='/Dashboard/Script/']")
                        # Extract the script detail links
                        script_links = scripts_list_page.query_selector_all("a[href^='/Dashboard/Script/']")
                        # Create a folder for the track title
                        unique_scripts_links = [script_link for script_link in script_links]

                        for i,script_link in enumerate(unique_scripts_links, 1):
                            # 4. Navigate to the script detail page
                            try:
                                script_href = script_link.get_attribute("href")
                                script_title = script_link.text_content()
                                invalid_chars = '<>:"/\\|?*'
                                script_title = str(i) + " " + "".join(c for c in script_title if c not in invalid_chars)
                                script_page = context.new_page()
                                script_page.goto(f"{base_url}{script_href}", timeout=30000)
                                
                                if script_page.is_visible(".row.japScript", timeout=30000):
                                    # # Extract the HTML content of the script detail page
                                    script_box = script_page.query_selector(".row.japScript p")
                                    script_text = script_box.text_content() if script_box else ""
                                elif script_page.is_visible(".row.bothScript", timeout=30000):
                                    script_box = script_page.query_selector(".row.bothScript > div:first-child p.double-box")
                                    script_text = script_box.text_content() if script_box else ""
                                else:
                                    import shutil
                                    shutil.rmtree(rj_code_dir)
                                    logging.info(f"Script Title: {script_title} - No script japanese content found, removing folder {rj_code_dir}")
                                    break
                                # Save the script content to a file
                                script_file = rj_code_dir / f"{script_title}.txt"
                                with open(script_file, "w", encoding="utf-8") as f:
                                    f.write(script_text)
                                # time.sleep(1)
                                script_page.close()
                            except Exception as e:
                                logging.error(f"Error occurred while fetching script for script {script_title}: {e}")
                                script_page.close()
                        scripts_list_page.close()
                        details_page.close()
                    except Exception as e:
                        logging.error(f"Error occurred while fetching rj detail link or its script lists for {href}: {e}")
                        scripts_list_page.close()
                        details_page.close()

                current_page += 1
                time.sleep(1)
                page.close()
            except Exception as e:
                logging.error(f"Error occurred while fetching page list {current_page}: {e}")
                current_page += 1
                continue
        # Close the browser
        browser.close()

if __name__ == "__main__":
    scrape_rj_codes()