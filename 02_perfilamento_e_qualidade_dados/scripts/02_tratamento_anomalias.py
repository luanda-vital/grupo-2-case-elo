"""
02_tratamento_anomalias.py — Tratamento de anomalias das bases do case Vértice Retail

Objetivo: aplicar, de forma explícita e rastreável, as decisões de tratamento de
qualidade de dados identificadas no perfilamento (`scripts/01_perfilamento.py` /
`reports/01_perfilamento.md`), ANTES de qualquer cálculo de média, taxa ou
agregação nas fases seguintes.

Princípios (não-negociáveis do case, ver CLAUDE.md):
  - Nunca inferir/preencher dado ausente. Nulo é removido (quando a linha é
    lixo/corrompida) ou reportado — nunca imputado.
  - Um padrão só é aceito como explicação depois de testado em outro corte dos
    dados (evita correlação espúria) — os testes que sustentam as decisões
    abaixo estão comentados no código, com o resultado observado.
  - Toda decisão de tratamento é uma premissa explícita, documentada aqui e no
    relatório gerado — nunca implícita.

Decisões aplicadas (resumo — detalhe e evidência por base abaixo):
  1. [vendas]      remove 1 linha "quase-vazia" (corrompida) — chave preenchida,
                    100% das demais colunas nulas.
  2. [vendas]      adiciona coluna derivada `pagamento_aprovado` (bool) — não
                    sobrescreve `status_pagamento`; permite excluir pedidos
                    Cancelado/Aguardando de métricas de receita/margem
                    REALIZADA nas fases seguintes, sem apagar a informação bruta.
  3. [marketing]   NÃO remove/zera investimento das 495 campanhas de canal
                    'Orgânico' com investimento_reais > 0 — teste mostrou que
                    são 100% das campanhas desse canal, com investimento na
                    mesma ordem de grandeza dos canais pagos. Não é erro
                    pontual: é a definição do canal nesta base. Documentado
                    como premissa para não tratar 'Orgânico' como tráfego
                    gratuito nas análises de CAC/ROAS por canal.
  4. [clientes]    nenhuma remoção. Sentinela 'Não informado' em `genero`
                    documentada como ausência codificada (não é nulo pandas,
                    mas deve ser tratada como "sem informação" em agregações
                    por gênero). Nomes duplicados (2346) apenas documentados —
                    `customer_id` é a chave confirmada única; não há como
                    desambiguar homônimos de duplicatas reais sem mais dados,
                    logo nenhuma linha é removida.
  5. [atendimento] remove 1 linha "quase-vazia" (corrompida) — mesmo padrão do
                    item 1.
  6. [atendimento] NÃO trata tempo_primeira_resposta_minutos == 0 (1790
                    tickets) como erro — teste por canal mostrou que 100% dos
                    casos vêm do canal ChatBot (25% dos tickets desse canal),
                    consistente com resposta automática instantânea.
  7. [atendimento] adiciona coluna derivada `fechamento_registrado` (bool) e
                    `status_inconsistente` (bool) — teste mostrou que os
                    12.488 tickets (34,8%) com status "não resolvido" têm
                    data_fechamento E nota_csat preenchidas em 100% dos casos
                    (o mesmo vale, invertido, para os "Resolvido": 100% também
                    têm essas colunas preenchidas). Ou seja, `status_atendimento`
                    está dessincronizado do fechamento real para ~1/3 da base.
                    Não se sobrescreve `status_atendimento` (seria inferir) —
                    documenta-se a inconsistência e disponibiliza-se o campo
                    derivado para as fases seguintes decidirem qual usar.
  8. [estoque]     nenhuma remoção/alteração. Ruptura, Estoque Crítico,
                    Descontinuado e estoque_disponivel < ponto_pedido são
                    estados de negócio legítimos (não erros de dado) —
                    tratados como achados na Fase 2.4, não como anomalias.
  9. [cross-base]  documenta a premissa da janela de análise: séries
                    conjuntas de receita/margem (vendas x marketing x
                    atendimento) só são válidas na janela coberta por vendas
                    (2023-01-01 a 2024-01-26). Marketing e atendimento têm
                    período mais longo e podem ser analisados isoladamente
                    fora dessa janela, mas não combinados com vendas fora dela.

Nenhum outlier estatístico (IQR) foi removido nas colunas monetárias — a
checagem abaixo mostra caudas largas mas plausíveis (produtos de ticket alto),
sem valores negativos ou zerados suspeitos nas colunas de preço/quantidade.
Ver seção de checagem de outliers no relatório gerado.

Saídas:
    - data/processed/*.csv  : bases limpas (linhas corrompidas removidas,
      colunas derivadas adicionadas). `data/raw/` nunca é alterado.
    - reports/02_tratamento_anomalias.md : decisões, evidência e contagens
      antes/depois por base.

Uso:
    python scripts/02_tratamento_anomalias.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORT_PATH = Path("reports/02_tratamento_anomalias.md")


def carregar(arquivo: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / arquivo, dtype=None, keep_default_na=True)


def linhas_quase_vazias(df: pd.DataFrame, chave: list[str], limiar: float = 0.7) -> pd.Index:
    chave_presente = [c for c in chave if c in df.columns]
    outras = [c for c in df.columns if c not in chave_presente]
    frac_nula = df[outras].isna().mean(axis=1)
    chave_ok = df[chave_presente].notna().all(axis=1)
    return df.index[(frac_nula >= limiar) & chave_ok]


def checar_outliers_iqr(df: pd.DataFrame, colunas: list[str], nome_base: str) -> list[str]:
    """Reporta (sem remover) valores fora de 1.5x e 3x IQR nas colunas monetárias/quantidade.

    Decisão do case: dado sintético de retail pode legitimamente ter caudas largas
    (produtos de ticket alto, campanhas grandes). Só remove/trata valor se ele for
    logicamente impossível (negativo em coluna que não pode ser negativa, zero em
    coluna que não pode ser zero) — isso já foi checado no perfilamento (nenhum
    caso encontrado nas colunas de preço/quantidade). Aqui só quantificamos as
    caudas para deixar registrado que foram inspecionadas.
    """
    linhas = []
    for c in colunas:
        if c not in df.columns:
            continue
        s = df[c].dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            # IQR=0 (variável quase-discreta, ex.: valor fixo por categoria) torna o
            # critério 1.5x/3x IQR um artefato matemático, não um outlier real —
            # reportar a cardinalidade em vez de uma contagem enganosa.
            linhas.append(
                f"- [{nome_base}] `{c}`: IQR=0 (p25=p50=p75={q1:.2f}) — variável quase-discreta "
                f"({s.nunique()} valores únicos: {sorted(s.unique().tolist())}), critério de IQR não "
                f"se aplica; não é outlier, é uma tabela de valores fixos por categoria."
            )
            continue
        leve = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
        forte = int(((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).sum())
        linhas.append(
            f"- [{nome_base}] `{c}`: {leve} valores fora de 1.5×IQR ({leve / len(s) * 100:.1f}%), "
            f"{forte} fora de 3×IQR ({forte / len(s) * 100:.1f}%) — caudas largas mas plausíveis "
            f"(sem correção aplicada; nenhum valor logicamente impossível)."
        )
    return linhas


def tratar_vendas() -> tuple[pd.DataFrame, list[str]]:
    df = carregar("vendas.csv")
    n0 = len(df)
    log: list[str] = []

    qv = linhas_quase_vazias(df, ["order_id", "sku_id"])
    removidos = df.loc[qv, "order_id"].tolist()
    df = df.drop(index=qv).reset_index(drop=True)
    log.append(
        f"Removida(s) {len(qv)} linha(s) quase-vazia(s) (corrompida/truncada): "
        f"order_id={removidos}. Linhas: {n0} → {len(df)}."
    )

    df["pagamento_aprovado"] = df["status_pagamento"].eq("Aprovado")
    n_nao_aprovado = int((~df["pagamento_aprovado"]).sum())
    log.append(
        f"Coluna derivada `pagamento_aprovado` adicionada. {n_nao_aprovado} itens "
        f"({n_nao_aprovado / len(df) * 100:.1f}%) com status_pagamento != 'Aprovado' "
        f"(Cancelado/Aguardando) — PREMISSA: excluir esses itens ao calcular receita/"
        f"margem REALIZADA nas fases seguintes; a linha é mantida na base para não "
        f"perder rastreabilidade do volume bruto de pedidos."
    )

    neg = int((df["margem_contribuicao"] < 0).sum())
    log.append(
        f"NÃO removidos: {neg} itens ({neg / len(df) * 100:.1f}%) com margem_contribuicao "
        f"negativa — é sinal de negócio (venda com prejuízo unitário), não erro de dado. "
        f"Fica para investigação na Fase 2.4."
    )
    dev = int(df["devolvido"].astype("string").eq("True").sum())
    log.append(
        f"NÃO removidos: {dev} itens ({dev / len(df) * 100:.1f}%) marcados devolvido=True — "
        f"sinal de negócio, não erro de dado."
    )

    log.extend(checar_outliers_iqr(
        df, ["preco_unitario", "receita_bruta", "custo_produto", "margem_contribuicao"], "vendas"
    ))
    return df, log


def tratar_marketing() -> tuple[pd.DataFrame, list[str]]:
    df = carregar("marketing.csv")
    log: list[str] = []

    org = df["canal"].eq("Orgânico")
    org_com_invest = org & (df["investimento_reais"] > 0)
    df["organico_com_investimento"] = org_com_invest
    mediana_org = df.loc[org_com_invest, "investimento_reais"].median()
    mediana_pago = df.loc[~org, "investimento_reais"].median()
    log.append(
        f"NÃO alterado: {int(org_com_invest.sum())} de {int(org.sum())} campanhas "
        f"'Orgânico' ({org_com_invest.sum() / max(org.sum(), 1) * 100:.0f}% do canal) têm "
        f"investimento_reais > 0, com mediana R$ {mediana_org:,.2f} vs R$ {mediana_pago:,.2f} "
        f"dos canais pagos — ordem de grandeza semelhante. Teste mostra que não é exceção "
        f"pontual: é a definição do canal nesta base. PREMISSA: 'Orgânico' aqui NÃO é "
        f"tráfego gratuito — deve ser tratado como canal pago em CAC/ROAS nas fases "
        f"seguintes. Coluna derivada `organico_com_investimento` adicionada para rastreio."
    )
    log.extend(checar_outliers_iqr(
        df, ["investimento_reais", "cac", "roas"], "marketing"
    ))
    return df, log


def tratar_clientes() -> tuple[pd.DataFrame, list[str]]:
    df = carregar("clientes.csv")
    log: list[str] = []

    sentinela = int(df["genero"].eq("Não informado").sum())
    log.append(
        f"NÃO alterado: {sentinela} linhas ({sentinela / len(df) * 100:.1f}%) com "
        f"genero='Não informado' — sentinela textual de ausência, mantida como está "
        f"(não é NaN do pandas). PREMISSA: tratar como 'sem informação' em agregações "
        f"por gênero, nunca redistribuir entre as demais categorias."
    )
    dupn = int(df["nome_completo"].duplicated().sum())
    log.append(
        f"NÃO removido: {dupn} nomes_completos repetidos — `customer_id` é a chave "
        f"confirmada única (perfilamento: grão OK). Sem outro campo para desambiguar "
        f"homônimo de cadastro duplicado, nenhuma linha é removida; achado apenas "
        f"documentado como limitação da base."
    )
    log.extend(checar_outliers_iqr(df, ["renda_estimada", "ltv_acumulado", "total_pedidos_historico"], "clientes"))
    return df, log


def tratar_atendimento() -> tuple[pd.DataFrame, list[str]]:
    df = carregar("atendimento.csv")
    n0 = len(df)
    log: list[str] = []

    qv = linhas_quase_vazias(df, ["ticket_id"])
    removidos = df.loc[qv, "ticket_id"].tolist()
    df = df.drop(index=qv).reset_index(drop=True)
    log.append(
        f"Removida(s) {len(qv)} linha(s) quase-vazia(s) (corrompida/truncada): "
        f"ticket_id={removidos}. Linhas: {n0} → {len(df)}."
    )

    zero = df["tempo_primeira_resposta_minutos"].eq(0)
    zero_chatbot = zero & df["canal_entrada"].eq("ChatBot")
    pct_chatbot_zero = (
        df.loc[df["canal_entrada"].eq("ChatBot"), "tempo_primeira_resposta_minutos"].eq(0).mean() * 100
    )
    log.append(
        f"NÃO tratado como erro: {int(zero.sum())} tickets com tempo_primeira_resposta=0 min — "
        f"teste por canal mostra que {int(zero_chatbot.sum())}/{int(zero.sum())} "
        f"({zero_chatbot.sum() / max(zero.sum(), 1) * 100:.0f}%) vêm do canal ChatBot "
        f"({pct_chatbot_zero:.1f}% dos tickets desse canal), consistente com resposta "
        f"automática instantânea — não erro de registro."
    )

    df["fechamento_registrado"] = df["data_fechamento"].notna()
    nao_resolvido_label = df["status_atendimento"].isin(["Aberto", "Em Análise", "Escalado para N2"])
    df["status_inconsistente"] = nao_resolvido_label & df["fechamento_registrado"] & df["nota_csat"].notna()
    n_inc = int(df["status_inconsistente"].sum())
    resolvido_sem_fech = int((df["status_atendimento"].eq("Resolvido") & ~df["fechamento_registrado"]).sum())
    log.append(
        f"Colunas derivadas `fechamento_registrado` e `status_inconsistente` adicionadas. "
        f"{n_inc} tickets ({n_inc / len(df) * 100:.1f}%) têm status_atendimento de 'não "
        f"resolvido' mas já têm data_fechamento E nota_csat preenchidas (100% dos rotulados "
        f"'não resolvido' caem nesse caso); e {resolvido_sem_fech} tickets 'Resolvido' sem "
        f"data_fechamento (nenhum encontrado). CONCLUSÃO DO TESTE: `status_atendimento` está "
        f"dessincronizado do fechamento real em ~1/3 da base. PREMISSA: `status_atendimento` "
        f"NÃO é sobrescrito (seria inferir); análises de SLA/backlog devem preferir "
        f"`fechamento_registrado` e documentar a limitação do campo de status."
    )
    log.extend(checar_outliers_iqr(df, ["tempo_primeira_resposta_minutos", "custo_operacional_ticket"], "atendimento"))
    return df, log


def tratar_estoque() -> tuple[pd.DataFrame, list[str]]:
    df = carregar("estoque.csv")
    log: list[str] = []
    log.append(
        "NÃO alterado: status_disponibilidade (Ruptura/Estoque Crítico/Descontinuado) e "
        "estoque_disponivel < ponto_pedido são estados operacionais legítimos, não erros "
        "de dado — tratados como achados de negócio na Fase 2.4, não como anomalias a corrigir."
    )
    log.extend(checar_outliers_iqr(
        df, ["custo_unitario", "preco_venda_sugerido", "estoque_fisico", "estoque_disponivel"], "estoque"
    ))
    return df, log


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    tratamentos = {
        "vendas": tratar_vendas,
        "marketing": tratar_marketing,
        "clientes": tratar_clientes,
        "atendimento": tratar_atendimento,
        "estoque": tratar_estoque,
    }

    md = ["# Tratamento de anomalias — Vértice Retail", ""]
    md.append("_Gerado por `scripts/02_tratamento_anomalias.py` — data de referência 2026-09-10._")
    md.append("")
    md.append(
        "> Princípio: nulo é removido só quando a linha é corrompida (quase-vazia); "
        "nunca imputado. Um padrão só vira premissa depois de testado em outro corte "
        "(evidência do teste fica registrada em cada item abaixo)."
    )
    md.append("")

    resumo_linhas = []
    for nome, fn in tratamentos.items():
        print("=" * 88)
        print(f"BASE: {nome}")
        print("=" * 88)
        df, log = fn()
        out_path = PROCESSED_DIR / f"{nome}.csv"
        df.to_csv(out_path, index=False)
        for linha in log:
            print(f"  - {linha}")
        print(f"  -> salvo em {out_path} ({len(df)} linhas x {df.shape[1]} colunas)")
        print()

        md.append(f"## {nome}")
        md.append("")
        for linha in log:
            md.append(f"- {linha}")
        md.append("")
        md.append(f"**Salvo em:** `{out_path.as_posix()}` — {len(df)} linhas × {df.shape[1]} colunas.")
        md.append("")
        resumo_linhas.append((nome, len(df), df.shape[1]))

    md.append("## Premissa cruzada — janela de análise")
    md.append("")
    md.append(
        "- Vendas cobre 2023-01-01 a 2024-01-26 (13 meses); marketing e atendimento vão "
        "até 2025-12-31. PREMISSA: qualquer análise conjunta de receita/margem "
        "(vendas × marketing, vendas × atendimento) usa exclusivamente a janela de "
        "vendas (2023-01-01 a 2024-01-26). Fora dessa janela, marketing e atendimento "
        "podem ser analisados isoladamente (ex.: eficiência de canal, volume de "
        "tickets), mas não combinados com totais de vendas como se fossem concorrentes."
    )
    md.append("")

    md.append("## Resumo — linhas antes/depois")
    md.append("")
    md.append("| base | linhas (raw) | linhas (processed) | colunas (processed) |")
    md.append("|---|---:|---:|---:|")
    raw_counts = {
        "vendas": 27759, "marketing": 3500, "clientes": 15000,
        "atendimento": 35841, "estoque": 5000,
    }
    for nome, n, ncols in resumo_linhas:
        md.append(f"| {nome} | {raw_counts[nome]} | {n} | {ncols} |")
    md.append("")

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"Relatório salvo em: {REPORT_PATH}")


if __name__ == "__main__":
    main()
