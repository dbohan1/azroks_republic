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


# ══════════════════════════════════════════════════════════════════════════════
#  THEME
# ══════════════════════════════════════════════════════════════════════════════

BG       = "#1a1a1a"
BG_MED   = "#2a2a2a"
BG_CARD  = "#323232"
RED      = "#c0392b"
RED_DK   = "#922b21"
GOLD     = "#e5a817"
GREEN    = "#1e8449"
GREEN_LT = "#27ae60"
DROW_CLR = "#7d3c98"
TEXT     = "#e8e8e8"
TEXT_DIM = "#888888"

F_TITLE   = ("Georgia",    26, "bold")
F_HEAD    = ("Georgia",    16, "bold")
F_SUB     = ("Georgia",    13, "bold")
F_BODY    = ("Arial",      12)
F_SMALL   = ("Arial",      10)
F_MONO    = ("Courier New",11)
F_BTN     = ("Arial",      12, "bold")


def lbl(parent, text, font=F_BODY, fg=TEXT, bg=BG, anchor="center", justify="center", **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg,
                    anchor=anchor, justify=justify, **kw)

def sep(parent, bg=BG_CARD, height=1):
    return tk.Frame(parent, bg=bg, height=height)

def btn(parent, text, cmd, color=RED, fg=TEXT, width=22, state="normal"):
    return tk.Button(
        parent, text=text, command=cmd, font=F_BTN,
        bg=color, fg=fg, activebackground=GOLD, activeforeground=BG,
        relief="flat", padx=10, pady=7, width=width,
        cursor="hand2", state=state,
    )

def card(parent, **kw):
    return tk.Frame(parent, bg=BG_CARD, padx=12, pady=10, **kw)


# ══════════════════════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════════════════════

