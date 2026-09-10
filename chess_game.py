import io
import os
import random
import threading

import chess
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# CONFIG
# ============================================================

BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8

LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)

LAST_MOVE_COLOR = (246, 246, 105)
SELECTED_COLOR = (170, 210, 100)
CHECK_COLOR = (220, 70, 70)

WHITE_PIECE = (245, 245, 245)
BLACK_PIECE = (30, 30, 30)

FILES = "abcdefgh"


# ============================================================
# ACTIVE GAMES
# ============================================================

# user_id -> ChessGame
GAMES = {}

GAMES_LOCK = threading.Lock()


# ============================================================
# FONT
# ============================================================

def get_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",

        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",

        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]

    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    return ImageFont.load_default()


PIECE_FONT = get_font(58)
COORD_FONT = get_font(16)


# ============================================================
# GAME
# ============================================================

class ChessGame:

    def __init__(self, user_id, color=None):

        self.user_id = str(user_id)

        self.board = chess.Board()

        if color not in ("white", "black"):
            color = random.choice(
                ("white", "black")
            )

        self.player_color = (
            chess.WHITE
            if color == "white"
            else chess.BLACK
        )

        self.bot_color = not self.player_color

        self.selected_square = None

        self.last_move = None

        self.move_history = []

        self.finished = False

        self.result = None

        self.lock = threading.Lock()


    # ========================================================
    # COLOR NAMES
    # ========================================================

    @property
    def player_color_name(self):

        return (
            "White"
            if self.player_color == chess.WHITE
            else "Black"
        )


    @property
    def bot_color_name(self):

        return (
            "White"
            if self.bot_color == chess.WHITE
            else "Black"
        )


    # ========================================================
    # TURN
    # ========================================================

    def player_turn(self):

        return (
            self.board.turn
            == self.player_color
        )


    # ========================================================
    # LEGAL DESTINATIONS
    # ========================================================

    def legal_destinations(self, square):

        destinations = []

        for move in self.board.legal_moves:

            if move.from_square == square:

                destinations.append(
                    move.to_square
                )

        return destinations


    # ========================================================
    # PLAYER MOVE
    # ========================================================

    def make_player_move(
        self,
        from_square,
        to_square
    ):

        if self.finished:

            return (
                False,
                "This game has already ended."
            )


        if not self.player_turn():

            return (
                False,
                "It's Burstsay's turn."
            )


        piece = self.board.piece_at(
            from_square
        )

        if piece is None:

            return (
                False,
                "There isn't a piece there."
            )


        if piece.color != self.player_color:

            return (
                False,
                "That's not your piece."
            )


        # ----------------------------------------------------
        # Promotion
        #
        # For now, automatically promote to queen.
        # ----------------------------------------------------

        promotion = None

        if (
            piece.piece_type == chess.PAWN
            and chess.square_rank(to_square)
            in (0, 7)
        ):

            promotion = chess.QUEEN


        move = chess.Move(
            from_square,
            to_square,
            promotion=promotion
        )


        if move not in self.board.legal_moves:

            return (
                False,
                "Illegal move."
            )


        san = self.board.san(move)

        self.board.push(move)

        self.last_move = move

        self.move_history.append(san)

        self.selected_square = None

        self.check_game_end()

        return True, san


    # ========================================================
    # BOT MOVE
    # ========================================================

    def make_bot_move(self):

        if self.finished:
            return None


        if self.player_turn():
            return None


        legal_moves = list(
            self.board.legal_moves
        )


        if not legal_moves:

            self.check_game_end()

            return None


        move = self.choose_bot_move(
            legal_moves
        )


        san = self.board.san(move)

        self.board.push(move)

        self.last_move = move

        self.move_history.append(san)

        self.check_game_end()

        return san


    # ========================================================
    # SIMPLE AI
    # ========================================================

    def choose_bot_move(
        self,
        legal_moves
    ):

        # ----------------------------------------------------
        # 1. Checkmate immediately
        # ----------------------------------------------------

        for move in legal_moves:

            test_board = self.board.copy()

            test_board.push(move)

            if test_board.is_checkmate():

                return move


        # ----------------------------------------------------
        # 2. Captures
        # ----------------------------------------------------

        captures = [
            move
            for move in legal_moves
            if self.board.is_capture(move)
        ]


        if captures:

            values = {

                chess.PAWN: 1,

                chess.KNIGHT: 3,

                chess.BISHOP: 3,

                chess.ROOK: 5,

                chess.QUEEN: 9,

                chess.KING: 100,
            }


            def capture_score(move):

                captured = (
                    self.board.piece_at(
                        move.to_square
                    )
                )


                if captured:

                    return values.get(
                        captured.piece_type,
                        0
                    )


                # En passant
                if self.board.is_en_passant(
                    move
                ):
                    return 1


                return 0


            return max(
                captures,
                key=capture_score
            )


        # ----------------------------------------------------
        # 3. Prefer checks
        # ----------------------------------------------------

        checking_moves = []

        for move in legal_moves:

            test_board = self.board.copy()

            test_board.push(move)

            if test_board.is_check():

                checking_moves.append(
                    move
                )


        if checking_moves:

            return random.choice(
                checking_moves
            )


        # ----------------------------------------------------
        # 4. Otherwise random legal move
        # ----------------------------------------------------

        return random.choice(
            legal_moves
        )


    # ========================================================
    # GAME END
    # ========================================================

    def check_game_end(self):

        if self.board.is_checkmate():

            self.finished = True

            winner = not self.board.turn

            if winner == self.player_color:

                self.result = "win"

            else:

                self.result = "loss"

            return


        if self.board.is_stalemate():

            self.finished = True

            self.result = "draw"

            return


        if self.board.is_insufficient_material():

            self.finished = True

            self.result = "draw"

            return


        if self.board.is_fivefold_repetition():

            self.finished = True

            self.result = "draw"

            return


        if self.board.is_seventyfive_moves():

            self.finished = True

            self.result = "draw"

            return


    # ========================================================
    # RESIGN
    # ========================================================

    def resign(self):

        if self.finished:
            return

        self.finished = True

        self.result = "loss"


    # ========================================================
    # FEN
    # ========================================================

    def fen(self):

        return self.board.fen()


    # ========================================================
    # MOVE TEXT
    # ========================================================

    def moves_text(self):

        if not self.move_history:

            return "No moves yet."


        output = []


        for i in range(
            0,
            len(self.move_history),
            2
        ):

            move_number = (
                i // 2
            ) + 1


            white_move = (
                self.move_history[i]
            )


            black_move = ""

            if (
                i + 1
                < len(self.move_history)
            ):

                black_move = (
                    self.move_history[i + 1]
                )


            output.append(
                f"{move_number}. "
                f"{white_move} "
                f"{black_move}"
            )


        return " ".join(output)


