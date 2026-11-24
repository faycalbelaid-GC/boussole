"""Collecteur Boussole — tourne chaque nuit sur GitHub Actions, gratuitement.

Il visite les sources de sources.json (fils RSS et pages publiques), garde les
vraies offres (doctorat, master, postdoc, bourses), les classe par règles
(niveau, domaine, pays, date limite, financement) et met à jour
site/data/offres.json, que le site affiche. Aucune IA payante.

Lancer à la main :  python collector/collect.py
"""
from __future__ import annotations

import datetime as dt
import email
import hashlib
import imaplib
import json
import os
import re
import sys
import time
import urllib.robotparser
from email.header import decode_header
from pathlib import Path
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"
OFFERS = DATA / "offres.json"
META = DATA / "meta.json"
SOURCES = Path(__file__).resolve().parent / "sources.json"

UA = "BoussoleBot/1.0 (+https://github.com/; collecte d'offres académiques publiques, 1 passage par nuit)"
TODAY = dt.date.today()
PAUSE = 2.0          # secondes entre deux pages d'un même site
STALE_DAYS = 45      # une offre sans date limite disparaît si on ne la revoit pas pendant 45 jours
MAX_OFFERS = 4000

# ---------------------------------------------------------------- classement par règles
FIELDS = {  # domaine du site -> mots-clés (anglais et français), du plus précis au plus large
    "Biomécanique": ["biomechanic", "biomécani", "gait", "musculoskeletal model"],
    "Physiologie de l'exercice": ["exercise physiology", "physiologie de l'exercice", "thermoregulation", "heat adaptation"],
    "Psychologie du sport": ["sport psychology", "psychologie du sport"],
    "Management du sport": ["sport management", "sports management", "management du sport"],
    "Nutrition du sport": ["sports nutrition", "nutrition du sport"],
    "STAPS & activité physique adaptée": ["staps", "physical activity", "activité physique"],
    "Sciences du sport et de l'exercice": ["sport", "exercise science", "athlet", "rugby", "football", "running", "olympic"],
    "Intelligence artificielle": ["artificial intelligence", "machine learning", "deep learning", "computer vision", "reinforcement learning", " ai ", "ai-", "llm", "intelligence artificielle", "apprentissage automatique"],
    "Cybersécurité": ["cyber", "security", "privacy", "sécurité informatique"],
    "Science des données": ["data science", "big data", "data analytics", "science des données"],
    "Informatique quantique": ["quantum comput", "quantum information"],
    "Informatique": ["computer science", "software", "computing", "informatique", "algorithm"],
    "Mathématiques": ["mathemat", "mathémat"],
    "Statistique": ["statistic", "biostatistic"],
    "Génie civil": ["civil engineering", "génie civil", "concrete", "béton", "structural engineering", "geotechn", "construction material"],
    "Génie mécanique": ["mechanical engineering", "génie mécanique", "fluid", "thermal", "composite", "tribolog", "welding"],
    "Génie électrique & énergie": ["electrical engineering", "power system", "power electronic", "grid", "électrique", "battery", "batteries", "hvdc"],
    "Énergies renouvelables": ["renewable", "energy system", "energy", "solar", "wind energy", "hydrogen", "net zero", "énergies renouvelables"],
    "Génie aérospatial": ["aerospace", "aeronaut", "aérospatial", "satellite"],
    "Génie chimique & procédés": ["chemical engineering", "process engineering", "génie chimique", "catalys"],
    "Génie biomédical": ["biomedical engineering", "medical device", "génie biomédical", "tissue engineering"],
    "Science des matériaux": ["materials science", "material science", "matériaux", "nanomaterial", "polymer", "alloy"],
    "Robotique": ["robot"],
    "Télécommunications": ["telecommunication", "wireless", "5g", "6g", "optical communication", "antenna"],
    "Transport & logistique": ["transport", "logistic", "mobility"],
    "Physique": ["physics", "physique", "photonic", "optics", "quantum"],
    "Chimie": ["chemistry", "chimie", "chemical"],
    "Astronomie & astrophysique": ["astronom", "astrophys", "cosmolog", "space weather"],
    "Sciences de la Terre & climat": ["climate", "atmospher", "hydrolog", "earth science", "geoscience", "climat"],
    "Géologie": ["geolog", "géolog"],
    "Océanographie & sciences marines": ["ocean", "marine", "coastal", "océan"],
    "Écologie & biodiversité": ["ecology", "biodiversity", "écologie", "conservation"],
    "Sciences de l'environnement": ["environment", "sustainab", "circular economy", "pollution", "environnement", "wastewater"],
    "Neurosciences": ["neuroscien", "neuro", "brain"],
    "Immunologie": ["immunolog", "immune"],
    "Génétique & génomique": ["genetic", "genom", "génétique"],
    "Microbiologie": ["microbio", "bacteria", "antimicrobial", "virus", "virolog"],
    "Biochimie & biologie moléculaire": ["biochem", "molecular biology", "protein", "biologie moléculaire"],
    "Psychiatrie & santé mentale": ["mental health", "psychiatr", "santé mentale"],
    "Santé publique": ["public health", "epidemiolog", "santé publique", "health services"],
    "Pharmacie & pharmacologie": ["pharmac", "drug discovery"],
    "Soins infirmiers": ["nursing", "infirmi"],
    "Odontologie": ["dental", "dentist"],
    "Sciences vétérinaires": ["veterinar", "vétérinaire", "animal health"],
    "Nutrition & alimentation": ["nutrition", "diet", "micronutrient"],
    "Kinésithérapie & réadaptation": ["physiotherap", "rehabilitation", "réadaptation", "kinésithérap"],
    "Médecine & sciences médicales": ["medicine", "medical", "clinical", "cancer", "oncolog", "cardio", "médecine", "health"],
    "Biologie & sciences de la vie": ["biology", "life science", "biolog", "cell", "plant"],
    "Agronomie & agriculture": ["agricultur", "agronom", "crop", "soil", "farming"],
    "Sciences alimentaires": ["food science", "food"],
    "Sciences forestières": ["forest"],
    "Psychologie": ["psycholog"],
    "Sociologie": ["sociolog", "social science", "social policy"],
    "Sciences politiques & relations internationales": ["political", "international relations", "politique", "governance"],
    "Anthropologie": ["anthropolog"],
    "Géographie": ["geograph", "géograph", "urban studies"],
    "Histoire": ["history", "histoire", "historical"],
    "Philosophie": ["philosoph"],
    "Sciences de l'éducation": ["education", "éducation", "teaching", "pedagog"],
    "Linguistique & langues": ["linguist", "language", "langue"],
    "Lettres & humanités": ["humanities", "literature", "littérature", "lettres", "classics"],
    "Communication & médias": ["media", "communication", "journalism"],
    "Études du développement": ["development studies", "international development"],
    "Archéologie": ["archaeolog", "archéolog"],
    "Théologie & sciences religieuses": ["theolog", "religio"],
    "Économie": ["economic", "économie", "econometric"],
    "Finance": ["finance", "financial", "banking"],
    "Comptabilité": ["accounting", "comptab"],
    "Marketing": ["marketing"],
    "Gestion & management": ["management", "business", "gestion", "mba", "entrepreneur"],
    "Droit": ["law", "legal", "droit", "llm"],
    "Tourisme & hôtellerie": ["tourism", "hospitality", "tourisme"],
    "Politiques publiques": ["public policy", "politiques publiques"],
    "Architecture & urbanisme": ["architect", "urban planning", "urbanisme", "placemaking"],
    "Arts & design": ["design", "art ", "arts", "fine art"],
    "Musique": ["music", "musique"],
    "Cinéma & audiovisuel": ["film", "cinema", "cinéma"],
}

