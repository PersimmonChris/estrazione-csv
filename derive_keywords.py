from __future__ import annotations
import json
from pathlib import Path

MAX_LEVELS = 3

class Node:
    __slots__ = ("name","full","parent","children","depth")
    def __init__(self, name: str, full: str, parent: 'Node|None', depth: int):
        self.name = name
        self.full = full
        self.parent = parent
        self.children: dict[str, Node] = {}
        self.depth = depth

def build_tree(paths: list[str]):
    root = Node("ROOT", "", None, -1)
    index: dict[str, Node] = {}
    for p in paths:
        parts = [s.strip() for s in p.split('|') if s.strip()]
        if not parts:
            continue
        node = root
        full = ""
        for part in parts[:MAX_LEVELS]:
            full = f"{full}|{part}" if full else part
            if part not in node.children:
                node.children[part] = Node(part, full, node, node.depth+1)
            node = node.children[part]
            index[node.full] = node
    return root, index

def leaf_paths(node: Node) -> list[str]:
    out: list[str] = []
    def dfs(n: Node):
        if not n.children:
            if n.depth >= 0:
                out.append(n.full)
            return
        for c in n.children.values():
            dfs(c)
    dfs(node)
    return out

def leaves_under(node: Node) -> set[str]:
    return set(leaf_paths(node))

def compute_coverage(root: Node, blacklist: set[str]):
    # Return set of selected keyword nodes via greedy cover: choose highest fully-covered nodes
    selected_keywords: list[str] = []

    def is_fully_covered(n: Node) -> bool:
        for c in n.children.values():
            if not is_fully_covered(c):
                return False
        if not n.children:
            return n.full in blacklist
        return True

    def mark_and_collect(n: Node):
        if not n.children:
            # leaf coverage guaranteed by caller
            return
        # if entire subtree fully covered, select node and stop descending
        fully = True
        def check(n2: Node) -> bool:
            if not n2.children:
                return n2.full in blacklist
            return all(check(c) for c in n2.children.values())
        fully = check(n)
        if fully:
            if n.depth >= 0:
                selected_keywords.append(n.full)
            return
        # else descend
        for c in n.children.values():
            if not c.children:
                if c.full in blacklist:
                    selected_keywords.append(c.full)
            else:
                mark_and_collect(c)

    mark_and_collect(root)
    return selected_keywords

def covered_leaves_by_keywords(keywords: list[str], index: dict[str, Node]) -> set[str]:
    covered: set[str] = set()
    for k in keywords:
        n = index.get(k)
        if n is None:
            # keyword might be a top-level that is also a leaf-less node synthesized from data
            # if not found, skip silently
            continue
        if n.children:
            covered.update(leaves_under(n))
        else:
            covered.add(n.full)
    return covered

def main():
    categories_path = Path('categorie_uniche.json')
    blacklist_path = Path('blacklist.txt')
    if not categories_path.exists() or not blacklist_path.exists():
        print("Missing categorie_uniche.json or blacklist.txt")
        return
    all_paths = json.loads(categories_path.read_text(encoding='utf-8'))
    bl_lines = [l.strip() for l in blacklist_path.read_text(encoding='utf-8').splitlines()]
    bl_norm = set(p for p in bl_lines if p)

    tree, index = build_tree(all_paths)

    # Validate: which blacklist entries are unknown
    unknown = sorted(p for p in bl_norm if p not in set(all_paths))

    # Coverage per root
    report = []
    for root_name, top in sorted(tree.children.items()):
        leaves = leaf_paths(top)
        leaves_set = set(leaves)
        bl_in_subtree = sorted(p for p in bl_norm if p in leaves_set)
        coverage = (len(bl_in_subtree), len(leaves))
        if coverage[1] > 0:
            report.append((root_name, coverage[0], coverage[1]))

    keywords = compute_coverage(tree, bl_norm)

    print("Suggested blacklist keywords (safe, minimal):")
    for k in keywords:
        print(f" - {k}")

    print("\nCoverage by root (blacklisted/total leaves):")
    for name, a, b in report:
        pct = 0 if b == 0 else (a*100.0/b)
        print(f" - {name}: {a}/{b} ({pct:.1f}%)")

    if unknown:
        print("\nWarning: blacklist entries not found in categorie_uniche.json (after normalization):")
        for u in unknown:
            print(f" - {u}")

    # Residuals after applying minimal keywords
    covered = covered_leaves_by_keywords(keywords, index)
    residual = sorted(p for p in bl_norm if p not in covered)
    print("\nResidual blacklist entries after applying suggested keywords:")
    if not residual:
        print(" - None (0)")
    else:
        for r in residual[:100]:
            print(f" - {r}")
        if len(residual) > 100:
            print(f" ... (+{len(residual)-100} more)")

    # If residuals exist, propose level-2 parents that fully cover their subtrees within residuals
    if residual:
        residual_set = set(residual)
        proposals: set[str] = set()
        # group residuals by their parent (level-1 and level-2)
        for r in residual:
            parts = [s.strip() for s in r.split('|') if s.strip()]
            for lvl in (1,2):
                if len(parts) >= lvl:
                    parent_path = '|'.join(parts[:lvl])
                    n = index.get(parent_path)
                    if not n:
                        continue
                    leaves = leaves_under(n)
                    # we only propose if ALL leaves under parent are in residual (i.e., client selected whole subtree under this parent)
                    if leaves and leaves.issubset(residual_set):
                        proposals.add(parent_path)
        if proposals:
            print("\nAdditional level-1/2 keywords that exactly cover residuals:")
            for p in sorted(proposals):
                print(f" - {p}")

if __name__ == '__main__':
    main()
