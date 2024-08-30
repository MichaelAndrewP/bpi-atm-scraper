import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
import json
import os
import requests
import geohash2 as geohash
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import googlemaps
from dotenv import load_dotenv
from google.cloud import firestore
import pytz  # Import pytz for time zone conversion

# Load environment variables from .env file
load_dotenv()

# Set the GOOGLE_APPLICATION_CREDENTIALS environment variable
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Initialize Google Maps client with API key from environment variable
gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))

# Initialize Firestore client
db = firestore.Client()

# NOTE Make sure this is the correct bank reference
bank_document_path = 'banks/hV6PZoo8KClZymEJS2bm' 


# List of search keys
# BPI ATM Taguig  
# BPI ATM Makati 
# BPI ATM Ortigas 
# BPI ATM Pampangga
# BPI ATM Puerto Gallera
search_keys = ["BPI ATM in Angeles City, Pampanga" ]

def reverse_geocode(lat, lng):
    results = gmaps.reverse_geocode((lat, lng))
    
    address = {
        'city': '',
        'country': '',
        'fullAddress': '',
        'postalCode': '',
        'stateProvince': '',
        'streetAddress': ''
    }
    
    for result in results:
        address_components = result['address_components']
        
        for component in address_components:
            if 'locality' in component['types']:
                address['city'] = component['long_name']
            elif 'country' in component['types']:
                address['country'] = component['short_name']
            elif 'postal_code' in component['types']:
                address['postalCode'] = component['long_name']
            elif 'administrative_area_level_1' in component['types']:
                address['stateProvince'] = component['long_name']
            elif 'route' in component['types']:
                address['streetAddress'] = component['long_name']
        
        # If we have at least one of the required components, we can use this result
        if any(address.values()):
            address['fullAddress'] = result['formatted_address']
            return address
    
    return None

# Function to transform item into the new model
def transform_item(item):
    # Convert current time to Asia/Manila time zone
    manila_tz = pytz.timezone('Asia/Manila')
    current_time = datetime.now(manila_tz)
    
    geohash_code = geohash.encode(item['lat'], item['lng'])
    external_id = f"{item['name']}_{current_time.strftime('%Y%m%d%H%M%S')}"
    address_details = reverse_geocode(item['lat'], item['lng'])
    geopoint = firestore.GeoPoint(item['lat'], item['lng'])
    
    # Create a reference to the bank document using the variable
    bank_ref = db.document(bank_document_path)
 
    
    return {
        'address': address_details if address_details else {
            'city': "",
            'country': "PH",
            'fullAddress': item['address'],
            'postalCode': "",
            'stateProvince': "",
            'streetAddress': ""
        },
        'bank': bank_ref,
        'createdAt': current_time,
        'updatedAt': current_time,
        'externalId': external_id,
        'id': '',  # Leave id empty initially
        'lastReportedStatus': {
            'reportedBy': {
                'appVersion': '',
                'deviceId': '',
                'deviceModel': '',
                'osVersion': ''
                        },
            'status': '', 
            'timestamp': current_time,
        },       
        'location': {
            'geohash': geohash_code,
            'geopoint': geopoint
        },
        'name': item['name'],
        'qrCode': 'https://example.com/qrcode/ ',
        'status': 'online',
        'addedBy': 'admin',
    }

def scrape_bpi_locations(search_key):
    # Step 1: Set up WebDriver
    service = Service('./chromedriver.exe')  # Update path to your chromedriver
    driver = webdriver.Chrome(service=service)

    # Step 2: Construct Google Maps URL with specific location parameters
    
    maps_url = f"https://www.google.com/maps/search/{search_key}"

    # Step 3: Open Google Maps with the constructed URL
    driver.get(maps_url)

    # Wait for results to load
    time.sleep(5)

    # Step 4: Scroll until all data is loaded
    # scrollable_div = driver.find_element(By.CSS_SELECTOR, "div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde.ecceSd.QjC7t")
    # last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)

    # while True:
    #     # Scroll down
    #     driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
    #     time.sleep(2)  # Wait for new data to load

    #     # Calculate new scroll height and compare with last scroll height
    #     new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
    #     if new_height == last_height:
    #         break  # Exit the loop if no new data is loaded
    #     last_height = new_height

    # Step 5: Extract Data
    results = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
    count = 0  # Initialize counter
    objects = []
    for result in results:
        try:
            name = result.get_attribute("aria-label")
            address = result.get_attribute("href")
            
            # Extract latitude and longitude using regex
            match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', address)
            if match:
                latitude = float(match.group(1))
                longitude = float(match.group(2))
                print(f"Name: {name}, Latitude: {latitude}, Longitude: {longitude}")
                data = {'name': name, 'lat': latitude, 'lng': longitude}
                objects.append(data)
            else:
                print(f"Name: {name}, Address: {address} (Latitude and Longitude not found)")
            
            count += 1  # Increment counter
        except Exception as e:
            print(f"Error extracting data: {e}")

    print(f"Total results for {search_key}: {count}")  # Print the total count

    # Close the driver
    driver.quit()

    return objects


def main():
    all_data=[]
    not_saved_count = 0
# Loop through the list of search keys and call the function for each key
    for key in search_keys:
        objects = scrape_bpi_locations(key)
        if objects:
            for obj in objects:
                new_object = transform_item(obj)
                print(new_object)
                all_data.append(new_object)
        else:
            print(f"Failed to scrape data")

    for item in all_data:
        print(item)
        try:
            # Check if the item already exists in Firestore
            existing_docs = db.collection('atms').where('name', '==', item['name']).stream()
            if any(existing_docs):
                print(f"Item with name {item['name']} already exists. Skipping.")
                not_saved_count += 1
                continue
            
            # Save each item to Firestore and get the document reference
            doc_ref = db.collection('atms').add(item)[1]
            # Update the item with the document ID
            item['id'] = doc_ref.id
            # Update the document with the new ID
            db.collection('atms').document(doc_ref.id).set(item)
        except Exception as e:
            print(f"Error saving item to Firestore: {e}")

    print(f"Total number of objects: {len(all_data)}")
    print(f"Number of objects not saved because it already exists or raw data is not available: {not_saved_count}")

if __name__=="__main__":
    main()