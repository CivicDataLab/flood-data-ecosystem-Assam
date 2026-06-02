from Utils import SeleniumScrappingUtils
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException
import time 
import os
import warnings
import re
warnings.filterwarnings("ignore", category=DeprecationWarning) 
import pytesseract
from google.cloud import vision
import google.generativeai as genai

# ---------------------------
# USER CONFIGURABLE PARAMETERS
# ---------------------------
YEARS_TO_PROCESS = ["2017-18", 
                    #"2018-19", 
                    #"2019-20", 
                    #"2020-21", 
                    #"2021-22", 
                    #"2022-23", 
                    #"2023-24", 
                    #"2024-25"
                    ]
START_PAGE_INDEX = 6        # Starting page number (0 = first page) 
END_PAGE_INDEX = None         # Set to a number to limit pages per year, or None to process all pages until no Next button is found.
OUTPUT_DIR = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\downloaded_pages"

# ---------------------------
# CONFIGURATION & INITIAL SETUP
# ---------------------------
firefox_options = Options()
firefox_options.headless = True  # Set to False if you need to see the browser

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
service = Service(r"C:\Users\saura\anaconda3\Scripts\geckodriver.exe")
PORTAL_URL = "https://fin.assam.gov.in/assamfinance/secure/aaIssuedDept"

# Service account key file and environment variable
credentials_path = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\gen-lang-client-0703494113-959eed01bd50.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

client = vision.ImageAnnotatorClient()
genai.configure(api_key="AIzaSyDZuCuwZCkL7axOLiynLCDxumLWI1tzwOk")

# ---------------------------
# CAPTCHA and Login Functions
# ---------------------------
# [captcha()] -> [Locate captcha image] -> [Save image as PNG] -> [OCR via Vision API] -> [Refine using generative model] -> [Clean & return text]

def captcha(browser, captcha_image_xpath):
    captcha_image_element = SeleniumScrappingUtils.get_page_element(browser, captcha_image_xpath)
    SeleniumScrappingUtils.save_image_as_png(captcha_image_element)
    image_path = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\captcha_image.png"
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    extracted_text = texts[0].description if texts else ""
    model = genai.GenerativeModel("gemma-3-27b-it")
    response = model.generate_content(f"Extract the letters and numbers from this text: '{extracted_text}'")
    extracted_text = re.sub(r'[^a-zA-Z0-9]', '', extracted_text).lower()
    print("Raw OCR Output (Vision API):", extracted_text)
    return extracted_text

# [captcha_input()] -> [Call captcha() to obtain text] -> [Input captcha text into field] -> [Click submit button] -> [Check for "Invalid Captcha"] -> [Loop & retry if needed]

def captcha_input(browser, captcha_image_xpath, xpath_input_text):
    captcha_text = captcha(browser, captcha_image_xpath)
    captcha_img = SeleniumScrappingUtils.get_page_element(browser, "//*[@id='imageElement']")
    print("Captcha image found!")
    captcha_input_element = SeleniumScrappingUtils.get_page_element(browser, xpath_input_text)
    SeleniumScrappingUtils.input_text_box(browser, captcha_input_element, captcha_text)
    time.sleep(3)
    button = browser.find_element(By.NAME, "submitBtn")
    button.click()
    time.sleep(3)
    invalid_elements = browser.find_elements(By.XPATH, "//*[@id='loginErrorsPanel']")
    print("Error elements found:", invalid_elements)
    while invalid_elements and "Invalid Captcha" in invalid_elements[0].text:
        print("Invalid captcha detected. Refreshing captcha and re-filling login details...")
        username = browser.find_element(By.ID, "username")
        password = browser.find_element(By.ID, "password")
        username.clear()
        password.clear()
        username.send_keys("ad.rdm")
        password.send_keys("Revenue#@2245")
        refresh_button = browser.find_element(By.XPATH, "//*[@id='refreshCaptchaButton']")
        refresh_button.click()
        time.sleep(5)
        captcha_text = captcha(browser, captcha_image_xpath)
        captcha_input_element = SeleniumScrappingUtils.get_page_element(browser, xpath_input_text)
        SeleniumScrappingUtils.input_text_box(browser, captcha_input_element, captcha_text)
        time.sleep(3)
        invalid_elements = browser.find_elements(By.XPATH, "//*[@id='loginErrorsPanel']")
        if not invalid_elements or "Invalid Captcha" not in invalid_elements[0].text:
            break

# ---------------------------
# Session Initialization and Navigation
# ---------------------------
def init_browser_session():
    """Starts a new Selenium session and logs in."""
    browser = webdriver.Firefox(service=service, options=firefox_options)
    browser.get(PORTAL_URL)
    username = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "username")))
    password = browser.find_element(By.ID, "password")
    username.send_keys("ad.rdm")
    password.send_keys("Revenue#@2245")
    captcha_input(browser, '//*[@id="imageElement"]', '//*[@id="captcha-customField"]')
    time.sleep(5)
    return browser