COUNTRIES = {  # nom (anglais/français, minuscules) -> pays en français
    "united kingdom": "Royaume-Uni", " uk": "Royaume-Uni", "england": "Royaume-Uni", "scotland": "Royaume-Uni", "wales": "Royaume-Uni",
    "london": "Royaume-Uni", "royaume-uni": "Royaume-Uni", "france": "France", "paris": "France", "germany": "Allemagne", "allemagne": "Allemagne",
    "netherlands": "Pays-Bas", "pays-bas": "Pays-Bas", "belgium": "Belgique", "belgique": "Belgique", "switzerland": "Suisse", "suisse": "Suisse",
    "zürich": "Suisse", "zurich": "Suisse", "sweden": "Suède", "suède": "Suède", "norway": "Norvège", "denmark": "Danemark", "finland": "Finlande",
    "ireland": "Irlande", "irlande": "Irlande", "italy": "Italie", "italie": "Italie", "spain": "Espagne", "espagne": "Espagne", "portugal": "Portugal",
    "austria": "Autriche", "luxembourg": "Luxembourg", "poland": "Pologne", "czech": "Tchéquie", "canada": "Canada", "united states": "États-Unis",
    " usa": "États-Unis", "u.s.": "États-Unis", "australia": "Australie", "new zealand": "Nouvelle-Zélande", "japan": "Japon", "korea": "Corée du Sud",
    "china": "Chine", "singapore": "Singapour", "hong kong": "Hong Kong", "israel": "Israël", "emirates": "Émirats arabes unis", "qatar": "Qatar",
    "saudi": "Arabie saoudite", "south africa": "Afrique du Sud", "morocco": "Maroc", "turkey": "Turquie", "brazil": "Brésil", "estonia": "Estonie",
    "greece": "Grèce", "hungary": "Hongrie", "iceland": "Islande", "europe": "Europe",
}

