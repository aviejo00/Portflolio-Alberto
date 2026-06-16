# Harry Potter Poisons Puzzle

An interactive Python version of the seven-bottle poison riddle from the first Harry Potter book. The app uses breadth-first search to solve the logic puzzle, then lets the player choose the bottle that moves forward and the bottle that brings them back.

This is a fan-made portfolio project and does not use official Harry Potter assets.

## Features

- Seven clickable, illustrated bottles.
- Two-step answer flow: choose the advance bottle first, then the return bottle.
- Result feedback with `You win` or `Try again`.
- Restart button for another attempt.
- BFS solver implemented in `poisons.py`.
- No third-party dependencies.

## Run

No package installation is required. The `requirements.txt` file is included to make that explicit.

```bash
python poisons.py
```

Tkinter is included with most Python installations. If the window does not open, make sure your Python installation includes Tk support.

## How The Solver Works

The solver treats each partial row of bottles as a BFS state. Each state stores:

- The bottle contents assigned so far.
- The remaining counts for poison, nettle wine, advance, and return.

The search expands possible contents one bottle at a time and prunes states that already break a clue:

- Three bottles contain poison.
- Two bottles contain nettle wine.
- One bottle moves the drinker forward.
- One bottle returns the drinker back.
- Neither end bottle moves forward.
- The end bottles are different.
- The smallest and largest bottles are not poison.
- The second bottle from the left and the second bottle from the right are the wine pair.
- Every wine bottle has poison somewhere to its left.

When the BFS finds the unique valid arrangement, the interface compares the player's two selections against that solution.

## Project Structure

```text
.
|-- poisons.py        # BFS solver and Tkinter interface
|-- README.md         # Project documentation
`-- requirements.txt # No third-party dependencies
```

## Portfolio Notes

The project is intentionally small and self-contained: it demonstrates state-space search, clue-based pruning, event-driven UI, and a polished desktop interaction without requiring a web framework or external packages.
