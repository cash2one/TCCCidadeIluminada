"""quantidade material

Revision ID: e2c0d6f51ee
Revises: 6ddd0ee4b4d
Create Date: 2015-11-27 13:32:14.944291

"""

# revision identifiers, used by Alembic.
revision = 'e2c0d6f51ee'
down_revision = '6ddd0ee4b4d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('material', sa.Column('quantidade', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('material', 'quantidade')
    ### end Alembic commands ###
