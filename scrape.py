"""Scrape TVU site for the University of Madras Tamil Lexicon.
All the HTML files will be saved under SAVEDIR/.
And abbreviations used in the Lexicon will be saved in a special file
SAVEDIR/ABBREVS.  This is already parsed and ready to be used.

"""

import bs4
from copy import copy
import html2text
from os import mkdir
from os.path import basename
from os.path import exists as file_exists_p
import re
import urllib.request as req

SAVEDIR = "./lexicon_html"
if not file_exists_p(SAVEDIR):
    mkdir(SAVEDIR)

def request(url):
    """Request URL."""
    return req.urlopen(
        req.Request(url, headers={
            "User-Agent": "Chrome/96.0.4664.110"
        }))

def abbrevs():
    """Return the abbrevs used in the Tamil Lexicon."""
    baseurl = "https://www.tamilvu.org/ta/library-lexicon-html-abb-161776"
    soup = bs4.BeautifulSoup(request(baseurl))
    table = soup.find_all("div", class_="tabdiv_row")
    links = [
        "https://www.tamilvu.org/ta/" + basename(a["href"])
        for a in table[-1].find_all("a")
    ]

    def abbrevs1(divs):
        ret = ""

        for i in divs:
            cells = i.find_all("div", class_="tabdiv_row_cell")
            ab = cells[0].text.strip().replace("\r\n", "")
            ex = cells[-1].text.strip().replace("\r\n", "")
            if ab != "":
                ret += "{} .. {}\n".format(ab, ex)

        return ret

    def abbrevs2(table):
        ret = ""
        for i in table:
            cells = i.find_all("div", class_="tabdiv_row_cell")
            ab = cells[0].text.strip().replace("\r\n", "")
            ex = cells[1].text.strip().replace("\r\n", "")
            if ab != "":
                ret += "{} .. {}\n".format(ab, ex)
            ab = cells[2].text.strip().replace("\r\n", "")
            ex = cells[3].text.strip().replace("\r\n", "")
            if ab != "":
                ret += "{} .. {}\n".format(ab, ex)
        return ret

    # First element is the title of the page, so skip it.
    # Second element contains everything, so skip it.
    # Last element is the links to other pages, so skip it.
    ret = abbrevs1(table[2:-1])
    for i in links:
        soup = bs4.BeautifulSoup(request(i))
        ret += abbrevs1(soup.find_all("div", class_="tabdiv_row")[1:-1])

    # Other abbreviations time.
    soup = bs4.BeautifulSoup(request("https://www.tamilvu.org/ta/library-lexicon-html-othabb-161859"))
    table = soup.find_all("div", class_="tabdiv_row")
    ret += abbrevs2(table)

    # Signs/குறுயீடுகள்.
    soup = bs4.BeautifulSoup(request("https://www.tamilvu.org/ta/library-lexicon-html-signs1-161867"))
    table = soup.find_all("div", class_="tabdiv_row")

    ret += abbrevs2(table[7:])
    ret += abbrevs1(table[:4])

    cells = table[5].find_all("div", class_="tabdiv_row_cell")
    ab = cells[0].text.strip().replace("\r\n", "")
    ex = cells[1].text.strip().replace("\r\n", "")
    ret += "{} {}".format(ab, ex)
    ret += table[6].find("span").text.strip().replace("\r\n", "")

    with open(SAVEDIR+"/ABBREVS", "w") as f:
        f.write(ret)

def pages():
    """Download and save all the pages of the Lexicon."""
    base = "https://www.tamilvu.org/slet/pmdictionary/lexpser_new.jsp?pageno="
    soup = bs4.BeautifulSoup(request(base+"1"))

    def N(soup):
        """Return the total number of pages.
        SOUP is the bs4 object for the first page."""
        t = soup.find("script").text
        i = t.index("t1>") + 3
        f = t.index(")", i)
        return int(t[i:f])

    print("Saving page no. 1")
    with open(SAVEDIR + "/1.html", "w") as f:
        f.write(str(soup))
    for i in range(2,N(soup)+1):
        r = request(base+str(i))
        print(f"Saving page no. {i}")
        with open(f"{SAVEDIR}/{i}.html", "wb") as f:
            f.write(r.read())

_SUP_TABLE = {
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "0": "⁰",
}

"""Group 1 is the word to link to."""
# U+0b80–U+0bff - Tamil block.
# U+11fc0–U+11fff - Tamil Suppl. block.
_LINK_RE = re.compile("See\\.? ([\u0b80-\u0bff\U00011FC0-\U00011FFF]+)\\.")

_RE_MD_DOT_MATCHER = re.compile(
    r"""
    ^             # start of line
    (\s*\d+)      # optional whitespace and a number
    \\
    (\.)          # dot
    (?=\s)        # lookahead assert whitespace
    """,
    re.MULTILINE | re.VERBOSE,
)
_RE_MD_PLUS_MATCHER = re.compile(
    r"""
    ^
    (\s*)
    \\
    (\+)
    (?=\s)
    """,
    flags=re.MULTILINE | re.VERBOSE,
)
_RE_MD_DASH_MATCHER = re.compile(
    r"""
    ^
    (\s*)
    \\
    (-)
    (?=\s|\-)     # followed by whitespace (bullet list, or spaced out hr)
                  # or another dash (header or hr)
    """,
    flags=re.MULTILINE | re.VERBOSE,
)
_RE_SLASH_CHARS = r"\`*_{}[]()#+-.!"
_RE_MD_BACKSLASH_MATCHER = re.compile(
    r"""
    \\
    (\\)          # match one slash
    (?=[%s])      # followed by a char that requires escaping
    """
    % re.escape(_RE_SLASH_CHARS),
    flags=re.VERBOSE,
)

def _unescape(md):
    """Unescape string MD."""
    # Thanks to the very helpful non-escapable escaping `html2text'
    # does, we are stuck with this horrible approach.
    md = _RE_MD_BACKSLASH_MATCHER.sub(r"\\1", md)
    md = _RE_MD_DOT_MATCHER.sub(r"\1\2", md)
    md = _RE_MD_PLUS_MATCHER.sub(r"\1\2", md)
    md = _RE_MD_DASH_MATCHER.sub(r"\1\2", md)
    return md

def words(file, transliteration=False):
    """Return list of [ WORD, DEFINITION ] for all WORDs in FILE.
    If TRANSLITERATION is True, then include the transliteration of
    WORD in DEFINITION.

    """
    soup = bs4.BeautifulSoup(file, "html.parser")
    table = soup.find("td", string="Word").parent.parent
    table = table.find_all("tr")[1:]
    ret = []

    for t in table:
        d = t.find_all("td")
        if len(d) < 2: continue
        if sup := d[0].sup:
            if sup.text.isnumeric():
                repl = ""
                for i in sup.text:
                    repl += _SUP_TABLE[i]
            else:
                repl = "(" + sup.text + ")"
            sup.replace_with(repl)

        if not transliteration:
            f = d[1].font
            # Everything is inside a single <font> tag.
            if f.br:
                d[1] = bs4.BeautifulSoup(
                    str(f)[str(f).index("<br/>")+5:][:-len("</font>")],
                    "html.parser"
                )
            else:
                d[1].font.extract()
                d[1].br.extract()

        # We don't want any newlines in word.
        word = d[0].text.strip().replace("\n", "")
        defn = "  " + _unescape(html2text.html2text(str(d[1]))).strip().replace("\n", "\n  ")

        # Look for links.
        while re.search(_LINK_RE, defn):
            defn = re.sub(_LINK_RE, "See {\\1}.", defn)

        ret.append([ word, word + "\n" + defn ])

    return ret
