import argparse
import re
import time
import gzip
import hashlib
import os
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup

try:
    import psycopg
except Exception: 
    psycopg = None

HEADERS = {
    "User-Agent": "AI4Juris-DGSI-Scraper/1.0"
}

DB_DSN = os.getenv("DGSISCRAPER_DB_DSN")  # e.g. postgresql://dgsi:dgsi@localhost:5433/dgsi
DB_ENABLED = bool(DB_DSN)


def db_connect():
    """Return a psycopg connection or None if DB is disabled/unavailable."""
    if not DB_ENABLED:
        return None
    if psycopg is None:
        raise RuntimeError(
            "DGSISCRAPER_DB_DSN is set but psycopg is not installed. Install with: pip install 'psycopg[binary]'"
        )
    return psycopg.connect(DB_DSN)


def db_ensure_schema(conn) -> None:
    """Create table/indexes if they do not exist."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dgsi_documents (
              id BIGSERIAL PRIMARY KEY,
              source TEXT NOT NULL,
              base_name TEXT NOT NULL,
              url TEXT NOT NULL UNIQUE,
              processo TEXT,
              sessao_date TEXT,
              relator TEXT,
              descritores TEXT[] NOT NULL DEFAULT '{}',
              text_sha256 TEXT NOT NULL,
              text_plain TEXT NOT NULL,
              text_gzip BYTEA NOT NULL,
              extra JSONB NOT NULL DEFAULT '{}'::jsonb,
              fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS dgsi_documents_source_idx ON dgsi_documents(source);")
        cur.execute("CREATE INDEX IF NOT EXISTS dgsi_documents_sessao_date_idx ON dgsi_documents(sessao_date);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS dgsi_documents_descritores_gin_idx ON dgsi_documents USING GIN (descritores);"
        )
    conn.commit()

def db_count_source(conn, source: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM dgsi_documents WHERE source = %s;", (source,))
        return int(cur.fetchone()[0])

def parse_source_limits(spec: str | None) -> dict[str, int]:
    """Parse a string like 'dgsi_stj=1700,dgsi_sta=500' into a dict."""
    if not spec:
        return {}
    out: dict[str, int] = {}
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    for p in parts:
        if "=" not in p:
            raise ValueError(f"Invalid --source-limits entry (missing '='): {p!r}")
        k, v = p.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise ValueError(f"Invalid --source-limits entry (empty source): {p!r}")
        out[k] = int(v)
    return out

def db_upsert_doc(conn, rec: "DocRecord", text_hash: str, text_gz: bytes) -> bool:
    """Insert/update a document row."""
    extra_json = json.dumps(rec.extra, ensure_ascii=False)
    fetched_at = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dgsi_documents (
            source, base_name, url, processo, sessao_date, relator,
            descritores, text_sha256, text_plain, text_gzip, extra, fetched_at
            ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s::jsonb, %s
            )
            ON CONFLICT (url) DO UPDATE SET
            source = EXCLUDED.source,
            base_name = EXCLUDED.base_name,
            processo = EXCLUDED.processo,
            sessao_date = EXCLUDED.sessao_date,
            relator = EXCLUDED.relator,
            descritores = EXCLUDED.descritores,
            text_sha256 = EXCLUDED.text_sha256,
            text_plain = EXCLUDED.text_plain,
            text_gzip = EXCLUDED.text_gzip,
            extra = EXCLUDED.extra,
            fetched_at = EXCLUDED.fetched_at
            RETURNING (xmax = 0) AS inserted;
            """,
            (
                rec.source,
                rec.base_name,
                rec.url,
                rec.processo,
                rec.sessao_date,
                rec.relator,
                rec.descritores,
                text_hash,
                rec.text_plain,
                text_gz,
                extra_json,
                fetched_at,
            ),
        )
        inserted = bool(cur.fetchone()[0])
    conn.commit()
    return inserted


@dataclass
class DocRecord:
    source: str
    base_name: str
    url: str
    processo: str | None
    sessao_date: str | None
    relator: str | None
    descritores: list[str]
    text_plain: str
    extra: dict[str, str]