KEEP = re.compile(r"\b(ph\.?d|doctoral|doctorate|doctorat|thèse|these\b|studentship|scholarship|bourse|fellowship|postdoc|post-doc|post-doctoral|master'?s?|msc|mba|llm|graduate)\b", re.I)
DROP = re.compile(r"\b(lecturer|professor of|technician|administrator|manager|assistant professor|associate professor|head of|director|webinar|newsletter)\b", re.I)

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTHS.update({"janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6, "juil": 7, "août": 8, "aout": 8, "sept": 9, "déc": 12})
DEADLINE_KW = r"(?:deadline|closing date|closes|close date|apply by|applications? (?:due|close)|date limite|clôture|until|before)"
DATE_RES = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-zéû]{3,9})\.?,?\s+(\d{4})"),
    re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"),
    re.compile(r"(\d{1,2})\s+([A-Za-zéû]{3,9})\b(?!\s*\d)"),
]


def month_num(s: str) -> int | None:
    s = s.lower().strip(".")
    for k, v in MONTHS.items():
        if s.startswith(k):
            return v
    return None


def parse_date(txt: str) -> str:
    """Cherche une date limite près d'un mot-clé (deadline, closes, date limite…)."""
    low = txt.replace("\xa0", " ")
    for m in re.finditer(DEADLINE_KW, low, re.I):
        window = low[m.end(): m.end() + 60]
        for i, rx in enumerate(DATE_RES):
            d = rx.search(window)
            if not d:
                continue
            try:
                if i == 0:
                    y, mo, da = int(d[1]), int(d[2]), int(d[3])
                elif i == 1:
                    da, mo, y = int(d[1]), month_num(d[2]), int(d[3])
                elif i == 2:
                    mo, da, y = month_num(d[1]), int(d[2]), int(d[3])
                else:
                    da, mo = int(d[1]), month_num(d[2])
                    if not mo:
                        continue
                    y = TODAY.year if (mo, da) >= (TODAY.month, TODAY.day) else TODAY.year + 1
                if not mo:
                    continue
                return dt.date(y, mo, da).isoformat()
            except (ValueError, TypeError):
                continue
    return ""


def level_of(txt: str) -> str:
    t = txt.lower()
    if re.search(r"post-?doc|post-doctoral|postdoctoral", t):
        return "Postdoc"
    if re.search(r"\bph\.?d|doctoral|doctorate|doctorat|thèse|studentship", t):
        return "PhD"
    if re.search(r"\bmaster|\bmsc\b|\bmba\b|\bllm\b|\bma\b", t):
        return "Master"
    if re.search(r"bachelor|undergraduate|licence", t):
        return "Licence"
    return ""


def field_of(txt: str) -> str:
    t = " " + txt.lower() + " "
    for f, kws in FIELDS.items():
        if any(k in t for k in kws):
            return f
    return "Pluridisciplinaire"


def country_of(txt: str, default: str = "") -> str:
    t = " " + txt.lower() + " "
    for k, v in COUNTRIES.items():
        if k in t:
            return v
    return default


def funding_of(txt: str) -> str:
    t = txt.lower()
    if "self-funded" in t or "self funded" in t or "autofinanc" in t:
        return "Autofinancé"
    if re.search(r"fully[- ]funded|full scholarship|entièrement financ", t):
        return "Entièrement financé"
    if re.search(r"competition funded|competitively funded", t):
        return "Financement sur concours"
    if re.search(r"stipend|funded|salary|tuition fee|financ|allocation|£\s?\d|€\s?\d|\$\s?\d", t):
        return "Financé"
    return ""


def kind_of(txt: str, default: str) -> str:
    if default in ("position", "scholarship"):
        return default
    t = txt.lower()
    if re.search(r"scholarship|bourse|fellowship|grant|award", t) and not re.search(r"position|studentship|vacanc|recruit", t):
        return "scholarship"
    return "position"


