"""
Convertit un rapport Markdown existant en PDF professionnel.
Usage : python3 md_to_pdf.py output/rapport_cse_20260610.md
"""

import sys
import markdown as md_lib
from pathlib import Path
from weasyprint import HTML

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
strong { color: #1a1a1a; }
p { margin: 6px 0; }
ul, ol { margin: 6px 0; padding-left: 20px; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 16px 0; }
"""


def convert(md_path: str) -> str:
    path = Path(md_path)
    if not path.exists():
        print(f"❌ Fichier introuvable : {md_path}")
        sys.exit(1)

    print(f"📄 Lecture : {path.name}")
    md_content = path.read_text(encoding="utf-8")

    print("🔄 Conversion Markdown → HTML…")
    html_content = md_lib.markdown(
        md_content,
        extensions=["tables", "fenced_code", "nl2br"]
    )

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

    pdf_path = str(path.with_suffix(".pdf"))
    print("🖨  Génération PDF…")
    HTML(string=full_html).write_pdf(pdf_path)
    print(f"✅ PDF généré : {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python3 md_to_pdf.py chemin/rapport.md")
        sys.exit(1)
    convert(sys.argv[1])