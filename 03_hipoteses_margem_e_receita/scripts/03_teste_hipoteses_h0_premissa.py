"""
03_teste_hipoteses_h0_premissa.py — Fase 2.4, H0 (bloqueante)

Hipótese: na janela de vendas, receita e pedidos crescem mês a mês enquanto a
margem de contribuição % cai ("cresce mas perde rentabilidade").

Teste (reports/03_arvore_hipoteses.md, H0):
  1. Série mensal só com pagamento_aprovado: itens (= pedidos, ver H9), receita
     líquida, ticket, margem R$ e margem % sobre a receita líquida.
  2. Tendência linear em 2023: (A) 12 meses, (B) sem nov/dez — critério da 2.3 —
     e (C) sem todos os meses de pico detectados nos dados.
  3. Ano contra ano no mesmo período: 01–26/jan/2023 × 01–26/jan/2024
     (jan/2024 tem só 26 dias, por isso fica fora da tendência).
  4. A 2.3 pediu usar o calendário de campanhas de marketing para separar
     sazonalidade: aqui se checa se esse calendário é utilizável.
  5. Corte adicional: tendência da margem % e da receita por canal e por
     categoria — se houver queda, é generalizada ou concentrada?

Critério (2.3): SUSTENTA a premissa se a receita tiver tendência positiva E a
margem % tendência negativa em 2023, E as duas se mantiverem sem nov/dez.
Caso contrário, refuta/reformula.

Obs.: H0 usa a margem REPORTADA (coluna margem_contribuicao). A margem "cheia"
(após devolução) é testada na H9.

Uso: python scripts/03_teste_hipoteses_h0_premissa.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import (  # noqa: E402
    ALPHA, Saida, agregados, agregados_total, carregar_marketing, carregar_vendas,
    meses_de_pico, tendencia,
)

NOME = "h0_premissa"
METRICAS = ["itens", "receita_liquida", "ticket", "margem", "margem_%RL"]

# Calendário do varejo brasileiro usado para checar se o nome da campanha bate com
# a data de início. É conhecimento externo, não vem da base: premissa declarada.
MESES_ESPERADOS = {
    "Black_Friday_Main": {10, 11},
    "Cyber_Monday": {11, 12},
    "Natal_Presentes": {11, 12},
    "Dia_Das_Maes": {4, 5},
    "Dia_Dos_Namorados": {5, 6},
    "Liquidacao_Julho": {6, 7},
    "Volta_as_Aulas": {1, 2, 7},
    "Semana_Consumidor": {2, 3},
}


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()
    a = v[v["pagamento_aprovado"]]
    out(f"Base: {len(a)} itens com pagamento aprovado (de {len(v)} na base tratada).")

    # ------------------------------------------------------------------ 1
    out.secao("1. Série mensal — itens com pagamento aprovado")
    g = agregados(a, "mes")
    out.tabela(
        g[["itens", "receita_liquida", "ticket", "margem", "margem_%RL",
           "desconto_%RB", "cmv_%RB", "frete_%RB"]],
        "serie_mensal",
    )
    out("Obs.: 2024-01 cobre só 26 dias: fica fora das tendências e é comparado em base igual na seção 3.")

    ano = g.loc[pd.Period("2023-01", "M"):pd.Period("2023-12", "M")]
    picos, mediana = meses_de_pico(ano["itens"])
    out(f"Meses de pico (itens > 1,5 × mediana mensal de 2023 = {mediana:.0f}): "
        + ", ".join(str(p) for p in picos))
    out(f"Participação dos meses de pico na receita líquida de 2023: "
        f"{ano.loc[picos, 'receita_liquida'].sum() / ano['receita_liquida'].sum() * 100:.1f}% "
        f"em {len(picos)} de 12 meses.")

    diario = a.groupby(a["data_pedido"].dt.normalize()).size()
    p95 = diario.quantile(0.95)
    top = diario[diario > p95]
    out(f"\nDias de pico: p95 diário = {p95:.0f} itens/dia (mediana {diario.median():.0f}). "
        f"{len(top)} dias acima do p95:")
    for mes, grupo in top.groupby(top.index.to_period("M")):
        out(f"  {mes}: " + ", ".join(f"{d:%d/%m} ({n})" for d, n in grupo.items()))

    # ------------------------------------------------------------------ 2
    out.secao("2. Tendência linear em 2023 (inclinação por mês; p-valor da regressão)")
    cenarios = {
        "A. 2023 completo": ano,
        "B. 2023 sem nov/dez (critério 2.3)": ano.drop([pd.Period("2023-11", "M"), pd.Period("2023-12", "M")]),
        "C. 2023 sem todos os picos": ano.drop(picos),
    }
    linhas = [
        {"cenario": c, "metrica": m, **tendencia(df[m])}
        for c, df in cenarios.items() for m in METRICAS
    ]
    tab = pd.DataFrame(linhas).set_index(["cenario", "metrica"])
    out.tabela(tab, "tendencias", casas=4)
    out("Leitura: 'inclinacao_por_mes' está na unidade da métrica (R$/mês, itens/mês, p.p./mês "
        "para margem_%RL); 'inclinacao_%_da_media' = inclinação ÷ média do período.")
    dp = ano["margem_%RL"].std()
    out(f"Margem % em 2023: média {ano['margem_%RL'].mean():.2f}%, mínimo {ano['margem_%RL'].min():.2f}% "
        f"({ano['margem_%RL'].idxmin()}), máximo {ano['margem_%RL'].max():.2f}% ({ano['margem_%RL'].idxmax()}), "
        f"desvio-padrão mensal {dp:.2f} p.p.")
    sem_nov = ano.drop(pd.Period("2023-11", "M"))["margem_%RL"]
    out(f"Sem novembro: margem % entre {sem_nov.min():.2f}% e {sem_nov.max():.2f}% "
        f"(amplitude {sem_nov.max() - sem_nov.min():.2f} p.p.). Novembro fica "
        f"{sem_nov.mean() - ano.loc[pd.Period('2023-11', 'M'), 'margem_%RL']:.2f} p.p. abaixo da média dos outros 11 meses.")

    # ------------------------------------------------------------------ 3
    out.secao("3. Ano contra ano no mesmo período: 01–26/jan/2023 × 01–26/jan/2024")
    j23 = a[(a["data_pedido"] >= "2023-01-01") & (a["data_pedido"] < "2023-01-27")]
    j24 = a[(a["data_pedido"] >= "2024-01-01") & (a["data_pedido"] < "2024-01-27")]
    comp = pd.DataFrame({"jan/2023 (01-26)": agregados_total(j23)[METRICAS],
                         "jan/2024 (01-26)": agregados_total(j24)[METRICAS]}).astype(float)
    comp["variacao_%"] = (comp.iloc[:, 1] / comp.iloc[:, 0] - 1) * 100
    comp.loc["margem_%RL", "variacao_%"] = float("nan")
    comp["variacao_pp"] = float("nan")
    comp.loc["margem_%RL", "variacao_pp"] = comp.loc["margem_%RL"].iloc[1] - comp.loc["margem_%RL"].iloc[0]
    out.tabela(comp, "jan23_x_jan24")
    out(f"Referência de ruído: desvio-padrão mensal da margem % em 2023 = {dp:.2f} p.p.")

    # ------------------------------------------------------------------ 4
    out.secao("4. O calendário de campanhas (marketing) serve para separar sazonalidade?")
    m = carregar_marketing()
    m["base_nome"] = m["nome_campanha"].str.replace(r"_\d{4}(?:_\d{2})?$", "", regex=True)
    m["ano_no_nome"] = pd.to_numeric(m["nome_campanha"].str.extract(r"_(\d{4})(?:_\d{2})?$")[0])
    m["mes_no_nome"] = pd.to_numeric(m["nome_campanha"].str.extract(r"_\d{4}_(\d{2})$")[0])
    saz = m[m["base_nome"].isin(MESES_ESPERADOS)].copy()
    saz["inicia_no_mes_esperado"] = [
        d.month in MESES_ESPERADOS[b] for d, b in zip(saz["data_inicio"], saz["base_nome"])
    ]
    saz["prob_acaso"] = saz["base_nome"].map(lambda b: len(MESES_ESPERADOS[b]) / 12)
    por_nome = saz.groupby("base_nome").agg(
        campanhas=("campanha_id", "size"),
        inicia_no_mes_esperado_pct=("inicia_no_mes_esperado", "mean"),
        esperado_se_aleatorio_pct=("prob_acaso", "mean"),
    )
    por_nome[["inicia_no_mes_esperado_pct", "esperado_se_aleatorio_pct"]] *= 100
    out.tabela(por_nome, "calendario_campanhas")
    obs, n_saz, esp = int(saz["inicia_no_mes_esperado"].sum()), len(saz), saz["prob_acaso"].mean()
    bt = stats.binomtest(obs, n_saz, esp)
    out(f"Total: {obs} de {n_saz} campanhas sazonais ({obs / n_saz * 100:.1f}%) iniciam no mês esperado; "
        f"se a data fosse aleatória, o esperado seria {esp * 100:.1f}% (teste binomial aproximado, p={bt.pvalue:.3f}).")
    com_ano = m["ano_no_nome"].notna()
    ano_ok = (m.loc[com_ano, "ano_no_nome"] == m.loc[com_ano, "data_inicio"].dt.year).mean() * 100
    com_mes = m["mes_no_nome"].notna()
    mes_ok = (m.loc[com_mes, "mes_no_nome"] == m.loc[com_mes, "data_inicio"].dt.month).mean() * 100
    out(f"Ano no nome = ano de data_inicio: {ano_ok:.1f}% de {int(com_ano.sum())} campanhas com ano no nome. "
        f"Mês no nome (sufixo _AAAA_MM) = mês de data_inicio: {mes_ok:.1f}% de {int(com_mes.sum())}.")
    out("→ Se as taxas acima estão perto do acaso, o calendário de marketing NÃO serve para marcar "
        "eventos sazonais; a sazonalidade é identificada pelos próprios picos diários de vendas (seção 1).")

    # ------------------------------------------------------------------ 5
    out.secao("5. Corte adicional — tendência em 2023 por canal e por categoria (12 meses)")
    a23 = a[a["mes"] <= pd.Period("2023-12", "M")]
    resumo_corte = {}
    for dim in ("canal", "categoria"):
        gm = agregados(a23, [dim, "mes"])
        linhas = []
        for grupo, sub in gm.groupby(level=0):
            sub = sub.droplevel(0)
            tm = tendencia(sub["margem_%RL"])
            tr = tendencia(sub["receita_liquida"])
            linhas.append({
                dim: grupo,
                "margem_%RL_media": tm["media"],
                "margem_incl_pp_mes": tm["inclinacao_por_mes"],
                "margem_p_valor": tm["p_valor"],
                "receita_incl_%_media_mes": tr["inclinacao_%_da_media"],
                "receita_p_valor": tr["p_valor"],
            })
        t = pd.DataFrame(linhas).set_index(dim)
        out.tabela(t, f"tendencia_por_{dim}", casas=4)
        neg = int(((t["margem_incl_pp_mes"] < 0) & (t["margem_p_valor"] < ALPHA)).sum())
        resumo_corte[dim] = (neg, len(t))
        out(f"  → {dim}: {neg} de {len(t)} com tendência de margem % negativa e significativa (p<{ALPHA}).")

    # ------------------------------------------------------------------ 6
    out.secao("6. Veredito proposto (critério da 2.3)")
    tA_r, tA_m = tendencia(cenarios["A. 2023 completo"]["receita_liquida"]), tendencia(cenarios["A. 2023 completo"]["margem_%RL"])
    tB_r = tendencia(cenarios["B. 2023 sem nov/dez (critério 2.3)"]["receita_liquida"])
    tB_m = tendencia(cenarios["B. 2023 sem nov/dez (critério 2.3)"]["margem_%RL"])
    cond = {
        "receita: tendência positiva e significativa (2023 completo)": tA_r["inclinacao_por_mes"] > 0 and tA_r["p_valor"] < ALPHA,
        "margem %: tendência negativa e significativa (2023 completo)": tA_m["inclinacao_por_mes"] < 0 and tA_m["p_valor"] < ALPHA,
        "receita: positiva e significativa sem nov/dez": tB_r["inclinacao_por_mes"] > 0 and tB_r["p_valor"] < ALPHA,
        "margem %: negativa e significativa sem nov/dez": tB_m["inclinacao_por_mes"] < 0 and tB_m["p_valor"] < ALPHA,
    }
    for k, ok in cond.items():
        out(f"  [{'SIM' if ok else 'NÃO'}] {k}")
    out(f"  Corte adicional: canais com queda de margem % significativa = {resumo_corte['canal'][0]}/{resumo_corte['canal'][1]}; "
        f"categorias = {resumo_corte['categoria'][0]}/{resumo_corte['categoria'][1]}.")
    veredito = "SUSTENTA a premissa" if all(cond.values()) else "NÃO SUSTENTA a premissa (refuta/reformula)"
    out(f"\nVEREDITO PROPOSTO H0: {veredito} — na régua da margem de contribuição reportada.")
    out.salvar()


if __name__ == "__main__":
    main()
