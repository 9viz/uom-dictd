# TODO: Figure out why on earth dictd or dico cannot search for all
# words.  Even if the dict file is produced by dictfmt(1).
# It might be better to give up on dictd and write a dico module to
# search a SQLite database or something.
import functools
from os import listdir
from os.path import exists as file_exists_p
from os.path import isfile as filep
import scrape

@functools.lru_cache(maxsize=None)
def b64_encode(i: int):
    """Base64 encode the integer I as per RFC1421.
    The implemention is taken from libmaa, part of the dictd project.

    """
    lst = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    ret = lst[(i & 0xc0000000) >> 30] + \
        lst[(i & 0x3f000000) >> 24] + \
        lst[(i & 0x00fc0000) >> 18] + \
        lst[(i & 0x0003f000) >> 12] + \
        lst[(i & 0x00000fc0) >>  6] + \
        lst[(i & 0x0000003f)      ]
    for n in range(5):
        if ret[n] != lst[0]:
            return ret[n:]
    return ret[5:]

# ¡Byte offset starts from zero!
def w(dictf, indexf, headword, entry, offset):
    """Write the ENTRY for HEADWORD.
    DICTF is the file object for the .dict file.
    INDEXF is the file object for the .index file.
    OFFSET is the byte offset for the file DICTF.
    This function assumes that ENTRY already contains HEADWORD and
    makes no effort to do anything special.
    If ENTRY does not end with a newline already, then it appends a
    newline to the end.
    DICTF and INDEXF MUST be opened in binary mode.
    Return the new offset value to use.

    """
    if entry == "" or entry[-1] != "\n":
        entry += "\n"
    l = dictf.write(bytes(entry, "utf-8"))
    indexf.write(bytes("{}\t{}\t{}\n".format(headword,
                                             b64_encode(offset),
                                             b64_encode(l)),
                       "utf-8"))
    return offset + l

def do():
    """Do the thing."""
    def key(x):
        if x[:-5].isnumeric():
            return int(x[:-5])
        else:
            return -1

    files = listdir(scrape.SAVEDIR)
    files.sort(key=key)
    offset = 0

    with open("uomlexicon.dict", "wb") as dictf:
        with open("uomlexicon.index", "wb") as indexf:
            with open(scrape.SAVEDIR + "/ABBREVS") as f:
                # For some reason, dictd searches for these entries
                # without dashes.  And it seems like they must be
                # sorted too!  Nothing about this is documented in the
                # manpage.
                offset = w(dictf, indexf, "00databaseinfo", f.read(), offset)
            offset = w(dictf, indexf, "00databaseshort", "சென்னைப் பல்கலைகழகத் தமிழ்ப் பேரகராதி", offset)
            offset = w(dictf, indexf, "00databaseurl",
                       "https://www.tamilvu.org/ta/library-lexicon-html-lexhome-161876", offset)
            offset = w(dictf, indexf, "00databaseutf8", "", offset)

            for i in files:
                if not i.endswith(".html"): continue
                if not filep(scrape.SAVEDIR + "/" + i): continue

                with open(scrape.SAVEDIR + "/" + i) as f:
                    words = scrape.words(f)
                    print(f"Writing words in {scrape.SAVEDIR}/{i}")
                    for headword, entry in words:
                        offset = w(dictf, indexf, headword, entry, offset)

if __name__ == "__main__":
    if not file_exists_p(scrape.SAVEDIR+"/1.html"):
        scrape.pages()
        scrape.abbrevs()
    do()

# offset = 0
# with open("tmp/T.dict", "wb") as dictf:
#     with open("tmp/T.index", "wb") as indexf:
#         offset = w(dictf, indexf, "", "00-dictinfo-utf8", offset)
#         offset = w(dictf, indexf, "asdf\nit is a new kind of monkey", "asdf", offset)
