"""preco equipamento

Revision ID: 6ddd0ee4b4d
Revises: 40fadf7b00a4
Create Date: 2015-11-27 11:44:47.434730

"""

# revision identifiers, used by Alembic.
revision = '6ddd0ee4b4d'
down_revision = '40fadf7b00a4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('preco_equipamento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('preco', sa.Numeric(scale=2), nullable=True),
    sa.Column('garantia_mes', sa.Integer(), nullable=True),
    sa.Column('inicio_vigencia', sa.Date(), nullable=True),
    sa.Column('equipamento_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['equipamento_id'], ['equipamento.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_column(u'equipamento', 'garantia_dias')
    op.drop_column(u'equipamento', 'preco')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(u'equipamento', sa.Column('preco', sa.NUMERIC(scale=2), autoincrement=False, nullable=True))
    op.add_column(u'equipamento', sa.Column('garantia_dias', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_table('preco_equipamento')
    ### end Alembic commands ###
