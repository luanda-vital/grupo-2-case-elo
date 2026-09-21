"""
03_teste_hipoteses_h7_pagamento.py — Fase 2.4, H7

Hipótese: parte da receita que "cresce" não se realiza — itens Cancelado/
Aguardando — e esse vazamento cresce no tempo ou está concentrado em algum
método de pagamento ou canal.

Teste:
  1. Tamanho do vazamento: receita registrada × realizada (pagamento_aprovado).
  2. Taxa de não aprovação por mês (tendência + qui-quadrado) e razão
     receita realizada / registrada por mês.
  3. Taxa por método de pagamento, canal e categoria (qui-quadrado, V de Cramér).
  4. Corte adicional: canal DENTRO de cada método (e método dentro de cada canal),
     para ver se um padrão de canal não é, na verdade, mix de método.
  5. Cruzamento com atendimento: tickets 'Pagamento não aprovado' apontam para
     pedidos de fato não aprovados? (todos os vínculos e só vínculos 0–30 dias).

Critério (2.3): CONFIRMA se a taxa crescer no tempo OU estiver concentrada em
método/canal identificável. REFUTA como causa da queda se for estável no tempo
(continua sendo um vazamento a dimensionar na 2.5).
Régua de "concentração relevante" (proposta, declarada): p < 0,05 E amplitude
entre grupos ≥ 3 p.p. (≈ 1/4 da taxa média de ~12%).

Uso: python scripts/03_teste_hipoteses_h7_pagamento.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import (  # noqa: E402
    ALPHA, Saida, carregar_atendimento, carregar_vendas, homogeneidade,
    tabela_taxa, tendencia,
)

NOME = "h7_pagamento"
AMPLITUDE_RELEVANTE_PP = 3.0


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()
    v["nao_aprovado"] = ~v["pagamento_aprovado"]
    v["cancelado"] = v["status_pagamento"].eq("Cancelado")
    v["aguardando"] = v["status_pagamento"].eq("Aguardando")

    # ------------------------------------------------------------------ 1
    out.secao("1. Tamanho do vazamento (janela de vendas inteira)")
    st = v.groupby("status_pagamento").agg(
        itens=("order_id", "size"), receita_liquida=("receita_liquida", "sum"),
        margem_reportada=("margem_contribuicao", "sum"))
    st["%itens"] = st["itens"] / st["itens"].sum() * 100
    st["%receita"] = st["receita_liquida"] / st["receita_liquida"].sum() * 100
    out.tabela(st, "status")
    rl_reg, rl_real = v["receita_liquida"].sum(), v.loc[v["pagamento_aprovado"], "receita_liquida"].sum()
    out(f"Receita líquida registrada: R$ {rl_reg:,.2f} | realizada (aprovada): R$ {rl_real:,.2f} | "
        f"não realizada: R$ {rl_reg - rl_real:,.2f} ({(1 - rl_real / rl_reg) * 100:.2f}%)")

    # ------------------------------------------------------------------ 2
    out.secao("2. No tempo — a taxa de não aprovação cresce?")
    mes = tabela_taxa(v, "mes", "nao_aprovado")
    mes["cancelado_%"] = v.groupby("mes")["cancelado"].mean() * 100
    mes["aguardando_%"] = v.groupby("mes")["aguardando"].mean() * 100
    rl_m = v.groupby("mes")["receita_liquida"].sum()
    rl_real_m = v[v["pagamento_aprovado"]].groupby("mes")["receita_liquida"].sum()
    mes["RL_registrada"] = rl_m
    mes["RL_realizada"] = rl_real_m
    mes["realizada/registrada_%"] = rl_real_m / rl_m * 100
    out.tabela(mes, "por_mes")
    t_taxa = tendencia(mes["taxa_%"])
    t_real = tendencia(mes["realizada/registrada_%"])
    t_ag = tendencia(mes["aguardando_%"])
    h_mes = homogeneidade(v, "mes", "nao_aprovado")
    out(f"Tendência da taxa de não aprovação (13 meses): {t_taxa['inclinacao_por_mes']:+.4f} p.p./mês, p={t_taxa['p_valor']:.4f}")
    out(f"Tendência de 'Aguardando' (checa se jan/2024 acumula pendentes recentes): {t_ag['inclinacao_por_mes']:+.4f} p.p./mês, p={t_ag['p_valor']:.4f}")
    out(f"Tendência da razão realizada/registrada: {t_real['inclinacao_por_mes']:+.4f} p.p./mês, p={t_real['p_valor']:.4f}")
    out(f"Homogeneidade entre meses: qui²={h_mes['chi2']:.2f}, gl={h_mes['gl']}, p={h_mes['p_valor']:.4f}; "
        f"amplitude {h_mes['amplitude_pp']:.2f} p.p. ({h_mes['grupo_min']} {h_mes['taxa_min_%']:.2f}% → {h_mes['grupo_max']} {h_mes['taxa_max_%']:.2f}%)")
    ano = mes.loc[pd.Period("2023-01", "M"):pd.Period("2023-12", "M")]
    tr_reg, tr_real = tendencia(ano["RL_registrada"]), tendencia(ano["RL_realizada"])
    out(f"Crescimento 2023 (tendência linear, % da média por mês): registrada {tr_reg['inclinacao_%_da_media']:+.2f}%/mês, "
        f"realizada {tr_real['inclinacao_%_da_media']:+.2f}%/mês — se iguais, o vazamento não explica 'cresce mas não vira caixa'.")

    # ------------------------------------------------------------------ 3
    out.secao("3. Concentração — método de pagamento, canal, categoria")
    resumo = []
    for dim in ("metodo_pagamento", "canal", "categoria"):
        out(f"\n  -- {dim} --")
        t = tabela_taxa(v, dim, "nao_aprovado")
        t["cancelado_%"] = v.groupby(dim)["cancelado"].mean() * 100
        t["aguardando_%"] = v.groupby(dim)["aguardando"].mean() * 100
        out.tabela(t, f"por_{dim}")
        resumo.append(homogeneidade(v, dim, "nao_aprovado"))
    resumo.append(h_mes)
    res = pd.DataFrame(resumo).set_index("corte")
    out("\n  Resumo dos cortes (não aprovado):")
    out.tabela(res, "resumo_cortes", casas=4)

    # ------------------------------------------------------------------ 4
    out.secao("4. Corte adicional — canal dentro de cada método e método dentro de cada canal")
    piv = v.pivot_table(index="canal", columns="metodo_pagamento", values="nao_aprovado", aggfunc="mean") * 100
    out.tabela(piv, "canal_x_metodo_taxa")
    cruz = []
    for met, sub in v.groupby("metodo_pagamento"):
        h = homogeneidade(sub, "canal", "nao_aprovado")
        cruz.append({"dentro_de": f"método={met}", "corte": "canal", "n": len(sub), **{k: h[k] for k in ("amplitude_pp", "p_valor")}})
    for can, sub in v.groupby("canal"):
        h = homogeneidade(sub, "metodo_pagamento", "nao_aprovado")
        cruz.append({"dentro_de": f"canal={can}", "corte": "método", "n": len(sub), **{k: h[k] for k in ("amplitude_pp", "p_valor")}})
    out.tabela(pd.DataFrame(cruz).set_index("dentro_de"), "cortes_cruzados", casas=4)
    n_testes = len(cruz)
    out(f"{n_testes} testes; com α=0,05 espera-se ~{n_testes * ALPHA:.1f} 'significativo' por acaso "
        f"(limiar de Bonferroni: p < {ALPHA / n_testes:.4f}).")

    # ------------------------------------------------------------------ 5
    out.secao("5. Atendimento — tickets 'Pagamento não aprovado' apontam para pedidos não aprovados?")
    at = carregar_atendimento()
    x = at.merge(v[["order_id", "data_pedido", "nao_aprovado"]], on="order_id", how="inner")
    x["lag_dias"] = (x["data_abertura"] - x["data_pedido"]).dt.days
    x["tema_pagamento"] = x["categoria_problema"].eq("Pagamento não aprovado")
    for rot, base in (("todos os vínculos", x), ("vínculo 0–30 dias após o pedido", x[(x["lag_dias"] >= 0) & (x["lag_dias"] <= 30)])):
        t = tabela_taxa(base, "tema_pagamento", "nao_aprovado")
        ct = pd.crosstab(base["tema_pagamento"], base["nao_aprovado"])
        p = stats.chi2_contingency(ct)[1]
        out(f"\n  {rot}: {len(base)} tickets (tema pagamento = {int(base['tema_pagamento'].sum())})")
        out.tabela(t.rename(index={True: "tema = Pagamento não aprovado", False: "outros temas"}),
                   f"atendimento_{'todos' if rot.startswith('todos') else '0a30d'}")
        out(f"  qui² p={p:.4f}")

    # ------------------------------------------------------------------ 6
    out.secao("6. Veredito proposto")
    cresce = t_taxa["inclinacao_por_mes"] > 0 and t_taxa["p_valor"] < ALPHA
    conc = res[(res["p_valor"] < ALPHA) & (res["amplitude_pp"] >= AMPLITUDE_RELEVANTE_PP)]
    out(f"  Taxa cresce no tempo: {'SIM' if cresce else 'NÃO'} (p={t_taxa['p_valor']:.4f})")
    out(f"  Concentração relevante (p<0,05 e amplitude ≥ {AMPLITUDE_RELEVANTE_PP} p.p.): "
        + (", ".join(conc.index) if len(conc) else "nenhum corte"))
    ver = "CONFIRMADA" if (cresce or len(conc)) else "REFUTADA como causa da queda (vazamento estável e difuso)"
    out(f"\nVEREDITO PROPOSTO H7: {ver}. Vazamento a dimensionar na 2.5: R$ {rl_reg - rl_real:,.2f} "
        f"({(1 - rl_real / rl_reg) * 100:.2f}% da receita registrada).")
    out.salvar()


if __name__ == "__main__":
    main()
