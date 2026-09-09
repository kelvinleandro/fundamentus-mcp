from app.scrapers.properties import format_properties, parse_properties


HTML = """
<table id="tabelaFiiImoveis">
  <thead>
    <tr>
      <th>FII</th>
      <th>Imóvel</th>
      <th>Endereço</th>
      <th>Outras características</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>FIIABC</td>
      <td><a href="/imovel/edificio-central">Edifício Central</a></td>
      <td>Av. Brasil, 100</td>
      <td>Área: 1.000 m²</td>
    </tr>
    <tr style="display: none">
      <td>FIIFILTERED</td>
      <td><a href="/imovel/filtrado">Imóvel filtrado</a></td>
      <td>Rua Oculta, 10</td>
      <td>Não deve aparecer</td>
    </tr>
    <tr>
      <td>FIINOINFO</td>
      <td><a href="/imovel/galpao-norte">Galpão Norte</a></td>
      <td>Rua Norte, 20</td>
      <td></td>
    </tr>
  </tbody>
</table>
"""


def test_parse_properties_keeps_visible_rows_and_empty_characteristics() -> None:
    properties = parse_properties(HTML)

    assert properties == [
        {
            "fund": "FIIABC",
            "property_name": "Edifício Central",
            "address": "Av. Brasil, 100",
            "other_characteristics": "Área: 1.000 m²",
        },
        {
            "fund": "FIINOINFO",
            "property_name": "Galpão Norte",
            "address": "Rua Norte, 20",
            "other_characteristics": "",
        },
    ]


def test_format_properties_omits_empty_characteristics_line() -> None:
    properties = parse_properties(HTML)

    assert format_properties(properties) == (
        "FIIABC - Edifício Central\n"
        "Endereço: Av. Brasil, 100\n"
        "Outras características: Área: 1.000 m²\n"
        "\n----\n\n"
        "FIINOINFO - Galpão Norte\n"
        "Endereço: Rua Norte, 20"
    )