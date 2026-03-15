import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.services.offers.offer_notification_service import OfferNotificationService
from app.database.models.enums import SourceType
from app.database.models.models import Offer

@pytest.fixture
def mock_slack_notifier():
    return AsyncMock()

@pytest.fixture
def mock_email_notifier():
    return AsyncMock()

@pytest.fixture
def notification_service(mock_slack_notifier, mock_email_notifier):
    return OfferNotificationService(
        slack_notifier=mock_slack_notifier,
        email_notifier=mock_email_notifier
    )

@pytest.mark.asyncio
async def test_notify_new_offer_slack_from_user(notification_service, mock_slack_notifier):
    offer_add = MagicMock()
    offer_add.source = SourceType.USER
    offer_add.author = "Test Author"
    offer_add.email = "test@example.com"
    offer_add.description = "Test Description"
    offer_uuid = str(uuid.uuid4())
    
    await notification_service.notify_new_offer_slack(offer_add, offer_uuid)
    
    mock_slack_notifier.send_new_offer_notification.assert_called_once_with(
        author="Test Author",
        email="test@example.com",
        description="Test Description",
        offer_uuid=offer_uuid
    )

@pytest.mark.asyncio
async def test_notify_new_offer_slack_from_bot_no_notify(notification_service, mock_slack_notifier):
    offer_add = MagicMock()
    offer_add.source = SourceType.BOT
    offer_uuid = str(uuid.uuid4())
    
    await notification_service.notify_new_offer_slack(offer_add, offer_uuid)
    
    mock_slack_notifier.send_new_offer_notification.assert_not_called()

@pytest.mark.asyncio
async def test_send_offer_imported_email_success(notification_service, mock_email_notifier):
    offer = MagicMock(spec=Offer)
    offer.email = "test@example.com"
    offer.author = "Test Author"
    offer_uuid = uuid.uuid4()
    
    mock_email_notifier.send_offer_imported_email.return_value = True
    
    await notification_service.send_offer_imported_email(offer, offer_uuid)
    
    mock_email_notifier.send_offer_imported_email.assert_called_once_with(
        recipient_email="test@example.com",
        recipient_name="Test Author",
        offer_uuid=str(offer_uuid)
    )

@pytest.mark.asyncio
async def test_send_offer_imported_email_failure(notification_service, mock_email_notifier):
    offer = MagicMock(spec=Offer)
    offer.email = "test@example.com"
    offer.author = None  # test default name "User"
    offer_uuid = uuid.uuid4()
    
    mock_email_notifier.send_offer_imported_email.return_value = False
    
    await notification_service.send_offer_imported_email(offer, offer_uuid)
    
    mock_email_notifier.send_offer_imported_email.assert_called_once_with(
        recipient_email="test@example.com",
        recipient_name="User",
        offer_uuid=str(offer_uuid)
    )
