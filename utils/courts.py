import csv
import json
import time

from geopy import Nominatim
from geopy.exc import GeocoderTimedOut

# Setup local Nominatim
geolocator = Nominatim(user_agent="erGeocoder", domain="localhost:7070", scheme="http")

FIELD_NAME_MAP = {
    "Typ": "type",
    "Nazwa sądu": "name",
    "Ulica": "street",
    "Kod pocztowy": "postal_code",
    "Miejscowość": "city",
    "Telefon": "phone",
    "E-mail": "email",
    "adres ePUAP": "epuap",
    "Department": "department"
}


def geolocate_address(street, city, postcode):
    try:
        # Use first postal code only, if multiple
        postcode = postcode.split(",")[0].strip()

        query = f"{street}, {postcode} {city}, Poland"
        location = geolocator.geocode(query, timeout=10)
        if location:
            return location.latitude, location.longitude
    except GeocoderTimedOut:
        print(f"Timeout during geolocation: {street}, {city}")
        time.sleep(1)
        return geolocate_address(street, city, postcode)  # retry once
    return None, None


def split_addresses_outside_brackets(address_string):
    """
    Split addresses on commas or semicolons that are not inside brackets.
    Returns a list of individual addresses.
    """
    if not address_string:
        return [""]

    addresses = []
    current_address = ""
    bracket_count = 0

    for char in address_string:
        if char == "(":
            bracket_count += 1
        elif char == ")":
            bracket_count -= 1
        elif (char == "," or char == ";") and bracket_count == 0:
            # Found a comma or semicolon outside brackets - this is a separator
            addresses.append(current_address.strip())
            current_address = ""
            continue

        current_address += char

    # Add the last address
    if current_address.strip():
        addresses.append(current_address.strip())

    # Return at least one empty string if no addresses found
    return addresses if addresses else [""]


def extract_address_and_department(address_with_dept):
    """
    Extract address and department from a string like "Pl. Kopernika 2 (Biuro Podawcze, Czytelnia)"
    Returns tuple: (clean_address, department_or_none)
    """
    if not address_with_dept:
        return "", None

    address_with_dept = address_with_dept.strip()

    # Find the first opening parenthesis
    paren_start = address_with_dept.find("(")

    if paren_start == -1:
        # No parentheses found - return address as is, department as None
        return address_with_dept, None

    # Find the last closing parenthesis
    paren_end = address_with_dept.rfind(")")

    if paren_end == -1 or paren_end <= paren_start:
        # Malformed parentheses - return address as is
        return address_with_dept, None

    # Extract address (everything before first parenthesis)
    address = address_with_dept[:paren_start].strip()

    # Extract department (everything between parentheses)
    department = address_with_dept[paren_start + 1:paren_end].strip()

    return address, department if department else None


def process_csv_to_json(csv_file_path, json_file_path):
    """
    Load CSV file with tab delimiters and extract specific columns,
    then save as JSON file. Split multiple addresses and duplicate records.
    """

    # Define the columns we want to extract
    columns_to_extract = [
        "Typ",
        "Nazwa sądu",
        "Ulica",
        "Kod pocztowy",
        "Miejscowość",
        "Telefon ",
        "E-mail  ",
        "adres ePUAP"
    ]

    extracted_data = []

    try:
        # Read the CSV file with tab delimiter
        with open(csv_file_path, encoding="utf-8") as csvfile:
            # Use tab as delimiter
            reader = csv.DictReader(csvfile, delimiter="\t")

            for row in reader:
                # First, extract the base data
                base_row = {}
                for column in columns_to_extract:
                    # Clean up column names for JSON (remove extra spaces)
                    clean_key = column.strip()
                    if clean_key == "Telefon":
                        clean_key = "Telefon"
                    elif clean_key == "E-mail":
                        clean_key = "E-mail"

                    # Get the value and strip whitespace
                    value = row.get(column, "").strip()
                    eng_key = FIELD_NAME_MAP.get(clean_key, clean_key)
                    base_row[eng_key] = value

                # Handle multiple addresses in Ulica field
                ulica_value = base_row.get("street", "")
                addresses = split_addresses_outside_brackets(ulica_value)

                # Create a record for each address
                for address in addresses:
                    record = base_row.copy()

                    # Extract clean address and department
                    clean_address, department = extract_address_and_department(address)
                    record["street"] = clean_address
                    record["department"] = department

                    # Geolocate
                    # lat, lon = geolocate_address(clean_address, record['city'], record['postal_code'])
                    # record['lat'] = lat
                    # record['lon'] = lon

                    record["category"] = "court"
                    record["website"] = "https://" + record["email"].split("@")[-1] if record.get("email") else None

                    extracted_data.append(record)

        # Save as JSON file
        with open(json_file_path, "w", encoding="utf-8") as jsonfile:
            json.dump(extracted_data, jsonfile, ensure_ascii=False, indent=2)

        print(f"Successfully processed {len(extracted_data)} records")
        print(f"Data saved to: {json_file_path}")

    except FileNotFoundError:
        print(f"Error: Could not find the file {csv_file_path}")
    except Exception as e:
        print(f"Error processing file: {str(e)}")


def main():
    # Set your file paths here
    csv_file_path = "input/courts_data.csv"  # Change this to your CSV file path
    json_file_path = "output/courts_data.json"  # Output JSON file path

    # Process the file
    process_csv_to_json(csv_file_path, json_file_path)

    # Optional: Display the first few records and show address splitting example
    try:
        with open(json_file_path, encoding="utf-8") as f:
            data = json.load(f)
            print("\nFirst record preview:")
            if data:
                print(json.dumps(data[0], ensure_ascii=False, indent=2))

            # Show example of address splitting if available
            multiple_address_records = [record for record in data if record.get("Department") is not None]
            if multiple_address_records:
                print("\nExample of address and department extraction:")
                court_name = multiple_address_records[0].get("Nazwa sądu", "")
                same_court_records = [r for r in data if r.get("Nazwa sądu", "") == court_name][:3]
                for i, record in enumerate(same_court_records):
                    print(f"Record {i + 1}:")
                    print(f"  Address: {record.get('Ulica', '')}")
                    print(f"  Department: {record.get('Department', 'None')}")
            else:
                print("\nNo records with departments found in the sample.")
    except:
        pass


if __name__ == "__main__":
    main()
