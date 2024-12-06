# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import sqlite3
import datetime
import random
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
            email TEXT NOT NULL UNIQUE,
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
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            error = 'Passwords do not match!'
            return render_template('signup.html', error=error)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, generate_password_hash(password)))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            error = 'Username or email already exists!'
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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user:
            return render_template('reset_password.html', email=email)
        else:
            error = 'Email not found.'
            return render_template('forgot_password.html', error=error)
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    if password != confirm_password:
        error = 'Passwords do not match.'
        return render_template('reset_password.html', email=email, error=error)

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    conn.execute('UPDATE users SET password = ? WHERE email = ?', (hashed_password, email))
    conn.commit()
    conn.close()

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

    if not code or not username:
        emit('error', {'message': 'Invalid data provided.'})
        return

    if code not in rooms:
        emit('error', {'message': 'Invalid join code.'})
        return

    # Prevent duplicate usernames in the same room
    if username in rooms[code]['players']:
        emit('error', {'message': 'Username already taken in this room.'})
        return

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
    player = data['playerSymbol']

    if code not in rooms:
        return

    # Update the room's board
    rooms[code]['board'] = board

    # Check for a winner on the server side
    winner, winning_line = check_winner(board)

    if winner:
        emit('update_board', {
            'board': board,
            'currentPlayer': player,
            'winner': winner,
            'winningLine': winning_line
        }, room=code)
    else:
        # Switch current player on the server
        currentPlayer = 'O' if player == 'X' else 'X'
        rooms[code]['currentPlayer'] = currentPlayer
        emit('update_board', {
            'board': board,
            'currentPlayer': currentPlayer,
            'winner': None,
            'winningLine': None
        }, room=code)

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

@socketio.on('leave_game')
def on_leave_game(data):
    code = data['code']
    username = data['username']
    if code in rooms:
        leave_room(code)
        rooms[code]['players'].remove(username)
        if not rooms[code]['players']:
            del rooms[code]
        else:
            emit('player_left', {'username': username}, room=code)

@socketio.on('chat_message')
def handle_chat_message(data):
    code = data['code']
    message = data['message']
    username = data['username']
    emit('chat_message', {'username': username, 'message': message}, room=code)

# app.py
def check_winner(board):
    winning_conditions = [
        [0,1,2], [3,4,5], [6,7,8],
        [0,3,6], [1,4,7], [2,5,8],
        [0,4,8], [2,4,6]
    ]
    for condition in winning_conditions:
        a, b, c = condition
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], condition
    if '' not in board:
        return 'Draw', None
    return None, None

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
def host_session_redirect(game_name):
    if 'username' in session:
        code = generate_join_code()
        return redirect(url_for('game_session', game_name=game_name, code=code))
    else:
        return redirect(url_for('login'))

@app.route('/join_session/<game_name>', methods=['GET', 'POST'], endpoint='join_session')
def join_session(game_name):
    if 'username' in session and request.method == 'POST':
        code = request.form['code']
        return redirect(url_for('game_session', game_name=game_name, code=code))
    elif 'username' not in session:
        return redirect(url_for('login'))
    else:
        return render_template('join_session.html', game_name=game_name)

@app.route('/game_session/<game_name>/<code>')
def game_session(game_name, code):
    if 'username' in session:
        return render_template('tictactoe_game.html', game_name=game_name, mode='online', code=code, username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/play_ai/<game_name>', methods=['GET', 'POST'])
def play_ai(game_name):
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            difficulty = request.form['difficulty']
            return render_template('tictactoe_game.html', game_name=game_name, mode='ai', difficulty=difficulty, username=username)
        return render_template('select_difficulty.html', game_name=game_name)
    else:
        return redirect(url_for('login'))
    
@app.route('/local_multiplayer/<game_name>')
def local_multiplayer(game_name):
    if 'username' in session:
        username = session['username']
        return render_template('tictactoe_game.html', game_name=game_name, mode='local', username=username)
    else:
        return redirect(url_for('login'))

@app.route('/<game_name>/host_session', methods=['GET', 'POST'], endpoint='host_session_unique')
def host_session_unique(game_name):
    if request.method == 'POST':
        custom_code = request.form.get('custom_code', '').strip()
        is_public = request.form.get('is_public') == 'yes'
        code = custom_code if custom_code else generate_join_code()
        
        # Ensure the join code is unique
        while code in rooms:
            code = generate_join_code() if not custom_code else code + str(random.randint(0,9))

        rooms[code] = {
            'game_name': game_name,
            'players': [],
            'board': ['']*9,
            'currentPlayer': 'X',
            'is_public': is_public,
            'host': session.get('username', 'Guest'),
            'created_at': datetime.datetime.now()
        }
        return redirect(url_for('play_online', game_name=game_name, code=code))
    else:
        return render_template('host_session.html', game_name=game_name)

@app.route('/<game_name>/public_sessions')
def public_sessions(game_name):
    public_rooms = []
    for code, room in rooms.items():
        if room['game_name'] == game_name and room['is_public'] and len(room['players']) < 2:
            public_rooms.append({
                'code': code,
                'host': room['host'],
                'created_at': room['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            })
    return render_template('public_sessions.html', game_name=game_name, public_rooms=public_rooms)

def generate_join_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

if __name__ == '__main__':
    socketio.run(app, debug=True)