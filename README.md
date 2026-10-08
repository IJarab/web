# Web Ivan Jarabinský — návod

## Co je v balíčku

| Složka / soubor | K čemu je | Upravuješ? |
|---|---|---|
| `site/` | **Hotový web.** Tahle složka se nahrává na hosting. Je generovaná, ručně ji neupravuj. | ne |
| `data/publications.csv` | Publikace (články, kapitoly, zprávy) | **ano** |
| `data/conferences.csv` | Konference | **ano** |
| `data/media.csv` | Podcasty, rozhovory, blogy | **ano** |
| `data/cv.csv` | Řádky životopisu | **ano** |
| `data/outputs.csv` | Další příspěvky k projektům (pořádané akce, datasety, briefy), které nejsou publikace ani konference | **ano** |
| `content/home.html` | Texty úvodní stránky (bio, karty aktuálního výzkumu) | **ano** |
| `content/research.html` | Stránka Research (projekty, dokončené projekty) | **ano** |
| `assets/` | Fotka, CV v PDF, favicony | vyměníš soubor stejného jména |
| `styles.css` | Vzhled (barvy, písma, rozvržení) | jen když chceš měnit design |
| `build.py` | Skript, který z `data/` + `content/` vyrobí `site/` | ne |

## Jak přidat publikaci, konferenci, článek

1. Otevři příslušný soubor v `data/` (v Excelu, Google Sheets, Numbers nebo v textovém editoru).
   Každý řádek je jedna položka, první řádek jsou názvy sloupců.
2. Přidej řádek. Pořadí řádků nerozhoduje, web řadí podle roku, resp. data.
3. Ulož **jako CSV (UTF-8, oddělovač čárka)**. V Google Sheets: Soubor → Stáhnout → CSV.
4. Nech web přegenerovat (viz níže).

Sloupce, které stojí za pozornost:

- `publications.csv`: `type` je `article`, `preprint`, `chapter` nebo `report`; `tag` je nepovinný štítek (např. `Book review`);
  `link_label` je text odkazu (`DOI`, `PDF`, `Link`) a `link` adresa. Prázdné = bez odkazu.
- `media.csv`: `section` je `podcast`, `press` nebo `blog`; `date` ve tvaru `RRRR-MM-DD` slouží jen k řazení,
  `date_text` je to, co se zobrazí.
- `conferences.csv`: `kind` je `Presentation` nebo `Roundtable`; `coauthors` se zobrazí v závorce.
- `cv.csv`: `section` je `experience`, `education`, `visits` nebo `training`.
- Sloupec `project` (v publikacích, konferencích i médiích): klíč projektu ze stránky Research, tedy `id` bloku
  v `content/research.html` (`electoral-systems`, `meaning-crisis`, `recounts`, `parliamentary-speeches`,
  `visegrad-capitals`, `disinformation-science`, `electoral-integrity-2015`). Více klíčů odděl středníkem.
  Položka se pak objeví v seznamu „My contributions“ u projektu (odkaz vede z Research na položku). Prázdné = nic.
- `outputs.csv`: totéž pro věci mimo ostatní tabulky; `kind` je libovolný popisek (např. `Conference organised`,
  `Dataset`), `where` místo nebo repozitář, `link` nepovinný.

Úvodní stránka sama vybere čtyři nejnovější články z `publications.csv`. Na stránce Research skript sám přečísluje projekty (01, 02, …); karty na úvodní stránce se ale neaktualizují samy, novou kartu tam přidáš ručně.

## Jak upravit texty a karty

Texty jsou v `content/home.html` a `content/research.html`. Otevři soubor v textovém editoru
(na Macu TextEdit v režimu prostého textu, na Windows Poznámkový blok, lépe VS Code).
Každý blok je ohraničený komentářem `<!-- ===== … ===== -->`. Novou kartu přidáš tak, že zkopíruješ
celý blok `<article class="card"> … </article>` a přepíšeš text. Znaky `<` a `>` v textu nepoužívej,
`&` napiš jako `&amp;`.

## Jak web přegenerovat

Tři možnosti, od nejpohodlnější:

1. **GitHub Pages (doporučeno).** Repozitář obsahuje `.github/workflows/deploy.yml`. Po každé změně
   (i editaci přímo v prohlížeči na GitHubu) se web sám přegeneruje a zveřejní během minuty.
   Nastavení jednorázově: Settings → Pages → Source: **GitHub Actions**.
2. **Poslat Claudovi** soubory z `data/` nebo `content/` s prosbou o přegenerování; dostaneš novou složku `site/`.
3. **Lokálně:** s nainstalovaným Pythonem 3 spustit v této složce `python3 build.py`. Nic dalšího není potřeba.

Cloudflare Pages a Netlify umí build spustit také: build command `python3 build.py`, output directory `site`.

## Hosting a doména

1. Založ účet u hostingu (GitHub Pages, Cloudflare Pages nebo Netlify, všechny zdarma pro tento typ webu).
2. Nahraj projekt (GitHub: celý repozitář; Netlify bez Gitu: přetáhni složku `site/`).
3. Kup doménu (např. `ivanjarabinsky.cz` nebo `.eu`) u libovolného registrátora.
4. V nastavení hostingu přidej vlastní doménu a u registrátora nastav DNS záznamy, které hosting vypíše
   (obvykle CNAME na adresu hostingu). HTTPS certifikát hosting vystaví sám.
5. Ve Wixu nastav přesměrování staré adresy na novou, nebo starý web vypni.

## Poznámky

- Písma EB Garamond a Source Sans 3 se načítají z Google Fonts. Kdyby měla být stránka úplně bez
  externích služeb, dají se stáhnout do `assets/` a v `styles.css` nahradit `@font-face` pravidly.
- Logo/značka je přímo v kódu stránek jako SVG; samostatně je v `assets/favicon.svg`.
- Nové CV vlož jako `assets/cv.pdf` (stejné jméno, přepsat).
