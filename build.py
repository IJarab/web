#!/usr/bin/env python3
"""
Build the site.

    python3 build.py            -> writes site/ (upload this folder to the hosting)
    python3 build.py --proto    -> also writes prototype.html (one file, all pages, for previewing)

Sources:
    data/publications.csv, data/conferences.csv, data/media.csv, data/cv.csv   (lists)
    data/outputs.csv   (other contributions to projects: events organised, datasets, briefs …)
    content/home.html, content/research.html                                     (prose)
    styles.css, assets/                                                          (look, files)

Needs only the Python standard library (Pillow is optional, for PNG favicons).
"""
import base64, csv, hashlib, html, pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent
SITE = ROOT / "site"
DATA = ROOT / "data"
CONTENT = ROOT / "content"

SITE_TITLE = "Ivan Jarabinský"
EMAIL = "ivan.jarabinsky@ih21.org"
FOOTER_LINKS = [
    ("ORCID", "https://orcid.org/0000-0002-2159-1191"),
    ("Google Scholar", "https://scholar.google.com/citations?user=6tASlU8AAAAJ"),
    ("ResearchGate", "https://www.researchgate.net/profile/Ivan-Jarabinsky"),
    ("LinkedIn", "https://www.linkedin.com/in/ivan-jarabinsk%C3%BD-088177bb/"),
    ("X", "https://x.com/eXampleee"),
]
PAGES = [  # file, label in menu, id used by the prototype
    ("index.html", "About", "home"),
    ("research.html", "Research", "research"),
    ("publications.html", "Publications", "publications"),
    ("conferences.html", "Conferences", "conferences"),
    ("media.html", "Media", "media"),
    ("cv.html", "CV", "cv"),
]
FONTS = ("https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400"
         "&family=Source+Sans+3:wght@400;500;600&display=swap")

I_PATH = "M26,20 H66 V27 H60 Q53,27 53,34 V106 Q53,113 60,113 H66 V120 H26 V113 H32 Q39,113 39,106 V34 Q39,27 32,27 H26 Z"
MARK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="26 20 120 100" role="img" aria-label="Ivan Jarabinský">'
        f'<path fill="currentColor" d="{I_PATH}"></path>'
        '<polygon style="fill: var(--accent)" points="76,118 88,118 146,22 134,22"></polygon></svg>')
RULE_ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 116 100" aria-hidden="true">'
             '<rect fill="currentColor" x="10" y="0" width="10" height="100"></rect>'
             '<rect fill="currentColor" x="32" y="0" width="10" height="100"></rect>'
             '<rect fill="currentColor" x="54" y="0" width="10" height="100"></rect>'
             '<rect fill="currentColor" x="76" y="0" width="10" height="100"></rect>'
             '<polygon fill="currentColor" points="0,98 12,98 116,2 104,2"></polygon></svg>')
FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="18 12 136 116">'
               f'<path fill="#1B1B1B" d="{I_PATH}"/>'
               '<polygon fill="#9A6620" points="76,118 88,118 146,22 134,22"/></svg>')

e = html.escape


def slug(title, prefix="o"):
    """Stable anchor for one item, derived from its title (prefix tells the tables apart)."""
    return f"{prefix}-" + hashlib.md5(title.encode("utf-8")).hexdigest()[:8]


def project_titles():
    """id -> title of every project / work item / completed card in content/research.html."""
    s = re.sub(r'<!--.*?-->', '', (CONTENT / "research.html").read_text(encoding="utf-8"), flags=re.S)
    out = {}
    for m in re.finditer(r'<article class="(?:project|work|card)" id="([\w-]+)">(.*?)</article>', s, flags=re.S):
        h = re.search(r'<h[23]>(.*?)</h[23]>', m.group(2), flags=re.S)
        out[m.group(1)] = re.sub(r'<[^>]+>', '', h.group(1)).strip() if h else m.group(1)
    return out


def project_tags(r, titles):
    keys = [k.strip() for k in r.get("project", "").split(";") if k.strip()]
    return ""  # back-links from items to projects are switched off; the link runs Research -> item only


