from __future__ import print_function
from flask import render_template, session, request, redirect, url_for, jsonify, after_this_request
from itsdangerous import URLSafeTimedSerializer
from decimal import Decimal, InvalidOperation
from sib_api_v3_sdk.rest import ApiException
from flask_socketio import SocketIO, emit
from app import mysql, socketio, recaptcha
from datetime import datetime
from flask import Blueprint
main = Blueprint('main', __name__)
import sib_api_v3_sdk
import paypalrestsdk
from app import app
import urllib.parse
import traceback
import requests
import hashlib
import base64
import random
import string
import bcrypt
import pyotp
import json
import uuid
import time
import re
import os

global money_cents

#Configure paysera's API
project_id = 000000
sign_password = 'pass'

#Configure the sendinblue's API key
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = 'key'

#Configure paypal's rest sdk keys
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": "id",
    "client_secret": "secret"
})

namespace = '/main'

#Make a list of connected users to identify sessions with usernames
connected_users = {}

def is_valid_email(email):
    """Check if the email address is valid"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_token(email):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])

def confirm_token(token, expiration=2629800):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(
            token, salt=app.config["SECURITY_PASSWORD_SALT"], max_age=expiration
        )
        return email
    except Exception:
        traceback.print_exc()
        return False

def generate_user_id(cursor, first_name, last_name):
    while True:
        # Generate a random 6-digit number
        random_number = ''.join(random.choices(string.digits, k=6))
        # Construct the user ID using the first and last name initials and the random number
        user_id = f"{first_name[0].upper()}{last_name[0].upper()}-{random_number}"
        # Check if the user ID already exists in the "users" table
        cursor = mysql.get_db().cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM users WHERE userid = %s)", (user_id,))
        cursor.close()
        if not cursor.fetchone()[0]:
            # If the user ID doesn't exist, return it
            return user_id

#Generate a data variable for paysera's deposits
def generate_sign(params, password):
    query_string = urllib.parse.urlencode(params)
    base64_encoded = base64.b64encode(query_string.encode('utf-8')).decode('utf-8')
    base64_encoded = base64_encoded.replace('/', '_').replace('+', '-')
    sign_data = f'{base64_encoded}{password}'.encode('utf-8')
    md5_hash = hashlib.md5(sign_data).hexdigest()
    print(base64_encoded)
    return md5_hash, base64_encoded

#Decode the reverse data for the callback
def reverse_generated_sign(base64_encoded):
    params = {}
    data = str.replace(str.replace(base64_encoded, '-', '+'), '_', '/')
    decoded_data = base64.b64decode(data)
    decoded_str = decoded_data.decode('utf-8')
    for pair in decoded_str.split('&'):
        key_value = pair.split('=')
        params[key_value[0]] = key_value[1]
    return params

def validate_amounts(amount):
    if amount.isdigit() and amount > 0:
        return round(amount, 2)
    else:
        return -1

@socketio.on('connect', namespace=namespace)
def main_connect():
        if session.get('loggedin', False):
                connected_users[session['username']] = request.sid
                cursor = mysql.get_db().cursor()
                cursor.execute('SELECT balance from users WHERE username = %s', (session['username'], ))
                balance = cursor.fetchone()
                socketio.emit('update_balance', data=(balance), namespace=namespace, room=request.sid)
                cursor.close()
        else:
                socketio.emit('update_balance', data=(0), namespace=namespace, room=request.sid)

@main.route("/confirm/<token>")
def confirm_email(token):
    cursor = mysql.get_db().cursor()
    cursor.execute('SELECT is_confirmed FROM users WHERE confirmation_token = % s', (token, ))
    is_confirmed = cursor.fetchone()
    if is_confirmed == 1:
        msg = "Account already confirmed."
        cursor.close()
        return redirect(url_for("dashboard.index", msg = msg))
    email = confirm_token(token)
    cursor.execute('SELECT email FROM users WHERE confirmation_token = % s', (token, ))
    user_email = cursor.fetchone()
    if user_email[0] == email:
        cursor.execute('UPDATE users SET is_confirmed = 1 WHERE confirmation_token = %s', (token, ))
        mysql.get_db().commit()
        msg = "You have confirmed your account. Thanks!"
    else:
        msg = "The confirmation link is invalid or has expired."
    cursor.close()
    return redirect(url_for("dashboard.index", msg = msg))

@main.route('/')
def index():
    if session.get('loggedin', False):
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('loggedin', False):
        return redirect(url_for('dashboard.index'))
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        #Salt and hash the password so we can check if it is the same in the database.
        password = request.form['password']
        password_bytes = password.encode('utf-8')
        salt = b'$2b$12$DFovMLKRCIRvThwljjV6Nu'
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT * FROM users WHERE username = % s AND password = % s', (username, hashed_password, ))
        account = cursor.fetchone()
        cursor.close()
        if account:
            if account[12] != 'GA======':
                if account and pyotp.TOTP(account[12]).verify(request.form['totp_code']):
                    session['loggedin'] = True
                    session['id'] = account[0]
                    session['username'] = account[1]
                    return redirect(url_for('dashboard.index'))
                else:
                    msg = 'Incorrect username / password / two factor code!'
            else:
                if account:
                    session['loggedin'] = True
                    session['id'] = account[0]
                    session['username'] = account[1]
                    return redirect(url_for('dashboard.index'))
                else:
                    msg = 'Incorrect username / password!'
        else:
            msg = 'Incorrect username / password!'
    return render_template('login.html', msg = msg)

@main.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('main.login'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('loggedin', False):
        return redirect(url_for('dashboard.index'))
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        if recaptcha.verify():
            username = request.form['username']

            #Salt and hash the password so it is safe from attacks.
            password = request.form['password']
            password_bytes = password.encode('utf-8')
            salt = b'salt'
            hashed_password = bcrypt.hashpw(password_bytes, salt)

            email = request.form['email']

            if is_valid_email(email) == False:
                msg = 'Please provide a valid email address!'
                return render_template('register.html', msg = msg)

            name = request.form['name']
            surname = request.form['surname']
            cursor = mysql.get_db().cursor()
            cursor.execute('SELECT * FROM users WHERE username = % s OR email = % s', (username, email, ))
            account = cursor.fetchone()
            cursor.close()
            if account:
                msg = 'Account already exists !'
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                msg = 'Invalid email address !'
            elif not re.match(r'[A-Za-z0-9]+', username):
                msg = 'Username must contain only characters and numbers !'
            elif request.form['password'] != request.form['repeat_password']:
                msg = 'The passwords do not match!'
            elif not username or not password or not email or not name or not surname:
                msg = 'Please fill out the form !'
            else:
                #Generate a token for email verification
                token = generate_token(email)
                user_id = generate_user_id(cursor, name, surname)
                current_time = datetime.now()
                auth_secret = 'secret'
                cursor = mysql.get_db().cursor()
                cursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (username, name, surname, email, hashed_password, 0, current_time, 0, user_id, token, str(request.headers.get('cf-connecting-ip')), auth_secret))
                mysql.get_db().commit()
                cursor.close()
                msg = 'You have successfully registered! Please check your email inbox to confirm your email.'

                #Send the confirmation link to the user

                api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
                subject = "Please confirm your email address!"
                sender = {"name":"Transacto.lt","email":"noreply@transacto.lt"}
                reply_to = {"name":"Tranasacto support","email":"support@transacto.lt"}
                html_content = "<h3>Dear user, welcome to <a href=\"https://transacto.lt/\">Transacto</a>!</h3><br />To confirm your email address, please visit this link: <br> https://transacto.lt/confirm/" + token
                to = [{"email":email}]
                send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to, reply_to=reply_to, html_content=html_content, sender=sender, subject=subject)

                try:
                    api_response = api_instance.send_transac_email(send_smtp_email)
                    print(api_response)
                except ApiException as e:
                    print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
        else:
            msg = 'Please fill out the ReCaptcha!'
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg = msg)

@main.route('/deposit')
def deposit():
    if session.get('loggedin', False):
        return render_template('depo.html')
    return redirect(url_for('main.login'))

@main.route('/paysera_accept')
def paysera_accept():
    print('accepted')
    return 'thx for buying'

@main.route('/paysera_cancel')
def paysera_cancel():
    print('cancelled')
    return 'f u bitch'

@main.route('/paysera_callback')
def paysera_callback():
    data = request.args.get('data')
    params = reverse_generated_sign(data)
    cursor = mysql.get_db().cursor()
    cursor.execute("SELECT currency, amount from paysera_deposits WHERE order_id = %s", (params['orderid'], ))
    print(f"params orderid: {params['orderid']}")
    transaction = cursor.fetchall()

    if int(params['status']) == 1 and str(params['currency']) == str(transaction[0][0]) and int(params['amount']) == int(transaction[0][1]):
        cursor.execute("SELECT username from paysera_deposits WHERE order_id = %s", (params['orderid'], ))
        username = cursor.fetchone()[0]
        cursor.execute("SELECT balance, userid from users WHERE username = %s", (username, ))
        user = cursor.fetchall()
        new_balance = user[0][0] + int(params['amount']) / 100
        cursor.execute('UPDATE users SET balance = %s WHERE username = %s', (new_balance, username))
        mysql.get_db().commit()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute('INSERT INTO transactions VALUES (NULL, %s, %s, %s, %s, %s)', ('Transacto.lt', user[0][1], int(params['amount']) / 100, 'Deposit', current_time))
        mysql.get_db().commit()
        cursor.execute('UPDATE paysera_deposits SET status = %s WHERE order_id = %s', (1, params['orderid']))
        mysql.get_db().commit()
        cursor.close()
        return 'OK'
    else:
        cursor.close()
        print('NO')
        return 'NO'

@socketio.on('get_news', namespace = namespace)
def get_news():
    if session.get('loggedin', False):
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT message, seen from news WHERE username = %s OR username = %s', (session['username'], "all", ))
        news = cursor.fetchall()
        for new in news:
            socketio.emit('add_news', data=new[0], namespace=namespace, room=request.sid)
            if '0' in new[1]:
                socketio.emit('news_unseen', namespace=namespace, room=request.sid)
        cursor.close()

@socketio.on('news_status', namespace=namespace)
def set_news_status():
    if session.get('loggedin', False):
        cursor = mysql.get_db().cursor()
        cursor.execute('UPDATE news SET seen = %s WHERE username = %s OR username = %s', (1, session['username'], "all"))
        mysql.get_db().commit()
        cursor.close()

@socketio.on('paypal_payment', namespace=namespace)
def paypal_payment(amount):
    if session.get('loggedin', False):
        amount = validate_amounts(amount)
        if amount > 0:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": "https://transacto.lt/dashboard",
                    "cancel_url": "https://transacto.lt/dashboard"},
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": "Balance for Transacto.lt",
                            "sku": "12345",
                            "price": amount,
                            "currency": "EUR",
                            "quantity": 1}]},
                    "amount": {
                        "total": amount,
                        "currency": "EUR"},
                    "description": "This is the payment transaction description."}]})

            if payment.create():
                print('Payment success!')
            else:
                socketio.emit('send_notification', data=payment.error.problem, namespace=namespace, room=request.sid)
            socketio.emit('paypal_payment_response', data=payment.id, namespace=namespace, room=request.sid)
        else:
            socketio.emit('send_notification', data="Invalid amount!", namespace=namespace, room=request.sid)
    else:
        return redirect(url_for('main.login'))

@socketio.on('paypal_execute', namespace=namespace)
def paypal_execute(paymentID, payerID, amount):
    if session.get('loggedin', False):
        amount = validate_amounts(amount)
        if amount > 0:
            success = False

            payment = paypalrestsdk.Payment.find(paymentID)

            if payment.execute({'payer_id' : payerID}):
                #Update balance and insert the transaction into database.
                cursor = mysql.get_db().cursor()
                cursor.execute("SELECT balance, userid from users WHERE username = %s", (session['username'], ))
                user = cursor.fetchall()
                new_balance = user[0][0] + float(amount)
                cursor.execute('UPDATE users SET balance = %s WHERE username = %s', (new_balance, session['username']))
                mysql.get_db().commit()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute('INSERT INTO transactions VALUES (NULL, %s, %s, %s, %s, %s)', ('Transacto.lt', user[0][1], amount, 'Deposit', current_time))
                mysql.get_db().commit()
                socketio.emit('send_notification', data='Deposit completed successfully!', namespace=namespace, room=request.sid)
                cursor.close()
                success = True

            else:
                socketio.emit('send_notification', data=payment.error, namespace=namespace, room=request.sid)
        else:
            socketio.emit('send_notification', data="Invalid amount!", namespace=namespace, room=request.sid)
        socketio.emit('paypal_execute_response', data=success, namespace=namespace, room=request.sid)
    else:
        return redirect(url_for('main.login'))

def initiate_paypal_payout(recipient_email, amount):
    try:
        batch_id = str(uuid.uuid4()) + '_' + str(int(time.time()))
        payout = paypalrestsdk.Payout({
            "sender_batch_header": {
                "sender_batch_id": batch_id,
                "email_subject": "Your payout is on its way!"
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": amount,
                        "currency": "EUR"
                    },
                    "note": "Thanks for using our service!",
                    "receiver": recipient_email,
                    "sender_item_id": "YOUR_SENDER_ITEM_ID"
                }
            ]
        })
    except paypalrestsdk.exceptions.PayPalRESTException as e:
        print('Error creating payout: ', e)
        return None

    return payout.create()



@socketio.on('paypal_payout', namespace=namespace)
def paypal_payout(amount):
    if session.get('loggedin', False):
        amount = validate_amounts(amount)
        if amount > 0:
            cursor = mysql.get_db().cursor()
            cursor.execute("SELECT balance, userid, email from users WHERE username = %s", (session['username'], ))
            user = cursor.fetchall()
            if float(user[0][0]) > float(amount):  
                #payout_batch_id, payout_status = initiate_paypal_payout(str(user[0][2]), int(amount))
                payout_status = initiate_paypal_payout('user@personal.example.com', int(amount))
                if payout_status == True:
                    print("Payout created successfully")
                    new_balance = user[0][0] - float(amount)
                    cursor.execute('UPDATE users SET balance = %s WHERE username = %s', (new_balance, session['username']))
                    mysql.get_db().commit()
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                    cursor.execute('INSERT INTO transactions VALUES (NULL, %s, %s, %s, %s, %s)', (user[0][1], 'Transacto.lt', amount, 'Withdrawal', current_time))
                    mysql.get_db().commit()
                    socketio.emit('send_notification', data='Withdrawal completed successfully!', namespace=namespace, room=request.sid)
                else:
                    print('Payout failed')
                    socketio.emit('send_notification', data='Failed to complete the withdrawal! ', namespace=namespace, room=request.sid)

            else:
                socketio.emit('send_notification', data='Insufficient balance!', namespace=namespace, room=request.sid)
            cursor.close()
        else:
            socketio.emit('send_notification', data='Invalid amount!', namespace=namespace, room=request.sid)
    else:
        return redirect(url_for('main.login'))

@socketio.on('paysera_deposit', namespace=namespace)
def paysera_deposit(amount):
    if session.get('loggedin', False):
        payment_id = str(uuid.uuid4()) + '_' + str(int(time.time()))
        # check if the input is a valid monetary value
        try:
            money_value = Decimal(amount)
        except InvalidOperation:
            # emit an error message if the input is invalid
            socketio.emit('send_notification', data='Invalid amount!', namespace=namespace, room=request.sid)
        else:
            # convert the money to cents and emit the result
            global money_cents
            money_cents = int(money_value * 100)
        
        paysera_params = {
            'projectid': project_id,
            'orderid': payment_id,
            'accepturl': 'https://transacto.lt/dashboard?response=OK',
            'cancelurl': 'https://transacto.lt/dashboard?response=NO',
            'callbackurl': 'https://transacto.lt/paysera_callback',
            'currency': 'EUR',
            'version': '1.6',
            'test': 1,
            'amount': money_cents
        }

        sign, data = generate_sign(paysera_params, sign_password)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = mysql.get_db().cursor()
        cursor.execute('INSERT INTO paysera_deposits VALUES (NULL, %s, %s, %s, %s, %s, %s)', (session['username'], payment_id, 'EUR', money_cents, 100, current_time))
        mysql.get_db().commit()
        cursor.close()

        url = f'https://www.paysera.com/pay/?data={data}&sign={sign}'

        socketio.emit('paysera_payment_direction', data=url, namespace=namespace, room=request.sid)

    else:
        return redirect(url_for('main.login'))