def fetch(url: str, timeout=30) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # remove noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # preserve line breaks a bit
    for br in soup.find_all("br"):
        br.replace_with("\n")

    text = soup.get_text(separator="\n")
    # normalize whitespace
    text = re.sub(r"\r", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_listing_page(html: str, min_doc_links: int = 3) -> bool:
    """True if the page looks like a listing/view page (not an individual OpenDocument).

    DGSI/Notes databases vary a lot across sources. The most reliable common signal is:
    a listing page contains multiple links to `?OpenDocument`.
    """
    soup = BeautifulSoup(html, "lxml")
    doc_links = soup.select('a[href*="?OpenDocument"], a[href*="&OpenDocument"]')
    return len(doc_links) >= min_doc_links


def extract_doc_links(listing_html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "lxml")
    links: list[str] = []

    # Strictly collect only OpenDocument links (works across DGSI sources)
    for a in soup.select('a[href*="?OpenDocument"], a[href*="&OpenDocument"]'):
        href = a.get("href")
        if not href:
            continue
        links.append(urljoin(base_url, href))

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_next_page_url(listing_html: str, current_url: str, page_step: int = 30) -> str | None:
    soup = BeautifulSoup(listing_html, "lxml")

    # 1) Prefer explicit navigation links
    for a in soup.select("a[href]"):
        txt = a.get_text(strip=True).lower()
        if txt in {"seguinte", "next", ">", "»"}:
            href = a.get("href")
            if href:
                return urljoin(current_url, href)

    # 2) Fallback: increment Start= in current URL (Notes view pagination)
    parsed = urlparse(current_url)
    qs = parse_qs(parsed.query)
    if "Start" in qs and qs["Start"]:
        try:
            start = int(qs["Start"][0])
            qs["Start"] = [str(start + page_step)]
            new_query = urlencode(qs, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except ValueError:
            return None

    return None


def try_fetch_texto_integral(doc_html: str, doc_url: str) -> str | None:
    """Some DGSI pages show only metadata + a collapsible "Texto Integral" section.

    In some sources (notably STA), the "Texto Integral" is loaded via a Notes-style
    `ExpandSection=` link (often the triangle control), and the anchor text may NOT
    contain "Texto Integral".

    Strategy:
      1) Prefer explicit links whose text contains "Texto Integral".
      2) Otherwise, try any links containing `ExpandSection` / `OpenSection`.
      3) If still nothing, brute-force a few common `&ExpandSection=N` URLs.

    Returns fetched HTML or None.
    """
    soup = BeautifulSoup(doc_html, "lxml")

    candidates: list[str] = []

    # 1) Explicit clickable link whose visible text contains "Texto Integral"
    for a in soup.select("a[href]"):
        txt = a.get_text(" ", strip=True).lower()
        href = a.get("href")
        if not href:
            continue
        href = href.strip()
        if "texto integral" in txt:
            if href.startswith("javascript:") or href.startswith("#"):
                continue
            full_url = urljoin(doc_url, href)
            if full_url != doc_url:
                candidates.append(full_url)

    # 2) Notes-style expandable sections (triangle/controls) often use ExpandSection
    if not candidates:
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            hlow = href.lower()
            if "expandsection" in hlow or "opensection" in hlow:
                if href.startswith("javascript:") or href.startswith("#"):
                    continue
                full_url = urljoin(doc_url, href)
                if full_url != doc_url:
                    candidates.append(full_url)

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    # 3) Brute-force common ExpandSection variants when the site doesn't expose a clear link
    if not deduped:
        # If url already has ?OpenDocument, appending &ExpandSection=N is typical
        for n in (1, 2, 3, 4, 5):
            if "?" in doc_url:
                brute = f"{doc_url}&ExpandSection={n}"
            else:
                brute = f"{doc_url}?OpenDocument&ExpandSection={n}"
            deduped.append(brute)

    # Try candidates; accept the first one that yields a materially larger text body
    base_text_len = len(html_to_text(doc_html))
    for full_url in deduped[:5]:
        try:
            extra_html = fetch(full_url)
        except Exception:
            continue

        extra_len = len(html_to_text(extra_html))
        # Heuristic: must add meaningful content
        if extra_len > base_text_len + 1500:
            return extra_html

    return None


def parse_document(doc_html: str, source: str, base_name: str, url: str) -> DocRecord:
    soup = BeautifulSoup(doc_html, "lxml")
    text_plain = html_to_text(doc_html)

    # Get a stable text version for regex-based label extraction
    full_text = soup.get_text("\n", strip=True)

    def find_field_any(labels: list[str]) -> str | None:
        for label in labels:
            # Match patterns like "Label: value" (case-insensitive)
            m = re.search(rf"{re.escape(label)}\s*:\s*(.+)", full_text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    # Common fields across many DGSI sources
    processo = find_field_any(["Processo", "Nº Processo", "N.º Processo"])
    relator = find_field_any(["Relator", "Juiz Relator"])

    # Session/date varies by source
    sessao_date = find_field_any([
        "Sessão",
        "Data",
        "Data do Acórdão",
        "Data do Acordão",
        "Data Decisão",
        "Data da Decisão",
        "Data da sentença",
    ])

    # Descritores can appear as a field; if not, keep empty list
    descritores_raw = find_field_any(["Descritor", "Descritores", "DESCRITOR", "DESCRITORES"]) or ""
    descritores = [d.strip() for d in re.split(r"[;\n,]+", descritores_raw) if d.strip()]

    # Extra fields for irregular sources
    extra: dict[str, str] = {}

    # Try to capture some known alternative labels if present
    for label in [
        "Réu", "Reu", "CONTRATO", "Contrato", "Data Decisão", "Data da Decisão",
        "Assunto", "Matéria", "Área", "Decisão", "Sumário", "Sumario",
        "Tribunal", "Nº Convencional", "N.º Convencional", "Nº do Documento", "N.º do Documento",
    ]:
        val = find_field_any([label])
        if val:
            extra[label] = val

    return DocRecord(
        source=source,
        base_name=base_name,
        url=url,
        processo=processo,
        sessao_date=sessao_date,
        relator=relator,
        descritores=descritores,
        text_plain=text_plain,
        extra=extra,
    )


def gzip_bytes(s: str) -> bytes:
    return gzip.compress(s.encode("utf-8"))


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def crawl_base(
    seed_url: str,
    source: str,
    base_name: str,
    max_pages: int | None = None,
    max_docs_per_page: int | None = None,
    max_docs_total: int | None = None,
    preview_chars: int = 500,
    save_samples_dir: str | None = None,
    db_conn=None,
):
    url = seed_url
    pages = 0
    processed_total = 0

    # If DB is enabled, resume based on what is already stored for this source.
    if db_conn is not None and max_docs_total is not None:
        try:
            processed_total = db_count_source(db_conn, source)
            if processed_total >= max_docs_total:
                print(f"[DONE] {source}: already have {processed_total} docs (limit={max_docs_total}).")
                return
        except Exception as e:
            print(f"[WARN] Failed to count existing docs for {source}: {e}")
            processed_total = 0
    while url:
        html = fetch(url)
        if not is_listing_page(html):
            print(f"[SKIP] Not a table listing page: {url}")
            return

        doc_links = extract_doc_links(html, base_url=url)
        if max_docs_per_page is not None:
            doc_links = doc_links[:max_docs_per_page]

        for doc_url in doc_links:
            if max_docs_total is not None and processed_total >= max_docs_total:
                break
            try:
                doc_html = fetch(doc_url)

                # Some sources load the "Texto Integral" behind a separate link/expand.
                initial_text = html_to_text(doc_html)
                if re.search(r"\btexto\s+integral\b", initial_text, re.IGNORECASE):
                    extra_html = try_fetch_texto_integral(doc_html, doc_url)
                    if extra_html:
                        # The expanded/section URL typically returns the full page again
                        # (metadata + integral text). Replacing avoids duplicating content.
                        doc_html = extra_html

                rec = parse_document(doc_html, source, base_name, doc_url)
                text_hash = sha256_hex(rec.text_plain)
                text_gz = gzip_bytes(rec.text_plain)

                inserted = True
                if db_conn is not None:
                    inserted = db_upsert_doc(db_conn, rec, text_hash, text_gz)

                # Count only NEW docs towards the limit (helps reruns/resume)
                if inserted:
                    processed_total += 1

                if save_samples_dir is not None:
                    os.makedirs(save_samples_dir, exist_ok=True)
                    safe_source = re.sub(r"[^a-zA-Z0-9_-]+", "_", source)
                    path = os.path.join(save_samples_dir, f"{safe_source}_{text_hash}.txt")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(rec.text_plain)

                snippet = rec.text_plain[:preview_chars].replace("\n", " ")
                print(
                    "[DOC]",
                    source,
                    rec.processo,
                    rec.sessao_date,
                    rec.relator,
                    f"descr={len(rec.descritores)}",
                    f"len={len(rec.text_plain)}",
                    doc_url,
                )
                print("[TXT_PREVIEW]", snippet)

                time.sleep(0.6)
            except Exception as e:
                print("[ERR]", doc_url, e)
        
        if max_docs_total is not None and processed_total >= max_docs_total:
            print(f"[DONE] {source}: reached limit {max_docs_total}.")
            break
        url = extract_next_page_url(html, current_url=url)
        pages += 1
        if max_pages and pages >= max_pages:
            break

        time.sleep(0.8)


SOURCES = [
    {
        "source": "dgsi_stj",
        "base_name": "Acórdãos do Supremo Tribunal de Justiça",
        "seed_url": "https://www.dgsi.pt/jstj.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_tc_ate_1998",
        "base_name": "Acórdãos do Tribunal Constitucional (até 1998)",
        "seed_url": "https://www.dgsi.pt/atco1.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_sta",
        "base_name": "Acórdãos do Supremo Tribunal Administrativo",
        "seed_url": "https://www.dgsi.pt/jsta.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_jcon",
        "base_name": "Acórdãos do Tribunal dos Conflitos",
        "seed_url": "https://www.dgsi.pt/jcon.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_trp",
        "base_name": "Acórdãos do Tribunal da Relação do Porto",
        "seed_url": "https://www.dgsi.pt/jtrp.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_trl",
        "base_name": "Acórdãos do Tribunal da Relação de Lisboa",
        "seed_url": "https://www.dgsi.pt/jtrl.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_trc",
        "base_name": "Acórdãos do Tribunal da Relação de Coimbra",
        "seed_url": "https://www.dgsi.pt/jtrc.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_trg",
        "base_name": "Acórdãos do Tribunal da Relação de Guimarães",
        "seed_url": "https://www.dgsi.pt/jtrg.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_tre",
        "base_name": "Acórdãos do Tribunal da Relação de Évora",
        "seed_url": "https://www.dgsi.pt/jtre.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_tca_sul",
        "base_name": "Acórdãos do Tribunal Central Administrativo Sul",
        "seed_url": "https://www.dgsi.pt/jtca.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_tca_norte",
        "base_name": "Acórdãos do Tribunal Central Administrativo Norte",
        "seed_url": "https://www.dgsi.pt/jtcn.nsf?OpenDatabase",
    },
    {
        "source": "dgsi_jpaz",
        "base_name": "Jurisprudência dos Julgados de Paz",
        "seed_url": "https://www.dgsi.pt/cajp.nsf/954f0ce6ad9dd8b980256b5f003fa814?OpenView",
    },
    {
        "source": "dgsi_clausulas_abusivas",
        "base_name": "Registo de Cláusulas Contratuais Abusivas julgadas pelos tribunais",
        "seed_url": "https://www.dgsi.pt/jdgpj.nsf?OpenDatabase",
    },
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DGSI scraper (stores docs in Postgres if DGSISCRAPER_DB_DSN is set)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max listing pages per source (default: no limit)")
    parser.add_argument("--max-docs-per-page", type=int, default=None, help="Max docs per listing page (default: no limit)")
    parser.add_argument("--preview-chars", type=int, default=600, help="Preview characters printed per document")
    parser.add_argument(
        "--save-samples-dir",
        type=str,
        default=None,
        help="Optional directory to also save .txt samples (default: disabled)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=None,
        help="Comma-separated source ids to crawl (e.g. dgsi_sta,dgsi_trl). Default: all sources.",
    )
    parser.add_argument(
        "--source-limits",
        type=str,
        default=None,
        help="Comma-separated per-source total limits, e.g. 'dgsi_stj=1700,dgsi_sta=1700'.",
    )
    args = parser.parse_args()
    source_limits = parse_source_limits(args.source_limits)
    selected = SOURCES
    if args.sources:
        wanted = {s.strip() for s in args.sources.split(",") if s.strip()}
        selected = [s for s in SOURCES if s["source"] in wanted]
        missing = wanted - {s["source"] for s in selected}
        if missing:
            print(f"[WARN] Unknown sources ignored: {', '.join(sorted(missing))}")

    # Optional Postgres
    conn = None
    if DB_ENABLED:
        conn = db_connect()
        db_ensure_schema(conn)

    try:
        for s in selected:
            print(f"\n=== Crawling {s['source']} | {s['base_name']} ===")
            crawl_base(
                seed_url=s["seed_url"],
                source=s["source"],
                base_name=s["base_name"],
                max_pages=args.max_pages,
                max_docs_per_page=args.max_docs_per_page,
                max_docs_total=source_limits.get(s["source"]),
                preview_chars=args.preview_chars,
                save_samples_dir=args.save_samples_dir,
                db_conn=conn,
            )
    finally:
        if conn is not None:
            conn.close()