import requests
import json

url = "https://drims.veldev.com/api/reports/flood/getStateCumulativeData?fromDate=2025-11-01&toDate=2025-11-30"

payload = {}
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6NTc5LCJwYXNzd29yZCI6IiQyYSQxMCRuYUF3UTVMT0tCUkVFSnFlTDRQNnN1WW5KLkVVNU1mZTBucUNOaklSenZQb1NSZzBWbS9WSyIsInVzZXJuYW1lIjoiY2RzLWxhYiIsImlhdCI6MTc3OTgwNDEzNywiZXhwIjoxNzc5ODIyMTM3fQ.2A7XgSzsKnCg-E27viSBXVSks0-22bBPP7DygqYvCh8'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)
