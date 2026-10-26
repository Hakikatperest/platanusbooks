#!/bin/bash
# Panelden gelen PDF listesini siteye yayınlar. systemd: platanus-belge.path → .service (root).
# Panel (panel2354) yalnız veri/yayinla.istek dosyasına dokunur; GitHub anahtarına erişimi yok.
# Sonuç veri/yayin-durum.json'a yazılır, panel üst bilgide gösterir.
set -uo pipefail
REPO=/root/platanusbooks_repo
V=/home/panel.platanusbooks.com/veri
U=panel2354
exec 9>/run/platanus-belge.lock
flock 9
sleep 5   # art arda yapılan düzenlemeleri tek yayında topla

durum() {  # durum <ok|hata> <mesaj>
  python3 - "$1" "$2" "$V/yayin-durum.json" <<'PY'
import json, sys, datetime
json.dump({"durum": sys.argv[1], "mesaj": sys.argv[2][-400:],
           "zaman": datetime.datetime.now().astimezone().isoformat(timespec="seconds")},
          open(sys.argv[3], "w"), ensure_ascii=False)
PY
  chown $U:$U "$V/yayin-durum.json"; chmod 600 "$V/yayin-durum.json"
}
hata() { echo "HATA: $1" >&2; durum hata "$1"; exit 1; }

cd "$REPO" || hata "depo yok"
git pull -q --rebase --autostash origin main 2>&1 || hata "git pull başarısız"
# Panelin kilidi alınır: okuma + bekleyen PDF'lerin taşınması sırasında panel yazmasın
exec 8>>"$V/.kilit"
flock 8
python3 _src/belge_al.py "$V" 2>/tmp/platanus-belge.txt || hata "belge listesi işlenemedi: $(tail -1 /tmp/platanus-belge.txt)"
find "$V/bekleyen" -type f -delete
flock -u 8
# ⚠️ Yalnız belge listesi + PDF'ler eklenir; depodaki başka yarım düzenlemeye dokunulmaz.
git add -A dosyalar _src/belgeler.json index.html
if git diff --cached --quiet; then durum ok "değişiklik yok"; exit 0; fi
git commit -q -m "Akademik belgeler panelden güncellendi" || hata "commit başarısız"
git push -q origin HEAD:main 2>&1 || hata "GitHub'a gönderilemedi"
durum ok "yayınlandı $(git rev-parse --short HEAD)"
echo "yayınlandı"
