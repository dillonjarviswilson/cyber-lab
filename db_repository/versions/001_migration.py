from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
session = Table('session', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('user_number', Integer),
    Column('unique_identifier', String(length=300)),
    Column('ap_address', String(length=30)),
    Column('client_address', String(length=30)),
    Column('pos_address', String(length=30)),
    Column('time_created', DateTime),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['session'].columns['user_number'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['session'].columns['user_number'].drop()
