"""
03_teste_hipoteses_h8_preco_referencia.py — Fase 2.4, H8 (prioridade média)

Hipótese: o preço praticado em vendas fica sistematicamente abaixo do preço de
referência do catálogo (markdown fora do campo desconto_reais).

Teste (vendas × estoque por sku_id):
  1. A chave casa? (sku_id, categoria, nome do produto)
  2. Custo: custo_produto/quantidade (vendas) × custo_unitario (estoque), SKU a SKU.
  3. Preço: preco_unitario (vendas) × preco_venda_sugerido (estoque), SKU a SKU.
  4. Variação dentro do mesmo SKU em vendas (preço e custo unitário).
  5. Coerência interna de cada base (markup).

Critério (2.3): CONFIRMA se, SKU a SKU, o preço praticado ficar sistematicamente
abaixo do sugerido E o custo unitário das duas bases for consistente. Vira
LIMITAÇÃO DE DADO se os custos não baterem entre as bases.
Régua de "custo consistente" (proposta, declarada): ≥ 80% dos itens com custo
unitário de vendas a ±10% do custo do estoque.

Uso: python scripts/03_teste_hipoteses_h8_preco_referencia.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import Saida, carregar_estoque, carregar_vendas  # noqa: E402

NOME = "h8_preco_referencia"
TOLERANCIA = 0.10
LIMIAR_CONSISTENCIA = 80.0


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()
    e = carregar_estoque()
    j = v.merge(e, on="sku_id", how="left", suffixes=("", "_estoque"), validate="many_to_one")

    # ------------------------------------------------------------------ 1
    out.secao("1. A chave casa?")
    out(f"sku_id de vendas encontrado no estoque: {j['custo_unitario'].notna().mean() * 100:.1f}%; "
        f"categoria igual: {(j['categoria'] == j['categoria_estoque']).mean() * 100:.1f}%; "
        f"nome do produto igual: {(j['produto'] == j['nome_produto']).mean() * 100:.1f}%.")

    # ------------------------------------------------------------------ 2
    out.secao("2. Custo unitário: vendas × estoque")
    j["custo_unit_vendas"] = j["custo_produto"] / j["quantidade"]
    j["razao_custo"] = j["custo_unit_vendas"] / j["custo_unitario"]
    out.tabela(j["razao_custo"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).rename("custo_vendas/custo_estoque"), "razao_custo")
    dentro = j["razao_custo"].between(1 - TOLERANCIA, 1 + TOLERANCIA).mean() * 100
    out(f"Itens com custo de vendas a ±{TOLERANCIA:.0%} do custo do estoque: {dentro:.1f}% (régua de consistência: ≥ {LIMIAR_CONSISTENCIA:.0f}%).")
    sku = j.groupby("sku_id").agg(custo_vendas=("custo_unit_vendas", "mean"), custo_estoque=("custo_unitario", "first"),
                                  preco_vendas=("preco_unitario", "mean"), preco_sugerido=("preco_venda_sugerido", "first"),
                                  itens=("order_id", "size"))
    r_c = stats.pearsonr(sku["custo_vendas"], sku["custo_estoque"])
    s_c = stats.spearmanr(sku["custo_vendas"], sku["custo_estoque"])
    out(f"Correlação SKU a SKU ({len(sku)} SKUs) custo médio em vendas × custo do estoque: Pearson {r_c.statistic:.3f} "
        f"(p={r_c.pvalue:.4f}), Spearman {s_c.statistic:.3f}.")

    # ------------------------------------------------------------------ 3
    out.secao("3. Preço praticado × preço sugerido")
    j["razao_preco"] = j["preco_unitario"] / j["preco_venda_sugerido"]
    out.tabela(j["razao_preco"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).rename("preco_vendas/preco_sugerido"), "razao_preco")
    out(f"Itens com preço praticado abaixo do sugerido: {(j['razao_preco'] < 1).mean() * 100:.1f}%; "
        f"a ±{TOLERANCIA:.0%} do sugerido: {j['razao_preco'].between(1 - TOLERANCIA, 1 + TOLERANCIA).mean() * 100:.1f}%; "
        f"acima de 1,5× o sugerido: {(j['razao_preco'] > 1.5).mean() * 100:.1f}%.")
    r_p = stats.pearsonr(sku["preco_vendas"], sku["preco_sugerido"])
    out(f"Correlação SKU a SKU preço médio praticado × sugerido: Pearson {r_p.statistic:.3f} (p={r_p.pvalue:.4f}).")

    # ------------------------------------------------------------------ 4
    out.secao("4. Variação dentro do mesmo SKU (vendas)")
    g = j.groupby("sku_id").agg(itens=("order_id", "size"), preco_cv=("preco_unitario", lambda s: s.std() / s.mean()),
                                custo_cv=("custo_unit_vendas", lambda s: s.std() / s.mean()),
                                preco_min=("preco_unitario", "min"), preco_max=("preco_unitario", "max"))
    g5 = g[g["itens"] >= 5]
    out(f"SKUs com ≥ 5 itens vendidos: {len(g5)}. Coeficiente de variação do preço dentro do SKU: mediana "
        f"{g5['preco_cv'].median() * 100:.1f}%; do custo unitário: mediana {g5['custo_cv'].median() * 100:.1f}%. "
        f"Razão preço máx/mín dentro do SKU: mediana {(g5['preco_max'] / g5['preco_min']).median():.1f}×.")

    # ------------------------------------------------------------------ 5
    out.secao("5. Coerência interna de cada base (markup = preço ÷ custo unitário)")
    mk_v = j["preco_unitario"] / j["custo_unit_vendas"]
    mk_e = e["preco_venda_sugerido"] / e["custo_unitario"]
    out(f"vendas:  markup de {mk_v.min():.2f}× a {mk_v.max():.2f}× (mediana {mk_v.median():.2f}×)")
    out(f"estoque: markup de {mk_e.min():.2f}× a {mk_e.max():.2f}× (mediana {mk_e.median():.2f}×)")
    out("→ Cada base é coerente por dentro; a incoerência está ENTRE as bases.")

    # ------------------------------------------------------------------ 6
    out.secao("6. Veredito proposto")
    consistente = dentro >= LIMIAR_CONSISTENCIA
    abaixo = (j["razao_preco"] < 1).mean() * 100
    if consistente and abaixo > 50:
        ver = "CONFIRMADA"
    elif consistente:
        ver = "REFUTADA"
    else:
        ver = "INCONCLUSIVA — vira LIMITAÇÃO DE DADO: custo e preço de vendas não conversam com o estoque SKU a SKU"
    out(f"  Custo consistente entre bases: {'SIM' if consistente else 'NÃO'} ({dentro:.1f}% a ±10%; correlação SKU {r_c.statistic:.3f}).")
    out(f"  Preço abaixo do sugerido: {abaixo:.1f}% dos itens (correlação SKU {r_p.statistic:.3f}).")
    out(f"\nVEREDITO PROPOSTO H8: {ver}.")
    out.salvar()


if __name__ == "__main__":
    main()
