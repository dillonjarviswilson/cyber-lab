from flask import Flask
from flask_sqlalchemy import SQLAlchemy


#basic config file
app = Flask(__name__)
app.config.from_object('config')

#init database
db = SQLAlchemy(app)

import logging
logging.basicConfig(filename='error.log',level=logging.DEBUG)

from app import views, models
