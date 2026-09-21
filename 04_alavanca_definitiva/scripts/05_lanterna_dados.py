"""
05_lanterna_dados.py — Rodada 3 (final), etapa 1: LANTERNA.

Objetivo desta etapa: deixar os DADOS apontarem onde procurar, antes de qualquer
explicação de negócio. Nada aqui é prova; tudo aqui é direcionamento. As provas
vêm nos scripts 05_b (cadeias/interseções) e 05_c (dimensionamento).

Diferença para as rodadas 1 e 2: não existe árvore de hipóteses guiando o corte.
As perguntas nascem de:
  (1) decomposição de variância da margem nos seus componentes contábeis;
  (2) matriz de correlação das numéricas contra margem e contra o VAZAMENTO;
  (3) feature importance (floresta + árvore rasa) com alvo = margem, vazamento,
      devolução e desfecho do pagamento, com split TEMPORAL (treina no 1º
      semestre, testa no 2º) — a robustez já entra no desenho;
  (4) clustering (KMeans) de itens, para achar segmento que corte manual não acha.

PREMISSAS DECLARADAS NESTE SCRIPT
  - P-05.1 "vazamento": para cada item, a margem POTENCIAL é a coluna
    `margem_contribuicao`; o RESULTADO REALIZADO é:
        * 0, se o pagamento não foi aprovado (Cancelado/Aguardando) — o pedido
          não gera receita nem custo de produto; a perda é margem que não
          aconteceu (custo de oportunidade), não caixa que saiu;
        * o cenário P1/P2 de devolução de `comum_hipoteses`, se devolvido;
        * a própria margem, caso contrário.
    vazamento = margem_potencial − resultado_realizado ≥ 0.
    É a MESMA aritmética de H9 (devolução) e H7 (pagamento) da rodada 1, agora
    somada numa única variável por item para poder ser usada como ALVO.
  - P-05.2: atributos de `estoque` entram apenas como características do SKU
    (subcategoria, fornecedor, lead time, shelf life, volume, status). Custo e
    preço sugerido do estoque NÃO entram (restrição 3 da mentoria de 11/09 e
    achado 2 da rodada 1: as duas bases não conversam SKU a SKU).
  - P-05.3: árvores com categóricas codificadas por código ordinal. Isso permite
    splits arbitrários em categorias sem ordem; é aceitável para RANQUEAR onde
    olhar (lanterna), e por isso nenhum veredito sai daqui.

Saídas: outputs/05_alavanca_definitiva/lanterna.txt e lanterna__*.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor, export_text

import comum_hipoteses as ch

SEMENTE = 42
s = ch.Saida("lanterna", out_dir=ch.OUT_DIR_05)


# --------------------------------------------------------------------------
# 0. Painel item × atributos
# --------------------------------------------------------------------------
def montar_painel() -> pd.DataFrame:
    v = ch.carregar_vendas()
    e = ch.carregar_estoque()

    cols_sku = [
        "sku_id", "subcategoria", "fornecedor_id", "lead_time_reposicao",
        "shelf_life_dias", "volume_m3", "status_disponibilidade",
        "estoque_disponivel", "ponto_pedido",
    ]
    d = v.merge(e[cols_sku], on="sku_id", how="left", validate="many_to_one")

    frete_rev = ch.frete_reverso_premissa(v)
    d["res_P1"] = ch.resultado_realizado(d, "P1", frete_rev)
    d["res_P2"] = ch.resultado_realizado(d, "P2", frete_rev)
    # P-05.1: pagamento não aprovado zera o resultado realizado.
    for cen in ("P1", "P2"):
        d[f"res_{cen}"] = d[f"res_{cen}"].where(d["pagamento_aprovado"], 0.0)
    d["vazamento_P1"] = d["margem_contribuicao"] - d["res_P1"]
    d["vazamento_P2"] = d["margem_contribuicao"] - d["res_P2"]

    rb = d["receita_bruta"]
    d["desc_pct"] = d["desconto_reais"] / rb * 100
    d["cmv_pct"] = d["custo_produto"] / rb * 100
    d["frete_pct"] = d["custo_frete"] / rb * 100
    d["margem_pct"] = d["margem_contribuicao"] / rb * 100
    d["vaz_P2_pct"] = d["vazamento_P2"] / rb * 100
    d["tem_frete"] = d["custo_frete"] > 0
    d["markup"] = d["preco_unitario"] / (d["custo_produto"] / d["quantidade"])
    d["dow"] = d["data_pedido"].dt.dayofweek
    d["hora"] = d["data_pedido"].dt.hour
    d["dia_mes"] = d["data_pedido"].dt.day
    d["abaixo_ponto_pedido"] = d["estoque_disponivel"] < d["ponto_pedido"]
    return d


d = montar_painel()
ap = d[d["pagamento_aprovado"]].copy()

s.secao("0. PAINEL")
s(f"itens totais .............. {len(d):,}")
s(f"itens aprovados ........... {len(ap):,}")
s(f"SKUs sem match em estoque . {int(d['subcategoria'].isna().sum())}")
s(f"janela .................... {d['data_pedido'].min():%Y-%m-%d} a {d['data_pedido'].max():%Y-%m-%d}")
s("")
s(ch.PREMISSAS_DEVOLUCAO)
s("")
s(f"frete reverso da premissa P2 ... R$ {ch.frete_reverso_premissa(d):.2f}")

tot_mc = d["margem_contribuicao"].sum()
s("")
s("Pool de vazamento na janela (P-05.1):")
resumo_pool = pd.DataFrame({
    "R$": [
        tot_mc,
        d.loc[~d["pagamento_aprovado"], "margem_contribuicao"].sum(),
        d.loc[d["pagamento_aprovado"], "vazamento_P1"].sum(),
        d.loc[d["pagamento_aprovado"], "vazamento_P2"].sum(),
        d["vazamento_P1"].sum(),
        d["vazamento_P2"].sum(),
        d["res_P1"].sum(),
        d["res_P2"].sum(),
    ]}, index=[
    "margem potencial (coluna somada, todos os status)",
    "  perda por pagamento não aprovado",
    "  perda por devolução (P1)",
    "  perda por devolução (P2)",
    "vazamento total P1",
    "vazamento total P2",
    "resultado realizado P1",
    "resultado realizado P2",
])
resumo_pool["% da margem potencial"] = resumo_pool["R$"] / tot_mc * 100
s.tabela(resumo_pool, "pool_vazamento")


# --------------------------------------------------------------------------
# 1. Onde mora a dispersão da margem: decomposição de variância
# --------------------------------------------------------------------------
s.secao("1. DECOMPOSIÇÃO DE VARIÂNCIA DA MARGEM % (identidade contábil)")
s("margem% = 100 − desconto% − CMV% − frete%  (tudo sobre receita bruta)")
s("Var(margem%) = ΣVar(componente) + 2Σcov(componentes), com sinal invertido nos componentes.")
s("")

comp = ap[["desc_pct", "cmv_pct", "frete_pct"]]
var_m = ap["margem_pct"].var()
linhas = []
for c in comp.columns:
    # margem = 100 − Σ comp ⇒ contribuição de cada comp = Var(c) + Σ_{c'≠c} cov(c, c')
    contrib = comp[c].var() + sum(comp[c].cov(comp[o]) for o in comp.columns if o != c)
    linhas.append({
        "componente": c,
        "media_%RB": comp[c].mean(),
        "dp_%RB": comp[c].std(),
        "variancia": comp[c].var(),
        "contrib_para_var_margem": contrib,
        "%_da_var_da_margem": contrib / var_m * 100,
    })
dec = pd.DataFrame(linhas).set_index("componente")
s(f"Var(margem%) item a item = {var_m:.2f} (dp = {np.sqrt(var_m):.2f} p.p.)")
s.tabela(dec, "decomposicao_variancia")
s("")
s("Correlação entre componentes (Pearson):")
s.tabela(comp.corr(), "correlacao_componentes", casas=3)


# --------------------------------------------------------------------------
# 2. Matriz de correlação: numéricas × alvos
# --------------------------------------------------------------------------
s.secao("2. CORRELAÇÃO (Spearman) DAS NUMÉRICAS CONTRA OS ALVOS")

numericas = [
    "quantidade", "preco_unitario", "receita_bruta", "receita_liquida",
    "desconto_reais", "custo_produto", "custo_frete", "tempo_entrega_real",
    "markup", "lead_time_reposicao", "shelf_life_dias", "volume_m3",
    "estoque_disponivel", "ponto_pedido", "dow", "hora", "dia_mes",
]
alvos = {
    "margem_pct (aprovados)": (ap, "margem_pct"),
    "vaz_P2_pct (aprovados)": (ap, "vaz_P2_pct"),
    "devolvido (aprovados)": (ap, "devolvido"),
    "nao_aprovado (todos)": (d.assign(nao_aprovado=~d["pagamento_aprovado"]), "nao_aprovado"),
}
mat = {}
for nome, (base, alvo) in alvos.items():
    col = {}
    y = base[alvo].astype(float)
    for n in numericas:
        x = base[n].astype(float)
        ok = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
        r, p = stats.spearmanr(x[ok], y[ok])
        col[n] = r
        col[f"{n}__p"] = p
    mat[nome] = col
corr = pd.DataFrame(mat)
corr_r = corr.loc[[n for n in numericas]]
corr_p = corr.loc[[f"{n}__p" for n in numericas]]
corr_p.index = numericas
s("rho de Spearman:")
s.tabela(corr_r, "correlacao_alvos_rho", casas=3)
s("")
s("p-valor correspondente:")
s.tabela(corr_p.rename(columns=lambda c: c + " p_valor"), "correlacao_alvos_p", casas=4)


# --------------------------------------------------------------------------
# 3. Feature importance com split TEMPORAL
# --------------------------------------------------------------------------
s.secao("3. FEATURE IMPORTANCE (floresta, split temporal treino=1º semestre)")
s("Split: treino = data_pedido < 2023-07-01; teste = o resto. Importância por")
s("PERMUTAÇÃO, medida no TESTE — importância que não generaliza no tempo cai a ~0.")
s("P-05.3: categóricas por código ordinal; isto ranqueia onde olhar, não prova nada.")

CATEG = ["canal", "categoria", "metodo_pagamento", "subcategoria",
         "fornecedor_id", "status_disponibilidade", "produto"]
NUM_FEAT = ["quantidade", "preco_unitario", "receita_bruta", "desconto_reais",
            "custo_produto", "custo_frete", "tempo_entrega_real", "markup",
            "lead_time_reposicao", "shelf_life_dias", "volume_m3",
            "estoque_disponivel", "ponto_pedido", "dow", "hora", "dia_mes"]


def matriz_features(base: pd.DataFrame, usar: list[str]) -> pd.DataFrame:
    X = pd.DataFrame(index=base.index)
    for c in usar:
        if c in CATEG:
            X[c] = base[c].astype("category").cat.codes
        else:
            X[c] = pd.to_numeric(base[c], errors="coerce")
    return X.fillna(-1)


def importancia(base: pd.DataFrame, alvo: str, usar: list[str], classif: bool,
                rotulo: str) -> pd.DataFrame:
    treino = base["data_pedido"] < pd.Timestamp("2023-07-01")
    X = matriz_features(base, usar)
    y = base[alvo].astype(int if classif else float)
    Modelo = RandomForestClassifier if classif else RandomForestRegressor
    m = Modelo(n_estimators=300, min_samples_leaf=25, random_state=SEMENTE, n_jobs=-1)
    m.fit(X[treino], y[treino])
    score = m.score(X[~treino], y[~treino])
    pi = permutation_importance(m, X[~treino], y[~treino], n_repeats=10,
                                random_state=SEMENTE, n_jobs=-1)
    t = pd.DataFrame({"importancia": pi.importances_mean, "dp": pi.importances_std},
                     index=usar).sort_values("importancia", ascending=False)
    s("")
    s(f"--- alvo: {rotulo}  (n treino={int(treino.sum()):,}, n teste={int((~treino).sum()):,})")
    s(f"    score no TESTE ({'acurácia' if classif else 'R²'}) = {score:.4f}")
    s.tabela(t.head(12), f"importancia_{alvo}", casas=5)
    return t


# (a) margem com os componentes dentro: confirma a identidade e diz qual pesa
importancia(ap, "margem_pct", NUM_FEAT + CATEG, False, "margem_pct COM componentes")
# (b) margem sem os componentes: o que de estrutural prevê a margem
sem_comp = [c for c in NUM_FEAT + CATEG if c not in
            ("desconto_reais", "custo_produto", "custo_frete", "markup")]
importancia(ap, "margem_pct", sem_comp, False, "margem_pct SEM componentes")
# (c) vazamento
importancia(ap, "vaz_P2_pct", sem_comp, False, "vaz_P2_pct (aprovados)")
# (d) devolução
importancia(ap, "devolvido", sem_comp, True, "devolvido (aprovados)")
# (e) não aprovado
importancia(d.assign(nao_aprovado=~d["pagamento_aprovado"]), "nao_aprovado",
            sem_comp, True, "nao_aprovado (todos)")

s("")
s("Árvore rasa (profundidade 3) sobre margem_pct, só com estrutura:")
Xt = matriz_features(ap, sem_comp)
arv = DecisionTreeRegressor(max_depth=3, min_samples_leaf=200, random_state=SEMENTE)
arv.fit(Xt, ap["margem_pct"])
s(export_text(arv, feature_names=list(Xt.columns), decimals=2))


# --------------------------------------------------------------------------
# 4. Clustering de itens
# --------------------------------------------------------------------------
s.secao("4. CLUSTERING (KMeans, k=6) DE ITENS APROVADOS")
s("Features padronizadas, só estruturais/comportamentais (sem os componentes da")
s("margem e sem o alvo). Serve para achar segmento que corte manual não acha.")

feat_cl = ["quantidade", "preco_unitario", "receita_bruta", "tempo_entrega_real",
           "lead_time_reposicao", "shelf_life_dias", "volume_m3", "hora"]
Xc = ap[feat_cl].apply(pd.to_numeric, errors="coerce")
ok = Xc.notna().all(axis=1)
Xs = StandardScaler().fit_transform(Xc[ok])
km = KMeans(n_clusters=6, n_init=10, random_state=SEMENTE).fit(Xs)
apc = ap[ok].copy()
apc["cluster"] = km.labels_

perfil = apc.groupby("cluster").agg(
    itens=("order_id", "size"),
    receita_bruta=("receita_bruta", "sum"),
    margem=("margem_contribuicao", "sum"),
    res_P2=("res_P2", "sum"),
    vaz_P2=("vazamento_P2", "sum"),
    tx_devolucao=("devolvido", "mean"),
    tx_frete=("tem_frete", "mean"),
    preco_med=("preco_unitario", "mean"),
    qtd_med=("quantidade", "mean"),
    prazo_med=("tempo_entrega_real", "mean"),
)
perfil["margem_%RB"] = perfil["margem"] / perfil["receita_bruta"] * 100
perfil["realizada_P2_%RB"] = perfil["res_P2"] / perfil["receita_bruta"] * 100
perfil["vaz_%RB"] = perfil["vaz_P2"] / perfil["receita_bruta"] * 100
perfil["tx_devolucao"] *= 100
perfil["tx_frete"] *= 100
s.tabela(perfil.sort_values("realizada_P2_%RB"), "clusters", casas=2)


# --------------------------------------------------------------------------
# 5. Onde o dado grita sozinho: margem realizada por faixa de valor do item
# --------------------------------------------------------------------------
s.secao("5. LEITURA DIRETA QUE A LANTERNA ACENDEU: FAIXA DE VALOR DO ITEM")
s("Motivo de estar aqui: frete é ~R$32 fixo por item com frete, então frete%RB")
s("depende do valor do item por construção. O corte por faixa de receita bruta")
s("nunca foi feito nas rodadas 1 e 2 (que cortaram por canal/categoria/SKU).")

ap["faixa_rb"] = pd.qcut(ap["receita_bruta"], 10,
                         labels=[f"D{i}" for i in range(1, 11)])
fx = ap.groupby("faixa_rb", observed=True).agg(
    itens=("order_id", "size"),
    rb=("receita_bruta", "sum"),
    rb_med=("receita_bruta", "mean"),
    desc=("desconto_reais", "sum"),
    cmv=("custo_produto", "sum"),
    frete=("custo_frete", "sum"),
    margem=("margem_contribuicao", "sum"),
    res_P2=("res_P2", "sum"),
    tx_frete=("tem_frete", "mean"),
    tx_dev=("devolvido", "mean"),
)
for c, nome in (("desc", "desc"), ("cmv", "cmv"), ("frete", "frete"),
                ("margem", "margem"), ("res_P2", "realizada_P2")):
    fx[f"{nome}_%RB"] = fx[c] / fx["rb"] * 100
fx["tx_frete"] *= 100
fx["tx_dev"] *= 100
s.tabela(fx[["itens", "rb_med", "rb", "tx_frete", "tx_dev", "desc_%RB", "cmv_%RB",
             "frete_%RB", "margem_%RB", "realizada_P2_%RB"]], "faixa_valor_item")

s.salvar()
