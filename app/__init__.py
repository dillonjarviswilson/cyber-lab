from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

#basic config file
app = Flask(__name__)

app.config.from_object(Config)

#init database
db = SQLAlchemy(app)

import logging
logging.basicConfig(filename='error.log',level=logging.DEBUG)

from app import views, models
