from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ArticleMetadata:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: int = 0
    doi: str = ""
    volume: str = ""
    issue: str = ""
    first_page: str = ""
    last_page: str = ""
    issn: str = ""
    pdf_url: str = ""
    url: str = ""
    keywords: list[str] = field(default_factory=list)

    @property
    def pages(self) -> str:
        if self.first_page and self.last_page:
            return f"{self.first_page}-{self.last_page}"
        return self.first_page or ""

    @property
    def first_author_surname(self) -> str:
        if not self.authors:
            return "unknown"
        # Authors stored as "Last, First"
        return self.authors[0].split(",")[0].strip().lower()


def extract_metadata(html: str, url: str, state: dict | None = None) -> ArticleMetadata:
    soup = BeautifulSoup(html, "html.parser")
    meta = ArticleMetadata(url=url)

    def get(name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        return tag["content"].strip() if tag and tag.get("content") else ""

    def get_all(name: str) -> list[str]:
        return [
            t["content"].strip()
            for t in soup.find_all("meta", attrs={"name": name})
            if t.get("content")
        ]

    meta.title = get("citation_title")
    meta.authors = get_all("citation_author")

    # Fallback: extract authors from HTML if no citation_author meta tags
    if not meta.authors:
        author_group = soup.find("div", class_="author-group")
        if author_group:
            for span in author_group.find_all(
                "span", class_="react-xocs-alternative-link"
            ):
                gn = span.find("span", class_="given-name")
                sn = span.find("span", class_="surname")
                if gn and sn:
                    meta.authors.append(
                        f"{sn.get_text(strip=True)}, {gn.get_text(strip=True)}"
                    )

    meta.journal = get("citation_journal_title")
    meta.doi = get("citation_doi")
    meta.volume = get("citation_volume")
    meta.issue = get("citation_issue")
    meta.first_page = get("citation_firstpage")
    meta.last_page = get("citation_lastpage")
    meta.issn = get("citation_issn")
    meta.pdf_url = get("citation_pdf_url")

    # Year from citation_publication_date (format: YYYY/MM/DD)
    pub_date = get("citation_publication_date")
    if pub_date:
        try:
            meta.year = int(pub_date.split("/")[0])
        except ValueError:
            pass

    # Keywords: try preloaded state first, then HTML fallback
    if state:
        meta.keywords = _extract_keywords_from_state(state)
    if not meta.keywords:
        kw_div = soup.find("div", class_="Keywords") or soup.find(
            "div", class_="keywords-section"
        )
        if kw_div:
            meta.keywords = [
                kw.get_text(strip=True)
                for kw in kw_div.find_all("div", class_="keyword")
                if kw.get_text(strip=True)
            ]

    return meta


def _extract_keywords_from_state(state: dict) -> list[str]:
    """Extract keywords from __PRELOADED_STATE__ JSON."""
    cci = state.get("combinedContentItems", {})
    keywords = []
    for item in cci.get("content", []):
        if item.get("#name") == "keywords":
            for kw_group in item.get("$$", []):
                if kw_group.get("#name") == "keywords":
                    for child in kw_group.get("$$", []):
                        if child.get("#name") == "keyword":
                            text = _collect_text(child)
                            if text:
                                keywords.append(text)
    return keywords


def _collect_text(node: dict) -> str:
    """Recursively collect text from a JSON node tree."""
    text = node.get("_", "")
    for child in node.get("$$", []):
        text += _collect_text(child)
    return text.strip()


def is_paywalled(state: dict) -> bool:
    """Check if article body is behind paywall using preloaded state."""
    article = state.get("article", {})
    return not article.get("entitledToken")
