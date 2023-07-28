from flask import render_template, session, request, redirect, url_for, abort
from sib_api_v3_sdk.rest import ApiException
from werkzeug.utils import secure_filename
from app import mysql, socketio
from datetime import datetime
from flask import Blueprint
from io import BytesIO
import sib_api_v3_sdk
from PIL import Image
from app import app
import traceback
import bcrypt
import string
import imghdr
import qrcode
import pyotp
import uuid
import time
import os
import io
#Configure the sendinblue's API key
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = 'key'

profilis = Blueprint('profile', __name__)

connected_users = {}

namespace = '/profile'

global auth_secret

def generate_qr_code(email, secret_key, username):
    totp_uri = pyotp.totp.TOTP(secret_key).provisioning_uri(name=email, issuer_name='Transacto.lt')
    qrcode.make(totp_uri).save('static/img/' + username + '_qr.png')

def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

@socketio.on('connect', namespace=namespace)
def profile_connect():
    if session.get('loggedin', False):
        connected_users[session['username']] = request.sid
        cursor = mysql.get_db().cursor()
        cursor.execute("SELECT auth_secret from users WHERE username = %s", (session['username'], ))
        status = cursor.fetchone()
        if status[0] != "GA======":
            socketio.emit("remove_2fa_button", namespace=namespace, room=request.sid)
        
@profilis.route('/profile')
def profile():
    if session.get('loggedin', False):
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT name, userid, email from users WHERE username = %s', (session['username'], ))
        user = cursor.fetchone()
        cursor.close()
        return render_template('profile.html', name=user[0], userid=user[1], email=user[2])
    return redirect(url_for('main.login'))

@profilis.route('/password_confirm/<token>')
def confirm_password_change(token):
    cursor = mysql.get_db().cursor()
    cursor.execute('SELECT password_token, email, new_password from password_changes WHERE password_token = %s', (token, ))
    entry = cursor.fetchone()
    if token == entry[0]:
        cursor.execute('UPDATE users SET password = %s WHERE email = %s', (entry[2], entry[1]))
        mysql.get_db().commit()
        cursor.close()
        return 'Password change completed! You may now close this window.'
    cursor.close()
    return 'Failed to find the password change token!'

@socketio.on('generate_2fa', namespace=namespace)
def generate_2fa():
    cursor = mysql.get_db().cursor()
    cursor.execute('SELECT email from users WHERE username = %s', (session['username'], ))
    email = cursor.fetchone()
    cursor.close()
    auth_secret = pyotp.random_base32()
    session['auth_secret'] = auth_secret
    generate_qr_code(email[0], auth_secret, session['username'])
    socketio.emit('load_qr', data=session['username'], namespace=namespace, room=request.sid)

@socketio.on('confirm_2fa', namespace=namespace)
def confirm_2fa(totp_code):
    if session.get('loggedin', False):
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT auth_secret from users WHERE username = %s', (session['username'], ))
        db_auth_secret = cursor.fetchone()
        if db_auth_secret[0] == 'GA======':
            if pyotp.TOTP(session['auth_secret']).verify(totp_code):
                os.remove('static/img/' + session['username'] + '_qr.png')
                cursor.execute('UPDATE users SET auth_secret = %s WHERE username = %s', (session['auth_secret'], session['username']))
                mysql.get_db().commit()
                socketio.emit('send_notification', data='Successfully enabled 2FA!', namespace=namespace, room=request.sid)
            else:
                socketio.emit('send_notification', data='Incorrect 2FA code!', namespace=namespace, room=request.sid)
        else:
            socketio.emit('send_notification', data='You have already enabled 2FA!', namespace=namespace, room=request.sid)
        cursor.close()
    else:
        return redirect(url_for('main.login'))

