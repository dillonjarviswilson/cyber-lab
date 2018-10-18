from app import app, db
import logging, logging.config

logfile    = logging.getLogger('file')
logconsole = logging.getLogger('console')


@app.before_first_request
def before_first_request():

    # Create any database tables that don't exist yet.
    db.create_all()
