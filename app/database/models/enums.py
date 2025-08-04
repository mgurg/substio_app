from enum import Enum


class SourceType(Enum):
    BOT = "bot"
    USER = "user"


class OfferStatus(Enum):
    NEW = "new"
    DRAFT = "draft"
    PROCESSED = "processed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ACTIVE = "active"


class PlaceCategory(Enum):
    PROSECUTOR = "prosecutor"
    COURT = "court"
    POLICE = "police"
    OTHER = "other"


class Voivodeship(Enum):
    DOLNOSLASKIE = "Dolnośląskie"
    KUJAWSKO_POMORSKIE = "Kujawsko-Pomorskie"
    LUBELSKIE = "Lubelskie"
    LUBUSKIE = "Lubuskie"
    LODZKIE = "Łódzkie"
    MALOPOLSKIE = "Małopolskie"
    MAZOWIECKIE = "Mazowieckie"
    OPOLSKIE = "Opolskie"
    PODKARPACKIE = "Podkarpackie"
    PODLASKIE = "Podlaskie"
    POMORSKIE = "Pomorskie"
    SLASKIE = "Śląskie"
    SWIETOKRZYSKIE = "Świętokrzyskie"
    WARMINSKO_MAZURSKIE = "Warmińsko-Mazurskie"
    WIELKOPOLSKIE = "Wielkopolskie"
    ZACHODNIOPOMORSKIE = "Zachodniopomorskie"