@socketio.on('change_password', namespace=namespace)
def change_password(current_password, new_password, repeat_password):
    if session.get('loggedin', False):
        if new_password != repeat_password:
            socketio.emit('send_notification', data='The repeated password does not match!', namespace=namespace, room=request.sid)
            return
        #Salt and hash the password so we can check if it is the same in the database.
        password_bytes = current_password.encode('utf-8')
        salt = b'salt'
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT * FROM users WHERE username = % s AND password = % s', (session['username'], hashed_password, ))
        account = cursor.fetchone()
        if account:
            token = str(uuid.uuid4()) + '_' + str(int(time.time()))
            cursor.execute('SELECT email from users WHERE username = %s', (session['username'], ))
            email = cursor.fetchone()[0]
            #Salt and hash the password to store it in a database
            password_bytes = new_password.encode('utf-8')
            salt = b'salt'
            hashed_password = bcrypt.hashpw(password_bytes, salt)
            cursor.execute('INSERT INTO password_changes VALUES (%s, %s, %s)', (token, email, hashed_password))
            mysql.get_db().commit()
            #Send the confirmation link to the user
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            subject = "Please confirm your password change!"
            sender = {"name":"Transacto.lt","email":"noreply@transacto.lt"}
            reply_to = {"name":"Tranasacto support","email":"support@transacto.lt"}
            html_content = "<h3>Dear user,</h3><br />To confirm your password change, please visit this link: <br> https://transacto.lt/password_confirm/" + token + "<br />If you did not request a password change please ignore this email and change your password."
            to = [{"email":email}]
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to, reply_to=reply_to, html_content=html_content, sender=sender, subject=subject)

            try:
                api_response = api_instance.send_transac_email(send_smtp_email)
                print(api_response)
            except ApiException as e:
                print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
            socketio.emit('send_notification', data='Click on the link in the email we sent you to confirm the password change!', namespace=namespace, room=request.sid)
        else:
            msg = 'Incorrect password !'
        cursor.close()
    else:
        return redirect(url_for('main.login'))

@profilis.route('/email_confirm/<token>')
def confirm_email_change(token):
    cursor = mysql.get_db().cursor()
    cursor.execute('SELECT email_token, email, new_email from email_changes WHERE email_token = %s', (token, ))
    entry = cursor.fetchone()
    if token == entry[0]:
        cursor.execute('UPDATE users SET email = %s WHERE email = %s', (entry[2], entry[1]))
        mysql.get_db().commit()
        cursor.close()
        return 'Email change completed! You may now close this window.'
    cursor.close()
    return 'Failed to find the password change token!'

@profilis.route('/upload_profile_picture', methods=['POST'])
def upload_pfp():
    if session.get('loggedin', False):
        file = request.files['file']
        filename = secure_filename(file.filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS'] or \
                file_ext != validate_image(file.stream):
                return 'Please upload a valid image!'
            original_path = os.path.join(app.config['PFP_PATH'], session['username'] + '_original.jpg')
            file.save(original_path)

            image = Image.open(original_path)

            max_size = (800, 800)
            image.thumbnail(max_size, Image.ANTIALIAS)
            image = image.convert('RGB')
            resized_path = os.path.join(app.config['PFP_PATH'], session['username'] + '.jpg')
            image.save(resized_path)

            os.remove(original_path)
            return redirect(url_for('profile.profile'))
    else:
        return redirect(url_for('main.login'))

@socketio.on('change_email', namespace=namespace)
def change_password(new_email):
    if session.get('loggedin', False):
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT * FROM users WHERE email = % s', (new_email, ))
        account = cursor.fetchone()
        if not account:
            token = str(uuid.uuid4()) + '_' + str(int(time.time()))
            cursor.execute('SELECT email from users WHERE username = %s', (session['username'], ))
            email = cursor.fetchone()[0]
            cursor.execute('INSERT INTO email_changes VALUES (%s, %s, %s)', (token, email, new_email))
            mysql.get_db().commit()
            #Send the confirmation link to the user
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            subject = "Please confirm your email change!"
            sender = {"name":"Transacto.lt","email":"noreply@transacto.lt"}
            reply_to = {"name":"Tranasacto support","email":"support@transacto.lt"}
            html_content = "<h3>Dear user,</h3><br />To confirm your email change, please visit this link: <br> https://transacto.lt/email_confirm/" + token + "<br />If you did not request an email change please ignore this email and change your password."
            to = [{"email":new_email}]
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to, reply_to=reply_to, html_content=html_content, sender=sender, subject=subject)

            try:
                api_response = api_instance.send_transac_email(send_smtp_email)
                print(api_response)
            except ApiException as e:
                print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
            socketio.emit('send_notification', data='Click on the link in the email we sent you to confirm the email change!', namespace=namespace, room=request.sid)
        else:
            socketio.emit('send_notification', data='Email already exists!', namespace=namespace, room=request.sid)
        cursor.close()
    else:
        return redirect(url_for('main.login'))
