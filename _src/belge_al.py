#!/usr/bin/env python3
"""Panel verisinden "Akademik Belgeler & Özel Yayınlar" bölümünü üretir.

Kullanım:
  belge_al.py <veri_dizini>   panelin belgeler.json'unu okur, bekleyen PDF'leri dosyalar/'a taşır,
                              listeden çıkan PDF'leri siler, index.html'deki bölümü yeniden yazar
  belge_al.py --tohum         index.html'deki mevcut düğmelerden belgeler.json tohumu basar (tek seferlik)

⚠️ index.html'de yalnız <!-- PDF-LISTE-BASLA --> ile <!-- PDF-LISTE-BITIR --> arası değişir.
⚠️ Jekyll _ ile başlayan klasörü yayınlamaz; bu betik ve _src/belgeler.json sitede görünmez.
"""
import html, json, os, re, shutil, sys, urllib.parse
from pathlib import Path

DEPO = Path(__file__).resolve().parent.parent
INDEX = DEPO / "index.html"
DOSYALAR = DEPO / "dosyalar"
KOPYA = DEPO / "_src" / "belgeler.json"
TABAN = "https://www.platanusbooks.com/dosyalar/"
BAS, BIT = "<!-- PDF-LISTE-BASLA -->", "<!-- PDF-LISTE-BITIR -->"
GUVENLI_AD = re.compile(r"^[^/\\\x00-\x1f]{1,150}\.pdf$")


def tohum():
    metin = INDEX.read_text(encoding="utf-8")
    kayitlar = []
    for n, (href, etiket) in enumerate(re.findall(
            r'<a href="https://www\.platanusbooks\.com/dosyalar/([^"]+)" class="btn-pdf"[^>]*>.*?'
            r'<span class="btn-label">(.*?)</span></a>', metin)):
        baslik = re.sub(r"\s*PDF$", "", html.unescape(etiket)).strip()
        kayitlar.append({"id": f"eski{n:02d}", "baslik": baslik,
                         "dosya": urllib.parse.unquote(href), "sira": n})
    print(json.dumps(kayitlar, ensure_ascii=False, indent=2))


def main(veri: Path):
    kayitlar = json.loads((veri / "belgeler.json").read_text(encoding="utf-8"))
    if not isinstance(kayitlar, list):
        sys.exit("belgeler.json liste değil")
    bekleyen = veri / "bekleyen"
    temiz = []
    for k in sorted(kayitlar, key=lambda x: (x.get("sira", 0), x.get("tarih", ""))):
        baslik = re.sub(r"\s+", " ", str(k.get("baslik", ""))).strip()
        dosya = str(k.get("dosya", ""))
        if not baslik or len(baslik) > 120 or not GUVENLI_AD.match(dosya) or dosya.startswith("."):
            sys.exit(f"geçersiz kayıt: {k.get('id')}")
        kaynak = bekleyen / dosya
        if kaynak.is_file():
            with kaynak.open("rb") as f:
                if f.read(5) != b"%PDF-":
                    sys.exit(f"PDF değil: {dosya}")
            shutil.copyfile(kaynak, DOSYALAR / dosya)
            os.chmod(DOSYALAR / dosya, 0o644)
        if not (DOSYALAR / dosya).is_file():
            sys.exit(f"dosya yok: {dosya}")
        temiz.append({"id": k.get("id"), "baslik": baslik, "dosya": dosya})

    # Listeden çıkan PDF'ler sitede de kalmasın (aynı URL'de indirilebilir kalırdı)
    kullanilan = {k["dosya"] for k in temiz}
    for p in DOSYALAR.glob("*.pdf"):
        if p.name not in kullanilan:
            p.unlink()

    satirlar = "\n".join(
        f'        <a href="{TABAN}{urllib.parse.quote(k["dosya"])}" class="btn-pdf" target="_blank">'
        f'<i class="fas fa-download"></i><span class="btn-label">{html.escape(k["baslik"])} PDF</span></a>'
        for k in temiz)
    metin = INDEX.read_text(encoding="utf-8")
    desen = re.compile(re.escape(BAS) + r".*?" + re.escape(BIT), re.S)
    if len(desen.findall(metin)) != 1:
        sys.exit("index.html'de işaretleyiciler bulunamadı")
    metin = desen.sub(lambda _: f"{BAS}\n{satirlar}\n        {BIT}", metin)
    INDEX.write_text(metin, encoding="utf-8")
    KOPYA.write_text(json.dumps(temiz, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(temiz)} belge")


if __name__ == "__main__":
    if sys.argv[1:] == ["--tohum"]:
        tohum()
    elif len(sys.argv) == 2:
        main(Path(sys.argv[1]))
    else:
        sys.exit(__doc__)
