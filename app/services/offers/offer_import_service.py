import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from starlette.status import HTTP_409_CONFLICT

from app.database.models.enums import OfferStatus, SourceType
from app.repositories.offer_repo import OfferRepo
from app.schemas.domain.offer import FacebookPost, ImportResult, OfferRawAdd
from app.utils.email_utils import extract_and_fix_email
from app.utils.timestamp_utils import extract_timestamp_from_filename


def parse_facebook_post_to_offer(post: FacebookPost, filename: str | None) -> "OfferRawAdd":
    """
    Convert a FacebookPost model into an OfferAdd object.
    Falls back to the filename timestamp or current datetime if date_posted is missing/invalid.
    """
    timestamp = datetime.now(UTC)

    if post.date_posted:
        try:
            timestamp = datetime.fromisoformat(post.date_posted)
        except ValueError:
            if filename:
                timestamp = extract_timestamp_from_filename(filename)
    elif filename:
        timestamp = extract_timestamp_from_filename(filename)

    return OfferRawAdd(
        raw_data=post.post_content,
        author=post.user_name,
        author_uid=post.user_profile_url,
        offer_uid=post.post_url,
        timestamp=timestamp,
        source=SourceType.BOT,
    )


class OfferImportService:
    def __init__(self, offer_repo: OfferRepo) -> None:
        self.offer_repo = offer_repo

    async def import_raw_offers(self, file: UploadFile) -> ImportResult:
        self._validate_json_upload(file)
        try:
            json_data = self._parse_json_upload(await file.read())
        except HTTPException:
            raise
        except json.JSONDecodeError as err:
            raise HTTPException(status_code=400, detail="Invalid JSON file") from err
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}") from e

        import_result = ImportResult(total_records=len(json_data), imported_records=0, skipped_records=0, errors=[])

        for i, post_data in enumerate(json_data, start=1):
            await self._import_single_post(post_data, file.filename, i, import_result)

        return import_result

    async def create_raw_offer(self, offer: OfferRawAdd) -> None:
        db_offer = await self.offer_repo.get_by_offer_uid(offer.offer_uid)
        if db_offer:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"Offer with {offer.offer_uid} already exists")
        email = None
        if isinstance(offer.raw_data, str):
            email = extract_and_fix_email(offer.raw_data)

        offer_data = {
            "uuid": str(uuid4()),
            "author": offer.author,
            "author_uid": offer.author_uid,
            "offer_uid": offer.offer_uid,
            "raw_data": offer.raw_data,
            "added_at": offer.timestamp,
            "source": offer.source,
            "status": OfferStatus.POSTPONED,
        }

        if email:
            offer_data["email"] = email
            offer_data["status"] = OfferStatus.NEW

        await self.offer_repo.create(**offer_data)
        return None

    def _validate_json_upload(self, file: UploadFile) -> None:
        if not file.filename or not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="File must be a JSON file")

    def _parse_json_upload(self, content: bytes) -> list[dict]:
        json_data = json.loads(content.decode("utf-8"))
        if not isinstance(json_data, list):
            raise HTTPException(status_code=400, detail="JSON file must contain an array of posts")
        return json_data

    async def _import_single_post(
        self, post_data: dict, filename: str | None, index: int, import_result: ImportResult
    ) -> None:
        try:
            post = FacebookPost.model_validate(post_data)
            if "nieaktualne" in post.post_content.lower():
                import_result.skipped_records += 1
                import_result.errors.append(f"Record {index + 1}: nieaktualne")
                return

            offer = parse_facebook_post_to_offer(post, filename)
            await self.create_raw_offer(offer)
            import_result.imported_records += 1

        except HTTPException as e:
            if e.status_code == 409:
                import_result.skipped_records += 1
                import_result.errors.append(f"Record {index + 1}: {e.detail}")
            else:
                import_result.errors.append(f"Record {index + 1}: {e.detail}")
        except Exception as e:
            import_result.errors.append(f"Record {index + 1}: {str(e)}")
