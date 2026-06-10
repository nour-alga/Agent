"""
Agent CSE — Génération automatique de rapport financier
Entrée  : 3 PDFs (comptes sociaux année N-2 / N-1 / N)
Sortie  : rapport Markdown structuré style expertise CSE cabinet haut de gamme
"""

import os
import sys
import time
import base64
import anthropic
import markdown as md_lib
from weasyprint import HTML
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
MODEL         = "claude-sonnet-4-6"
MAX_TOKENS    = 8000

# ── Prompt système ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un expert CSE senior spécialisé en analyse économique, financière et sociale des entreprises, avec une expérience équivalente à un cabinet de conseil haut de gamme.

Ta mission est de produire un rapport d'expertise CSE complet, structuré, pédagogique et stratégique, destiné à des élus du Comité Social et Économique.

Le rapport doit être directement exploitable en réunion CSE en vue d'assister les élus dans le cadre des consultations obligatoires, avec un objectif clair : permettre aux élus de comprendre, questionner et challenger la direction.

---

OBJECTIFS DU RAPPORT

- Fournir une analyse financière rigoureuse (activités/CA/ventes détaillés par nature ou analytique si disponibles, soldes intermédiaires de gestions, performances opérationnelles, taux de marges, structure des charges, analyse des bilans actifs immobilisés, circulants, trésorerie, comptes courants groupe, les passifs, capitaux propres, dettes financières, dettes circulantes, analyse des poids des actifs, analyse des immobilisations et vétusté des outils, analyse des poids des passifs…)

- Adopter une lecture stratégique (et non uniquement descriptive)

- Identifier les choix de gestion opérés par la direction

- Mettre en évidence les incohérences éventuelles

- Traduire les données en impacts concrets pour les salariés

- Générer des questions directement utilisables en réunion

---

MÉTHODOLOGIE OBLIGATOIRE

Pour chaque analyse :

1. Présenter les données sous forme de tableaux clairs :
   - Année N, N-1, N-2
   - Variation en valeur (k€) : N-1/N
   - Variation en pourcentage (%) : N-1/N

2. Les analyses doivent être pédagogiques avec une lecture experte et une lecture stratégique :
   - expliquer simplement
   - vulgariser pour des élus non experts
   - interprétation des chiffres
   - identification des causes
   - quels choix de gestion ?
   - quels arbitrages ?
   - impact social : conséquences pour les salariés, emploi, conditions de travail, rémunération...
   - rappel synthétique : reformulation des points clés, mise en tension (contradictions éventuelles)

---

EXIGENCE STRATÉGIQUE

Tu ne dois jamais te limiter à décrire.

Tu dois systématiquement :
- questionner les choix de gestion
- identifier les arbitrages implicites
- détecter les incohérences
- mettre en évidence les enjeux sociaux

---

POINT CRITIQUE

Chaque partie doit répondre implicitement à :
"Qu'est-ce que les élus peuvent dire en réunion avec cette information ?"

---

STYLE RÉDACTIONNEL

- ton professionnel et pédagogique
- phrases claires et compréhensibles
- éviter le jargon inutile
- structurer en paragraphes fluides (pas de listes excessives)
- intégrer des formulations réutilisables en réunion
- utiliser des tableaux Markdown pour toutes les données chiffrées
- signaler les alertes avec ⚠"""

# ── Prompt utilisateur ─────────────────────────────────────────────────────────
RAPPORT_PROMPT = """Voici les comptes sociaux de l'entreprise sur 3 exercices consécutifs (PDFs joints).

Génère un rapport d'expertise CSE complet structuré selon le plan suivant :

---

## 1. SYNTHÈSE EXÉCUTIVE (2 slides max)
- 5 à 7 messages clés maximum
- Points d'alerte ⚠
- Lecture globale de la situation
- Questions clés à poser en réunion CSE

---

## 2. ANALYSE DE L'ACTIVITÉ DÉTAILLÉE
- Évolution du chiffre d'affaires (tableau détaillé N / N-1 / N-2 avec variations € et %)
- Analyse des données analytiques si disponibles
- Analyse des variations (volume, prix, clients)
- Dépendance économique
- Rappel synthétique

---

## 3. SOLDES INTERMÉDIAIRES DE GESTION — PARTIE I (Production → EBE)
- Calculs détaillés des SIG en valeur et % : Production de l'exercice, Marge commerciale, Valeur Ajoutée, EBE
- Analyse des indicateurs : marge commerciale/CA, VA/CA, EBE/CA, EBE/VA
- Explication des variations
- Rappel stratégique

