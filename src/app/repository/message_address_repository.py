from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import MessageAddress
from app.repository.base import BaseRepository


class MessageAddressRepository(BaseRepository[MessageAddress]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_message_id(self, message_id: int) -> list[MessageAddress]:
        return self.list(MessageAddress, MessageAddress.message_row_id == message_id)

    def create_message_address(
        self,
        message_id: int,
        address_role: str,
        display_name: str | None,
        email_address: str,
    ) -> MessageAddress:
        address = MessageAddress(
            message_row_id=message_id,
            address_role=address_role,
            display_name=display_name,
            email_address=email_address,
        )
        return self.add(address)
