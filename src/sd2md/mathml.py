import logging
import re
import xml.etree.ElementTree as ET

from mathml_to_latex import MathMLToLaTeX

logger = logging.getLogger(__name__)


def json_tree_to_mathml_xml(node: dict) -> str:
    """Reconstruct MathML XML string from ScienceDirect's JSON tree."""
    elem = _build_element(node)
    return ET.tostring(elem, encoding="unicode")


def _build_element(node: dict) -> ET.Element:
    tag = node.get("#name", "")
    # Strip mml: namespace prefix
    if tag.startswith("mml:"):
        tag = tag[4:]
    attrs = {k: v for k, v in node.get("$", {}).items() if not k.startswith("xmlns")}
    elem = ET.Element(tag, attrs)

    # Text content can be directly on the node via "_" attribute
    direct_text = node.get("_", "")
    if direct_text:
        elem.text = direct_text

    children = node.get("$$", [])
    prev = None
    for child in children:
        if child.get("#name") == "__text__":
            text = child.get("_", "")
            if prev is None:
                elem.text = (elem.text or "") + text
            else:
                prev.tail = (prev.tail or "") + text
        else:
            child_elem = _build_element(child)
            elem.append(child_elem)
            prev = child_elem

    return elem


def extract_tex_annotation(node: dict) -> str | None:
    """Search for TeX annotation inside a <semantics> element in the JSON tree."""
    name = node.get("#name", "")
    if name.endswith("semantics") or name == "semantics":
        for child in node.get("$$", []):
            child_name = child.get("#name", "")
            if child_name.endswith("annotation") or child_name == "annotation":
                encoding = child.get("$", {}).get("encoding", "")
                if "tex" in encoding.lower():
                    # Text may be directly in _ or in a __text__ child
                    text = child.get("_", "")
                    if text:
                        return text.strip()
                    for sub in child.get("$$", []):
                        if sub.get("#name") == "__text__":
                            return sub.get("_", "").strip()
    # Recurse into children
    for child in node.get("$$", []):
        result = extract_tex_annotation(child)
        if result:
            return result
    return None


def _extract_text(node: dict) -> str:
    """Recursively extract plain text from a JSON tree node."""
    text = node.get("_", "")
    if text:
        return text
    parts = []
    for child in node.get("$$", []):
        parts.append(_extract_text(child))
    return "".join(parts)


_SPACED_OPERATORS = re.compile(
    r"(?<![a-zA-Z])"
    r"(a r g m a x|a r g m i n|a r g|m a x|m i n|l o g|e x p|s i n|c o s|t a n"
    r"|l i m|i n f|s u p|d e t|d i m|k e r|h o m|d e g|g c d|l c m|Pr)"
    r"(?![a-zA-Z])"
)

_OPERATOR_MAP = {
    s: s.replace(" ", "")
    for s in [
        "a r g m a x",
        "a r g m i n",
        "a r g",
        "m a x",
        "m i n",
        "l o g",
        "e x p",
        "s i n",
        "c o s",
        "t a n",
        "l i m",
        "i n f",
        "s u p",
        "d e t",
        "d i m",
        "k e r",
        "h o m",
        "d e g",
        "g c d",
        "l c m",
        "Pr",
    ]
}


def _fix_latex(latex: str) -> str:
    """Fix known issues in mathml-to-latex output."""
    # Fix unescaped braces: \left{ → \left\{ and \right} → \right\}
    latex = re.sub(r"\\left\{", r"\\left\\{", latex)
    latex = re.sub(r"\\right\}", r"\\right\\}", latex)
    # Fix spaced-out operator names: "a r g m a x" → "\operatorname{argmax}"
    latex = _SPACED_OPERATORS.sub(
        lambda m: f"\\operatorname{{{_OPERATOR_MAP[m.group(1)]}}}",
        latex,
    )
    return latex


def math_node_to_latex(node: dict) -> str:
    """Convert a math/formula JSON node to LaTeX.

    Fallback chain:
    1. Embedded TeX annotation
    2. MathML conversion via mathml-to-latex
    3. alttext attribute
    4. Recursive text extraction
    """
    # 1. Try embedded TeX annotation
    try:
        tex = extract_tex_annotation(node)
        if tex:
            return tex
    except Exception:
        logger.warning("Failed to extract TeX annotation", exc_info=True)

    # 2. Try MathML conversion
    try:
        xml_str = json_tree_to_mathml_xml(node)
        latex = MathMLToLaTeX().convert(xml_str)
        if latex and latex.strip():
            return _fix_latex(latex.strip())
    except Exception:
        logger.warning("MathML to LaTeX conversion failed", exc_info=True)

    # 3. alttext
    alttext = node.get("$", {}).get("alttext", "")
    if alttext:
        return alttext

    # 4. Recursive text extraction
    return _extract_text(node)
