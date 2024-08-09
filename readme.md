BDO ATM Scraper
This Python script uses chromedriver to fireup google maps and search for the key provided (ec. BPI ATM Taguig). It will wait for the results and starts scraping them and then model each with respect to Crimson Compass' data model.

NOTE: When the url is executed on your brower, you would need to scroll the container of the results. Else, it would return an error that the css selector is not found.

Prerequisites
Python 3.x
requests library
beautifulsoup4 libraryBDO ATM Scraper
chromedriver.exe

GOOGLE_MAPS_API_KEY
GOOGLE_APPLICATION_CREDENTIALS (service account json)

```sh

pip install .
```

```sh
Usage

1. Clone the repository or download the script:


2. Update the areas list in the script with the area values you want to scrape:

# List of search keys
search_keys = ["BPI Ortigas"]

3. Run the script:

python scrape.py

4. Current output

The script will scrape data from BDO's ATM Locations and model these data to be saved into your firebase firestore database

```
