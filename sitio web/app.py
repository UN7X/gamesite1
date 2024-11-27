# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.secret_key = '0424525252S6XU'

# Initialize SocketIO
socketio = SocketIO(app)

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            game TEXT NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/guest_login', methods=('GET', 'POST'))
def guest_login():
    if request.method == 'POST':
        guest_username = request.form['guest_username']
        session['username'] = guest_username
        session['guest'] = True
        return redirect(url_for('game_lobby'))
    return render_template('guest_login.html')

@app.route('/game_lobby')
def game_lobby():
    if 'username' in session:
        return render_template('game_lobby.html', username=session['username'], guest=session.get('guest', False))
    else:
        return redirect(url_for('login'))

# Modify the home route to redirect to the game lobby
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('game_lobby'))
    return redirect(url_for('login'))

@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, generate_password_hash(password)))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            error = 'Username already exists!'
            return render_template('signup.html', error=error)
    return render_template('signup.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error = 'Invalid username or password!'
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/delete_account')
def delete_account():
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        conn.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        session.pop('username', None)
        return redirect(url_for('signup'))
    else:
        return redirect(url_for('login'))

@app.route('/tictactoe')
def tictactoe():
    if 'username' in session:
        return render_template('tictactoe.html', username=session['username'])
    else:
        return redirect(url_for('login'))

# Handle players joining the game
@socketio.on('join_game')
def on_join_game(data):
    username = data['username']
    # Logic to assign players to game rooms goes here
    emit('message', f'{username} has joined the game.')

def update_stats(username, game, result):
    conn = get_db_connection()
    if result == 'win':
        conn.execute('UPDATE stats SET wins = wins + 1 WHERE username = ? AND game = ?', (username, game))
    elif result == 'loss':
        conn.execute('UPDATE stats SET losses = losses + 1 WHERE username = ? AND game = ?', (username, game))
    elif result == 'draw':
        conn.execute('UPDATE stats SET draws = draws + 1 WHERE username = ? AND game = ?', (username, game))
    else:
        pass  # Invalid result
    conn.commit()
    conn.close()

if __name__ == '__main__':
    socketio.run(app, debug=True)