"""
03_teste_hipoteses_h2_canais.py — Fase 2.4, H2

Hipótese: alguns canais compram volume com CAC alto, margem baixa ou pouca
recorrência.
  H2.1 margem por pedido difere entre canais (detalhe da causa em H1.2 — frete)
  H2.2 investimento por canal desproporcional à margem que o canal gera
  H2.3 canais que trazem clientes de baixa recorrência
  H2.4 comissão de marketplace não registrada — SEM DADO, não testável

Teste:
  1. Marketing na janela de vendas, com PREMISSA declarada: o investimento de
     cada campanha se distribui uniformemente entre data_inicio e data_fim
     (pro rata por dia). Robustez: campanhas que COMEÇAM na janela, sem pro rata.
  2. Escala: investimento, receita_gerada e conversões de marketing × receita,
     margem e pedidos de vendas, por canal.
  3. Participação no investimento × participação na margem (índice).
  4. Corte adicional 1: o índice por trimestre de 2023 (estabilidade).
  5. Corte adicional 2: o índice dentro de cada categoria (categoria_foco ×
     categoria de vendas; campanhas 'Geral' ficam fora).
  6. O gasto explica as vendas? Correlação canal × mês (2023) entre investimento
     pro rata e pedidos/margem de vendas — total e DENTRO de cada canal.
  7. ROAS por modelo de atribuição (a mistura de modelos distorce o ranking?) e
     se o ROAS de marketing concorda com o índice de vendas.
  8. H2.3 recorrência por canal da 1ª compra (só clientes consistentes — ver H5).

Critério (2.3): CONFIRMA H2.2 se houver canais com participação no investimento
muito acima da participação na margem E o padrão se repetir em outro corte.
Régua (proposta, declarada): índice = part. margem ÷ part. investimento;
"desproporcional" se < 0,8 ou > 1,2 na janela E em ≥ 3 dos 4 trimestres E em
≥ 3 das 4 categorias. Condição extra: o gasto precisa ter relação com as vendas
(correlação dentro do canal); sem isso, a comparação vira só diagnóstico de
alocação e a hipótese fica INCONCLUSIVA por limitação da base de marketing.

Uso: python scripts/03_teste_hipoteses_h2_canais.py
"""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import (  # noqa: E402
    ALPHA, JANELA_FIM_DIA, JANELA_INI, Saida, carregar_clientes, carregar_marketing,
    carregar_vendas, classe, consistencia_clientes, homogeneidade, indice, no_intervalo,
    tabela_taxa,
)

