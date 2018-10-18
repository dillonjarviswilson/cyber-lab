from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
session = Table('session', pre_meta,
    Column('id', INTEGER, primary_key=True, nullable=False),
    Column('unique_identifier', VARCHAR(length=300)),
    Column('ap_address', VARCHAR(length=30)),
    Column('client_address', VARCHAR(length=30)),
    Column('pos_address', VARCHAR(length=30)),
    Column('time_created', DATETIME),
    Column('user_number', INTEGER),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['session'].columns['user_number'].drop()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['session'].columns['user_number'].create()
