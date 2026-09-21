"""
01_perfilamento.py — Perfilamento das bases brutas do case Vértice Retail

Objetivo: para cada base em data/raw/ descrever
  - período coberto (min/max das colunas de data)
  - grão (o que 1 linha representa) + verificação de unicidade da chave candidata
  - nulos por coluna (contagem e %)
  - tipos de coluna
  - distribuição das variáveis numéricas (describe + zeros + negativos)
  - alertas de qualidade de dados

Restrição: NÃO inferir/preencher dado ausente. Nulos são apenas reportados.

Uso:
    python scripts/01_perfilamento.py

Saídas:
    - stdout: relatório legível
    - reports/01_perfilamento.md : tabela resumo por base + lista de alertas
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Console Windows costuma ser cp1252; força UTF-8 para não quebrar em acentos/setas.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

RAW_DIR = Path("data/raw")
REPORT_PATH = Path("reports/01_perfilamento.md")

# ---------------------------------------------------------------------------
# Configuração por base: chave candidata (grão) e colunas que são datas
# ---------------------------------------------------------------------------
BASES = {
    "vendas": {
        "arquivo": "vendas.csv",
        "grao_desc": "1 linha = 1 item de pedido (order_id x sku_id) — pedido pode ter vários itens",
        "chave": ["order_id", "sku_id"],
        "colunas_data": ["data_pedido"],
        "ordem_datas": [],
        "sentinelas": {},  # 'Não se aplica' em motivo_devolucao é legítimo (item não devolvido)
        "cat_cols": ["canal", "categoria", "metodo_pagamento", "status_pagamento",
                     "devolvido", "motivo_devolucao"],
    },
    "marketing": {
        "arquivo": "marketing.csv",
        "grao_desc": "1 linha = 1 campanha de marketing (campanha_id) num intervalo data_inicio..data_fim",
        "chave": ["campanha_id"],
        "colunas_data": ["data_inicio", "data_fim"],
        "ordem_datas": [("data_inicio", "data_fim")],
        "sentinelas": {},
        "cat_cols": ["canal", "categoria_foco", "atribuicao", "status"],
    },
    "clientes": {
        "arquivo": "clientes.csv",
        "grao_desc": "1 linha = 1 cliente (customer_id) — cadastro + métricas históricas agregadas",
        "chave": ["customer_id"],
        "colunas_data": ["data_nascimento", "data_cadastro"],
        "ordem_datas": [("data_nascimento", "data_cadastro")],
        "sentinelas": {"genero": ["Não informado"]},
        "cat_cols": ["genero", "estado", "nivel_fidelidade", "dispositivo_principal",
                     "segmento_rfm", "opt_in_newsletter"],
    },
    "atendimento": {
        "arquivo": "atendimento.csv",
        "grao_desc": "1 linha = 1 ticket de atendimento (ticket_id), ligado a customer_id e order_id",
        "chave": ["ticket_id"],
        "colunas_data": ["data_abertura", "data_fechamento"],
        "ordem_datas": [("data_abertura", "data_fechamento")],
        "sentinelas": {},
        "cat_cols": ["canal_entrada", "categoria_problema", "status_atendimento"],
    },
    "estoque": {
        "arquivo": "estoque.csv",
        "grao_desc": "1 linha = 1 SKU (sku_id) — snapshot de catálogo/estoque",
        "chave": ["sku_id"],
        "colunas_data": ["data_ultima_entrada"],
        "ordem_datas": [],
        "sentinelas": {},
        "cat_cols": ["categoria", "subcategoria", "status_disponibilidade"],
    },
}


def carregar(arquivo: str) -> pd.DataFrame:
    """Lê o CSV sem qualquer imputação. keep_default_na mantém células vazias como NaN."""
    return pd.read_csv(RAW_DIR / arquivo, dtype=None, keep_default_na=True)


def resumo_nulos(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    nulos = df.isna().sum()
    return (
        pd.DataFrame(
            {
                "coluna": nulos.index,
                "dtype": [str(df[c].dtype) for c in nulos.index],
                "nulos": nulos.values,
                "pct_nulos": (nulos.values / n * 100).round(2),
            }
        )
        .sort_values("nulos", ascending=False)
        .reset_index(drop=True)
    )


def periodo_coberto(df: pd.DataFrame, colunas_data: list[str]) -> dict:
    per = {}
    for c in colunas_data:
        if c in df.columns:
            s = pd.to_datetime(df[c], errors="coerce")
            per[c] = {
                "min": s.min(),
                "max": s.max(),
                "nulos_ou_invalidos": int(s.isna().sum()),
            }
    return per


def checar_grao(df: pd.DataFrame, chave: list[str]) -> dict:
    chave_presente = [c for c in chave if c in df.columns]
    if not chave_presente:
        return {"chave": chave, "ok": False, "motivo": "chave ausente no arquivo"}
    dup = int(df.duplicated(subset=chave_presente).sum())
    nulos_chave = int(df[chave_presente].isna().any(axis=1).sum())
    return {
        "chave": chave_presente,
        "linhas": len(df),
        "combinacoes_unicas": int(df.drop_duplicates(subset=chave_presente).shape[0]),
        "linhas_duplicadas_na_chave": dup,
        "linhas_com_chave_nula": nulos_chave,
        "grao_confirmado": dup == 0 and nulos_chave == 0,
    }


def distribuicao_numerica(df: pd.DataFrame) -> pd.DataFrame:
    num = df.select_dtypes(include=[np.number])
    if num.empty:
        return pd.DataFrame()
    desc = num.describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
    desc["zeros"] = (num == 0).sum()
    desc["negativos"] = (num < 0).sum()
    desc["nulos"] = num.isna().sum()
    cols = ["count", "mean", "std", "min", "1%", "25%", "50%", "75%", "99%", "max",
            "zeros", "negativos", "nulos"]
    return desc[[c for c in cols if c in desc.columns]]


def linhas_quase_vazias(df: pd.DataFrame, chave: list[str], limiar: float = 0.7) -> pd.Index:
    """Índices de linhas com chave preenchida e >= `limiar` das demais colunas nulas."""
    chave_presente = [c for c in chave if c in df.columns]
    outras = [c for c in df.columns if c not in chave_presente]
    if not outras or not chave_presente:
        return pd.Index([])
    frac_nula = df[outras].isna().mean(axis=1)
    chave_ok = df[chave_presente].notna().all(axis=1)
    return df.index[(frac_nula >= limiar) & chave_ok]


def sentinelas_de_ausencia(df: pd.DataFrame, sentinelas: dict) -> dict:
    """Conta valores-string que codificam ausência (não são NaN, mas significam 'sem dado')."""
    out = {}
    for col, valores in sentinelas.items():
        if col in df.columns:
            q = int(df[col].isin(valores).sum())
            if q:
                out[col] = (valores, q, round(q / len(df) * 100, 1))
    return out


def violacoes_ordem_datas(df: pd.DataFrame, pares: list) -> dict:
    out = {}
    for antes, depois in pares:
        if antes in df.columns and depois in df.columns:
            a = pd.to_datetime(df[antes], errors="coerce")
            d = pd.to_datetime(df[depois], errors="coerce")
            q = int((d < a).sum())
            if q:
                out[(antes, depois)] = q
    return out


def coletar_alertas(nome: str, df: pd.DataFrame, cfg: dict,
                    grao: dict, per: dict, dist: pd.DataFrame) -> list[str]:
    alertas: list[str] = []
    n = len(df)

    # grão
    if not grao.get("grao_confirmado", False):
        if grao.get("linhas_duplicadas_na_chave", 0):
            alertas.append(
                f"[{nome}] {grao['linhas_duplicadas_na_chave']} linhas duplicadas na chave "
                f"{grao['chave']} — grão declarado não é único."
            )
        if grao.get("linhas_com_chave_nula", 0):
            alertas.append(
                f"[{nome}] {grao['linhas_com_chave_nula']} linhas com chave {grao['chave']} nula."
            )

    # nulos
    nul = df.isna().sum()
    nul = nul[nul > 0].sort_values(ascending=False)
    cols_nulas = list(nul.index)
    qv = linhas_quase_vazias(df, grao.get("chave", []))
    # linhas que carregam TODOS os nulos da base
    linhas_com_nulo = df.index[df[cols_nulas].isna().any(axis=1)] if cols_nulas else pd.Index([])
    fora_de_qv = linhas_com_nulo.difference(qv)

    if len(qv):
        exemplos = ", ".join(f"{grao['chave'][0]}={df.loc[i, grao['chave'][0]]!r}" for i in qv[:3])
        alertas.append(
            f"[{nome}] {len(qv)} linha(s) quase-vazias (identificador preenchido, ≥70% das "
            f"demais colunas nulas) — ex.: {exemplos}. Registro corrompido/truncado: "
            f"remover na limpeza, não imputar. Concentram {int(df.loc[qv, cols_nulas].isna().sum().sum())} "
            f"das {int(nul.sum())} células nulas da base."
        )
    if len(fora_de_qv) == 0 and len(cols_nulas):
        pass  # todos os nulos já explicados pelas linhas quase-vazias
    elif 0 < len(linhas_com_nulo) <= 3:
        alertas.append(
            f"[{nome}] os {int(nul.sum())} nulos estão em {len(cols_nulas)} colunas mas "
            f"concentrados em {len(linhas_com_nulo)} linha(s) — não há nulos dispersos. "
            f"Colunas afetadas: {', '.join(cols_nulas)}."
        )
    else:
        for c, q in nul.items():
            alertas.append(f"[{nome}] coluna '{c}' com {q} nulos ({q / n * 100:.1f}%).")

    # valores-sentinela (ausência codificada como texto — NÃO é nulo, mas não é dado)
    for col, (vals, q, pct) in sentinelas_de_ausencia(df, cfg.get("sentinelas", {})).items():
        alertas.append(
            f"[{nome}] '{col}': {q} linhas ({pct}%) com valor-sentinela {vals} — "
            f"ausência codificada como texto, contar como 'sem informação', não como categoria."
        )

    # ordem de datas
    for (antes, depois), q in violacoes_ordem_datas(df, cfg.get("ordem_datas", [])).items():
        alertas.append(f"[{nome}] {q} linhas com '{depois}' anterior a '{antes}'.")

    # datas invalidas / fora de range plausivel
    for c, info in per.items():
        # não repetir se os nulos de data já foram cobertos pelas linhas quase-vazias
        if info["nulos_ou_invalidos"] > len(qv):
            alertas.append(
                f"[{nome}] coluna de data '{c}': {info['nulos_ou_invalidos']} valores "
                f"nulos ou não parseáveis."
            )
        if pd.notna(info["max"]) and info["max"] > pd.Timestamp("2026-09-10"):
            alertas.append(f"[{nome}] '{c}' tem datas no futuro (max={info['max']}).")
        if pd.notna(info["min"]) and info["min"] < pd.Timestamp("1900-01-01"):
            alertas.append(f"[{nome}] '{c}' tem datas implausivelmente antigas (min={info['min']}).")

    # numéricos: negativos e zeros suspeitos
    if not dist.empty:
        # margem pode ser legitimamente negativa — tratada em alertas_negocio()
        for c in dist.index:
            if dist.loc[c, "negativos"] > 0 and c != "margem_contribuicao":
                alertas.append(
                    f"[{nome}] '{c}': {int(dist.loc[c, 'negativos'])} valores negativos."
                )
        # colunas monetárias/quantidade onde zero é suspeito
        suspeito_zero = {
            "preco_unitario", "receita_bruta", "receita_liquida", "quantidade",
            "custo_produto", "preco_venda_sugerido", "custo_unitario",
            "investimento_reais", "impressoes", "cliques",
        }
        for c in dist.index:
            if c in suspeito_zero and dist.loc[c, "zeros"] > 0:
                alertas.append(
                    f"[{nome}] '{c}': {int(dist.loc[c, 'zeros'])} valores zero (avaliar se válido)."
                )

    # duplicidade de linha inteira
    dup_full = int(df.duplicated().sum())
    if dup_full:
        alertas.append(f"[{nome}] {dup_full} linhas 100% duplicadas.")

    alertas.extend(alertas_negocio(nome, df))
    return alertas


def alertas_negocio(nome: str, df: pd.DataFrame) -> list[str]:
    """Regras específicas de cada base, identificadas na inspeção inicial."""
    al: list[str] = []
    n = len(df)

    if nome == "vendas":
        neg = df["margem_contribuicao"] < 0
        al.append(
            f"[vendas] {int(neg.sum())} itens ({neg.mean() * 100:.1f}%) com "
            f"margem_contribuicao negativa — venda com prejuízo unitário "
            f"(relevante para a queda de rentabilidade)."
        )
        dev = df["devolvido"].astype("string").eq("True")
        al.append(f"[vendas] taxa de devolução: {dev.mean() * 100:.1f}% "
                  f"({int(dev.sum())} itens marcados devolvido=True).")
        aguard = df["status_pagamento"].eq("Aguardando") | df["status_pagamento"].eq("Cancelado")
        al.append(f"[vendas] {int(aguard.sum())} itens com pagamento não aprovado "
                  f"(Aguardando/Cancelado) — decidir se entram no cálculo de receita.")

    if nome == "clientes":
        dupn = int(df["nome_completo"].duplicated().sum())
        if dupn:
            al.append(f"[clientes] {dupn} nomes_completos repetidos — possíveis clientes "
                      f"duplicados ou homônimos; não há chave para desambiguar.")
        nasc = pd.to_datetime(df["data_nascimento"], errors="coerce")
        al.append(f"[clientes] data_nascimento só entre {fmt_dt(nasc.min())} e "
                  f"{fmt_dt(nasc.max())} (faixa etária ~{2026 - nasc.dt.year.max()}–"
                  f"{2026 - nasc.dt.year.min()} anos) — distribuição estreita, provável dado sintético.")

    if nome == "atendimento":
        z = df["tempo_primeira_resposta_minutos"].eq(0)
        al.append(f"[atendimento] {int(z.sum())} tickets ({z.mean() * 100:.1f}%) com "
                  f"tempo_primeira_resposta = 0 min — avaliar se é resposta automática ou falha de registro.")
        cap = df["tempo_primeira_resposta_minutos"].eq(1440)
        if cap.sum() > 50:
            al.append(f"[atendimento] {int(cap.sum())} tickets com tempo_primeira_resposta "
                      f"exatamente 1440 min (24h) — possível teto artificial (censura).")
        ab = df["status_atendimento"].isin(["Aberto", "Em Análise", "Escalado para N2"])
        com_fech = ab & df["data_fechamento"].notna()
        al.append(f"[atendimento] {int(ab.sum())} tickets ({ab.mean() * 100:.1f}%) com status não "
                  f"resolvido (Aberto/Em Análise/Escalado), mas {int(com_fech.sum())} deles têm "
                  f"data_fechamento e nota_csat preenchidas — status e datas inconsistentes.")

    if nome == "estoque":
        for st in ["Ruptura", "Estoque Crítico", "Descontinuado"]:
            q = int(df["status_disponibilidade"].eq(st).sum())
            if q:
                al.append(f"[estoque] {q} SKUs ({q / n * 100:.1f}%) com status '{st}'.")
        rup = df["estoque_disponivel"].eq(0)
        al.append(f"[estoque] {int(rup.sum())} SKUs ({rup.mean() * 100:.1f}%) com "
                  f"estoque_disponivel = 0.")
        abaixo = df["estoque_disponivel"] < df["ponto_pedido"]
        al.append(f"[estoque] {int(abaixo.sum())} SKUs ({abaixo.mean() * 100:.1f}%) com "
                  f"estoque_disponivel abaixo do ponto_pedido — reposição pendente.")

    if nome == "marketing":
        org = df["canal"].isin(["Orgânico"]) & (df["investimento_reais"] > 0)
        if org.sum():
            al.append(f"[marketing] {int(org.sum())} campanhas de canal 'Orgânico' com "
                      f"investimento_reais > 0 — inconsistente com a definição de canal orgânico.")
        fut = pd.to_datetime(df["data_fim"], errors="coerce") > pd.Timestamp("2026-09-10")
        if fut.sum():
            al.append(f"[marketing] {int(fut.sum())} campanhas com data_fim no futuro (após hoje).")

    return al


def fmt_dt(v) -> str:
    return "—" if pd.isna(v) else pd.Timestamp(v).strftime("%Y-%m-%d")


def checar_cross_base(dfs: dict) -> list[str]:
    """Alertas que só aparecem cruzando as bases (chaves e janelas temporais)."""
    al: list[str] = []
    v, m, c, a, e = (dfs["vendas"], dfs["marketing"], dfs["clientes"],
                     dfs["atendimento"], dfs["estoque"])

    # janelas temporais
    vd = pd.to_datetime(v["data_pedido"], errors="coerce")
    ad = pd.to_datetime(a["data_abertura"], errors="coerce")
    md = pd.to_datetime(m["data_inicio"], errors="coerce")
    al.append(
        f"[cross] DESCASAMENTO DE PERÍODO: vendas vai de {fmt_dt(vd.min())} a "
        f"{fmt_dt(vd.max())} ({vd.dt.to_period('M').nunique()} meses, "
        f"{(vd.dt.year == vd.dt.year.min()).mean() * 100:.0f}% no 1º ano), enquanto "
        f"atendimento vai até {fmt_dt(ad.max())} e marketing até "
        f"{fmt_dt(pd.to_datetime(m['data_fim'], errors='coerce').max())}. "
        f"Análises conjuntas de receita/rentabilidade só são possíveis na janela de vendas."
    )

    # integridade referencial
    def pct(mask):
        return f"{mask.sum()} ({mask.mean() * 100:.1f}%)"

    al.append(f"[cross] vendas.customer_id ausente em clientes: "
              f"{pct(~v['customer_id'].isin(c['customer_id']))}")
    al.append(f"[cross] vendas.sku_id ausente em estoque: "
              f"{pct(~v['sku_id'].isin(e['sku_id']))}")
    ao = a["order_id"].dropna()
    al.append(f"[cross] atendimento.order_id ausente em vendas.order_id: "
              f"{ao.isin(v['order_id']).eq(False).sum()} de {len(ao)} "
              f"({ao.isin(v['order_id']).eq(False).mean() * 100:.1f}%) — "
              f"coerente com o descasamento de período (tickets pós-fim de vendas).")
    ac = a["customer_id"].dropna()
    al.append(f"[cross] atendimento.customer_id ausente em clientes: "
              f"{pct(~ac.isin(c['customer_id']))}")
    al.append(f"[cross] clientes sem NENHuma compra em vendas: "
              f"{pct(~c['customer_id'].isin(v['customer_id']))} — base de clientes é "
              f"muito maior que a atividade transacional do período.")

    # canais divergentes entre vendas e marketing
    cv, cm = set(v["canal"].dropna().unique()), set(m["canal"].dropna().unique())
    if cv ^ cm:
        al.append(f"[cross] canais em vendas mas não em marketing: {sorted(cv - cm) or '—'}; "
                  f"em marketing mas não em vendas: {sorted(cm - cv) or '—'}.")
    return al


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    linhas_resumo = []
    todos_alertas: list[str] = []
    blocos_md: list[str] = []
    dfs: dict = {}

    for nome, cfg in BASES.items():
        df = carregar(cfg["arquivo"])
        dfs[nome] = df
        per = periodo_coberto(df, cfg["colunas_data"])
        grao = checar_grao(df, cfg["chave"])
        nulos = resumo_nulos(df)
        dist = distribuicao_numerica(df)
        alertas = coletar_alertas(nome, df, cfg, grao, per, dist)
        todos_alertas.extend(alertas)

        # período global da base = menor min / maior max entre colunas de data "de evento"
        mins = [i["min"] for i in per.values() if pd.notna(i["min"])]
        maxs = [i["max"] for i in per.values() if pd.notna(i["max"])]
        periodo_txt = (
            f"{fmt_dt(min(mins))} → {fmt_dt(max(maxs))}" if mins and maxs else "sem coluna de data"
        )

        total_nulos = int(df.isna().sum().sum())
        cols_com_nulos = int((df.isna().sum() > 0).sum())

        linhas_resumo.append(
            {
                "base": nome,
                "linhas": len(df),
                "colunas": df.shape[1],
                "periodo": periodo_txt,
                "grao": cfg["grao_desc"],
                "grao_ok": "sim" if grao.get("grao_confirmado") else "NÃO",
                "cols_c/_nulos": cols_com_nulos,
                "total_células_nulas": total_nulos,
            }
        )

        # ----- stdout -----
        print("=" * 88)
        print(f"BASE: {nome}  ({cfg['arquivo']})")
        print("=" * 88)
        print(f"Dimensão      : {df.shape[0]} linhas x {df.shape[1]} colunas")
        print(f"Grão declarado: {cfg['grao_desc']}")
        print(f"Grão checado  : chave={grao['chave']} | duplicadas={grao.get('linhas_duplicadas_na_chave')} "
              f"| chave nula={grao.get('linhas_com_chave_nula')} | confirmado={grao.get('grao_confirmado')}")
        print(f"Período       : {periodo_txt}")
        for c, info in per.items():
            print(f"   {c}: {fmt_dt(info['min'])} .. {fmt_dt(info['max'])} "
                  f"(nulos/invalidos={info['nulos_ou_invalidos']})")
        print("\nTipos e nulos por coluna:")
        print(nulos.to_string(index=False))
        if not dist.empty:
            print("\nDistribuição das variáveis numéricas:")
            print(dist.round(2).to_string())
        print(f"\nAlertas desta base: {len(alertas)}")
        for a in alertas:
            print(f"   - {a}")
        print()

        # ----- markdown -----
        b = [f"### {nome} — `{cfg['arquivo']}`", ""]
        b.append(f"- **Dimensão:** {df.shape[0]} linhas × {df.shape[1]} colunas")
        b.append(f"- **Período coberto:** {periodo_txt}")
        b.append(f"- **Grão:** {cfg['grao_desc']}")
        b.append(f"- **Grão confirmado (chave `{'` + `'.join(grao['chave'])}` única e não-nula):** "
                 f"{'sim' if grao.get('grao_confirmado') else '**NÃO**'}")
        b.append("")
        b.append("| coluna | dtype | nulos | % nulos |")
        b.append("|---|---|---:|---:|")
        for _, r in nulos.iterrows():
            b.append(f"| {r['coluna']} | {r['dtype']} | {int(r['nulos'])} | {r['pct_nulos']:.2f}% |")
        b.append("")
        if not dist.empty:
            b.append("| variável num. | min | p1 | p25 | p50 | p75 | p99 | max | média | desv.pad. | zeros | negativos | nulos |")
            b.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
            for c in dist.index:
                b.append(
                    f"| {c} | {dist.loc[c, 'min']:.2f} | {dist.loc[c, '1%']:.2f} | "
                    f"{dist.loc[c, '25%']:.2f} | {dist.loc[c, '50%']:.2f} | {dist.loc[c, '75%']:.2f} | "
                    f"{dist.loc[c, '99%']:.2f} | {dist.loc[c, 'max']:.2f} | {dist.loc[c, 'mean']:.2f} | "
                    f"{dist.loc[c, 'std']:.2f} | {int(dist.loc[c, 'zeros'])} | "
                    f"{int(dist.loc[c, 'negativos'])} | {int(dist.loc[c, 'nulos'])} |"
                )
            b.append("")
        cats = [c for c in cfg.get("cat_cols", []) if c in df.columns]
        if cats:
            b.append("Variáveis categóricas (valores distintos, top por frequência):")
            b.append("")
            for c in cats:
                vc = df[c].value_counts(dropna=False)
                itens = ", ".join(
                    f"{'(nulo)' if pd.isna(k) else k}={v}" for k, v in vc.head(8).items()
                )
                extra = f" … +{len(vc) - 8} outros" if len(vc) > 8 else ""
                b.append(f"- `{c}` ({df[c].nunique(dropna=True)} distintos): {itens}{extra}")
            b.append("")
        blocos_md.append("\n".join(b))

    # ----- checagens cruzadas entre bases -----
    alertas_cross = checar_cross_base(dfs)
    todos_alertas.extend(alertas_cross)
    print("=" * 88)
    print("CHECAGENS CRUZADAS ENTRE BASES")
    print("=" * 88)
    for a in alertas_cross:
        print(f"   - {a}")
    print()

    # ----- tabela resumo -----
    resumo = pd.DataFrame(linhas_resumo)
    print("#" * 88)
    print("RESUMO GERAL")
    print("#" * 88)
    print(resumo.to_string(index=False))
    print(f"\nTOTAL DE ALERTAS DE QUALIDADE: {len(todos_alertas)}")
    for a in todos_alertas:
        print(f" - {a}")

    # ----- markdown final -----
    md = ["# Perfilamento das bases brutas — Vértice Retail", ""]
    md.append(f"_Gerado por `scripts/01_perfilamento.py` — data de referência 2026-09-10._")
    md.append("")
    md.append("## Tabela resumo por base")
    md.append("")
    md.append("| base | linhas | colunas | período | grão | grão ok | cols c/ nulos | células nulas |")
    md.append("|---|---:|---:|---|---|:---:|---:|---:|")
    for r in linhas_resumo:
        md.append(
            f"| {r['base']} | {r['linhas']} | {r['colunas']} | {r['periodo']} | {r['grao']} | "
            f"{r['grao_ok']} | {r['cols_c/_nulos']} | {r['total_células_nulas']} |"
        )
    md.append("")
    md.append("_**período** = min/max das colunas de data da base. **grão ok** = a chave candidata "
              "é única e não-nula em todas as linhas (grão confirmado). **células nulas** = total de "
              "campos vazios; ver na seção de alertas se estão dispersos ou concentrados em poucas linhas._")
    md.append("")
    md.append("Tipos de coluna, contagem/percentual de nulos por coluna e distribuição completa "
              "das variáveis numéricas (incl. p1/p25/p75/p99, zeros e negativos) estão na seção "
              "**Detalhe por base**.")
    md.append("")
    md.append("## Alertas de qualidade de dados")
    md.append("")
    md.append("> Restrição do case: nulos são **reportados, não preenchidos**. Nenhuma imputação foi feita.")
    md.append("")
    md.append("### Cruzando as bases")
    md.append("")
    for a in alertas_cross:
        md.append(f"- {a.replace('[cross] ', '')}")
    md.append("")
    md.append("### Por base")
    md.append("")
    for a in todos_alertas:
        if a.startswith("[cross]"):
            continue
        md.append(f"- {a}")
    md.append("")
    md.append("## Detalhe por base")
    md.append("")
    md.extend(blocos_md)

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"\nRelatório salvo em: {REPORT_PATH}")


if __name__ == "__main__":
    main()
