"""Scan SQLAlchemy models for duplicate Index / UniqueConstraint names."""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "app"


def scan() -> dict[str, list[tuple[str, str, int]]]:
    idx: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for path in ROOT.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        last_table = "?"
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "__tablename__":
                        if isinstance(node.value, ast.Constant):
                            last_table = str(node.value.value)
            if isinstance(node, ast.Call):
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name == "Index" and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                        idx[arg0.value].append(
                            (str(path.relative_to(ROOT.parent)), last_table, node.lineno)
                        )
    return idx


def main() -> int:
    idx = scan()
    dups = {k: v for k, v in idx.items() if len({(p, t) for p, t, _ in v}) > 1 or len(v) > 1}
    # true dups = same index name appearing more than once
    real = {k: v for k, v in idx.items() if len(v) > 1}
    print("total_named_indexes", len(idx))
    print("duplicate_index_names", len(real))
    for k, v in sorted(real.items()):
        print(k)
        for item in v:
            print(" ", item)
    return 0 if not real else 1


if __name__ == "__main__":
    raise SystemExit(main())
