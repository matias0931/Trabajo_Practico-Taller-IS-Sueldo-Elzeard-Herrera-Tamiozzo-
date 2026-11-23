"""Restricciones de votos

Revision ID: c7a4e9f1b2d3
Revises: 48411a29c46f
Create Date: 2026-11-23 10:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c7a4e9f1b2d3"
down_revision = "48411a29c46f"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite no permite agregar constraints con ALTER TABLE, por eso se usa
    # batch_alter_table: Alembic recrea la tabla y copia los datos.
    with op.batch_alter_table("votos", schema=None) as batch_op:
        batch_op.create_check_constraint("ck_votos_valor", "valor IN (-1, 1)")
        batch_op.create_check_constraint(
            "ck_votos_un_destino",
            "(pregunta_id IS NOT NULL) != (respuesta_id IS NOT NULL)",
        )
        batch_op.create_unique_constraint(
            "uq_votos_usuario_pregunta", ["usuario_id", "pregunta_id"]
        )
        batch_op.create_unique_constraint(
            "uq_votos_usuario_respuesta", ["usuario_id", "respuesta_id"]
        )


def downgrade():
    with op.batch_alter_table("votos", schema=None) as batch_op:
        batch_op.drop_constraint("uq_votos_usuario_respuesta", type_="unique")
        batch_op.drop_constraint("uq_votos_usuario_pregunta", type_="unique")
        batch_op.drop_constraint("ck_votos_un_destino", type_="check")
        batch_op.drop_constraint("ck_votos_valor", type_="check")