---

## 4. ANALYSE DES CHARGES EXTERNES
- Détail complet par poste : sous-traitance, intérim, honoraires, frais groupe, autres charges externes
- Évolution et poids dans le CA
- Analyse critique : externalisation, stratégie groupe, arbitrage salaires vs prestataires
- Rappel offensif

---

## 5. MASSE SALARIALE ET EMPLOI
- Évolution des effectifs (tableau par catégorie si disponible)
- Évolution de la masse salariale
- Coût moyen par salarié
- Comparaison charges externes vs salaires
- Lecture sociale : participation, pouvoir d'achat, conditions de travail
- Rappel

---

## 6. SOLDES INTERMÉDIAIRES DE GESTION — PARTIE II (EBE → REX)
- Calculs détaillés des SIG : EBE → Résultat d'exploitation
- Analyse des indicateurs : REX/CA, REX/VA
- Détail des dotations (amortissements et provisions) et reprises, solde et impacts
- Détail des autres charges et produits d'exploitation si disponibles
- Explication des variations
- Rappel stratégique

---

## 7. ANALYSE DES DIFFÉRENTS RÉSULTATS
- Analyse détaillée des résultats (exploitation, financier, exceptionnel) en valeur et %
- Contributions de chaque résultat au résultat net
- Détail des postes financiers et exceptionnels et leurs explications si disponibles

---

## 8. FLUX FINANCIERS INTRA-GROUPE
- Nature des flux : management fees, refacturations, redevances de marque, intérêts, dividendes
- Évolution et impact sur la performance
- Dépendance au groupe
- Rappel critique

---

## 9. ANALYSE DU BILAN ACTIF-PASSIF, TRÉSORERIE ET FINANCEMENT
- Analyse des bilans : actifs immobilisés, circulants ; poids des actifs
- Analyse des immobilisations, amortissements et vétusté des outils
- Analyse des passifs : capitaux propres, dettes financières, dettes circulantes ; poids des passifs
- Analyse trésorerie, comptes courants groupe, trésorerie retraitée
- Évolution de la trésorerie, niveau d'endettement, capacité de financement
- Calcul et analyse des flux de trésorerie
- L'entreprise peut-elle financer des augmentations ? ou ne le souhaite-t-elle pas ?
- Rappel

---

## 10. SYNTHÈSE STRATÉGIQUE
- Lecture globale
- Identification des choix de gestion
- Analyse des contradictions
- Risques pour les salariés

---

## 11. PRÉCONISATIONS CSE
- Questions à poser à la direction (format **Q1**, **Q2**…)
- Axes de négociation
- Points de vigilance
- Projet de résolution à soumettre en séance plénière

---

