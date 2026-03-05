import re


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

    parts = []
    for node in content:
        parts.append(_convert_node(node, heading_depth=2, floats=floats))

    md = "\n".join(parts)
    # Clean up excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def _convert_node(node: dict, heading_depth: int, floats: dict) -> str:
    """Recursively convert a JSON node to Markdown."""
    name = node.get("#name", "")
    children = node.get("$$", [])
    attrs = node.get("$", {})

    if name in ("body", "sections", "appendices"):
        return _convert_children(children, heading_depth, floats)

    if name == "section":
        return _convert_section(node, heading_depth, floats)

    if name in ("para", "simple-para", "note-para"):
        return _convert_inline(node) + "\n\n"

    if name == "acknowledgment":
        heading = "#" * heading_depth + " Acknowledgments\n\n"
        return heading + _convert_children(children, heading_depth + 1, floats)

    if name == "conflict-of-interest":
        heading = "#" * heading_depth + " Conflict of Interest\n\n"
        return heading + _convert_children(children, heading_depth + 1, floats)

    if name == "list":
        return _convert_list(node, floats) + "\n"

    if name == "display":
        return _convert_display(node, floats)

    if name == "float-anchor":
        refid = attrs.get("refid", "")
        if refid in floats:
            return _convert_float(floats[refid])
        return ""

    if name == "footnote":
        return _convert_children(children, heading_depth, floats)

    # Fallback: convert children
    if children:
        return _convert_children(children, heading_depth, floats)

    return ""


def _convert_children(children: list, heading_depth: int, floats: dict) -> str:
    parts = []
    for child in children:
        parts.append(_convert_node(child, heading_depth, floats))
    return "".join(parts)


def _convert_section(node: dict, heading_depth: int, floats: dict) -> str:
    children = node.get("$$", [])
    title = ""
    body_parts = []

    for child in children:
        if child.get("#name") == "section-title":
            title = _convert_inline(child)
        else:
            body_parts.append(_convert_node(child, heading_depth + 1, floats))

    heading = "#" * heading_depth + " " + title + "\n\n" if title else ""
    return heading + "".join(body_parts)


def _convert_inline(node: dict) -> str:
    """Convert a node and its children to inline Markdown text."""
    name = node.get("#name", "")
    text = node.get("_", "")
    children = node.get("$$", [])
    attrs = node.get("$", {})

    if name == "__text__":
        return text

    if name == "bold":
        inner = _inline_children(node) if children else text
        return f"**{inner}**"

    if name == "italic":
        inner = _inline_children(node) if children else text
        return f"*{inner}*"

    if name == "sup":
        inner = _inline_children(node) if children else text
        return f"^{inner}^"

    if name == "cross-ref":
        return _inline_children(node) if children else text

    if name == "inter-ref":
        href = attrs.get("href", "")
        inner = _inline_children(node) if children else text
        return f"[{inner}]({href})" if href else inner

    if name == "float-anchor":
        return ""

    if name in ("math", "formula"):
        alttext = attrs.get("alttext", "")
        if alttext:
            return alttext
        return _inline_children(node) if children else text

    if name == "label":
        return text

    if name == "display":
        return _convert_display(node, {})

    # For para/simple-para/section-title and other containers, join children
    if children:
        return _inline_children(node)

    return text


def _inline_children(node: dict) -> str:
    parts = []
    for child in node.get("$$", []):
        parts.append(_convert_inline(child))
    return "".join(parts)


def _convert_list(node: dict, floats: dict) -> str:
    items = []
    for child in node.get("$$", []):
        if child.get("#name") == "list-item":
            item_parts = []
            for sub in child.get("$$", []):
                if sub.get("#name") == "label":
                    continue  # skip bullet labels
                item_parts.append(_convert_inline(sub).strip())
            items.append("- " + " ".join(item_parts))
    return "\n".join(items) + "\n"


def _convert_display(node: dict, floats: dict) -> str:
    """Convert display elements (usually equations)."""
    children = node.get("$$", [])
    for child in children:
        if child.get("#name") == "formula":
            label = ""
            alttext = ""
            for sub in child.get("$$", []):
                if sub.get("#name") == "label":
                    label = sub.get("_", "")
                elif sub.get("#name") == "math":
                    alttext = sub.get("$", {}).get("alttext", "")
            if alttext:
                return f"\n\n{alttext} {label}\n\n"
            elif label:
                return f"\n\n{label}\n\n"
    return ""


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
        label = ""
        caption = ""
        for child in children:
            cname = child.get("#name", "")
            if cname == "label":
                label = child.get("_", "")
            elif cname == "caption":
                caption = _inline_children(child)
        desc = f"{label}: {caption}" if label and caption else caption or label
        return f"\n\n*{desc}*\n\n"

    return ""
