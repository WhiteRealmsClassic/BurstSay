import io
import os
import random
import threading

import chess
from PIL import Image, ImageDraw, ImageFont


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

GAMES = {}
GAMES_LOCK = threading.Lock()


# ============================================================
# FONTS
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
                return ImageFont.truetype(
                    path,
                    size
                )

            except Exception:
                pass

    return ImageFont.load_default()


PIECE_FONT = get_font(58)
COORD_FONT = get_font(16)


# ============================================================
# PIECES
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
# HELPERS
# ============================================================

def square_name(square):

    return (
        FILES[chess.square_file(square)]
        + str(chess.square_rank(square) + 1)
    )


# ============================================================
# CHESS GAME
# ============================================================

class ChessGame:

    def __init__(
        self,
        player1_id,
        player2_id=None,
        mode="bot",
        player1_name="Player 1",
        player2_name="BurstSay",
        color=None
    ):

        self.mode = mode

        self.player1_id = str(
            player1_id
        )

        self.player2_id = (
            str(player2_id)
            if player2_id
            else None
        )

        self.player1_name = (
            player1_name
        )

        self.player2_name = (
            player2_name
            if player2_id
            else "BurstSay"
        )

        self.board = chess.Board()

        self.selected_square = None

        self.last_move = None

        self.move_history = []

        self.finished = False

        self.result = None

        self.winner_name = None

        self.last_player_name = None

        self.lock = threading.Lock()


        # ----------------------------------------------------
        # BOT MODE
        # ----------------------------------------------------

        if mode == "bot":

            if color not in (
                "white",
                "black"
            ):

                color = random.choice(
                    (
                        "white",
                        "black"
                    )
                )

            self.player_color = (
                chess.WHITE
                if color == "white"
                else chess.BLACK
            )

            self.bot_color = (
                not self.player_color
            )

        # ----------------------------------------------------
        # PLAYER MODE
        # ----------------------------------------------------

        else:

            # Player 1 = White
            # Player 2 = Black

            self.player_color = None
            self.bot_color = None


    # ========================================================
    # TURN
    # ========================================================

    @property
    def current_player_id(self):

        if self.board.turn == chess.WHITE:

            return self.player1_id

        if self.mode == "player":

            return self.player2_id

        return None


    @property
    def current_player_name(self):

        if self.board.turn == chess.WHITE:

            return self.player1_name

        return self.player2_name


    # ========================================================
    # PLAYER CHECK
    # ========================================================

    def is_player(self, user_id):

        user_id = str(user_id)

        return user_id in {

            self.player1_id,
            self.player2_id

        }


    def player_turn_for(self, user_id):

        user_id = str(user_id)

        if not self.is_player(user_id):

            return False


        # ----------------------------------------------------
        # Bot mode
        # ----------------------------------------------------

        if self.mode == "bot":

            return (

                user_id
                == self.player1_id

                and

                self.board.turn
                == self.player_color

            )


        # ----------------------------------------------------
        # Player mode
        # ----------------------------------------------------

        return (
            user_id
            == self.current_player_id
        )


    # ========================================================
    # LEGAL DESTINATIONS
    # ========================================================

    def legal_destinations(
        self,
        square
    ):

        return [

            move.to_square

            for move in self.board.legal_moves

            if move.from_square
            == square

        ]


    # ========================================================
    # PLAYER MOVE
    # ========================================================

    def make_player_move(
        self,
        user_id,
        from_square,
        to_square
    ):

        user_id = str(user_id)


        if self.finished:

            return (
                False,
                "This game has already ended."
            )


        if not self.player_turn_for(
            user_id
        ):

            return (
                False,
                "It isn't your turn."
            )


        piece = self.board.piece_at(
            from_square
        )


        if piece is None:

            return (
                False,
                "There isn't a piece there."
            )


        # ----------------------------------------------------
        # Bot mode
        # ----------------------------------------------------

        if self.mode == "bot":

            if piece.color != self.player_color:

                return (
                    False,
                    "That's not your piece."
                )


        # ----------------------------------------------------
        # Player mode
        # ----------------------------------------------------

        else:

            expected_color = (

                chess.WHITE

                if user_id
                == self.player1_id

                else chess.BLACK

            )


            if piece.color != expected_color:

                return (
                    False,
                    "That's not your piece."
                )


        # ----------------------------------------------------
        # Promotion
        # ----------------------------------------------------

        promotion = None


        if (

            piece.piece_type
            == chess.PAWN

            and

            chess.square_rank(
                to_square
            ) in (0, 7)

        ):

            # Queen promotion for now.
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


        san = self.board.san(
            move
        )


        self.board.push(
            move
        )


        self.last_move = move


        self.move_history.append(
            san
        )


        self.last_player_name = (
            self.current_player_name_for_move(
                user_id
            )
        )


        self.selected_square = None


        self.check_game_end()


        return (
            True,
            san
        )


    # ========================================================
    # PLAYER NAME
    # ========================================================

    def current_player_name_for_move(
        self,
        user_id
    ):

        if str(user_id) == self.player1_id:

            return self.player1_name

        return self.player2_name


    # ========================================================
    # BOT MOVE
    # ========================================================

    def make_bot_move(self):

        if self.mode != "bot":

            return None


        if self.finished:

            return None


        if self.player_turn_for(
            self.player1_id
        ):

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


        san = self.board.san(
            move
        )


        self.board.push(
            move
        )


        self.last_move = move


        self.move_history.append(
            san
        )


        self.check_game_end()


        return san


    # ========================================================
    # SIMPLE BOT AI
    # ========================================================

    def choose_bot_move(
        self,
        legal_moves
    ):

        # ----------------------------------------------------
        # Checkmate
        # ----------------------------------------------------

        for move in legal_moves:

            test_board = (
                self.board.copy()
            )


            test_board.push(
                move
            )


            if test_board.is_checkmate():

                return move


        # ----------------------------------------------------
        # Captures
        # ----------------------------------------------------

        values = {

            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 100,

        }


        captures = [

            move

            for move in legal_moves

            if self.board.is_capture(
                move
            )

        ]


        if captures:

            def score(move):

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


                if self.board.is_en_passant(
                    move
                ):

                    return 1


                return 0


            return max(
                captures,
                key=score
            )


        # ----------------------------------------------------
        # Checks
        # ----------------------------------------------------

        checks = []


        for move in legal_moves:

            test_board = (
                self.board.copy()
            )


            test_board.push(
                move
            )


            if test_board.is_check():

                checks.append(
                    move
                )


        if checks:

            return random.choice(
                checks
            )


        # ----------------------------------------------------
        # Random legal move
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

            winner_color = (
                not self.board.turn
            )


            if self.mode == "bot":

                self.result = (

                    "win"

                    if winner_color
                    == self.player_color

                    else "loss"

                )


                self.winner_name = (

                    self.player1_name

                    if winner_color
                    == self.player_color

                    else self.player2_name

                )

            else:

                self.result = "win"


                self.winner_name = (

                    self.player1_name

                    if winner_color
                    == chess.WHITE

                    else self.player2_name

                )


        elif (

            self.board.is_stalemate()

            or

            self.board.is_insufficient_material()

            or

            self.board.is_fivefold_repetition()

            or

            self.board.is_seventyfive_moves()

        ):

            self.finished = True

            self.result = "draw"


    # ========================================================
    # RESIGN
    # ========================================================

    def resign(
        self,
        user_id
    ):

        user_id = str(user_id)


        if self.finished:

            return


        if not self.is_player(
            user_id
        ):

            return


        self.finished = True

        self.result = "loss"


        if user_id == self.player1_id:

            self.winner_name = (
                self.player2_name
            )

        else:

            self.winner_name = (
                self.player1_name
            )


