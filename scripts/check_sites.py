import json, os, smtplib, subprocess, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY_LIMIT = 2016  # Aproximadamente 7 días a intervalos de 5 minutos

def load(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback

def stamp_now():
    return datetime.now(timezone.utc).isoformat()

def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": "GOZT-Monitor/1.2"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            code = r.getcode()
            return {"ok": 200 <= code < 400, "http_status": code, "error": None,
                    "duration_ms": round((time.monotonic() - started) * 1000)}
    except urllib.error.HTTPError as e:
        return {"ok": 200 <= e.code < 400, "http_status": e.code, "error": "HTTP error",
                "duration_ms": round((time.monotonic() - started) * 1000)}
    except Exception as e:
        return {"ok": False, "http_status": None, "error": type(e).__name__,
                "duration_ms": round((time.monotonic() - started) * 1000)}

def email_alert(subject, body):
    host, user, password, recipient = (os.getenv(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL"))
    if not all((host, user, password, recipient)):
        print("Correo omitido: alertas por correo no configuradas.")
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, recipient
    msg.set_content(body)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT") or "587"), timeout=20) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)

sites = [s for s in load(ROOT / "sites.json", []) if s.get("enabled") and s.get("url")]
old = load(ROOT / "status.json", {"sites": {}})
history = load(ROOT / "history.json", {"samples": []})
samples = history.get("samples", [])
current, transitions, new_samples = {}, [], []
for site in sites:
    result = probe(site["url"])
    result["name"] = site.get("name", site["id"])
    result["checked_at"] = stamp_now()
    current[site["id"]] = result
    sample = {"id": site["id"], "name": result["name"], "checked_at": result["checked_at"],
              "ok": result["ok"], "http_status": result["http_status"],
              "duration_ms": result["duration_ms"], "error": result["error"]}
    new_samples.append(sample)
    before = old.get("sites", {}).get(site["id"])
    if before is not None and before.get("ok") != result.get("ok"):
        transitions.append((site, result))

stamp = stamp_now()
(ROOT / "status.json").write_text(
    json.dumps({"checked_at": stamp, "sites": current}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8")
samples.extend(new_samples)
# Conservar la ventana reciente y limitar el tamaño del archivo.
cutoff = datetime.now(timezone.utc) - timedelta(days=7)
kept = []
for sample in samples:
    try:
        when = datetime.fromisoformat(sample.get("checked_at", "").replace("Z", "+00:00"))
        if when >= cutoff:
            kept.append(sample)
    except (ValueError, TypeError):
        continue
(ROOT / "history.json").write_text(
    json.dumps({"updated_at": stamp, "retention_days": 7,
                "samples": kept[-HISTORY_LIMIT:]}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8")

for site, result in transitions:
    state = "RECUPERADO" if result["ok"] else "SIN RESPUESTA"
    try:
        email_alert(f"[GOZT] {state}: {site.get('name', site['id'])}",
                    f"Sistema: {site.get('name', site['id'])}\nURL: {site['url']}\nEstado: {state}\nDetalle: {result.get('http_status') or result.get('error')}\nHora UTC: {stamp}")
    except Exception as e:
        print("No se pudo enviar correo:", type(e).__name__)

subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "status.json", "history.json"], check=True)
if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
    subprocess.run(["git", "commit", "-m", "Update monitoring status and history"], check=True)
    subprocess.run(["git", "push"], check=True)
