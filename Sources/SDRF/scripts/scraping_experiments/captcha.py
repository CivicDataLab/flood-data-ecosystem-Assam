from Utils import SeleniumScrappingUtils
from PIL import Image, ImageFilter
from pytesseract import image_to_string 
import numpy
from scipy.ndimage.filters import gaussian_filter
import os
from selenium.webdriver.common.by import By
import time
import re

th1 = 140
th2 = 140 # threshold after blurring 
sig = 1.5

path = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments"

'''
import requests
import urllib3
from PIL import Image
from io import BytesIO

import certifi
print(path)

import cv2
import numpy as np
from PIL import Image

def remove_noise_with_opencv(image_path):
    # Load image and convert to grayscale
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # Apply median blur to remove noise
    blurred = cv2.medianBlur(image, 3)

    # Apply binary threshold
    _, thresh = cv2.threshold(blurred, th1, 255, cv2.THRESH_BINARY)
    
    # Remove small dots with morphological operations
    kernel = np.ones((3, 3), np.uint8)
    processed_image = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # Convert back to PIL for further processing
    return Image.fromarray(processed_image)

def refresh_captcha(browser, refresh_button_xpath):
    """Click the refresh button to reload the CAPTCHA image."""
    refresh_button = SeleniumScrappingUtils.get_page_element(browser, refresh_button_xpath)
    refresh_button.click()
    time.sleep(3)  # Wait for the CAPTCHA to refresh

import base64

def download_captcha_image(browser, captcha_image_xpath):
    """Extracts base64 CAPTCHA image from a data URL, decodes it, and saves it."""
    
    refresh_captcha(browser, "//*[@id='refreshCaptchaButton']")
    
    captcha_image_element = SeleniumScrappingUtils.get_page_element(browser, captcha_image_xpath)
    captcha_image_data = captcha_image_element.get_attribute('src')

    if captcha_image_data.startswith('data:image'):
        # Extract base64 part
        base64_data = captcha_image_data.split(',')[1]
        
        # Decode and save the image
        captcha_image_path = "captcha_image.png"
        with open(captcha_image_path, "wb") as f:
            f.write(base64.b64decode(base64_data))
        
        print("Captcha image saved from base64 data.")
        return captcha_image_path
    else:
        print("Unexpected CAPTCHA format.")
        return None

def download_captcha_image(browser, captcha_image_xpath):
    # Get the CAPTCHA image element and retrieve the URL
    refresh_captcha(browser, "//*[@id='refreshCaptchaButton']")
    captcha_image_element = SeleniumScrappingUtils.get_page_element(browser, captcha_image_xpath)
    captcha_image_url = captcha_image_element.get_attribute('src')
    print(f"Captcha URL: {captcha_image_url}")    
    # Download the image
    cookies = browser.get_cookies()  # Retrieve cookies from Selenium
    # Convert Selenium cookies to a format compatible with requests
    session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
    response = requests.get(captcha_image_url, cookies=session_cookies, verify=False)

    #response = requests.get(captcha_image_url, stream=True, verify=False)  # Disable SSL verification if necessary
    if response.status_code == 200:
        # Convert response content to an image
        captcha_image = Image.open(BytesIO(response.content))
        captcha_image.save("captcha_image.png")
        print("Captcha image downloaded successfully.")
    else:
        print("Failed to download captcha image.")
    
    return "captcha_image.png"


def captcha(browser, captcha_image_xpath):
    # Download the CAPTCHA image from the `.ashx` URL
    captcha_image_path = download_captcha_image(browser, captcha_image_xpath)
    
    # Open and process the downloaded image
    original = Image.open(captcha_image_path)
    original.save(path + r"2_original.png")
    black_and_white = original.convert("L")
    black_and_white.save(path + r"3_black_and_white.png")

    processed_image = remove_noise_with_opencv(path + r"3_black_and_white.png")
    processed_image.save(path + r"4_processed_captcha.png")

    #filtered_image = black_and_white.filter(ImageFilter.MinFilter(size=3))
    #filtered_image.save(path + r"filtered_min.png")
    first_threshold = processed_image.point(lambda p: p > th1 and 255)
    first_threshold.save(path + r"5_first_threshold.png")

    blur = numpy.array(first_threshold)
    blurred = gaussian_filter(blur, sigma=sig)
    blurred = Image.fromarray(blurred)
    blurred.save(path + r"6_blurred.png")

    final = blurred.point(lambda p: p > th2 and 255)
    final = final.filter(ImageFilter.EDGE_ENHANCE_MORE)
    final = final.filter(ImageFilter.SHARPEN)
    final.save(path + r"7_final.png")

    # OCR configuration and text extraction
    config = "-l eng --oem 1 --psm 11"
    captcha_text = image_to_string(Image.open(path + r"7_final.png"), lang="eng", config=config)
    print(f"Captcha Text: {captcha_text}")
    return captcha_text
'''

def captcha(browser,captcha_image_xpath):
    captcha_image_element = SeleniumScrappingUtils.get_page_element(browser,captcha_image_xpath)
    SeleniumScrappingUtils.save_image_as_png(captcha_image_element)
    original = Image.open('captcha_image.png')
    original.save("original.png")
    black_and_white =original.convert("L") 
    black_and_white.save("black_and_white.png")

    first_threshold = black_and_white.point(lambda p: p > th1 and 255)
    first_threshold.save("first_threshold.png")


    blur=numpy.array(first_threshold) #create an image array
    blurred = gaussian_filter(blur, sigma=sig)
    blurred = Image.fromarray(blurred)
    blurred.save("blurred.png")

    final = blurred.point(lambda p: p > th2 and 255)
    final = final.filter(ImageFilter.EDGE_ENHANCE_MORE)
    final = final.filter(ImageFilter.SHARPEN)
    final.save("final.png")

    #         remove images 
    #os.remove("black_and_white.png")
    #os.remove("first_threshold.png")
    #os.remove("blurred.png")
    #os.remove("original.png")


    config = ("-l eng --oem 3 --psm 11")
    captcha_text = image_to_string(Image.open('final.png'), lang = "eng",config=config)
    captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text)
    print(f"Cleaned Captcha Text: {captcha_text}")
    return captcha_text
