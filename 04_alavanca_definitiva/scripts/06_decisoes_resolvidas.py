"""Fase 2.4-final · Decisões resolvidas — robustez da alavanca 1.

Resolve as pendências que mexem em número. A decisão de ESCOPO DE ENTREGA
(qual módulo de IA, o que vai para a apresentação) ficou explicitamente para
depois — este script não toca nela.

O que ele responde:

  1. Reprodução da curva de teto de desconto (checagem de rastreabilidade: tem
     de bater com dimensionamento__desconto_cenarios_teto.csv da rodada 3).

  2. SENSIBILIDADE do teto: 25% / 20% / 15%. A decisão registrada é apresentar
     a curva, não um ponto — o teto é política (captura grau C), não medição.

  3. ROBUSTEZ aos 2 IDs concentradores (achado 8 da rodada 1: 2 customer_id =
     61% dos itens). Pergunta: se a diretoria descartar esses 2 IDs como
     artefato de dado, a alavanca 1 sobrevive?
     Os IDs NÃO são removidos da análise — o desconto que eles recebem é
     dinheiro real sobre receita real. O corte aqui é um PISO de robustez.
     Dois denominadores, porque tirar do numerador sem tirar do denominador
     seria trapaça:
       (a) R1  — margem anual cheia (só o numerador encolhe);
       (b) R1b — margem anual do negócio que sobra (numerador e denominador).

  4. Concentração medida sobre a CAPTURA, não sobre o pool. A rodada 3 mediu
     "25 contas = 92,86% do desconto concedido"; para a ação o que importa é
     quanto da captura de um teto vem de quantas contas.

Saídas: outputs/05_alavanca_definitiva/decisoes.txt e decisoes__*.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import comum_hipoteses as ch

TETOS_APRESENTADOS = (25, 20, 15)
COL_R1B = "R1b_%_margem_do_que_sobra"
s = ch.Saida("decisoes", out_dir=ch.OUT_DIR_05)

v = ch.carregar_vendas()
ap = v[v["pagamento_aprovado"]].copy()
ap["d_pct"] = ap["desconto_reais"] / ap["receita_bruta"] * 100

DIAS = (ch.JANELA_FIM_DIA - ch.JANELA_INI).days + 1
ANUAL = 365 / DIAS
MARGEM_ANUAL = ap["margem_contribuicao"].sum() * ANUAL

com_d = ap[ap["desconto_reais"] > 0].copy()


def recuperado(df: pd.DataFrame, teto: float) -> float:
    """P-05.7: recupera a soma de max(0, desconto% - teto) x receita bruta, anualizada."""
    excedente = np.maximum(0.0, df["d_pct"] - teto) / 100 * df["receita_bruta"]
    return float(excedente.sum() * ANUAL)


s.secao("0. CONVENÇÕES (idênticas à rodada 3)")
s(f"janela ............................... {DIAS} dias -> fator anual {ANUAL:.4f}")
s(f"margem de contribuição ANUAL (R1) .... R$ {MARGEM_ANUAL:,.2f}")
s(f"itens aprovados ...................... {len(ap):,}")
s(f"itens com desconto ................... {len(com_d):,}")
s("")
s("Premissas herdadas: P-05.5 (tem desconto = desconto_reais > 0), P-05.7")
s("(cenário de teto) e P-05.4 (a ressalva-mãe: todo teste é condicional ao")
s("pedido existir). Nenhuma premissa nova é criada aqui.")

# ------------------------------------------------------------------ 1 e 2
s.secao("1-2. CURVA DE TETO — reprodução e sensibilidade")
s("Decisão registrada: apresentar a CURVA (25/20/15%), não o ponto de 20%.")
s("Motivo: o teto é escolha de política (captura grau C). A mediana do desconto")
s(f"entre os itens com desconto é {com_d['d_pct'].median():.2f}% — um teto de 20%")
s("corta abaixo da mediana, e isso precisa estar visível em vez de escondido.")
s("")

curva = pd.DataFrame(
    [
        {
            "teto_%": t,
            "itens_afetados": int((com_d["d_pct"] > t).sum()),
            "%_dos_itens_com_desconto": (com_d["d_pct"] > t).mean() * 100,
            "recuperado_ano_R$": recuperado(com_d, t),
            "R1_%_margem_anual": recuperado(com_d, t) / MARGEM_ANUAL * 100,
        }
        for t in TETOS_APRESENTADOS
    ]
).set_index("teto_%")
s.tabela(curva, "curva_teto_apresentada")
s("")
s("Checagem de rastreabilidade contra a rodada 3 (dimensionamento__desconto_")
s("cenarios_teto.csv): teto de 20% = R$ 345.243,80/ano e 4,08% da margem.")
s(f"Aqui: R$ {curva.loc[20, 'recuperado_ano_R$']:,.2f}/ano e "
  f"{curva.loc[20, 'R1_%_margem_anual']:.2f}%.")
bate = abs(float(curva.loc[20, "recuperado_ano_R$"]) - 345243.79529411765) < 0.01
s(f"REPRODUZ: {'sim' if bate else 'NAO — investigar antes de usar qualquer número abaixo'}")

# -------------------------------------------------------------------- 3
s.secao("3. ROBUSTEZ AOS 2 IDs CONCENTRADORES")

por_cliente = (
    ap.groupby("customer_id")
    .agg(itens=("order_id", "size"), desconto=("desconto_reais", "sum"))
    .sort_values("itens", ascending=False)
)
top2 = list(por_cliente.head(2).index)
s("Os 2 maiores IDs por volume de itens (derivados, não hard-coded):")
for cid in top2:
    li = por_cliente.loc[cid]
    s(f"  {cid} ....... {int(li['itens']):>6,} itens "
      f"({li['itens'] / len(ap) * 100:5.2f}% dos aprovados) · "
      f"R$ {li['desconto']:,.2f} de desconto")
s(f"  soma dos 2 ..... {por_cliente.head(2)['itens'].sum() / len(ap) * 100:.2f}% dos itens e "
  f"{por_cliente.head(2)['desconto'].sum() / ap['desconto_reais'].sum() * 100:.2f}% do desconto")
s("")
s("Um ID com 40% dos pedidos de um varejo de moda/beleza não é uma pessoa. O")
s("que ele é não é observável nesta base (não há campo de tipo de conta): as")
s("leituras plausíveis são checkout de convidado, conta-agregadora de")
s("marketplace ou erro de integração. Por isso o corte abaixo é um PISO, e a")
s("narrativa recomendada fala de REGRA ÚNICA, não de 25 contas.")
s("")

sem2 = ap[~ap["customer_id"].isin(top2)]
sem2_com_d = sem2[sem2["desconto_reais"] > 0]
MARGEM_ANUAL_SEM2 = sem2["margem_contribuicao"].sum() * ANUAL
s(f"negócio que sobra: {len(sem2):,} itens · margem anual R$ {MARGEM_ANUAL_SEM2:,.2f} "
  f"({MARGEM_ANUAL_SEM2 / MARGEM_ANUAL * 100:.2f}% da cheia)")
s("")

rob = pd.DataFrame(
    [
        {
            "teto_%": t,
            "com_os_2_IDs_R$": recuperado(com_d, t),
            "R1_%": recuperado(com_d, t) / MARGEM_ANUAL * 100,
            "SEM_os_2_IDs_R$": recuperado(sem2_com_d, t),
            "R1_%_margem_cheia": recuperado(sem2_com_d, t) / MARGEM_ANUAL * 100,
            COL_R1B: recuperado(sem2_com_d, t) / MARGEM_ANUAL_SEM2 * 100,
        }
        for t in TETOS_APRESENTADOS
    ]
).set_index("teto_%")
s.tabela(rob, "robustez_2_ids")
s("")
p20 = rob.loc[20]
queda = (1 - p20["SEM_os_2_IDs_R$"] / p20["com_os_2_IDs_R$"]) * 100
s(f"LEITURA (teto de 20%): descartando os 2 IDs, a captura cai de "
  f"R$ {p20['com_os_2_IDs_R$']:,.0f} para R$ {p20['SEM_os_2_IDs_R$']:,.0f}/ano "
  f"(-{queda:.1f}%),")
s(f"e vale {p20['R1_%_margem_cheia']:.2f}% da margem cheia / {p20[COL_R1B]:.2f}% da "
  f"margem do negócio que sobra.")
passa = p20["R1_%_margem_cheia"] >= 1.0 and p20[COL_R1B] >= 1.0
s(f"Régua de 1% nos dois denominadores: {'PASSA' if passa else 'NÃO passa nos dois'}.")

# -------------------------------------------------------------------- 4
s.secao("4. CONCENTRAÇÃO MEDIDA SOBRE A CAPTURA (não sobre o pool)")
s("A rodada 3 mediu a concentração do desconto CONCEDIDO. Para a ação o que")
s("importa é de quantas contas sai a captura de um teto.")
s("")

com_d["exced_20"] = np.maximum(0.0, com_d["d_pct"] - 20) / 100 * com_d["receita_bruta"]
cap_cli = com_d.groupby("customer_id")["exced_20"].sum().sort_values(ascending=False)
cap_tot = float(cap_cli.sum())
conc = pd.DataFrame(
    [
        {
            "top_N_contas": n,
            "%_da_captura": cap_cli.head(n).sum() / cap_tot * 100,
            "captura_ano_R$": cap_cli.head(n).sum() * ANUAL,
        }
        for n in (1, 2, 5, 10, 25, 50)
    ]
).set_index("top_N_contas")
s.tabela(conc, "concentracao_da_captura")
s("")
s(f"contas com algum desconto acima de 20%: {int((cap_cli > 0).sum()):,}")
s(f"top 2 = {conc.loc[2, '%_da_captura']:.2f}% da captura · "
  f"top 25 = {conc.loc[25, '%_da_captura']:.2f}%")
s("")
s("CONCLUSÃO DE NARRATIVA: a concentração da captura repete a do pool, e os 2")
s("IDs concentradores respondem pela maior parte dela. Dizer 'intervenção de")
s("governança em 25 contas' é verdadeiro na aritmética e frágil na sala — o")
s("eixo defensável é a UNICIDADE DA REGRA (uma regra cobre mais de 90% do")
s("valor), que vale com ou sem os 2 IDs.")

s.salvar()
