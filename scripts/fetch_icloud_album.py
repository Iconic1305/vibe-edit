"""Download the videos of a PUBLIC iCloud shared-album link (photos.icloud.com/shared/album/<token>).

Usage:
    python3 scripts/fetch_icloud_album.py <album-url-or-token> projects/<slug>/input [--list]

Uses the same anonymous public-access path the album's own web page uses (no Apple ID, no login):
  1. records/resolve with the share token -> zone + a short-lived anonymous access token + partition host
  2. records/query (paged) on that partition host -> CPLMaster records with original-resolution download URLs
  3. download each video (never overwrites an existing file), then ffprobe it.
Hosts needed: photos.icloud.com, ckdatabasews.icloud.com, <partition>-ckdatabasews.icloud.com (e.g. p198-...),
and the *.icloud-content.com host(s) in each downloadURL. Any blocked host is reported by name.
--list prints what is in the album without downloading.
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CK = "https://ckdatabasews.icloud.com/database/1/com.apple.photos.cloud/production"
HDR = {"content-type": "text/plain", "Origin": "https://photos.icloud.com", "User-Agent": "Mozilla/5.0"}
VIDEO_UTI = ("movie", "mpeg-4", "mp4", "video")


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=HDR)
    try:
        return json.load(urllib.request.urlopen(req, timeout=90))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {urllib.parse.urlparse(url).netloc}: {e.read()[:300]!r}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach host '{urllib.parse.urlparse(url).netloc}' ({e.reason}). Add this exact hostname to the environment's allowed domains.")


def token_of(s):
    m = re.search(r"/shared/album/([A-Za-z0-9_-]+)", s)
    return m.group(1) if m else s.strip()


def filename(rec):
    enc = rec["fields"].get("filenameEnc", {}).get("value")
    try:
        return base64.b64decode(enc).decode("utf-8") if enc else rec["recordName"]
    except Exception:
        return rec["recordName"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("album")
    ap.add_argument("dest")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    tok = token_of(a.album)

    res = post(f"{CK}/public/records/resolve?remapEnums=true&getCurrentSyncToken=true&sharing_url_key={tok}",
               {"shortGUIDs": [{"value": tok}]})["results"][0]
    if res.get("requireAppleLogin"):
        sys.exit("This album requires an Apple login; it can't be downloaded anonymously.")
    acc = res.get("anonymousPublicAccess")
    if not acc:
        sys.exit("Album has no anonymous public access token.")
    part = acc["databasePartition"].rstrip("/").replace(":443", "")
    print(f"album zone {res['zoneID']['zoneName']} · partition {urllib.parse.urlparse(part).netloc}")

    qs = urllib.parse.urlencode({"remapEnums": "true", "getCurrentSyncToken": "true",
                                 "sharing_url_key": tok, "publicAccessAuthToken": acc["token"]})
    url = f"{part}/database/1/com.apple.photos.cloud/production/shared/records/query?{qs}"
    masters, marker = [], None
    while True:
        body = {"query": {"recordType": "CPLAssetAndMasterByAssetDateWithoutHiddenOrDeleted",
                          "filterBy": [{"fieldName": "direction", "comparator": "EQUALS",
                                        "fieldValue": {"value": "ASCENDING", "type": "STRING"}}]},
                "zoneID": res["zoneID"], "resultsLimit": 100}
        if marker:
            body["continuationMarker"] = marker
        r = post(url, body)
        masters += [x for x in r.get("records", []) if x["recordType"] == "CPLMaster"]
        marker = r.get("continuationMarker")
        if not marker:
            break
    vids = [m for m in masters if any(k in str(m["fields"].get("itemType", {}).get("value", "")).lower() for k in VIDEO_UTI)
            or filename(m).lower().endswith((".mov", ".mp4", ".m4v"))]
    print(f"{len(masters)} item(s) in album, {len(vids)} video(s)")
    for m in vids:
        o = m["fields"].get("resOriginalRes", {}).get("value", {})
        print(f"  {filename(m)}  {int(o.get('size', 0)) / 1e6:.1f} MB")
    if a.list:
        return

    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    manifest, failed = [], 0
    for m in vids:
        name = filename(m)
        o = m["fields"].get("resOriginalRes", {}).get("value", {})
        target = dest / Path(name).name
        if target.exists():
            print(f"  skip (exists, never overwritten): {target.name}")
            manifest.append({"file": target.name, "status": "existing"})
            continue
        dl = o.get("downloadURL", "").replace("${f}", urllib.parse.quote(name))
        if not dl:
            print(f"  NO DOWNLOAD URL for {name}")
            failed += 1
            continue
        print(f"  downloading {name} from {urllib.parse.urlparse(dl).netloc} …")
        tmp = target.with_suffix(target.suffix + ".part")
        try:
            with urllib.request.urlopen(urllib.request.Request(dl, headers={"User-Agent": HDR["User-Agent"]}), timeout=120) as resp, open(tmp, "wb") as f:
                while chunk := resp.read(1 << 20):
                    f.write(chunk)
        except urllib.error.URLError as e:
            tmp.unlink(missing_ok=True)
            print(f"  FAILED {name}: host '{urllib.parse.urlparse(dl).netloc}' -> {getattr(e, 'reason', e)}")
            failed += 1
            continue
        tmp.rename(target)
        manifest.append({"file": target.name, "bytes": target.stat().st_size, "expected": o.get("size"), "recordName": m["recordName"]})

    # validate every downloaded file with ffprobe
    for item in manifest:
        p = dest / item["file"]
        pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
                             "-of", "json", str(p)], capture_output=True, text=True)
        ok = pr.returncode == 0 and '"video"' in pr.stdout
        item["ffprobe_ok"] = ok
        if ok:
            j = json.loads(pr.stdout)
            v = next(s for s in j["streams"] if s["codec_type"] == "video")
            item.update(width=v["width"], height=v["height"], codec=v["codec_name"], duration=float(j["format"]["duration"]),
                        audio=any(s["codec_type"] == "audio" for s in j["streams"]))
        print(f"  ffprobe {'OK ' if ok else 'FAIL'} {item['file']} {item.get('width', '')}x{item.get('height', '')} {item.get('duration', 0):.1f}s")
        failed += 0 if ok else 1
    (dest.parent / "work").mkdir(exist_ok=True)
    (dest.parent / "work" / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