NOME = "h2_canais"


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()
    a = v[v["pagamento_aprovado"]].copy()
    m = carregar_marketing()

    # ------------------------------------------------------------------ 1
    out.secao("1. Marketing na janela de vendas (01/01/2023–26/01/2024)")
    out("PREMISSA: investimento, receita_gerada e conversões de cada campanha distribuídos uniformemente "
        "por dia entre data_inicio e data_fim (pro rata).")
    for col, novo in (("investimento_reais", "inv_janela"), ("receita_gerada", "rec_mkt_janela"), ("conversoes", "conv_janela")):
        m[novo] = no_intervalo(m, JANELA_INI, JANELA_FIM_DIA, col)
    sobrepoe = m["inv_janela"] > 0
    comeca = m["data_inicio"].between(JANELA_INI, JANELA_FIM_DIA)
    out(f"Campanhas que se sobrepõem à janela: {int(sobrepoe.sum())} de {len(m)}; investimento pro rata na janela: "
        f"R$ {m['inv_janela'].sum():,.2f}.")
    out(f"Robustez — campanhas que começam na janela: {int(comeca.sum())}; investimento total delas: "
        f"R$ {m.loc[comeca, 'investimento_reais'].sum():,.2f}.")

    # ------------------------------------------------------------------ 2
    out.secao("2. Escala marketing × vendas, por canal (janela)")
    vend = a.groupby("canal").agg(itens=("order_id", "size"), receita_liquida=("receita_liquida", "sum"),
                                  margem=("margem_contribuicao", "sum"))
    mk = m.groupby("canal")[["inv_janela", "rec_mkt_janela", "conv_janela"]].sum()
    esc = vend.join(mk)
    esc.loc["TOTAL"] = esc.sum()
    esc["invest/receita_vendas"] = esc["inv_janela"] / esc["receita_liquida"]
    esc["receita_mkt/receita_vendas"] = esc["rec_mkt_janela"] / esc["receita_liquida"]
    esc["conversoes_mkt/pedidos_vendas"] = esc["conv_janela"] / esc["itens"]
    out.tabela(esc, "escala")
    out("→ Se as razões são ≫ 1, a base de marketing não reconcilia em nível absoluto com vendas "
        "(CAC/ROAS absolutos não podem ser combinados com a margem de vendas; só comparações relativas).")

    # ------------------------------------------------------------------ 3
    out.secao("3. Participação no investimento × participação na margem (janela)")
    mg_canal = a.groupby("canal")["margem_contribuicao"].sum()
    t_jan = indice(m.groupby("canal")["inv_janela"].sum(), mg_canal)
    t_jan["part_pedidos_%"] = a.groupby("canal").size() / len(a) * 100
    t_jan["classe"] = t_jan["indice"].map(classe)
    out.tabela(t_jan.sort_values("indice"), "indice_janela")
    t_rob = indice(m.loc[comeca].groupby("canal")["investimento_reais"].sum(), mg_canal)
    rho_rob = stats.spearmanr(t_jan["indice"], t_rob.loc[t_jan.index, "indice"]).statistic
    out(f"Robustez (campanhas que começam na janela, sem pro rata): índice de {t_rob['indice'].min():.2f} a "
        f"{t_rob['indice'].max():.2f}; Spearman com o índice pro rata = {rho_rob:.3f}.")

    # ------------------------------------------------------------------ 4
    out.secao("4. Corte adicional 1 — índice por trimestre de 2023")
    idx_q = {}
    for q in pd.period_range("2023Q1", "2023Q4", freq="Q"):
        ini, fim = q.start_time.normalize(), q.end_time.normalize()
        inv = m.assign(x=no_intervalo(m, ini, fim, "investimento_reais")).groupby("canal")["x"].sum()
        sel = (a["data_pedido"] >= ini) & (a["data_pedido"] < fim + pd.Timedelta(days=1))
        idx_q[str(q)] = indice(inv, a[sel].groupby("canal")["margem_contribuicao"].sum())["indice"]
    Q = pd.DataFrame(idx_q)
    Q["janela"] = t_jan["indice"]
    out.tabela(Q, "indice_por_trimestre")
    rhos = [stats.spearmanr(Q[x], Q[y]).statistic for x, y in combinations(Q.columns[:4], 2)]
    out(f"Spearman entre pares de trimestres (ordem dos canais pelo índice): média {np.mean(rhos):.3f}, "
        f"mín {np.min(rhos):.3f}, máx {np.max(rhos):.3f}.")
    cls_q = Q.iloc[:, :4].apply(lambda col: col.map(classe))

    # ------------------------------------------------------------------ 5
    out.secao("5. Corte adicional 2 — índice dentro de cada categoria")
    out(f"Campanhas 'Geral' (sem categoria) ficam fora: {m.loc[m['categoria_foco'].eq('Geral'), 'inv_janela'].sum() / m['inv_janela'].sum() * 100:.1f}% "
        "do investimento na janela.")
    idx_c = {}
    for cat in ("Acessórios", "Beleza", "Lifestyle", "Moda"):
        inv = m[m["categoria_foco"].eq(cat)].groupby("canal")["inv_janela"].sum()
        idx_c[cat] = indice(inv, a[a["categoria"].eq(cat)].groupby("canal")["margem_contribuicao"].sum())["indice"]
    C = pd.DataFrame(idx_c)
    C["janela"] = t_jan["indice"]
    out.tabela(C, "indice_por_categoria")
    for cat in idx_c:
        out(f"  Spearman {cat} × janela: {stats.spearmanr(C[cat], C['janela']).statistic:.3f}")
    cls_c = C.iloc[:, :4].apply(lambda col: col.map(classe))

    # ------------------------------------------------------------------ 6
    out.secao("6. O gasto explica as vendas? (canal × mês, 2023)")
    meses = pd.period_range("2023-01", "2023-12", freq="M")
    inv_cm = pd.DataFrame({p: m.assign(x=no_intervalo(m, p.start_time.normalize(), p.end_time.normalize(), "investimento_reais"))
                          .groupby("canal")["x"].sum() for p in meses})
    conv_cm = pd.DataFrame({p: m.assign(x=no_intervalo(m, p.start_time.normalize(), p.end_time.normalize(), "conversoes"))
                           .groupby("canal")["x"].sum() for p in meses})
    a23 = a[a["mes"].isin(meses)]
    ped_cm = a23.groupby(["canal", "mes"]).size().unstack("mes")[meses]
    mg_cm = a23.groupby(["canal", "mes"])["margem_contribuicao"].sum().unstack("mes")[meses]
    res6 = []
    for rot, x_cm, y_cm in (("investimento × pedidos", inv_cm, ped_cm), ("investimento × margem", inv_cm, mg_cm),
                            ("conversões (mkt) × pedidos (vendas)", conv_cm, ped_cm)):
        xm = x_cm.loc[ped_cm.index]
        x, y = xm.to_numpy().ravel(), y_cm.to_numpy().ravel()
        rp = stats.spearmanr(x, y)
        xd, yd = xm.sub(xm.mean(axis=1), axis=0), y_cm.sub(y_cm.mean(axis=1), axis=0)
        rw = stats.pearsonr(xd.to_numpy().ravel(), yd.to_numpy().ravel())
        # efeito fixo de canal E de mês (painel balanceado): tira o que é comum a todos os canais no mês
        x2, y2 = xd.sub(xd.mean(axis=0), axis=1), yd.sub(yd.mean(axis=0), axis=1)
        r2 = stats.pearsonr(x2.to_numpy().ravel(), y2.to_numpy().ravel())
        res6.append({"relacao": rot, "spearman_total": rp.statistic, "p_total": rp.pvalue,
                     "pearson_dentro_do_canal": rw.statistic, "p_valor_dentro": rw.pvalue,
                     "pearson_canal_e_mes": r2.statistic, "p_valor_canal_e_mes": r2.pvalue})
    t6 = pd.DataFrame(res6).set_index("relacao")
    out.tabela(t6, "gasto_x_vendas", casas=4)
    out("'dentro do canal' = cada canal centrado na própria média (n = 7 canais × 12 meses = 84). "
        "'canal e mês' = tira também a média do mês entre canais: sobra só 'este canal gastou mais do que o "
        "normal DELE, num mês em que os OUTROS canais não gastaram' — descarta tendência e sazonalidade comuns.")
    tot = pd.DataFrame({"investimento_pro_rata": inv_cm.sum(axis=0), "pedidos_vendas": ped_cm.sum(axis=0)})
    out.tabela(tot, "total_mensal_2023")
    rt = stats.pearsonr(tot["investimento_pro_rata"], tot["pedidos_vendas"])
    out(f"Totais mensais (todos os canais): Pearson investimento × pedidos = {rt.statistic:.3f} (p={rt.pvalue:.4f}). "
        f"Investimento de jan/2023 = {tot['investimento_pro_rata'].iloc[0] / tot['investimento_pro_rata'].iloc[3:].mean() * 100:.0f}% "
        "da média de abr–dez: a base de marketing começa em 01/01/2023, então os primeiros meses só têm campanhas "
        "recém-iniciadas (efeito de rampa / censura à esquerda).")

    # ------------------------------------------------------------------ 6b
    out.secao("6b. Marketing isolado 2023–2025 — o investimento cresce? (pro rata por ano)")
    anos = {}
    for ano in (2023, 2024, 2025):
        ini, fim = pd.Timestamp(f"{ano}-01-01"), pd.Timestamp(f"{ano}-12-31")
        anos[ano] = {c: no_intervalo(m, ini, fim, c).sum() for c in ("investimento_reais", "receita_gerada", "conversoes")}
    ta = pd.DataFrame(anos).T
    ta["roas"] = ta["receita_gerada"] / ta["investimento_reais"]
    ta["cac"] = ta["investimento_reais"] / ta["conversoes"]
    ta["var_investimento_%"] = ta["investimento_reais"].pct_change() * 100
    ta["var_conversoes_%"] = ta["conversoes"].pct_change() * 100
    out.tabela(ta, "marketing_por_ano")
    out("Ressalva: 2023 tem rampa de entrada (ver acima); campanhas 'Ativa' terminam em 31/12/2025 na base "
        "(censura à direita). Não cruza com vendas fora da janela — é leitura da base de marketing isolada.")

    # ------------------------------------------------------------------ 7
    out.secao("7. ROAS por modelo de atribuição (base marketing isolada)")
    for rot, base in (("todas as campanhas 2023–2025", m), ("campanhas que tocam a janela", m[sobrepoe])):
        med = base.groupby(["canal", "atribuicao"])["roas"].median().unstack()
        out(f"\n  {rot} — ROAS mediano:")
        out.tabela(med, f"roas_mediano_{'todas' if base is m else 'janela'}")
        rh = [stats.spearmanr(med[x], med[y]).statistic for x, y in combinations(med.columns, 2)]
        kw = [stats.kruskal(*[g["roas"] for _, g in base[base["canal"].eq(c)].groupby("atribuicao")]).pvalue for c in med.index]
        out(f"  Spearman do ranking de canais entre modelos: {', '.join(f'{r:.3f}' for r in rh)}; "
            f"Kruskal-Wallis (modelo dentro do canal): menor p = {min(kw):.4f} de {len(kw)} canais.")
    roas_canal = m[sobrepoe].groupby("canal")["roas"].median()
    rho_roas = stats.spearmanr(roas_canal.loc[t_jan.index], t_jan["indice"])
    out(f"\nConcordância entre bases: Spearman(ROAS mediano de marketing, índice margem/invest de vendas) = "
        f"{rho_roas.statistic:.3f} (p={rho_roas.pvalue:.4f}).")
    out.tabela(pd.DataFrame({"roas_mediano_mkt": roas_canal, "indice_vendas": t_jan["indice"]}).sort_values("roas_mediano_mkt"),
               "roas_x_indice")

    # ------------------------------------------------------------------ 8
    out.secao("8. H2.3 recorrência por canal da 1ª compra (clientes consistentes — ver H5)")
    c = carregar_clientes()
    cons = consistencia_clientes(v, c)
    ok = cons.index[cons["consistente_pedidos"]]
    out(f"Clientes compradores: {len(cons)}; consistentes (pedidos em vendas ≤ total_pedidos_historico): {len(ok)}; "
        f"excluídos: {len(cons) - len(ok)}, que somam {int(cons.loc[~cons['consistente_pedidos'], 'pedidos_vendas'].sum())} pedidos.")
    aa = a[a["customer_id"].isin(ok)].sort_values("data_pedido")
    cli = aa.groupby("customer_id").agg(canal_aquisicao=("canal", "first"), pedidos=("order_id", "size"),
                                        primeira=("data_pedido", "min"), canais=("canal", "nunique"))
    cli["recompra"] = cli["pedidos"] >= 2
    out.tabela(tabela_taxa(cli, "canal_aquisicao", "recompra"), "recompra_por_canal")
    h23 = homogeneidade(cli, "canal_aquisicao", "recompra")
    out(f"Qui² recompra × canal da 1ª compra: p={h23['p_valor']:.4f}, amplitude {h23['amplitude_pp']:.1f} p.p., n={len(cli)} clientes.")
    cedo = cli[cli["primeira"] <= "2023-06-30"]
    h23b = homogeneidade(cedo, "canal_aquisicao", "recompra")
    out(f"Corte adicional (1ª compra até 30/06/2023, ≥ 7 meses para recomprar): n={len(cedo)}, p={h23b['p_valor']:.4f}, "
        f"amplitude {h23b['amplitude_pp']:.1f} p.p.")
    rec = cli[cli["recompra"]]
    out(f"Entre os que recompraram ({len(rec)}), {(rec['canais'] > 1).mean() * 100:.1f}% compraram por mais de um canal "
        "→ 'canal de aquisição' não é atributo estável do cliente nesta base.")

    # ------------------------------------------------------------------ 9
    out.secao("9. Veredito proposto")
    mkp = t_jan.loc["Marketplace"]
    out(f"  H2.1 margem por canal: Marketplace {a.loc[a['canal'].eq('Marketplace'), 'margem_contribuicao'].sum() / a.loc[a['canal'].eq('Marketplace'), 'receita_liquida'].sum() * 100:.2f}% "
        f"vs demais {a.loc[~a['canal'].eq('Marketplace'), 'margem_contribuicao'].sum() / a.loc[~a['canal'].eq('Marketplace'), 'receita_liquida'].sum() * 100:.2f}% "
        "(causa: frete — ver H1.2).")
    desprop = []
    for canal in t_jan.index:
        cj = t_jan.loc[canal, "classe"]
        if cj == "proporcional":
            continue
        nq = int((cls_q.loc[canal] == cj).sum())
        nc = int((cls_c.loc[canal] == cj).sum())
        out(f"  {canal}: índice janela {t_jan.loc[canal, 'indice']:.2f} ({cj}); mesma classe em {nq}/4 trimestres e {nc}/4 categorias")
        if nq >= 3 and nc >= 3:
            desprop.append(canal)
    out(f"  Canais desproporcionais e estáveis nos dois cortes: {', '.join(desprop) if desprop else 'nenhum'}")
    dentro = t6.loc["investimento × pedidos"]
    liga = dentro["p_valor_canal_e_mes"] < ALPHA and dentro["pearson_canal_e_mes"] > 0
    out(f"  Gasto explica vendas do canal, com efeito fixo de canal e de mês: {'SIM' if liga else 'NÃO'} "
        f"(r={dentro['pearson_canal_e_mes']:.3f}, p={dentro['p_valor_canal_e_mes']:.4f}; "
        f"só com efeito de canal era r={dentro['pearson_dentro_do_canal']:.3f}, p={dentro['p_valor_dentro']:.4f})")
    s = t_jan.loc["Marketplace", "part_invest_%"] / 100
    rl_mkp = a.loc[a["canal"].eq("Marketplace"), "receita_liquida"].sum()
    c_star = (mg_canal["Marketplace"] - s * mg_canal.sum()) / (rl_mkp * (1 - s))
    out(f"  Sensibilidade H2.4: comissão de marketplace ≥ {c_star * 100:.1f}% da receita líquida do canal levaria o índice "
        "do Marketplace a ≤ 1,0 (proporcional). A taxa real não está na base — premissa a validar.")
    if desprop and liga:
        ver = "CONFIRMADA"
    elif desprop:
        ver = "INCONCLUSIVA — há desproporção estável, mas o gasto de marketing não se relaciona com as vendas"
    else:
        ver = "REFUTADA" if liga else "INCONCLUSIVA — sem desproporção estável e base de marketing sem relação com vendas"
    out(f"  H2.2: {ver}")
    out(f"  H2.3: n={len(cli)} clientes consistentes, p={h23['p_valor']:.4f} → "
        f"{'diferença entre canais' if h23['p_valor'] < ALPHA else 'sem diferença detectável (amostra pequena)'}")
    out("  H2.4: não testável — não há comissão de marketplace na base (premissa necessária na 2.5).")
    out(f"  Referência: Marketplace = {mkp['part_invest_%']:.1f}% do investimento e {mkp['part_margem_%']:.1f}% da margem.")
    out.salvar()


if __name__ == "__main__":
    main()