def select_year_and_set_max(browser, year):
    """Selects the given year and sets results per page to 100."""
    year_dropdown = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "year")))
    Select(year_dropdown).select_by_value(year)
    time.sleep(3)
    max_result_dropdown = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "aaIssuedDept_paginationVO_maxResult"))
    )
    Select(max_result_dropdown).select_by_value("100")
    time.sleep(3)

def click_next(browser):
    """Clicks the Next button and waits for the page to load."""
    next_button = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Next')]"))
    )
    next_button.click()
    time.sleep(3)

# ---------------------------
# Download Function Using New Tab
# ---------------------------
def save_page_as_html(browser, href, year_folder):
    """
    Opens the target link in a new tab using Selenium 4's new_window API,
    extracts the proposal number and description for a descriptive filename,
    skips saving if a file with that name already exists, then closes the new tab.
    """
    # Open a new tab and switch to it
    browser.switch_to.new_window('tab')
    browser.get(href)
    time.sleep(3)  # Wait for the page to load

    # Extract the proposal number from the page.
    try:
        proposal_number = browser.find_element(
            By.XPATH,
            "//div[@class='form-group' and contains(text(),'AA-')]"
        ).text.strip()
    except Exception as e:
        print("Could not extract proposal number:", e)
        proposal_number = "unknown_proposal"

    # Extract the description text from the description element.
    #try:
    #    description = browser.find_element(
    #        By.XPATH,
    #        "//div[contains(@class,'col-sm-18')]"
    #    ).text.strip()
    #except Exception as e:
    #    print("Could not extract description:", e)
    #    description = "no_description"

    # Limit the description to 50 characters.
    #short_description = description[:50].strip()
    # Remove unsafe characters and replace spaces with underscores.
    #safe_description = re.sub(r'[\\/*?:"<>|]', "", short_description).replace(" ", "_")
    
    # Build the descriptive filename using the proposal number.
    #filename = f"{proposal_number}_{safe_description}.html"
    filename = f"{proposal_number}.html"
    filename = filename.strip()
    filename = re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "-")
    page_filename = os.path.join(year_folder, filename)
    
    # If file exists, skip download.
    if os.path.exists(page_filename):
        print(f"File {page_filename} already exists. Skipping download.")
        browser.close()
        browser.switch_to.window(browser.window_handles[0])
        return

    # Save the page source.
    page_source = browser.page_source
    with open(page_filename, "w", encoding="utf-8") as f:
        f.write(page_source)
    print(f"Downloaded: {page_filename}")

    # Close the new tab and switch back to the main window.
    browser.close()
    browser.switch_to.window(browser.window_handles[0])


def download_links_on_current_page(browser, year_folder):
    """Download all target pages on the current main page by opening each link in a new tab."""
    links = browser.find_elements(By.XPATH, "//a[@data-toggle='tooltip']")
    print(f"Found {len(links)} links on current page.")
    for link in links:
        href = link.get_attribute('href')
        if href:
            save_page_as_html(browser, href, year_folder)

# ---------------------------
# Main Process Functions
# ---------------------------
def process_year(year, output_dir, start_page=0, end_page=None):
    """
    Process one year by:
      - Starting a new session,
      - Selecting the year and setting results per page to 100,
      - Clicking "Next" the required number of times,
      - Downloading all links on the current page (using new tabs).
    
    Each page is processed in a separate session. The process stops if no Next button exists
    or if the current page index exceeds end_page (if specified).
    """
    page_index = start_page
    while True:
        print(f"Processing year {year}, page {page_index}")
        browser = init_browser_session()
        try:
            select_year_and_set_max(browser, year)
            # Click "Next" button page_index times to reach the desired page.
            for i in range(page_index):
                click_next(browser)
            # Ensure the folder for this year exists.
            year_folder = os.path.join(output_dir, year)
            os.makedirs(year_folder, exist_ok=True)
            # Download all links on the current page.
            download_links_on_current_page(browser, year_folder)
            # Check if a Next button exists.
            next_buttons = browser.find_elements(By.XPATH, "//button[contains(text(),'Next')]")
            if next_buttons:
                print(f"Next page exists for year {year}.")
                page_index += 1
                if end_page is not None and page_index > end_page:
                    print(f"Reached end page limit ({end_page}) for year {year}.")
                    break
            else:
                print(f"No more pages for year {year}.")
                break
        except Exception as e:
            print(f"Error processing year {year}, page {page_index}: {e}")
            break
        finally:
            browser.quit()

def process_all_years(years, output_dir, start_page=0, end_page=None):
    """Process each year in the provided list using the given page parameters."""
    for year in years:
        print(f"--- Processing Year: {year} ---")
        process_year(year, output_dir, start_page=start_page, end_page=end_page)

# ---------------------------
# Main Script Execution
# ---------------------------
try:
    process_all_years(YEARS_TO_PROCESS, OUTPUT_DIR, start_page=START_PAGE_INDEX, end_page=END_PAGE_INDEX)
finally:
    print("Download complete!")
