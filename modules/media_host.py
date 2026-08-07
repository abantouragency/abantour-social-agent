"""
media_host.py — uploads the finished reel to a PUBLIC url so Instagram Graph API
can publish it. Three backends, switch via settings/env:
  - "ftp": your own host (abantour.ir) via FTP  [recommended, permanent url]
  - "catbox": free ephemeral host (catbox.moe)  [no creds, easy test]
  - "r2": Cloudflare R2 (s3-compatible, durable) [needs creds]
Returns a public https URL string.
"""
import os, sys, json, urllib.request, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))


def _ftp_upload(local_path, remote_name):
    import ftplib
    host = os.environ.get("FTP_HOST", "")
    user = os.environ.get("FTP_USER", "")
    pw = os.environ.get("FTP_PASS", "")
    remote_dir = os.environ.get("FTP_REMOTE_DIR", "/public_html/reels")
    if not host or not user:
        return None
    with ftplib.FTP(host, user, pw) as ftp:
        try:
            ftp.cwd(remote_dir)
        except Exception:
            pass
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_name}", f)
    base = os.environ.get("FTP_PUBLIC_BASE", "https://abantour.ir/reels")
    return f"{base.rstrip('/')}/{remote_name}"


def _catbox_upload(local_path):
    url = "https://catbox.moe/api.php"
    data = urllib.parse.urlencode({"reqtype": "fileupload"}).encode()
    with open(local_path, "rb") as f:
        import urllib.request as u
        req = u.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
        # multipart needed; use simple form
    # catbox requires multipart; do it properly
    import requests
    with open(local_path, "rb") as f:
        r = requests.post(url, data={"reqtype": "fileupload"},
                          files={"fileToUpload": f}, timeout=60)
    if r.status_code == 200 and r.text.startswith("https://"):
        return r.text.strip()
    return None


def _r2_upload(local_path, remote_name):
    try:
        import boto3
    except Exception:
        return None
    import datetime
    ak = os.environ.get("R2_ACCESS_KEY", "")
    sk = os.environ.get("R2_SECRET_KEY", "")
    bkt = os.environ.get("R2_BUCKET", "")
    endp = os.environ.get("R2_ENDPOINT", "")
    pub = os.environ.get("R2_PUBLIC_URL", "")
    if not (ak and sk and bkt and endp):
        return None
    s3 = boto3.client("s3", aws_access_key_id=ak, aws_secret_access_key=sk,
                      endpoint_url=endp, region_name="auto")
    s3.upload_file(local_path, bkt, remote_name,
                   ExtraArgs={"ContentType": "video/mp4"})
    return f"{pub.rstrip('/')}/{remote_name}"


def upload(local_path, backend=None, remote_name=None):
    backend = backend or os.environ.get("MEDIA_HOST_BACKEND", "catbox")
    remote_name = remote_name or os.path.basename(local_path)
    if backend == "ftp":
        return _ftp_upload(local_path, remote_name)
    if backend == "r2":
        return _r2_upload(local_path, remote_name)
    # default catbox
    try:
        return _catbox_upload(local_path)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("media_host loaded. Set MEDIA_HOST_BACKEND and creds to use.")
