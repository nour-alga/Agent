"""
Agent CSE — Génération automatique de rapport financier
Entrée  : 3 PDFs (comptes sociaux année N-2 / N-1 / N)
Sortie  : rapport Markdown structuré style expertise CSE cabinet haut de gamme
"""

import os
import sys
import anthropic
import pymupdf4llm
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

load_dotenv()  # charge automatiquement le fichier .env

# ── Configuration ──────────────────────────────────────────────────────────────
MODEL         = "claude-sonnet-4-6"
MAX_TOKENS    = 8000
TOKEN_LIMIT   = 150_000   # seuil d'alerte (200k = limite absolue du modèle)
CHARS_PER_TOK = 4         # estimation grossière : 1 token ≈ 4 caractères

# ── Prompt système (ton prompt docx intégral) ──────────────────────────────────
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

# ── Prompt utilisateur (structure du rapport) ──────────────────────────────────
RAPPORT_PROMPT = """Voici les comptes sociaux de l'entreprise sur 3 exercices consécutifs.

{annee_sections}

---

Génère un rapport d'expertise CSE complet structuré en slides selon le plan suivant :

---

## 1. SYNTHÈSE EXÉCUTIVE (2 slides max)
- 5 à 7 messages clés maximum
- Points d'alerte ⚠
- Lecture globale de la situation
- Questions clés à poser en réunion CSE

---

## 2. ANALYSE DE L'ACTIVITÉ DÉTAILLÉE
- Évolution du chiffre d'affaires (tableau détaillé N / N-1 / N-2 avec variations €  et %)
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


# ── Conversion PDF → Markdown ──────────────────────────────────────────────────
def pdf_to_markdown(pdf_path: str) -> str:
    """Convertit un PDF en Markdown propre via pymupdf4llm."""
    print(f"  📄 Conversion : {Path(pdf_path).name}")
    md = pymupdf4llm.to_markdown(pdf_path)
    print(f"     → {len(md):,} caractères | ~{len(md)//CHARS_PER_TOK:,} tokens estimés")
    return md


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOK


def check_token_budget(sections: dict) -> None:
    """Alerte si le total dépasse le seuil recommandé."""
    total_chars = sum(len(v) for v in sections.values())
    total_tokens = estimate_tokens(total_chars)
    print(f"\n📊 Budget tokens estimé : {total_tokens:,} / {TOKEN_LIMIT:,} recommandés")
    if total_tokens > TOKEN_LIMIT:
        print("  ⚠  Dépassement probable — envisage de tronquer les annexes longues")
    else:
        print("  ✅ Dans les limites — envoi direct possible")


# ── Construction du prompt utilisateur ────────────────────────────────────────
def build_user_prompt(markdowns: dict) -> str:
    sections = "\n\n".join(
        f"## Comptes sociaux — Exercice {annee}\n\n{md}"
        for annee, md in markdowns.items()
    )
    return RAPPORT_PROMPT.format(
        annee_sections=sections,
        today=date.today().strftime("%d/%m/%Y")
    )


# ── Appel API Anthropic ────────────────────────────────────────────────────────
def generate_report(user_prompt: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print(f"\n🤖 Envoi à {MODEL}…")
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text


# ── Sauvegarde du rapport ──────────────────────────────────────────────────────
def save_report(rapport: str, output_dir: str = "output") -> str:
    Path(output_dir).mkdir(exist_ok=True)
    filename = f"rapport_cse_{date.today().strftime('%Y%m%d')}.md"
    output_path = Path(output_dir) / filename
    output_path.write_text(rapport, encoding="utf-8")
    print(f"\n✅ Rapport sauvegardé : {output_path}")
    return str(output_path)


# ── Point d'entrée principal ───────────────────────────────────────────────────
def run(pdf_paths: list) -> str:
    """
    Prend une liste de 3 chemins PDF (ordre chronologique : N-2, N-1, N)
    et retourne le chemin du rapport généré.
    """
    if len(pdf_paths) != 3:
        raise ValueError("Exactement 3 PDFs requis (ex : 2022, 2023, 2024)")

    annees = ["N-2", "N-1", "N"]

    # Étape 1 — Conversion PDF → Markdown
    print("─── Étape 1/3 : Conversion PDF → Markdown ───")
    markdowns = {}
    for annee, path in zip(annees, pdf_paths):
        markdowns[annee] = pdf_to_markdown(path)

    # Étape 2 — Vérification du budget tokens
    print("\n─── Étape 2/3 : Vérification tokens ───")
    check_token_budget(markdowns)

    # Étape 3 — Génération du rapport via l'API
    print("\n─── Étape 3/3 : Génération du rapport ───")
    user_prompt = build_user_prompt(markdowns)
    rapport = generate_report(user_prompt)

    # Sauvegarde
    return save_report(rapport)


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage : python agent.py comptes_N-2.pdf comptes_N-1.pdf comptes_N.pdf")
        sys.exit(1)
    run(sys.argv[1:])