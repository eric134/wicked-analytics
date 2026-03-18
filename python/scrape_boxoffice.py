import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.boxofficemojo.com/title/tt1262426/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)
print("Status code:", response.status_code)