"""Interactive version of the seven-bottle poison puzzle.

The puzzle is solved internally with breadth-first search. The interface then
lets the player choose the bottle for moving forward and the bottle for coming
back.
"""

from collections import Counter, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple
import tkinter as tk


POISON = "poison"
WINE = "wine"
ADVANCE = "advance"
RETURN = "return"

POTION_ORDER = (POISON, WINE, ADVANCE, RETURN)
TARGET_COUNTS = {
    POISON: 3,
    WINE: 2,
    ADVANCE: 1,
    RETURN: 1,
}


@dataclass(frozen=True)
class Bottle:
    number: int
    name: str
    body_width: int
    height: int
    neck_width: int
    liquid_color: str


BOTTLES: Tuple[Bottle, ...] = (
    Bottle(1, "wide bottle", 64, 128, 26, "#8b3e2f"),
    Bottle(2, "giant bottle", 76, 178, 30, "#325c8a"),
    Bottle(3, "tiny bottle", 42, 88, 18, "#d9a441"),
    Bottle(4, "square bottle", 58, 132, 28, "#476b47"),
    Bottle(5, "tall bottle", 50, 148, 20, "#7a4b8f"),
    Bottle(6, "thin bottle", 46, 136, 16, "#2f7c85"),
    Bottle(7, "round bottle", 70, 126, 24, "#a34f36"),
)

SECOND_FROM_LEFT = 1
SECOND_FROM_RIGHT = 5
SMALLEST_BOTTLE = min(range(len(BOTTLES)), key=lambda index: BOTTLES[index].height)
LARGEST_BOTTLE = max(range(len(BOTTLES)), key=lambda index: BOTTLES[index].height)

BACKGROUND = "#10141f"
PANEL = "#171d2a"
INK = "#f3ead7"
MUTED = "#b7aa91"
GOLD = "#d7a441"
BLUE = "#68a6df"
RED = "#c24f4f"
GREEN = "#5abf80"
GLASS = "#d9edf0"
GLASS_SHADOW = "#b8d3dc"
OUTLINE = "#0a0d14"


def partial_clues_hold(assignment: List[str]) -> bool:
    """Return True when a partial BFS state still can satisfy the riddle."""

    current_index = len(assignment) - 1
    current_potion = assignment[-1]

    # Clue: neither bottle at either end lets the drinker move onward.
    if current_index == 0 and current_potion == ADVANCE:
        return False
    if current_index == len(BOTTLES) - 1:
        if current_potion == ADVANCE:
            return False
        if assignment[0] == current_potion:
            return False

    # Clue: neither the dwarf nor the giant bottle contains poison.
    if current_index in (SMALLEST_BOTTLE, LARGEST_BOTTLE):
        if current_potion == POISON:
            return False

    # Clue: the second from the left and the second from the right are twins.
    # With two nettle wines in the riddle, the twin pair is the wine.
    if current_index in (SECOND_FROM_LEFT, SECOND_FROM_RIGHT):
        if current_potion != WINE:
            return False

    # Clue: every nettle wine has poison somewhere on its left side.
    for index, potion in enumerate(assignment):
        if potion == WINE and POISON not in assignment[:index]:
            return False

    return True


def full_clues_hold(assignment: List[str]) -> bool:
    """Validate a complete bottle assignment against all puzzle clues."""

    if len(assignment) != len(BOTTLES):
        return False

    if Counter(assignment) != TARGET_COUNTS:
        return False

    if assignment[0] == assignment[-1]:
        return False

    if assignment[0] == ADVANCE or assignment[-1] == ADVANCE:
        return False

    if assignment[SMALLEST_BOTTLE] == POISON:
        return False

    if assignment[LARGEST_BOTTLE] == POISON:
        return False

    if assignment[SECOND_FROM_LEFT] != WINE:
        return False

    if assignment[SECOND_FROM_RIGHT] != WINE:
        return False

    for index, potion in enumerate(assignment):
        if potion == WINE and POISON not in assignment[:index]:
            return False

    return True


