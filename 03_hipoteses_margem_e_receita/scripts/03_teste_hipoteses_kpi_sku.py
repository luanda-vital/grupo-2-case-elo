"""
03_teste_hipoteses_kpi_sku.py — Fase 2.4, KPI complementar do case: rentabilidade por SKU (liga à H1)

Hipótese: existem SKUs específicos com margem % (sobre a receita líquida)
CONSISTENTEMENTE fora da faixa de 53–56% observada no agregado (H1: categorias
54,14–54,45%; subcategorias 53,04–55,73%).

Premissas (declaradas):
  - Faixa de referência = 53–56% (a do agregado); margem do SKU = Σ margem ÷ Σ RL
    dos itens aprovados.
  - Mínimo de itens para ler a margem de um SKU = 5 (mediana de itens por SKU).
  - "Consistente" = fora da faixa, do mesmo lado, nas duas metades do tempo:
    A = jan–jun/2023 e B = jul/2023–jan/2024, com ≥ 3 itens em cada metade.

Teste:
  1. Distribuição da margem por SKU e % fora da faixa.
  2. Nulo por permutação: embaralhando os itens entre SKUs (tamanhos mantidos),
     quanto da dispersão e da fração fora da faixa aparece só por acaso?
  3. Corte adicional (tempo): a margem do SKU na metade A prevê a da metade B?
     Os SKUs fora da faixa em A continuam fora em B mais do que o acaso?
  4. De onde vem a dispersão (desconto, CMV, frete por SKU; markup dentro do SKU).
  5. Candidatos persistentes e seu peso em R$.

Critério (proposto): CONFIRMA se a dispersão entre SKUs for maior que o acaso
(permutação p < 0,05) E a margem de A prever a de B (correlação positiva, p < 0,05)
E os persistentes excederem o esperado (Fisher p < 0,05). REFUTA se a dispersão
for compatível com o acaso e a correlação entre metades ≈ 0.

Uso: python scripts/03_teste_hipoteses_kpi_sku.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum_hipoteses import ALPHA, Saida, agregados, carregar_vendas  # noqa: E402

NOME = "kpi_sku"
FAIXA = (53.0, 56.0)
MIN_ITENS = 5
MIN_METADE = 3
N_PERM = 2000
FIM_A = pd.Period("2023-06", "M")


def lado(m: pd.Series) -> pd.Series:
    return np.where(m < FAIXA[0], "abaixo", np.where(m > FAIXA[1], "acima", "dentro"))


def main() -> None:
    out = Saida(NOME)
    v = carregar_vendas()
    a = v[v["pagamento_aprovado"]].copy()

    # ------------------------------------------------------------------ 1
    out.secao("1. Distribuição da margem % por SKU")
    s = agregados(a, "sku_id")
    s5 = s[s["itens"] >= MIN_ITENS]
    out(f"SKUs vendidos: {len(s)}; com ≥ {MIN_ITENS} itens: {len(s5)} ({s5['receita_liquida'].sum() / s['receita_liquida'].sum() * 100:.1f}% da RL).")
    out.tabela(pd.DataFrame({f"todos ({len(s)})": s["margem_%RL"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]),
                             f"≥ {MIN_ITENS} itens ({len(s5)})": s5["margem_%RL"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])}),
               "distribuicao_sku")
    lados = pd.Series(lado(s5["margem_%RL"]), index=s5.index).value_counts(normalize=True) * 100
    out(f"SKUs (≥ {MIN_ITENS} itens) abaixo de {FAIXA[0]:.0f}%: {lados.get('abaixo', 0):.1f}%; dentro: {lados.get('dentro', 0):.1f}%; "
        f"acima de {FAIXA[1]:.0f}%: {lados.get('acima', 0):.1f}%.")
    m_item = a["margem_contribuicao"] / a["receita_liquida"] * 100
    out(f"Referência — margem % por ITEM: mediana {m_item.median():.2f}%, desvio-padrão {m_item.std():.2f} p.p.")

    # ------------------------------------------------------------------ 2
    out.secao(f"2. Nulo por permutação ({N_PERM} embaralhamentos dos itens entre SKUs)")
    cod = a.groupby("sku_id").ngroup().to_numpy()
    k = cod.max() + 1
    tam = np.bincount(cod, minlength=k)
    elig = tam >= MIN_ITENS
    mc, rl = a["margem_contribuicao"].to_numpy(), a["receita_liquida"].to_numpy()

    def estat(c: np.ndarray) -> tuple[float, float]:
        mg = np.bincount(c, weights=mc, minlength=k) / np.bincount(c, weights=rl, minlength=k) * 100
        mg = mg[elig]
        return float(mg.std()), float(((mg < FAIXA[0]) | (mg > FAIXA[1])).mean() * 100)

    obs_sd, obs_fora = estat(cod)
    rng = np.random.default_rng(42)
    nula = np.array([estat(rng.permutation(cod)) for _ in range(N_PERM)])
    p_sd = (np.sum(nula[:, 0] >= obs_sd) + 1) / (N_PERM + 1)
    p_fora = (np.sum(nula[:, 1] >= obs_fora) + 1) / (N_PERM + 1)
    tp = pd.DataFrame({"observado": [obs_sd, obs_fora], "media_acaso": nula.mean(axis=0),
                       "p95_acaso": np.percentile(nula, 95, axis=0), "p_valor": [p_sd, p_fora]},
                      index=["desvio-padrão entre SKUs (p.p.)", "% SKUs fora de 53–56%"])
    out.tabela(tp, "permutacao", casas=4)

    # ------------------------------------------------------------------ 3
    out.secao("3. Corte adicional (tempo) — a margem do SKU persiste entre metades?")
    sa = agregados(a[a["mes"] <= FIM_A], "sku_id")
    sb = agregados(a[a["mes"] > FIM_A], "sku_id")
    j = sa[["itens", "margem_%RL"]].join(sb[["itens", "margem_%RL"]], lsuffix="_A", rsuffix="_B", how="inner")
    j = j[(j["itens_A"] >= MIN_METADE) & (j["itens_B"] >= MIN_METADE)]
    rp = stats.pearsonr(j["margem_%RL_A"], j["margem_%RL_B"])
    rs = stats.spearmanr(j["margem_%RL_A"], j["margem_%RL_B"])
    out(f"SKUs com ≥ {MIN_METADE} itens em cada metade: {len(j)}. Correlação margem A × B: Pearson {rp.statistic:.3f} "
        f"(p={rp.pvalue:.4f}), Spearman {rs.statistic:.3f} (p={rs.pvalue:.4f}).")
    j["lado_A"], j["lado_B"] = lado(j["margem_%RL_A"]), lado(j["margem_%RL_B"])
    ct = pd.crosstab(j["lado_A"], j["lado_B"])
    out.tabela(ct, "lado_A_x_lado_B")
    pers = {}
    for ld in ("abaixo", "acima"):
        tab = pd.crosstab(j["lado_A"].eq(ld), j["lado_B"].eq(ld))
        fis = stats.fisher_exact(tab.to_numpy()) if tab.shape == (2, 2) else (np.nan, np.nan)
        obs = int((j["lado_A"].eq(ld) & j["lado_B"].eq(ld)).sum())
        esp = j["lado_A"].eq(ld).mean() * j["lado_B"].eq(ld).mean() * len(j)
        pers[ld] = (obs, esp, fis[1])
        out(f"  Persistentes '{ld}' nas duas metades: {obs} SKUs vs {esp:.1f} esperados se A e B fossem independentes "
            f"(Fisher p={fis[1]:.4f}).")

    # ------------------------------------------------------------------ 4
    out.secao("4. De onde vem a dispersão entre SKUs?")
    for comp in ("desconto_%RB", "cmv_%RB", "frete_%RB"):
        r = stats.spearmanr(s5[comp], s5["margem_%RL"])
        out(f"  Spearman(margem_%RL, {comp}) entre SKUs (≥ {MIN_ITENS} itens): {r.statistic:.3f}")
    a["markup"] = a["preco_unitario"] / (a["custo_produto"] / a["quantidade"])
    cv = a.groupby("sku_id")["markup"].agg(lambda x: x.std() / x.mean() if len(x) >= MIN_ITENS else np.nan).dropna()
    out(f"  Markup (preço ÷ custo unitário) dentro do mesmo SKU: CV mediano {cv.median() * 100:.1f}% "
        f"(markup de item vai de {a['markup'].min():.2f}× a {a['markup'].max():.2f}×, ver H8).")
    for comp in ("cmv_%RB", "desconto_%RB", "frete_%RB"):
        jj = sa[["itens", comp]].join(sb[["itens", comp]], lsuffix="_A", rsuffix="_B", how="inner")
        jj = jj[(jj["itens_A"] >= MIN_METADE) & (jj["itens_B"] >= MIN_METADE)]
        r = stats.pearsonr(jj[f"{comp}_A"], jj[f"{comp}_B"])
        out(f"  Persistência A × B de {comp} por SKU: Pearson {r.statistic:.3f} (p={r.pvalue:.4f}, n={len(jj)})")

    # ------------------------------------------------------------------ 5
    out.secao("5. Candidatos persistentes abaixo da faixa")
    cand = j[j["lado_A"].eq("abaixo") & j["lado_B"].eq("abaixo")].join(s[["receita_liquida", "margem", "margem_%RL"]])
    cand["gap_ate_53_R$"] = (FAIXA[0] - cand["margem_%RL"]).clip(lower=0) / 100 * cand["receita_liquida"]
    out.tabela(cand.sort_values("receita_liquida", ascending=False).head(10)[
        ["itens_A", "itens_B", "margem_%RL_A", "margem_%RL_B", "margem_%RL", "receita_liquida", "gap_ate_53_R$"]],
        "candidatos_abaixo")
    out(f"Persistentes abaixo: {len(cand)} SKUs, {cand['receita_liquida'].sum() / a['receita_liquida'].sum() * 100:.2f}% da RL aprovada; "
        f"margem que faltaria para chegarem a 53%: R$ {cand['gap_ate_53_R$'].sum():,.2f} (ordem de grandeza, não oportunidade).")

    # ------------------------------------------------------------------ 6
    out.secao("6. Veredito proposto")
    disp_real = p_sd < ALPHA
    persiste = rp.statistic > 0 and rp.pvalue < ALPHA
    exced = any(o > e and p < ALPHA for o, e, p in pers.values())
    out(f"  Dispersão entre SKUs maior que o acaso: {'SIM' if disp_real else 'NÃO'} (sd {obs_sd:.2f} vs {nula[:, 0].mean():.2f} "
        f"p.p. ao acaso, p={p_sd:.4f}); fora da faixa {obs_fora:.1f}% vs {nula[:, 1].mean():.1f}% ao acaso (p={p_fora:.4f}).")
    out(f"  Margem da metade A prevê a da B: {'SIM' if persiste else 'NÃO'} (r={rp.statistic:.3f}, p={rp.pvalue:.4f}).")
    out(f"  Persistentes acima do esperado: {'SIM' if exced else 'NÃO'}.")
    if disp_real and persiste and exced:
        ver = "CONFIRMADA — há SKUs com margem consistentemente fora da faixa"
    elif not disp_real and not persiste:
        ver = "REFUTADA — a dispersão por SKU é compatível com o acaso e não persiste no tempo"
    else:
        ver = "INCONCLUSIVA — sinais mistos"
    out(f"\nVEREDITO PROPOSTO KPI SKU: {ver}.")
    out.salvar()


if __name__ == "__main__":
    main()
