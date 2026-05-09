"""OpenEvolve browser visualizer removed.

The project keeps only the terminal interactive UI. This module remains as a
small compatibility stub so imports fail with an explicit message instead of
looking for deleted HTML templates or static assets.
"""

from __future__ import annotations


def main() -> None:
    raise RuntimeError("OpenEvolve browser visualizer was removed; use ui-tui instead.")


if __name__ == "__main__":
    main()
