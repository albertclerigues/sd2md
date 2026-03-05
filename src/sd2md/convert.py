import re

from sd2md.mathml import math_node_to_latex


def extract_abstract(state: dict) -> str:
    """Extract abstract text from preloaded state."""
    abstracts = state.get("abstracts", {})
    for item in abstracts.get("content", []):
        # Find the first abstract with actual paragraph content
        paragraphs = []
        for child in item.get("$$", []):
            if child.get("#name") in ("simple-para", "para"):
                paragraphs.append(_convert_inline(child))
            # Abstract may have nested divs with paragraphs
            for grandchild in child.get("$$", []):
                if grandchild.get("#name") in ("simple-para", "para"):
                    paragraphs.append(_convert_inline(grandchild))
        if paragraphs:
            return "\n\n".join(paragraphs)
    return ""


def convert_body(body_json: dict) -> str:
    """Convert body JSON tree to Markdown."""
    content = body_json.get("content", [])
    floats = {
        f.get("$", {}).get("id", ""): f
        for f in body_json.get("floats", [])
        if f.get("$", {}).get("id")
    }

    footnotes = {}  # id -> (label, content)

    parts = []
    for node in content:
        parts.append(
            _convert_node(node, heading_depth=2, floats=floats, footnotes=footnotes)
        )

    md = "\n".join(parts)

    # Append footnote definitions
    if footnotes:
        fn_lines = []
        for fn_id in sorted(
            footnotes,
            key=lambda k: int(footnotes[k][0]) if footnotes[k][0].isdigit() else 0,
        ):
            label, fn_content = footnotes[fn_id]
            fn_lines.append(f"[^{label}]: {fn_content}")
        md += "\n\n" + "\n".join(fn_lines)

    # Clean up excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def _convert_node(
    node: dict, heading_depth: int, floats: dict, footnotes: dict | None = None
) -> str:
    """Recursively convert a JSON node to Markdown."""
    name = node.get("#name", "")
    children = node.get("$$", [])
    attrs = node.get("$", {})

    if footnotes is None:
        footnotes = {}

    if name in ("body", "sections", "appendices"):
        return _convert_children(children, heading_depth, floats, footnotes)

    if name == "section":
        return _convert_section(node, heading_depth, floats, footnotes)

    if name in ("para", "simple-para", "note-para"):
        text = _convert_inline(node, footnotes) + "\n\n"
        # Expand any float-anchors embedded in the paragraph
        for child in children:
            if child.get("#name") == "float-anchor":
                refid = child.get("$", {}).get("refid", "")
                if refid in floats:
                    text += _convert_float(floats[refid])
        return text

    if name == "acknowledgment":
        heading = "#" * heading_depth + " Acknowledgments\n\n"
        return heading + _convert_children(
            children, heading_depth + 1, floats, footnotes
        )

    if name == "conflict-of-interest":
        heading = "#" * heading_depth + " Conflict of Interest\n\n"
        return heading + _convert_children(
            children, heading_depth + 1, floats, footnotes
        )

    if name == "list":
        return _convert_list(node, floats, footnotes) + "\n"

    if name == "display":
        return _convert_display(node, floats)

    if name == "float-anchor":
        refid = attrs.get("refid", "")
        if refid in floats:
            return _convert_float(floats[refid])
        return ""

    if name == "footnote":
        # Collect footnote definition; don't render inline
        fn_id = attrs.get("id", "")
        label = ""
        content_parts = []
        for child in children:
            if child.get("#name") == "label":
                label = child.get("_", "")
            else:
                content_parts.append(_convert_inline(child, footnotes).strip())
        if fn_id and label:
            footnotes[fn_id] = (label, " ".join(content_parts))
        return ""

    # Fallback: convert children
    if children:
        return _convert_children(children, heading_depth, floats, footnotes)

    return ""


def _convert_children(
    children: list, heading_depth: int, floats: dict, footnotes: dict | None = None
) -> str:
    parts = []
    for child in children:
        parts.append(_convert_node(child, heading_depth, floats, footnotes))
    return "".join(parts)


def _convert_section(
    node: dict, heading_depth: int, floats: dict, footnotes: dict | None = None
) -> str:
    children = node.get("$$", [])
    title = ""
    body_parts = []

    for child in children:
        if child.get("#name") == "section-title":
            title = _convert_inline(child)
        else:
            body_parts.append(
                _convert_node(child, heading_depth + 1, floats, footnotes)
            )

    heading = "#" * heading_depth + " " + title + "\n\n" if title else ""
    return heading + "".join(body_parts)


