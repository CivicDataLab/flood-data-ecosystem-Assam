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
#from captcha import captcha
import time 
import os
import warnings
import re
import sys
warnings.filterwarnings("ignore", category=DeprecationWarning) 
import pytesseract
#!pip install google-cloud-vision google-generativeai opencv-python numpy
from PIL import Image, ImageFilter

import cv2
import numpy as np
from google.cloud import vision
import google.generativeai as genai
import os


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
#genai.configure(api_key="959eed01bd50d3d8362cc38cc48d5c2bbfcb4f7c")  # Replace with your key
genai.configure(api_key="AIzaSyDZuCuwZCkL7axOLiynLCDxumLWI1tzwOk")  # Replace with your key

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

    # Print results
    print("Raw OCR Output (Vision API):", extracted_text)
    return extracted_text    

# Alert handling function
def handle_alert(driver):
    try:
        alert = driver.switch_to.alert
        print("Alert text:", alert.text)  # Print the alert text

        alert.dismiss()  # alert.accept() #or 
        print("Alert dismissed.")
    except NoAlertPresentException:
        print("No alert present.")

def captcha_input(captcha_image_xpath, xpath_input_text):
    captcha_text = captcha(browser, captcha_image_xpath)
    captcha_img = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "imageElement"))
        )
    print("Captcha image found!")
    captcha_input_element = SeleniumScrappingUtils.get_page_element(browser, xpath_input_text)
    SeleniumScrappingUtils.input_text_box(browser, captcha_input_element, captcha_text)
    time.sleep(3)
    #button = browser.find_element(By.XPATH, "//*[@id='refreshCaptchaButton']")
    button = browser.find_element(By.NAME, "submitBtn")

    button.click()
    time.sleep(3)
    # Handle alert if present
    handle_alert(browser)
    
    invalid_string = browser.find_elements(By.CLASS_NAME, "banner banner-danger alert alert-danger banner-dismissible")
    print(invalid_string)
    
    if len(invalid_string) == 0:
        pass
    else:
        while 'Invalid Code' in invalid_string[0].text:
            captcha_text = captcha(browser, captcha_image_xpath)
            captcha_input_element = SeleniumScrappingUtils.get_page_element(browser, xpath_input_text)
            SeleniumScrappingUtils.input_text_box(browser, captcha_input_element, captcha_text)
            time.sleep(3)
            
            button = browser.find_element(By.XPATH, "//*[@id='refreshCaptchaButton']")
            WebDriverWait(browser, 10)
            button.click()
            
            # Handle alert if present
            handle_alert(browser)
            
            invalid_string = browser.find_elements(By.CLASS_NAME, "error")
            if len(invalid_string) == 0:
                break
            elif 'Invalid Captcha!' not in invalid_string[0].text:
                break

def download_html_pages(browser, year, output_dir=r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\downloaded_pages"):
    # Create a subfolder for the year inside the output directory
    year_folder = os.path.join(output_dir, year)
    os.makedirs(year_folder, exist_ok=True)
    
    # Loop through pages and download HTML files
    while True:
        # Extract all relevant links (those with administrativeApprovalDetailsDept in the href)
        links = browser.find_elements(By.XPATH, "//a[contains(@href, 'administrativeApprovalDetailsDept')]")
        
        # Loop through each link and download the page
        for link in links:
            href = link.get_attribute('href')
            if href:  # If href is valid
                # Navigate to the target page
                browser.get(href)
                time.sleep(3)  # Wait for the page to load
                
                # Get the page source (HTML content)
                page_source = browser.page_source
                # Generate a filename based on part of the query string
                page_filename = os.path.join(year_folder, f"{href.split('=')[-1]}.html")
                
                # Save the page as an HTML file
                with open(page_filename, "w", encoding="utf-8") as file:
                    file.write(page_source)
                print(f"Downloaded: {page_filename}")
                
                # Go back to the initial page
                browser.back()
                time.sleep(2)
        
        # Handle pagination: find and click the "Next" button
        next_button = browser.find_elements(By.XPATH, "//a[text()='Next']")
        if next_button:
            next_button[0].click()
            time.sleep(3)  # Wait for the next page to load
        else:
            print(f"No more pages for year {year}.")
            break


def select_year_and_scrape(browser, start_year="2018-19", end_year="2024-25"):
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
        
        # Wait for the page to reload (if necessary)
        time.sleep(3)  # Adjust based on how long it takes for the page to reload
        
        # After selecting the year, call the function to download the HTML pages
        download_html_pages(browser)
        
        # Optionally, you can add a small delay between iterations
        time.sleep(2)


# Log in process
try:
    username = WebDriverWait(browser, 2).until(EC.presence_of_element_located((By.ID, "username")))
    password = browser.find_element(By.ID, "password")
    
    # Enter credentials
    username.send_keys("ad.rdm")
    password.send_keys("Revenue#@2245")
    captcha_input('//*[@id="imageElement"]', '//*[@id="captcha-customField"]') #    
    
    time.sleep(5)
    select_year_and_scrape(browser, start_year="2017-18", end_year="2024-25")

finally:
    browser.quit()  # Close the driver

print("Download complete!")
