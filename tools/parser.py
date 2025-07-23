import json
import os
from datetime import date, time
from typing import Literal

import openai
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, EmailStr

# Load environment variables once at module level
load_dotenv()

# Constants
SOURCE_JSON = "rooms_data_poland_2025-02-25.json"
OPENAI_MODEL = "gpt-4.1-nano"
BASE_API_URL = os.getenv("BACKEND_URL")
SYSTEM_PROMPT = """
Z podanego opisu zastępstwa procesowego wyodrębnij następujące informacje:

- `location`: Typ instytucji – wybierz jedną z: "sąd", "policja", "prokuratura". Ustaw `null`, jeśli nie można określić.
- `location_full_name`: Pełna nazwa instytucji, np. "Sąd Rejonowy dla Warszawy-Mokotowa", lub `null`.
- `date`: Lista dat zastępstwa w formacie **RRRR-MM-DD (np. 2025-07-30)**. Jeśli podana jest tylko jedna, zwróć listę z jednym elementem. Jeśli brak – `null`.
- `time`: Lista godzin zastępstwa w formacie  **HH:MM** (24-godzinny format, np. 13:45). Jeśli brak – `null`.
- `description`: Krótkie streszczenie charakteru sprawy lub kontekstu. **Usuń email** jeżeli występuje.
- `target_audience`: Lista grup docelowych – wybierz spośród: "adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski". Jeśli brak informacji – `null`.
- `email`: Adres e-mail, jeśli występuje w opisie. Jeśli nie ma – `null`.

Zwróć dane w formacie JSON zgodnym ze schematem.
"""


class SubstitutionOffer(BaseModel):
    location: Literal["sąd", "policja", "prokuratura"] | None = None
    location_full_name: str | None = None
    date: list[str] | None = None
    time: list[str] | None = None
    description: str | None = None
    target_audience: list[Literal["adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski"]] | None = None
    email: EmailStr | None = None


def generate_ai_desc(text: str):
    """Generate AI description using OpenAI API."""
    client = openai.OpenAI(api_key=os.getenv("OPENAPI_KEY"))

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            functions=[
                {
                    "name": "generate_response",
                    "description": "Wygeneruj dane na podstawie opisu w języku polskim",
                    "parameters": SubstitutionOffer.model_json_schema(),
                }
            ],
            function_call={"name": "generate_response"},
            temperature=0.8,
        )

        function_args = response.choices[0].message.function_call.arguments
        args_dict = json.loads(function_args)  # load string into dict
        validated = SubstitutionOffer.model_validate(args_dict)  # allows coercion

        usage = response.usage
        logger.info(
            f"Tokens prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}, total: {usage.total_tokens}")

        result = validated.model_dump()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    except Exception as e:
        logger.error(f"Error generating AI description: {e}")
        return None


def main():
    text = "#SO Łodzi Fotokopia R.pr. , adw - faktura VAT Zlecenie wykonania fotokopii akt karnych (dochodzenie) dołączonych do akt sprawy cywilnej. Prosze o kontakt osoby, które mogą wykonać fotokopię w następnym tygodniu - 28 lipca- 1 sierpnia. Prosze o kontakt priv że wskazaniem stawki. Pozdrawiam r.pr r.pr 8w7YaReQ.com r.pr XcefP7wfg6ly2kXz1g8RdG47NQ5CSo o e r e L r M n a All reactions: 1 1"

    generate_ai_desc(text)
    # Optionally: Uncomment to parse entries from a JSON file
    # if os.path.exists(SOURCE_JSON):
    #     with open(SOURCE_JSON, "r", encoding="utf-8") as f:
    #         data = json.load(f)
    #         for i, item in enumerate(data):
    #             logger.info(f"Processing entry {i + 1}")
    #             generate_ai_desc(item.get("description", ""))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting gracefully.")
