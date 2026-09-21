"""
03_teste_hipoteses_h1_margem.py — Fase 2.4, H1

Hipótese: o crescimento vem com pior margem por pedido.
  H1.1 desconto mais agressivo (no tempo ou em canais/categorias)
  H1.2 frete subsidiado consumindo margem
  H1.3 mudança de mix para canais/categorias de menor margem
  H1.4 itens vendidos com margem negativa

Teste (só pagamento_aprovado):
  1. Ponte de margem mensal em % da receita bruta (aditiva):
     margem_%RB = 100 − desconto_%RB − cmv_%RB − frete_%RB. Tendência de cada termo.
  2. Novembro × resto de 2023 (o único mês com margem fora da faixa na H0) e o
     dia 24/11; corte adicional: o desconto de novembro é generalizado por canal
     e categoria ou concentrado?
  3. Ponte por canal, por categoria e matriz canal × categoria.
  4. Frete: por canal; Marketplace × categoria e Marketplace × mês (corte
     adicional para ver se o frete é do canal e não de categoria/mês).
  5. Efeito mix × efeito taxa (shift-share) em células canal, categoria e
     canal × categoria: 1º × 2º semestre, resto do ano × nov, jan/23 × jan/24.
  6. Participação de cada canal na receita ao longo dos meses.
  7. H1.4 itens com margem negativa.
  8. Subcategoria (join com estoque por sku_id).
  9. H1.1 frequência e profundidade do desconto, por mês e por canal; corte
     adicional canal × categoria.

Réguas de materialidade (propostas, declaradas):
  - efeito relevante na margem % = ≥ 0,5 p.p. (acima do desvio-padrão mensal
    de 0,46 p.p. medido na H0);
  - H1.4 relevante se a soma da margem negativa for ≥ 1% da margem total.

Critério (2.3): confirma H1.1 se desc% subir no tempo ou for estruturalmente
maior em canais/categorias e explicar parte relevante da queda; confirma H1.3 se
o efeito mix for relevante; refuta se a margem dentro de canal × categoria for
estável e o mix não mudar.

Uso: python scripts/03_teste_hipoteses_h1_margem.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import (  # noqa: E402
    ALPHA, Saida, agregados, agregados_total, carregar_estoque, carregar_vendas,
    homogeneidade, meses_de_pico, tabela_taxa, tendencia,
)

NOME = "h1_margem"
COMP = ["desconto_%RB", "cmv_%RB", "frete_%RB", "margem_%RB", "margem_%RL"]
LIMIAR_PP = 0.5
LIMIAR_NEG = 1.0
NOV = pd.Period("2023-11", "M")
DEZ23 = pd.Period("2023-12", "M")


def shift_share(a: pd.DataFrame, mask_a: pd.Series, mask_b: pd.Series, celulas) -> dict:
    """Variação da margem % (sobre RL) de A para B = efeito mix + efeito taxa + interação."""
    ga, gb = agregados(a[mask_a], celulas), agregados(a[mask_b], celulas)
    idx = ga.index.union(gb.index)
    ga, gb = ga.reindex(idx), gb.reindex(idx)
    if ga["receita_liquida"].isna().any() or gb["receita_liquida"].isna().any():
        raise ValueError(f"célula vazia em {celulas}")
    wa = ga["receita_liquida"] / ga["receita_liquida"].sum()
    wb = gb["receita_liquida"] / gb["receita_liquida"].sum()
    ma = ga["margem"] / ga["receita_liquida"]
    mb = gb["margem"] / gb["receita_liquida"]
    return {
        "margem_A_%": (wa * ma).sum() * 100,
        "margem_B_%": (wb * mb).sum() * 100,
        "variacao_pp": ((wb * mb).sum() - (wa * ma).sum()) * 100,
        "efeito_mix_pp": ((wb - wa) * ma).sum() * 100,
        "efeito_taxa_pp": (wa * (mb - ma)).sum() * 100,
        "interacao_pp": ((wb - wa) * (mb - ma)).sum() * 100,
    }


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()
    a = v[v["pagamento_aprovado"]].copy()
    a23 = a[a["mes"] <= DEZ23]
    out(f"Base: {len(a)} itens aprovados; 2023 = {len(a23)} itens.")

    # ------------------------------------------------------------------ 1
    out.secao("1. Ponte de margem mensal (% da receita bruta)")
    g = agregados(a, "mes")
    out.tabela(g[["itens"] + COMP], "ponte_mensal")
    out("Identidade: margem_%RB = 100 − desconto_%RB − cmv_%RB − frete_%RB. margem_%RL = margem ÷ receita líquida.")
    ano = g.loc[:DEZ23]
    picos, _ = meses_de_pico(ano["itens"])
    cen = {"2023 completo": ano, "2023 sem nov": ano.drop(NOV), "2023 sem picos": ano.drop(picos)}
    linhas = [{"cenario": c, "componente": k, **tendencia(df[k])} for c, df in cen.items() for k in COMP]
    tt = pd.DataFrame(linhas).set_index(["cenario", "componente"])[["media", "inclinacao_por_mes", "p_valor", "r2"]]
    out.tabela(tt, "tendencias_componentes", casas=4)

    # ------------------------------------------------------------------ 2
    out.secao("2. Novembro × resto de 2023 — o que explica o único mês fora da faixa?")
    nov = a23["mes"].eq(NOV)
    comp = pd.DataFrame({"resto_2023": agregados_total(a23[~nov])[COMP],
                         "nov_2023": agregados_total(a23[nov])[COMP]}).astype(float)
    comp["delta_pp"] = comp["nov_2023"] - comp["resto_2023"]
    out.tabela(comp, "novembro_x_resto")
    dia = a23["data_pedido"].dt.normalize()
    bf = dia.eq(pd.Timestamp("2023-11-24"))
    tb = pd.DataFrame({
        "24/11 (maior dia do ano)": agregados_total(a23[bf])[["itens"] + COMP],
        "resto de nov": agregados_total(a23[nov & ~bf])[["itens"] + COMP],
        "resto de 2023": agregados_total(a23[~nov])[["itens"] + COMP],
    }).astype(float)
    out.tabela(tb, "dia_24_11")
    gen = {}
    for dim in ("canal", "categoria"):
        dn = agregados(a23[nov], dim)["desconto_%RB"]
        dr = agregados(a23[~nov], dim)["desconto_%RB"]
        t = pd.DataFrame({"resto_2023": dr, "nov_2023": dn})
        t["delta_pp"] = t["nov_2023"] - t["resto_2023"]
        out(f"\n  Corte adicional — desconto_%RB em nov × resto, por {dim}:")
        out.tabela(t, f"desconto_nov_por_{dim}")
        gen[dim] = (int((t["delta_pp"] > 0).sum()), len(t), t["delta_pp"].min(), t["delta_pp"].max())
        out(f"  → desconto maior em nov em {gen[dim][0]} de {gen[dim][1]} ({dim}); Δ de {gen[dim][2]:.2f} a {gen[dim][3]:.2f} p.p.")
    m_ano = agregados_total(a23)["margem_%RL"]
    m_sem_nov = agregados_total(a23[~nov])["margem_%RL"]
    rl_nov = a23.loc[nov, "receita_liquida"].sum()
    out(f"\nMargem % de 2023: {m_ano:.2f}% com nov, {m_sem_nov:.2f}% sem nov → nov tira {m_sem_nov - m_ano:.2f} p.p. da margem anual.")
    out(f"Custo de margem de nov a volume constante: R$ {(m_sem_nov - comp.loc['margem_%RL', 'nov_2023']) / 100 * rl_nov:,.2f} "
        "(ordem de grandeza do evento — NÃO é oportunidade: sem o desconto, o volume de nov provavelmente não existiria).")

    # ------------------------------------------------------------------ 3
    out.secao("3. Ponte por canal, por categoria e matriz canal × categoria")
    for dim in ("canal", "categoria"):
        t = agregados(a, dim)
        t["part_RL_%"] = t["receita_liquida"] / t["receita_liquida"].sum() * 100
        out.tabela(t[["itens", "part_RL_%", "ticket"] + COMP].sort_values("margem_%RL"), f"ponte_por_{dim}")
    mat = agregados(a, ["canal", "categoria"])["margem_%RL"].unstack("categoria")
    out.tabela(mat, "matriz_margem_canal_x_categoria")
    sem_mkp = mat.drop("Marketplace")
    out(f"Sem Marketplace: 24 células entre {sem_mkp.min().min():.2f}% e {sem_mkp.max().max():.2f}%. "
        f"Marketplace: 4 células entre {mat.loc['Marketplace'].min():.2f}% e {mat.loc['Marketplace'].max():.2f}%.")

    # ------------------------------------------------------------------ 4
    out.secao("4. H1.2 frete — por canal e corte adicional Marketplace × categoria e × mês")
    a["tem_frete"] = a["custo_frete"] > 0
    fc = a.groupby("canal").agg(
        itens=("order_id", "size"),
        pct_itens_com_frete=("tem_frete", "mean"),
        frete_medio_quando_ha=("custo_frete", lambda s: s[s > 0].mean()),
        prazo_medio_dias=("tempo_entrega_real", "mean"),
    )
    fc["pct_itens_com_frete"] *= 100
    fc["frete_%RB"] = agregados(a, "canal")["frete_%RB"]
    out.tabela(fc, "frete_por_canal")
    a["grupo_canal"] = np.where(a["canal"].eq("Marketplace"), "Marketplace", "Demais canais")
    fcat = agregados(a, ["categoria", "grupo_canal"])["frete_%RB"].unstack()
    fcat["diferenca_pp"] = fcat["Marketplace"] - fcat["Demais canais"]
    out.tabela(fcat, "frete_marketplace_x_categoria")
    fmes = agregados(a, ["mes", "grupo_canal"])["frete_%RB"].unstack()
    fmes["diferenca_pp"] = fmes["Marketplace"] - fmes["Demais canais"]
    out.tabela(fmes, "frete_marketplace_x_mes")
    t_mkp_frete = tendencia(fmes.loc[:DEZ23, "Marketplace"])
    out(f"Tendência do frete_%RB do Marketplace em 2023: {t_mkp_frete['inclinacao_por_mes']:+.4f} p.p./mês, p={t_mkp_frete['p_valor']:.4f}")
    gap = agregados(a, "grupo_canal")[COMP].T
    gap["Marketplace − demais (pp)"] = gap["Marketplace"] - gap["Demais canais"]
    out.tabela(gap, "gap_marketplace")
    ag_mkp = agregados_total(a[a["canal"].eq("Marketplace")])
    ag_dem = agregados_total(a[~a["canal"].eq("Marketplace")])
    frete_excedente = (ag_mkp["frete_%RB"] - ag_dem["frete_%RB"]) / 100 * ag_mkp["receita_bruta"]
    out(f"Frete do Marketplace: R$ {ag_mkp['frete']:,.2f}. Excedente vs. a taxa de frete dos demais canais: "
        f"R$ {frete_excedente:,.2f} na janela (conta simples: diferença de frete_%RB × receita bruta do Marketplace).")

    # ------------------------------------------------------------------ 5
    out.secao("5. H1.3 efeito mix × efeito taxa (shift-share)")
    jan23 = (a["data_pedido"] >= "2023-01-01") & (a["data_pedido"] < "2023-01-27")
    jan24 = (a["data_pedido"] >= "2024-01-01") & (a["data_pedido"] < "2024-01-27")
    comparacoes = {
        "1º sem/2023 → 2º sem/2023": ((a["mes"] >= pd.Period("2023-01", "M")) & (a["mes"] <= pd.Period("2023-06", "M")),
                                      (a["mes"] >= pd.Period("2023-07", "M")) & (a["mes"] <= DEZ23)),
        "resto de 2023 → nov/2023": ((a["mes"] <= DEZ23) & a["mes"].ne(NOV), a["mes"].eq(NOV)),
        "01-26/jan/23 → 01-26/jan/24": (jan23, jan24),
    }
    linhas = [
        {"comparacao": c, "celulas": rot, **shift_share(a, ma, mb, cel)}
        for c, (ma, mb) in comparacoes.items()
        for rot, cel in (("canal", "canal"), ("categoria", "categoria"), ("canal×categoria", ["canal", "categoria"]))
    ]
    ss = pd.DataFrame(linhas).set_index(["comparacao", "celulas"])
    out.tabela(ss, "shift_share", casas=3)
    max_mix = ss["efeito_mix_pp"].abs().max()
    out(f"Maior |efeito mix| em todas as comparações: {max_mix:.3f} p.p. (régua de relevância: {LIMIAR_PP} p.p.)")

    # ------------------------------------------------------------------ 6
    out.secao("6. Participação de cada canal na receita líquida, por mês")
    part = a.groupby(["mes", "canal"])["receita_liquida"].sum().unstack()
    part = part.div(part.sum(axis=1), axis=0) * 100
    out.tabela(part, "participacao_canal_mes")
    tp = pd.DataFrame([{"canal": c, **tendencia(part.loc[:DEZ23, c])} for c in part.columns]).set_index("canal")
    out.tabela(tp[["media", "inclinacao_por_mes", "p_valor"]], "tendencia_participacao", casas=4)

    # ------------------------------------------------------------------ 7
    out.secao("7. H1.4 itens com margem negativa")
    a["margem_negativa"] = a["margem_contribuicao"] < 0
    neg = a[a["margem_negativa"]]
    pct_neg = abs(neg["margem_contribuicao"].sum()) / a["margem_contribuicao"].sum() * 100
    out(f"Itens aprovados com margem negativa: {len(neg)} ({len(neg) / len(a) * 100:.2f}%); soma R$ {neg['margem_contribuicao'].sum():,.2f} "
        f"= {pct_neg:.2f}% da margem total aprovada (R$ {a['margem_contribuicao'].sum():,.2f}).")
    carac = pd.DataFrame({"margem negativa": agregados_total(neg)[COMP],
                          "margem ≥ 0": agregados_total(a[~a["margem_negativa"]])[COMP]}).astype(float)
    out.tabela(carac, "caracteristicas_margem_negativa")
    out.tabela(tabela_taxa(a, "canal", "margem_negativa"), "margem_negativa_por_canal")
    hn = [homogeneidade(a, d, "margem_negativa") for d in ("canal", "categoria")]
    out.tabela(pd.DataFrame(hn).set_index("corte"), "margem_negativa_homogeneidade", casas=4)

    # ------------------------------------------------------------------ 8
    out.secao("8. Subcategoria (join com estoque por sku_id)")
    e = carregar_estoque()
    s = a.merge(e[["sku_id", "subcategoria"]], on="sku_id", how="left", validate="many_to_one")
    if s["subcategoria"].isna().any():
        raise ValueError("sku_id sem subcategoria no estoque")
    gs = agregados(s, ["categoria", "subcategoria"])
    gs_ord = gs[["itens", "margem_%RL", "desconto_%RB", "cmv_%RB", "frete_%RB"]].sort_values("margem_%RL")
    gs_ord.to_csv(Path(__file__).resolve().parents[1] / "outputs" / "03_teste_hipoteses" / f"{NOME}__margem_por_subcategoria.csv")
    out("5 menores e 5 maiores margens % (48 subcategorias; tabela completa no CSV):")
    out.tabela(pd.concat([gs_ord.head(5), gs_ord.tail(5)]))
    w = gs["receita_liquida"] / gs["receita_liquida"].sum()
    dp_pond = np.sqrt((w * (gs["margem_%RL"] - (w * gs["margem_%RL"]).sum()) ** 2).sum())
    out(f"Margem % por subcategoria: de {gs['margem_%RL'].min():.2f}% a {gs['margem_%RL'].max():.2f}%; "
        f"desvio-padrão ponderado pela receita {dp_pond:.2f} p.p.")

    # ------------------------------------------------------------------ 9
    out.secao("9. H1.1 desconto — frequência e profundidade")
    a["tem_desconto"] = a["desconto_reais"] > 0
    a["prof_desconto"] = a["desconto_reais"] / a["receita_bruta"] * 100
    dm = a.groupby("mes").agg(pct_itens_com_desconto=("tem_desconto", "mean"),
                              prof_media_quando_ha_pct=("prof_desconto", lambda s: s[s > 0].mean()))
    dm["pct_itens_com_desconto"] *= 100
    dm["desconto_%RB"] = g["desconto_%RB"]
    out.tabela(dm, "desconto_por_mes")
    dm23 = dm.loc[:DEZ23]
    td = {k: tendencia(dm23.drop(NOV)[k]) for k in ("pct_itens_com_desconto", "prof_media_quando_ha_pct", "desconto_%RB")}
    for k, t in td.items():
        out(f"  Tendência 2023 sem nov — {k}: {t['inclinacao_por_mes']:+.4f}/mês, p={t['p_valor']:.4f}")
    dc = a.groupby("canal").agg(pct_itens_com_desconto=("tem_desconto", "mean"),
                                prof_media_quando_ha_pct=("prof_desconto", lambda s: s[s > 0].mean()))
    dc["pct_itens_com_desconto"] *= 100
    dc["desconto_%RB"] = agregados(a, "canal")["desconto_%RB"]
    out.tabela(dc.sort_values("desconto_%RB"), "desconto_por_canal")
    hd = pd.DataFrame([homogeneidade(a, d, "tem_desconto") for d in ("canal", "categoria")]).set_index("corte")
    out.tabela(hd, "desconto_homogeneidade", casas=4)
    piv = agregados(a, ["canal", "categoria"])["desconto_%RB"].unstack("categoria")
    out("\n  Corte adicional — desconto_%RB canal × categoria:")
    out.tabela(piv, "desconto_canal_x_categoria")
    desvio_canal = dc["desconto_%RB"] - agregados_total(a)["desconto_%RB"]
    desvio_cel = piv.sub(piv.mean(axis=0), axis=1)
    consist = {c: int((np.sign(desvio_cel.loc[c]) == np.sign(desvio_canal[c])).sum()) for c in piv.index}
    out("  Nº de categorias (de 4) em que o canal fica do mesmo lado da média que no total: "
        + ", ".join(f"{c}={n}" for c, n in consist.items()))

    # ------------------------------------------------------------------ 10
    out.secao("10. Veredito proposto por sub-hipótese")
    t_desc = tendencia(ano["desconto_%RB"])
    t_desc_sn = tendencia(ano.drop(NOV)["desconto_%RB"])
    cresce_desc = (t_desc_sn["inclinacao_por_mes"] > 0 and t_desc_sn["p_valor"] < ALPHA)
    out(f"  H1.1 desconto: tendência 2023 {t_desc['inclinacao_por_mes']:+.4f} p.p./mês (p={t_desc['p_valor']:.4f}); "
        f"sem nov {t_desc_sn['inclinacao_por_mes']:+.4f} (p={t_desc_sn['p_valor']:.4f}) → "
        f"{'cresce no tempo' if cresce_desc else 'não cresce no tempo'}. Nov: +{comp.loc['desconto_%RB', 'delta_pp']:.2f} p.p. "
        f"de desconto, maior em {gen['canal'][0]}/{gen['canal'][1]} canais e {gen['categoria'][0]}/{gen['categoria'][1]} categorias "
        "(evento generalizado, pontual).")
    out(f"       amplitude de desconto_%RB entre canais: {dc['desconto_%RB'].max() - dc['desconto_%RB'].min():.2f} p.p. "
        f"({dc['desconto_%RB'].idxmin()} {dc['desconto_%RB'].min():.2f}% → {dc['desconto_%RB'].idxmax()} {dc['desconto_%RB'].max():.2f}%).")
    cats_pos = int((fcat["diferenca_pp"] > 0).sum())
    meses_pos = int((fmes["diferenca_pp"] > 0).sum())
    out(f"  H1.2 frete: Marketplace − demais = {gap.loc['frete_%RB', 'Marketplace − demais (pp)']:+.2f} p.p. da RB; "
        f"positivo em {cats_pos}/4 categorias e {meses_pos}/{len(fmes)} meses; "
        f"explica {gap.loc['frete_%RB', 'Marketplace − demais (pp)'] / -gap.loc['margem_%RB', 'Marketplace − demais (pp)'] * 100:.0f}% "
        f"do gap de margem_%RB do Marketplace ({gap.loc['margem_%RB', 'Marketplace − demais (pp)']:+.2f} p.p.). "
        f"Frete do Marketplace sem tendência em 2023 (p={t_mkp_frete['p_valor']:.4f}).")
    out(f"  H1.3 mix: maior |efeito mix| = {max_mix:.3f} p.p. → {'RELEVANTE' if max_mix >= LIMIAR_PP else 'NÃO relevante'} "
        f"(régua {LIMIAR_PP} p.p.).")
    out(f"  H1.4 margem negativa: {pct_neg:.2f}% da margem total → {'RELEVANTE' if pct_neg >= LIMIAR_NEG else 'NÃO relevante'} "
        f"(régua {LIMIAR_NEG}%).")
    out.salvar()


if __name__ == "__main__":
    main()