def collect_outputs():
    """project id -> outputs (newest first) from the three tables."""
    out = {}
    def add(key, year, kind, title, venue, href):
        for k in [x.strip() for x in key.split(";") if x.strip()]:
            out.setdefault(k, []).append((int(year), kind, title, venue, href))
    labels = {"article": "Article", "preprint": "Preprint", "chapter": "Book chapter", "report": "Report"}
    for r in rows("publications.csv"):
        if r.get("project"):
            add(r["project"], r["year"], r["tag"] or labels.get(r["type"], "Publication"), r["title"], r["venue"],
                f'publications.html#{slug(r["title"], "p")}')
    for r in rows("conferences.csv"):
        if r.get("project"):
            add(r["project"], r["year"], "Conference paper" if r["kind"] == "Presentation" else (r["kind"] or "Conference"),
                r["title"], r["event"], f'conferences.html#{slug(r["title"] + r["event"], "c")}')
    for r in rows("media.csv"):
        if r.get("project"):
            add(r["project"], r["date"][:4], r["kind"] or "Media", r["title"], r["outlet"], f'media.html#{slug(r["title"], "m")}')
    if (DATA / "outputs.csv").exists():  # anything else: datasets, events organised, software, briefs …
        for r in rows("outputs.csv"):
            if r.get("project"):
                add(r["project"], r["year"], r["kind"] or "Output", r["title"], r["where"], r["link"])
    for k in out:
        out[k].sort(key=lambda x: -x[0])
    return out


def outputs_block(items):
    lis = "\n".join(f'    <li><span class="o-meta">{y} · {e(kind)} · {e(venue)}</span> '
                    + (f'<a href="{href}">{e(title)}</a>' if href else f'<span class="o-title">{e(title)}</span>') + '</li>'
                    for y, kind, title, venue, href in items)
    return f'\n  <div class="outputs">\n    <p class="label">My contributions</p>\n    <ul>\n{lis}\n    </ul>\n  </div>\n'


def attach_outputs(s):
    """Insert an Outputs list before the closing tag of every project / work / card that has outputs."""
    outs = collect_outputs()
    for key, items in outs.items():
        m = re.search(rf'<article class="(?:project|work|card)" id="{re.escape(key)}">', s)
        if not m:
            continue
        end = s.index("</article>", m.end())
        s = s[:end] + outputs_block(items) + s[end:]
    return s



def rows(name):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def link(label, url):
    return f' · <a href="{e(url)}">{e(label)}</a>' if url else ""


# ---------------------------------------------------------------- items ----
def pub_item(r, titles=None):
    meta = f'<span>{e(r["year"])} · {e(r["venue"])}</span>'
    if r["tag"]:
        meta += f'<span class="tag">{e(r["tag"])}</span>'
    authors = e(r["authors"]) + (f' · {e(r["note"])}' if r["note"] else "")
    if r["type"] == "article":
        where = f'{e(r["venue"])} {e(r["details"])}'.strip()
    else:
        where = e(r["details"]) + (f' · {e(r["venue"])}' if r["venue"] and r["venue"] not in r["details"] else "")
    title = e(r["title"])
    if r["link"]:
        title = f'<a href="{e(r["link"])}" class="title-link">{title}</a>'
    return (f'<article class="item" id="{slug(r["title"], "p")}">\n  <p class="meta">{meta}</p>\n  <h3>{title}</h3>\n'
            f'  <p class="authors">{authors}</p>\n  <p class="where">{where}{link(r["link_label"], r["link"])}</p>'
            f'{project_tags(r, titles or {})}\n</article>')


def media_item(r, titles=None):
    title = e(r["title"])
    if r["link"]:
        title = f'<a href="{e(r["link"])}" class="title-link">{title}</a>'
    meta = f'<span>{e(r["date_text"])}</span>' + (f'<span class="tag">{e(r["kind"])}</span>' if r["kind"] else "")
    authors = f'\n  <p class="authors">{e(r["authors"])}</p>' if r["authors"] else ""
    where = ", ".join(e(x) for x in (r["outlet"], r["details"]) if x)
    return (f'<article class="item" id="{slug(r["title"], "m")}">\n  <p class="meta">{meta}</p>\n  <h3>{title}</h3>{authors}\n'
            f'  <p class="where">{where}{link("Link", r["link"])}</p>{project_tags(r, titles or {})}\n</article>')