def guess_institution(lines: list[str], title: str) -> str:
    for ln in lines:
        if ln and ln != title and len(ln) < 90 and re.search(r"universit|college|institut|school|école|ecole|eth |epfl|kth|max planck|centre|center|laborator|academy|hochschule|politecnico", ln, re.I):
            return ln.strip(" ·-|")
    return ""


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def make(src: dict, title: str, url: str, context: str, institution: str = "", date_hint: str = "") -> dict | None:
    title = clean(title)[:220]
    if len(title) < 8:
        return None
    whole = f"{title} {context}"
    if not KEEP.search(whole) or DROP.search(title):
        return None
    dl = parse_date(context) or parse_date(title) or date_hint
    if dl and dl < TODAY.isoformat():
        return None  # déjà clôturée
    return {
        "id": hashlib.sha1(url.encode()).hexdigest()[:12],
        "k": kind_of(whole, src.get("kind", "auto")),
        "t": title,
        "u": clean(institution or src.get("institution", ""))[:120],
        "c": country_of(whole, src.get("country", "")),
        "lvl": level_of(whole),
        "f": field_of(whole),
        "fund": funding_of(whole),
        "dl": dl,
        "url": url,
        "src": src["name"],
    }


# ---------------------------------------------------------------- accès poli au web
session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "en,fr;q=0.8",
                        "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml;q=0.9,*/*;q=0.8"})
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def allowed(url: str) -> bool:
    host = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = session.get(host + "/robots.txt", timeout=20)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            _robots[host] = rp
        except requests.RequestException:
            _robots[host] = None
    rp = _robots[host]
    return True if rp is None else rp.can_fetch("BoussoleBot", url)


def get(url: str) -> str:
    if not allowed(url):
        raise PermissionError("interdit par robots.txt")
    r = session.get(url, timeout=30)
    r.raise_for_status()
    time.sleep(PAUSE)
    return r.text


# ---------------------------------------------------------------- lecteurs de sources
def read_rss(src: dict) -> list[dict]:
    out = []
    for u in src["urls"]:
        raw = get(u)
        feed = feedparser.parse(raw)
        if not feed.entries and "<item" in raw:  # fil mal formé : lecture tolérante
            soup = BeautifulSoup(raw, "html.parser")
            feed.entries = [{"title": clean(i.title.get_text()) if i.title else "",
                             "link": clean((i.find("link").get_text() or (i.find("link").next_sibling or "")) if i.find("link") else ""),
                             "summary": i.description.get_text() if i.description else ""} for i in soup.find_all("item")]
        n0 = len(out)
        for e in feed.entries[:80]:
            summary = BeautifulSoup(e.get("summary", "") or "", "html.parser").get_text(" ")
            title = e.get("title", "")
            if src.get("strip_source"):
                title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title)  # « Titre - Nom du site » (Google Actualités)
            it = make(src, title, e.get("link", ""), summary)
            if it:
                out.append(it)
        if not feed.entries:
            print(f"   ! {u} : fil vide ou illisible ({feed.get('bozo_exception', '') or 'aucun élément'})")
        elif len(out) == n0:
            print(f"   ! {u} : {len(feed.entries)} élément(s), tous écartés. Exemples : {[e.get('title','')[:70] for e in feed.entries[:4]]}")
    return out


def read_rss_index(src: dict) -> list[dict]:
    """Page « RSS Feeds » d'une université : on suit seulement les fils dont le nom parle de doctorat."""
    want = re.compile(src.get("match", r"phd|doctoral|studentship|research degree"), re.I)
    feeds = []
    for u in src["urls"]:
        soup = BeautifulSoup(get(u), "html.parser")
        for a in soup.find_all("a", href=True):
            if want.search(a.get_text(" ")) and re.search(r"rss|feed|xml", a["href"], re.I):
                feeds.append(urljoin(u, a["href"]))
    feeds = list(dict.fromkeys(feeds))[:4]
    if not feeds:
        raise ValueError("aucun fil doctorat trouvé sur la page RSS")
    print(f"   fils suivis : {feeds}")
    return read_rss({**src, "urls": feeds})


