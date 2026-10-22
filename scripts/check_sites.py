import json, os, smtplib, subprocess, urllib.request, urllib.error
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def load(path, fallback):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return fallback

def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": "GOZT-Monitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            code = r.getcode()
            return {"ok": 200 <= code < 400, "http_status": code, "error": None}
    except urllib.error.HTTPError as e:
        return {"ok": 200 <= e.code < 400, "http_status": e.code, "error": "HTTP error"}
    except Exception as e:
        return {"ok": False, "http_status": None, "error": type(e).__name__}

def email_alert(subject, body):
    host, user, password, recipient = (os.getenv(k) for k in ("SMTP_HOST","SMTP_USER","SMTP_PASSWORD","ALERT_EMAIL"))
    if not all((host,user,password,recipient)):
        print("Correo omitido: configure los secretos SMTP opcionales.")
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, recipient
    msg.set_content(body)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT") or "587"), timeout=20) as server:
        server.starttls()
        server.login(user,password)
        server.send_message(msg)

sites = [s for s in load(ROOT/"sites.json",[]) if s.get("enabled") and s.get("url")]
old = load(ROOT/"status.json",{"sites":{}})
current, transitions = {}, []
for site in sites:
    result = probe(site["url"])
    result["name"] = site.get("name",site["id"])
    current[site["id"]] = result
    before = old.get("sites",{}).get(site["id"])
    if before is not None and before.get("ok") != result.get("ok"):
        transitions.append((site,result))
stamp = datetime.now(timezone.utc).isoformat()
(ROOT/"status.json").write_text(json.dumps({"checked_at":stamp,"sites":current},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for site,result in transitions:
    state = "RECUPERADO" if result["ok"] else "SIN RESPUESTA"
    try:
        email_alert(f"[GOZT] {state}: {site.get('name',site['id'])}",f"Sistema: {site.get('name',site['id'])}\nURL: {site['url']}\nEstado: {state}\nDetalle: {result.get('http_status') or result.get('error')}\nHora UTC: {stamp}")
    except Exception as e:
        print("No se pudo enviar correo:",type(e).__name__)

subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
subprocess.run(["git","add","status.json"],check=True)
if subprocess.run(["git","diff","--cached","--quiet"]).returncode != 0:
    subprocess.run(["git","commit","-m","Update monitored system status"],check=True)
    subprocess.run(["git","push"],check=True)
