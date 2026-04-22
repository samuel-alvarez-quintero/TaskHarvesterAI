"""add config and prompt tables

Revision ID: 0f9e7d1b2c3a
Revises: a6b308e0ea40
Create Date: 2026-04-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f9e7d1b2c3a"
down_revision: Union[str, Sequence[str], None] = "a6b308e0ea40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "secret_store",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("secret_name", sa.String(), nullable=False),
        sa.Column("secret_type", sa.String(), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("key_version", sa.String(), server_default=sa.text("'v1'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("secret_name"),
    )
    op.create_index("idx_secret_store_secret_type", "secret_store", ["secret_type"], unique=False)

    op.create_table(
        "workspace_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("setting_key", sa.String(), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
    )
    op.create_index(
        "idx_workspace_settings_key",
        "workspace_settings",
        ["setting_key"],
        unique=True,
    )

    op.create_table(
        "mailbox_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("mailbox_name", sa.String(), server_default=sa.text("'INBOX'"), nullable=False),
        sa.Column("imap_host", sa.String(), nullable=False),
        sa.Column("imap_port", sa.Integer(), server_default=sa.text("993"), nullable=False),
        sa.Column("imap_username", sa.String(), nullable=False),
        sa.Column("imap_password_secret_id", sa.Integer(), nullable=True),
        sa.Column(
            "polling_interval_seconds",
            sa.Integer(),
            server_default=sa.text("300"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["imap_password_secret_id"], ["secret_store.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_mailbox_settings_account_mailbox",
        "mailbox_settings",
        ["account_id", "mailbox_name"],
        unique=False,
    )
    op.create_index("idx_mailbox_settings_active", "mailbox_settings", ["is_active"], unique=False)

    op.create_table(
        "llm_provider_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mailbox_id", sa.Integer(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("api_key_secret_id", sa.Integer(), nullable=True),
        sa.Column(
            "request_timeout_seconds",
            sa.Integer(),
            server_default=sa.text("120"),
            nullable=False,
        ),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["api_key_secret_id"], ["secret_store.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mailbox_id"], ["mailbox_settings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_llm_provider_settings_mailbox_id",
        "llm_provider_settings",
        ["mailbox_id"],
        unique=False,
    )
    op.create_index(
        "idx_llm_provider_settings_active",
        "llm_provider_settings",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mailbox_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("language_hint", sa.String(), server_default=sa.text("'English'"), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("json_response_schema", sa.Text(), nullable=False),
        sa.Column("context_template", sa.Text(), nullable=False),
        sa.Column("message_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["mailbox_id"], ["mailbox_settings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_prompt_templates_mailbox_operation",
        "prompt_templates",
        ["mailbox_id", "operation"],
        unique=False,
    )
    op.create_index("idx_prompt_templates_active", "prompt_templates", ["is_active"], unique=False)

    op.create_table(
        "prompt_template_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prompt_template_id", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(), nullable=False),
        sa.Column("language_hint", sa.String(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["prompt_template_id"], ["prompt_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_prompt_template_versions_template_id",
        "prompt_template_versions",
        ["prompt_template_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_prompt_template_versions_template_id", table_name="prompt_template_versions")
    op.drop_table("prompt_template_versions")
    op.drop_index("idx_prompt_templates_active", table_name="prompt_templates")
    op.drop_index("idx_prompt_templates_mailbox_operation", table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_index("idx_llm_provider_settings_active", table_name="llm_provider_settings")
    op.drop_index("idx_llm_provider_settings_mailbox_id", table_name="llm_provider_settings")
    op.drop_table("llm_provider_settings")
    op.drop_index("idx_mailbox_settings_active", table_name="mailbox_settings")
    op.drop_index("idx_mailbox_settings_account_mailbox", table_name="mailbox_settings")
    op.drop_table("mailbox_settings")
    op.drop_index("idx_workspace_settings_key", table_name="workspace_settings")
    op.drop_table("workspace_settings")
    op.drop_index("idx_secret_store_secret_type", table_name="secret_store")
    op.drop_table("secret_store")
