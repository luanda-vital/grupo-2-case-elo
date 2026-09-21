"""
03_teste_hipoteses_h3a_devolucoes.py — Fase 2.4, H3a

Hipótese: a devolução (14,9% dos itens) está concentrada em categorias, SKUs,
fornecedores ou canais identificáveis — e portanto tem alavanca de ação.

Teste (só pagamento_aprovado; join com estoque por sku_id):
  1. Taxa geral + checagem de coerência (itens não aprovados marcados devolvidos).
  2. Taxa por 11 cortes: categoria, subcategoria, canal, mês, fornecedor, método
     de pagamento, faixa de preço, faixa de desconto, faixa de prazo de entrega,
     faixa de lead time do fornecedor, status atual de estoque. Qui-quadrado +
     V de Cramér + amplitude.
  3. Motivos × categoria e × canal (inclui checagem de coerência do motivo).
  4. Corte adicional (paradoxo de Simpson): células canal × categoria e
     subcategoria / canal DENTRO de cada categoria — para ver se a homogeneidade
     no agregado não esconde efeitos que se compensam.
  5. Exposição financeira com as premissas P1/P2 (as mesmas da H9).

Critério (2.3): CONFIRMA se a taxa (ou um motivo) estiver concentrada em
grupos identificáveis E a concentração se mantiver em outro corte. REFUTA se a
taxa for homogênea em todos os cortes (custo "de base", sem alavanca clara).
Régua (proposta, declarada): concentração relevante = p < 0,05/11 (Bonferroni
nos 11 cortes) E amplitude ≥ 3 p.p. (≈ 20% da taxa média).

Uso: python scripts/03_teste_hipoteses_h3a_devolucoes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import (  # noqa: E402
    ALPHA, OUT_DIR, PREMISSAS_DEVOLUCAO, Saida, carregar_estoque, carregar_vendas,
    frete_reverso_premissa, homogeneidade, resultado_realizado, tabela_taxa,
)

NOME = "h3a_devolucoes"
AMPLITUDE_RELEVANTE_PP = 3.0
CORTES = ["categoria", "subcategoria", "canal", "mes", "fornecedor_id", "metodo_pagamento",
          "faixa_preco", "faixa_desconto", "faixa_prazo", "faixa_lead_time", "status_disponibilidade"]
IMPRIMIR = {"categoria", "canal", "metodo_pagamento", "faixa_preco", "faixa_desconto", "faixa_prazo",
            "faixa_lead_time", "status_disponibilidade"}
CONTROLAVEIS = ["Produto com defeito", "Tamanho errado", "Atraso na entrega"]


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()
    e = carregar_estoque()

    # ------------------------------------------------------------------ 1
    out.secao("1. Taxa geral e coerência")
    a = v[v["pagamento_aprovado"]].merge(
        e[["sku_id", "subcategoria", "fornecedor_id", "lead_time_reposicao", "status_disponibilidade"]],
        on="sku_id", how="left", validate="many_to_one")
    if a["fornecedor_id"].isna().any():
        raise ValueError("sku_id sem correspondência no estoque")
    out(f"Aprovados: {len(a)} itens; devolvidos {int(a['devolvido'].sum())} ({a['devolvido'].mean() * 100:.2f}%).")
    inc = pd.crosstab(v["status_pagamento"], v["devolvido"])
    out.tabela(inc, "status_x_devolvido")
    n_inc = int(v.loc[~v["pagamento_aprovado"], "devolvido"].sum())
    out(f"Incoerência de dado: {n_inc} itens com pagamento NÃO aprovado marcados como devolvidos "
        f"({n_inc / (~v['pagamento_aprovado']).sum() * 100:.1f}% dos não aprovados — mesma ordem da taxa dos aprovados). "
        "Não se devolve o que não foi pago/entregue: ficam fora da taxa (base = aprovados) e são reportados como achado de qualidade.")

    # ------------------------------------------------------------------ 2
    out.secao("2. A taxa de devolução é concentrada em algum corte?")
    a["faixa_preco"] = pd.qcut(a["preco_unitario"], 5).astype(str)
    a["prof_desc"] = a["desconto_reais"] / a["receita_bruta"]
    a["faixa_desconto"] = pd.cut(a["prof_desc"], [-0.001, 0.0, 0.15, 0.30, 0.41],
                                 labels=["sem desconto", "(0-15%]", "(15-30%]", "(30-40%]"])
    a["faixa_prazo"] = pd.cut(a["tempo_entrega_real"], [0, 5, 10, 14, 18], labels=["1-5 d", "6-10 d", "11-14 d", "15-18 d"])
    a["faixa_lead_time"] = pd.cut(a["lead_time_reposicao"], [0, 9, 14, 50, 60], labels=["5-9 d", "10-14 d", "15-50 d", "51-60 d"])
    resumo = []
    for c in CORTES:
        t = tabela_taxa(a, c, "devolvido")
        t.to_csv(OUT_DIR / f"{NOME}__taxa_por_{c}.csv", encoding="utf-8")
        if c in IMPRIMIR:
            out(f"\n  -- {c} --")
            out.tabela(t)
        resumo.append(homogeneidade(a, c, "devolvido"))
    res = pd.DataFrame(resumo).set_index("corte")
    bonf = ALPHA / len(CORTES)
    res["relevante"] = (res["p_valor"] < bonf) & (res["amplitude_pp"] >= AMPLITUDE_RELEVANTE_PP)
    out(f"\n  Resumo dos {len(CORTES)} cortes (limiar de Bonferroni p < {bonf:.4f}; amplitude relevante ≥ {AMPLITUDE_RELEVANTE_PP} p.p.):")
    out.tabela(res, "resumo_cortes", casas=4)
    out("Nota: em cortes com muitos grupos pequenos (fornecedor, subcategoria) a amplitude cresce só por "
        "tamanho de amostra — por isso a régua exige também o qui-quadrado.")
    tf = tabela_taxa(a, "fornecedor_id", "devolvido")
    p_med = a["devolvido"].mean()
    dp_esp = np.sqrt(p_med * (1 - p_med) / tf["n"]).mean() * 100
    out(f"Fornecedores ({len(tf)}): desvio-padrão observado das taxas {tf['taxa_%'].std():.2f} p.p. vs "
        f"≈ {dp_esp:.2f} p.p. esperado só por amostragem binomial (n médio {tf['n'].mean():.0f}).")

    # ------------------------------------------------------------------ 3
    out.secao("3. Motivos de devolução")
    dev = a[a["devolvido"]]
    ctm = pd.crosstab(dev["categoria"], dev["motivo_devolucao"], margins=True, margins_name="Total")
    out.tabela(ctm, "motivo_x_categoria_contagem")
    pct = pd.crosstab(a["categoria"], a["motivo_devolucao"], normalize="index").drop(columns="Não se aplica") * 100
    out("  % dos itens vendidos (aprovados) de cada categoria:")
    out.tabela(pct, "motivo_x_categoria_pct_itens")
    p_mc = stats.chi2_contingency(pd.crosstab(dev["categoria"], dev["motivo_devolucao"]))[1]
    out(f"  Qui² motivo × categoria (entre devolvidos): p={p_mc:.4f}")
    tam = dev[dev["motivo_devolucao"].eq("Tamanho errado")]
    sem_tam = tam[tam["categoria"].isin(["Beleza", "Lifestyle"])]
    out(f"  Coerência: {len(sem_tam)} de {len(tam)} devoluções por 'Tamanho errado' ({len(sem_tam) / len(tam) * 100:.1f}%) são de "
        "Beleza/Lifestyle — produtos sem grade de tamanho. Exemplos (subcategoria: itens): "
        + ", ".join(f"{k}: {n}" for k, n in sem_tam["subcategoria"].value_counts().head(6).items()))
    pmc = pd.crosstab(a["canal"], a["motivo_devolucao"], normalize="index").drop(columns="Não se aplica") * 100
    out("\n  % dos itens de cada canal, por motivo:")
    out.tabela(pmc, "motivo_x_canal_pct_itens")
    p_mcan = stats.chi2_contingency(pd.crosstab(dev["canal"], dev["motivo_devolucao"]))[1]
    out(f"  Qui² motivo × canal (entre devolvidos): p={p_mcan:.4f}")
    ctrl = dev["motivo_devolucao"].isin(CONTROLAVEIS).mean() * 100
    out(f"  Motivos em tese controláveis pela operação ({', '.join(CONTROLAVEIS)}): {ctrl:.1f}% das devoluções.")

    # ----------------------------------------------------------------- 3b
    out.secao("3b. Corte adicional — o mix de motivos do Influenciador se mantém em outros cortes?")
    a["nao_gostei"] = a["motivo_devolucao"].eq("Não gostei")
    a["atraso_mot"] = a["motivo_devolucao"].eq("Atraso na entrega")
    a["influenciador"] = a["canal"].eq("Influenciador")
    a["trimestre"] = a["data_pedido"].dt.to_period("Q").astype(str)
    linhas = []
    for flag, rot in (("nao_gostei", "Não gostei"), ("atraso_mot", "Atraso na entrega"), ("devolvido", "Devolução total")):
        for dim in ("categoria", "trimestre"):
            for grupo, sub in a.groupby(dim):
                ct = pd.crosstab(sub["influenciador"], sub[flag])
                linhas.append({
                    "motivo": rot, "corte": dim, "grupo": grupo,
                    "itens_influenciador": int(sub["influenciador"].sum()),
                    "taxa_influenciador_%": sub.loc[sub["influenciador"], flag].mean() * 100,
                    "taxa_demais_%": sub.loc[~sub["influenciador"], flag].mean() * 100,
                    "p_valor": stats.chi2_contingency(ct)[1] if ct.shape == (2, 2) else np.nan,
                })
    tm = pd.DataFrame(linhas).set_index(["motivo", "corte", "grupo"])
    out.tabela(tm, "motivo_influenciador_cortes", casas=3)
    resumo_inf = {}
    for rot in ("Não gostei", "Atraso na entrega", "Devolução total"):
        sub = tm.loc[rot]
        mais = int((sub["taxa_influenciador_%"] > sub["taxa_demais_%"]).sum())
        menos = int((sub["taxa_influenciador_%"] < sub["taxa_demais_%"]).sum())
        sig = int((sub["p_valor"] < ALPHA).sum())
        resumo_inf[rot] = (mais, menos, sig, len(sub))
        out(f"  {rot}: Influenciador acima dos demais em {mais}/{len(sub)} cortes, abaixo em {menos}/{len(sub)}; p<0,05 em {sig}/{len(sub)}.")
    out("  Obs.: 2024Q1 tem só 26 dias de janeiro (poucos itens do Influenciador).")

    # ------------------------------------------------------------------ 4
    out.secao("4. Corte adicional — interação (a homogeneidade esconde efeitos que se compensam?)")
    inter = [homogeneidade(a, ["canal", "categoria"], "devolvido")]
    for cat, sub in a.groupby("categoria"):
        for d in ("subcategoria", "canal"):
            h = homogeneidade(sub, d, "devolvido")
            h["corte"] = f"{d} dentro de {cat}"
            inter.append(h)
    ti = pd.DataFrame(inter).set_index("corte")
    bonf_i = ALPHA / len(ti)
    out.tabela(ti, "cortes_interacao", casas=4)
    out(f"  {len(ti)} testes; limiar de Bonferroni p < {bonf_i:.4f}; abaixo do limiar: {int((ti['p_valor'] < bonf_i).sum())}.")
    forn_cat = e.groupby("fornecedor_id")["categoria"].nunique()
    out(f"  Fornecedores atendem de {forn_cat.min()} a {forn_cat.max()} categorias (mediana {forn_cat.median():.0f}) — "
        "o corte por fornecedor não é um proxy de categoria.")

    # ------------------------------------------------------------------ 5
    out.secao("5. Exposição financeira (premissas P1/P2 — as mesmas da H9)")
    out(PREMISSAS_DEVOLUCAO)
    fr = frete_reverso_premissa(v)
    a["custo_P1"] = a["margem_contribuicao"] - resultado_realizado(a, "P1", fr)
    a["custo_P2"] = a["margem_contribuicao"] - resultado_realizado(a, "P2", fr)
    fin = a[a["devolvido"]].groupby("motivo_devolucao").agg(
        itens=("order_id", "size"), receita_liquida_devolvida=("receita_liquida", "sum"),
        custo_P1=("custo_P1", "sum"), custo_P2=("custo_P2", "sum"))
    fin.loc["Total"] = fin.sum()
    fin["%custo_P2"] = fin["custo_P2"] / fin.loc["Total", "custo_P2"] * 100
    out.tabela(fin, "exposicao_por_motivo")
    out(f"  Frete reverso P2: R$ {fr:.2f}/devolução. Controláveis = "
        f"R$ {fin.loc[CONTROLAVEIS, 'custo_P2'].sum():,.2f} do custo P2 ({fin.loc[CONTROLAVEIS, '%custo_P2'].sum():.1f}%).")

    # ------------------------------------------------------------------ 6
    out.secao("6. Veredito proposto")
    rel = res[res["relevante"]]
    out(f"  Cortes com concentração relevante da TAXA: {', '.join(rel.index) if len(rel) else 'nenhum'} (de {len(CORTES)}).")
    out(f"  Cortes de interação abaixo do limiar de Bonferroni: {int((ti['p_valor'] < bonf_i).sum())} de {len(ti)}.")
    ver = ("CONFIRMADA (concentração identificável da taxa)" if len(rel)
           else "REFUTADA para a TAXA — homogênea em todos os cortes: custo 'de base' sem alavanca por segmento nesta base")
    out(f"\nVEREDITO PROPOSTO H3a: {ver}. Tamanho do custo (P1–P2): R$ {fin.loc['Total', 'custo_P1']:,.2f} a "
        f"R$ {fin.loc['Total', 'custo_P2']:,.2f} na janela.")
    mais, _, sig, n = resumo_inf["Não gostei"]
    robusto = mais == n and sig >= n / 2
    out(f"  Motivo × canal (qui² p={p_mcan:.4f}): 'Não gostei' no Influenciador acima dos demais em {mais}/{n} cortes "
        f"(p<0,05 em {sig}/{n}) → {'CONCENTRAÇÃO DE MOTIVO ROBUSTA' if robusto else 'não robusta nos cortes'}; "
        f"taxa total do Influenciador acima em {resumo_inf['Devolução total'][0]}/{resumo_inf['Devolução total'][3]} cortes "
        f"(p<0,05 em {resumo_inf['Devolução total'][2]}) — muda a composição dos motivos, não o nível.")
    out.salvar()


if __name__ == "__main__":
    main()
