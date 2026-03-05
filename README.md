# sd2md

Convert ScienceDirect articles to clean Markdown files with YAML frontmatter — directly from a URL.

**Highlights:**

- Fetches article HTML and structured JSON directly from a ScienceDirect URL — no manual browser DevTools steps
- Extracts full metadata (title, authors, DOI, journal, year, volume, issue, pages, keywords)
- Converts article body (sections, equations, figures, tables, lists) to Markdown
- Generates YAML frontmatter for easy integration with Obsidian, Zettlr, Pandoc, etc.
- Auto-generates filenames: `YYYY-author-title-in-kebab-case.md`
- Detects paywalled articles and warns you, still extracting metadata and abstract

## Installation

Requires Python 3.10+. Install with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/albertclerigues/sd2md.git
```

Or run without installing:

```bash
uvx --from git+https://github.com/albertclerigues/sd2md.git sd2md <url>
```

## Usage

```bash
# Convert an article (saves to auto-generated filename in current directory)
sd2md https://www.sciencedirect.com/science/article/pii/S1053811911012328

# Specify output file
sd2md https://www.sciencedirect.com/science/article/pii/S1053811911012328 -o paper.md

# Print to stdout
sd2md https://www.sciencedirect.com/science/article/pii/S1053811911012328 --stdout
```

### Output format

The generated Markdown file includes YAML frontmatter with `title`, `authors`, `journal`, `year`, `doi`, `volume`, `issue`, `pages`, `issn`, `url`, `keywords`, `date_retrieved`, and `complete`, followed by the article abstract and body content.

### Paywalled articles

If the article is behind a paywall, `sd2md` will still extract all available metadata and the abstract, and mark the output with `complete: false` in the frontmatter. A warning is printed to stderr.

## Planned features

- Local figure/image download
- MathML to LaTeX equation conversion
- Batch processing (multiple URLs)
- Table rendering to GFM Markdown
