import argparse
import sys
from pathlib import Path

from sd2md.fetch import fetch_article
from sd2md.metadata import extract_metadata, is_paywalled
from sd2md.convert import extract_abstract, convert_body
from sd2md.output import generate_filename, assemble_document


def main():
    parser = argparse.ArgumentParser(
        prog="sd2md",
        description="Convert ScienceDirect articles to Markdown",
    )
    parser.add_argument("url", help="ScienceDirect article URL")
    parser.add_argument(
        "-o", "--output", help="Output file path (default: auto-generated)"
    )
    parser.add_argument(
        "--stdout", action="store_true", help="Print to stdout instead of file"
    )
    args = parser.parse_args()

    if "sciencedirect.com" not in args.url:
        print("Error: URL must be a ScienceDirect article URL", file=sys.stderr)
        sys.exit(1)

    # Fetch page + body JSON
    try:
        html, state, body_json = fetch_article(args.url)
    except Exception as e:
        print(f"Error fetching article: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract metadata
    meta = extract_metadata(html, args.url, state)
    if not meta.title:
        print(
            "Error: Could not extract article metadata. Is this a valid ScienceDirect article?",
            file=sys.stderr,
        )
        sys.exit(1)

    # Paywall check
    paywalled = is_paywalled(state)
    if paywalled:
        print(
            "WARNING: Article body not accessible (paywall/login required).\n"
            "         Only metadata and abstract were extracted.\n"
            "         Output marked as incomplete (complete: false in frontmatter).",
            file=sys.stderr,
        )

    # Convert content
    abstract = extract_abstract(state)
    body = convert_body(body_json) if body_json else ""

    # Assemble document
    document = assemble_document(meta, abstract, body, complete=not paywalled)

    # Output
    if args.stdout:
        print(document)
    else:
        filename = args.output or generate_filename(meta)
        Path(filename).write_text(document, encoding="utf-8")
        print(f"Written to {filename}", file=sys.stderr)
