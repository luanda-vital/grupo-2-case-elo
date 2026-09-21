"""
comum_hipoteses.py — utilitários compartilhados pelos scripts da Fase 2.4
(`scripts/03_teste_hipoteses_*.py`).

Por que existe: as hipóteses precisam usar exatamente as mesmas definições
(receita realizada, janela de vendas, meses de pico, premissas de custo de
devolução, régua de consistência de clientes). Centralizar aqui evita que dois
scripts cheguem a números diferentes para a mesma coisa.

Cada script de hipótese grava o próprio log em
`outputs/03_teste_hipoteses/<nome>.txt` e as tabelas em
`outputs/03_teste_hipoteses/<nome>__<tabela>.csv`. É desses arquivos que saem os
números citados em `reports/03_teste_hipoteses.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)

RAIZ = Path(__file__).resolve().parents[1]
PROCESSED_DIR = RAIZ / "data" / "processed"
OUT_DIR = RAIZ / "outputs" / "03_teste_hipoteses"
# Fase 2.4-op (rodada operacional): mesmos helpers, outra pasta de saída.
OUT_DIR_OP = RAIZ / "outputs" / "04_teste_hipoteses_operacional"
# Fase 2.4-final (rodada 3, sem viés de hipótese): mesmos helpers, outra pasta.
OUT_DIR_05 = RAIZ / "outputs" / "05_alavanca_definitiva"

# Janela de vendas (premissa da Fase 2.2): cruzamentos com receita/margem ficam
# restritos a este intervalo. JANELA_FIM_DIA é a data (sem hora) do último dia.
JANELA_INI = pd.Timestamp("2023-01-01")
JANELA_FIM_DIA = pd.Timestamp("2024-01-26")
ALPHA = 0.05

# ---------------------------------------------------------------------------
# PREMISSAS DE CUSTO DE DEVOLUÇÃO — não existem na base. Declaradas aqui e usadas
# igualmente por H9 e H3a. Precisam de validação do Davi / do cliente.
# ---------------------------------------------------------------------------
PREMISSAS_DEVOLUCAO = """\
PREMISSAS DE DEVOLUÇÃO (declaradas; a base não tem custo de devolução):
  P1 (piso)    — o item devolvido tem a receita estornada integralmente, o produto
                 volta ao estoque pelo custo (CMV recuperado) e não há frete reverso.
                 Resultado realizado do item = −custo_frete (só o frete de ida se perde).
  P2 (central) — P1 + frete reverso por devolução igual ao frete médio de ida dos
                 itens aprovados com frete > 0 + perda integral do CMV quando o motivo
                 é 'Produto com defeito' (produto não revendável).
  Nenhum cenário inclui custo de manuseio/recondicionamento nem comissão estornada."""


# ------------------------------------------------------------------ leitura
def carregar_vendas() -> pd.DataFrame:
    v = pd.read_csv(PROCESSED_DIR / "vendas.csv", parse_dates=["data_pedido"])
    # astype(bool) numa string "False" daria True — por isso só aceita bool nativo.
    for col in ("devolvido", "pagamento_aprovado"):
        if v[col].dtype != bool:
            raise TypeError(f"vendas.{col} não veio como bool (veio {v[col].dtype})")
    v["mes"] = v["data_pedido"].dt.to_period("M")
    return v


def carregar_marketing() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "marketing.csv", parse_dates=["data_inicio", "data_fim"])


def carregar_clientes() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "clientes.csv", parse_dates=["data_cadastro"])


def carregar_atendimento() -> pd.DataFrame:
    return pd.read_csv(
        PROCESSED_DIR / "atendimento.csv", parse_dates=["data_abertura", "data_fechamento"]
    )


def carregar_estoque() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "estoque.csv")


# ------------------------------------------------------------------- saída
def fmt_p(p: float) -> str:
    if pd.isna(p):
        return "n/a"
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


class Saida:
    """Imprime no console e guarda tudo para gravar em `out_dir` (padrão: a pasta da Fase 2.4)."""

    def __init__(self, nome: str, out_dir: Path = OUT_DIR):
        self.nome = nome
        self.out_dir = out_dir
        self.linhas: list[str] = []
        out_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self, texto: object = "") -> None:
        print(texto)
        self.linhas.append(str(texto))

    def secao(self, titulo: str) -> None:
        self("")
        self("=" * 96)
        self(titulo)
        self("=" * 96)

    def tabela(self, df: pd.DataFrame | pd.Series, nome_csv: str | None = None, casas: int = 2) -> None:
        if isinstance(df, pd.Series):
            df = df.to_frame()
        if nome_csv:
            df.to_csv(self.out_dir / f"{self.nome}__{nome_csv}.csv", encoding="utf-8")
        # Coluna a coluna por posição: rótulos booleanos (crosstab False/True) não podem virar máscara.
        cols = []
        for i, c in enumerate(df.columns):
            col = df.iloc[:, i]
            if "p_valor" in str(c):
                col = col.map(fmt_p)
            elif pd.api.types.is_numeric_dtype(col) and not pd.api.types.is_bool_dtype(col):
                col = col.round(casas)
            cols.append(col)
        exib = pd.concat(cols, axis=1)
        exib.columns = df.columns
        self(exib.to_string())

    def salvar(self) -> None:
        caminho = self.out_dir / f"{self.nome}.txt"
        caminho.write_text("\n".join(self.linhas) + "\n", encoding="utf-8")
        print(f"\n[log salvo em {caminho.relative_to(RAIZ).as_posix()}]")


# ------------------------------------------------------------- agregações
def agregados(df: pd.DataFrame, por) -> pd.DataFrame:
    """Soma dos componentes de margem por grupo + razões (soma/soma, nunca média de razões)."""
    g = df.groupby(por, observed=True).agg(
        itens=("order_id", "size"),
        receita_bruta=("receita_bruta", "sum"),
        desconto=("desconto_reais", "sum"),
        receita_liquida=("receita_liquida", "sum"),
        cmv=("custo_produto", "sum"),
        frete=("custo_frete", "sum"),
        margem=("margem_contribuicao", "sum"),
    )
    g["ticket"] = g["receita_liquida"] / g["itens"]
    g["margem_%RL"] = g["margem"] / g["receita_liquida"] * 100
    # Ponte aditiva sobre a receita bruta: margem/RB = 1 − desconto/RB − CMV/RB − frete/RB
    for c in ("desconto", "cmv", "frete", "margem"):
        g[f"{c}_%RB"] = g[c] / g["receita_bruta"] * 100
    return g


def agregados_total(df: pd.DataFrame) -> pd.Series:
    return agregados(df.assign(_total="total"), "_total").iloc[0]


def meses_de_pico(itens_mensais: pd.Series, fator: float = 1.5) -> tuple[list, float]:
    """Meses cujo volume de itens passa de `fator` × a mediana mensal (regra usada em H0 e H1)."""
    mediana = float(itens_mensais.median())
    return list(itens_mensais.index[itens_mensais > fator * mediana]), mediana


# --------------------------------------------------------------- estatística
def wilson(k, n, z: float = 1.96):
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    p = k / n
    den = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / den
    meia = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return centro - meia, centro + meia


def tabela_taxa(df: pd.DataFrame, grupo, flag: str) -> pd.DataFrame:
    g = df.groupby(grupo, observed=True)[flag].agg(n="size", eventos="sum")
    g["taxa_%"] = g["eventos"] / g["n"] * 100
    lo, hi = wilson(g["eventos"].to_numpy(), g["n"].to_numpy())
    g["ic95_inf_%"] = lo * 100
    g["ic95_sup_%"] = hi * 100
    return g


def homogeneidade(df: pd.DataFrame, grupo, flag: str) -> dict:
    """Qui-quadrado de homogeneidade da taxa `flag` entre os grupos + tamanho do efeito."""
    chave = [df[g] for g in grupo] if isinstance(grupo, list) else df[grupo]
    ct = pd.crosstab(chave, df[flag])
    taxa = df.groupby(grupo, observed=True)[flag].mean() * 100
    base = {
        "corte": grupo if isinstance(grupo, str) else "×".join(grupo),
        "grupos": int(ct.shape[0]),
        "taxa_min_%": taxa.min(),
        "grupo_min": str(taxa.idxmin()),
        "taxa_max_%": taxa.max(),
        "grupo_max": str(taxa.idxmax()),
        "amplitude_pp": taxa.max() - taxa.min(),
    }
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return {**base, "chi2": np.nan, "gl": np.nan, "p_valor": np.nan, "v_cramer": np.nan}
    chi2, p, gl, _ = stats.chi2_contingency(ct)
    n = ct.to_numpy().sum()
    return {**base, "chi2": chi2, "gl": gl, "p_valor": p,
            "v_cramer": float(np.sqrt(chi2 / (n * (min(ct.shape) - 1))))}


def tendencia(serie: pd.Series) -> dict:
    """Regressão linear valor ~ mês. Com PeriodIndex, x = mês real (meses retirados não são 'colados')."""
    if isinstance(serie.index, pd.PeriodIndex):
        x = np.array([p.ordinal for p in serie.index], dtype=float)
    else:
        x = np.arange(len(serie), dtype=float)
    x = x - x.min()
    y = serie.to_numpy(dtype=float)
    r = stats.linregress(x, y)
    media = float(y.mean())
    return {
        "n_meses": len(y),
        "media": media,
        "inclinacao_por_mes": r.slope,
        "inclinacao_%_da_media": r.slope / media * 100 if media else np.nan,
        "p_valor": r.pvalue,
        "r2": r.rvalue**2,
    }


# ------------------------------------------------------- premissas / réguas
def frete_reverso_premissa(v: pd.DataFrame) -> float:
    a = v[v["pagamento_aprovado"] & (v["custo_frete"] > 0)]
    return float(a["custo_frete"].mean())


def resultado_realizado(df: pd.DataFrame, cenario: str, frete_rev: float) -> pd.Series:
    """Resultado de cada item: margem reportada se não devolvido; se devolvido, conforme P1/P2."""
    mc = df["margem_contribuicao"]
    if cenario == "reportada":
        return mc.copy()
    if cenario == "P1":
        res_dev = -df["custo_frete"]
    elif cenario == "P2":
        defeito = df["motivo_devolucao"].eq("Produto com defeito")
        res_dev = -df["custo_frete"] - frete_rev - df["custo_produto"].where(defeito, 0.0)
    else:
        raise ValueError(cenario)
    return mc.where(~df["devolvido"], res_dev)


# ------------------------------------------------------ marketing (H2 e CAC)
LIM_BAIXO, LIM_ALTO = 0.8, 1.2


def no_intervalo(m: pd.DataFrame, ini: pd.Timestamp, fim: pd.Timestamp, col: str) -> pd.Series:
    """Parcela de `col` de cada campanha que cai em [ini, fim] (datas inclusive).

    PREMISSA (H2): o valor da campanha se distribui uniformemente por dia entre
    data_inicio e data_fim (pro rata)."""
    dur = (m["data_fim"] - m["data_inicio"]).dt.days + 1
    dias = ((m["data_fim"].clip(upper=fim) - m["data_inicio"].clip(lower=ini)).dt.days + 1).clip(lower=0)
    return m[col] * dias / dur


def indice(inv: pd.Series, mg: pd.Series) -> pd.DataFrame:
    """Índice da H2: participação na margem ÷ participação no investimento."""
    t = pd.DataFrame({"investimento": inv, "margem": mg}).fillna(0.0)
    t["part_invest_%"] = t["investimento"] / t["investimento"].sum() * 100
    t["part_margem_%"] = t["margem"] / t["margem"].sum() * 100
    t["indice"] = t["part_margem_%"] / t["part_invest_%"]
    return t


def classe(x: float) -> str:
    return "abaixo" if x < LIM_BAIXO else ("acima" if x > LIM_ALTO else "proporcional")


def correlacoes_painel(x_gp: pd.DataFrame, y_gp: pd.DataFrame) -> dict:
    """Correlação num painel grupo × período (linhas = grupo, colunas = período).

    Total (Spearman), com efeito fixo de grupo e com efeito fixo de grupo E de
    período (Pearson, painel balanceado) — o corte anti-espúrio usado na H2."""
    x = x_gp.loc[y_gp.index, y_gp.columns]
    rp = stats.spearmanr(x.to_numpy().ravel(), y_gp.to_numpy().ravel())
    xd, yd = x.sub(x.mean(axis=1), axis=0), y_gp.sub(y_gp.mean(axis=1), axis=0)
    rw = stats.pearsonr(xd.to_numpy().ravel(), yd.to_numpy().ravel())
    x2, y2 = xd.sub(xd.mean(axis=0), axis=1), yd.sub(yd.mean(axis=0), axis=1)
    r2 = stats.pearsonr(x2.to_numpy().ravel(), y2.to_numpy().ravel())
    return {"spearman_total": rp.statistic, "p_total": rp.pvalue,
            "pearson_ef_grupo": rw.statistic, "p_valor_ef_grupo": rw.pvalue,
            "pearson_ef_grupo_e_periodo": r2.statistic, "p_valor_ef_grupo_e_periodo": r2.pvalue}


def consistencia_clientes(v: pd.DataFrame, c: pd.DataFrame) -> pd.DataFrame:
    """Por cliente comprador: pedidos em vendas × total_pedidos_historico e 1ª compra × cadastro."""
    ped = v.groupby("customer_id").agg(
        pedidos_vendas=("order_id", "size"), primeira_compra=("data_pedido", "min")
    )
    cc = c.set_index("customer_id")[
        ["total_pedidos_historico", "data_cadastro", "segmento_rfm", "nivel_fidelidade"]
    ]
    d = ped.join(cc, how="left")
    d["consistente_pedidos"] = d["pedidos_vendas"] <= d["total_pedidos_historico"]
    d["compra_antes_cadastro"] = d["primeira_compra"] < d["data_cadastro"]
    return d
