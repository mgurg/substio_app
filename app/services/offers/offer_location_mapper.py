from app.database.models.models import Offer


class OfferLocationMapper:
    @staticmethod
    def assign_place_to_data(offer_data: dict, place, place_name: str | None = None) -> None:
        if place is not None:
            offer_data["place_id"] = place.id
            offer_data["lat"] = place.lat
            offer_data["lon"] = place.lon
            offer_data["place_name"] = place_name or place.name

    @staticmethod
    def assign_city_to_data(offer_data: dict, city, city_name: str | None = None) -> None:
        if city is not None:
            offer_data["city_id"] = city.id
            offer_data["lat"] = city.lat
            offer_data["lon"] = city.lon
            offer_data["city_name"] = city_name or city.name

    @staticmethod
    def assign_place_to_offer(db_offer: Offer, place, place_name: str | None = None) -> None:
        if place is not None:
            db_offer.lat = place.lat
            db_offer.lon = place.lon
            db_offer.place = place
            db_offer.place_name = place_name or place.name

    @staticmethod
    def assign_city_to_offer(db_offer: Offer, city, city_name: str | None = None) -> None:
        if city is not None:
            db_offer.lat = city.lat
            db_offer.lon = city.lon
            db_offer.city = city
            db_offer.city_name = city_name or city.name