def read_html(src: dict) -> list[dict]:
    out, seen = [], set()
    rx = re.compile(src["pattern"])
    for u in src["urls"]:
        soup = BeautifulSoup(get(u), "html.parser")
        anchors = soup.find_all("a", href=True)
        hits = 0
        for a in anchors:
            href = a["href"]
            if not rx.search(href):
                continue
            url = urljoin(u, href).split("#")[0]
            title = clean(a.get_text(" "))
            if url in seen or len(title) < 12:
                continue
            seen.add(url)
            card = a
            for _ in range(5):  # remonte jusqu'à la "carte" qui contient l'annonce
                if card.parent is None:
                    break
                card = card.parent
                if len(card.get_text(" ", strip=True)) > len(title) + 60:
                    break
            lines = [clean(x) for x in card.get_text("\n").split("\n") if clean(x)]
            it = make(src, title, url, " ".join(lines), guess_institution(lines, title))
            if it:
                out.append(it)
                hits += 1
        if hits == 0:  # aide au réglage : montre à quoi ressemblent les liens de la page
            sample = [x["href"] for x in anchors[:400] if len(clean(x.get_text())) > 25][:15]
            print(f"   ! {src['id']} : aucun lien reconnu sur {u}. Exemples de liens : {sample}")
    return out


def read_linkedin_mail() -> list[dict]:
    """Facultatif : lit les alertes emploi LinkedIn reçues sur une boîte Gmail dédiée.
    Activé seulement si les secrets GMAIL_USER et GMAIL_APP_PASSWORD existent."""
    user, pwd = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pwd:
        return []
    src = {"name": "LinkedIn (alertes)", "kind": "position"}
    out = []
    box = imaplib.IMAP4_SSL("imap.gmail.com")
    box.login(user, pwd)
    box.select("INBOX")
    since = (TODAY - dt.timedelta(days=3)).strftime("%d-%b-%Y")
    _, ids = box.search(None, f'(FROM "linkedin.com" SINCE {since})')
    for i in ids[0].split()[-30:]:
        _, data = box.fetch(i, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        for part in msg.walk():
            if part.get_content_type() != "text/html":
                continue
            soup = BeautifulSoup(part.get_payload(decode=True).decode(errors="ignore"), "html.parser")
            for a in soup.find_all("a", href=True):
                m = re.search(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)", a["href"])
                if m and len(clean(a.get_text())) > 10:
                    ctx = clean(a.find_parent("table").get_text(" ")) if a.find_parent("table") else ""
                    it = make(src, a.get_text(), f"https://www.linkedin.com/jobs/view/{m[1]}/", ctx)
                    if it:
                        out.append(it)
    box.logout()
    return out


# ---------------------------------------------------------------- programme principal
def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    old = json.loads(OFFERS.read_text("utf-8")) if OFFERS.exists() else []
    by_url = {o["url"]: o for o in old}
    cfg = json.loads(SOURCES.read_text("utf-8"))
    report, fresh = {}, []

    for src in cfg["sources"]:
        if not src.get("enabled", True):
            continue
        print(f"→ {src['name']}")
        try:
            reader = {"rss": read_rss, "rss_index": read_rss_index, "html": read_html}[src["type"]]
            items = reader(src)
            report[src["name"]] = {"ok": True, "offres": len(items)}
            print(f"   {len(items)} offre(s) retenue(s)")
            fresh += items
        except Exception as e:  # une source en panne ne bloque pas les autres
            report[src["name"]] = {"ok": False, "erreur": str(e)[:200]}
            print(f"   ✗ {e}")
    try:
        li = read_linkedin_mail()
        if li or os.environ.get("GMAIL_USER"):
            report["LinkedIn (alertes)"] = {"ok": True, "offres": len(li)}
        fresh += li
    except Exception as e:
        report["LinkedIn (alertes)"] = {"ok": False, "erreur": str(e)[:200]}

    added = 0
    for it in fresh:
        prev = by_url.get(it["url"])
        if prev:
            for k, v in it.items():  # complète sans écraser ce qui était déjà connu
                if v and not prev.get(k):
                    prev[k] = v
            prev["seen"] = TODAY.isoformat()
        else:
            it["found"] = it["seen"] = TODAY.isoformat()
            by_url[it["url"]] = it
            added += 1

    keep = []
    for o in by_url.values():
        if o.get("dl") and o["dl"] < TODAY.isoformat():
            continue
        seen = o.get("seen") or o.get("found") or TODAY.isoformat()
        if not o.get("dl") and (TODAY - dt.date.fromisoformat(seen)).days > STALE_DAYS:
            continue
        keep.append(o)
    keep.sort(key=lambda o: (o.get("found", ""), o.get("dl") or "9999"), reverse=True)
    keep = keep[:MAX_OFFERS]

    OFFERS.write_text(json.dumps(keep, ensure_ascii=False, separators=(",", ":")), "utf-8")
    META.write_text(json.dumps({"mis_a_jour": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                                "total": len(keep), "nouvelles": added, "sources": report}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nTotal : {len(keep)} offres ({added} nouvelles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
