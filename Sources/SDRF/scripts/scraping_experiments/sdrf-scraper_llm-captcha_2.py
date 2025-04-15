from Utils import SeleniumScrappingUtils
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from selenium.webdriver.support.ui import Select
import time 
import os
import warnings
import re
warnings.filterwarnings("ignore", category=DeprecationWarning) 
import pytesseract
from google.cloud import vision
import google.generativeai as genai
from selenium.webdriver.support.ui import Select



# Set up Firefox options and Tesseract path
firefox_options = Options()
firefox_options.headless = True

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Initialize WebDriver
service = Service(r"C:\Users\saura\anaconda3\Scripts\geckodriver.exe")
browser = webdriver.Firefox(service=service)

# Open the portal
browser.get("https://fin.assam.gov.in/assamfinance/secure/aaIssuedDept")

# Replace with the path to your service account key file
credentials_path = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\gen-lang-client-0703494113-959eed01bd50.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

# Configure Google Cloud Vision API
client = vision.ImageAnnotatorClient()

# Configure Google AI API Key
genai.configure(api_key="AIzaSyDZuCuwZCkL7axOLiynLCDxumLWI1tzwOk")

def captcha(browser,captcha_image_xpath):
    captcha_image_element = SeleniumScrappingUtils.get_page_element(browser,captcha_image_xpath)
    SeleniumScrappingUtils.save_image_as_png(captcha_image_element)
    #image_path = Image.open('captcha_image.png') 
    image_path = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\captcha_image.png"
    
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)

    # Perform OCR using Vision API
    response = client.text_detection(image=image)
    texts = response.text_annotations
    extracted_text = texts[0].description if texts else ""

    # Clean the extracted text (Optional)
    # extracted_text = re.sub(r'[^a-zA-Z0-9]', '', extracted_text)

    # Use Gemma to refine the OCR text
    model = genai.GenerativeModel("gemma-3-27b-it")
    response = model.generate_content(f"Extract the letters and numbers from this text: '{extracted_text}'")
    extracted_text = re.sub(r'[^a-zA-Z0-9]', '', extracted_text)
    extracted_text = extracted_text.lower()
    # Print results
    print("Raw OCR Output (Vision API):", extracted_text)

    return extracted_text    

# Alert handling function - not being used currently
def handle_alert(driver):
    try:
        alert = driver.switch_to.alert
        print("Alert text:", alert.text)  # Print the alert text

        alert.dismiss()  # alert.accept() #or 
        print("Alert dismissed.")
    except NoAlertPresentException:
        print("No alert present.")

def captcha_input(captcha_image_xpath, xpath_input_text):
    # Get the initial captcha text.
    captcha_text = captcha(browser, captcha_image_xpath)
    
    # Wait for the captcha image to be present.
    captcha_img = SeleniumScrappingUtils.get_page_element(browser, "//*[@id='imageElement']")
    print("Captcha image found!")
    
    # Input the captcha.
    captcha_input_element = SeleniumScrappingUtils.get_page_element(browser, xpath_input_text)
    SeleniumScrappingUtils.input_text_box(browser, captcha_input_element, captcha_text)
    time.sleep(3)
    
    # Click the submit button.
    button = browser.find_element(By.NAME, "submitBtn")
    button.click()
    time.sleep(3)
    
    # Check if there's an error (invalid captcha).
    invalid_elements = browser.find_elements(By.XPATH, "//*[@id='loginErrorsPanel']")
    print("Error elements found:", invalid_elements)
    
    # If error is found, repeatedly refresh the captcha and re-fill login fields.
    while invalid_elements and "Invalid Captcha" in invalid_elements[0].text:
        print("Invalid captcha detected. Refreshing captcha and re-filling login details...")
        
        # Re-fill username and password fields.
        username = browser.find_element(By.ID, "username")
        password = browser.find_element(By.ID, "password")
        username.clear()
        password.clear()
        username.send_keys("ad.rdm")
        password.send_keys("Revenue#@2245")
        
        # Get a new captcha.
        captcha_text = captcha(browser, captcha_image_xpath)
        
        # Re-enter the new captcha.
        captcha_input_element = SeleniumScrappingUtils.get_page_element(browser, xpath_input_text)
        SeleniumScrappingUtils.input_text_box(browser, captcha_input_element, captcha_text)
        time.sleep(3)
        
        # Click the refresh captcha button.
        refresh_button = browser.find_element(By.XPATH, "//*[@id='refreshCaptchaButton']")
        refresh_button.click()
        time.sleep(3)
        
        # Re-check for the error message.
        invalid_elements = browser.find_elements(By.XPATH, "//*[@id='loginErrorsPanel']")
        if not invalid_elements or "Invalid Captcha" not in invalid_elements[0].text:
            break


# captcha and login functions remain the same

def go_back_to_list(browser):
    # Find the "Go Back" button and click it
    go_back_button = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn btn-primary btn-sm')]"))
    )
    go_back_button.click()
    time.sleep(3)  # Wait for the page to reload

