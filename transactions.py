from flask import render_template, session, request, redirect, url_for
from flask import Blueprint
from app import mysql, socketio
transactions = Blueprint('transactions', __name__)

namespace = '/transactions'

@socketio.on('get_transactions', namespace=namespace)
def get_transactions(page):
    page_size = 20

    offset = (page - 1) * page_size
    cursor = mysql.get_db().cursor()
    cursor.execute('SELECT userid FROM users WHERE username = %s', (session['username'], ))
    userid = cursor.fetchone()
    cursor.execute('SELECT time, sender, receiver, description, CASE WHEN sender = %s THEN amount * -1 ELSE amount END AS amount FROM transactions WHERE sender = %s OR receiver = %s ORDER BY id DESC LIMIT %s OFFSET %s', (userid, userid, userid, page_size, offset))
    data = cursor.fetchall()
    cursor.close()
    for col in data:
        socketio.emit('transactions_data', [{'date': col[0],'from': col[1],'to': col[2],'desc': col[3],'amount': col[4]}], namespace=namespace, room=request.sid)

@transactions.route('/transactions')
def index():
    try:
        if session['loggedin']:
            return render_template('transactions.html')
    except:
        pass
    return redirect(url_for('main.login'))