import json
from datetime import datetime
from typing import Any

import overpy
from loguru import logger


class PolandFacilityFetcher:
    """Fetch and manage police stations and prosecutor offices data for Poland only."""

    COUNTRY_CODE = "PL"
    COUNTRY_NAME = "Poland"

    FACILITY_TYPES = {
        "police": {
            "name": "Komisariaty i Komendy Policji",
            "name_en": "Police Stations",
            "query_tags": [
                'node["amenity"="police"]',
                'way["amenity"="police"]',
                'relation["amenity"="police"]'
            ]
        },
        "prosecutor": {
            "name": "Prokuratura",
            "name_en": "Prosecutor Offices",
            "query_tags": [
                'node["office"="prosecutor"]',
                'way["office"="prosecutor"]',
                'relation["office"="prosecutor"]',
                'node["government"="prosecutor"]',
                'way["government"="prosecutor"]',
                'relation["government"="prosecutor"]',
                'node["office"="government"]["government"="prosecutor"]',
                'way["office"="government"]["government"="prosecutor"]',
                'relation["office"="government"]["government"="prosecutor"]'
            ]
        }
    }

    def __init__(self):
        self.api = overpy.Overpass()

    def fetch_facilities(self, facility_type: str) -> list[dict[str, Any]]:
        """
        Fetch facility data from Overpass API for Poland.

        Args:
            facility_type: Type of facility ('police' or 'prosecutor')

        Returns:
            List of facility dictionaries
        """
        if facility_type not in self.FACILITY_TYPES:
            raise ValueError(f"Invalid facility type. Choose from: {list(self.FACILITY_TYPES.keys())}")

        logger.info(f"Fetching {self.FACILITY_TYPES[facility_type]['name']} data for {self.COUNTRY_NAME}")

        # Build query for Poland
        facility_config = self.FACILITY_TYPES[facility_type]
        query_parts = facility_config["query_tags"]

        query = f"""
        [out:json][timeout:300];
        area["ISO3166-1"={self.COUNTRY_CODE}][admin_level=2]->.searchArea;
        (
            {';'.join(f"{tag}(area.searchArea)" for tag in query_parts)};
        );
        out body center;
        """

        try:
            result = self.api.query(query)
            facilities = []

            # Process nodes
            for node in result.nodes:
                facility = self._extract_facility_data(node, "node")
                if facility:
                    facilities.append(facility)

            # Process ways
            for way in result.ways:
                facility = self._extract_facility_data(way, "way")
                if facility:
                    facilities.append(facility)

            # Process relations
            for relation in result.relations:
                facility = self._extract_facility_data(relation, "relation")
                if facility:
                    facilities.append(facility)

            logger.info(f"Found {len(facilities)} {facility_config['name'].lower()}")
            return facilities

        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            raise

    def _extract_facility_data(self, element, element_type: str) -> dict[str, Any] | None:
        """Extract relevant data from an OSM element."""
        tags = element.tags

        # Get coordinates
        if element_type == "node":
            lat, lon = element.lat, element.lon
        elif hasattr(element, "center_lat") and hasattr(element, "center_lon"):
            lat, lon = element.center_lat, element.center_lon
        else:
            lat, lon = None, None

        # Extract names in different languages
        names = {key: value for key, value in tags.items() if key.startswith("name:")}

        # Extract contact information
        contact_info = {}
        for key in ["phone", "mobile", "fax", "email", "website"]:
            if key in tags:
                contact_info[key] = tags[key]
            elif f"contact:{key}" in tags:
                contact_info[key] = tags[f"contact:{key}"]

        # Extract address information with Polish-specific fields
        address = {}
        address_keys = ["addr:street", "addr:housenumber", "addr:postcode",
                        "addr:city", "addr:state", "addr:country"]
        for key in address_keys:
            if key in tags:
                address[key.replace("addr:", "")] = tags[key]

        # Early return if address is empty
        if not address:
            return None

        # Add Polish administrative divisions
        polish_admin = {}
        admin_keys = ["is_in:province", "is_in:county", "is_in:commune",
                      "addr:province", "addr:county", "addr:state"]
        for key in admin_keys:
            if key in tags:
                polish_admin[key] = tags[key]

        facility_data = {
            "id": element.id,
            "element_type": element_type,
            "name": tags.get("name"),
            "official_name": tags.get("official_name"),
            "amenity": tags.get("amenity"),
            "office": tags.get("office"),
            "government": tags.get("government"),
            "operator": tags.get("operator"),
            "operator_type": tags.get("operator:type"),
            "police_type": tags.get("police:type") if "police" in tags.get("amenity", "") else None,
            "coordinates": {
                "lat": str(lat) if lat else None,
                "lon": str(lon) if lon else None
            },
            "address": address if address else None,
            "polish_admin": polish_admin if polish_admin else None,
            "contact": contact_info if contact_info else None,
            "names": names if names else None,
            "opening_hours": tags.get("opening_hours"),
            "website": tags.get("website"),
            "wikipedia": tags.get("wikipedia"),
            "wikidata": tags.get("wikidata"),
            "description": tags.get("description"),
            "note": tags.get("note"),
            "all_tags": dict(tags)  # Keep all original tags for reference
        }

        return facility_data

    def save_to_json(self, data: list[dict[str, Any]], filename: str,
                     facility_type: str) -> None:
        """Save facility data to JSON file with metadata."""
        output = {
            "metadata": {
                "country": self.COUNTRY_CODE,
                "country_name": self.COUNTRY_NAME,
                "facility_type": facility_type,
                "facility_name_pl": self.FACILITY_TYPES[facility_type]["name"],
                "facility_name_en": self.FACILITY_TYPES[facility_type]["name_en"],
                "total_count": len(data),
                "generated_at": datetime.now().isoformat(),
                "source": "OpenStreetMap via Overpass API"
            },
            "facilities": data
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Data saved to {filename}")

    def get_facility_statistics(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate basic statistics about the fetched facilities."""
        if not data:
            return {"total": 0}

        stats = {
            "total": len(data),
            "with_names": sum(1 for f in data if f.get("name")),
            "with_coordinates": sum(1 for f in data if f["coordinates"]["lat"] and f["coordinates"]["lon"]),
            "with_phone": sum(1 for f in data if f.get("contact") and f["contact"].get("phone")),
            "with_address": sum(1 for f in data if f.get("address")),
            "by_element_type": {},
            "by_operator": {}
        }

        # Count by element type
        for facility in data:
            element_type = facility.get("element_type", "unknown")
            stats["by_element_type"][element_type] = stats["by_element_type"].get(element_type, 0) + 1

        # Count by operator
        for facility in data:
            operator = facility.get("operator", "unknown")
            stats["by_operator"][operator] = stats["by_operator"].get(operator, 0) + 1

        return stats


def main():
    """Interactive main function to fetch and save facility data for Poland."""
    fetcher = PolandFacilityFetcher()

    print("Poland Facility Data Fetcher")
    print("=============================================================")
    print(f"Kraj: {fetcher.COUNTRY_NAME} ({fetcher.COUNTRY_CODE})")

    # Select facility type
    print("\nAvailable facility types:")
    for key, value in fetcher.FACILITY_TYPES.items():
        print(f"  {key}: {value['name']} / {value['name_en']}")

    facility_type = input("\nWybierz typ placówki / Select facility type: ").strip().lower()
    if facility_type not in fetcher.FACILITY_TYPES:
        print("Invalid facility type.")
        return

    try:
        # Fetch data
        print(f"Fetching data: {fetcher.FACILITY_TYPES[facility_type]['name_en']}...")
        data = fetcher.fetch_facilities(facility_type)

        if not data:
            print("No facilities found.")
            return

        # Show statistics
        stats = fetcher.get_facility_statistics(data)
        print("\nStatistics:")
        print(f"  Total facilities: {stats['total']}")
        print(f"  With names: {stats['with_names']}")
        print(f"  With coordinates: {stats['with_coordinates']}")
        print(f"  With phone numbers: {stats['with_phone']}")
        print(f"  With addresses: {stats['with_address']}")

        # Save to file
        filename = f"output/poland_{facility_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        fetcher.save_to_json(data, filename, facility_type)

        print(f"\nData saved to: {filename}")

        # Show sample data
        if data:
            print("\nSample facility:")
            sample = data[0]
            print(f"  Name: {sample.get('name', 'N/A')}")
            print(f"  Type: {sample.get('amenity') or sample.get('office') or sample.get('government')}")
            if sample["coordinates"]["lat"]:
                print(f"  Location: {sample['coordinates']['lat']}, {sample['coordinates']['lon']}")
            if sample.get("address"):
                addr = sample["address"]
                street = f"{addr.get('street', '')} {addr.get('housenumber', '')}".strip()
                city = addr.get("city", "")
                if street or city:
                    print(f" Address: {street}, {city}")
            if sample.get("polish_admin"):
                admin = sample["polish_admin"]
                if admin:
                    print(f"  Administrative unit: {list(admin.values())[0]}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
