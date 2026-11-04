"""tool basket unique by range

Revision ID: 8b4cd046dc20
Revises: 36cc6898690f
Create Date: 2026-11-02

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "8b4cd046dc20"
down_revision: Union[str, None] = "36cc6898690f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_tool_basket", "tool_baskets", type_="unique")
    op.create_index(
        "uq_tool_basket",
        "tool_baskets",
        [
            "operation_group",
            "material_iso_group",
            text("coalesce(diameter_from_mm, -1)"),
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_tool_basket", table_name="tool_baskets")
    op.create_unique_constraint(
        "uq_tool_basket",
        "tool_baskets",
        ["operation_group", "material_iso_group"],
    )
