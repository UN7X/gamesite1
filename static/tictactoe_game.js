// static/tictactoe_game.js
document.addEventListener('DOMContentLoaded', () => {
    let playerSymbol;
    let maxDepth;
    let opponentUsername = '';
    if (difficulty === 'easy') {
        maxDepth = 1;
    } else if (difficulty === 'medium') {
        maxDepth = 3;
    } else {
        maxDepth = Infinity; // Hard difficulty
    }
    const cells = document.querySelectorAll('.cell');
    let board = ['', '', '', '', '', '', '', '', ''];
    let currentPlayer;
    let gameActive = false;
    const statusDisplay = document.getElementById('status');
    let socket;

    // Chat functionality
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    const backToLobbyLink = document.querySelector('a[href$="game_lobby"]');
    if (backToLobbyLink && mode === 'online') {
        backToLobbyLink.addEventListener('click', (event) => {
            event.preventDefault();

            // Emit 'leave_game' event to the server
            socket.emit('leave_game', { code: code, username: username });

            // Allow some time for the event to be sent
            setTimeout(() => {
                window.location.href = backToLobbyLink.href;
            }, 100);
        });
    }

    if (mode === 'local' || mode === 'ai') {
        gameActive = true;
        statusDisplay.textContent = 'Game started. Your turn.';
    } else if (mode === 'online') {
        statusDisplay.textContent = 'Waiting for Opponent to join';

        // Initialize Socket.IO
        socket = io();

        // Join the room
        socket.emit('join_room', { code: code, username: username });

        // Listen for game start
        socket.on('game_start', data => {
            playerSymbol = data.symbol; // 'X' or 'O'
            opponentUsername = data.opponent;
            currentPlayer = 'X';
            gameActive = true;

            if (playerSymbol === 'X') {
                statusDisplay.textContent = 'Game started. Your turn.';
            } else {
                statusDisplay.textContent = `Game started. It's ${opponentUsername}'s turn.`;
            }

            console.log(`Player Symbol: ${playerSymbol}`);
            console.log(`Opponent Username: ${opponentUsername}`);
            console.log(`Current Player: ${currentPlayer}`);
        });

        // Listen for opponent moves
        socket.on('update_board', data => {
            board = data.board;
            currentPlayer = data.currentPlayer;
            updateBoard();

            if (data.winner) {
                if (data.winningLine) {
                    data.winningLine.forEach(index => {
                        cells[index].classList.add('winner');
                    });
                }
                if (data.winner === playerSymbol) {
                    statusDisplay.textContent = 'You won!';
                } else if (data.winner === 'Draw') {
                    statusDisplay.textContent = "It's a draw!";
                } else {
                    statusDisplay.textContent = `${opponentUsername} won!`;
                }
                gameActive = false;
            } else {
                if (currentPlayer === playerSymbol) {
                    statusDisplay.textContent = 'Your turn';
                } else {
                    statusDisplay.textContent = `It's ${opponentUsername}'s turn`;
                }
            }
        });

        // Chat functionality
        chatForm.addEventListener('submit', event => {
            event.preventDefault();
            const message = chatInput.value;
            if (message.trim() !== '') {
                socket.emit('chat_message', { code: code, username: username, message: message });
                chatInput.value = '';
            }
        });

        socket.on('chat_message', data => {
            const messageElement = document.createElement('div');
            messageElement.className = 'chat-message';
            messageElement.textContent = `${data.username}: ${data.message}`;
            chatMessages.appendChild(messageElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });

        // Player joined notification
        socket.on('player_joined', data => {
            if (data.username !== username) {
                opponentUsername = data.username;
                const notification = document.createElement('div');
                notification.className = 'chat-notification';
                notification.textContent = `${opponentUsername} has joined the game`;
                chatMessages.appendChild(notification);
                chatMessages.scrollTop = chatMessages.scrollHeight;
                showNotification(`${opponentUsername} has joined the game`);
            }
        });

        socket.on('player_left', data => {
            if (data.username !== username) {
                opponentUsername = '';
                statusDisplay.textContent = `${data.username} left the game`;
                showNotification(`${data.username} left the game`);
                gameActive = false;
            }
        });

        // Handle opponent disconnect due to connection issues
        socket.on('opponent_disconnected', data => {
            statusDisplay.textContent = `${opponentUsername} was disconnected`;
        });

        // Handle opponent reconnect
        socket.on('opponent_reconnected', data => {
            statusDisplay.textContent = `${opponentUsername} reconnected!`;
            showNotification(`${opponentUsername} reconnected!`);
        });

        // Handle chat messages and disconnections
        socket.on('connect_error', () => {
            statusDisplay.textContent = 'Connection error. Reconnecting...';
        });

        socket.on('reconnect', () => {
            statusDisplay.textContent = 'Reconnected to server.';
            socket.emit('rejoin_room', { code: code, username: username });
        });

        socket.on('disconnect', () => {
            statusDisplay.textContent = 'Disconnected from server.';
            gameActive = false;
        });
    }

    function handleCellClick(event) {
        const clickedCell = event.target;
        const clickedCellIndex = parseInt(clickedCell.getAttribute('data-cell-index'));

        if (board[clickedCellIndex] !== '' || !gameActive) {
            return;
        }

        if (mode === 'online') {
            if (currentPlayer !== playerSymbol) {
                return;
            }
            makeMove(clickedCellIndex, playerSymbol);
            socket.emit('make_move', { code: code, board: board, playerSymbol: playerSymbol });
        } else {
            makeMove(clickedCellIndex, currentPlayer);
            if (mode === 'ai' && gameActive) {
                currentPlayer = 'O';
                statusDisplay.textContent = "AI's turn";
                setTimeout(aiMove, 500);
            } else if (mode === 'local') {
                currentPlayer = currentPlayer === 'X' ? 'O' : 'X';
                statusDisplay.textContent = `Player ${currentPlayer}'s turn`;
            }
        }
    }

    function makeMove(index, player) {
        board[index] = player;
        updateBoard();
    }

    function updateBoard() {
        cells.forEach((cell, index) => {
            cell.textContent = board[index];
            cell.className = 'cell'; // Reset classes
            if (board[index] !== '') {
                cell.classList.add(board[index]);
            }
        });
    }

    function checkWinner() {
        const winningConditions = [
            [0,1,2], [3,4,5], [6,7,8],
            [0,3,6], [1,4,7], [2,5,8],
            [0,4,8], [2,4,6]
        ];

        for (let condition of winningConditions) {
            const [a, b, c] = condition;
            if (board[a] && board[a] === board[b] && board[a] === board[c]) {
                cells[a].classList.add('winner');
                cells[b].classList.add('winner');
                cells[c].classList.add('winner');
                return board[a];
            }
        }

        return board.includes('') ? null : 'Draw';
    }

    function aiMove() {
        let index;
        if (difficulty === 'easy') {
            index = randomMove();
        } else {
            index = bestMove();
        }
        makeMove(index, 'O');
        if (gameActive) {
            currentPlayer = 'X';
            statusDisplay.textContent = 'Your turn';
        }
    }

    function randomMove() {
        const available = board.map((val, idx) => val === '' ? idx : null).filter(val => val !== null);
        return available[Math.floor(Math.random() * available.length)];
    }

    function bestMove() {
        let bestScore = -Infinity;
        let move;
        for (let i = 0; i < board.length; i++) {
            if (board[i] === '') {
                board[i] = 'O';
                let score = minimax(board, 0, false);
                board[i] = '';
                if (score > bestScore) {
                    bestScore = score;
                    move = i;
                }
            }
        }
        return move;
    }

    function minimax(newBoard, depth, isMaximizing) {
        let result = checkWinner();
        if (result !== null || depth === maxDepth) {
            if (result === 'O') return 10 - depth;
            else if (result === 'X') return depth - 10;
            else return 0;
        }

        if (isMaximizing) {
            let bestScore = -Infinity;
            for (let i = 0; i < newBoard.length; i++) {
                if (newBoard[i] === '') {
                    newBoard[i] = 'O';
                    let score = minimax(newBoard, depth + 1, false);
                    newBoard[i] = '';
                    bestScore = Math.max(score, bestScore);
                }
            }
            return bestScore;
        } else {
            let bestScore = Infinity;
            for (let i = 0; i < newBoard.length; i++) {
                if (newBoard[i] === '') {
                    newBoard[i] = 'X';
                    let score = minimax(newBoard, depth + 1, true);
                    newBoard[i] = '';
                    bestScore = Math.min(score, bestScore);
                }
            }
            return bestScore;
        }
    }

    cells.forEach(cell => {
        cell.addEventListener('click', handleCellClick);
    });

    // Numpad mapping for local two-player game
    if (mode === 'local' || mode === 'pvp') {
        document.addEventListener('keydown', (event) => {
            const key = event.key;
            const cellMap = {
                '7': 0,
                '8': 1,
                '9': 2,
                '4': 3,
                '5': 4,
                '6': 5,
                '1': 6,
                '2': 7,
                '3': 8,
            };
            if (cellMap[key] !== undefined) {
                const index = cellMap[key];
                if (board[index] === '' && gameActive) {
                    makeMove(index, currentPlayer);
                }
            }
        });
    }

    function showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        document.body.appendChild(notification);

        // Slide in the notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Remove the notification after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 500);
        }, 3000);
    }
});