import re
from datetime import date
from sd2md.metadata import ArticleMetadata


def slugify(text: str, max_length: int = 80) -> str:
    """Convert text to kebab-case slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)  # remove non-word chars except hyphens
    text = re.sub(r"[\s_]+", "-", text)  # spaces/underscores to hyphens
    text = re.sub(r"-+", "-", text)  # collapse multiple hyphens
    text = text.strip("-")
    if len(text) > max_length:
        # Truncate at word boundary
        text = text[:max_length].rsplit("-", 1)[0]
    return text


def generate_filename(meta: ArticleMetadata) -> str:
    """Generate filename: YYYY-author-title-slug.md"""
    year = meta.year or "unknown"
    author = re.sub(r"[^\w]", "", meta.first_author_surname.lower()) or "unknown"
    title_slug = slugify(meta.title)
    return f"{year}-{author}-{title_slug}.md"


def yaml_scalar(value: str) -> str:
    """Quote a YAML string value if needed."""
    if any(c in value for c in ":{}[]#&*!|>'\"%@`"):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def build_frontmatter(meta: ArticleMetadata, complete: bool) -> str:
    """Build YAML frontmatter string."""
    lines = ["---"]
    lines.append(f"title: {yaml_scalar(meta.title)}")

    lines.append("authors:")
    for author in meta.authors:
        lines.append(f"  - {yaml_scalar(author)}")

    lines.append(f"journal: {yaml_scalar(meta.journal)}")
    lines.append(f"year: {meta.year}")
    lines.append(f"doi: {yaml_scalar(meta.doi)}")

    if meta.volume:
        lines.append(f"volume: {yaml_scalar(meta.volume)}")
    if meta.issue:
        lines.append(f"issue: {yaml_scalar(meta.issue)}")
    if meta.pages:
        lines.append(f"pages: {yaml_scalar(meta.pages)}")
    if meta.issn:
        lines.append(f"issn: {yaml_scalar(meta.issn)}")

    lines.append(f"url: {yaml_scalar(meta.url)}")

    if meta.keywords:
        lines.append("keywords:")
        for kw in meta.keywords:
            lines.append(f"  - {yaml_scalar(kw)}")

    lines.append(f"date_retrieved: {yaml_scalar(date.today().isoformat())}")
    lines.append(f"complete: {'true' if complete else 'false'}")
    lines.append("---")
    return "\n".join(lines)


def assemble_document(
    meta: ArticleMetadata,
    abstract: str,
    body: str,
    complete: bool,
) -> str:
    """Assemble the full Markdown document."""
    parts = [build_frontmatter(meta, complete)]
    parts.append(f"\n# {meta.title}\n")

    if abstract:
        parts.append("## Abstract\n")
        parts.append(abstract + "\n")

    if body:
        parts.append(body + "\n")

    return "\n".join(parts)
