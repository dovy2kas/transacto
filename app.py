from flask import Flask, render_template, request, redirect, url_for, session
from flask_recaptcha import ReCaptcha
from flask_socketio import SocketIO, emit
from flaskext.mysql import MySQL
from dotenv import load_dotenv
import re
import os

load_dotenv()

from gevent import monkey
monkey.patch_all()

app = Flask(__name__)
mysql = MySQL()
mysql.init_app(app)

app.config['MYSQL_DATABASE_HOST'] = os.getenv('MYSQL_DATABASE_HOST')
app.config['MYSQL_DATABASE_USER'] = os.getenv('MYSQL_DATABASE_USER')
app.config['MYSQL_DATABASE_PASSWORD'] = os.getenv('MYSQL_DATABASE_PASSWORD')
app.config['MYSQL_DATABASE_DB'] = os.getenv('MYSQL_DATABASE_DB')

app.secret_key = 'secret'

app.config['RECAPTCHA_SITE_KEY'] = 'key'
app.config['RECAPTCHA_SECRET_KEY'] = 'secret'

app.config['SECURITY_PASSWORD_SALT'] = 'salt'

app.config['Mailjet_API_key'] = 'key'
app.config['Mailjet_API_secret'] = 'secret'

app.config['MAX_IMAGE_LENGTH'] = 1024 * 1024
app.config['PFP_PATH'] = 'static/pfp/'
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png']

socketio = SocketIO(app, async_handlers=True, cors_allowed_origins='*', async_mode='gevent', engineio_logger=True)

recaptcha = ReCaptcha(app)
mysql.init_app(app)

from dashboard import dashboard
app.register_blueprint(dashboard)

from transactions import transactions
app.register_blueprint(transactions)

from main import main
app.register_blueprint(main)

from profile import profilis
app.register_blueprint(profilis)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', cors_allowed_origins='*', debug=True)
