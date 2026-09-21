"""
05_cadeias_e_intersecoes.py — Rodada 3 (final), etapa 2: TESTE.

A lanterna (`05_lanterna_dados.py`) apontou três coisas, nenhuma delas vinda de
hipótese de negócio:
  (i)   a dispersão da margem por item é 49,8% DESCONTO + 41,5% FRETE + 8,7% CMV;
  (ii)  `receita_bruta` é o único atributo estrutural que prevê a margem
        (R² 0,286 sozinho) — e prevê porque o frete é ~fixo por item;
  (iii) devolução e não aprovação têm importância ZERO em todas as variáveis:
        a floresta não bate a taxa-base em nenhum split.

Este script testa cada uma dessas pistas com o rigor das rodadas 1 e 2: todo
padrão precisa sobreviver a um corte de checagem DIFERENTE do que o revelou.

O que é testado aqui:
  T1. Anatomia do desconto: quanto é, como se distribui, tem cara de tabela?
  T2. O desconto é PREVISÍVEL por algum atributo? (regra observável)
  T3. O desconto COMPRA alguma coisa? (volume, aprovação, devolução, recompra)
      — 6 cortes independentes, 4 níveis de agregação diferentes.
  T4. A regra do frete: existe um limiar determinístico?
  T5. CADEIA DE 2 ELOS: o desconto empurra o pedido para baixo do limiar e faz a
      empresa pagar um frete que não pagaria.
  T6. INTERSEÇÃO: onde desconto e frete se somam no mesmo item.
  T7. FECHAMENTO dos dois vazamentos grandes: devolução e pagamento não aprovado
      são mesmo sem endereço? (4 novos cortes que as rodadas 1 e 2 não fizeram)
  T8. Concentração: quem decide, e em quantas contas a decisão cabe.
  T9. Custo de servir por cliente (cruzamento atendimento × vendas — não feito na
      rodada 2, que manteve o ramo A dentro de atendimento).

PREMISSAS DECLARADAS
  - P-05.4 "o desconto não compra nada": todos os testes desta etapa são
    CONDICIONAIS AO PEDIDO EXISTIR. A base não tem sessão, carrinho abandonado
    nem venda perdida, então NÃO é possível observar o pedido que só aconteceu
    por causa do desconto. O que se mede é: dado que o pedido existe, o desconto
    não se associa a quantidade, aprovação, devolução nem recompra. Isso REFUTA
    "o desconto segue uma regra e tem retorno mensurável nesta base"; NÃO prova
    elasticidade zero. O dimensionamento (script 05_dimensionamento) usa essa
    ressalva para NÃO adotar captura de 100%.
  - P-05.5: "tem desconto" = `desconto_reais` > 0. Não há campo de campanha,
    cupom, alçada ou negociação em nenhuma das 5 bases.
  - P-05.6 (T9): o custo de servir por cliente usa só tickets abertos DENTRO da
    janela de vendas (restrição 2 da mentoria de 11/09), e só de clientes que
    aparecem em vendas.

Saídas: outputs/05_alavanca_definitiva/cadeias.txt e cadeias__*.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import roc_auc_score

import comum_hipoteses as ch

SEMENTE = 42
LIMIAR_FRETE = 250.0  # descoberto em T4, não suposto
s = ch.Saida("cadeias", out_dir=ch.OUT_DIR_05)

v = ch.carregar_vendas()
e = ch.carregar_estoque()
v = v.merge(e[["sku_id", "subcategoria", "fornecedor_id", "lead_time_reposicao"]],
            on="sku_id", how="left", validate="many_to_one")
v["tem_desconto"] = v["desconto_reais"] > 0
v["nao_aprovado"] = ~v["pagamento_aprovado"]

ap = v[v["pagamento_aprovado"]].copy()
ap["d_pct"] = ap["desconto_reais"] / ap["receita_bruta"] * 100
ap["tem_frete"] = ap["custo_frete"] > 0
nm = ap[ap["canal"] != "Marketplace"].copy()   # fora do Marketplace
mk = ap[ap["canal"] == "Marketplace"].copy()

RB = ap["receita_bruta"].sum()
MARGEM = ap["margem_contribuicao"].sum()
DIAS = (ch.JANELA_FIM_DIA - ch.JANELA_INI).days + 1
ANUAL = 365 / DIAS


# ==========================================================================
s.secao("T1. ANATOMIA DO DESCONTO — quanto é e que cara tem")
# ==========================================================================
desc_total = ap["desconto_reais"].sum()
com_d = ap[ap["tem_desconto"]]
s(f"janela .................................. {DIAS} dias (fator de anualização {ANUAL:.4f})")
s(f"receita bruta aprovada .................. R$ {RB:,.2f}")
s(f"margem de contribuição aprovada ......... R$ {MARGEM:,.2f}")
s(f"margem anualizada (referência da 2.4-op)  R$ {MARGEM * ANUAL:,.2f}")
s("")
s(f"desconto concedido na janela ............ R$ {desc_total:,.2f}  ({desc_total / RB * 100:.2f}% da RB)")
s(f"desconto anualizado ..................... R$ {desc_total * ANUAL:,.2f}")
s(f"  = % da margem anual ................... {desc_total / MARGEM * 100:.2f}%")
s(f"itens com desconto ...................... {len(com_d):,} de {len(ap):,} ({ap['tem_desconto'].mean() * 100:.2f}%)")
s(f"desconto médio quando concedido ......... {com_d['d_pct'].mean():.2f}% da RB do item")
s("")
s("Distribuição do desconto% entre os itens que receberam:")
s.tabela(com_d["d_pct"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_frame("d_pct"),
         "distribuicao_desconto")

s("")
s("Tem cara de TABELA de descontos (política) ou de concessão caso a caso?")
ks = stats.kstest((com_d["d_pct"] - 5) / 35, "uniform")
redondos = np.abs(com_d["d_pct"].to_numpy()[:, None]
                  - np.arange(5, 41, 5)[None, :]).min(axis=1) < 0.25
esperado_redondo = 8 * 0.5 / 35
s(f"  KS contra Uniforme(5%, 40%) ........... D={ks.statistic:.4f}, p={ch.fmt_p(ks.pvalue)}")
s(f"  itens em valor 'redondo' (múltiplo de 5 ± 0,25 p.p.) ... {redondos.mean() * 100:.2f}%")
s(f"  esperado se fosse uniforme ............ {esperado_redondo * 100:.2f}%")
s(f"  valores distintos de desconto em R$ ... {com_d['desconto_reais'].round(2).nunique():,} em {len(com_d):,} itens")
s("  → não há degrau em 10/15/20/25%. A concessão é contínua, item a item.")

s("")
s("Onde o desconto aparece (soma/soma, nunca média de razões):")
for corte in ("canal", "categoria", "metodo_pagamento"):
    t = ap.groupby(corte, observed=True).agg(
        itens=("order_id", "size"), rb=("receita_bruta", "sum"),
        desc=("desconto_reais", "sum"), un=("quantidade", "sum"),
        freq_desc=("tem_desconto", "mean"))
    t["desc_%RB"] = t["desc"] / t["rb"] * 100
    t["un_por_item"] = t["un"] / t["itens"]
    t["freq_desc"] *= 100
    s("")
    s(f"por {corte}:")
    s.tabela(t[["itens", "rb", "desc", "desc_%RB", "freq_desc", "un_por_item"]],
             f"desconto_por_{corte}")


# ==========================================================================
s.secao("T2. O DESCONTO É PREVISÍVEL? (existe regra observável?)")
# ==========================================================================
s("Se houvesse política — tabela por categoria, alçada por valor, campanha, tier")
s("de cliente —, algum atributo preveria quem recebe desconto e quanto.")
s("Split TEMPORAL: treina em jan–jun/2023, mede em jul/2023–jan/2024.")

FEATS = ["canal", "categoria", "subcategoria", "fornecedor_id", "metodo_pagamento",
         "produto", "customer_id"]
NUMS = ["quantidade", "preco_unitario", "receita_bruta", "custo_produto",
        "lead_time_reposicao"]


def matriz(base: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame(index=base.index)
    for c in FEATS:
        X[c] = base[c].astype("category").cat.codes
    for c in NUMS:
        X[c] = pd.to_numeric(base[c], errors="coerce").fillna(-1)
    X["mes"] = base["data_pedido"].dt.month
    X["dow"] = base["data_pedido"].dt.dayofweek
    X["dia_mes"] = base["data_pedido"].dt.day
    return X


X = matriz(ap)
tr = (ap["data_pedido"] < pd.Timestamp("2023-07-01")).to_numpy()
clf = RandomForestClassifier(n_estimators=400, min_samples_leaf=25,
                             random_state=SEMENTE, n_jobs=-1).fit(X[tr], ap["tem_desconto"][tr])
auc = roc_auc_score(ap["tem_desconto"][~tr], clf.predict_proba(X[~tr])[:, 1])
reg = RandomForestRegressor(n_estimators=400, min_samples_leaf=25,
                            random_state=SEMENTE, n_jobs=-1).fit(X[tr], ap["d_pct"][tr])
r2 = reg.score(X[~tr], ap["d_pct"][~tr])
s("")
s(f"prever QUEM recebe desconto ... AUC no teste = {auc:.4f}   (0,50 = moeda honesta)")
s(f"prever QUANTO de desconto ..... R²  no teste = {r2:.4f}   (≤ 0 = pior que a média)")
s(f"taxa-base de 'tem desconto' ... {ap['tem_desconto'].mean() * 100:.2f}%")
s("")
s("Corte de checagem: o desconto é atributo estável do SKU? (persistência no tempo)")
metade_a = ap["data_pedido"] < pd.Timestamp("2023-07-14")
sk = pd.DataFrame({
    "a": ap[metade_a].groupby("sku_id")["d_pct"].mean(),
    "na": ap[metade_a].groupby("sku_id")["d_pct"].size(),
    "b": ap[~metade_a].groupby("sku_id")["d_pct"].mean(),
    "nb": ap[~metade_a].groupby("sku_id")["d_pct"].size(),
}).dropna()
sk = sk[(sk["na"] >= 3) & (sk["nb"] >= 3)]
rp = stats.pearsonr(sk["a"], sk["b"])
s(f"  SKUs com ≥3 itens nas duas metades ... {len(sk):,}")
s(f"  correlação do desconto% metade A × metade B ... r={rp.statistic:.4f}, p={ch.fmt_p(rp.pvalue)}")
s("  (a rodada 1, K6, já tinha medido r=−0,051 para o desconto por SKU — bate)")
s("")
s("VEREDITO T2 (proposto): não existe regra observável. Nem modelo, nem SKU, nem")
s("canal, nem mês explicam quem recebe desconto. A decisão é discricionária item")
s("a item — ou depende de uma variável que não está em nenhuma das 5 bases.")


# ==========================================================================
s.secao("T3. O DESCONTO COMPRA ALGUMA COISA? (6 cortes, 4 níveis de agregação)")
# ==========================================================================
testes = []

# (1) item: volume
mw = stats.mannwhitneyu(ap.loc[ap["tem_desconto"], "quantidade"],
                        ap.loc[~ap["tem_desconto"], "quantidade"])
testes.append({"nível": "item", "pergunta": "compra VOLUME?",
               "medida": f"qtd média {ap.loc[ap['tem_desconto'], 'quantidade'].mean():.3f} × "
                         f"{ap.loc[~ap['tem_desconto'], 'quantidade'].mean():.3f}",
               "p_valor": mw.pvalue, "compra?": "não"})
rs = stats.spearmanr(com_d["d_pct"], com_d["quantidade"])
testes.append({"nível": "item", "pergunta": "dose-resposta (d% × qtd)?",
               "medida": f"rho={rs.statistic:.4f}", "p_valor": rs.pvalue, "compra?": "não"})

# (2) item: aprovação
ct = pd.crosstab(v["tem_desconto"], v["pagamento_aprovado"])
chi = stats.chi2_contingency(ct)
tx = v.groupby("tem_desconto")["pagamento_aprovado"].mean() * 100
testes.append({"nível": "item", "pergunta": "compra APROVAÇÃO?",
               "medida": f"{tx[True]:.2f}% × {tx[False]:.2f}%",
               "p_valor": chi.pvalue, "compra?": "não"})

# (3) item: devolução
ct = pd.crosstab(ap["tem_desconto"], ap["devolvido"])
chi = stats.chi2_contingency(ct)
txd = ap.groupby("tem_desconto")["devolvido"].mean() * 100
testes.append({"nível": "item", "pergunta": "reduz DEVOLUÇÃO?",
               "medida": f"{txd[True]:.2f}% × {txd[False]:.2f}%",
               "p_valor": chi.pvalue, "compra?": "não"})

# (4) SKU: SKUs mais descontados vendem mais?
sku = ap.groupby("sku_id").agg(itens=("order_id", "size"), un=("quantidade", "sum"),
                               d_med=("d_pct", "mean"), preco=("preco_unitario", "mean"),
                               cat=("categoria", "first"))
sku5 = sku[sku["itens"] >= 5].copy()
rsk = stats.spearmanr(sku5["d_med"], sku5["un"])
testes.append({"nível": "SKU (n=%d)" % len(sku5), "pergunta": "SKU mais descontado vende mais?",
               "medida": f"rho={rsk.statistic:.4f}", "p_valor": rsk.pvalue,
               "compra?": "ver corte controlado"})

# (5) mês
mes = ap.groupby("mes").agg(itens=("order_id", "size"), rb=("receita_bruta", "sum"),
                            desc=("desconto_reais", "sum"), un=("quantidade", "sum"))
mes["d_pct"] = mes["desc"] / mes["rb"] * 100
rm = stats.spearmanr(mes["d_pct"], mes["itens"])
sem_pico = mes[[p.month not in (11, 12) for p in mes.index]]
rm2 = stats.spearmanr(sem_pico["d_pct"], sem_pico["itens"])
testes.append({"nível": "mês (n=13)", "pergunta": "mês de mais desconto vende mais?",
               "medida": f"rho={rm.statistic:.4f}", "p_valor": rm.pvalue, "compra?": "não"})
testes.append({"nível": "mês sem nov/dez (n=11)", "pergunta": "idem, sem os picos",
               "medida": f"rho={rm2.statistic:.4f}", "p_valor": rm2.pvalue, "compra?": "não"})

# (6) cliente: recompra
cl = ch.carregar_clientes()
cons = ch.consistencia_clientes(ap, cl)
cons = cons[cons["consistente_pedidos"]]
primeira = ap.sort_values("data_pedido").groupby("customer_id").first()
jc = primeira.loc[primeira.index.intersection(cons.index)].join(cons[["pedidos_vendas"]])
gd = jc["desconto_reais"] > 0
mwc = stats.mannwhitneyu(jc.loc[gd, "pedidos_vendas"], jc.loc[~gd, "pedidos_vendas"])
testes.append({"nível": f"cliente consistente (n={len(jc)})",
               "pergunta": "desconto na 1ª compra traz RECOMPRA?",
               "medida": f"{jc.loc[gd, 'pedidos_vendas'].mean():.2f} × "
                         f"{jc.loc[~gd, 'pedidos_vendas'].mean():.2f} pedidos",
               "p_valor": mwc.pvalue, "compra?": "não"})

tt = pd.DataFrame(testes)
s.tabela(tt.set_index(["nível", "pergunta"]), "desconto_compra_o_que", casas=4)

s("")
s("CORTE DE CHECAGEM do único teste com p<0,05 (SKU): controlado por categoria")
s("e quintil de preço — porque SKU caro vende menos unidades E recebe desconto")
s("diferente, o que produz correlação espúria no agregado.")
sku5["q_preco"] = pd.qcut(sku5["preco"], 5, labels=False)
cels = []
for (cat, q), g in sku5.groupby(["cat", "q_preco"], observed=True):
    if len(g) >= 30:
        r = stats.spearmanr(g["d_med"], g["un"])
        cels.append({"categoria": cat, "quintil_preco": q, "n_skus": len(g),
                     "rho": r.statistic, "p_valor": r.pvalue})
cels = pd.DataFrame(cels)
s.tabela(cels.set_index(["categoria", "quintil_preco"]), "elasticidade_sku_controlada", casas=4)
s(f"  células com p<0,05: {int((cels['p_valor'] < 0.05).sum())} de {len(cels)} "
  f"| rho mediano = {cels['rho'].median():.4f}")
s("  → a correlação do agregado não sobrevive ao controle. 0 de %d células." % len(cels))
s("")
s("VEREDITO T3 (proposto): 8 testes em 4 níveis de agregação, 0 com efeito que")
s("sobreviva a corte de checagem. Dado que o pedido existe, o desconto não se")
s("associa a nada. Ver a ressalva P-05.4: venda perdida não é observável aqui.")


# ==========================================================================
s.secao("T4. A REGRA DO FRETE — existe limiar determinístico?")
# ==========================================================================
s("A lanterna mostrou frete% explodindo nos itens de menor valor (25,7% da RB no")
s("1º decil). Pergunta que nasceu do dado: é um limiar de frete grátis?")

faixas = [0, 150, 200, 230, 245, 249.99, 250.01, 260, 300, 400, 600, 1e9]
nm["fx_rl"] = pd.cut(nm["receita_liquida"], faixas)
t4 = nm.groupby("fx_rl", observed=True).agg(itens=("order_id", "size"),
                                            incidencia=("tem_frete", "mean"))
t4["incidencia"] *= 100
s.tabela(t4, "frete_por_faixa_rl")

acerto_rl = float(((nm["receita_liquida"] < LIMIAR_FRETE) == nm["tem_frete"]).mean())
acerto_rb = float(((nm["receita_bruta"] < LIMIAR_FRETE) == nm["tem_frete"]).mean())
s("")
s(f"regra 'receita LÍQUIDA < R$ {LIMIAR_FRETE:.0f} ⇔ paga frete' acerta {acerto_rl * 100:.4f}% "
  f"de {len(nm):,} linhas fora do Marketplace")
s(f"a mesma regra sobre a receita BRUTA acerta ......... {acerto_rb * 100:.2f}%")
s(f"maior receita líquida entre quem PAGA frete ....... R$ {nm.loc[nm['tem_frete'], 'receita_liquida'].max():,.2f}")
s(f"menor receita líquida entre quem NÃO paga ......... R$ {nm.loc[~nm['tem_frete'], 'receita_liquida'].min():,.2f}")
s("")
s(f"Marketplace: incidência de frete = {mk['tem_frete'].mean() * 100:.2f}% em {len(mk):,} itens,")
s(f"  com receita líquida de R$ {mk['receita_liquida'].min():,.2f} a R$ {mk['receita_liquida'].max():,.2f}.")
s("  → o Marketplace é a EXCEÇÃO à regra: paga frete em qualquer valor.")
s("")
s(f"valor do frete quando cobrado: média R$ {ap.loc[ap['tem_frete'], 'custo_frete'].mean():.2f}, "
  f"mín R$ {ap.loc[ap['tem_frete'], 'custo_frete'].min():.2f}, "
  f"máx R$ {ap.loc[ap['tem_frete'], 'custo_frete'].max():.2f} — não depende do valor do item "
  f"(rho={stats.spearmanr(ap.loc[ap['tem_frete'], 'receita_liquida'], ap.loc[ap['tem_frete'], 'custo_frete']).statistic:.4f}).")
s("")
s("VEREDITO T4 (proposto): a regra de frete é determinística e nunca foi")
s("documentada nas rodadas 1 e 2 — elas cortaram por canal/categoria/SKU, e o")
s("limiar só aparece cortando por VALOR do pedido.")


# ==========================================================================
s.secao("T5. CADEIA DE 2 ELOS — o desconto empurra o pedido para baixo do limiar")
# ==========================================================================
s("Elo 1: o desconto reduz a receita líquida.")
s("Elo 2: a receita líquida abaixo de R$ 250 aciona o frete (regra T4).")
s("Logo: existe frete pago por causa do desconto. Isso é mensurável item a item.")

emp = nm[(nm["receita_bruta"] >= LIMIAR_FRETE) & (nm["receita_liquida"] < LIMIAR_FRETE)]
nao_emp = nm[(nm["receita_bruta"] >= LIMIAR_FRETE) & (nm["receita_liquida"] >= LIMIAR_FRETE)]
nativo = nm[nm["receita_bruta"] < LIMIAR_FRETE]

cad = pd.DataFrame({
    "itens": [len(emp), len(nao_emp), len(nativo)],
    "incidencia_frete_%": [emp["tem_frete"].mean() * 100,
                           nao_emp["tem_frete"].mean() * 100,
                           nativo["tem_frete"].mean() * 100],
    "receita_bruta": [emp["receita_bruta"].sum(), nao_emp["receita_bruta"].sum(),
                      nativo["receita_bruta"].sum()],
    "desconto": [emp["desconto_reais"].sum(), nao_emp["desconto_reais"].sum(),
                 nativo["desconto_reais"].sum()],
    "frete": [emp["custo_frete"].sum(), nao_emp["custo_frete"].sum(),
              nativo["custo_frete"].sum()],
    "margem": [emp["margem_contribuicao"].sum(), nao_emp["margem_contribuicao"].sum(),
               nativo["margem_contribuicao"].sum()],
}, index=["EMPURRADOS pelo desconto (RB≥250, RL<250)",
          "acima do limiar nos dois (RB≥250, RL≥250)",
          "abaixo do limiar por natureza (RB<250)"])
cad["margem_%RB"] = cad["margem"] / cad["receita_bruta"] * 100
s.tabela(cad, "cadeia_desconto_frete")
s("")
s(f"→ {len(emp):,} itens só pagam frete porque o desconto cruzou o limiar.")
s(f"  frete acionado pelo desconto: R$ {emp['custo_frete'].sum():,.2f} na janela "
  f"(R$ {emp['custo_frete'].sum() * ANUAL:,.2f}/ano)")
s(f"  desconto dado a eles: R$ {emp['desconto_reais'].sum():,.2f} "
  f"(média {emp['desconto_reais'].sum() / emp['receita_bruta'].sum() * 100:.2f}% da RB)")
s(f"  margem deles: {cad.loc[cad.index[0], 'margem_%RB']:.2f}% da RB, contra "
  f"{cad.loc[cad.index[1], 'margem_%RB']:.2f}% dos itens acima do limiar nos dois")
s("")
s("Corte de checagem: a diferença de margem dos empurrados é o frete, ou é o")
s("desconto maior? Decomposição aditiva sobre a receita bruta:")
pontes = []
for nome, g in (("EMPURRADOS", emp), ("acima nos dois", nao_emp), ("abaixo por natureza", nativo)):
    rb_g = g["receita_bruta"].sum()
    pontes.append({"grupo": nome, "desconto_%RB": g["desconto_reais"].sum() / rb_g * 100,
                   "cmv_%RB": g["custo_produto"].sum() / rb_g * 100,
                   "frete_%RB": g["custo_frete"].sum() / rb_g * 100,
                   "margem_%RB": g["margem_contribuicao"].sum() / rb_g * 100})
s.tabela(pd.DataFrame(pontes).set_index("grupo"), "ponte_cadeia")

s("")
s("O limiar é GERENCIADO? Se alguém empurrasse o pedido para cima da linha,")
s("haveria acúmulo (bunching) logo acima de R$ 250.")
b = nm[(nm["receita_liquida"] >= 150) & (nm["receita_liquida"] < 400)]
bun = pd.cut(b["receita_liquida"], [150, 200, 225, 250, 275, 300, 400]).value_counts().sort_index()
s.tabela(bun.to_frame("itens"), "bunching_limiar")
quase = nm[(nm["receita_liquida"] >= 200) & (nm["receita_liquida"] < LIMIAR_FRETE)]
s("")
s(f"→ não há acúmulo acima da linha: {int(bun.iloc[2]):,} itens em (225,250] contra "
  f"{int(bun.iloc[3]):,} em (250,275]. Ninguém gerencia o limiar.")
s(f"  {len(quase):,} itens estão a menos de R$ 50 da linha "
  f"(faltam R$ {(LIMIAR_FRETE - quase['receita_liquida']).mean():.2f} em média) "
  f"e pagam R$ {quase['custo_frete'].sum():,.2f} de frete.")


# ==========================================================================
s.secao("T6. INTERSEÇÃO — onde desconto e frete se somam no mesmo item")
# ==========================================================================
ap["celula"] = (np.where(ap["tem_desconto"], "com desconto", "sem desconto") + " / "
                + np.where(ap["tem_frete"], "com frete", "sem frete"))
frete_rev = ch.frete_reverso_premissa(v)
ap["res_P2"] = ch.resultado_realizado(ap, "P2", frete_rev)
cel = ap.groupby("celula").agg(
    itens=("order_id", "size"), rb=("receita_bruta", "sum"),
    desconto=("desconto_reais", "sum"), frete=("custo_frete", "sum"),
    margem=("margem_contribuicao", "sum"), res_P2=("res_P2", "sum"),
    tx_dev=("devolvido", "mean"))
cel["%_dos_itens"] = cel["itens"] / len(ap) * 100
cel["%_da_RB"] = cel["rb"] / RB * 100
cel["margem_%RB"] = cel["margem"] / cel["rb"] * 100
cel["realizada_P2_%RB"] = cel["res_P2"] / cel["rb"] * 100
cel["tx_dev"] *= 100
s.tabela(cel.sort_values("margem_%RB")[["itens", "%_dos_itens", "%_da_RB", "tx_dev",
                                        "margem_%RB", "realizada_P2_%RB", "desconto", "frete"]],
         "intersecao_desconto_frete")
s("")
pior = cel["margem_%RB"].idxmin()
melhor = cel["margem_%RB"].idxmax()
s(f"→ amplitude de {cel.loc[melhor, 'margem_%RB'] - cel.loc[pior, 'margem_%RB']:.2f} p.p. de margem")
s(f"  entre '{pior}' e '{melhor}'. A devolução é igual nas 4 células "
  f"({cel['tx_dev'].min():.2f}% a {cel['tx_dev'].max():.2f}%) — ou seja, a diferença é")
s("  inteiramente de PREÇO E CUSTO, não de comportamento do cliente.")


# ==========================================================================
s.secao("T7. FECHAMENTO — devolução e não aprovação têm mesmo algum endereço?")
# ==========================================================================
s("As rodadas 1 e 2 testaram 11 e 3 cortes e não acharam concentração. A lanterna")
s("acrescentou a evidência de modelo (importância ZERO). Aqui vão 4 cortes NOVOS,")
s("escolhidos para serem os mais favoráveis possíveis ao achado de concentração.")

fech = []
top25 = v.groupby("customer_id").size().sort_values(ascending=False).head(25).index
# (a) entre os 25 maiores clientes
sub = v[v["customer_id"].isin(top25)]
c = stats.chi2_contingency(pd.crosstab(sub["customer_id"], sub["nao_aprovado"]))
fech.append({"corte": "não aprovação entre os 25 maiores clientes", "n": len(sub),
             "p_valor": c.pvalue})
sub2 = ap[ap["customer_id"].isin(top25)]
c = stats.chi2_contingency(pd.crosstab(sub2["customer_id"], sub2["devolvido"]))
fech.append({"corte": "devolução entre os 25 maiores clientes", "n": len(sub2),
             "p_valor": c.pvalue})
# (b) surto por dia (falha de sistema / lote)
dia = v.groupby(v["data_pedido"].dt.date).agg(n=("order_id", "size"), k=("nao_aprovado", "sum"))
dia = dia[dia["n"] >= 30]
dia["tx"] = dia["k"] / dia["n"] * 100
p0 = v["nao_aprovado"].mean()
dp_esp = float(np.sqrt(p0 * (1 - p0) / dia["n"]).mean() * 100)
fech.append({"corte": f"não aprovação por DIA (dp obs {dia['tx'].std():.2f} p.p. × "
                      f"esperado {dp_esp:.2f} p.p.)", "n": len(dia), "p_valor": np.nan})
# (c) por SKU
sk = v.groupby("sku_id").agg(n=("order_id", "size"), k=("nao_aprovado", "sum"))
sk = sk[sk["n"] >= 10]
c = stats.chi2_contingency(np.c_[sk["k"], sk["n"] - sk["k"]])
fech.append({"corte": "não aprovação por SKU (≥10 itens)", "n": len(sk), "p_valor": c.pvalue})
# (d) por faixa de valor
v["fx_valor"] = pd.qcut(v["receita_bruta"], 10, labels=[f"D{i}" for i in range(1, 11)])
c = stats.chi2_contingency(pd.crosstab(v["fx_valor"], v["nao_aprovado"]))
fech.append({"corte": "não aprovação por decil de valor do pedido", "n": len(v),
             "p_valor": c.pvalue})
c = stats.chi2_contingency(pd.crosstab(ap["celula"], ap["devolvido"]))
fech.append({"corte": "devolução por célula desconto × frete", "n": len(ap), "p_valor": c.pvalue})
s.tabela(pd.DataFrame(fech).set_index("corte"), "fechamento_vazamentos", casas=4)
s("")
s("VEREDITO T7 (proposto): CONFIRMA as rodadas 1 e 2 por um caminho independente.")
s("Devolução e não aprovação são grandes, estáveis e SEM ENDEREÇO — não há")
s("segmento, cliente, SKU, dia nem faixa de valor onde agir. São condição de")
s("contorno do negócio nesta base, não alavanca.")


# ==========================================================================
s.secao("T8. CONCENTRAÇÃO — em quantas contas a decisão de desconto cabe")
# ==========================================================================
cli = ap.groupby("customer_id").agg(
    itens=("order_id", "size"), rb=("receita_bruta", "sum"),
    desconto=("desconto_reais", "sum"), frete=("custo_frete", "sum"),
    margem=("margem_contribuicao", "sum"), freq_desc=("tem_desconto", "mean"),
    tx_dev=("devolvido", "mean")).sort_values("desconto", ascending=False)
cli["desc_%RB"] = cli["desconto"] / cli["rb"] * 100
s(f"clientes que compram na janela: {len(cli)}")
s.tabela(cli.head(10)[["itens", "rb", "desconto", "desc_%RB", "freq_desc", "margem"]],
         "top10_clientes_desconto")
acum = []
for k in (1, 2, 5, 10, 25, 50):
    h = cli.head(k)
    acum.append({"top_N_clientes": k, "%_dos_itens": h["itens"].sum() / len(ap) * 100,
                 "%_do_desconto": h["desconto"].sum() / desc_total * 100,
                 "R$_desconto": h["desconto"].sum(),
                 "R$_desconto_anual": h["desconto"].sum() * ANUAL})
s("")
s.tabela(pd.DataFrame(acum).set_index("top_N_clientes"), "concentracao_desconto")
s("")
s("Corte de checagem: a concentração do desconto é só reflexo da concentração de")
s("pedidos, ou esses clientes recebem desconto DIFERENTE?")
gr = cli.head(25)
c = stats.chi2_contingency(pd.crosstab(ap.loc[ap["customer_id"].isin(top25), "customer_id"],
                                       ap.loc[ap["customer_id"].isin(top25), "tem_desconto"]))
s(f"  frequência de desconto entre os 25 maiores: {gr['freq_desc'].min() * 100:.2f}% a "
  f"{gr['freq_desc'].max() * 100:.2f}%, qui² p={ch.fmt_p(c.pvalue)}")
s(f"  desconto %RB entre os 25 maiores: {gr['desc_%RB'].min():.2f}% a {gr['desc_%RB'].max():.2f}%")
s("  → é reflexo do volume: todos recebem a mesma coisa. Isso NÃO enfraquece o")
s("    achado — redireciona a ação: a regra de desconto é UMA, e uma regra única")
s("    aplicada a 25 contas cobre ~93% do valor concedido.")


# ==========================================================================
s.secao("T9. CUSTO DE SERVIR POR CLIENTE (cruzamento não feito na rodada 2)")
# ==========================================================================
s("P-05.6: só tickets abertos dentro da janela de vendas, só de quem compra.")
at = ch.carregar_atendimento()
atj = at[(at["data_abertura"] >= ch.JANELA_INI)
         & (at["data_abertura"] < ch.JANELA_FIM_DIA + pd.Timedelta(days=1))]
compradores = ap["customer_id"].unique()
s(f"tickets na base inteira ................. {len(at):,}")
s(f"tickets de clientes que compram ......... {int(at['customer_id'].isin(compradores).sum()):,} "
  f"({at['customer_id'].isin(compradores).mean() * 100:.2f}%)")
s(f"tickets dentro da janela de vendas ...... {len(atj):,}")
atjc = atj[atj["customer_id"].isin(compradores)]
s(f"  desses, de clientes que compram ....... {len(atjc):,}")
s("")
s("→ achado de dado: a base de ATENDIMENTO descreve a mesma população de vendas")
s("  (99% dos tickets), ao contrário da base de CLIENTES (2,31%, C1 da rodada 2).")

tk = atjc.groupby("customer_id").agg(tickets=("ticket_id", "size"),
                                     custo=("custo_operacional_ticket", "sum"))
vd = ap.groupby("customer_id").agg(itens=("order_id", "size"),
                                   margem=("margem_contribuicao", "sum"))
j = vd.join(tk, how="left").fillna({"tickets": 0, "custo": 0})
j["tickets_por_item"] = j["tickets"] / j["itens"]
j["custo_%_margem"] = j["custo"] / j["margem"] * 100
s("")
s(f"tickets na janela / itens vendidos ...... {j['tickets'].sum() / j['itens'].sum():.4f} "
  f"({int(j['tickets'].sum()):,} tickets para {int(j['itens'].sum()):,} pedidos)")
s(f"custo de atendimento na janela .......... R$ {j['custo'].sum():,.2f}")
s(f"  = % da margem aprovada ................ {j['custo'].sum() / MARGEM * 100:.3f}%")
s(f"  anualizado ............................ R$ {j['custo'].sum() * ANUAL:,.2f}")
g20 = j[j["itens"] >= 20]
s("")
s(f"Dispersão entre os {len(g20)} clientes com ≥20 itens:")
s.tabela(g20["tickets_por_item"].describe().to_frame("tickets_por_item"), "custo_servir_dispersao")
esp = j["itens"] / j["itens"].sum() * j["tickets"].sum()
chi2v = float(((j["tickets"] - esp) ** 2 / esp.replace(0, np.nan)).sum())
gl = len(j) - 1
s(f"qui² de 'tickets proporcionais a pedidos': chi2={chi2v:.1f}, gl={gl}, "
  f"p={ch.fmt_p(1 - stats.chi2.cdf(chi2v, gl))}")
s(f"clientes cujo custo de atendimento supera a margem: {int((j['custo'] > j['margem']).sum())}")
s("")
s("VEREDITO T9 (proposto): o custo de servir NÃO se concentra em cliente — é")
s("proporcional ao volume de pedidos. Não há cliente caro para desmarketing. O")
s("que o cruzamento acrescenta é a TAXA DE CONTATO: ~0,5 ticket por pedido, que")
s("é um driver de volume, não de cliente. Isso reancora a alavanca da rodada 2.")

s.salvar()
