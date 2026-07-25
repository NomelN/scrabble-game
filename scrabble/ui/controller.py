"""Contrôleur : relie la partie (`core`), les vues et l'IA.

Le coup en cours de composition est modélisé par une liste de **slots** (l'ordre
d'affichage du chevalet). Chaque slot porte sa lettre et, s'il est posé sur le
plateau, la case correspondante. Ce modèle rend naturelles les quatre
manipulations : poser, **déplacer** une tuile posée, la **ramener** au chevalet,
et **réordonner** les lettres — sans jamais désynchroniser l'affichage.

Le tour de l'IA est calculé dans un *thread* (l'appel réseau DeepSeek ne fige
donc pas l'UI). Toutes les animations sont déclenchées par les **événements**
émis par `Game`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..ai import Action, ActionKind, AIPlayer
from ..core.board import Placement
from ..core.game import EventType, Game
from ..core.rules import InvalidMove
from ..core.tiles import BLANK
from ..definitions import Definitions
from ..stats import Stats
from . import animations
from .board_view import BoardView
from .rack_view import RackView


@dataclass
class RackSlot:
    """Une position du chevalet : sa lettre, et la case où elle est posée (ou None)."""
    letter: str                         # tuile réelle ('?' pour un joker)
    cell: tuple[int, int] | None = None
    display: str | None = None          # lettre effectivement posée (joker -> minuscule)


class _AiSignals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _DefSignals(QObject):
    done = Signal(str, str)   # mot, définition


class _DefWorker(QRunnable):
    """Récupère une définition hors du thread UI (secours DeepSeek = réseau)."""

    def __init__(self, definitions: Definitions, word: str) -> None:
        super().__init__()
        self._definitions = definitions
        self._word = word
        self.signals = _DefSignals()

    @Slot()
    def run(self) -> None:
        try:
            text = self._definitions.remote_lookup(self._word) or ""
        except Exception:  # pragma: no cover - garde-fou
            text = ""
        self.signals.done.emit(self._word, text)


class _AiWorker(QRunnable):
    """Calcule la décision de l'IA hors du thread UI (lecture seule du jeu)."""

    def __init__(self, ai: AIPlayer, game: Game) -> None:
        super().__init__()
        self._ai = ai
        self._game = game
        self.signals = _AiSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.done.emit(self._ai.choose(self._game))
        except Exception as exc:  # pragma: no cover - garde-fou
            self.signals.failed.emit(str(exc))


