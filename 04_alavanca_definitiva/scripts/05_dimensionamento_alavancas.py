"""
05_dimensionamento_alavancas.py — Rodada 3 (final), etapa 3: DIMENSIONAMENTO.

Dimensiona as 3 alavancas que sobreviveram a `05_cadeias_e_intersecoes.py`, sob
MAIS DE UMA RÉGUA, e mostra a régua de 1% da margem como PARÂMETRO VISÍVEL — não
como filtro automático (foi ela que travou a rodada 2).

Cada número sai com dois rótulos:
  TAMANHO DO POOL  — quanto vale o fenômeno inteiro;
  CAPTURA          — quanto se recupera, e com que premissa.

GRAU DE CONFIANÇA (escala declarada aqui, usada em todas as linhas):
  A  dado direto      — soma de uma coluna da base, sem premissa nenhuma.
  B  regra derivada   — vem de uma regra descoberta e testada nos próprios dados
                        (ex.: o limiar de frete de R$ 250, que acerta 100% das
                        linhas) ou de uma premissa já declarada na rodada 1 (P1/P2).
  C  suposição        — parâmetro que NÃO existe em nenhuma das 5 bases
                        (taxa de captura, contenção de bot, redução de contato).

RÉGUAS DE COMPARAÇÃO (todas reportadas, nenhuma usada como filtro)
  R1  % da margem de contribuição ANUAL (R$ 8.456.077) — a régua da rodada 2.
  R2  % da margem do SEGMENTO ENDEREÇÁVEL — o denominador certo para julgar se a
      ação é grande DENTRO do que ela toca.
  R3  R$ absolutos por ano.
  R4  % do custo do próprio processo, quando a alavanca é custo de processo.

PREMISSAS DE CAPTURA (todas grau C, todas a validar com o Davi)
  P-05.7 (desconto, cenário por TETO): a captura é calculada como política
      implementável — "nenhum desconto acima de X% sem alçada" —, e o valor
      recuperado é Σ max(0, desconto% − X) × receita bruta do item. NÃO supõe
      elasticidade zero: supõe que o desconto ATÉ o teto continua sendo dado.
  P-05.8 (desconto, cenário por CAPTURA GENÉRICA): 10% / 25% / 40% do pool.
      O teto de 100% é reportado só como limite aritmético e marcado como
      indefensável (ver P-05.4: venda perdida não é observável).
  P-05.9 (frete): o frete acionado pelo desconto é 100% evitável por regra de
      sistema (bloquear o desconto que cruza o limiar, ou absorver o limiar no
      cálculo do desconto). Os demais componentes usam captura declarada.
  P-05.10 (atendimento): mantém as premissas da rodada 2 — contenção de bot de
      30/50/70% e custo de R$ 2 para o ticket contido — e acrescenta redução da
      TAXA DE CONTATO de 10/20/30%, aplicada ANTES da migração de canal para não
      contar o mesmo ticket duas vezes.

Saídas: outputs/05_alavanca_definitiva/dimensionamento.txt e dimensionamento__*.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import comum_hipoteses as ch

LIMIAR_FRETE = 250.0
s = ch.Saida("dimensionamento", out_dir=ch.OUT_DIR_05)

v = ch.carregar_vendas()
ap = v[v["pagamento_aprovado"]].copy()
ap["d_pct"] = ap["desconto_reais"] / ap["receita_bruta"] * 100
ap["tem_desconto"] = ap["desconto_reais"] > 0
ap["tem_frete"] = ap["custo_frete"] > 0

DIAS = (ch.JANELA_FIM_DIA - ch.JANELA_INI).days + 1
ANUAL = 365 / DIAS
RB = ap["receita_bruta"].sum()
MARGEM = ap["margem_contribuicao"].sum()
MARGEM_ANUAL = MARGEM * ANUAL
REGUA_1PCT = MARGEM_ANUAL * 0.01

s.secao("0. RÉGUAS E CONVENÇÕES")
s(f"janela ............................... {DIAS} dias → fator anual {ANUAL:.4f}")
s(f"receita bruta aprovada na janela ..... R$ {RB:,.2f}")
s(f"margem de contribuição na janela ..... R$ {MARGEM:,.2f}")
s(f"R1 · margem de contribuição ANUAL .... R$ {MARGEM_ANUAL:,.2f}")
s(f"     régua de 1% dela (parâmetro) .... R$ {REGUA_1PCT:,.2f}")
s("")
s("A régua de 1% é MOSTRADA, não aplicada como corte. Na rodada 2 ela refutou a")
s("única oportunidade encontrada; aqui cada alavanca é reportada sob R1, R2, R3")
s("e — quando cabe — R4, e a decisão de materialidade fica com o Davi.")


def reporte(nome: str, pool_janela: float, margem_segmento: float,
            capturas: dict[str, float], grau_pool: str, grau_captura: str,
            custo_processo: float | None = None) -> pd.DataFrame:
    """Uma alavanca sob todas as réguas. `capturas` = {rótulo: fração do pool}."""
    pool_ano = pool_janela * ANUAL
    linhas = []
    for rot, frac in capturas.items():
        val = pool_ano * frac
        linha = {
            "cenário": rot,
            "R3_R$_por_ano": val,
            "R1_%_margem_anual": val / MARGEM_ANUAL * 100,
            "R2_%_margem_do_segmento": val / (margem_segmento * ANUAL) * 100
            if margem_segmento else np.nan,
            "passa_na_régua_de_1%": "sim" if val >= REGUA_1PCT else "não",
        }
        if custo_processo:
            linha["R4_%_custo_do_processo"] = val / (custo_processo * ANUAL) * 100
        linhas.append(linha)
    t = pd.DataFrame(linhas).set_index("cenário")
    s("")
    s(f"POOL (grau {grau_pool}): R$ {pool_janela:,.2f} na janela = "
      f"R$ {pool_ano:,.2f}/ano = {pool_ano / MARGEM_ANUAL * 100:.2f}% da margem anual")
    if margem_segmento:
        s(f"SEGMENTO ENDEREÇÁVEL: margem de R$ {margem_segmento * ANUAL:,.2f}/ano "
          f"({margem_segmento / MARGEM * 100:.2f}% da margem)")
    s(f"CAPTURA: grau {grau_captura}")
    s.tabela(t, f"alavanca_{nome}")
    return t


# ==========================================================================
s.secao("ALAVANCA 1 — DESCONTO CONCEDIDO SEM REGRA")
# ==========================================================================
com_d = ap[ap["tem_desconto"]]
pool_desc = ap["desconto_reais"].sum()
margem_seg_desc = com_d["margem_contribuicao"].sum()
s(f"itens que recebem desconto ........... {len(com_d):,} ({len(com_d) / len(ap) * 100:.2f}%)")
s(f"margem desses itens .................. R$ {margem_seg_desc:,.2f} "
  f"({margem_seg_desc / MARGEM * 100:.2f}% da margem total)")
s("")
s("(a) CENÁRIO POR POLÍTICA — teto de desconto com alçada acima dele (P-05.7).")
s("    Recupera Σ max(0, desconto% − teto) × receita bruta. Não supõe que o")
s("    desconto some: supõe que ele para no teto.")
tetos = []
for teto in (35, 30, 25, 20, 15, 10, 5, 0):
    excedente = np.maximum(0.0, com_d["d_pct"] - teto) / 100 * com_d["receita_bruta"]
    n_afetados = int((com_d["d_pct"] > teto).sum())
    tetos.append({
        "teto_de_desconto_%": teto,
        "itens_afetados": n_afetados,
        "%_dos_itens_com_desconto": n_afetados / len(com_d) * 100,
        "recuperado_janela_R$": excedente.sum(),
        "recuperado_ano_R$": excedente.sum() * ANUAL,
        "R1_%_margem_anual": excedente.sum() * ANUAL / MARGEM_ANUAL * 100,
        "%_do_pool_de_desconto": excedente.sum() / pool_desc * 100,
    })
tt = pd.DataFrame(tetos).set_index("teto_de_desconto_%")
s.tabela(tt, "desconto_cenarios_teto")
s("")
s("    Leitura: um teto de 20% — que ainda é um desconto alto para varejo —")
s(f"    recupera R$ {tt.loc[20, 'recuperado_ano_R$']:,.2f}/ano, "
  f"{tt.loc[20, 'R1_%_margem_anual']:.2f}% da margem anual, mexendo em "
  f"{tt.loc[20, 'itens_afetados']:,} itens.")

s("")
s("(b) CENÁRIO POR CAPTURA GENÉRICA (P-05.8):")
reporte("desconto", pool_desc, margem_seg_desc,
        {"conservador (10% do pool)": 0.10,
         "central (25% do pool)": 0.25,
         "agressivo (40% do pool)": 0.40,
         "limite aritmético (100%) — INDEFENSÁVEL, ver P-05.4": 1.00},
        grau_pool="A", grau_captura="C")

s("")
s("(c) INTENSIFICADOR — NÃO somar ao total. Quanto do desconto vai para pedido")
s("    que nunca vira caixa:")
d_nao_ap = v.loc[~v["pagamento_aprovado"], "desconto_reais"].sum()
d_dev = ap.loc[ap["devolvido"], "desconto_reais"].sum()
d_caixa = ap.loc[~ap["devolvido"], "desconto_reais"].sum()
intens = pd.DataFrame({
    "R$_janela": [d_nao_ap, d_dev, d_caixa],
    "%_do_desconto_total": [x / (d_nao_ap + d_dev + d_caixa) * 100
                            for x in (d_nao_ap, d_dev, d_caixa)],
}, index=["em pedidos NÃO APROVADOS", "em pedidos APROVADOS e DEVOLVIDOS",
          "em pedidos que viraram caixa"])
s.tabela(intens, "desconto_intensificador")
s(f"    → {(d_nao_ap + d_dev) / (d_nao_ap + d_dev + d_caixa) * 100:.2f}% do desconto é")
s("      concedido a pedidos que não se realizam. Isso NÃO é caixa recuperável")
s("      (o pedido cancelado também não gera a receita), é medida do quanto a")
s("      decisão é tomada às cegas. Por isso não entra em nenhum total.")


# ==========================================================================
s.secao("ALAVANCA 2 — FRETE: A REGRA DOS R$ 250 E A EXCEÇÃO DO MARKETPLACE")
# ==========================================================================
nm = ap[ap["canal"] != "Marketplace"]
mk = ap[ap["canal"] == "Marketplace"]
emp = nm[(nm["receita_bruta"] >= LIMIAR_FRETE) & (nm["receita_liquida"] < LIMIAR_FRETE)]
nat = nm[nm["receita_bruta"] < LIMIAR_FRETE]
nat_quase = nat[nat["receita_liquida"] >= 200]
nat_fundo = nat[nat["receita_liquida"] < 200]
mk_acima = mk[mk["receita_liquida"] >= LIMIAR_FRETE]
mk_abaixo = mk[mk["receita_liquida"] < LIMIAR_FRETE]

comp = pd.DataFrame({
    "itens": [len(emp), len(nat_quase), len(nat_fundo), len(mk_acima), len(mk_abaixo)],
    "frete_janela_R$": [emp["custo_frete"].sum(), nat_quase["custo_frete"].sum(),
                        nat_fundo["custo_frete"].sum(), mk_acima["custo_frete"].sum(),
                        mk_abaixo["custo_frete"].sum()],
}, index=[
    "A · empurrados abaixo do limiar PELO DESCONTO (RB≥250, RL<250)",
    "B · abaixo por natureza, a menos de R$ 50 da linha (200≤RL<250)",
    "C · abaixo por natureza, longe da linha (RL<200)",
    "D · MARKETPLACE acima do limiar (pagaria R$ 0 em qualquer outro canal)",
    "E · MARKETPLACE abaixo do limiar (pagaria de qualquer forma)",
])
comp["frete_ano_R$"] = comp["frete_janela_R$"] * ANUAL
comp["%_do_frete_total"] = comp["frete_janela_R$"] / ap["custo_frete"].sum() * 100
comp["R1_%_margem_anual"] = comp["frete_ano_R$"] / MARGEM_ANUAL * 100
s(f"frete total pago na janela ........... R$ {ap['custo_frete'].sum():,.2f} "
  f"(R$ {ap['custo_frete'].sum() * ANUAL:,.2f}/ano = "
  f"{ap['custo_frete'].sum() * ANUAL / MARGEM_ANUAL * 100:.2f}% da margem anual)")
s.tabela(comp, "frete_componentes")

s("")
s("Endereçabilidade de cada componente (a régua aqui é MECANISMO, não tamanho):")
end = pd.DataFrame({
    "mecanismo": [
        "regra de sistema: o desconto não pode cruzar o limiar (ou o limiar passa a ser calculado sobre a RB)",
        "nudge de carrinho: faltam R$ 25,23 em média para o frete grátis",
        "revisão do limiar / do mínimo de pedido — decisão comercial, não regra de sistema",
        "política de frete do canal: renegociar quem paga o frete no Marketplace",
        "nenhum — pagaria frete sob qualquer regra",
    ],
    "captura_premissa": ["100% (grau B: a regra é determinística)",
                         "30% dos itens sobem a linha (grau C)",
                         "0% (não dimensionado)",
                         "50% (grau C)",
                         "0%"],
    "captura_frac": [1.00, 0.30, 0.00, 0.50, 0.00],
}, index=comp.index)
end["recuperado_ano_R$"] = comp["frete_ano_R$"] * end["captura_frac"]
end["R1_%_margem_anual"] = end["recuperado_ano_R$"] / MARGEM_ANUAL * 100
s.tabela(end[["captura_premissa", "recuperado_ano_R$", "R1_%_margem_anual"]],
         "frete_enderecabilidade")
s("")
s("    O componente B tem um ganho a mais que não é corte de custo: subir o item")
s("    acima da linha ACRESCENTA receita.")
falta = (LIMIAR_FRETE - nat_quase["receita_liquida"])
s(f"    {len(nat_quase):,} itens, faltando R$ {falta.mean():.2f} em média "
  f"(R$ {falta.sum():,.2f} no total).")
s(f"    A 30% de conversão e 50,0% de margem: "
  f"+R$ {falta.sum() * 0.30 * 0.50 * ANUAL:,.2f}/ano de margem incremental (grau C).")

pool_frete_end = float(end["recuperado_ano_R$"].sum())
s("")
s("R2 para esta alavanca = margem dos itens QUE PAGAM FRETE (o segmento que a")
s("ação toca), não a margem total.")
margem_seg_frete = ap.loc[ap["tem_frete"], "margem_contribuicao"].sum()
reporte("frete", ap["custo_frete"].sum(), margem_seg_frete,
        {"só o componente A (regra determinística)":
             float(comp.loc[comp.index[0], "frete_janela_R$"]) / ap["custo_frete"].sum(),
         "A + B (regra + nudge)":
             (comp.loc[comp.index[0], "frete_janela_R$"]
              + 0.30 * comp.loc[comp.index[1], "frete_janela_R$"]) / ap["custo_frete"].sum(),
         "A + B + D (inclui política do Marketplace)":
             (comp.loc[comp.index[0], "frete_janela_R$"]
              + 0.30 * comp.loc[comp.index[1], "frete_janela_R$"]
              + 0.50 * comp.loc[comp.index[3], "frete_janela_R$"]) / ap["custo_frete"].sum()},
        grau_pool="A", grau_captura="B no componente A, C nos demais")


# ==========================================================================
s.secao("ALAVANCA 3 — TAXA DE CONTATO E CANAL DO ATENDIMENTO")
# ==========================================================================
at = ch.carregar_atendimento()
atj = at[(at["data_abertura"] >= ch.JANELA_INI)
         & (at["data_abertura"] < ch.JANELA_FIM_DIA + pd.Timedelta(days=1))]
compradores = ap["customer_id"].unique()
atjc = atj[atj["customer_id"].isin(compradores)]
custo_at = atjc["custo_operacional_ticket"].sum()
taxa_contato = len(atjc) / len(ap)

s(f"tickets na janela, de quem compra .... {len(atjc):,}")
s(f"pedidos aprovados na janela .......... {len(ap):,}")
s(f"TAXA DE CONTATO ...................... {taxa_contato:.4f} ticket por pedido")
s(f"custo de atendimento na janela ....... R$ {custo_at:,.2f}")
s(f"  anualizado ......................... R$ {custo_at * ANUAL:,.2f} "
  f"= {custo_at * ANUAL / MARGEM_ANUAL * 100:.2f}% da margem anual")
s("")
s("Composição por tema e por canal (dentro da janela, base de quem compra):")
tema = atjc.groupby("categoria_problema").agg(
    tickets=("ticket_id", "size"), custo=("custo_operacional_ticket", "sum"))
tema["%_custo"] = tema["custo"] / custo_at * 100
tema["custo_ano"] = tema["custo"] * ANUAL
s.tabela(tema.sort_values("custo", ascending=False), "atendimento_por_tema")

PADRONIZAVEIS = ["Onde está meu pedido?", "Pagamento não aprovado", "Dúvida Técnica"]
humano = atjc[atjc["canal_entrada"] != "ChatBot"]
pad_hum = humano[humano["categoria_problema"].isin(PADRONIZAVEIS)]
alavanca_unit = pad_hum["custo_operacional_ticket"].mean() - 2.0
s("")
s(f"P-A1 (herdada da rodada 2) temas padronizáveis: {PADRONIZAVEIS}")
s(f"tickets padronizáveis em canal humano na janela ... {len(pad_hum):,}")
s(f"alavanca por ticket migrado (custo do canal − R$ 2) ... R$ {alavanca_unit:.2f}")
s("")
s("Cenários combinados (P-05.10): primeiro reduz CONTATO, depois migra o resto.")
grid = []
for red in (0.0, 0.10, 0.20, 0.30):
    # A redução de contato evita o ticket inteiro, no custo médio do canal de origem.
    evitados_R = custo_at * red
    restantes_pad = len(pad_hum) * (1 - red)
    for cont in (0.30, 0.50, 0.70):
        migrado_R = restantes_pad * alavanca_unit * cont
        total = (evitados_R + migrado_R) * ANUAL
        grid.append({
            "redução_de_contato": f"{red:.0%}",
            "contenção_do_bot": f"{cont:.0%}",
            "R3_R$_por_ano": total,
            "R4_%_custo_do_atendimento": total / (custo_at * ANUAL) * 100,
            "R1_%_margem_anual": total / MARGEM_ANUAL * 100,
            "passa_na_régua_de_1%": "sim" if total >= REGUA_1PCT else "não",
        })
gr = pd.DataFrame(grid).set_index(["redução_de_contato", "contenção_do_bot"])
s.tabela(gr, "atendimento_cenarios")
s("")
s("A linha 'redução 0%' reproduz a rodada 2 (R$ 26–61 mil/ano) com a base da")
s("janela de vendas em vez dos 3 anos — serve de validação cruzada entre rodadas.")


# ==========================================================================
s.secao("RANKING FINAL — as 3 alavancas e os 2 pools sem endereço")
# ==========================================================================
teto20 = float(tt.loc[20, "recuperado_ano_R$"])
frete_AB = float(end.loc[end.index[0], "recuperado_ano_R$"]
                 + end.loc[end.index[1], "recuperado_ano_R$"])
frete_ABD = pool_frete_end
at_central = float(gr.loc[("20%", "50%"), "R3_R$_por_ano"])
at_piso = float(gr.loc[("0%", "30%"), "R3_R$_por_ano"])
at_teto = float(gr.loc[("30%", "70%"), "R3_R$_por_ano"])

rank = pd.DataFrame([
    {"#": 1, "alavanca": "Desconto concedido sem regra",
     "pool_ano_R$": pool_desc * ANUAL,
     "captura_piso_R$": float(tt.loc[30, "recuperado_ano_R$"]),
     "captura_central_R$": teto20,
     "captura_teto_R$": float(tt.loc[10, "recuperado_ano_R$"]),
     "grau_pool": "A", "grau_captura": "C"},
    {"#": 2, "alavanca": "Frete: limiar de R$ 250 + exceção do Marketplace",
     "pool_ano_R$": ap["custo_frete"].sum() * ANUAL,
     "captura_piso_R$": float(end.loc[end.index[0], "recuperado_ano_R$"]),
     "captura_central_R$": frete_AB, "captura_teto_R$": frete_ABD,
     "grau_pool": "A", "grau_captura": "B/C"},
    {"#": 3, "alavanca": "Taxa de contato e canal do atendimento",
     "pool_ano_R$": custo_at * ANUAL,
     "captura_piso_R$": at_piso, "captura_central_R$": at_central,
     "captura_teto_R$": at_teto,
     "grau_pool": "A", "grau_captura": "C"},
    {"#": "—", "alavanca": "[sem endereço] Devolução (P2)",
     "pool_ano_R$": 1796098.60 * ANUAL, "captura_piso_R$": np.nan,
     "captura_central_R$": np.nan, "captura_teto_R$": np.nan,
     "grau_pool": "B", "grau_captura": "não dimensionável"},
    {"#": "—", "alavanca": "[sem endereço] Pagamento não aprovado (margem)",
     "pool_ano_R$": v.loc[~v["pagamento_aprovado"], "margem_contribuicao"].sum() * ANUAL,
     "captura_piso_R$": np.nan, "captura_central_R$": np.nan,
     "captura_teto_R$": np.nan, "grau_pool": "A", "grau_captura": "não dimensionável"},
    {"#": "—", "alavanca": "[sem endereço] CMV / markup",
     "pool_ano_R$": ap["custo_produto"].sum() * ANUAL, "captura_piso_R$": np.nan,
     "captura_central_R$": np.nan, "captura_teto_R$": np.nan,
     "grau_pool": "A", "grau_captura": "não dimensionável (H8/B3.0: estoque não reconcilia)"},
]).set_index("#")
for c in ("pool_ano_R$", "captura_piso_R$", "captura_central_R$", "captura_teto_R$"):
    rank[c.replace("R$", "%margem")] = rank[c] / MARGEM_ANUAL * 100
s.tabela(rank, "ranking")
s("")
s(f"Régua de 1% da margem anual = R$ {REGUA_1PCT:,.2f} (mostrada, não aplicada).")
s("Alavancas cujo cenário CENTRAL passa nessa régua: " +
  ", ".join(rank.loc[rank["captura_central_R$"] >= REGUA_1PCT, "alavanca"].tolist()))
s("")
s("Soma dos 3 cenários centrais: R$ "
  f"{teto20 + frete_AB + at_central:,.2f}/ano = "
  f"{(teto20 + frete_AB + at_central) / MARGEM_ANUAL * 100:.2f}% da margem anual.")
s("A soma é legítima: as três alavancas tocam linhas diferentes da ponte de")
s("margem (desconto, frete, custo de processo) e o frete atribuído ao desconto")
s("(componente A) é contado UMA vez só, na alavanca 2.")

s.salvar()
