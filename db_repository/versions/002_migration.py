from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
port_table = Table('port_table', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('session_id', Integer, nullable=False),
    Column('container_id', Integer, nullable=False),
    Column('friendly_name', String(length=300)),
    Column('internal_port', Integer),
    Column('external_port', Integer),
    Column('url', String(length=300)),
    Column('title', String(length=300)),
    Column('show_as_window', Boolean),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['port_table'].columns['show_as_window'].create()
    post_meta.tables['port_table'].columns['title'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['port_table'].columns['show_as_window'].drop()
    post_meta.tables['port_table'].columns['title'].drop()
