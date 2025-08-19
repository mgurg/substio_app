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
                facility = self._extract_facility_data(node, "node", facility_type)
                if facility:
                    facilities.append(facility)

            # Process ways
            for way in result.ways:
                facility = self._extract_facility_data(way, "way", facility_type)
                if facility:
                    facilities.append(facility)

            # Process relations
            for relation in result.relations:
                facility = self._extract_facility_data(relation, "relation", facility_type)
                if facility:
                    facilities.append(facility)

            logger.info(f"Found {len(facilities)} {facility_config['name'].lower()}")
            return facilities

        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            raise

    def _extract_facility_data(self, element, element_type: str, facility_type: str) -> dict[str, Any] | None:
        tags = element.tags

        facility_name = tags.get("name")
        if not facility_name:
            return None

        # Coordinates
        if element_type == "node" and hasattr(element, "lat") and hasattr(element, "lon"):
            lat, lon = element.lat, element.lon
        elif hasattr(element, "center_lat") and hasattr(element, "center_lon"):
            lat, lon = element.center_lat, element.center_lon
        else:
            lat = lon = None

        if lat is None or lon is None:
            return None

        lat = float(lat)
        lon = float(lon)

        # Name-based type mapping
        name = tags.get("name", "").lower()
        type_code = None

        police_types = {
            "komenda powiatowa policji": "KPP",
            "komenda miejska policji": "KMP",
            "komenda główna policji": "KGP",
            "komisariat policji": "KP",
            "posterunek policji": "PP",
            "komenda wojewódzka policji": "KWP"
        }

        prosecutor_types = {
            "prokuratura okręgowa": "PO",
            "prokuratura rejonowa": "PR",
            "prokuratura generalna": "PG"
        }

        if facility_type == "police":
            for key, val in police_types.items():
                if key in name:
                    type_code = val
                    break
            if not type_code:
                type_code = "POL"
        elif facility_type == "prosecutor":
            for key, val in prosecutor_types.items():
                if key in name:
                    type_code = val
                    break
            if not type_code:
                type_code = "PRO"

        # Address parts
        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        postal_code = tags.get("addr:postcode")
        city = tags.get("addr:city")
        street_full = f"{street} {housenumber}".strip() if street or housenumber else None

        # Contact
        phone = tags.get("phone") or tags.get("contact:phone")
        email = tags.get("email") or tags.get("contact:email")
        website = tags.get("website") or tags.get("contact:website")

        return {
            "type": type_code,
            "name": facility_name,
            "street": street_full,
            "postal_code": postal_code,
            "city": city,
            "phone": phone,
            "email": email,
            "epuap": None,
            "department": None,
            "lat": lat,
            "lon": lon,
            "category": facility_type,
            "website": website,
        }

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
        if not data:
            return {"total": 0}

        stats = {
            "total": len(data),
            "with_names": sum(1 for f in data if f.get("name")),
            "with_coordinates": sum(1 for f in data if f.get("lat") and f.get("lon")),
            "with_phone": sum(1 for f in data if f.get("phone")),
            "with_address": sum(1 for f in data if f.get("street") and f.get("city")),
            "by_type": {}
        }

        for facility in data:
            type_ = facility.get("type", "unknown")
            stats["by_type"][type_] = stats["by_type"].get(type_, 0) + 1

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

    facility_type = input("\nSelect facility type: ").strip().lower()
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

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting gracefully.")
