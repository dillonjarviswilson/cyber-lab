from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_socketio import SocketIO
from flask_admin import Admin


#basic config file
app = Flask(__name__)

app.config.from_object(Config)

socketio = SocketIO(app)

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

admin = Admin(app, name='Cyber-lab Admin', template_mode='bootstrap3')


#init database
db = SQLAlchemy(app)

import logging
logging.basicConfig(filename='error.log',level=logging.DEBUG)

from app import views, models
