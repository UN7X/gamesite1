# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.secret_key = '0424525252S6XU'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

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
        return redirect(url_for('game_options', game_name='Tic-Tac-Toe'))
    else:
        return redirect(url_for('login'))

rooms = {}

@socketio.on('join_room')
def on_join_room(data):
    code = data['code']
    username = data['username']
    join_room(code)
    if code in rooms:
        rooms[code]['players'].append(username)
    else:
        rooms[code] = {'players': [username], 'board': [''] * 9, 'currentPlayer': 'X'}
    emit('player_joined', {'username': username}, room=code)

    if len(rooms[code]['players']) == 2:
        # Start the game
        players = rooms[code]['players']
        emit('game_start', {'symbol': 'X', 'opponent': players[1]}, to=request.sid)
        emit('game_start', {'symbol': 'O', 'opponent': players[0]}, room=code, include_self=False)

@socketio.on('make_move')
def on_make_move(data):
    code = data['code']
    board = data['board']
    currentPlayer = data['currentPlayer']
    rooms[code]['board'] = board
    rooms[code]['currentPlayer'] = currentPlayer
    winner = check_winner(board)
    if winner:
        emit('update_board', {'board': board, 'currentPlayer': currentPlayer, 'winner': winner}, room=code)
    else:
        emit('update_board', {'board': board, 'currentPlayer': currentPlayer, 'winner': None}, room=code)

@socketio.on('disconnect')
def on_disconnect():
    for code, room in list(rooms.items()):
        if request.sid in room.get('sids', []):
            leave_room(code)
            room['players'].remove(request.sid)
            if not room['players']:
                del rooms[code]
            else:
                emit('opponent_left', room=code)
            break

def check_winner(board):
    winning_conditions = [
        [0,1,2], [3,4,5], [6,7,8],
        [0,3,6], [1,4,7], [2,5,8],
        [0,4,8], [2,4,6]
    ]
    for condition in winning_conditions:
        a, b, c = condition
        if board[a] == board[b] == board[c] != '':
            return board[a]
    return 'Draw' if '' not in board else None

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

@app.route('/game/<game_name>')
def game_options(game_name):
    if 'username' in session:
        return render_template('game_options.html', game_name=game_name)
    else:
        return redirect(url_for('login'))

@app.route('/play_local/<game_name>')
def play_local(game_name):
    if 'username' in session:
        return render_template('play_local.html', game_name=game_name)
    else:
        return redirect(url_for('login'))

@app.route('/host_session/<game_name>')
def host_session(game_name):
    if 'username' in session:
        code = generate_join_code()
        return redirect(url_for('game_session', game_name=game_name, code=code))
    else:
        return redirect(url_for('login'))

@app.route('/join_session/<game_name>', methods=['POST'])
def join_session(game_name):
    if 'username' in session:
        code = request.form['code']
        return redirect(url_for('game_session', game_name=game_name, code=code))
    else:
        return redirect(url_for('login'))

@app.route('/game_session/<game_name>/<code>')
def game_session(game_name, code):
    if 'username' in session:
        return render_template('game_session.html', game_name=game_name, code=code, username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/play_ai/<game_name>', methods=['GET', 'POST'])
def play_ai(game_name):
    if 'username' in session:
        if request.method == 'POST':
            difficulty = request.form['difficulty']
            return render_template('tictactoe_game.html', game_name=game_name, mode='ai', difficulty=difficulty)
        return render_template('select_difficulty.html', game_name=game_name)
    else:
        return redirect(url_for('login'))

@app.route('/local_multiplayer/<game_name>')
def local_multiplayer(game_name):
    if 'username' in session:
        return render_template('tictactoe_game.html', game_name=game_name, mode='local')
    else:
        return redirect(url_for('login'))

def generate_join_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

if __name__ == '__main__':
    socketio.run(app, debug=True)