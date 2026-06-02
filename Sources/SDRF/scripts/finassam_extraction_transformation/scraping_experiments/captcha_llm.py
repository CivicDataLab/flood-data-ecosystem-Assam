#!pip install google-cloud-vision google-generativeai opencv-python numpy

import cv2
import numpy as np
from google.cloud import vision
import google.generativeai as genai
import os

# Replace with the path to your service account key file
credentials_path = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\scripts\scraping_experiments\gen-lang-client-0703494113-959eed01bd50.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

# Configure Google Cloud Vision API
client = vision.ImageAnnotatorClient()

# Configure Google AI API Key
#genai.configure(api_key="959eed01bd50d3d8362cc38cc48d5c2bbfcb4f7c")  # Replace with your key

genai.configure(api_key="AIzaSyDZuCuwZCkL7axOLiynLCDxumLWI1tzwOk")  # Replace with your key



# Load the image
image_path = r"/content/drive/MyDrive/IDS-DRR/Government Response/SDRF data/captcha2.png"
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
if response.parts:
    print("Refined Text from LLM (Gemma):", response.text)
else:
    print("LLM Refinement Failed: No valid text returned.")