def solve_with_bfs() -> Tuple[List[str], int]:
    """Find the unique solution to the riddle using breadth-first search."""

    queue: Deque[Tuple[List[str], Dict[str, int]]] = deque()
    queue.append(([], dict(TARGET_COUNTS)))
    solutions: List[List[str]] = []
    explored_states = 0

    while queue:
        assignment, remaining = queue.popleft()
        explored_states += 1

        if len(assignment) == len(BOTTLES):
            if full_clues_hold(assignment):
                solutions.append(assignment)
            continue

        for potion in POTION_ORDER:
            if remaining[potion] == 0:
                continue

            next_assignment = assignment + [potion]
            next_remaining = dict(remaining)
            next_remaining[potion] -= 1

            if partial_clues_hold(next_assignment):
                queue.append((next_assignment, next_remaining))

    if len(solutions) != 1:
        raise RuntimeError(f"Expected 1 solution, found {len(solutions)}.")

    return solutions[0], explored_states


SOLUTION, EXPLORED_STATES = solve_with_bfs()
ADVANCE_BOTTLE = SOLUTION.index(ADVANCE)
RETURN_BOTTLE = SOLUTION.index(RETURN)


class PoisonPuzzleApp:
    """Tkinter interface for the seven-bottle puzzle."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Seven Bottles Poison Puzzle")
        self.root.configure(bg=BACKGROUND)
        self.root.minsize(860, 560)

        self.phase = ADVANCE
        self.advance_choice: Optional[int] = None
        self.return_choice: Optional[int] = None
        self.bottle_hitboxes: Dict[int, Tuple[float, float, float, float]] = {}

        self._build_layout()
        self.reset_game()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = tk.Frame(self.root, bg=BACKGROUND)
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 8))
        header.columnconfigure(0, weight=1)

        title = tk.Label(
            header,
            text="The Seven Bottles",
            bg=BACKGROUND,
            fg=INK,
            font=("Georgia", 28, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = tk.Label(
            header,
            text="A BFS-solved logic puzzle inspired by the first Harry Potter book",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 11),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.canvas = tk.Canvas(
            self.root,
            bg=PANEL,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        self.canvas.bind("<Button-1>", self._handle_canvas_click)
        self.canvas.bind("<Configure>", lambda _event: self.draw_bottles())

        footer = tk.Frame(self.root, bg=BACKGROUND)
        footer.grid(row=2, column=0, sticky="ew", padx=28, pady=(8, 24))
        footer.columnconfigure(0, weight=1)

        self.status_label = tk.Label(
            footer,
            text="",
            bg=BACKGROUND,
            fg=INK,
            font=("Segoe UI", 15, "bold"),
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.detail_label = tk.Label(
            footer,
            text=f"BFS explored {EXPLORED_STATES} states",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.detail_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.restart_button = tk.Button(
            footer,
            text="Restart",
            command=self.reset_game,
            bg=GOLD,
            fg="#15110a",
            activebackground="#f1c96b",
            activeforeground="#15110a",
            relief=tk.FLAT,
            padx=18,
            pady=9,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        )
        self.restart_button.grid(row=0, column=1, rowspan=2, sticky="e")

    def reset_game(self) -> None:
        self.phase = ADVANCE
        self.advance_choice = None
        self.return_choice = None
        self.status_label.config(text="Pick the bottle that moves forward.", fg=INK)
        self.detail_label.config(text=f"BFS explored {EXPLORED_STATES} states")
        self.draw_bottles()

    def _handle_canvas_click(self, event: tk.Event) -> None:
        bottle_index = self._bottle_at(event.x, event.y)
        if bottle_index is None or self.phase == "done":
            return

        if self.phase == ADVANCE:
            self.advance_choice = bottle_index
            self.phase = RETURN
            self.status_label.config(text="Pick the bottle that brings you back.", fg=INK)
            self.detail_label.config(text=f"Advance choice: bottle {bottle_index + 1}")
        else:
            self.return_choice = bottle_index
            self.phase = "done"
            self._show_result()

        self.draw_bottles()

    def _bottle_at(self, x: int, y: int) -> Optional[int]:
        for index, (left, top, right, bottom) in self.bottle_hitboxes.items():
            if left <= x <= right and top <= y <= bottom:
                return index
        return None

    def _show_result(self) -> None:
        won = self.advance_choice == ADVANCE_BOTTLE and self.return_choice == RETURN_BOTTLE

        if won:
            self.status_label.config(text="You win", fg=GREEN)
        else:
            self.status_label.config(text="Try again", fg=RED)

        self.detail_label.config(
            text=(
                f"Advance: bottle {self.advance_choice + 1}  "
                f"Return: bottle {self.return_choice + 1}"
            )
        )

    def draw_bottles(self) -> None:
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        self.canvas.delete("all")
        self.bottle_hitboxes.clear()

        self._draw_backdrop(width, height)

        margin = 72
        usable_width = max(width - margin * 2, 1)
        spacing = usable_width / (len(BOTTLES) - 1)
        max_bottle_height = max(bottle.height for bottle in BOTTLES)
        scale = min(1.22, max(0.78, (height - 110) / max_bottle_height))
        shelf_y = height - 62

        self.canvas.create_line(
            38,
            shelf_y + 10,
            width - 38,
            shelf_y + 10,
            fill="#3b2d21",
            width=8,
        )
        self.canvas.create_line(
            42,
            shelf_y + 17,
            width - 42,
            shelf_y + 17,
            fill="#16100c",
            width=3,
        )

        for index, bottle in enumerate(BOTTLES):
            center_x = margin + index * spacing
            self._draw_bottle(index, bottle, center_x, shelf_y, scale)

    def _draw_backdrop(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(0, 0, width, height, fill=PANEL, outline="")
        self.canvas.create_rectangle(0, 0, width, height, fill="", outline="#2b3447", width=2)

        for y in range(44, max(height - 80, 44), 54):
            self.canvas.create_line(32, y, width - 32, y, fill="#222b3d", width=1)

    def _draw_bottle(
        self,
        index: int,
        bottle: Bottle,
        center_x: float,
        shelf_y: float,
        scale: float,
    ) -> None:
        body_width = bottle.body_width * scale
        height = bottle.height * scale
        neck_width = bottle.neck_width * scale
        neck_height = max(30, height * 0.28)
        body_top = shelf_y - height + neck_height
        top = shelf_y - height
        left = center_x - body_width / 2
        right = center_x + body_width / 2
        neck_left = center_x - neck_width / 2
        neck_right = center_x + neck_width / 2

        is_advance_selected = self.advance_choice == index
        is_return_selected = self.return_choice == index
        selected = is_advance_selected or is_return_selected
        outline = OUTLINE
        outline_width = 3

        if is_advance_selected:
            outline = GOLD
            outline_width = 5
        if is_return_selected:
            outline = BLUE
            outline_width = 5

        glow_pad = 15
        if selected:
            glow_color = GOLD if is_advance_selected else BLUE
            self.canvas.create_oval(
                left - glow_pad,
                top - glow_pad,
                right + glow_pad,
                shelf_y + glow_pad,
                fill=glow_color,
                outline="",
                stipple="gray25",
            )

        shoulder_y = body_top + 14 * scale
        if index == 6:
            self._draw_round_bottle(
                center_x,
                shelf_y,
                body_width,
                height,
                neck_width,
                neck_height,
                bottle.liquid_color,
                outline,
                outline_width,
            )
        else:
            self.canvas.create_polygon(
                left,
                shoulder_y,
                neck_left,
                body_top,
                neck_left,
                top + 8,
                neck_right,
                top + 8,
                neck_right,
                body_top,
                right,
                shoulder_y,
                right,
                shelf_y,
                left,
                shelf_y,
                fill=GLASS,
                outline=outline,
                width=outline_width,
                smooth=True,
            )

            liquid_top = shelf_y - height * 0.34
            self.canvas.create_rectangle(
                left + 7 * scale,
                liquid_top,
                right - 7 * scale,
                shelf_y - 7 * scale,
                fill=bottle.liquid_color,
                outline="",
            )
            self.canvas.create_line(
                left + 10 * scale,
                liquid_top + 7 * scale,
                right - 10 * scale,
                liquid_top + 7 * scale,
                fill="#f4dfab",
                width=max(1, int(2 * scale)),
            )

        self.canvas.create_rectangle(
            neck_left - 5 * scale,
            top,
            neck_right + 5 * scale,
            top + 9 * scale,
            fill="#c8b07a",
            outline=outline,
            width=2,
        )

        self.canvas.create_line(
            center_x - body_width * 0.22,
            body_top + 18 * scale,
            center_x - body_width * 0.22,
            shelf_y - 18 * scale,
            fill="#ffffff",
            width=max(1, int(2 * scale)),
        )
        self.canvas.create_line(
            center_x + body_width * 0.26,
            body_top + 26 * scale,
            center_x + body_width * 0.26,
            shelf_y - 18 * scale,
            fill=GLASS_SHADOW,
            width=max(1, int(2 * scale)),
        )

        marker_y = shelf_y + 34
        marker_fill = "#242d3e"
        marker_outline = "#39445a"

        if is_advance_selected:
            marker_fill = "#3b2a11"
            marker_outline = GOLD
        elif is_return_selected:
            marker_fill = "#172a3d"
            marker_outline = BLUE

        self.canvas.create_oval(
            center_x - 17,
            marker_y - 17,
            center_x + 17,
            marker_y + 17,
            fill=marker_fill,
            outline=marker_outline,
            width=2,
        )
        self.canvas.create_text(
            center_x,
            marker_y,
            text=str(bottle.number),
            fill=INK,
            font=("Segoe UI", 11, "bold"),
        )

        if is_advance_selected:
            self.canvas.create_text(
                center_x,
                marker_y + 30,
                text="Advance",
                fill=GOLD,
                font=("Segoe UI", 9, "bold"),
            )
        elif is_return_selected:
            self.canvas.create_text(
                center_x,
                marker_y + 30,
                text="Return",
                fill=BLUE,
                font=("Segoe UI", 9, "bold"),
            )

        self.bottle_hitboxes[index] = (
            left - 18,
            top - 18,
            right + 18,
            shelf_y + 58,
        )

    def _draw_round_bottle(
        self,
        center_x: float,
        shelf_y: float,
        body_width: float,
        height: float,
        neck_width: float,
        neck_height: float,
        liquid_color: str,
        outline: str,
        outline_width: int,
    ) -> None:
        body_height = height - neck_height * 0.55
        body_top = shelf_y - body_height
        left = center_x - body_width / 2
        right = center_x + body_width / 2
        neck_left = center_x - neck_width / 2
        neck_right = center_x + neck_width / 2
        top = shelf_y - height

        self.canvas.create_rectangle(
            neck_left,
            top + 8,
            neck_right,
            body_top + 12,
            fill=GLASS,
            outline=outline,
            width=outline_width,
        )
        self.canvas.create_oval(
            left,
            body_top,
            right,
            shelf_y,
            fill=GLASS,
            outline=outline,
            width=outline_width,
        )
        self.canvas.create_arc(
            left + 7,
            body_top + body_height * 0.38,
            right - 7,
            shelf_y - 6,
            start=180,
            extent=180,
            fill=liquid_color,
            outline="",
        )
        self.canvas.create_line(
            left + body_width * 0.26,
            body_top + body_height * 0.28,
            left + body_width * 0.2,
            shelf_y - body_height * 0.26,
            fill="#ffffff",
            width=2,
        )


def main() -> None:
    root = tk.Tk()
    PoisonPuzzleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()