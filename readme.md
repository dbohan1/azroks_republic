# ☭ Azrok's Republic — Digital Pass-and-Play Edition

> *Rules Version 1.4.2*

A digital adaptation of the social-deduction board game **Azrok's Republic**, built in Python with Tkinter. Two to eight players share one device, secretly working either to defend the Republic or to help the Drow invaders destroy it.

---

## Requirements

| Requirement | Details |
|---|---|
| Python | 3.x (3.8+ recommended) |
| Tkinter | Bundled with most Python installs |
| OS | Windows, macOS, or Linux |

---

## Running the Game

**Windows (double-click):**
```
play_azroks_republic.bat
```

**Any platform (command line):**
```bash
python azroks_republic.py
```

---

## Setup

1. Choose the number of players (2–8).
2. Enter each player's name.
3. Click **Begin the Republic**.

The game then secretly assigns each player:
- A **sector** (Teachers, Builders, Miners, or Military) — determines flavour only.
- A **secret role** (revealed privately, one player at a time, by passing the device).
- One player is publicly designated as the **General Secretary** (★).

---

## Secret Roles

| Role | Goal | Count |
|---|---|---|
| **Brother of the Republic** | Keep the war fund supplied for all 10 turns. | Majority |
| **Agent of the Drow** | Let the war fund fail 3 times. | ~1 per 3 players (min. 1) |

Roles are revealed on screen privately before the first turn begins.

---

## Turn Structure

The game lasts **up to 10 turns**. Each turn proceeds as follows:

### 1. Salary Distribution
Every player receives their salary at the start of the turn.  
- Base salary: **$2/turn**.  
- Players may upgrade their salary multiplier via **Labor Improvement** (see actions below).  
  - Multipliers: 1× → 2× → 3× → 4× (up to 3 upgrades, costing $7 each).

### 2. Determine Turn Order
The **General Secretary** rolls a die to select the first player. All other players follow in seat order; the GS always acts last.

### 3. Player Actions (pass-and-play)
Each player is handed the device privately and may take actions from three tabs:

#### 📥 People's Pot — Invest in the shared war fund
Contribute any amount of your own money to the **People's Pot**.  
At end of turn the pot is multiplied by a **Fruits of Labor** card and the result is split equally among *all* players — even those who contributed nothing.  
> ⚠️ If no one contributes enough, the war fund requirement may not be met!

#### 🔧 Special Interests — Private power moves

| Action | Cost | Effect |
|---|---|---|
| **Labor Improvement** | $7 | Increase your salary multiplier by 1 (max 4×). |
| **Powder Charge** 💣 | $12 | Blow a hole in the walls — Drow gain **1 victory**. |
| **Azrok's Dagger** 🗡️ | $16 | Bribe the Duergars — Republic wins **immediately**. |

#### 💸 Tax — Sabotage a rival
Spend $1 to remove $2 from any other player.  
The taxed money is **discarded** (not transferred to you). Usable **once per turn**.

### 4. End-of-Turn Resolution (automatic)

1. **War fund check** — the pot must cover the current turn's war cost:
   | Turns | War cost |
   |---|---|
   | 1–3 | $1 × number of players |
   | 4–6 | $2 × number of players |
   | 7–10 | $3 × number of players |
   - ✅ Cost met → pot reduced by the cost.
   - ❌ Cost not met → **Drow gain a victory**, pot is zeroed.

2. **Fruits of Labor card** — a random multiplier (0.50×–2.50×) is drawn and applied to the remaining pot (rounded up).

3. **Payout** — the pot is divided equally among all players (rounded down); any remainder carries over.

4. **War track** advances to the next turn.

---

## Win Conditions

| Winner | Condition |
|---|---|
| 🏆 **Republic** | Survive all 10 turns with fewer than 3 Drow victories, **or** a player buys Azrok's Dagger. |
| 💀 **Drow** | The war fund fails **3 times** (including via Powder Charges). |

At game over, all secret roles are publicly revealed alongside the final wealth ranking.

---

## Strategy Tips

- **Brothers** should invest heavily in the People's Pot, especially in later turns when the war cost scales up.
- **Agents** can free-ride, use the Tax action to drain reliable contributors, or risk blowing their cover with a Powder Charge.
- **Labor Improvement** is a personal investment — great for wealth, but every dollar spent on it is a dollar not going to the war fund.
- **Azrok's Dagger** is an instant win for whoever can afford it — a strong incentive to hoard money.

---

## File Overview

| File | Description |
|---|---|
| `azroks_republic.py` | Full game source (data model, UI, game logic). |
| `play_azroks_republic.bat` | Windows launcher — double-click to start. |
