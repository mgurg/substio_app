from uuid import uuid4

from app.common.text_utils import sanitize_name
from app.schemas.domain.place import CityAdd


class CityMapper:
    @staticmethod
    def map_to_db_dict(city: CityAdd) -> dict:
        """Map CityAdd schema to a database-ready dictionary."""
        return {
            "uuid": str(uuid4()),
            "name": city.city_name,
            "name_ascii": sanitize_name(city.city_name),
            "lat": city.coordinates.lat,
            "lon": city.coordinates.lon,
            "lat_min": city.range.lat_min if city.range else None,
            "lat_max": city.range.lat_max if city.range else None,
            "lon_min": city.range.lon_min if city.range else None,
            "lon_max": city.range.lon_max if city.range else None,
            "population": city.population,
            "importance": city.importance,
            "category": city.category,
            "voivodeship_name": city.voivodeship_name,
            "voivodeship_iso": city.voivodeship_iso,
            "teryt_simc": city.teryt_simc if city.teryt_simc else None,
        }
