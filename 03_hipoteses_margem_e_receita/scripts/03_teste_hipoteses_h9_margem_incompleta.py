"""
03_teste_hipoteses_h9_margem_incompleta.py — Fase 2.4, H9

Hipótese: a margem reportada (`margem_contribuicao`) é incompleta — não abate
devolução nem cancelamento — e por isso a empresa otimiza a métrica errada.

Sub-hipóteses testadas:
  H9.a  A fórmula de margem_contribuicao não tem nenhum termo de devolução ou
        cancelamento (formaliza as notas [AH] da seção 7 da 2.3).
  H9.b  A margem "cheia" (após devolução, com premissas P1/P2 declaradas em
        comum_hipoteses.py) conta uma história diferente da reportada — no
        tempo, por canal ou por categoria.
  H9.c  Vale-Troca é crédito de devolução recirculando como receita "nova".

Corte de checagem de H9.b: além de mês, canal e categoria, as 28 células
canal × categoria (para ver se a ordem se mantém quando as duas dimensões são
cruzadas).

Critério (2.3): CONFIRMA se a fórmula não abater devolução/cancelamento E a
margem cheia se comportar diferente da reportada. REFUTA se as duas métricas
contarem a mesma história.
Régua de "história diferente" (proposta, declarada): o custo da devolução
(gap reportada − P2, em p.p. da receita líquida) varia entre grupos ALÉM DO
ACASO — teste de permutação, p < 0,05/4 (Bonferroni nos 4 cortes) — OU a
tendência mensal muda de sinal ou de significância. Trocas de posição no
ranking sozinhas NÃO bastam: a margem reportada entre categorias e entre canais
(fora o Marketplace) difere por décimos de p.p., e qualquer ruído troca a ordem.
(Uma primeira versão deste script usava "mudança ≥ 2 posições" como régua; foi
substituída por gerar falso positivo com grupos quase empatados.)

Comissão de marketplace e mídia não estão em vendas: ficam para H2.

Uso: python scripts/03_teste_hipoteses_h9_margem_incompleta.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import (  # noqa: E402
    ALPHA, PREMISSAS_DEVOLUCAO, Saida, carregar_vendas, frete_reverso_premissa,
    resultado_realizado, tabela_taxa, tendencia,
)

NOME = "h9_margem_incompleta"
N_PERMUTACOES = 2000


def permutacao_gap(df: pd.DataFrame, grupo, n_perm: int = N_PERMUTACOES, semente: int = 42) -> dict:
    """O custo de devolução (reportada − P2, em % da RL) varia entre grupos além do acaso?

    Estatística: amplitude (máx − mín) do gap entre os grupos. Distribuição nula:
    rótulos de grupo embaralhados entre os itens (mantém o tamanho de cada grupo).
    """
    codigos = df.groupby(grupo, observed=True).ngroup().to_numpy()
    custo = (df["margem_contribuicao"] - df["res_P2"]).to_numpy()
    rl = df["receita_liquida"].to_numpy()
    k = codigos.max() + 1

    def amplitude(c: np.ndarray) -> float:
        gap = np.bincount(c, weights=custo, minlength=k) / np.bincount(c, weights=rl, minlength=k)
        return float(gap.max() - gap.min())

    obs = amplitude(codigos)
    rng = np.random.default_rng(semente)
    nula = np.array([amplitude(rng.permutation(codigos)) for _ in range(n_perm)])
    return {"amplitude_gap_obs_pp": obs * 100, "amplitude_p95_acaso_pp": float(np.percentile(nula, 95)) * 100,
            "p_valor": (np.sum(nula >= obs) + 1) / (n_perm + 1)}


def margens_ajustadas(df: pd.DataFrame, por) -> pd.DataFrame:
    g = df.groupby(por, observed=True).agg(
        itens=("order_id", "size"),
        receita_liquida=("receita_liquida", "sum"),
        reportada=("margem_contribuicao", "sum"),
        P1=("res_P1", "sum"),
        P2=("res_P2", "sum"),
        taxa_devolucao_pct=("devolvido", "mean"),
    )
    g["taxa_devolucao_pct"] *= 100
    for c in ("reportada", "P1", "P2"):
        g[f"{c}_%RL"] = g[c] / g["receita_liquida"] * 100
    g["gap_P2_pp"] = g["reportada_%RL"] - g["P2_%RL"]
    g["rank_reportada"] = g["reportada_%RL"].rank(ascending=False).astype(int)
    g["rank_P2"] = g["P2_%RL"].rank(ascending=False).astype(int)
    g["mudanca_rank"] = (g["rank_reportada"] - g["rank_P2"]).abs()
    return g


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()

    # ------------------------------------------------------------------ 1
    out.secao("1. Checagens estruturais (formaliza as notas [AH] da seção 7 da 2.3)")
    n_ped = v["order_id"].nunique()
    multi = int((v.groupby("order_id").size() > 1).sum())
    out(f"Linhas: {len(v)} | order_id distintos: {n_ped} | pedidos com mais de 1 item: {multi}")
    out("→ 1 linha = 1 pedido = 1 SKU (corrige o grão descrito no perfilamento). "
        "Ticket médio = receita líquida por pedido = por item.")
    col_mc = "margem_contribuicao = receita_liquida − custo_produto − custo_frete"
    residuos = {
        "receita_bruta = quantidade × preco_unitario": v["receita_bruta"] - v["quantidade"] * v["preco_unitario"],
        "receita_liquida = receita_bruta − desconto_reais": v["receita_liquida"] - (v["receita_bruta"] - v["desconto_reais"]),
        col_mc: v["margem_contribuicao"] - (v["receita_liquida"] - v["custo_produto"] - v["custo_frete"]),
    }
    for nome, r in residuos.items():
        out(f"  {nome}: resíduo máximo {r.abs().max():.1e}; linhas com |resíduo| > R$ 0,01 = {int((r.abs() > 0.01).sum())}")

    v = v.assign(
        identidade_ok=residuos[col_mc].abs() <= 0.01,
        margem_pct_item=v["margem_contribuicao"] / v["receita_liquida"] * 100,
    )
    grupos = {
        "devolvido=False": v[~v["devolvido"]],
        "devolvido=True": v[v["devolvido"]],
        "status=Aprovado": v[v["status_pagamento"].eq("Aprovado")],
        "status=Cancelado": v[v["status_pagamento"].eq("Cancelado")],
        "status=Aguardando": v[v["status_pagamento"].eq("Aguardando")],
    }
    linhas = [{
        "grupo": nome,
        "itens": len(df),
        "identidade_mc_ok_%": df["identidade_ok"].mean() * 100,
        "receita_liquida_media": df["receita_liquida"].mean(),
        "margem_media_R$": df["margem_contribuicao"].mean(),
        "margem_%RL_soma/soma": df["margem_contribuicao"].sum() / df["receita_liquida"].sum() * 100,
    } for nome, df in grupos.items()]
    out.tabela(pd.DataFrame(linhas).set_index("grupo"), "identidade_por_grupo")
    a = v[v["pagamento_aprovado"]].copy()
    mw = stats.mannwhitneyu(a.loc[a["devolvido"], "margem_pct_item"], a.loc[~a["devolvido"], "margem_pct_item"])
    kw = stats.kruskal(*[g["margem_pct_item"] for _, g in v.groupby("status_pagamento")])
    out(f"Margem % por item, devolvido × não devolvido (aprovados): Mann-Whitney p={mw.pvalue:.4f}")
    out(f"Margem % por item entre status de pagamento: Kruskal-Wallis p={kw.pvalue:.4f}")
    out("→ A identidade da margem fecha em 100% das linhas, inclusive devolvidas e canceladas: "
        "não existe termo de devolução/cancelamento na fórmula.")

    # ------------------------------------------------------------------ 2
    out.secao("2. Quanto um relatório que 'soma a coluna' superestima")
    niveis = {
        "Base inteira (todos os status, com devolvidos)": v,
        "Só pagamento aprovado (receita realizada — H7)": a,
        "Aprovado e não devolvido": a[~a["devolvido"]],
    }
    linhas = [{"recorte": k, "itens": len(df), "receita_liquida": df["receita_liquida"].sum(),
               "margem_reportada": df["margem_contribuicao"].sum()} for k, df in niveis.items()]
    t = pd.DataFrame(linhas).set_index("recorte")
    t["margem_vs_base_inteira_%"] = t["margem_reportada"] / t["margem_reportada"].iloc[0] * 100
    out.tabela(t, "niveis_de_receita_margem")

    # ------------------------------------------------------------------ 3
    out.secao("3. Margem após devolução — premissas declaradas")
    fr = frete_reverso_premissa(v)
    out(PREMISSAS_DEVOLUCAO)
    out(f"  Valor do frete reverso usado em P2 (média do frete de ida, aprovados com frete>0): R$ {fr:.2f}")
    a["res_P1"] = resultado_realizado(a, "P1", fr)
    a["res_P2"] = resultado_realizado(a, "P2", fr)
    dev = a[a["devolvido"]]
    defeito = dev["motivo_devolucao"].eq("Produto com defeito")
    rl_total = a["receita_liquida"].sum()
    comp = pd.DataFrame({
        "margem_R$": [a["margem_contribuicao"].sum(), a["res_P1"].sum(), a["res_P2"].sum()],
    }, index=["reportada", "P1 (piso)", "P2 (central)"])
    comp["margem_%RL_aprovada"] = comp["margem_R$"] / rl_total * 100
    comp["diferenca_vs_reportada_R$"] = comp["margem_R$"] - comp.loc["reportada", "margem_R$"]
    comp["diferenca_pp"] = comp["margem_%RL_aprovada"] - comp.loc["reportada", "margem_%RL_aprovada"]
    out.tabela(comp, "margem_reportada_vs_ajustada")
    out(f"Denominador comum: receita líquida aprovada R$ {rl_total:,.2f} (mesmo denominador nas 3 linhas, "
        "para que a diferença seja só o custo da devolução).")
    out("Composição da diferença (P2):")
    out(f"  margem de produto estornada (RL − CMV dos devolvidos): R$ {(dev['receita_liquida'] - dev['custo_produto']).sum():,.2f}")
    out(f"  frete reverso ({len(dev)} devoluções × R$ {fr:.2f}): R$ {len(dev) * fr:,.2f}")
    out(f"  CMV perdido de itens com defeito ({int(defeito.sum())} itens): R$ {dev.loc[defeito, 'custo_produto'].sum():,.2f}")
    out(f"Itens aprovados devolvidos: {len(dev)} de {len(a)} ({len(dev) / len(a) * 100:.2f}%); "
        f"receita líquida desses itens: R$ {dev['receita_liquida'].sum():,.2f}.")

    # ------------------------------------------------------------------ 4
    out.secao("4. A margem cheia conta outra história? (tempo, canal, categoria, canal×categoria)")
    mensal = margens_ajustadas(a, "mes")
    out.tabela(mensal[["itens", "taxa_devolucao_pct", "reportada_%RL", "P1_%RL", "P2_%RL", "gap_P2_pp"]], "mensal_reportada_vs_ajustada")
    m23 = mensal.loc[pd.Period("2023-01", "M"):pd.Period("2023-12", "M")]
    tend = {}
    for c in ("reportada_%RL", "P2_%RL", "taxa_devolucao_pct"):
        tend[c] = tendencia(m23[c])
        out(f"  Tendência 2023 {c}: {tend[c]['inclinacao_por_mes']:+.4f} p.p./mês, p={tend[c]['p_valor']:.4f}")
    r_mes = stats.pearsonr(m23["reportada_%RL"], m23["P2_%RL"])
    out(f"  Correlação mensal reportada × P2 (2023): r={r_mes.statistic:.3f} (p={r_mes.pvalue:.4f})")
    out(f"  Amplitude mensal do gap P2 em 2023: {m23['gap_P2_pp'].min():.2f} a {m23['gap_P2_pp'].max():.2f} p.p.")

    perm = {"mês": permutacao_gap(a, "mes")}
    resumo_rank = {}
    for dim in ("canal", "categoria", ["canal", "categoria"]):
        rotulo = dim if isinstance(dim, str) else "canal×categoria"
        g = margens_ajustadas(a, dim)
        out(f"\n  -- {rotulo} --")
        out.tabela(g[["itens", "taxa_devolucao_pct", "reportada_%RL", "P2_%RL", "gap_P2_pp",
                      "rank_reportada", "rank_P2", "mudanca_rank"]].sort_values("rank_reportada"),
                   f"ranking_{rotulo.replace('×', '_x_')}")
        rho = stats.spearmanr(g["reportada_%RL"], g["P2_%RL"])
        resumo_rank[rotulo] = (rho.statistic, int(g["mudanca_rank"].max()), len(g))
        out(f"  Spearman reportada × P2: {rho.statistic:.3f}; maior mudança de posição: {int(g['mudanca_rank'].max())} "
            f"(de {len(g)} grupos); gap P2 de {g['gap_P2_pp'].min():.2f} a {g['gap_P2_pp'].max():.2f} p.p.")
        perm[rotulo] = permutacao_gap(a, dim)

    out(f"\n  Teste de permutação ({N_PERMUTACOES} embaralhamentos): a amplitude do gap entre grupos é maior que o acaso?")
    tperm = pd.DataFrame(perm).T
    tperm.index.name = "corte"
    out.tabela(tperm, "permutacao_gap", casas=4)
    out(f"  Limiar com Bonferroni (4 cortes): p < {ALPHA / len(perm):.4f}.")

    # ------------------------------------------------------------------ 5
    out.secao("5. H9.c — Vale-Troca é crédito de devolução recirculando?")
    o = v[["order_id", "customer_id", "data_pedido", "tempo_entrega_real", "devolvido", "metodo_pagamento"]].copy()
    o["data_entrega"] = o["data_pedido"] + pd.to_timedelta(o["tempo_entrega_real"], unit="D")
    primeira_dev = o[o["devolvido"]].groupby("customer_id")["data_entrega"].min()
    o["dev_anterior_possivel"] = o["customer_id"].map(primeira_dev) < o["data_pedido"]
    o["vale_troca"] = o["metodo_pagamento"].eq("Vale-Troca")
    out("Aproximação declarada: a data da devolução não existe na base; usa-se a data de entrega "
        "(data_pedido + tempo_entrega_real) do primeiro pedido devolvido do cliente como a data "
        "mais cedo em que um crédito de devolução poderia existir.")
    out.tabela(tabela_taxa(o, "dev_anterior_possivel", "vale_troca"), "vale_troca_x_devolucao_anterior")
    p_vt = stats.chi2_contingency(pd.crosstab(o["dev_anterior_possivel"], o["vale_troca"]))[1]
    out(f"Qui² (taxa de Vale-Troca com × sem devolução anterior possível): p={p_vt:.4f}")
    vt_sem = int((o["vale_troca"] & ~o["dev_anterior_possivel"]).sum())
    out(f"Pedidos pagos com Vale-Troca SEM nenhuma devolução anterior possível do cliente na base: {vt_sem} "
        f"de {int(o['vale_troca'].sum())} ({vt_sem / o['vale_troca'].sum() * 100:.1f}%).")
    out("Limitação: devoluções anteriores a 2023 não estão na base — um Vale-Troca 'sem devolução anterior' "
        "pode vir de crédito antigo. Por isso o teste principal é a comparação de taxas acima.")

    # ------------------------------------------------------------------ 6
    out.secao("6. Veredito proposto")
    h9a = bool(v["identidade_ok"].all())
    out(f"  H9.a fórmula sem termo de devolução/cancelamento: {'CONFIRMADA' if h9a else 'REFUTADA'} "
        f"(identidade fecha em {v['identidade_ok'].mean() * 100:.2f}% das linhas, inclusive devolvidas/canceladas).")
    limiar = ALPHA / len(perm)
    gap_real = [c for c, r in perm.items() if r["p_valor"] < limiar]
    sig_rep = tend["reportada_%RL"]["p_valor"] < ALPHA
    sig_p2 = tend["P2_%RL"]["p_valor"] < ALPHA
    sinal_ok = (tend["reportada_%RL"]["inclinacao_por_mes"] > 0) == (tend["P2_%RL"]["inclinacao_por_mes"] > 0)
    muda_tend = (sig_rep != sig_p2) or (not sinal_ok and (sig_rep or sig_p2))
    for rot, (rho, mx, n) in resumo_rank.items():
        out(f"  ranking {rot}: Spearman {rho:.3f}, maior mudança {mx} posição(ões) em {n} grupos "
            f"(permutação do gap p={perm[rot]['p_valor']:.4f})")
    out(f"  gap por mês: permutação p={perm['mês']['p_valor']:.4f}")
    out(f"  tendência mensal: reportada p={tend['reportada_%RL']['p_valor']:.4f} | P2 p={tend['P2_%RL']['p_valor']:.4f}")
    h9b = bool(gap_real) or muda_tend
    out(f"  H9.b margem cheia conta outra história: {'CONFIRMADA' if h9b else 'REFUTADA'} "
        f"(gap varia além do acaso em: {', '.join(gap_real) if gap_real else 'nenhum corte'}; "
        f"muda tendência: {'sim' if muda_tend else 'não'}).")
    if not h9b:
        out("  Ou seja: a margem cheia muda o NÍVEL (seção 3), mas não a ordem entre grupos nem a tendência.")
    out.salvar()


if __name__ == "__main__":
    main()
