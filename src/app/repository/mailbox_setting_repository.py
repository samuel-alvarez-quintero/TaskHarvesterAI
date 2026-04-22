from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import MailboxSetting
from app.repository.base import BaseRepository


class MailboxSettingRepository(BaseRepository[MailboxSetting]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_active(self) -> MailboxSetting | None:
        return (
            self.session.query(MailboxSetting)
            .filter(MailboxSetting.is_active == 1)
            .order_by(MailboxSetting.id.asc())
            .first()
        )

    def get_by_account_and_mailbox(
        self, account_id: str, mailbox_name: str
    ) -> MailboxSetting | None:
        return (
            self.session.query(MailboxSetting)
            .filter(
                MailboxSetting.account_id == account_id,
                MailboxSetting.mailbox_name == mailbox_name,
            )
            .first()
        )

    def create_or_update(
        self,
        account_id: str,
        mailbox_name: str,
        imap_host: str,
        imap_port: int,
        imap_username: str,
        imap_password_secret_id: int | None,
        polling_interval_seconds: int = 300,
        is_active: bool = True,
    ) -> MailboxSetting:
        mailbox = self.get_by_account_and_mailbox(account_id, mailbox_name)
        if mailbox is None:
            mailbox = MailboxSetting(
                account_id=account_id,
                mailbox_name=mailbox_name,
                imap_host=imap_host,
                imap_port=imap_port,
                imap_username=imap_username,
                imap_password_secret_id=imap_password_secret_id,
                polling_interval_seconds=polling_interval_seconds,
                is_active=1 if is_active else 0,
            )
            self.add(mailbox)
            self.session.flush()
            return mailbox

        mailbox.imap_host = imap_host
        mailbox.imap_port = imap_port
        mailbox.imap_username = imap_username
        mailbox.imap_password_secret_id = imap_password_secret_id
        mailbox.polling_interval_seconds = polling_interval_seconds
        mailbox.is_active = 1 if is_active else 0
        mailbox.updated_at = datetime.now().astimezone()
        return mailbox