def conf_entry(r, titles=None):
    co = f'\n    <p class="coauthors">({e(r["coauthors"])})</p>' if r["coauthors"] else ""
    kind = f'\n    <span class="tag kind">{e(r["kind"])}</span>' if r["kind"] else ""
    title = e(r["title"])
    if r["link"]:
        title = f'<a href="{e(r["link"])}" class="title-link">{title}</a>'
    when = e(r["dates"]) + (f', {e(r["place"])}' if r["place"] else "")
    return (f'  <div class="entry" id="{slug(r["title"] + r["event"], "c")}">\n    <p class="event">{e(r["event"])}</p>\n    <p class="when">{when}</p>\n'
            f'    <h3>{title}</h3>{co}{kind}{project_tags(r, titles or {})}\n  </div>')


def cv_row(r):
    note = f'\n      <em>{e(r["note"])}</em>' if r["note"] else ""
    return (f'<div class="cv-row">\n    <div class="period">{e(r["period"])}</div>\n'
            f'    <div class="what"><strong>{e(r["title"])}</strong><span>{e(r["organisation"])}</span>{note}</div>\n  </div>')


def externalise(s):
    """Links that leave the site (http/https, and the CV PDF) open in a new tab."""
    return re.sub(r'<a href="(https?://[^"]+|assets/cv\.pdf)"(?![^>]*target=)',
                  r'<a href="\1" target="_blank" rel="noopener"', s)


# ---------------------------------------------------------------- pages ----
def page_title(title):
    return (f'<section class="wrap page-title">\n  <h1>{e(title)}</h1>\n'
            f'  <div class="rule">{RULE_ICON}</div>\n</section>\n')


def build_home():
    pubs = sorted([r for r in rows("publications.csv") if r["type"] == "article"], key=lambda r: -int(r["year"]))[:4]
    body = (CONTENT / "home.html").read_text(encoding="utf-8")
    selected = re.sub(r' id="p-[0-9a-f]+"', "", "\n".join(pub_item(r) for r in pubs))
    return body.replace("{{selected_publications}}", selected).replace("{{rule_icon}}", RULE_ICON)


WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]


def build_research():
    s = attach_outputs((CONTENT / "research.html").read_text(encoding="utf-8")).replace("{{rule_icon}}", RULE_ICON)
    n = len(re.findall(r'<article class="project"', re.sub(r'<!--.*?-->', '', s, flags=re.S)))  # comments don't count
    s = s.replace("{{project_count}}", WORDS[n] if n < len(WORDS) else str(n))
    counter = iter(range(1, n + 1))
    return re.sub(r'<span class="num">[^<]*</span>', lambda m: f'<span class="num">{next(counter):02d}</span>', s)


def build_publications():
    data = rows("publications.csv"); titles = project_titles()
    groups = [("journals", "Peer-reviewed journals", "article"), ("preprints", "Preprints", "preprint"),
              ("chapters", "Book chapters", "chapter"), ("reports", "Expert reports", "report")]
    aside = "".join(
        f'<li><a href="#{gid}"><span>{e(label)}</span><span>{sum(1 for r in data if r["type"] == t)}</span></a></li>'
        for gid, label, t in groups)
    sections = []
    for gid, label, t in groups:
        items = sorted([r for r in data if r["type"] == t], key=lambda r: -int(r["year"]))
        sections.append(f'<section class="group" id="{gid}">\n<h2>{e(label)}</h2>\n<div class="items">\n'
                        + "\n".join(pub_item(r, titles) for r in items) + "\n</div>\n</section>")
    return (page_title("Publications")
            + f'<section class="wrap with-aside">\n<nav class="aside" aria-label="Publication categories"><ul>{aside}</ul></nav>\n'
            + '<div class="main-col">\n' + "\n".join(sections) + '\n</div>\n</section>\n')


def build_conferences():
    data = rows("conferences.csv"); titles = project_titles()
    years = sorted({int(r["year"]) for r in data}, reverse=True)
    out = []
    for y in years:
        entries = "\n".join(conf_entry(r, titles) for r in data if int(r["year"]) == y)
        out.append(f'<div class="year-row">\n  <div class="year">{y}</div>\n  <div class="entries">\n{entries}\n  </div>\n</div>')
    return (page_title("Conferences")
            + '<section class="wrap" style="padding-top: 16px; padding-bottom: 64px">\n' + "\n".join(out) + '\n</section>\n')


