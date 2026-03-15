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
            "street_name": place_add.address.street_name if place_add.address else None,
            "street_number": place_add.address.street_number if place_add.address else None,
            "department": place_add.department,
            "name_ascii": sanitize_name(place_add.name),
            "category": place_add.category,
            "postal_code": place_add.address.postal_code if place_add.address else None,
            "city": place_add.address.city if place_add.address else None,
            "lat": place_add.coordinates.lat if place_add.coordinates else None,
            "lon": place_add.coordinates.lon if place_add.coordinates else None
        }

        # Handle street splitting if only combined street is provided
        if place_add.address and not place_add.address.street_name and place_add.address.street:
            street_name, street_number = split_street(place_add.address.street)
            place_dict["street_name"] = street_name
            place_dict["street_number"] = street_number

        return place_dict
