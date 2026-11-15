"""PubMed listing of one person's papers for the public-track harvest (docs/track-s-extraction.md §2).
Same shape as scrape.list_arxiv_author, for researchers who publish in journals rather than on arXiv.
NCBI E-utilities without a key allow 3 requests a second."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .scrape import UA, author_position

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _get(path, **params):
    time.sleep(0.4)
    url = EUTILS + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def _date(article):
    # The electronic date, else the day PubMed listed it: a journal's print issue can trail by months.
    d = article.find(".//ArticleDate")
    if d is None:
        d = article.find(".//PubMedPubDate[@PubStatus='pubmed']")
    if d is None:
        return ""
    return "{:04d}-{:02d}-{:02d}".format(*(int(d.findtext(k)) for k in ("Year", "Month", "Day")))


def parse_pubmed(xml_bytes, name):
    """{URL: {authors, published, title}} for the efetch articles that list `name` as an author.
    The URL is the PMC full text when there is one, else the DOI, else the PubMed page."""
    out = {}
    for a in ET.fromstring(xml_bytes).iter("PubmedArticle"):
        authors = [" ".join(filter(None, (au.findtext("ForeName"), au.findtext("LastName"))))
                   or au.findtext("CollectiveName", "") for au in a.findall(".//AuthorList/Author")]
        if not author_position(authors, name):
            continue
        ids = {i.get("IdType"): (i.text or "").strip() for i in a.findall("PubmedData/ArticleIdList/ArticleId")}
        url = (f"https://pmc.ncbi.nlm.nih.gov/articles/{ids['pmc']}/" if ids.get("pmc")
               else f"https://doi.org/{ids['doi']}" if ids.get("doi")
               else f"https://pubmed.ncbi.nlm.nih.gov/{ids['pubmed']}/")
        title = " ".join("".join(a.find(".//ArticleTitle").itertext()).split())
        out[url] = {"authors": authors, "published": _date(a), "title": title}
    return out


def list_pubmed_author(name, start, end):
    """Every PubMed paper listing `name` published between start and end (YYYY-MM-DD). Searches the
    surname and keeps papers whose author list names her, as list_arxiv_author does."""
    ids = json.loads(_get("esearch.fcgi", db="pubmed", term=f"{name.split()[-1]}[Author]",
                                        mindate=start.replace("-", "/"), maxdate=end.replace("-", "/"),
                                        datetype="pdat", retmax=10000, retmode="json"))["esearchresult"]["idlist"]
    out = {}
    for i in range(0, len(ids), 200):
        out.update(parse_pubmed(_get("efetch.fcgi", db="pubmed", id=",".join(ids[i:i + 200]), retmode="xml"), name))
    return out
