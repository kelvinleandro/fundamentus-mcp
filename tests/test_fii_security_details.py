from app.scrapers.security_search import _parse_fii_details


FII_HTML = """
<table class="w728">
  <tr><td>FII</td><td>BLMO11</td><td>Cotação</td><td>92,51</td></tr>
  <tr><td>Nome</td><td>VBI OFFICE FUND II</td><td>Data últ cot</td><td>09/09/2026</td></tr>
  <tr><td>Mandato</td><td></td><td>Segmento</td><td>Escritórios</td></tr>
</table>
<table class="w728"><tr><td>Valor de mercado</td><td>92.030.200</td><td>Nro. Cotas</td><td>994.814</td></tr></table>
<table class="w728">
  <tr><td class="nivel1">Oscilações</td><td></td><td class="nivel1">Indicadores</td><td></td></tr>
  <tr><td>Dia</td><td>0,00%</td><td>FFO Yield</td><td>6,97%</td></tr>
  <tr><td>Mês</td><td>-2,25%</td><td>P/VP</td><td>0,94</td></tr>
  <tr><td class="nivel1">Resultado</td><td></td><td></td><td></td></tr>
  <tr><td></td><td></td><td>Receita</td><td>8.267.770</td><td>Receita</td><td>2.217.730</td></tr>
  <tr><td class="nivel1">Balanço Patrimonial</td><td></td><td></td><td></td></tr>
  <tr><td></td><td></td><td>Ativos</td><td>98.561.500</td><td>Patrim Líquido</td><td>97.939.400</td></tr>
</table>
<table class="w728"><tr><td class="nivel1">Composição dos Ativos</td></tr></table>
<table class="w728">
  <tr><td class="nivel1">Imóveis</td></tr>
  <tr><td>Qtd imóveis</td><td>1</td><td>Área (m2)</td><td>7.893</td><td>Cap Rate</td><td>9,0%</td></tr>
</table>
"""


def test_parse_fii_details_uses_fii_schema() -> None:
    result = _parse_fii_details(FII_HTML)

    assert result["geral"]["FII"] == "BLMO11"
    assert result["geral"]["Mandato"] == ""
    assert result["indicadores"]["P/VP"] == "0,94"
    assert result["resultado"]["ultimos_12_meses"]["Receita"] == "8.267.770"
    assert result["balanco_patrimonial"]["Ativos"] == "98.561.500"
    assert result["imoveis"]["Qtd imóveis"] == "1"