def build_media():
    data = rows("media.csv"); titles = project_titles()
    groups = [("podcast", "Interviews & podcasts"), ("press", "Newspapers & magazines"), ("blog", "Blog posts")]
    groups = [(k, l) for k, l in groups if any(r["section"] == k for r in data)]
    aside = "".join(
        f'<li><a href="#{k}"><span>{e(l)}</span><span>{sum(1 for r in data if r["section"] == k)}</span></a></li>'
        for k, l in groups)
    sections = []
    for key, label in groups:
        items = sorted([r for r in data if r["section"] == key], key=lambda r: r["date"], reverse=True)
        sections.append(f'<section class="group" id="{key}">\n<h2>{e(label)}</h2>\n<div class="items">\n'
                        + "\n".join(media_item(r, titles) for r in items) + "\n</div>\n</section>")
    return (page_title("Media")
            + f'<section class="wrap with-aside">\n<nav class="aside" aria-label="Media categories"><ul>{aside}</ul></nav>\n'
            + '<div class="main-col">\n' + "\n".join(sections) + '\n</div>\n</section>\n')


def build_cv():
    data = rows("cv.csv")
    groups = [("experience", "Professional experience"), ("education", "Education"),
              ("visits", "Academic visits"), ("training", "Training")]
    out = []
    for key, label in groups:
        rws = [r for r in data if r["section"] == key]
        if not rws:
            continue
        out.append(f'<section class="wrap section" id="{key}">\n  <div class="section-label"><h2>{e(label)}</h2></div>\n'
                   f'  <div class="section-body cv-rows">\n' + "\n".join(cv_row(r) for r in rws) + '\n  </div>\n</section>')
    head = ('<section class="wrap page-title">\n  <h1>Curriculum vitae</h1>\n'
            '  <div class="actions"><a class="btn" href="assets/cv.pdf">Download full CV (PDF)</a></div>\n'
            f'  <div class="rule">{RULE_ICON}</div>\n</section>\n')
    return head + "\n".join(out) + '\n<div style="height: 32px"></div>\n'


BUILDERS = {"home": build_home, "research": build_research, "publications": build_publications,
            "conferences": build_conferences, "media": build_media, "cv": build_cv}
TITLES = {"home": "Ivan Jarabinský · Political scientist", "research": "Research · Ivan Jarabinský",
          "publications": "Publications · Ivan Jarabinský", "conferences": "Conferences · Ivan Jarabinský",
          "media": "Media · Ivan Jarabinský", "cv": "Curriculum vitae · Ivan Jarabinský"}
DESCRIPTION = ("Ivan Jarabinský is a political scientist studying elections, electoral integrity and voting methods. "
               "Head of Election Research at Institute H21, Prague.")


# ---------------------------------------------------------------- shell ----
def header(active, proto=False):
    items = []
    for f, label, pid in PAGES:
        href = f"#{pid}" if proto else f
        cur = ' aria-current="page"' if pid == active else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    home = "#home" if proto else "index.html"
    return (f'<header class="wrap site-header">\n  <a class="brand" href="{home}">{MARK}<span>{SITE_TITLE}</span></a>\n'
            f'  <nav class="nav" aria-label="Main"><ul>{"".join(items)}</ul></nav>\n</header>\n')


def footer():
    links = "".join(f'<li><a href="{e(u)}">{e(l)}</a></li>' for l, u in FOOTER_LINKS)
    return (f'<footer class="wrap site-footer">\n  <div class="rule">{RULE_ICON}</div>\n  <div class="footer-grid">\n'
            f'    <div class="contact"><span>Contact</span><a href="mailto:{EMAIL}">{EMAIL}</a></div>\n'
            f'    <ul class="footer-links">{links}</ul>\n    <p class="copy">© 2026 Ivan Jarabinský</p>\n  </div>\n</footer>\n')


def shell(pid, body, css_href="styles.css"):
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{e(TITLES[pid])}</title>\n<meta name="description" content="{e(DESCRIPTION)}">\n'
            f'<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">\n'
            f'<link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png">\n'
            f'<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">\n'
            f'<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="{FONTS}">\n<link rel="stylesheet" href="{css_href}">\n</head>\n<body>\n'
            + externalise(header(pid) + f'<main>\n{body}</main>\n' + footer()) + '</body>\n</html>\n')


