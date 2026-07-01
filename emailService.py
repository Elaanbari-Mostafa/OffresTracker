import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

COLUMNS = [
    ("Titre", "titre"),
    ("Administration", "administration"),
    ("Grade", "grade"),
    ("Spécialité", "specialite"),
    ("Code", "code_concours"),
    ("Limite", "limite_depot"),
]

def _build_email_html(offres: list[dict]) -> str:
    thead = "".join(f"<th style='padding:10px 8px;text-align:left;font-size:13px;'>{label}</th>" for label, _ in COLUMNS)
    trows = ""
    for o in offres:
        cells = ""
        for _, key in COLUMNS:
            val = o.get(key, "")
            if key == "titre":
                val = f'<a href="{o["url"]}" style="color:#1a73e8;text-decoration:none;font-weight:600;">{val}</a>'
            cells += f"<td style='padding:8px;font-size:13px;border-bottom:1px solid #e0e0e0;'>{val}</td>"
        trows += f"<tr>{cells}</tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background-color:#f0f2f5;">
<div style="max-width:1420px;margin:0 auto;padding:24px 16px;font-family:'Segoe UI',Arial,sans-serif;">
    <h2 style="color:#1a1a2e;font-size:20px;margin:0 0 16px 0;">
        {len(offres)} nouvelle(s) offre(s) trouvée(s)
    </h2>
    <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">
        <thead><tr style="background:#1a1a2e;color:#fff;">{thead}</tr></thead>
        <tbody>{trows}</tbody>
    </table>
    <p style="color:#999;font-size:11px;text-align:center;margin-top:20px;">
        OffresTracker &mdash; Scraping automatique emploi-public.ma
    </p>
</div></body></html>"""


def envoyer_email(offres: list[dict]) -> None:
    if not offres:
        print("Aucune nouvelle offre à envoyer.")
        return

    sujet = f"{len(offres)} nouvelle(s) offre(s) d'emploi trouvée(s) !"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = sujet
    msg.attach(MIMEText(_build_email_html(offres), "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email envoyé avec succès !")
    except Exception as e:
        print(f"Tentative TLS (587) échouée : {e}")
        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            print("Email envoyé avec succès (SSL/465) !")
        except Exception as e2:
            print(f"Erreur lors de l'envoi de l'email : {e2}")
