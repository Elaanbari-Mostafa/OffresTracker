import requests
from bs4 import BeautifulSoup
from databaseService import supabase
from emailService import envoyer_email

MOTS_CLES = [
    "dotnet", ".net", "exploitation", "production", "génie logiciel", "développeur",
    "ingénieur", "informatique", "data", "analyste", "python", "java", "c#", "javascript",
    "fullstack", "développement", "web", "mobile", "backend", "frontend", "cloud", "devops",
    "sql", "nosql",
]


def scraper_site():
    url_site = "https://www.emploi-public.ma"
    concours_url = url_site + "/fr/concours-liste"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        reponse = requests.get(concours_url, headers=headers)
        reponse.raise_for_status()
    except Exception as e:
        raise Exception(f"Erreur lors de la requête HTTP : {e}")

    soup = BeautifulSoup(reponse.text, "html.parser")
    offres_trouvees = []

    page_number = soup.find("ul", class_="pagination").find_all("li")[-2].get_text(strip=True)
    for page in range(1, int(page_number) + 1):
        url_page = f"{concours_url}?page={page}"
        reponse_page = requests.get(url_page, headers=headers)
        soup_page = BeautifulSoup(reponse_page.text, "html.parser")

        articles = [
            article
            for article in soup_page.find_all("div", class_="s-item")
            if (
                (btn := article.select_one("a > div.card-body > div.card--btn > div"))
                and btn.get_text(strip=True) == "Annonce"
            )
        ]

        for article in articles:
            titre = article.select_one("a > div.card-body > h2").get_text(strip=True)
            url_offre = url_site + article.select_one("a")["href"]
            uuid_offre = url_offre.split("/")[-1]
            limit_depot = article.select_one(
                "a > div.card-footer > div:nth-child(2)"
            ).get_text(strip=True).replace("\n", "").replace("Limite de dépôt : ", "")

            reponse_offre = requests.get(url_offre, headers=headers)
            soup_offre = BeautifulSoup(reponse_offre.text, "html.parser")

            description = soup_offre.select(
                "#read_content > div.row.s-content > div.col-12.col-md-8 > div:nth-child(1) > ul > li"
            )

            specialite = description[0].get_text(strip=True).replace("Spécialité :", "")
            for cle in MOTS_CLES:
                if cle.lower() in titre.lower() or cle.lower() in specialite.lower():
                    grade = description[1].get_text(strip=True).replace("\n", "").replace("Grade :", "")
                    code_concours = description[-1].get_text(strip=True).replace("\n", "").replace("Code du concours :", "")
                    administration = soup_offre.select_one(
                        "#read_content > div.row.s-content > div.col-12.col-md-4 > div > h3:nth-child(2)"
                    ).get_text(strip=True).replace("Administration qui recrute", "")

                    offres_trouvees.append({
                        "id": uuid_offre,
                        "titre": titre,
                        "url": url_offre,
                        "limite_depot": limit_depot,
                        "administration": administration,
                        "grade": grade,
                        "code_concours": code_concours,
                        "specialite": specialite,
                    })
                    break

    return offres_trouvees


def filtrer_et_sauvegarder(offres):
    nouvelles_offres_pertinentes = []

    for offre in offres:
        result = supabase.table("offres_emploi").select("id").eq("id", offre["id"]).execute()

        if len(result.data) == 0:
            offre_to_db = {
                "id": offre["id"],
                "titre": offre["titre"],
                "url": offre["url"],
                "limite_depot": offre["limite_depot"],
                "administration": offre["administration"],
                "grade": offre["grade"],
                "code_concours": offre["code_concours"],
                "specialite": offre["specialite"],
            }
            supabase.table("offres_emploi").insert(offre_to_db).execute()
            nouvelles_offres_pertinentes.append(offre)

    return nouvelles_offres_pertinentes


if __name__ == "__main__":
    print("Démarrage du scraping...")
    toutes_les_offres = scraper_site()
    nouvelles = filtrer_et_sauvegarder(toutes_les_offres)
    envoyer_email(nouvelles)
    print("Terminé.")
