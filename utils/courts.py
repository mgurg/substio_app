import csv
import json
import re


def split_addresses_outside_brackets(address_string):
    """
    Split addresses on commas that are not inside brackets.
    Returns a list of individual addresses.
    """
    if not address_string:
        return ['']

    addresses = []
    current_address = ''
    bracket_count = 0

    for char in address_string:
        if char == '(':
            bracket_count += 1
        elif char == ')':
            bracket_count -= 1
        elif char == ',' and bracket_count == 0:
            # Found a comma outside brackets - this is a separator
            addresses.append(current_address.strip())
            current_address = ''
            continue

        current_address += char

    # Add the last address
    if current_address.strip():
        addresses.append(current_address.strip())

    # Return at least one empty string if no addresses found
    return addresses if addresses else ['']


def process_csv_to_json(csv_file_path, json_file_path):
    """
    Load CSV file with tab delimiters and extract specific columns,
    then save as JSON file. Split multiple addresses and duplicate records.
    """

    # Define the columns we want to extract
    columns_to_extract = [
        'Typ',
        'Nazwa sądu',
        'Ulica',
        'Kod pocztowy',
        'Miejscowość',
        'Telefon ',
        'E-mail  ',
        'adres ePUAP'
    ]

    extracted_data = []

    try:
        # Read the CSV file with tab delimiter
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            # Use tab as delimiter
            reader = csv.DictReader(csvfile, delimiter='\t')

            for row in reader:
                # First, extract the base data
                base_row = {}
                for column in columns_to_extract:
                    # Clean up column names for JSON (remove extra spaces)
                    clean_key = column.strip()
                    if clean_key == 'Telefon':
                        clean_key = 'Telefon'
                    elif clean_key == 'E-mail':
                        clean_key = 'E-mail'

                    # Get the value and strip whitespace
                    value = row.get(column, '').strip()
                    base_row[clean_key] = value

                # Handle multiple addresses in Ulica field
                ulica_value = base_row.get('Ulica', '')
                addresses = split_addresses_outside_brackets(ulica_value)

                # Create a record for each address
                for address in addresses:
                    record = base_row.copy()
                    record['Ulica'] = address
                    extracted_data.append(record)

        # Save as JSON file
        with open(json_file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(extracted_data, jsonfile, ensure_ascii=False, indent=2)

        print(f"Successfully processed {len(extracted_data)} records")
        print(f"Data saved to: {json_file_path}")

    except FileNotFoundError:
        print(f"Error: Could not find the file {csv_file_path}")
    except Exception as e:
        print(f"Error processing file: {str(e)}")


def main():
    # Set your file paths here
    csv_file_path = 'input/courts_data.csv'  # Change this to your CSV file path
    json_file_path = 'output/courts_data.json'  # Output JSON file path

    # Process the file
    process_csv_to_json(csv_file_path, json_file_path)

    # Optional: Display the first few records and show address splitting example
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"\nFirst record preview:")
            if data:
                print(json.dumps(data[0], ensure_ascii=False, indent=2))

            # Show example of address splitting if available
            multiple_address_records = [record for record in data if '(' in record.get('Ulica', '')]
            if multiple_address_records:
                print(f"\nExample of address splitting (showing records with same court name):")
                court_name = multiple_address_records[0].get('Nazwa sądu', '')
                same_court_records = [r for r in data if r.get('Nazwa sądu', '') == court_name][:3]
                for i, record in enumerate(same_court_records):
                    print(f"Record {i + 1}: {record.get('Ulica', '')}")
    except:
        pass


if __name__ == "__main__":
    main()