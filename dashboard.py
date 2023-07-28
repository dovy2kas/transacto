from flask import render_template, session, request, redirect, url_for
from app import mysql, socketio
from datetime import datetime
from flask import Blueprint
import pyotp
import traceback
import logging
import string

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('errors.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

dashboard = Blueprint('dashboard', __name__)

connected_users = {}

namespace = '/dashboard'

@socketio.on('connect', namespace=namespace)
def dashboard_connect():
    if session.get('loggedin', False):
        if session['response'] == 'OK':
            socketio.emit('send_notification', data='Deposit successful!', namespace=namespace, room=request.sid)
        elif session['response'] == 'NO':
            socketio.emit('send_notification', data='Failed to complete the deposit! ', namespace=namespace, room=request.sid)
        cursor = mysql.get_db().cursor()
        connected_users[session['username']] = request.sid
        cursor.execute('SELECT balance from users WHERE username = %s', (session['username'], ))
        balance = cursor.fetchone()
        cursor.execute('SELECT auth_secret from users WHERE username = %s', (session['username'], ))
        auth_secret = cursor.fetchone()
        cursor.close()
        if auth_secret[0] == 'GA======':
            socketio.emit('send_notification', data='Please enable two factor authentication in the profile page! ', namespace=namespace, room=request.sid)
        socketio.emit('update_balance', data=(balance), namespace=namespace, room=request.sid)
    else:
        socketio.emit('update_balance', data=(0), namespace=namespace, room=request.sid)

@socketio.on('update_transactions', namespace=namespace)
def update_transactions():
    if session.get('loggedin', False):
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT userid from users WHERE username = %s', (session['username'], ))
        userid = cursor.fetchone()[0]
        cursor.execute('SELECT time, description, CASE WHEN sender = %s THEN amount * -1 ELSE amount END AS amount FROM transactions WHERE sender = %s OR receiver = %s ORDER BY ID DESC LIMIT 5', (userid, userid, userid, ))
        data = cursor.fetchall()
        cursor.close()
        transactions = []
        for transaction in data:
            transactions.append({'date': transaction[0], 'description': transaction[1], 'amount': transaction[2]})
        socketio.emit('update_transactions', transactions, namespace=namespace, room=request.sid)

@socketio.on('send_money', namespace=namespace)
def send_money(recipient, amount, description, totp_code):
    cursor = mysql.get_db().cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE userid = %s", (recipient, ))
    recipient_count = cursor.fetchone()[0]
    cursor.execute("SELECT balance from users WHERE username = %s", (session['username'], ))
    balance = cursor.fetchone()[0]
    cursor.execute("SELECT auth_secret from users WHERE username = %s", (session['username'], ))
    auth_secret = cursor.fetchone()[0]
    cursor.close()

    if len(description) > 50:
        message = 'Description is too long!'
        socketio.emit('send_failed', data=(message), namespace=namespace, room=request.sid)
        return

    if recipient_count == 0:
        message = 'Recipient does not exist!'
        socketio.emit('send_failed', data=(message), namespace=namespace, room=request.sid)
        return
    try:
        amount_float = float(amount)
    except ValueError:
        message = 'Invalid amount!'
        socketio.emit('send_failed', data=(message), namespace=namespace, room=request.sid)
        return

    if amount_float <= 0:
        message = 'Amount must be greater than zero!'
        socketio.emit('send_failed', data=(message), namespace=namespace, room=request.sid)
        return
    
    if amount_float > balance:
        message = 'Insufficient funds!'
        socketio.emit('send_failed', data=(message), namespace=namespace, room=request.sid)
        return
    if not pyotp.TOTP(auth_secret).verify(totp_code):
        message = 'Invalid two factor authentication code!'
        socketio.emit('send_failed', data=(message), namespace=namespace, room=request.sid)
        return
    try:
        cursor = mysql.get_db().cursor()
        cursor.execute('SELECT userid from users WHERE username = %s', (session['username'], ))
        sender = cursor.fetchone()
        cursor.close()
        if sender[0] == recipient:
            message = 'You cannot send funds to yourself!'
            socketio.emit('send_failed', data=(message), namespace=namespace, room=request.sid)
            return
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        #Remove the sent amount from the sender's balance
        new_balance = balance - amount_float
        cursor = mysql.get_db().cursor()
        cursor.execute('UPDATE users SET balance = %s WHERE userid = %s', (new_balance, sender))
        mysql.get_db().commit()
        socketio.emit('update_balance', data=(new_balance), namespace=namespace, room=request.sid)
        #Get the recipient's balance and add the sent amount.
        cursor.execute('SELECT balance from users WHERE userid = %s', (recipient, ))
        balance = cursor.fetchone()[0]
        new_balance = balance + amount_float
        cursor.execute('UPDATE users SET balance = %s WHERE userid = %s', (new_balance, recipient))
        mysql.get_db().commit()
        #Log the transaction into transactions table
        cursor.execute('INSERT INTO transactions VALUES (NULL, %s, %s, %s, %s, %s)', (sender[0].upper(), recipient.upper(), amount_float, description, current_time))
        mysql.get_db().commit()
        cursor.close()
        socketio.emit('send_success', namespace=namespace, room=request.sid)
    except Exception:
        traceback.print_exc()
        logger.error(traceback.print_exc())


@dashboard.route('/dashboard')
def index():
    message = 'Empty'
    session['response'] = request.args.get('response')
    try:
        message = request.args.get('msg')
        if message is None:
            message = 'Empty'
    except:
        pass
    try:
        if session.get('loggedin', False):
            cursor = mysql.get_db().cursor()
            cursor.execute('SELECT name, userid, is_confirmed, balance FROM users WHERE username = % s', (session['username'], ))
            account = cursor.fetchone()
            cursor.close()
            session['balance'] = account[3]
            try:
                if account[2] == 0:
                    msg = 'Please confirm your email address!'
                    return render_template('dashboard.html', msg = msg, name = account[0], user_id = account[1])
            except Exception:
                traceback.print_exc()
                logger.error(traceback.print_exc())
            return render_template('dashboard.html', msg = message, name = account[0], user_id = account[1])
    except Exception:
        traceback.print_exc()
        logger.error(traceback.print_exc())
    return redirect(url_for('main.login'))