from uuid import uuid4
from app.common.text_utils import sanitize_name
from app.schemas.rest.requests import CityAdd

class CityMapper:
    @staticmethod
    def map_to_db_dict(city: CityAdd) -> dict:
        """Map CityAdd schema to a database-ready dictionary."""
        return {
            "uuid": str(uuid4()),
            "name": city.city_name,
            "name_ascii": sanitize_name(city.city_name),
            "lat": city.lat,
            "lon": city.lon,
            "lat_min": city.lat_min,
            "lat_max": city.lat_max,
            "lon_min": city.lon_min,
            "lon_max": city.lon_max,
            "population": city.population,
            "importance": city.importance,
            "category": city.category,
            "voivodeship_name": city.voivodeship_name,
            "voivodeship_iso": city.voivodeship_iso,
            "teryt_simc": city.teryt_simc if city.teryt_simc else None,
        }
