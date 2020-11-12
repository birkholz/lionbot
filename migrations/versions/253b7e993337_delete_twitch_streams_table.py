"""Delete twitch_streams table

Revision ID: 253b7e993337
Revises: 2de4fac3e7f9
Create Date: 2020-11-12 14:51:33.173460

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '253b7e993337'
down_revision = '2de4fac3e7f9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('twitch_streams')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('twitch_streams',
    sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
    sa.Column('guild_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], name='twitch_streams_guild_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='twitch_streams_pkey')
    )
    # ### end Alembic commands ###