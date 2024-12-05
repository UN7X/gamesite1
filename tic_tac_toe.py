import pygame
import sys
import argparse  # For command-line arguments
import os  # For file handling

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 300, 300
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tic-Tac-Toe")

# Colors
WHITE = (255, 255, 255)
LINE_COLOR = (0, 0, 0)
OVERLAY_COLOR = (0, 0, 0, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# Game variables
BOARD = [['' for _ in range(3)] for _ in range(3)]
CURRENT_PLAYER = 'X'

# Numpad key mapping
KEY_MAP = {
    pygame.K_KP7: (0, 0),
    pygame.K_KP8: (0, 1),
    pygame.K_KP9: (0, 2),
    pygame.K_KP4: (1, 0),
    pygame.K_KP5: (1, 1),
    pygame.K_KP6: (1, 2),
    pygame.K_KP1: (2, 0),
    pygame.K_KP2: (2, 1),
    pygame.K_KP3: (2, 2),
}

# Exit confirmation variables
exit_confirmation = False

# Winning positions
WINNING_POSITIONS = []

def draw_grid():
    SCREEN.fill(WHITE)
    # Vertical lines
    pygame.draw.line(SCREEN, LINE_COLOR, (100, 0), (100, 300), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (200, 0), (200, 300), 2)
    # Horizontal lines
    pygame.draw.line(SCREEN, LINE_COLOR, (0, 100), (300, 100), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (0, 200), (300, 200), 2)

def draw_marks():
    font = pygame.font.SysFont(None, 100)
    for row in range(3):
        for col in range(3):
            mark = BOARD[row][col]
            if mark != '':
                if WINNING_POSITIONS and (row, col) in WINNING_POSITIONS:
                    color = GREEN
                else:
                    color = RED if mark == 'X' else BLUE
                img = font.render(mark, True, color)
                SCREEN.blit(img, (col * 100 + 30, row * 100 + 20))

def check_winner(board, player):
    global WINNING_POSITIONS
    # Reset WINNING_POSITIONS at the start
    WINNING_POSITIONS = []
    # Check rows
    for i in range(3):
        if all([spot == player for spot in board[i]]):
            WINNING_POSITIONS = [(i, col) for col in range(3)]
            return True
    # Check columns
    for i in range(3):
        if all([board[row][i] == player for row in range(3)]):
            WINNING_POSITIONS = [(row, i) for row in range(3)]
            return True
    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] == player and board[0][0] != '':
        WINNING_POSITIONS = [(i, i) for i in range(3)]
        return True
    if board[0][2] == board[1][1] == board[2][0] == player and board[0][2] != '':
        WINNING_POSITIONS = [(0, 2), (1, 1), (2, 0)]
        return True
    return False

def is_board_full(board):
    return all([cell != '' for row in board for cell in row])

def minimax(board, depth, is_maximizing):
    if check_winner(board, 'O'):
        return 1
    if check_winner(board, 'X'):
        return -1
    if is_board_full(board):
        return 0

    if is_maximizing:
        best_score = -float('inf')
        for row in range(3):
            for col in range(3):
                if board[row][col] == '':
                    board[row][col] = 'O'
                    score = minimax(board, depth + 1, False)
                    board[row][col] = ''
                    best_score = max(score, best_score)
        return best_score
    else:
        best_score = float('inf')
        for row in range(3):
            for col in range(3):
                if board[row][col] == '':
                    board[row][col] = 'X'
                    score = minimax(board, depth + 1, True)
                    board[row][col] = ''
                    best_score = min(score, best_score)
        return best_score

def ai_move():
    best_score = -float('inf')
    move = None
    for row in range(3):
        for col in range(3):
            if BOARD[row][col] == '':
                BOARD[row][col] = 'O'
                score = minimax(BOARD, 0, False)
                BOARD[row][col] = ''
                if score > best_score:
                    best_score = score
                    move = (row, col)
    if move:
        BOARD[move[0]][move[1]] = 'O'

def show_exit_confirmation():
    font = pygame.font.SysFont(None, 30)
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(128)
    overlay.fill((0, 0, 0))
    SCREEN.blit(overlay, (0, 0))

    text = font.render("Press ESC again to exit, any key to cancel.", True, WHITE)
    SCREEN.blit(text, (WIDTH / 2 - text.get_width() / 2, HEIGHT / 2))
    pygame.display.update()