class GameController(QObject):
    status_changed = Signal(str)
    comment_changed = Signal(str)
    scores_changed = Signal(list)
    bag_changed = Signal(int)
    definition_changed = Signal(str, str)   # mot, définition (ou "" / "…")
    game_over = Signal(bool, int)           # (le joueur a gagné, score du joueur)

    def __init__(
        self,
        game: Game,
        board_view: BoardView,
        rack_view: RackView,
        ai_players: dict[int, AIPlayer],
        human_index: int = 0,
        blank_resolver: Callable[[], str | None] | None = None,
        definitions: Definitions | None = None,
        stats: Stats | None = None,
    ) -> None:
        super().__init__()
        self.game = game
        self.board = board_view
        self.rack = rack_view
        self.ai_players = ai_players
        self.human_index = human_index
        self.blank_resolver = blank_resolver or self._default_blank_resolver
        self.definitions = definitions or Definitions.load_default()
        self.stats = stats
        self.sync_ai = False

        self._slots: list[RackSlot] = []
        self._events_seen = 0
        #: contrôleur actif ? Passe à False via shutdown() quand la partie est
        #: remplacée, pour que les workers en cours ne touchent plus les vues
        #: (dont le plateau détruit) — évite les segfaults.
        self._active = True
        #: workers en cours, gardés en vie explicitement (sinon le GC Python
        #: peut les détruire pendant que Qt les exécute → segfault).
        self._workers: set = set()

        # L'image de glisser du chevalet est dimensionnée à la case du plateau.
        self.rack.set_cell_size_provider(self.board.screen_cell_size)

        self.board.cell_clicked.connect(self.place_at)
        self.board.tile_dropped.connect(self.place_index_at)
        self.board.pending_moved.connect(self.move_pending)
        self.rack.tile_selected.connect(self._on_rack_selected)
        self.rack.reorder_requested.connect(self.reorder)
        self.rack.return_requested.connect(self.return_to_rack)

    # -- Introspection (utilisée par les tests) ---------------------------
    @property
    def pending_count(self) -> int:
        return sum(1 for s in self._slots if s.cell is not None)

    @property
    def placed_cells(self) -> set[tuple[int, int]]:
        return {s.cell for s in self._slots if s.cell is not None}

    def shutdown(self) -> None:
        """Désactive le contrôleur (partie remplacée / fenêtre fermée) : les
        callbacks des workers encore en vol deviennent des no-op."""
        self._active = False

    # -- Démarrage --------------------------------------------------------
    def start(self) -> None:
        self._rebuild_slots()
        self._refresh_scores()
        self._refresh_bag()
        self._announce_turn()
        if self._current_is_ai():
            self._run_ai_turn()

    def shuffle_rack(self) -> None:
        """Réordonne aléatoirement le chevalet (bouton « Mélanger »)."""
        if self._current_is_ai():
            return
        import random
        self.recall()
        random.shuffle(self._slots)
        self._refresh_rack()

    # -- Saisie humaine : pose / déplacement / retour / réordonnancement --
    @Slot(int)
    def _on_rack_selected(self, index: int) -> None:
        if 0 <= index < len(self._slots) and self._slots[index].cell is not None:
            self.rack.clear_selection()

    @Slot(int, int)
    def place_at(self, row: int, col: int) -> None:
        """Pose la tuile sélectionnée (interaction au clic)."""
        self.place_index_at(row, col, self.rack.selected_index())

    @Slot(int, int, int)
    def place_index_at(self, row: int, col: int, idx: int | None) -> None:
        """Pose la tuile d'indice `idx` du chevalet sur une case (clic ou glisser)."""
        if self._current_is_ai() or idx is None or not 0 <= idx < len(self._slots):
            return
        slot = self._slots[idx]
        if slot.cell is not None:                 # déjà posée
            return
        if not self._cell_free(row, col):
            self.status_changed.emit("Case déjà occupée.")
            return
        display = slot.letter
        if slot.letter == BLANK:
            chosen = self.blank_resolver()
            if not chosen:
                return
            display = chosen.lower()              # minuscule = joker (0 point)
        slot.cell = (row, col)
        slot.display = display
        self.board.place_pending(row, col, display)
        self._refresh_rack()

    @Slot(int, int, int, int)
    def move_pending(self, fr: int, fc: int, tr: int, tc: int) -> None:
        """Déplace une tuile déjà posée vers une autre case libre."""
        if self._current_is_ai() or (fr, fc) == (tr, tc):
            return
        if not self._cell_free(tr, tc):
            self.status_changed.emit("Case déjà occupée.")
            return
        slot = self._slot_at_cell(fr, fc)
        if slot is None:
            return
        slot.cell = (tr, tc)
        self.board.move_pending_tile((fr, fc), (tr, tc))

    @Slot(int, int, int)
    def return_to_rack(self, row: int, col: int, target: int) -> None:
        """Ramène une tuile posée dans le chevalet, à la position `target`."""
        if self._current_is_ai():
            return
        slot = self._slot_at_cell(row, col)
        if slot is None:
            return
        slot.cell = None
        slot.display = None
        self.board.remove_pending_at((row, col))
        self._move_slot(slot, target)
        self._refresh_rack()

    @Slot(int, int)
    def reorder(self, frm: int, to: int) -> None:
        """Réordonne les lettres du chevalet (glisser une tuile sur une autre)."""
        if not 0 <= frm < len(self._slots):
            return
        self._move_slot(self._slots[frm], to)
        self._refresh_rack()

    def recall(self) -> None:
        """Annule le coup en cours : toutes les tuiles reviennent au chevalet."""
        for slot in self._slots:
            if slot.cell is not None:
                self.board.remove_pending_at(slot.cell)
                slot.cell = None
                slot.display = None
        self._refresh_rack()

    # -- Validation du coup ----------------------------------------------
    def commit(self) -> None:
        if self._current_is_ai():
            return
        placed = [s for s in self._slots if s.cell is not None]
        if not placed:
            return
        placements = [Placement(s.cell[0], s.cell[1], s.display) for s in placed]
        try:
            self.game.play(placements)
        except InvalidMove as exc:
            self.status_changed.emit(f"Coup refusé : {exc.detail or exc.reason}")
            return                                 # on laisse la composition en place
        # Coup accepté : tuiles en attente -> tuiles définitives animées.
        self.board.clear_pending()
        for p in placements:
            self.board.place_tile(p.row, p.col, p.letter)
        self._after_turn()

    def exchange_selected(self) -> None:
        """Échange les tuiles actuellement tirées sur le plateau (ou la sélectionnée)."""
        if self._current_is_ai():
            return
        placed = [s for s in self._slots if s.cell is not None]
        if not placed:
            sel = self.rack.selected_index()
            if sel is not None:
                placed = [self._slots[sel]]
        if not placed:
            self.status_changed.emit("Sélectionne les tuiles à échanger.")
            return
        letters = [s.letter for s in placed]
        self.recall()
        try:
            self.game.exchange(letters)
        except InvalidMove as exc:
            self.status_changed.emit(f"Échange impossible : {exc.detail or exc.reason}")
            return
        self._after_turn()

    def pass_turn(self) -> None:
        if self._current_is_ai():
            return
        self.recall()
        self.game.pass_turn()
        self._after_turn()

    # -- Tour de l'IA -----------------------------------------------------
    def _run_ai_turn(self, sync: bool | None = None) -> None:
        if sync is None:
            sync = self.sync_ai
        ai = self.ai_players[self.game.current]
        self.status_changed.emit(f"{self.game.current_player.name} réfléchit…")
        if sync:
            self._apply_ai_action(ai.choose(self.game))
            return
        worker = _AiWorker(ai, self.game)
        worker.setAutoDelete(False)          # on gère nous-mêmes la durée de vie
        self._workers.add(worker)
        worker.signals.done.connect(self._apply_ai_action)
        worker.signals.failed.connect(
            lambda msg: self.status_changed.emit(f"IA en erreur : {msg}")
        )
        worker.signals.done.connect(lambda *_: self._workers.discard(worker))
        worker.signals.failed.connect(lambda *_: self._workers.discard(worker))
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def _apply_ai_action(self, action: Action) -> None:
        if not self._active:          # partie remplacée : ne touche plus les vues
            return
        ai = self.ai_players.get(self.game.current)
        comment = getattr(ai, "last_comment", "")
        if comment:
            self.comment_changed.emit(comment)
        if action.kind is ActionKind.PLAY:
            self.game.play(action.placements)
            for p in action.placements:
                self.board.place_tile(p.row, p.col, p.letter)
        elif action.kind is ActionKind.EXCHANGE:
            self.game.exchange(action.tiles)
        else:
            self.game.pass_turn()
        self._after_turn()

    # -- Après chaque coup ------------------------------------------------
    def _after_turn(self) -> None:
        self._drain_events()
        self._rebuild_slots()
        self._refresh_scores()
        self._refresh_bag()
        if self.game.is_over:
            self.status_changed.emit("Partie terminée !")
            return
        self._announce_turn()
        if self._current_is_ai():
            self._run_ai_turn()

    def _drain_events(self) -> None:
        for event in self.game.events[self._events_seen:]:
            if event.type is EventType.BINGO:
                cells = event.payload["result"].words[0].cells
                animations.bingo_flash(self.board.tiles_at(cells))
                self.status_changed.emit("SCRABBLE ! +50 points 🎉")
            elif event.type is EventType.MOVE_PLAYED:
                res = event.payload["result"]
                name = self.game.players[event.player].name
                self.status_changed.emit(f"{name} joue « {res.main_word} » (+{res.total})")
                # Badge de score (remplace le précédent) + définition du mot.
                self.board.show_score_badge(res.words[0].cells, res.total)
                self._show_definition(res.main_word)
                # Statistiques : uniquement les coups du joueur humain.
                if self.stats is not None and event.player == self.human_index:
                    self.stats.record_move(res.total, res.main_word, res.is_bingo)
            elif event.type is EventType.EXCHANGED:
                name = self.game.players[event.player].name
                self.status_changed.emit(f"{name} échange {event.payload['count']} lettre(s).")
            elif event.type is EventType.PASSED:
                self.status_changed.emit(f"{self.game.players[event.player].name} passe.")
            elif event.type is EventType.GAME_OVER:
                self._record_game_over(event.payload["scores"])
        self._events_seen = len(self.game.events)

    def _record_game_over(self, scores: list[int]) -> None:
        human = scores[self.human_index]
        won = human == max(scores) and scores.count(max(scores)) == 1
        if self.stats is not None:
            self.stats.record_game_end(human, won)
            self.stats.save()
        self.game_over.emit(won, human)

    # -- Définition du mot joué -------------------------------------------
    def _show_definition(self, word: str) -> None:
        """Local d'abord (instantané) ; sinon DeepSeek dans un thread."""
        if not word:
            return
        local = self.definitions.local_lookup(word)
        if local is not None:
            self.definition_changed.emit(word, local)
            return
        if not self.definitions.remote_available:
            self.definition_changed.emit(word, "")   # aucune source
            return
        self.definition_changed.emit(word, "…")       # en attente de DeepSeek
        worker = _DefWorker(self.definitions, word)
        worker.setAutoDelete(False)
        self._workers.add(worker)
        worker.signals.done.connect(self._on_definition_ready)
        worker.signals.done.connect(lambda *_: self._workers.discard(worker))
        QThreadPool.globalInstance().start(worker)

    @Slot(str, str)
    def _on_definition_ready(self, word: str, text: str) -> None:
        if self._active:
            self.definition_changed.emit(word, text)

    # -- Helpers ----------------------------------------------------------
    def _cell_free(self, row: int, col: int) -> bool:
        return self.game.board.is_empty_at(row, col) and not self.board.has_pending_at(row, col)

    def _slot_at_cell(self, row: int, col: int) -> RackSlot | None:
        for slot in self._slots:
            if slot.cell == (row, col):
                return slot
        return None

    def _move_slot(self, slot: RackSlot, target: int) -> None:
        self._slots.remove(slot)
        target = max(0, min(target, len(self._slots)))
        self._slots.insert(target, slot)

    def _current_is_ai(self) -> bool:
        return self.game.current in self.ai_players

    def _rebuild_slots(self) -> None:
        """Reconstruit le chevalet depuis l'état du jeu (nouvelles tuiles piochées)."""
        self._slots = [RackSlot(letter) for letter in
                       self.game.players[self.human_index].rack.tiles]
        self._refresh_rack()

    def _refresh_rack(self) -> None:
        self.rack.set_letters([s.letter for s in self._slots])
        self.rack.set_used({i for i, s in enumerate(self._slots) if s.cell is not None})

    def _refresh_scores(self) -> None:
        self.scores_changed.emit([(p.name, p.score) for p in self.game.players])

    def _refresh_bag(self) -> None:
        self.bag_changed.emit(len(self.game.bag))

    def _announce_turn(self) -> None:
        if not self._current_is_ai():
            self.status_changed.emit("À toi de jouer.")

    @staticmethod
    def _default_blank_resolver() -> str | None:
        from PySide6.QtWidgets import QInputDialog
        letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        letter, ok = QInputDialog.getItem(
            None, "Joker", "Ce joker représente la lettre :", letters, 0, False
        )
        return letter if ok else None
