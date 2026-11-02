"""Layout for the assessment → LO → PO diagram on the course evidence page.

Mirrors the Team Project Brief's flow slides with the enrollment's real data.
Only geometry and labels are computed here; scores come from the calculators.
"""

NODE_W = 210
NODE_H = 56
ROW_GAP = 20
HEAD_H = 32
COLUMN_X = (0, 330, 660)


def _number(value):
    text = f"{value:.2f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _place(nodes, x, body_height):
    total = len(nodes) * NODE_H + max(len(nodes) - 1, 0) * ROW_GAP
    top = HEAD_H + (body_height - total) / 2
    for index, node in enumerate(nodes):
        node.update(x=x, y=top + index * (NODE_H + ROW_GAP), w=NODE_W, h=NODE_H)
        node["cy"] = node["y"] + NODE_H / 2


def _ports(edges, end, other):
    """Spread several lines meeting one node along its side so labels don't collide."""
    groups = {}
    for edge in edges:
        groups.setdefault(id(edge[end]), []).append(edge)
    for group in groups.values():
        group.sort(key=lambda edge: edge[other]["cy"])
        count = len(group)
        spacing = min(22, (NODE_H - 16) / max(count - 1, 1))
        for index, edge in enumerate(group):
            edge[f"{end}_y"] = edge[end]["cy"] + (index - (count - 1) / 2) * spacing


def _edge(spec, t):
    source, target = spec["source"], spec["target"]
    x1, y1 = source["x"] + NODE_W, spec["source_y"]
    x2, y2 = target["x"], spec["target_y"]
    label, missing = spec["label"], spec["missing"]
    bend = (x2 - x1) / 2
    # Point on the cubic curve at t, where the weight label sits.
    u = 1 - t
    lx = u**3 * x1 + 3 * u * u * t * (x1 + bend) + 3 * u * t * t * (x2 - bend) + t**3 * x2
    ly = u**3 * y1 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y2
    return {
        "d": f"M{x1:.1f},{y1:.1f} C{x1 + bend:.1f},{y1:.1f} {x2 - bend:.1f},{y2:.1f} {x2:.1f},{y2:.1f}",
        "label": label,
        "lx": lx, "ly": ly, "lw": 12 + 7 * len(label),
        "missing": missing,
    }


def build_flow(assessment_results, lo_results, po_results):
    """Nodes and edges for one enrollment, or None when there is nothing to draw."""
    if not assessment_results or not lo_results:
        return None

    assessments, by_assessment = [], {}
    for row in assessment_results:
        assessment, score = row["assessment"], row["score"]
        node = {
            "title": assessment.name,
            "value": f"{_number(score)} / {_number(assessment.max_score)}" if score is not None else "Not graded",
            "percent": score / assessment.max_score * 100 if score is not None else None,
            "missing": score is None,
            "hint": f"{assessment.name}: {'not graded yet' if score is None else _number(score)}",
        }
        assessments.append(node)
        by_assessment[assessment.pk] = node

    los, by_lo = [], {}
    for row in lo_results:
        node = {
            "title": row["outcome"].code,
            "value": f"{row['score']:.2f}%" if row["score"] is not None else "No score yet",
            "percent": row["score"],
            "missing": row["score"] is None,
            "hint": row["outcome"].description,
        }
        los.append(node)
        by_lo[row["outcome"].pk] = node

    pos = []
    for row in po_results:
        pos.append({
            "title": row["outcome"].code,
            "value": f"{row['score']:.2f}%" if row["score"] is not None else "No score yet",
            "percent": row["score"],
            "missing": row["score"] is None,
            "hint": row["outcome"].description,
            "sources": row["sources"],
        })

    rows = max(len(assessments), len(los), len(pos), 1)
    body = rows * NODE_H + (rows - 1) * ROW_GAP
    for nodes, x in zip((assessments, los, pos), COLUMN_X):
        _place(nodes, x, body)

    first, second = [], []
    for row in assessment_results:
        source = by_assessment[row["assessment"].pk]
        for mapping in row["mappings"]:
            target = by_lo.get(mapping.learning_outcome_id)
            if target:
                first.append({"source": source, "target": target, "missing": source["missing"],
                              "label": f"{_number(mapping.weight)}%"})
    for node in pos:
        for item in node.pop("sources"):
            source = by_lo.get(item["mapping"].learning_outcome_id)
            if source:
                second.append({"source": source, "target": node, "missing": source["missing"],
                               "label": f"{item['mapping'].strength}/5"})
    for specs in (first, second):
        _ports(specs, "source", "target")
        _ports(specs, "target", "source")
    # Labels sit near the receiving node, where its incoming lines are already apart.
    edges = [_edge(spec, 0.8) for spec in first + second]

    return {
        "width": COLUMN_X[-1] + NODE_W if pos else COLUMN_X[1] + NODE_W,
        "height": HEAD_H + body + 8,
        "columns": [
            {"x": COLUMN_X[0], "label": "Assessments"},
            {"x": COLUMN_X[1], "label": "Learning outcomes"},
        ] + ([{"x": COLUMN_X[2], "label": "Program outcomes"}] if pos else []),
        "nodes": assessments + los + pos,
        "edges": edges,
    }