def game_loop(game_mode='pva', starting_player='X'):
    global CURRENT_PLAYER, exit_confirmation, WINNING_POSITIONS, BOARD
    CURRENT_PLAYER = starting_player
    running = True
    while running:
        draw_grid()
        draw_marks()
        pygame.display.update()

        if exit_confirmation:
            continue  # Skip game updates while waiting for confirmation

        if game_mode == 'pva' and CURRENT_PLAYER == 'O':
            # AI's turn
            ai_move()
            if check_winner(BOARD, 'O'):
                draw_grid()
                draw_marks()
                pygame.display.update()
                print("O wins!")
                pygame.time.delay(2000)
                running = False
            elif is_board_full(BOARD):
                draw_grid()
                draw_marks()
                pygame.display.update()
                print("It's a tie!")
                pygame.time.delay(2000)
                running = False
            else:
                CURRENT_PLAYER = 'X'
            continue  # Skip the rest of the loop to avoid handling events during AI's turn

        if game_mode == 'ava':
            while running:
                if game_mode == 'ava' and CURRENT_PLAYER == 'O':
                    # AI's turn
                    ai_move()
                    if check_winner(BOARD, 'O'):
                        draw_grid()
                        draw_marks()
                        pygame.display.update()
                        print("O wins!")
                        pygame.time.delay(2000)
                        running = False
                    elif is_board_full(BOARD):
                        draw_grid()
                        draw_marks()
                        pygame.display.update()
                        print("It's a tie!")
                        pygame.time.delay(2000)
                        running = False
                    else:
                        CURRENT_PLAYER = 'X'
                
                if game_mode == 'ava' and CURRENT_PLAYER == 'X':
                    # AI's turn
                    ai_move()
                    if check_winner(BOARD, 'X'):
                        draw_grid()
                        draw_marks()
                        pygame.display.update()
                        print("X wins!")
                        pygame.time.delay(2000)
                        running = False
                    elif is_board_full(BOARD):
                        draw_grid()
                        draw_marks()
                        pygame.display.update()
                        print("It's a tie!")
                        pygame.time.delay(2000)
                        running = False
                    else:
                        CURRENT_PLAYER = 'O'
                    continue

        
        # Player's turn
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if exit_confirmation:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        sys.exit()
                    else:
                        exit_confirmation = False
                else:
                    if event.key == pygame.K_ESCAPE:
                        exit_confirmation = True
                        show_exit_confirmation()
                    elif event.key in KEY_MAP:
                        row, col = KEY_MAP[event.key]
                        if BOARD[row][col] == '':
                            BOARD[row][col] = CURRENT_PLAYER
                            if check_winner(BOARD, CURRENT_PLAYER):
                                draw_grid()
                                draw_marks()
                                pygame.display.update()
                                print(f"{CURRENT_PLAYER} wins!")
                                pygame.time.delay(2000)
                                running = False
                            elif is_board_full(BOARD):
                                draw_grid()
                                draw_marks()
                                pygame.display.update()
                                print("It's a tie!")
                                pygame.time.delay(2000)
                                running = False
                            else:
                                CURRENT_PLAYER = 'O' if CURRENT_PLAYER == 'X' else 'X'
            elif event.type == pygame.MOUSEBUTTONDOWN and not exit_confirmation:
                x, y = event.pos
                col = x // 100
                row = y // 100
                if BOARD[row][col] == '':
                    BOARD[row][col] = CURRENT_PLAYER
                    if check_winner(BOARD, CURRENT_PLAYER):
                        draw_grid()
                        draw_marks()
                        pygame.display.update()
                        print(f"{CURRENT_PLAYER} wins!")
                        pygame.time.delay(2000)
                        running = False
                    elif is_board_full(BOARD):
                        draw_grid()
                        draw_marks()
                        pygame.display.update()
                        print("It's a tie!")
                        pygame.time.delay(2000)
                        running = False
                    else:
                        CURRENT_PLAYER = 'O' if CURRENT_PLAYER == 'X' else 'X'

        pygame.time.delay(100)
    pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['pva', 'pvp'], default='pva', help='Game mode: pva (Player vs AI) or pvp (Player vs Player)')
    args = parser.parse_args()

    # Update starting player to alternate between games
    # This requires storing the last starting player
    # For simplicity, we'll store it in a file
    last_player_file = 'last_player.txt'
    if os.path.exists(last_player_file):
        with open(last_player_file, 'r') as f:
            last_player = f.read().strip()
        starting_player = 'O' if last_player == 'X' else 'X'
    else:
        starting_player = 'X'  # Default starting player

    # Save the current starting player for the next game
    with open(last_player_file, 'w') as f:
        f.write(starting_player)

    # Reset the game board
    BOARD = [['' for _ in range(3)] for _ in range(3)]

    game_loop(game_mode=args.mode, starting_player=starting_player)
