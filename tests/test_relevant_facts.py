from app.scrapers.relevant_facts import format_relevant_facts, parse_relevant_facts


HTML = """
<table id="comunicados">
  <thead>
    <tr>
      <th>Data</th>
      <th>Empresa</th>
      <th>Tipo</th>
      <th>Descricao</th>
      <th>Download</th>
      <th>Analisar</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>09/09/2026</td>
      <td>ACME S.A.</td>
      <td>FR</td>
      <td>Resultado do segundo trimestre</td>
      <td><a href="https://www.fundamentus.com.br/docs/acme.pdf">PDF</a></td>
      <td><a href="analise/acme">Ver detalhes</a></td>
    </tr>
    <tr>
      <td>08/09/2026</td>
      <td>Outra S.A.</td>
      <td>ITR</td>
      <td>Informacao trimestral</td>
      <td><a href="https://www.fundamentus.com.br/docs/outra.pdf">PDF</a></td>
      <td><a href="analise/outra">Analisar</a></td>
    </tr>
  </tbody>
</table>
"""


def test_parse_relevant_facts_keeps_only_fr_and_extracts_links() -> None:
    facts = parse_relevant_facts(HTML)

    assert facts == [
        {
            "date": "09/09/2026",
            "company": "ACME S.A.",
            "description": "Resultado do segundo trimestre",
            "download_url": "https://www.fundamentus.com.br/docs/acme.pdf",
            "analysis": "Ver detalhes",
        }
    ]


def test_format_relevant_facts_matches_public_response() -> None:
    facts = parse_relevant_facts(HTML)

    assert format_relevant_facts(facts) == (
        "09/09/2026 - ACME S.A. (Ver detalhes)\n"
        "Resultado do segundo trimestre\n"
        "Url para Download do PDF: "
        "https://www.fundamentus.com.br/docs/acme.pdf"
    )


def test_parse_relevant_facts_accepts_detalhes_header() -> None:
    facts = parse_relevant_facts(HTML)

    assert facts[0]["analysis"] == "Ver detalhes"
