import json
import re

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30,
    )


def _extract_preloaded_state(html: str) -> dict:
    """Extract __PRELOADED_STATE__ JSON from page HTML."""
    match = re.search(
        r"window\.__PRELOADED_STATE__\s*=\s*({.*?});\s*</script>",
        html,
        re.DOTALL,
    )
    if not match:
        return {}
    return json.loads(match.group(1))


def fetch_article(url: str) -> tuple[str, dict, dict | None]:
    """Fetch article page and body JSON if entitled.

    Returns (html, preloaded_state, body_json_or_None).
    """
    url = url.replace("/article/abs/", "/article/")

    with _make_client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

        state = _extract_preloaded_state(html)
        article = state.get("article", {})
        pii = article.get("pii", "")
        token = article.get("entitledToken")

        body_json = None
        if pii and token and article.get("hasBody"):
            body_resp = client.get(
                f"https://www.sciencedirect.com/sdfe/arp/pii/{pii}/body",
                params={"entitledToken": token},
            )
            if body_resp.status_code == 200:
                body_json = body_resp.json()

    return html, state, body_json
