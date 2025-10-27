import logging
import hmac
import hashlib
from typing import Dict, Any
from fastapi import HTTPException, Header, Request
from app.config import settings

logger = logging.getLogger(__name__)


def verify_gitlab_signature(payload: bytes, signature: str) -> bool:

    if not settings.GITLAB_WEBHOOK_SECRET:
        logger.warning("GITLAB_WEBHOOK_SECRET not set, skipping signature verification")
        return True

    expected_token = settings.GITLAB_WEBHOOK_SECRET
    return hmac.compare_digest(signature, expected_token)


class WebhookHandler:

    def __init__(self, analyzer):

        self.analyzer = analyzer

    async def handle_push_event(
        self,
        payload: Dict[str, Any],
        gitlab_token: str
    ) -> Dict[str, Any]:

        if not self.verify_token(gitlab_token):
            raise HTTPException(status_code=401, detail="Invalid webhook token")

        event_name = payload.get('event_name')
        object_kind = payload.get('object_kind')

        logger.info(f"Received webhook: event={event_name}, kind={object_kind}")

        if object_kind != 'push':
            return {
                'status': 'skipped',
                'reason': f'Not a push event: {object_kind}'
            }

        result = self.analyzer.process_commit(payload)

        return result

    def verify_token(self, provided_token: str) -> bool:
        if not settings.GITLAB_WEBHOOK_SECRET:
            logger.warning("GITLAB_WEBHOOK_SECRET not set")
            return True

        expected = settings.GITLAB_WEBHOOK_SECRET
        return hmac.compare_digest(provided_token, expected)


class WebhookQueue:

    def __init__(self):
        self.queue = []
        self.processing = False

    def add(self, event_data: Dict[str, Any]):
        self.queue.append(event_data)
        logger.info(f"Added to queue. Queue size: {len(self.queue)}")

    def get_next(self) -> Dict[str, Any]:
        if self.queue:
            return self.queue.pop(0)
        return None

    def size(self) -> int:
        return len(self.queue)

    def is_empty(self) -> bool:
        return len(self.queue) == 0
