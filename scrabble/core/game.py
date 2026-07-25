"""État d'une partie et machine à états des tours.

`Game` orchestre le sac, le plateau, les chevalets et les scores. Il expose
trois actions de jeu — `play`, `exchange`, `pass_turn` — et émet des
`GameEvent` que l'UI peut observer pour déclencher les animations, sans que le
cœur du jeu ne connaisse quoi que ce soit à l'interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from .bag import Bag
from .board import Board, Placement
from .dictionary import Dictionary
from .rack import Rack, RACK_SIZE
from .rules import MoveResult, validate_and_score


class EventType(Enum):
    MOVE_PLAYED = auto()   # un mot a été posé (payload: MoveResult, joueur)
    BINGO = auto()         # « Scrabble » ! 7 tuiles posées (animation spéciale)
    EXCHANGED = auto()     # échange de lettres
    PASSED = auto()        # tour passé
    GAME_OVER = auto()     # partie terminée


@dataclass
class GameEvent:
    type: EventType
    player: int
    payload: dict = field(default_factory=dict)


@dataclass
class Player:
    name: str
    rack: Rack
    score: int = 0
    is_ai: bool = False


class Game:
    def __init__(
        self,
        player_names: list[str],
        dictionary: Dictionary | None = None,
        ai_flags: list[bool] | None = None,
        seed: int | None = None,
    ) -> None:
        if not 2 <= len(player_names) <= 4:
            raise ValueError("Le Scrabble se joue de 2 à 4 joueurs.")
        self.dictionary = dictionary or Dictionary.load_default()
        self.board = Board()
        self.bag = Bag(seed=seed)
        ai_flags = ai_flags or [False] * len(player_names)
        self.players = [
            Player(name=n, rack=Rack(self.bag.draw(RACK_SIZE)), is_ai=ai)
            for n, ai in zip(player_names, ai_flags)
        ]
        self.current = 0
        self.is_over = False
        self._consecutive_scoreless = 0  # 6 tours blancs => fin de partie
        self.events: list[GameEvent] = []

    # -- Introspection ----------------------------------------------------
    @property
    def current_player(self) -> Player:
        return self.players[self.current]

    def _emit(self, event: GameEvent) -> None:
        self.events.append(event)

    # -- Actions ----------------------------------------------------------
    def play(self, placements: list[Placement]) -> MoveResult:
        """Pose un mot. Lève `InvalidMove` si le coup est illégal (l'état du
        jeu reste alors inchangé : on valide *avant* de modifier quoi que ce soit)."""
        self._ensure_active()
        player = self.current_player
        letters = [p.letter for p in placements]
        if not player.rack.can_play(letters):
            from .rules import InvalidMove
            raise InvalidMove("not_in_rack", "Tuiles absentes du chevalet.")

        result = validate_and_score(self.board, placements, self.dictionary)

        # À partir d'ici le coup est valide : on applique les effets.
        self.board.commit(placements)
        player.rack.remove(letters)
        player.rack.add(self.bag.draw(RACK_SIZE - len(player.rack)))
        player.score += result.total
        self._consecutive_scoreless = 0

        self._emit(GameEvent(EventType.MOVE_PLAYED, self.current,
                             {"result": result}))
        if result.is_bingo:
            self._emit(GameEvent(EventType.BINGO, self.current,
                                 {"result": result}))

        # Fin de partie : le joueur a vidé son chevalet et le sac est vide.
        if not player.rack.tiles and self.bag.is_empty:
            self._end_game()
        else:
            self._advance()
        return result

    def exchange(self, tiles: list[str]) -> list[str]:
        """Échange des tuiles du chevalet (impossible si le sac est vide)."""
        self._ensure_active()
        player = self.current_player
        if self.bag.is_empty:
            from .rules import InvalidMove
            raise InvalidMove("bag_empty", "Le sac est vide : échange impossible.")
        for t in tiles:
            if t not in player.rack:
                from .rules import InvalidMove
                raise InvalidMove("not_in_rack", f"Tuile absente : {t!r}.")

        for t in tiles:
            player.rack.tiles.remove(t)
        player.rack.add(self.bag.exchange(tiles))
        self._register_scoreless()
        self._emit(GameEvent(EventType.EXCHANGED, self.current,
                             {"count": len(tiles)}))
        self._advance()
        return list(player.rack.tiles)

    def pass_turn(self) -> None:
        self._ensure_active()
        self._emit(GameEvent(EventType.PASSED, self.current))
        self._register_scoreless()
        self._advance()

    # -- Machine à états --------------------------------------------------
    def _advance(self) -> None:
        self.current = (self.current + 1) % len(self.players)

    def _register_scoreless(self) -> None:
        self._consecutive_scoreless += 1
        # Règle usuelle : la partie s'arrête après 6 tours sans score.
        if self._consecutive_scoreless >= len(self.players) * 3:
            self._end_game()

    def _end_game(self) -> None:
        # Décompte final : chaque joueur perd la valeur des tuiles restantes.
        from .tiles import letter_value
        for p in self.players:
            p.score -= sum(letter_value(t) for t in p.rack.tiles if t != "?")
        self.is_over = True
        self._emit(GameEvent(EventType.GAME_OVER, self.current,
                             {"scores": [p.score for p in self.players]}))

    def _ensure_active(self) -> None:
        if self.is_over:
            from .rules import InvalidMove
            raise InvalidMove("game_over", "La partie est terminée.")