# ============================================================
# GAME MANAGEMENT
# ============================================================

def get_game(
    user_id
):

    with GAMES_LOCK:

        return GAMES.get(
            str(user_id)
        )


def create_game(
    player1_id,
    mode="bot",
    player2_id=None,
    player1_name="Player 1",
    player2_name="BurstSay",
    color=None
):

    with GAMES_LOCK:

        game = ChessGame(

            player1_id=player1_id,

            player2_id=player2_id,

            mode=mode,

            player1_name=player1_name,

            player2_name=player2_name,

            color=color

        )


        # Player 1 lookup

        GAMES[
            str(player1_id)
        ] = game


        # Player 2 lookup
        #
        # This is important:
        # both Discord IDs point to
        # the EXACT SAME game object.

        if player2_id:

            GAMES[
                str(player2_id)
            ] = game


        return game


def delete_game(
    user_id
):

    with GAMES_LOCK:

        game = GAMES.pop(
            str(user_id),
            None
        )


        if game:

            GAMES.pop(
                game.player1_id,
                None
            )


            if game.player2_id:

                GAMES.pop(
                    game.player2_id,
                    None
                )


        return game


# ============================================================
# BOARD RENDERING
# ============================================================

def render_board(
    game
):

    image = Image.new(

        "RGB",

        (
            BOARD_SIZE,
            BOARD_SIZE
        ),

        LIGHT_SQUARE

    )


    draw = ImageDraw.Draw(
        image
    )


    # --------------------------------------------------------
    # Board orientation
    # --------------------------------------------------------

    if (

        game.mode == "bot"

        and

        game.player_color
        == chess.BLACK

    ):

        display_squares = [

            chess.square(
                7 - file,
                rank
            )

            for rank in range(8)

            for file in range(8)

        ]

    else:

        display_squares = [

            chess.square(
                file,
                7 - rank
            )

            for rank in range(8)

            for file in range(8)

        ]


    # --------------------------------------------------------
    # Squares
    # --------------------------------------------------------

    for index, square in enumerate(
        display_squares
    ):

        file_index = index % 8

        rank_index = index // 8


        x = (
            file_index
            * SQUARE_SIZE
        )


        y = (
            rank_index
            * SQUARE_SIZE
        )


        color = (

            DARK_SQUARE

            if (
                file_index
                + rank_index
            ) % 2

            else LIGHT_SQUARE

        )


        if game.last_move:

            if square in (

                game.last_move.from_square,

                game.last_move.to_square

            ):

                color = LAST_MOVE_COLOR


        if (
            game.selected_square
            == square
        ):

            color = SELECTED_COLOR


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


    # --------------------------------------------------------
    # Pieces
    # --------------------------------------------------------

    for square, piece in (
        game.board.piece_map().items()
    ):

        index = display_squares.index(
            square
        )


        file_index = index % 8

        rank_index = index // 8


        x = (
            file_index
            * SQUARE_SIZE
        )


        y = (
            rank_index
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


        draw.text(

            (
                px + 2,
                py + 2
            ),

            symbol,

            font=PIECE_FONT,

            fill=(0, 0, 0)

        )


        draw.text(

            (
                px,
                py
            ),

            symbol,

            font=PIECE_FONT,

            fill=(

                WHITE_PIECE

                if piece.color
                == chess.WHITE

                else BLACK_PIECE

            )

        )


    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    if (

        game.mode == "bot"

        and

        game.player_color
        == chess.BLACK

    ):

        shown_files = "hgfedcba"

        shown_ranks = "12345678"

    else:

        shown_files = "abcdefgh"

        shown_ranks = "87654321"


    for index, letter in enumerate(
        shown_files
    ):

        draw.text(

            (

                index
                * SQUARE_SIZE
                + 6,

                BOARD_SIZE - 21

            ),

            letter,

            font=COORD_FONT,

            fill=(

                DARK_SQUARE

                if index % 2 == 0

                else LIGHT_SQUARE

            )

        )


    for index, number in enumerate(
        shown_ranks
    ):

        draw.text(

            (
                5,

                index
                * SQUARE_SIZE
                + 4

            ),

            number,

            font=COORD_FONT,

            fill=(

                DARK_SQUARE

                if index % 2 == 0

                else LIGHT_SQUARE

            )

        )


    # --------------------------------------------------------
    # PNG
    # --------------------------------------------------------

    output = io.BytesIO()


    image.save(

        output,

        format="PNG"

    )


    output.seek(0)


    return output
