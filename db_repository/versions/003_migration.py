from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
container = Table('container', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=50)),
    Column('description', String(length=5000)),
    Column('image', String(length=500)),
    Column('expose_ports', String(length=500)),
    Column('is_ready', Boolean),
    Column('port_titles', String(length=5000)),
    Column('port_icons', String(length=5000)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['container'].columns['port_icons'].create()
    post_meta.tables['container'].columns['port_titles'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['container'].columns['port_icons'].drop()
    post_meta.tables['container'].columns['port_titles'].drop()