class Player:
    def __init__(self, name: str, sector: str = ""):
        self.name        = name
        self.sector      = sector
        self.role        = ""
        self.is_gs       = False
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
        self.geometry("960x720")
        self.minsize(800, 600)
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
        self._goto(RoleRevealScreen, player_idx=0)

    def next_role_reveal(self, idx: int):
        if idx >= len(self.game.players):
            self._goto(TurnStartScreen)
        else:
            self._goto(RoleRevealScreen, player_idx=idx)

    def show_player_turn(self):
        if self.game.current_player is None:
            lines = self.game.resolve_end_of_turn()
            self._goto(EndOfTurnScreen, lines=lines)
        else:
            p = self.game.current_player
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
        self.master = master
        self.name_vars = []
        self._build()

    def _build(self):
        lbl(self, "☭  AZROK'S REPUBLIC  ☭", font=F_TITLE, fg=GOLD).pack(pady=(40, 4))
        lbl(self, "Rules Version 1.4.2", font=F_SMALL, fg=TEXT_DIM).pack()
        sep(self).pack(fill="x", padx=50, pady=18)

        lbl(self, "Game Setup", font=F_HEAD, fg=GOLD).pack(pady=(0, 12))

        # Player count row
        row = tk.Frame(self, bg=BG)
        row.pack()
        lbl(row, "Number of Players:", bg=BG).pack(side="left", padx=(0, 10))
        self.count_var = tk.IntVar(value=4)
        for n in range(2, 9):
            tk.Radiobutton(
                row, text=str(n), variable=self.count_var, value=n,
                font=F_BODY, bg=BG, fg=TEXT, selectcolor=BG_MED,
                activebackground=BG, activeforeground=GOLD,
                command=self._rebuild_names,
            ).pack(side="left", padx=4)

        sep(self).pack(fill="x", padx=50, pady=14)

        self.names_frame = tk.Frame(self, bg=BG)
        self.names_frame.pack()
        self._rebuild_names()

        sep(self).pack(fill="x", padx=50, pady=14)
        btn(self, "⚑   BEGIN THE REPUBLIC", self._start, width=32).pack(pady=6)

    def _rebuild_names(self):
        for w in self.names_frame.winfo_children():
            w.destroy()
        self.name_vars.clear()
        n = self.count_var.get()
        lbl(self.names_frame, "Enter Player Names", font=F_SUB, fg=TEXT).pack(pady=(0, 8))
        for i in range(n):
            row = tk.Frame(self.names_frame, bg=BG)
            row.pack(pady=2)
            lbl(row, f"Player {i+1}:", fg=TEXT_DIM, bg=BG, anchor="e").pack(side="left", padx=(0, 8))
            var = tk.StringVar(value=f"Player {i+1}")
            self.name_vars.append(var)
            tk.Entry(row, textvariable=var, font=F_BODY, bg=BG_MED, fg=TEXT,
                     insertbackground=TEXT, relief="flat", width=22).pack(side="left")

    def _start(self):
        n     = self.count_var.get()
        names = [v.get().strip() for v in self.name_vars[:n]]
        if any(not nm for nm in names):
            messagebox.showwarning("Missing Names", "Please enter a name for every player.", parent=self)
            return
        if len(set(names)) != len(names):
            messagebox.showwarning("Duplicate Names", "All player names must be unique.", parent=self)
            return
        self.master.start_game([Player(nm) for nm in names])


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

        lbl(self, "☭  AZROK'S REPUBLIC  ☭", font=F_TITLE, fg=GOLD).pack(pady=(35, 4))
        sep(self).pack(fill="x", padx=50, pady=12)

        lbl(self, f"Player {self.player_idx + 1} of {total}", font=F_SMALL, fg=TEXT_DIM).pack()
        lbl(self, "Pass the device to:", font=F_BODY, fg=TEXT_DIM).pack(pady=(10, 2))
        lbl(self, p.name, font=F_HEAD, fg=GOLD).pack()
        lbl(self, f"Sector: {p.sector}", font=F_SMALL, fg=TEXT_DIM).pack(pady=3)
        if p.is_gs:
            lbl(self, "★  You are the GENERAL SECRETARY  ★", font=F_SUB, fg=GOLD).pack(pady=4)

        sep(self).pack(fill="x", padx=50, pady=12)

        self.hint = lbl(self, "Your secret role is hidden.\nPress the button to reveal it privately.", fg=TEXT_DIM)
        self.hint.pack(pady=6)

        # Role card (hidden until revealed)
        self.role_card = card(self)
        role_color = DROW_CLR if "Drow" in p.role else GREEN_LT
        lbl(self.role_card, "YOUR SECRET ROLE", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()
        lbl(self.role_card, p.role, font=("Georgia", 18, "bold"), fg=role_color, bg=BG_CARD).pack(pady=6)
        if "Drow" in p.role:
            lbl(self.role_card, "Help the Drow overcome the Republic!\nLet the war fund fail 3 times.",
                font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()
        else:
            lbl(self.role_card, "Defend the Republic!\nKeep the war fund supplied for all turns.",
                font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        self.reveal_btn = btn(self, "👁   Reveal My Role", self._reveal, color=BG_MED, width=26)
        self.reveal_btn.pack(pady=12)

        self.next_btn = btn(self, "✔   Hide & Pass Device", self._next, color=GREEN, width=26)

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
        lbl(self, "☭  AZROK'S REPUBLIC  ☭", font=F_TITLE, fg=GOLD).pack(pady=(28, 4))
        sep(self).pack(fill="x", padx=50, pady=10)

        lbl(self, f"Turn {g.turn}  of  {MAX_TURNS}", font=F_HEAD, fg=GOLD).pack(pady=4)

        # War status banner
        c = card(self)
        c.pack(padx=50, pady=4, fill="x")
        cost = war_cost(g.turn, len(g.players))
        lbl(c, f"War Fund Required This Turn: ${cost}", fg=TEXT, bg=BG_CARD).pack()
        dc = RED if g.drow_victories > 0 else TEXT_DIM
        lbl(c, f"Drow Victories: {g.drow_victories} / {MAX_DROW}", fg=dc, bg=BG_CARD).pack()
        # War track visual
        filled = g.turn - 1
        track  = "█" * filled + "░" * (MAX_TURNS - filled)
        lbl(c, f"[{track}]", font=F_MONO, fg=TEXT_DIM, bg=BG_CARD).pack(pady=2)

        sep(self).pack(fill="x", padx=50, pady=10)

        # Salary phase
        lbl(self, "💰  Salary Distribution", font=F_SUB, fg=TEXT).pack(pady=(0, 6))
        sal_card = card(self)
        sal_card.pack(padx=50, pady=2, fill="x")

        g.deal_salaries()
        for p in g.players:
            row = tk.Frame(sal_card, bg=BG_CARD)
            row.pack(fill="x", pady=1)
            gs_mk = " ★" if p.is_gs else ""
            lbl(row, f"{p.name}{gs_mk}  ({p.sector})", fg=TEXT, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"+${p.salary}  (salary {p.mult_label})", fg=GOLD, bg=BG_CARD, anchor="e").pack(side="right")

        sep(self).pack(fill="x", padx=50, pady=10)

        # GS dice roll
        gs = g.gs
        lbl(self, f"🎲  {gs.name} (General Secretary) rolls for first player", font=F_SUB, fg=TEXT).pack(pady=(0, 4))
        self.dice_lbl = lbl(self, "Press the button below to roll.", fg=TEXT_DIM)
        self.dice_lbl.pack(pady=4)

        self.roll_btn = btn(self, "🎲   Roll the Dice", self._roll, color=RED, width=22)
        self.roll_btn.pack(pady=8)

        self.go_btn = btn(self, "▶   Begin Player Turns", self.master.show_player_turn, color=GREEN, width=24)

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
        lbl(self, "☭  AZROK'S REPUBLIC  ☭", font=F_TITLE, fg=GOLD).pack(pady=(80, 8))
        sep(self).pack(fill="x", padx=50, pady=12)
        lbl(self, "Pass the device to:", fg=TEXT_DIM).pack(pady=(20, 4))
        lbl(self, player.name, font=F_HEAD, fg=GOLD).pack()
        lbl(self, f"{player.sector} Delegate", fg=TEXT_DIM).pack(pady=3)
        if player.is_gs:
            lbl(self, "★  General Secretary  ★", fg=GOLD).pack()
        sep(self).pack(fill="x", padx=50, pady=20)
        btn(self, f"▶   I'm {player.name} — Continue", on_continue, color=RED, width=34).pack(pady=16)


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

        # ── Top bar ──
        top = tk.Frame(self, bg=BG_MED, padx=14, pady=8)
        top.pack(fill="x")
        lbl(top, f"⚑  {p.name}'s Turn", font=F_HEAD, fg=GOLD, bg=BG_MED).pack(side="left")
        gs_mk = "  ★ GS" if p.is_gs else ""
        lbl(top, f"Turn {g.turn}/{MAX_TURNS}{gs_mk}", fg=TEXT_DIM, bg=BG_MED).pack(side="right")

        # ── Two-column body ──
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=6)

        left  = tk.Frame(body, bg=BG, width=280)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_status(left)
        self._build_actions(right)

        # ── End turn button ──
        sep(self).pack(fill="x", padx=10, pady=4)
        btn(self, "✔   End My Turn", self._end_turn, color=BG_MED, width=26).pack(pady=8)

    def _build_status(self, parent):
        p = self.player
        g = self.game

        # Money card
        mc = card(parent)
        mc.pack(fill="x", pady=4)
        lbl(mc, "YOUR WALLET", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()
        self.money_lbl = lbl(mc, f"${p.money}", font=("Georgia", 28, "bold"), fg=GOLD, bg=BG_CARD)
        self.money_lbl.pack()
        self.salary_lbl = lbl(mc, f"Salary: ${p.salary}/turn  ({p.mult_label})", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD)
        self.salary_lbl.pack()
        lbl(mc, f"Sector: {p.sector}", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        # People's pot card
        pc = card(parent)
        pc.pack(fill="x", pady=4)
        lbl(pc, "PEOPLE'S POT", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()
        self.pot_lbl = lbl(pc, f"${g.people_pot}", font=("Georgia", 22, "bold"), fg=GREEN_LT, bg=BG_CARD)
        self.pot_lbl.pack()
        cost = war_cost(g.turn, len(g.players))
        lbl(pc, f"War fund needed: ${cost}", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        # All players summary
        sc = card(parent)
        sc.pack(fill="x", pady=4)
        lbl(sc, "ALL DELEGATES", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()
        sep(sc, BG_MED).pack(fill="x", pady=3)
        for q in g.players:
            row = tk.Frame(sc, bg=BG_CARD)
            row.pack(fill="x")
            gs = " ★" if q.is_gs else "   "
            nc = GOLD if q is p else TEXT
            lbl(row, f"{gs}{q.name}", font=F_SMALL, fg=nc, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"${q.money}  {q.mult_label}", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, anchor="e").pack(side="right")

        # War tracker
        wc = card(parent)
        wc.pack(fill="x", pady=4)
        dc = RED if g.drow_victories > 0 else TEXT_DIM
        lbl(wc, f"⚔️  Drow: {g.drow_victories}/{MAX_DROW}", font=F_SMALL, fg=dc, bg=BG_CARD).pack()
        filled = g.turn - 1
        track  = "█" * filled + "░" * (MAX_TURNS - filled)
        lbl(wc, f"[{track}]", font=F_MONO, fg=TEXT_DIM, bg=BG_CARD).pack()

    def _build_actions(self, parent):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook",       background=BG,     borderwidth=0)
        style.configure("TNotebook.Tab",   background=BG_MED, foreground=TEXT,
                        padding=[12, 6],   font=F_BTN)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_CARD)],
                  foreground=[("selected", GOLD)])

        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        tab_people  = tk.Frame(nb, bg=BG_CARD, padx=16, pady=12)
        tab_special = tk.Frame(nb, bg=BG_CARD, padx=16, pady=12)
        tab_tax     = tk.Frame(nb, bg=BG_CARD, padx=16, pady=12)

        nb.add(tab_people,  text="📥  People's Pot")
        nb.add(tab_special, text="🔧  Special Interests")
        nb.add(tab_tax,     text="💸  Tax")

        self._tab_people(tab_people)
        self._tab_special(tab_special)
        self._tab_tax(tab_tax)

    # ── Tab: People's Pot ─────────────────────────────────────────────────────

    def _tab_people(self, parent):
        lbl(parent, "Invest in the People's Pot", font=F_SUB, fg=GOLD, bg=BG_CARD).pack(pady=(4, 4))
        lbl(parent,
            "Your contribution goes into the shared pot.\n"
            "After all players act, the pot is multiplied by the Fruits of Labor card\n"
            "and split equally among ALL players — even those who contributed nothing.",
            fg=TEXT_DIM, bg=BG_CARD).pack(pady=(0, 10))

        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(pady=6)
        lbl(row, "Amount to invest: $", bg=BG_CARD).pack(side="left")
        self.invest_var = tk.StringVar(value="0")
        tk.Entry(row, textvariable=self.invest_var, font=F_BODY,
                 bg=BG_MED, fg=TEXT, insertbackground=TEXT,
                 relief="flat", width=8).pack(side="left", padx=6)

        btn(parent, "📥   Invest in People", self._invest_people,
            color=GREEN, width=28).pack(pady=8)

        lbl(parent,
            "💡  Tip: You can invest $0 and free-ride on others' contributions.\n"
            "But if nobody invests, the war fund may not be met!",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack(pady=(10, 0))

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
        imp_c = card(parent)
        imp_c.pack(fill="x", pady=6)
        lbl(imp_c, f"🔧  Labor Improvement  (${IMPROVEMENT_COST})", font=F_SUB, fg=GOLD, bg=BG_CARD).pack(anchor="w")
        next_mult = f"{p.improvement + 2}×" if p.improvement < MAX_IMPROVEMENT else "MAX"
        lbl(imp_c, f"Upgrade salary multiplier: {p.mult_label} → {next_mult}\n"
                   f"Improved salary will be ${BASE_SALARY * (p.improvement + 2)}/turn.",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, justify="left", anchor="w").pack(anchor="w", pady=3)
        imp_color = GOLD if p.can_improve() else BG_MED
        btn(imp_c, f"🔧   Improve Tools (${IMPROVEMENT_COST})",
            self._improve, color=imp_color, width=30).pack(pady=4)
        if p.improvement >= MAX_IMPROVEMENT:
            lbl(imp_c, "Already at maximum improvement.", font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

        sep(parent, BG_MED).pack(fill="x", pady=8)

        # ── Powder Charge ──
        pw_c = card(parent)
        pw_c.pack(fill="x", pady=6)
        lbl(pw_c, f"💣  Powder Charge  (${POWDER_COST})", font=F_SUB, fg=DROW_CLR, bg=BG_CARD).pack(anchor="w")
        lbl(pw_c, "Blow a hole in the undermountain walls.\nThe Drow gain ONE victory on the war track.",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, justify="left", anchor="w").pack(anchor="w", pady=3)
        pw_color = DROW_CLR if p.can_buy_powder() else BG_MED
        btn(pw_c, f"💣   Buy Powder Charge (${POWDER_COST})",
            self._powder, color=pw_color, width=30).pack(pady=4)

        sep(parent, BG_MED).pack(fill="x", pady=8)

        # ── Azrok's Dagger ──
        dg_c = card(parent)
        dg_c.pack(fill="x", pady=6)
        lbl(dg_c, f"🗡️  Azrok's Dagger  (${DAGGER_COST})", font=F_SUB, fg=GOLD, bg=BG_CARD).pack(anchor="w")
        lbl(dg_c, "Bribe the Duergars to return Azrok's Dagger.\n"
                  "Azrok regains his sight and guides the Republic to IMMEDIATE VICTORY!",
            font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD, justify="left", anchor="w").pack(anchor="w", pady=3)
        dg_color = GOLD if p.can_buy_dagger() else BG_MED
        btn(dg_c, f"🗡️   Buy Azrok's Dagger (${DAGGER_COST})",
            self._dagger, color=dg_color, fg=BG if p.can_buy_dagger() else TEXT_DIM,
            width=30).pack(pady=4)

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

        lbl(parent, f"💸  Tax  (${TAX_COST})", font=F_SUB, fg=GOLD, bg=BG_CARD).pack(pady=(4, 4))
        lbl(parent,
            f"Spend ${TAX_COST} to immediately remove ${TAX_AMOUNT} from another player.\n"
            "The taxed money is DISCARDED — not given to you.\n"
            "Can only be done ONCE per turn.",
            fg=TEXT_DIM, bg=BG_CARD).pack(pady=(0, 10))

        if p.used_tax:
            lbl(parent, "✔  Tax already used this turn.", fg=TEXT_DIM, bg=BG_CARD).pack(pady=10)
            return

        targets = [q.name for q in self.game.players if q is not p]
        if not targets:
            lbl(parent, "No other players to tax.", fg=TEXT_DIM, bg=BG_CARD).pack()
            return

        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(pady=8)
        lbl(row, "Tax target:", bg=BG_CARD).pack(side="left", padx=(0, 8))
        self.tax_var = tk.StringVar(value=targets[0])

        menu = tk.OptionMenu(row, self.tax_var, *targets)
        menu.config(font=F_BODY, bg=BG_MED, fg=TEXT, activebackground=BG_CARD,
                    activeforeground=GOLD, relief="flat", padx=6)
        menu["menu"].config(font=F_BODY, bg=BG_MED, fg=TEXT)
        menu.pack(side="left")

        tax_color = RED if p.can_tax() else BG_MED
        btn(parent, f"💸   Apply Tax (${TAX_COST})", self._tax,
            color=tax_color, width=28).pack(pady=8)

        if p.money < TAX_COST:
            lbl(parent, f"Not enough money (need ${TAX_COST}).",
                font=F_SMALL, fg=TEXT_DIM, bg=BG_CARD).pack()

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
        lbl(self, "⚖️   End of Turn Resolution", font=F_HEAD, fg=GOLD).pack(pady=(30, 6))
        sep(self).pack(fill="x", padx=50, pady=8)

        report = card(self)
        report.pack(fill="x", padx=50, pady=6)
        for text, tag in lines:
            fg = self.TAG_COLORS.get(tag, TEXT)
            lbl(report, text, fg=fg, bg=BG_CARD, anchor="w", justify="left").pack(fill="x", pady=1)

        sep(self).pack(fill="x", padx=50, pady=12)

        if g.game_over:
            lbl(self, "The game has ended!", font=F_SUB, fg=GOLD).pack(pady=6)
            btn(self, "🏁   See Final Results", self.master.show_game_over, color=RED, width=26).pack(pady=8)
        else:
            btn(self, "▶   Begin Next Turn", self.master.next_turn, color=GREEN, width=26).pack(pady=8)


# ─────────────────────────────────────────────────────────────────────────────

class GameOverScreen(tk.Frame):
    def __init__(self, master: App, **_):
        super().__init__(master, bg=BG)
        self.master = master
        self._build()

    def _build(self):
        g = self.master.game

        lbl(self, "☭  GAME OVER  ☭", font=F_TITLE, fg=GOLD).pack(pady=(35, 6))
        sep(self).pack(fill="x", padx=50, pady=8)

        if g.republic_won:
            result_text = "🏆  THE REPUBLIC HAS SURVIVED!"
            sub_text    = "Brothers of the Republic WIN!"
            result_fg   = GREEN_LT
        else:
            result_text = "💀  THE DROW HAVE OVERCOME THE REPUBLIC!"
            sub_text    = "Agents of the Drow WIN!"
            result_fg   = RED

        lbl(self, result_text, font=F_HEAD, fg=result_fg).pack(pady=6)
        lbl(self, sub_text,    font=F_SUB,  fg=result_fg).pack()

        sep(self).pack(fill="x", padx=50, pady=12)

        # Role reveal
        lbl(self, "Secret Role Reveal", font=F_SUB, fg=GOLD).pack(pady=(0, 6))
        rc = card(self)
        rc.pack(padx=50, pady=4, fill="x")
        for p in g.players:
            row = tk.Frame(rc, bg=BG_CARD, pady=3)
            row.pack(fill="x")
            gs_mk      = "  ★ GS" if p.is_gs else ""
            role_fg    = DROW_CLR if "Drow" in p.role else GREEN_LT
            is_winner  = ((g.republic_won and "Brother" in p.role)
                          or (not g.republic_won and "Drow" in p.role))
            win_mk     = "  🏆" if is_winner else ""
            lbl(row, f"{p.name}{gs_mk}  ({p.sector})", fg=TEXT, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"{p.role}{win_mk}", fg=role_fg, bg=BG_CARD, anchor="e").pack(side="right")

        sep(self).pack(fill="x", padx=50, pady=10)

        # Final wealth
        lbl(self, "Final Wealth (richest first)", font=F_SUB, fg=GOLD).pack(pady=(0, 6))
        wc = card(self)
        wc.pack(padx=50, pady=4, fill="x")
        for p in sorted(g.players, key=lambda q: q.money, reverse=True):
            row = tk.Frame(wc, bg=BG_CARD, pady=2)
            row.pack(fill="x")
            lbl(row, p.name,      fg=TEXT, bg=BG_CARD, anchor="w").pack(side="left")
            lbl(row, f"${p.money}", fg=GOLD, bg=BG_CARD, anchor="e").pack(side="right")

        sep(self).pack(fill="x", padx=50, pady=12)
        btn(self, "🔄   Play Again", self.master._goto,
            color=RED, width=22).pack(pady=6)

        # Wire play-again correctly
        # Rebind to pass SetupScreen
        for w in self.winfo_children():
            if isinstance(w, tk.Button) and "Play Again" in w.cget("text"):
                w.config(command=lambda: self.master._goto(SetupScreen))


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