def download_html_pages(browser, year, output_dir=r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\downloaded_pages"):
    # Create a subfolder for the year inside the output directory
    year_folder = os.path.join(output_dir, year)
    os.makedirs(year_folder, exist_ok=True)
    
    # Loop through pages and download HTML files
    while True:
        links = browser.find_elements(By.XPATH, "//a[@data-toggle='tooltip']")
        for link in links:
            href = link.get_attribute('href')
            if href:
                browser.get(href)
                time.sleep(3)
                page_source = browser.page_source
                page_filename = os.path.join(year_folder, f"{href.split('=')[-1]}.html")
                with open(page_filename, "w", encoding="utf-8") as file:
                    file.write(page_source)
                print(f"Downloaded: {page_filename}")
                go_back_to_list(browser)
                time.sleep(2)
        
        # Handle pagination
        next_button = browser.find_elements(By.XPATH, "//a[text()='Next']")
        if next_button:
            next_button[0].click()
            time.sleep(3)
        else:
            print(f"No more pages for year {year}.")
            break


def download_html_pages_for_year(browser, year, output_dir):
    #r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\downloaded_pages"
    # Create a subfolder for the year inside the output directory
    year_folder = os.path.join(output_dir, year)
    os.makedirs(year_folder, exist_ok=True)
    
    # Start on the first page and loop through until all pages are downloaded
    while True:
        # Extract all relevant links (those with data-toggle='tooltip')
        links = browser.find_elements(By.XPATH, "//a[@data-toggle='tooltip']")
        
        # Loop through each link and download the page as an HTML file
        for link in links:
            href = link.get_attribute('href')
            if href:  # If href is valid
                save_page_as_html(browser, href, year_folder)
        
        # Handle pagination: find and click the "Next" button
        next_button = browser.find_elements(By.XPATH, "//button[contains(text(),'Next')]")
        time.sleep(5) 
        if next_button:
            next_button[0].click()
            time.sleep(3)  # Wait for the next page to load
        else:
            print(f"No more pages for year {year}.")
            break



def select_year_and_scrape(browser, start_year="2017-18", end_year="2024-25", output_dir=r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\downloaded_pages"):
    # Find the year dropdown element
    year_dropdown = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "year"))
    )
    # Create a Select object to interact with the dropdown
    select = Select(year_dropdown)
    # Get all available options from the dropdown
    available_years = [option.get_attribute("value") for option in select.options]
    # Filter the years based on the range you need (2017-18 to 2024-25)
    years_to_scrape = [year for year in available_years if start_year <= year <= end_year]
    # Loop through each year and scrape the data
    for year in years_to_scrape:
        print(f"Selecting year: {year}")
        # Select the year
        select.select_by_value(year)
        time.sleep(3)  # Allow the page to reload
        # After selecting the year, call the function to download the HTML pages
        download_html_pages_for_year(browser, year, output_dir)
        time.sleep(2)  # Add delay between years for good measure


def save_page_as_html(browser, href, year_folder):
        # Open the target link in a new tab using JavaScript
    browser.execute_script(f"window.open('{href}', '_blank');")
    # Switch to the new tab
    browser.switch_to.window(browser.window_handles[-1])
    
    time.sleep(3)  # Wait for the page to load
    
    # Get the page source (HTML content)
    page_source = browser.page_source
    # Generate a filename based on the part of the query string in the href
    page_filename = os.path.join(year_folder, f"{href.split('=')[-1]}.html")
    
    # Save the page as an HTML file
    with open(page_filename, "w", encoding="utf-8") as file:
        file.write(page_source)
    print(f"Downloaded: {page_filename}")
    
    # Close the new tab and switch back to the main window
    browser.close()
    browser.switch_to.window(browser.window_handles[0])

    
def select_year_and_save(browser, start_year="2017-18", end_year="2024-25"):
    # Find the year dropdown element
    year_dropdown = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "year"))
    )
    
    select = Select(year_dropdown)
    available_years = [option.get_attribute("value") for option in select.options]
    years_to_scrape = [year for year in available_years if start_year <= year <= end_year]
    
    for year in years_to_scrape:
        print(f"Selecting year: {year}")
        select.select_by_value(year)
        time.sleep(3)  # Allow the page to reload
        save_page_as_html(browser, year)  # Save the main page HTML
        time.sleep(2)


# Log in and scraping process
try:
    username = WebDriverWait(browser, 2).until(EC.presence_of_element_located((By.ID, "username")))
    password = browser.find_element(By.ID, "password")
    username.send_keys("ad.rdm")
    password.send_keys("Revenue#@2245")
    captcha_input('//*[@id="imageElement"]', '//*[@id="captcha-customField"]') 
    time.sleep(5)
    select_year_and_scrape(browser, start_year="2017-18", end_year="2024-25", output_dir="downloaded_pages")
finally:
    browser.quit()

print("Download complete!")