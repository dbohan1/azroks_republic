#!/usr/bin/env python3
"""
Azrok's Republic — Digital Pass-and-Play Edition
Rules Version 1.4.2

Run with:  python azroks_republic.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
import math

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

SECTORS          = ["Teachers", "Builders", "Miners", "Military"]
BASE_SALARY      = 2
IMPROVEMENT_COST = 7
TAX_COST         = 1
TAX_AMOUNT       = 2
POWDER_COST      = 12
DAGGER_COST      = 16   # action-item header says $16; body says $14 — using header
MAX_IMPROVEMENT  = 3    # 0-indexed: 0=1×  1=2×  2=3×  3=4×
MAX_DROW         = 3
MAX_TURNS        = 10

# Fruits of Labor deck — multipliers applied to the People's pot each turn
FRUITS_DECK_TEMPLATE = [
    0.50, 0.75, 0.75,
    1.00, 1.00, 1.00, 1.00, 1.00,
    1.25, 1.25, 1.25,
    1.50, 1.50, 1.50,
    1.75, 1.75,
    2.00, 2.00,
    2.50, 0.50,
]

def war_cost(turn: int, num_players: int) -> int:
    per = 1 if turn <= 3 else (2 if turn <= 6 else 3)
    return per * num_players

# AI personality roster  {name: short description}
AI_TYPES = {
    "The Idealist": "Invests heavily for the common good. Loyal to the Republic.",
    "The Miser":    "Hoards every coin and improves tools. Contributes nothing to the pot.",
    "The Wrecker":  "Sabotages if it serves the Drow. Dangerous and unpredictable.",
    "The Schemer":  "Uses tax to weaken rivals. Cold, calculating, self-serving.",
}


# ══════════════════════════════════════════════════════════════════════════════
#  THEME — Windows 95
# ══════════════════════════════════════════════════════════════════════════════

BG        = "#c0c0c0"   # Classic Win95 window/button face
BG_MED    = "#808080"   # Shadow / darker gray
BG_CARD   = "#c0c0c0"   # Panel face (depth via relief, not color)
W95_BLUE  = "#000080"   # Title-bar blue
W95_WHITE = "#ffffff"   # Input field / highlight text
RED       = "#800000"   # Dark red  (danger actions)
RED_DK    = "#c00000"
GOLD      = "#6b5900"   # Dark olive-gold (important/GS)
GREEN     = "#005000"   # Dark green (positive actions)
GREEN_LT  = "#006400"
DROW_CLR  = "#800080"   # Purple (drow / traitor)
TEXT      = "#000000"   # Standard black text
TEXT_DIM  = "#444444"   # Dimmed / secondary text

F_TITLE   = ("MS Sans Serif", 14, "bold")
F_HEAD    = ("MS Sans Serif", 11, "bold")
F_SUB     = ("MS Sans Serif", 10, "bold")
F_BODY    = ("MS Sans Serif",  9)
F_SMALL   = ("MS Sans Serif",  8)
F_MONO    = ("Courier New",    9)
F_BTN     = ("MS Sans Serif",  9)


def lbl(parent, text, font=F_BODY, fg=TEXT, bg=BG, anchor="center", justify="center", **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg,
                    anchor=anchor, justify=justify, **kw)

def sep(parent, bg=BG_MED, height=2):
    """Win95 sunken-line separator."""
    return tk.Frame(parent, bg=bg, height=height, relief="sunken", bd=1)

def btn(parent, text, cmd, color=BG, fg=TEXT, width=22, state="normal"):
    """Win95-style raised button."""
    return tk.Button(
        parent, text=text, command=cmd, font=F_BTN,
        bg=color, fg=fg,
        activebackground=color, activeforeground=fg,
        relief="raised", bd=2, padx=8, pady=3, width=width,
        cursor="arrow", state=state,
    )

def card(parent, title="", **kw):
    """Win95-style group-box (LabelFrame with groove border)."""
    if title:
        return tk.LabelFrame(parent, text=title, font=F_SMALL, fg=TEXT, bg=BG_CARD,
                             relief="groove", bd=2, padx=8, pady=6, **kw)
    return tk.Frame(parent, bg=BG_CARD, relief="groove", bd=2, padx=8, pady=6, **kw)

def titlebar(parent, title):
    """Simulate a Win95 dialog title bar."""
    bar = tk.Frame(parent, bg=W95_BLUE, pady=3, padx=6)
    tk.Label(bar, text=title, font=("MS Sans Serif", 9, "bold"),
             fg=W95_WHITE, bg=W95_BLUE).pack(side="left")
    return bar


# ══════════════════════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════════════════════

class Player:
    def __init__(self, name: str, sector: str = ""):
        self.name        = name
        self.sector      = sector
        self.role        = ""
        self.is_gs       = False
        self.is_ai       = False
        self.money       = 0
        self.improvement = 0   # 0–3
        self.used_tax    = False

    @property
    def salary(self) -> int:
        return BASE_SALARY * (self.improvement + 1)

    @property
    def mult_label(self) -> str:
        return f"{self.improvement + 1}×"

    def can_improve(self)    -> bool:
        return self.improvement < MAX_IMPROVEMENT and self.money >= IMPROVEMENT_COST
    def can_tax(self)        -> bool:
        return not self.used_tax and self.money >= TAX_COST
    def can_buy_powder(self) -> bool:
        return self.money >= POWDER_COST
    def can_buy_dagger(self) -> bool:
        return self.money >= DAGGER_COST


class AIPlayer(Player):
    """A player slot controlled by an AI personality."""

    def __init__(self, name: str, ai_type: str):
        super().__init__(name)
        self.ai_type = ai_type
        self.is_ai   = True

    # ── Public entry point ────────────────────────────────────────────────────

    def decide(self, game: "GameState") -> tuple:
        """Execute a full AI turn. Returns (log_lines, game_ended).
        log_lines is a list of (text, tag) matching EndOfTurnScreen conventions.
        """
        log = []
        log.append((f'[{self.ai_type}] — {AI_TYPES[self.ai_type]}', "dim"))

        if self.ai_type == "The Idealist":
            self._act_idealist(game, log)
        elif self.ai_type == "The Miser":
            self._act_miser(game, log)
        elif self.ai_type == "The Wrecker":
            self._act_wrecker(game, log)
        elif self.ai_type == "The Schemer":
            self._act_schemer(game, log)

        return log, game.game_over

    # ── Shared action primitives ──────────────────────────────────────────────

    def _do_improve(self, game, log) -> bool:
        if self.can_improve():
            self.money -= IMPROVEMENT_COST
            self.improvement += 1
            log.append((f"Improved tools to {self.mult_label}. "
                         f"Next salary: ${self.salary}/turn.", "ok"))
            return True
        return False

    def _do_invest(self, game, log, amount: int) -> int:
        amount = max(0, min(amount, self.money))
        if amount > 0:
            self.money -= amount
            game.people_pot += amount
            log.append((f"Invested ${amount} in the People's Pot "
                         f"(pot now ${game.people_pot}).", "ok"))
        else:
            log.append(("Invested $0 in the People's Pot. Free-riding!", "dim"))
        return amount

    def _do_tax(self, game, log) -> bool:
        if not self.can_tax():
            return False
        targets = [p for p in game.players if p is not self]
        if not targets:
            return False
        target = max(targets, key=lambda p: p.money)
        self.money -= TAX_COST
        removed = min(target.money, TAX_AMOUNT)
        target.money -= removed
        self.used_tax = True
        log.append((f"Taxed {target.name} — removed ${removed}. "
                     f"(Money discarded.)", "dim"))
        return True

    def _do_powder(self, game, log) -> bool:
        if not self.can_buy_powder():
            return False
        self.money -= POWDER_COST
        game.drow_victories += 1
        log.append((f"Bought a Powder Charge! Walls breached. "
                     f"Drow victories: {game.drow_victories}/{MAX_DROW}.", "bad"))
        if game.drow_victories >= MAX_DROW:
            game.game_over    = True
            game.republic_won = False
            log.append(("The Drow have overcome the Republic! "
                         "Agents of the Drow WIN!", "bad"))
        return True

    def _do_dagger(self, game, log) -> bool:
        if not self.can_buy_dagger():
            return False
        self.money -= DAGGER_COST
        game.game_over    = True
        game.republic_won = True
        log.append((f"Bought Azrok's Dagger! The Republic wins IMMEDIATELY!", "ok"))
        return True

    # ── AI Strategies ─────────────────────────────────────────────────────────

    def _act_idealist(self, game, log):
        """Cooperates fully. Invests most of their money; upgrades tools modestly."""
        if "Brother" in self.role and self._do_dagger(game, log):
            return
        # Invest generously — keep a $3 buffer
        self._do_invest(game, log, max(0, self.money - 3))
        # Upgrade tools once if early in progression
        if self.improvement < 2:
            self._do_improve(game, log)

    def _act_miser(self, game, log):
        """Hoards money. Improves tools first, then taxes, invests nothing."""
        if self._do_dagger(game, log):
            return
        # Max out tools
        self._do_improve(game, log)
        # Kneecap the richest rival
        self._do_tax(game, log)
        # Contribute nothing to the pot
        self._do_invest(game, log, 0)

    def _act_wrecker(self, game, log):
        """Sabotages if Drow. Acts as a cautious cooperator if Brother."""
        if "Drow" in self.role:
            # Buy powder to score Drow victories
            if self._do_powder(game, log):
                if game.game_over:
                    return
            # Weaken the richest player
            self._do_tax(game, log)
            # Never contribute to pot
            self._do_invest(game, log, 0)
        else:
            # Revealed as Brother — play cooperatively
            if self._do_dagger(game, log):
                return
            self._do_invest(game, log, self.money // 2)

    def _act_schemer(self, game, log):
        """Tax-focused opportunist. Moderate investor, upgrades tools early."""
        if "Brother" in self.role and self._do_dagger(game, log):
            return
        # Tax first to weaken rivals
        self._do_tax(game, log)
        # Invest moderately (1/3 of money)
        self._do_invest(game, log, max(0, self.money // 3))
        # Upgrade tools while still cheap
        if self.improvement < 2:
            self._do_improve(game, log)


class GameState:
    def __init__(self, players: list):
        self.players        = players
        self.turn           = 1
        self.drow_victories = 0
        self.people_pot     = 0
        self.turn_order     = []
        self.current_idx    = 0
        self.fruits_deck    = FRUITS_DECK_TEMPLATE.copy()
        random.shuffle(self.fruits_deck)
        self.game_over      = False
        self.republic_won   = None   # True / False / None

    @property
    def current_player(self):
        if self.current_idx < len(self.turn_order):
            return self.turn_order[self.current_idx]
        return None

    @property
    def gs(self) -> Player:
        return next(p for p in self.players if p.is_gs)

    def build_turn_order(self, first_player: Player):
        n   = len(self.players)
        gs  = self.gs
        idx = self.players.index(first_player)
        order = []
        for _ in range(n):
            p = self.players[idx % n]
            if p is not gs:
                order.append(p)
            idx += 1
        order.append(gs)       # GS always takes player turn + resolution last
        self.turn_order  = order
        self.current_idx = 0

    def advance(self):
        self.current_idx += 1

    def deal_salaries(self):
        for p in self.players:
            p.money += p.salary

    def resolve_end_of_turn(self):
        """Returns list of (text, tag) tuples; tag in {ok, bad, gold, dim, normal}."""
        n    = len(self.players)
        cost = war_cost(self.turn, n)
        lines = []

        # 1. War fund
        if self.people_pot >= cost:
            self.people_pot -= cost
            lines.append((f"✅  War fund satisfied — ${cost} taken from pot.", "ok"))
        else:
            self.drow_victories += 1
            lines.append(("❌  War fund NOT met!", "bad"))
            lines.append((f"    Needed ${cost}, pot only had ${self.people_pot}. Drow gain a victory!", "bad"))
            lines.append((f"    Drow victories: {self.drow_victories} / {MAX_DROW}", "bad"))
            self.people_pot = 0
            if self.drow_victories >= MAX_DROW:
                self.game_over    = True
                self.republic_won = False
                return lines

        # 2. Fruits of Labor card
        mult = self.fruits_deck.pop() if self.fruits_deck else 1.0
        lines.append((f"🌾  Fruits of Labor card: ×{mult}", "gold"))

        # 3. Multiply (round up)
        new_pot = math.ceil(self.people_pot * mult)
        lines.append((f"    Pot: ${self.people_pot} × {mult} = ${new_pot} (rounded up)", "dim"))
        self.people_pot = new_pot

        # 4. Distribute (round down)
        share     = self.people_pot // n
        remainder = self.people_pot % n
        for p in self.players:
            p.money += share
        self.people_pot = remainder
        lines.append((f"💰  Each player receives ${share}.", "ok"))
        if remainder:
            lines.append((f"    ${remainder} remains in pot for next round.", "dim"))

        # 5. Advance war track
        self.turn += 1
        lines.append((f"⚔️   War track advanced — now turn {self.turn}.", "normal"))

        # 6. Republic victory?
        if self.turn > MAX_TURNS:
            self.game_over    = True
            self.republic_won = True
            return lines

        for p in self.players:
            p.used_tax = False

        return lines


# ══════════════════════════════════════════════════════════════════════════════
#  APP CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Azrok's Republic")
        self.configure(bg=BG)
        self.geometry("900x680")
        self.minsize(760, 560)
        # Win95-style ttk defaults
        style = ttk.Style()
        try:
            style.theme_use("winnative")
        except Exception:
            style.theme_use("default")
        self.game: GameState = None
        self._frame: tk.Frame = None
        self._goto(SetupScreen)

    def _goto(self, screen_cls, **kw):
        new = screen_cls(self, **kw)
        if self._frame:
            self._frame.destroy()
        self._frame = new
        self._frame.pack(fill="both", expand=True)

    # ── Navigation helpers ─────────────────────────────────────────────────

    def start_game(self, players: list):
        sectors = SECTORS.copy()
        random.shuffle(sectors)
        for i, p in enumerate(players):
            p.sector = sectors[i % len(sectors)]

        # Assign General Secretary (public)
        random.choice(players).is_gs = True

        # Assign secret roles (~1 agent per 3 players, minimum 1)
        n          = len(players)
        num_agents = max(1, n // 3)
        roles      = ["Agent of the Drow"] * num_agents + ["Brother of the Republic"] * (n - num_agents)
        random.shuffle(roles)
        for p, r in zip(players, roles):
            p.role = r

        self.game = GameState(players)
        self.next_role_reveal(0)   # skips AI players automatically

    def next_role_reveal(self, idx: int):
        if idx >= len(self.game.players):
            self._goto(TurnStartScreen)
        else:
            p = self.game.players[idx]
            if p.is_ai:
                # AI players don't need a private role reveal — skip ahead
                self.next_role_reveal(idx + 1)
            else:
                self._goto(RoleRevealScreen, player_idx=idx)

    def show_player_turn(self):
        if self.game.current_player is None:
            lines = self.game.resolve_end_of_turn()
            self._goto(EndOfTurnScreen, lines=lines)
        else:
            p = self.game.current_player
            if p.is_ai:
                log, ended = p.decide(self.game)
                self._goto(AITurnScreen, player=p, log=log, game_ended=ended)
            else:
                self._goto(PrivacyScreen, player=p,
                           on_continue=lambda: self._goto(PlayerTurnScreen))

    def next_turn(self):
        self._goto(TurnStartScreen)

    def show_game_over(self):
        self._goto(GameOverScreen)


# ══════════════════════════════════════════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════════════════════════════════════════

class SetupScreen(tk.Frame):
    def __init__(self, master: App, **_):
        super().__init__(master, bg=BG)
        self.master    = master
        self.name_vars = []
        self.type_vars = []   # "Human" or an AI_TYPES key
        self._build()

    def _build(self):
        titlebar(self, "Azrok's Republic").pack(fill="x")

        lbl(self, "AZROK'S REPUBLIC", font=F_TITLE, fg=W95_BLUE).pack(pady=(22, 2))
        lbl(self, "Rules Version 1.4.2", font=F_SMALL, fg=TEXT_DIM).pack()
        sep(self).pack(fill="x", padx=40, pady=12)

        lbl(self, "Game Setup", font=F_HEAD, fg=TEXT).pack(pady=(0, 8))

        # Player count row
        row = tk.Frame(self, bg=BG)
        row.pack()
        lbl(row, "Number of Players:", bg=BG).pack(side="left", padx=(0, 8))
        self.count_var = tk.IntVar(value=4)
        for n in range(2, 9):
            tk.Radiobutton(
                row, text=str(n), variable=self.count_var, value=n,
                font=F_BODY, bg=BG, fg=TEXT, selectcolor=BG,
                activebackground=BG, activeforeground=TEXT,
                relief="flat",
                command=self._rebuild_names,
            ).pack(side="left", padx=3)

        sep(self).pack(fill="x", padx=40, pady=10)

        self.names_frame = tk.Frame(self, bg=BG)
        self.names_frame.pack()
        self._rebuild_names()

        sep(self).pack(fill="x", padx=40, pady=10)
        btn(self, "Begin the Republic", self._start, color=BG, fg=W95_BLUE, width=28).pack(pady=6)

    def _rebuild_names(self):
        for w in self.names_frame.winfo_children():
            w.destroy()
        self.name_vars.clear()
        self.type_vars.clear()
        n = self.count_var.get()

        # Header row
        hdr = tk.Frame(self.names_frame, bg=BG)
        hdr.pack(fill="x", pady=(0, 4))
        lbl(hdr, "Player",      font=F_SMALL, fg=TEXT_DIM, bg=BG, anchor="w", width=8).pack(side="left")
        lbl(hdr, "Name",        font=F_SMALL, fg=TEXT_DIM, bg=BG, anchor="w", width=22).pack(side="left", padx=(0, 6))
        lbl(hdr, "Type",        font=F_SMALL, fg=TEXT_DIM, bg=BG, anchor="w").pack(side="left")

        type_choices = ["Human"] + list(AI_TYPES.keys())

        for i in range(n):
            row = tk.Frame(self.names_frame, bg=BG)
            row.pack(pady=2)

            lbl(row, f"Player {i+1}:", fg=TEXT_DIM, bg=BG, anchor="e", width=8).pack(side="left")

            name_var = tk.StringVar(value=f"Player {i+1}")
            self.name_vars.append(name_var)
            entry = tk.Entry(row, textvariable=name_var, font=F_BODY,
                             bg=W95_WHITE, fg=TEXT, insertbackground=TEXT,
                             relief="sunken", bd=2, width=20)
            entry.pack(side="left", padx=(0, 6))

            type_var = tk.StringVar(value="Human")
            self.type_vars.append(type_var)

            menu = tk.OptionMenu(row, type_var, *type_choices,
                                 command=lambda val, e=entry, nv=name_var:
                                     self._on_type_change(val, e, nv))
            menu.config(font=F_SMALL, bg=BG, fg=TEXT,
                        activebackground=W95_BLUE, activeforeground=W95_WHITE,
                        relief="raised", bd=2, width=16)
            menu["menu"].config(font=F_SMALL, bg=W95_WHITE, fg=TEXT,
                                activebackground=W95_BLUE, activeforeground=W95_WHITE)
            menu.pack(side="left")

    def _on_type_change(self, type_val: str, entry: tk.Entry, name_var: tk.StringVar):
        if type_val != "Human":
            name_var.set(type_val)   # suggest the AI type as a default name
        entry.config(state="normal") # always keep editable

    def _start(self):
        n       = self.count_var.get()
        players = []
        names   = []
        for i in range(n):
            name  = self.name_vars[i].get().strip()
            ptype = self.type_vars[i].get()
            if not name:
                messagebox.showwarning("Missing Name",
                                       f"Please enter a name for Player {i+1}.", parent=self)
                return
            names.append(name)
            if ptype == "Human":
                players.append(Player(name))
            else:
                players.append(AIPlayer(name, ptype))

        if len(set(names)) != len(names):
            messagebox.showwarning("Duplicate Names",
                                   "All player names must be unique.\n"
                                   "Two AI players of the same type will have the same name — "
                                   "rename one.", parent=self)
            return
        self.master.start_game(players)


# ─────────────────────────────────────────────────────────────────────────────

class RoleRevealScreen(tk.Frame):
    def __init__(self, master: App, player_idx: int, **_):
        super().__init__(master, bg=BG)
        self.master     = master
        self.player_idx = player_idx
        self.player     = master.game.players[player_idx]
        self._build()

    def _build(self):
        total = len(self.master.game.players)
        p     = self.player

        titlebar(self, "Azrok's Republic - Role Assignment").pack(fill="x")
        lbl(self, "AZROK'S REPUBLIC", font=F_TITLE, fg=W95_BLUE).pack(pady=(18, 2))
        sep(self).pack(fill="x", padx=40, pady=8)

        lbl(self, f"Player {self.player_idx + 1} of {total}", font=F_SMALL, fg=TEXT_DIM).pack()
        lbl(self, "Pass the device to:", font=F_BODY, fg=TEXT_DIM).pack(pady=(8, 2))
        lbl(self, p.name, font=F_HEAD, fg=W95_BLUE).pack()
        lbl(self, f"Sector: {p.sector}", font=F_SMALL, fg=TEXT_DIM).pack(pady=2)
        if p.is_gs:
            lbl(self, "[ You are the GENERAL SECRETARY ]", font=F_SUB, fg=GOLD).pack(pady=3)

        sep(self).pack(fill="x", padx=40, pady=8)

        self.hint = lbl(self, "Your secret role is hidden.\nPress the button to reveal it privately.", fg=TEXT_DIM)
        self.hint.pack(pady=6)

        # Role card (hidden until revealed)
        self.role_card = card(self, title="Secret Role")
        role_color = DROW_CLR if "Drow" in p.role else GREEN
        lbl(self.role_card, p.role, font=("MS Sans Serif", 13, "bold"), fg=role_color, bg=BG_CARD).pack(pady=4)
        if "Drow" in p.role:
            lbl(self.role_card, "Help the Drow overcome the Republic!\nLet the war fund fail 3 times.",
                font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()
        else:
            lbl(self.role_card, "Defend the Republic!\nKeep the war fund supplied for all turns.",
                font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        self.reveal_btn = btn(self, "Reveal My Role", self._reveal, color=BG, width=24)
        self.reveal_btn.pack(pady=10)

        self.next_btn = btn(self, "Hide & Pass Device", self._next, color=BG, fg=GREEN, width=24)

    def _reveal(self):
        self.hint.pack_forget()
        self.reveal_btn.pack_forget()
        self.role_card.pack(pady=10)
        self.next_btn.pack(pady=10)

    def _next(self):
        self.master.next_role_reveal(self.player_idx + 1)


# ─────────────────────────────────────────────────────────────────────────────

class TurnStartScreen(tk.Frame):
    def __init__(self, master: App, **_):
        super().__init__(master, bg=BG)
        self.master  = master
        self.game    = master.game
        self.rolled  = False
        self._build()

    def _build(self):
        g = self.game
        titlebar(self, f"Azrok's Republic - Turn {g.turn} of {MAX_TURNS}").pack(fill="x")
        lbl(self, "AZROK'S REPUBLIC", font=F_TITLE, fg=W95_BLUE).pack(pady=(16, 2))
        sep(self).pack(fill="x", padx=40, pady=8)

        lbl(self, f"Turn {g.turn}  of  {MAX_TURNS}", font=F_HEAD, fg=TEXT).pack(pady=3)

        # War status banner
        c = card(self, title="War Status")
        c.pack(padx=40, pady=4, fill="x")
        cost = war_cost(g.turn, len(g.players))
        lbl(c, f"War Fund Required This Turn: ${cost}", fg=TEXT, bg=BG_CARD).pack()
        dc = RED if g.drow_victories > 0 else TEXT_DIM
        lbl(c, f"Drow Victories: {g.drow_victories} / {MAX_DROW}", fg=dc, bg=BG_CARD).pack()
        filled = g.turn - 1
        track  = "[" + "#" * filled + "." * (MAX_TURNS - filled) + "]"
        lbl(c, track, font=F_MONO, fg=TEXT_DIM, bg=BG_CARD).pack(pady=2)

        sep(self).pack(fill="x", padx=40, pady=8)

        # Salary phase
        lbl(self, "Salary Distribution", font=F_SUB, fg=TEXT).pack(pady=(0, 4))
        sal_card = card(self, title="Salaries Paid")
        sal_card.pack(padx=40, pady=2, fill="x")

        g.deal_salaries()
        for p in g.players:
            row = tk.Frame(sal_card, bg=BG_CARD)
            row.pack(fill="x", pady=1)
            gs_mk = " [GS]" if p.is_gs else ""
            lbl(row, f"{p.name}{gs_mk}  ({p.sector})", fg=TEXT, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"+${p.salary}  ({p.mult_label})", fg=GREEN, bg=BG_CARD, anchor="e").pack(side="right")

        sep(self).pack(fill="x", padx=40, pady=8)

        # GS dice roll
        gs = g.gs
        lbl(self, f"{gs.name} (General Secretary) rolls for first player", font=F_SUB, fg=TEXT).pack(pady=(0, 3))
        self.dice_lbl = lbl(self, "Press the button below to roll.", fg=TEXT_DIM)
        self.dice_lbl.pack(pady=3)

        self.roll_btn = btn(self, "Roll the Dice", self._roll, color=BG, width=20)
        self.roll_btn.pack(pady=6)

        self.go_btn = btn(self, "Begin Player Turns", self.master.show_player_turn, color=BG, fg=GREEN, width=22)

    def _roll(self):
        g   = self.game
        n   = len(g.players)
        gs  = g.gs
        # Position 1 = GS, position 2 = player to GS's left, etc.
        gs_idx       = g.players.index(gs)
        result       = random.randint(1, n)
        first_player = g.players[(gs_idx + result - 1) % n]
        g.build_turn_order(first_player)

        order_str = " → ".join(p.name for p in g.turn_order)
        self.dice_lbl.config(
            text=f"Rolled: {result}  →  {first_player.name} goes first!\nOrder: {order_str}",
            fg=GOLD,
        )
        self.roll_btn.config(state="disabled")
        self.go_btn.pack(pady=8)


# ─────────────────────────────────────────────────────────────────────────────

class PrivacyScreen(tk.Frame):
    def __init__(self, master: App, player: Player, on_continue, **_):
        super().__init__(master, bg=BG)
        titlebar(self, "Azrok's Republic - Pass Device").pack(fill="x")
        lbl(self, "AZROK'S REPUBLIC", font=F_TITLE, fg=W95_BLUE).pack(pady=(50, 6))
        sep(self).pack(fill="x", padx=40, pady=10)
        lbl(self, "Pass the device to:", fg=TEXT_DIM).pack(pady=(16, 3))
        lbl(self, player.name, font=F_HEAD, fg=W95_BLUE).pack()
        lbl(self, f"{player.sector} Delegate", fg=TEXT_DIM).pack(pady=2)
        if player.is_gs:
            lbl(self, "[ General Secretary ]", fg=GOLD).pack()
        sep(self).pack(fill="x", padx=40, pady=16)
        btn(self, f"I'm {player.name} - Continue", on_continue, color=BG, fg=W95_BLUE, width=32).pack(pady=14)


# ─────────────────────────────────────────────────────────────────────────────

class PlayerTurnScreen(tk.Frame):
    """Main action screen; uses a ttk.Notebook to keep actions organised."""

    def __init__(self, master: App, **_):
        super().__init__(master, bg=BG)
        self.master = master
        self.game   = master.game
        self.player = master.game.current_player
        self._build()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        p = self.player
        g = self.game

        # ── Title bar ──
        titlebar(self, f"Azrok's Republic - {p.name}'s Turn").pack(fill="x")

        # ── Top info bar ──
        top = tk.Frame(self, bg=BG, padx=10, pady=4, relief="flat")
        top.pack(fill="x")
        gs_mk = "  [GS]" if p.is_gs else ""
        lbl(top, f"{p.name}'s Turn{gs_mk}", font=F_HEAD, fg=W95_BLUE, bg=BG).pack(side="left")
        lbl(top, f"Turn {g.turn}/{MAX_TURNS}", fg=TEXT_DIM, bg=BG).pack(side="right")

        sep(self).pack(fill="x", padx=0, pady=2)

        # ── Two-column body ──
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=4)

        left  = tk.Frame(body, bg=BG, width=240)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_status(left)
        self._build_actions(right)

        # ── End turn button ──
        sep(self).pack(fill="x", padx=0, pady=2)
        btn(self, "End My Turn", self._end_turn, color=BG, width=22).pack(pady=6)

    def _build_status(self, parent):
        p = self.player
        g = self.game

        # Money card
        mc = card(parent, title="Your Wallet")
        mc.pack(fill="x", pady=3)
        self.money_lbl = lbl(mc, f"${p.money}", font=("MS Sans Serif", 20, "bold"), fg=W95_BLUE, bg=BG_CARD)
        self.money_lbl.pack()
        self.salary_lbl = lbl(mc, f"Salary: ${p.salary}/turn  ({p.mult_label})", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD)
        self.salary_lbl.pack()
        lbl(mc, f"Sector: {p.sector}", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        # People's pot card
        pc = card(parent, title="People's Pot")
        pc.pack(fill="x", pady=3)
        self.pot_lbl = lbl(pc, f"${g.people_pot}", font=("MS Sans Serif", 16, "bold"), fg=GREEN, bg=BG_CARD)
        self.pot_lbl.pack()
        cost = war_cost(g.turn, len(g.players))
        lbl(pc, f"War fund needed: ${cost}", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        # All players summary
        sc = card(parent, title="All Delegates")
        sc.pack(fill="x", pady=3)
        for q in g.players:
            row = tk.Frame(sc, bg=BG_CARD)
            row.pack(fill="x")
            gs = " [GS]" if q.is_gs else "      "
            nc = W95_BLUE if q is p else TEXT
            lbl(row, f"{q.name}{gs}", font=F_SMALL, fg=nc, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"${q.money}  {q.mult_label}", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, anchor="e").pack(side="right")

        # War tracker
        wc = card(parent, title="War Track")
        wc.pack(fill="x", pady=3)
        dc = RED if g.drow_victories > 0 else TEXT_DIM
        lbl(wc, f"Drow: {g.drow_victories}/{MAX_DROW}", font=F_SMALL, fg=dc, bg=BG_CARD).pack()
        filled = g.turn - 1
        track  = "[" + "#" * filled + "." * (MAX_TURNS - filled) + "]"
        lbl(wc, track, font=F_MONO, fg=TEXT_DIM, bg=BG_CARD).pack()

    def _build_actions(self, parent):
        style = ttk.Style()
        try:
            style.theme_use("winnative")
        except Exception:
            style.theme_use("default")
        style.configure("TNotebook",     background=BG,      borderwidth=2)
        style.configure("TNotebook.Tab", background=BG_MED,  foreground=TEXT,
                        padding=[10, 4], font=F_BTN)
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", W95_BLUE)])

        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        tab_people  = tk.Frame(nb, bg=BG_CARD, padx=12, pady=10, relief="sunken", bd=2)
        tab_special = tk.Frame(nb, bg=BG_CARD, padx=12, pady=10, relief="sunken", bd=2)
        tab_tax     = tk.Frame(nb, bg=BG_CARD, padx=12, pady=10, relief="sunken", bd=2)

        nb.add(tab_people,  text="People's Pot")
        nb.add(tab_special, text="Special Interests")
        nb.add(tab_tax,     text="Tax")

        self._tab_people(tab_people)
        self._tab_special(tab_special)
        self._tab_tax(tab_tax)

    # ── Tab: People's Pot ─────────────────────────────────────────────────────

    def _tab_people(self, parent):
        lbl(parent, "Invest in the People's Pot", font=F_SUB, fg=W95_BLUE, bg=BG_CARD).pack(pady=(4, 4))
        lbl(parent,
            "Your contribution goes into the shared pot.\n"
            "After all players act, the pot is multiplied by the Fruits of Labor card\n"
            "and split equally among ALL players — even those who contributed nothing.",
            fg=TEXT_DIM, bg=BG_CARD).pack(pady=(0, 8))

        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(pady=4)
        lbl(row, "Amount to invest: $", bg=BG_CARD).pack(side="left")
        self.invest_var = tk.StringVar(value="0")
        tk.Entry(row, textvariable=self.invest_var, font=F_BODY,
                 bg=W95_WHITE, fg=TEXT, insertbackground=TEXT,
                 relief="sunken", bd=2, width=8).pack(side="left", padx=4)

        btn(parent, "Invest in People's Pot", self._invest_people,
            color=BG, fg=GREEN, width=26).pack(pady=6)

        lbl(parent,
            "Tip: You can invest $0 and free-ride on others' contributions.\n"
            "But if nobody invests, the war fund may not be met!",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack(pady=(8, 0))

    def _invest_people(self):
        try:
            amount = int(self.invest_var.get())
        except ValueError:
            messagebox.showwarning("Invalid", "Enter a whole number.", parent=self)
            return
        if amount < 0:
            messagebox.showwarning("Invalid", "Amount cannot be negative.", parent=self)
            return
        if amount == 0:
            messagebox.showinfo("Nothing invested",
                                "You chose not to invest in the People this turn.", parent=self)
            return
        if amount > self.player.money:
            messagebox.showwarning("Insufficient Funds",
                                   f"You only have ${self.player.money}.", parent=self)
            return
        self.player.money    -= amount
        self.game.people_pot += amount
        self.invest_var.set("0")
        self._refresh()
        messagebox.showinfo("Invested!",
                            f"You invested ${amount}.\nPeople's pot is now ${self.game.people_pot}.",
                            parent=self)

    # ── Tab: Special Interests ────────────────────────────────────────────────

    def _tab_special(self, parent):
        p = self.player

        # ── Improve ──
        imp_c = card(parent, title=f"Labor Improvement  (${IMPROVEMENT_COST})")
        imp_c.pack(fill="x", pady=4)
        next_mult = f"{p.improvement + 2}x" if p.improvement < MAX_IMPROVEMENT else "MAX"
        lbl(imp_c, f"Upgrade salary multiplier: {p.mult_label} -> {next_mult}\n"
                   f"Improved salary will be ${BASE_SALARY * (p.improvement + 2)}/turn.",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, justify="left", anchor="w").pack(anchor="w", pady=2)
        imp_fg = TEXT if p.can_improve() else TEXT_DIM
        btn(imp_c, f"Improve Tools (${IMPROVEMENT_COST})",
            self._improve, color=BG, fg=imp_fg, width=28).pack(pady=3)
        if p.improvement >= MAX_IMPROVEMENT:
            lbl(imp_c, "Already at maximum improvement.", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        sep(parent, BG_MED).pack(fill="x", pady=6)

        # ── Powder Charge ──
        pw_c = card(parent, title=f"Powder Charge  (${POWDER_COST})")
        pw_c.pack(fill="x", pady=4)
        lbl(pw_c, "Blow a hole in the undermountain walls.\nThe Drow gain ONE victory on the war track.",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, justify="left", anchor="w").pack(anchor="w", pady=2)
        pw_fg = RED if p.can_buy_powder() else TEXT_DIM
        btn(pw_c, f"Buy Powder Charge (${POWDER_COST})",
            self._powder, color=BG, fg=pw_fg, width=28).pack(pady=3)

        sep(parent, BG_MED).pack(fill="x", pady=6)

        # ── Azrok's Dagger ──
        dg_c = card(parent, title=f"Azrok's Dagger  (${DAGGER_COST})")
        dg_c.pack(fill="x", pady=4)
        lbl(dg_c, "Bribe the Duergars to return Azrok's Dagger.\n"
                  "Azrok regains his sight and guides the Republic to IMMEDIATE VICTORY!",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, justify="left", anchor="w").pack(anchor="w", pady=2)
        dg_fg = GREEN if p.can_buy_dagger() else TEXT_DIM
        btn(dg_c, f"Buy Azrok's Dagger (${DAGGER_COST})",
            self._dagger, color=BG, fg=dg_fg, width=28).pack(pady=3)

    def _improve(self):
        p = self.player
        if not p.can_improve():
            msg = ("Already at max improvement." if p.improvement >= MAX_IMPROVEMENT
                   else f"Need ${IMPROVEMENT_COST}, you have ${p.money}.")
            messagebox.showwarning("Cannot Improve", msg, parent=self)
            return
        if not messagebox.askyesno(
            "Confirm Improvement",
            f"Spend ${IMPROVEMENT_COST} to improve tools?\n"
            f"Salary multiplier: {p.mult_label} → {p.improvement + 2}×", parent=self,
        ):
            return
        p.money       -= IMPROVEMENT_COST
        p.improvement += 1
        self._refresh()
        messagebox.showinfo("Improved!", f"New salary multiplier: {p.mult_label}\n"
                                         f"Next salary: ${p.salary}/turn", parent=self)

    def _powder(self):
        p = self.player
        if not p.can_buy_powder():
            messagebox.showwarning("Insufficient Funds",
                                   f"Powder Charge costs ${POWDER_COST}.", parent=self)
            return
        if not messagebox.askyesno(
            "⚠️  Confirm Powder Charge",
            f"Spend ${POWDER_COST} to blow a hole in the walls?\n"
            "The DROW gain a victory point!", parent=self,
        ):
            return
        p.money              -= POWDER_COST
        self.game.drow_victories += 1
        self._refresh()
        if self.game.drow_victories >= MAX_DROW:
            self.game.game_over    = True
            self.game.republic_won = False
            messagebox.showinfo("💥 The Drow Invade!",
                                "Three Drow victories — the Republic falls!\n"
                                "Agents of the Drow WIN!", parent=self)
            self.master.show_game_over()
        else:
            messagebox.showwarning("BOOM!",
                                   f"The walls are breached!\n"
                                   f"Drow victories: {self.game.drow_victories}/{MAX_DROW}", parent=self)

    def _dagger(self):
        p = self.player
        if not p.can_buy_dagger():
            messagebox.showwarning("Insufficient Funds",
                                   f"Azrok's Dagger costs ${DAGGER_COST}.", parent=self)
            return
        if not messagebox.askyesno(
            "🗡️  Azrok's Dagger",
            f"Spend ${DAGGER_COST} to bribe the Duergars?\n"
            "Azrok regains his sight — the Republic wins IMMEDIATELY!", parent=self,
        ):
            return
        p.money            -= DAGGER_COST
        self.game.game_over    = True
        self.game.republic_won = True
        self.master.show_game_over()

    # ── Tab: Tax ──────────────────────────────────────────────────────────────

    def _tab_tax(self, parent):
        p = self.player

        lbl(parent, f"Tax  (${TAX_COST})", font=F_SUB, fg=W95_BLUE, bg=BG_CARD).pack(pady=(4, 4))
        lbl(parent,
            f"Spend ${TAX_COST} to immediately remove ${TAX_AMOUNT} from another player.\n"
            "The taxed money is DISCARDED — not given to you.\n"
            "Can only be done ONCE per turn.",
            fg=TEXT_DIM, bg=BG_CARD).pack(pady=(0, 8))

        if p.used_tax:
            lbl(parent, "[Tax already used this turn.]", fg=TEXT_DIM, bg=BG_CARD).pack(pady=8)
            return

        targets = [q.name for q in self.game.players if q is not p]
        if not targets:
            lbl(parent, "No other players to tax.", fg=TEXT_DIM, bg=BG_CARD).pack()
            return

        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(pady=6)
        lbl(row, "Tax target:", bg=BG_CARD).pack(side="left", padx=(0, 6))
        self.tax_var = tk.StringVar(value=targets[0])

        menu = tk.OptionMenu(row, self.tax_var, *targets)
        menu.config(font=F_BODY, bg=BG, fg=TEXT, activebackground=W95_BLUE,
                    activeforeground=W95_WHITE, relief="raised", bd=2, padx=4)
        menu["menu"].config(font=F_BODY, bg=W95_WHITE, fg=TEXT,
                            activebackground=W95_BLUE, activeforeground=W95_WHITE)
        menu.pack(side="left")

        tax_fg = RED if p.can_tax() else TEXT_DIM
        btn(parent, f"Apply Tax (${TAX_COST})", self._tax,
            color=BG, fg=tax_fg, width=26).pack(pady=6)

        if p.money < TAX_COST:
            lbl(parent, f"Not enough money (need ${TAX_COST}).",
                font=F_SMALL, fg=RED, bg=BG_CARD).pack()

    def _tax(self):
        p = self.player
        if p.used_tax:
            messagebox.showwarning("Already Taxed", "You've already taxed someone this turn.", parent=self)
            return
        if p.money < TAX_COST:
            messagebox.showwarning("Insufficient Funds", f"Taxing costs ${TAX_COST}.", parent=self)
            return
        target_name = self.tax_var.get()
        target      = next((q for q in self.game.players if q.name == target_name), None)
        if not target:
            return
        if not messagebox.askyesno(
            "Confirm Tax",
            f"Spend ${TAX_COST} to remove ${TAX_AMOUNT} from {target.name}?\n"
            "(Taxed money is discarded.)", parent=self,
        ):
            return
        p.money     -= TAX_COST
        removed      = min(target.money, TAX_AMOUNT)
        target.money -= removed
        p.used_tax   = True
        self._refresh()
        messagebox.showinfo("Tax Applied",
                            f"{target.name} lost ${removed}. Money discarded.", parent=self)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh(self):
        p = self.player
        g = self.game
        self.money_lbl.config(text=f"${p.money}")
        self.salary_lbl.config(text=f"Salary: ${p.salary}/turn  ({p.mult_label})")
        self.pot_lbl.config(text=f"${g.people_pot}")

    def _end_turn(self):
        self.game.advance()
        self.master.show_player_turn()


# ─────────────────────────────────────────────────────────────────────────────

class EndOfTurnScreen(tk.Frame):
    TAG_COLORS = {"ok": GREEN_LT, "bad": RED, "gold": GOLD, "dim": TEXT_DIM, "normal": TEXT}

    def __init__(self, master: App, lines: list, **_):
        super().__init__(master, bg=BG)
        self.master = master
        self._build(lines)

    def _build(self, lines):
        g = self.master.game
        titlebar(self, "Azrok's Republic - End of Turn").pack(fill="x")
        lbl(self, "End of Turn Resolution", font=F_HEAD, fg=W95_BLUE).pack(pady=(18, 4))
        sep(self).pack(fill="x", padx=40, pady=6)

        report = card(self, title="Results")
        report.pack(fill="x", padx=40, pady=4)
        for text, tag in lines:
            fg = self.TAG_COLORS.get(tag, TEXT)
            lbl(report, text, fg=fg, bg=BG_CARD, anchor="w", justify="left").pack(fill="x", pady=1)

        sep(self).pack(fill="x", padx=40, pady=10)

        if g.game_over:
            lbl(self, "The game has ended!", font=F_SUB, fg=TEXT).pack(pady=4)
            btn(self, "See Final Results", self.master.show_game_over, color=BG, fg=W95_BLUE, width=24).pack(pady=6)
        else:
            btn(self, "Begin Next Turn", self.master.next_turn, color=BG, fg=GREEN, width=24).pack(pady=6)


# ─────────────────────────────────────────────────────────────────────────────

class GameOverScreen(tk.Frame):
    def __init__(self, master: App, **_):
        super().__init__(master, bg=BG)
        self.master = master
        self._build()

    def _build(self):
        g = self.master.game

        titlebar(self, "Azrok's Republic - Game Over").pack(fill="x")
        lbl(self, "GAME OVER", font=F_TITLE, fg=W95_BLUE).pack(pady=(22, 4))
        sep(self).pack(fill="x", padx=40, pady=6)

        if g.republic_won:
            result_text = "THE REPUBLIC HAS SURVIVED!"
            sub_text    = "Brothers of the Republic WIN!"
            result_fg   = GREEN
        else:
            result_text = "THE DROW HAVE OVERCOME THE REPUBLIC!"
            sub_text    = "Agents of the Drow WIN!"
            result_fg   = RED

        lbl(self, result_text, font=F_HEAD, fg=result_fg).pack(pady=4)
        lbl(self, sub_text,    font=F_SUB,  fg=result_fg).pack()

        sep(self).pack(fill="x", padx=40, pady=10)

        # Role reveal
        lbl(self, "Secret Role Reveal", font=F_SUB, fg=TEXT).pack(pady=(0, 4))
        rc = card(self, title="Roles")
        rc.pack(padx=40, pady=3, fill="x")
        for p in g.players:
            row = tk.Frame(rc, bg=BG_CARD, pady=2)
            row.pack(fill="x")
            gs_mk      = "  [GS]" if p.is_gs else ""
            role_fg    = DROW_CLR if "Drow" in p.role else GREEN
            is_winner  = ((g.republic_won and "Brother" in p.role)
                          or (not g.republic_won and "Drow" in p.role))
            win_mk     = "  [WINNER]" if is_winner else ""
            lbl(row, f"{p.name}{gs_mk}  ({p.sector})", fg=TEXT, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"{p.role}{win_mk}", fg=role_fg, bg=BG_CARD, anchor="e").pack(side="right")

        sep(self).pack(fill="x", padx=40, pady=8)

        # Final wealth
        lbl(self, "Final Wealth (richest first)", font=F_SUB, fg=TEXT).pack(pady=(0, 4))
        wc = card(self, title="Wealth")
        wc.pack(padx=40, pady=3, fill="x")
        for p in sorted(g.players, key=lambda q: q.money, reverse=True):
            row = tk.Frame(wc, bg=BG_CARD, pady=1)
            row.pack(fill="x")
            lbl(row, p.name,        fg=TEXT, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"${p.money}", fg=W95_BLUE, bg=BG_CARD, anchor="e").pack(side="right")

        sep(self).pack(fill="x", padx=40, pady=10)
        btn(self, "Play Again", self.master._goto,
            color=BG, fg=W95_BLUE, width=20).pack(pady=4)

        # Wire play-again correctly
        for w in self.winfo_children():
            if isinstance(w, tk.Button) and "Play Again" in w.cget("text"):
                w.config(command=lambda: self.master._goto(SetupScreen))


# ─────────────────────────────────────────────────────────────────────────────

class AITurnScreen(tk.Frame):
    """Displays what an AI player decided to do, then lets humans continue."""

    TAG_COLORS = {"ok": GREEN_LT, "bad": RED, "gold": GOLD, "dim": TEXT_DIM, "normal": TEXT}

    def __init__(self, master: App, player: AIPlayer, log: list, game_ended: bool, **_):
        super().__init__(master, bg=BG)
        self.master = master
        self._build(player, log, game_ended)

    def _build(self, player, log, game_ended):
        g = self.master.game
        titlebar(self, f"Azrok's Republic - {player.name}'s Turn [AI]").pack(fill="x")

        top = tk.Frame(self, bg=BG, padx=10, pady=4)
        top.pack(fill="x")
        gs_mk = "  [GS]" if player.is_gs else ""
        lbl(top, f"{player.name}{gs_mk}  \u2014  {player.ai_type}",
            font=F_HEAD, fg=W95_BLUE, bg=BG).pack(side="left")
        lbl(top, f"Turn {g.turn}/{MAX_TURNS}", fg=TEXT_DIM, bg=BG).pack(side="right")

        sep(self).pack(fill="x", pady=2)

        # Status strip: wallet + pot
        info = tk.Frame(self, bg=BG, padx=10, pady=2)
        info.pack(fill="x")
        lbl(info, f"Wallet: ${player.money}", font=F_SMALL, fg=TEXT_DIM, bg=BG).pack(side="left", padx=(0, 16))
        lbl(info, f"People's Pot: ${g.people_pot}", font=F_SMALL, fg=TEXT_DIM, bg=BG).pack(side="left")

        # Action log
        log_frame = card(self, title="AI Actions This Turn")
        log_frame.pack(fill="x", padx=20, pady=8)
        for text, tag in log:
            fg = self.TAG_COLORS.get(tag, TEXT)
            lbl(log_frame, text, fg=fg, bg=BG_CARD, anchor="w", justify="left").pack(fill="x", pady=1)

        sep(self).pack(fill="x", pady=6)

        if game_ended:
            lbl(self, "The game has ended!", font=F_SUB, fg=TEXT).pack(pady=4)
            btn(self, "See Final Results", self.master.show_game_over,
                color=BG, fg=W95_BLUE, width=24).pack(pady=6)
        else:
            btn(self, "Continue", self._continue, color=BG, fg=GREEN, width=20).pack(pady=8)

    def _continue(self):
        self.master.game.advance()
        self.master.show_player_turn()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
