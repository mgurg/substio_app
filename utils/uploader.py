import argparse
import json
import re

import requests
from loguru import logger

# Constants
LOCAL_API_URL = "http://localhost:5000/places"
PROD_API_URL = "https://api.subaro.pl/places"

AUTH_HEADER = {"Authorization": "Bearer fake_dev_token_12345678890_abcd"}

# File mapping
JSON_FILES = {
    "places": "export/courts_data.json",
    "cities": "export/pl_overpass_nominatim_sorted.json"
}


def load_json_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def send_places_to_api(item, api_url):
    try:
        if not re.fullmatch(r"\d{2}-\d{3}", item["postal_code"]):
            logger.warning(f"Item `{item['id']}` - {item['name']} has incorrect postal code format.")

        response = requests.post(api_url, json=item, headers=AUTH_HEADER)
        response.raise_for_status()
        print('.', end='', flush=True)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending item `{item['id']}` - {item['name']}: {e}")


def send_cities_to_api(item, api_url):
    try:
        response = requests.post(f"{api_url}/city", json=item, headers=AUTH_HEADER)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code != 409:
            logger.error(f"Error, city: {item['city_name']} {e.response.text}")
        else:
            print('.', end='', flush=True)


def main(mode, env):
    api_url = PROD_API_URL if env == 'prod' else LOCAL_API_URL
    json_file = JSON_FILES[mode]

    data = load_json_file(json_file)

    if mode == "places":
        facilities = data.get("facilities", [])
        if facilities and isinstance(facilities, list):
            for facility in facilities:
                send_places_to_api(facility, api_url)

    elif mode == "cities":
        cities = data if isinstance(data, list) else data.get("cities", [])
        if cities and isinstance(cities, list):
            for city in cities:
                send_cities_to_api(city, api_url)


if __name__ == "__main__":
    # uv run uploader.py --env local --mode places
    # uv run uploader.py --env prod --mode cities

    parser = argparse.ArgumentParser(description="Send place/city data to API.")
    parser.add_argument('--env', choices=['local', 'prod'], default='local', help="Environment to use: local or prod")
    parser.add_argument('--mode', choices=['places', 'cities'], required=True,
                        help="Data type to send: places or cities")

    args = parser.parse_args()

    try:
        main(args.mode, args.env)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Exiting gracefully.")