def write_favicons(assets):
    (assets / "favicon.svg").write_text(FAVICON_SVG, encoding="utf-8")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    for name, size in (("favicon-32.png", 32), ("apple-touch-icon.png", 180)):
        s = size * 8
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0) if size == 32 else (255, 255, 255, 255))
        d = ImageDraw.Draw(im)
        k = s / 136.0  # viewBox 18..154 wide, 12..128 tall

        def P(x, y):
            return ((x - 18) * k, (y - 12) * k)
        # serif I as polygons (stem + two serifs)
        d.polygon([P(39, 27), P(53, 27), P(53, 113), P(39, 113)], fill="#1B1B1B")
        d.polygon([P(26, 20), P(66, 20), P(66, 27), P(26, 27)], fill="#1B1B1B")
        d.polygon([P(26, 113), P(66, 113), P(66, 120), P(26, 120)], fill="#1B1B1B")
        d.polygon([P(76, 118), P(88, 118), P(146, 22), P(134, 22)], fill="#9A6620")
        im = im.resize((size, size), Image.LANCZOS)
        im.save(assets / name)


def build_site():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    assets = SITE / "assets"
    shutil.copytree(ROOT / "assets", assets)
    shutil.copy(ROOT / "styles.css", SITE / "styles.css")
    write_favicons(assets)
    for f, _, pid in PAGES:
        (SITE / f).write_text(shell(pid, BUILDERS[pid]()), encoding="utf-8")
    print("site/ written:", ", ".join(f for f, _, _ in PAGES))


DARK = """
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --ground: #161412; --ink: #F3EEE4; --text: #E6DFD3; --muted: #C9C2B6;
    --caption: #A89F92; --accent: #D89D4D; --sand: #D89D4D; --tint: #221F1B; --rule: #3A352F; }
}
:root[data-theme="dark"] { --ground: #161412; --ink: #F3EEE4; --text: #E6DFD3; --muted: #C9C2B6;
  --caption: #A89F92; --accent: #D89D4D; --sand: #D89D4D; --tint: #221F1B; --rule: #3A352F; }
"""
HIDDEN = ".page[hidden] { display: none; }\n"

ROUTER = """
<script>
(function () {
  var ids = ['home', 'research', 'publications', 'conferences', 'media', 'cv'];
  function show() {
    var h = (location.hash || '#home').slice(1), target = null;
    if (ids.indexOf(h) < 0) { target = document.getElementById(h); h = target ? target.closest('.page').id.slice(5) : 'home'; }
    ids.forEach(function (i) { document.getElementById('page-' + i).hidden = (i !== h); });
    document.querySelectorAll('.nav a').forEach(function (a) {
      if (a.getAttribute('href') === '#' + h) { a.setAttribute('aria-current', 'page'); } else { a.removeAttribute('aria-current'); }
    });
    if (target) { target.scrollIntoView(); } else { window.scrollTo(0, 0); }
  }
  window.addEventListener('hashchange', show);
  show();
})();
</script>
"""


def build_prototype():
    css = (ROOT / "styles.css").read_text(encoding="utf-8") + HIDDEN + (DARK if "--dark" in sys.argv else "")
    portrait = base64.b64encode((ROOT / "assets" / "portrait.jpg").read_bytes()).decode()
    fav = "data:image/svg+xml;base64," + base64.b64encode(FAVICON_SVG.encode()).decode()

    def relink(s):
        s = re.sub(r'href="(index|research|publications|conferences|media|cv)\.html(#[\w-]+)?"',
                   lambda m: f'href="{m.group(2) or "#" + ("home" if m.group(1) == "index" else m.group(1))}"', s)
        s = s.replace('href="assets/cv.pdf"', 'href="#cv"')
        s = s.replace('src="assets/portrait.jpg"', f'src="data:image/jpeg;base64,{portrait}"')
        return s

    pages = "\n".join(f'<section class="page" id="page-{pid}"{"" if pid == "home" else " hidden"}>\n{relink(BUILDERS[pid]())}</section>'
                      for _, _, pid in PAGES)
    doc = (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
           f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           f'<title>Ivan Jarabinský · prototype</title>\n<link rel="icon" href="{fav}">\n'
           f'<link rel="stylesheet" href="{FONTS}">\n<style>\n{css}\n</style>\n</head>\n<body>\n'
           + externalise(header("home", proto=True) + f'<main>\n{pages}\n</main>\n' + footer()) + ROUTER + '</body>\n</html>\n')
    (ROOT / "prototype.html").write_text(doc, encoding="utf-8")
    print("prototype.html written")


if __name__ == "__main__":
    build_site()
    if "--proto" in sys.argv:
        build_prototype()
