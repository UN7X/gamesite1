// static/game.js
document.addEventListener('DOMContentLoaded', () => {
        // static/game.js
    let maxDepth;
    if (difficulty === 'easy') {
        maxDepth = 1;
    } else if (difficulty === 'medium') {
        maxDepth = 3;
    } else {
        maxDepth = Infinity; // Hard difficulty
    }
    const cells = document.querySelectorAll('.cell');
    let board = ['', '', '', '', '', '', '', '', ''];
    let currentPlayer = 'X';
    let gameActive = true;
    const statusDisplay = document.getElementById('status');
    const mode = "{{ mode | safe }}";
    const difficulty = "{{ difficulty | safe }}";
    const code = "{{ code | safe }}";
    const username = "{{ username | safe }}";
    let socket;

    if (mode !== 'local') {
        // Initialize Socket.IO
        socket = io();

        // Join the room
        socket.emit('join_room', { 'code': code, 'username': username });

        // Listen for starter info
        socket.on('game_start', data => {
            currentPlayer = data.symbol;
            gameActive = true;
            statusDisplay.textContent = `Game started. You are '${currentPlayer}'.`;
        });

        // Listen for opponent moves
        socket.on('update_board', data => {
            board = data.board;
            currentPlayer = data.currentPlayer;
            updateBoard();
            if (data.winner) {
                statusDisplay.textContent = data.winner === 'Draw' ? "It's a draw!" : `${data.winner} wins!`;
                gameActive = false;
            } else {
                statusDisplay.textContent = currentPlayer === data.symbol ? 'Your turn' : "Opponent's turn";
            }
        });
    }

    function handleCellClick(clickedCellEvent) {
        const clickedCell = clickedCellEvent.target;
        const clickedCellIndex = parseInt(clickedCell.getAttribute('data-cell-index'));

        if (board[clickedCellIndex] !== '' || !gameActive) {
            return;
        }

        if (mode === 'online' && currentPlayer !== '{{ symbol }}') {
            return; // Not this player's turn
        }

        makeMove(clickedCellIndex, currentPlayer);

        if (mode === 'ai' && gameActive) {
            currentPlayer = 'O';
            statusDisplay.textContent = "AI's turn";
            setTimeout(aiMove, 500);
        }
    }

    function makeMove(index, player) {
        board[index] = player;
        updateBoard();
        const winner = checkWinner();
        if (winner) {
            statusDisplay.textContent = winner === 'Draw' ? "It's a draw!" : `${winner} wins!`;
            gameActive = false;
            if (mode !== 'local' && mode !== 'ai') {
                socket.emit('game_over', { 'code': code, 'winner': winner });
            }
        } else {
            currentPlayer = currentPlayer === 'X' ? 'O' : 'X';
            if (mode === 'online') {
                socket.emit('make_move', { 'code': code, 'board': board, 'currentPlayer': currentPlayer });
            }
        }
    }

    function updateBoard() {
        cells.forEach((cell, index) => {
            cell.textContent = board[index];
            if (board[index] !== '') {
                cell.classList.add('mark', 'visible');
            } else {
                cell.classList.remove('mark', 'visible');
            }
        });
    }

    function checkWinner() {
        const winningConditions = [
            [0,1,2], [3,4,5], [6,7,8], // Rows
            [0,3,6], [1,4,7], [2,5,8], // Columns
            [0,4,8], [2,4,6]           // Diagonals
        ];

        for (let condition of winningConditions) {
            const [a, b, c] = condition;
            if (board[a] && board[a] === board[b] && board[a] === board[c]) {
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

    if (mode === 'online') {
        socket.on('connect_error', () => {
            statusDisplay.textContent = 'Connection error. Reconnecting...';
        });
    
        socket.on('reconnect', () => {
            statusDisplay.textContent = 'Reconnected to server.';
            socket.emit('join_room', { 'code': code, 'username': username });
        });
    
        socket.on('disconnect', () => {
            statusDisplay.textContent = 'Disconnected from server.';
            gameActive = false;
        });
    
        socket.on('opponent_left', () => {
            statusDisplay.textContent = 'Opponent disconnected.';
            gameActive = false;
        });
    }
});