# ============================================================
# GAME MANAGEMENT
# ============================================================

def get_game(user_id):

    with GAMES_LOCK:

        return GAMES.get(
            str(user_id)
        )


def create_game(
    user_id,
    color=None
):

    with GAMES_LOCK:

        game = ChessGame(
            user_id=user_id,
            color=color
        )

        GAMES[
            str(user_id)
        ] = game

        return game


def delete_game(user_id):

    with GAMES_LOCK:

        GAMES.pop(
            str(user_id),
            None
        )


# ============================================================
# BOARD
# ============================================================

UNICODE_PIECES = {

    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",

    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}


# ============================================================
# SQUARE NAME
# ============================================================

def square_name(square):

    return (
        FILES[
            chess.square_file(square)
        ]
        + str(
            chess.square_rank(square) + 1
        )
    )


# ============================================================
# BOARD RENDER
# ============================================================

def render_board(game):

    board_image = Image.new(
        "RGB",
        (
            BOARD_SIZE,
            BOARD_SIZE
        ),
        LIGHT_SQUARE
    )


    draw = ImageDraw.Draw(
        board_image
    )


    # ========================================================
    # ORIENTATION
    # ========================================================

    if game.player_color == chess.WHITE:

        display_squares = [

            chess.square(
                file,
                7 - rank
            )

            for rank in range(8)

            for file in range(8)
        ]

    else:

        display_squares = [

            chess.square(
                7 - file,
                rank
            )

            for rank in range(8)

            for file in range(8)
        ]


    # ========================================================
    # DRAW SQUARES
    # ========================================================

    for index, square in enumerate(
        display_squares
    ):

        display_rank = index // 8

        display_file = index % 8

        x = (
            display_file
            * SQUARE_SIZE
        )

        y = (
            display_rank
            * SQUARE_SIZE
        )


        is_dark = (
            display_file
            + display_rank
        ) % 2 == 1


        color = (
            DARK_SQUARE
            if is_dark
            else LIGHT_SQUARE
        )


        # ----------------------------------------------------
        # Last move
        # ----------------------------------------------------

        if game.last_move:

            if square in (
                game.last_move.from_square,
                game.last_move.to_square
            ):

                color = LAST_MOVE_COLOR


        # ----------------------------------------------------
        # Selected
        # ----------------------------------------------------

        if (
            game.selected_square
            == square
        ):

            color = SELECTED_COLOR


        # ----------------------------------------------------
        # Check
        # ----------------------------------------------------

        if game.board.is_check():

            king_square = (
                game.board.king(
                    game.board.turn
                )
            )

            if square == king_square:

                color = CHECK_COLOR


        draw.rectangle(
            [
                x,
                y,
                x + SQUARE_SIZE,
                y + SQUARE_SIZE
            ],
            fill=color
        )


    # ========================================================
    # DRAW PIECES
    # ========================================================

    for square, piece in (
        game.board.piece_map().items()
    ):

        index = display_squares.index(
            square
        )

        display_rank = index // 8

        display_file = index % 8


        x = (
            display_file
            * SQUARE_SIZE
        )

        y = (
            display_rank
            * SQUARE_SIZE
        )


        symbol = UNICODE_PIECES[
            piece.symbol()
        ]


        bbox = draw.textbbox(
            (0, 0),
            symbol,
            font=PIECE_FONT
        )


        width = (
            bbox[2] - bbox[0]
        )

        height = (
            bbox[3] - bbox[1]
        )


        px = (
            x
            + (
                SQUARE_SIZE
                - width
            ) / 2
        )


        py = (
            y
            + (
                SQUARE_SIZE
                - height
            ) / 2
            - 5
        )


        # ----------------------------------------------------
        # Shadow
        # ----------------------------------------------------

        draw.text(
            (
                px + 2,
                py + 2
            ),
            symbol,
            font=PIECE_FONT,
            fill=(0, 0, 0)
        )


        # ----------------------------------------------------
        # Piece
        # ----------------------------------------------------

        draw.text(
            (
                px,
                py
            ),
            symbol,
            font=PIECE_FONT,
            fill=(
                WHITE_PIECE
                if piece.color == chess.WHITE
                else BLACK_PIECE
            )
        )


    # ========================================================
    # COORDINATES
    # ========================================================

    if game.player_color == chess.WHITE:

        shown_files = list(
            "abcdefgh"
        )

        shown_ranks = list(
            "87654321"
        )

    else:

        shown_files = list(
            "hgfedcba"
        )

        shown_ranks = list(
            "12345678"
        )


    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    for index, letter in enumerate(
        shown_files
    ):

        x = (
            index
            * SQUARE_SIZE
            + 6
        )

        y = (
            BOARD_SIZE
            - 21
        )


        is_dark = (
            index % 2 == 0
        )


        draw.text(
            (x, y),
            letter,
            font=COORD_FONT,
            fill=(
                DARK_SQUARE
                if is_dark
                else LIGHT_SQUARE
            )
        )


    # --------------------------------------------------------
    # Ranks
    # --------------------------------------------------------

    for index, number in enumerate(
        shown_ranks
    ):

        x = 5

        y = (
            index
            * SQUARE_SIZE
            + 4
        )


        is_dark = (
            index % 2 == 0
        )


        draw.text(
            (x, y),
            number,
            font=COORD_FONT,
            fill=(
                DARK_SQUARE
                if is_dark
                else LIGHT_SQUARE
            )
        )


    # ========================================================
    # PNG
    # ========================================================

    output = io.BytesIO()


    board_image.save(
        output,
        format="PNG"
    )


    output.seek(0)


    return output
