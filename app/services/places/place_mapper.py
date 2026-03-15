from uuid import uuid4
from app.common.text_utils import sanitize_name, split_street
from app.schemas.domain.place import PlaceAdd

class PlaceMapper:
    @staticmethod
    def map_to_db_dict(place_add: PlaceAdd) -> dict:
        """Map PlaceAdd schema to a database-ready dictionary."""
        place_dict = {
            "uuid": str(uuid4()),
            "type": place_add.type,
            "name": place_add.name,
            "street_name": place_add.street_name,
            "street_number": place_add.street_number,
            "department": place_add.department,
            "name_ascii": sanitize_name(place_add.name),
            "category": place_add.category,
            "postal_code": place_add.postal_code,
            "city": place_add.city,
            "lat": place_add.lat,
            "lon": place_add.lon
        }

        # Handle street splitting if only combined street is provided
        if not place_add.street_name and place_add.street:
            street_name, street_number = split_street(place_add.street)
            place_dict["street_name"] = street_name
            place_dict["street_number"] = street_number
            
        return place_dict
