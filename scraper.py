import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client

# --- CONFIGURATION (Récupérée depuis GitHub Actions) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

# Initialisation de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Mots-clés à rechercher (en minuscules)
MOTS_CLES = [
    "dotnet", ".net", "exploitation", "production", "génie logiciel", "développeur",
    "ingénieur", "informatique", "data", "analyste", "python", "java", "c#", "javascript", "fullstack", "developpement", "web", "mobile", "backend", "frontend", "cloud", "devops", "sql", "nosql"
    ]

def scraper_site():
    url_site = "https://www.emploi-public.ma"
    concours_url = url_site + "/fr/concours-liste"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        reponse = requests.get(concours_url, headers=headers)
        reponse.raise_for_status()
    except Exception as e:
        raise Exception(f"Erreur lors de la requête HTTP : {e}")

    soup = BeautifulSoup(reponse.text, 'html.parser')
    offres_trouvees = []

    page_number = soup.find("ul", class_="pagination").find_all("li")[-2].get_text(strip=True)
    for page in range(1, int(page_number) + 1):
        url_page = f"{concours_url}?page={page}"
        reponse_page = requests.get(url_page, headers=headers)
        soup_page = BeautifulSoup(reponse_page.text, 'html.parser')

        
        articles = [
            article
            for article in soup_page.find_all('div', class_='s-item')
            if (
                (btn := article.select_one("a > div.card-body > div.card--btn > div"))
                and btn.get_text(strip=True) == "Annonce"
            )
        ]

        for article in articles:
            titre = article.select_one("a > div.card-body > h2").get_text(strip=True)
            url_offre = "https://www.emploi-public.ma/fr/concours/details/71a531e3-204b-4323-bf63-0922acbdd3c8" #url_site + article.select_one("a")["href"]
            uuid_offre = url_offre.split("/")[-1]
            limit_depot = article.select_one("a > div.card-footer > div:nth-child(2)").get_text(strip=True).replace("\n", "").replace("Limite de dépôt : ","")
            
            reponse_page = requests.get(url_offre, headers=headers)
            soup_page = BeautifulSoup(reponse_page.text, 'html.parser')

            description = soup_page.select("#read_content > div.row.s-content > div.col-12.col-md-8 > div:nth-child(1) > ul > li")
            
            Spécialité = description[0].get_text(strip=True).replace("Spécialité :",'')
            for cle in MOTS_CLES:
                if cle.lower() in titre.lower() or cle.lower() in Spécialité.lower():
                    grade = description[1].get_text(strip=True).replace("\n", "").replace("Grade :","")
                    code_concours = description[-1].get_text(strip=True).replace("\n", "").replace("Code du concours :","")
                    administration = soup_page.select_one("#read_content > div.row.s-content > div.col-12.col-md-4 > div > h3:nth-child(2)").get_text(strip=True).replace("Administration qui recrute",'')
                    
                    offres_trouvees.append({"id": uuid_offre, "titre": titre, "url": url_offre, "limite_depot": limit_depot, "administration": administration,
                                            "grade": grade, "code_concours": code_concours, "specialite": Spécialité})
                    break
            
            return offres_trouvees
            break
            
        break
            
            # offres_trouvees.append({"titre": titre, "url": url_offre})
        
       


def filtrer_et_sauvegarder(offres):
    nouvelles_offres_pertinentes = []
    
    for offre in offres:
        result = supabase.table("offres_emploi").select("id").eq("id", offre['id']).execute()
        
        if len(result.data) == 0:
            offre_to_db =  {
                "id": offre['id'], "titre": offre['titre'], "url": offre['url'], "limite_depot": offre['limite_depot'], "administration": offre['administration'], "grade": offre['grade'], "code_concours": offre['code_concours'], "specialite": offre['specialite']}
            supabase.table("offres_emploi").insert(offre_to_db).execute()
            nouvelles_offres_pertinentes.append(offre)
    
    print("Nouvelles offres pertinentes trouvées :", len(nouvelles_offres_pertinentes))
    return nouvelles_offres_pertinentes

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
        cells = "".join(
            f"<td style='padding:8px;font-size:13px;border-bottom:1px solid #e0e0e0;'>"
            f"{'<a href=\"' + o['url'] + '\" style=\"color:#1a73e8;text-decoration:none;font-weight:600;\">' + o['titre'] + '</a>' if key == 'titre' else o.get(key, '')}"
            f"</td>"
            for _, key in COLUMNS
        )
        trows += f"<tr>{cells}</tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background-color:#f0f2f5;">
<div style="max-width:800px;margin:0 auto;padding:24px 16px;font-family:'Segoe UI',Arial,sans-serif;">
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

if __name__ == "__main__":
    print("Démarrage du scraping...")
    toutes_les_offres = scraper_site()
    nouvelles = filtrer_et_sauvegarder(toutes_les_offres)
    envoyer_email(nouvelles)
    #print(nouvelles[0])
    print("Terminé.")