Date du rapport : {today}
Document strictement confidentiel — réservé aux membres du CSE"""


# ── Chargement PDF en base64 ───────────────────────────────────────────────────
def load_pdf_base64(pdf_path: str) -> str:
    """Lit un PDF et le encode en base64 pour l'API Anthropic."""
    print(f"  📄 Chargement : {Path(pdf_path).name} ({Path(pdf_path).stat().st_size / 1024 / 1024:.1f} MB)")
    with open(pdf_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


# ── Appel API Anthropic avec PDFs natifs ───────────────────────────────────────
def generate_report(pdf_paths: list) -> str:
    """
    Envoie les 3 PDFs directement à Claude via l'API — exactement comme
    le chat Claude.ai — Claude gère lui-même la lecture, l'OCR si nécessaire,
    et l'extraction des données.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Construction du contenu : 3 PDFs + le prompt
    content = []

    annees = ["Exercice N-2 (le plus ancien)", "Exercice N-1", "Exercice N (le plus récent)"]
    for annee, path in zip(annees, pdf_paths):
        content.append({
            "type": "text",
            "text": f"--- {annee} ---"
        })
        content.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": load_pdf_base64(path)
            }
        })

    # Ajout du prompt de génération
    content.append({
        "type": "text",
        "text": RAPPORT_PROMPT.format(today=date.today().strftime("%d/%m/%Y"))
    })

    print(f"\n🤖 Envoi à {MODEL} (3 PDFs joints)…")
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )
    return response.content[0].text



# ── CSS du rapport PDF ────────────────────────────────────────────────────────
PDF_CSS = """
@page {
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
    @bottom-center {
        content: "Document confidentiel — CSE — Page " counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #888;
    }
}
body {
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1a1a1a;
}
h1 {
    font-size: 18pt;
    color: #1a3a5c;
    border-bottom: 3px solid #1a3a5c;
    padding-bottom: 6px;
    margin-top: 30px;
}
h2 {
    font-size: 13pt;
    color: #1a3a5c;
    border-left: 4px solid #e85d24;
    padding-left: 8px;
    margin-top: 20px;
}
h3 {
    font-size: 11pt;
    color: #333;
    margin-top: 14px;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 8.5pt;
}
th {
    background-color: #1a3a5c;
    color: white;
    padding: 6px 8px;
    text-align: left;
    font-weight: bold;
}
td {
    padding: 5px 8px;
    border-bottom: 1px solid #dde;
}
tr:nth-child(even) td {
    background-color: #f5f7fa;
}
blockquote {
    background: #fff8e1;
    border-left: 4px solid #f9a825;
    padding: 8px 12px;
    margin: 10px 0;
    font-size: 9pt;
    color: #555;
}
code {
    background: #f4f4f4;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 8.5pt;
}
strong {
    color: #1a1a1a;
}
p { margin: 6px 0; }
ul, ol { margin: 6px 0; padding-left: 20px; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 16px 0; }
.page-break { page-break-after: always; }
"""

# ── Conversion Markdown → PDF ──────────────────────────────────────────────────
def markdown_to_pdf(md_path: str) -> str:
    """Convertit le rapport Markdown en PDF professionnel."""
    print(f"\n📄 Conversion en PDF…")
    
    md_content = Path(md_path).read_text(encoding="utf-8")
    
    # Conversion Markdown → HTML
    html_content = md_lib.markdown(
        md_content,
        extensions=["tables", "fenced_code", "nl2br"]
    )
    
    # HTML complet avec CSS
    full_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <style>{PDF_CSS}</style>
</head>
<body>
{html_content}
</body>
</html>"""
    
    # Génération PDF
    pdf_path = md_path.replace(".md", ".pdf")
    HTML(string=full_html).write_pdf(pdf_path)
    print(f"✅ PDF généré : {pdf_path}")
    return pdf_path

# ── Sauvegarde du rapport ──────────────────────────────────────────────────────
def save_report(rapport: str, output_dir: str = "output") -> str:
    Path(output_dir).mkdir(exist_ok=True)
    filename = f"rapport_cse_{date.today().strftime('%Y%m%d')}.md"
    output_path = Path(output_dir) / filename
    output_path.write_text(rapport, encoding="utf-8")
    print(f"\n✅ Rapport sauvegardé : {output_path}")
    return str(output_path)


# ── Chronomètre ───────────────────────────────────────────────────────────────
def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}m {secs:.1f}s"


# ── Point d'entrée principal ───────────────────────────────────────────────────
def run(pdf_paths: list) -> str:
    if len(pdf_paths) != 3:
        raise ValueError("Exactement 3 PDFs requis (ordre chronologique : N-2, N-1, N)")

    t_start = time.time()

    # Étape 1 — Chargement et envoi des PDFs à Claude
    print("─── Étape 1/2 : Chargement des PDFs ───")
    t0 = time.time()
    # (le chargement se fait dans generate_report, on mesure tout ensemble)

    print("\n─── Étape 2/2 : Génération du rapport ───")
    rapport = generate_report(pdf_paths)
    t_api = time.time() - t0

    # Sauvegarde Markdown
    t0 = time.time()
    output_path = save_report(rapport)
    t_save = time.time() - t0

    # Conversion PDF
    t0 = time.time()
    pdf_path = markdown_to_pdf(output_path)
    t_pdf = time.time() - t0

    # Résumé des temps
    total = time.time() - t_start
    print("\n─── ⏱ Temps d'exécution ───")
    print(f"  Chargement PDFs + appel API : {format_duration(t_api)}")
    print(f"  Sauvegarde Markdown         : {format_duration(t_save)}")
    print(f"  Conversion PDF              : {format_duration(t_pdf)}")
    print(f"  ──────────────────────────────────────")
    print(f"  ⏱ Total                     : {format_duration(total)}")

    print(f"\n📁 Fichiers générés :\n   Markdown : {output_path}\n   PDF      : {pdf_path}")
    return output_path, pdf_path


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage : python3 src/agent.py comptes_N-2.pdf comptes_N-1.pdf comptes_N.pdf")
        sys.exit(1)
    run(sys.argv[1:])