def _convert_inline(node: dict, footnotes: dict | None = None) -> str:
    """Convert a node and its children to inline Markdown text."""
    name = node.get("#name", "")
    text = node.get("_", "")
    children = node.get("$$", [])
    attrs = node.get("$", {})

    if name == "__text__":
        return text

    if name == "bold":
        inner = _inline_children(node, footnotes) if children else text
        return f"**{inner}**"

    if name == "italic":
        inner = _inline_children(node, footnotes) if children else text
        return f"*{inner}*"

    if name == "sup":
        inner = _inline_children(node, footnotes) if children else text
        return f"^{inner}^"

    if name == "cross-ref":
        refid = attrs.get("refid", "")
        if refid.startswith("fn"):
            # Footnote reference - extract label from sup child
            label = ""
            for child in children:
                if child.get("#name") == "sup":
                    label = child.get("_", "") or _inline_children(child, footnotes)
            return f"[^{label}]" if label else _inline_children(node, footnotes)
        return _inline_children(node, footnotes) if children else text

    if name == "inter-ref":
        href = attrs.get("href", "")
        inner = _inline_children(node, footnotes) if children else text
        return f"[{inner}]({href})" if href else inner

    if name == "float-anchor":
        return ""

    if name == "footnote":
        # Collect footnote and return empty string
        fn_id = attrs.get("id", "")
        label = ""
        content_parts = []
        for child in children:
            if child.get("#name") == "label":
                label = child.get("_", "")
            else:
                content_parts.append(_convert_inline(child, footnotes).strip())
        if footnotes is not None and fn_id and label:
            footnotes[fn_id] = (label, " ".join(content_parts))
        return ""

    if name in ("math", "formula"):
        math_node = node
        if name == "formula":
            for child in children:
                if child.get("#name") == "math":
                    math_node = child
                    break
        latex = math_node_to_latex(math_node)
        if latex:
            return f"${latex}$"
        return _inline_children(node, footnotes) if children else text

    if name == "label":
        return text

    if name == "br":
        return " "

    if name == "display":
        return _convert_display(node, {})

    # For para/simple-para/section-title and other containers, join children
    if children:
        return _inline_children(node, footnotes)

    return text


def _inline_children(node: dict, footnotes: dict | None = None) -> str:
    parts = []
    for child in node.get("$$", []):
        parts.append(_convert_inline(child, footnotes))
    return "".join(parts)


def _convert_list(node: dict, floats: dict, footnotes: dict | None = None) -> str:
    items = []
    for child in node.get("$$", []):
        if child.get("#name") == "list-item":
            item_parts = []
            for sub in child.get("$$", []):
                if sub.get("#name") == "label":
                    continue  # skip bullet labels
                item_parts.append(_convert_inline(sub, footnotes).strip())
            items.append("- " + " ".join(item_parts))
    return "\n".join(items) + "\n"


def _convert_display(node: dict, floats: dict) -> str:
    """Convert display elements (usually equations)."""
    children = node.get("$$", [])
    for child in children:
        if child.get("#name") == "formula":
            label = ""
            math_node = None
            for sub in child.get("$$", []):
                if sub.get("#name") == "label":
                    label = sub.get("_", "")
                elif sub.get("#name") == "math":
                    math_node = sub
            if math_node is not None:
                latex = math_node_to_latex(math_node)
                if latex:
                    tag = f" \\tag{{{label}}}" if label else ""
                    return f"\n\n$${latex}{tag}$$\n\n"
            if label:
                return f"\n\n{label}\n\n"
    return ""


def _convert_table(node: dict) -> str:
    """Convert a table float to a GFM Markdown table."""
    children = node.get("$$", [])
    label = ""
    caption = ""
    tgroup = None

    for child in children:
        cname = child.get("#name", "")
        if cname == "label":
            label = child.get("_", "")
        elif cname == "caption":
            caption = _inline_children(child)
        elif cname == "tgroup":
            tgroup = child

    # Caption line
    desc = f"{label}: {caption}" if label and caption else caption or label
    caption_line = f"**{desc}**" if desc else ""

    if tgroup is None:
        # Fallback to caption-only
        return f"\n\n*{desc}*\n\n" if desc else ""

    num_cols = int(tgroup.get("$", {}).get("cols", 0))
    thead = None
    tbody = None
    for child in tgroup.get("$$", []):
        cname = child.get("#name", "")
        if cname == "thead":
            thead = child
        elif cname == "tbody":
            tbody = child

    def _extract_rows(section):
        rows = []
        if section is None:
            return rows
        for child in section.get("$$", []):
            if child.get("#name") == "row":
                cells = []
                for entry in child.get("$$", []):
                    if entry.get("#name") == "entry":
                        cell_text = entry.get("_", "")
                        if entry.get("$$"):
                            cell_text = _inline_children(entry)
                        # Replace any newlines/pipes that would break GFM
                        cell_text = cell_text.replace("\n", " ").strip()
                        cells.append(cell_text)
                rows.append(cells)
        return rows

    header_rows = _extract_rows(thead)
    body_rows = _extract_rows(tbody)

    # Determine header
    if header_rows:
        header = header_rows[0]
    elif body_rows:
        header = body_rows.pop(0)
    else:
        header = [""] * num_cols

    # Ensure consistent column count
    if num_cols == 0:
        num_cols = max(
            len(header),
            max((len(r) for r in body_rows), default=0),
        )

    # Pad rows to num_cols
    def _pad(row):
        return row + [""] * (num_cols - len(row)) if len(row) < num_cols else row

    header = _pad(header)
    body_rows = [_pad(r) for r in body_rows]

    # Build GFM table
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in range(num_cols)) + " |")
    for row in body_rows:
        lines.append("| " + " | ".join(row) + " |")

    table_md = "\n".join(lines)
    parts = [p for p in [caption_line, table_md] if p]
    return "\n\n" + "\n\n".join(parts) + "\n\n"


def _convert_float(node: dict) -> str:
    """Convert a float (figure/table) to Markdown."""
    name = node.get("#name", "")
    children = node.get("$$", [])

    if name == "figure":
        label = ""
        caption = ""
        alt_text = ""
        for child in children:
            cname = child.get("#name", "")
            if cname == "label":
                label = child.get("_", "")
            elif cname == "caption":
                caption = _inline_children(child)
            elif cname == "alt-text":
                alt_text = child.get("_", "")
        desc = f"{label}: {caption}" if label and caption else caption or label
        return f"\n\n*{desc}*\n\n"

    if name == "table":
        return _convert_table(node)

    return ""
