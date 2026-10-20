"""Todas as contas do painel ficam aqui, só com pandas.

Separado do app para dar pra testar sem abrir o Streamlit.
"""
from __future__ import annotations

import pandas as pd

COLUNAS = ["data", "descricao", "categoria", "tipo", "valor"]
TIPOS = {"Receita", "Despesa", "Investimento"}
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def rotulo_mes(ts: pd.Timestamp) -> str:
    return f"{MESES_PT[ts.month - 1]}/{str(ts.year)[2:]}"


# ---------------------------------------------------------------- carga
def preparar_transacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Valida e padroniza o extrato (o de exemplo ou um CSV enviado)."""
    df = df.rename(columns=str.strip).rename(columns=str.lower)
    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        raise ValueError(f"O CSV precisa das colunas {COLUNAS}. Faltou: {faltando}")

    df = df[COLUNAS].copy()
    df["data"] = pd.to_datetime(df["data"], dayfirst=False, errors="coerce")
    if not pd.api.types.is_numeric_dtype(df["valor"]):
        # aceita "1.234,56" no padrão brasileiro
        txt = df["valor"].astype(str).str.strip()
        br = txt.str.contains(",")
        txt[br] = txt[br].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df["valor"] = pd.to_numeric(txt, errors="coerce")
    df["tipo"] = df["tipo"].astype(str).str.strip().str.capitalize()
    df = df.dropna(subset=["data", "valor"])
    df = df[df["tipo"].isin(TIPOS)]

    # despesas e investimentos sempre negativos, receitas sempre positivas
    df["valor"] = df["valor"].abs().where(df["tipo"] == "Receita", -df["valor"].abs())
    df["mes"] = df["data"].dt.to_period("M").dt.to_timestamp()
    return df.sort_values("data").reset_index(drop=True)


# ---------------------------------------------------------------- visão geral
def _soma(df, tipo):
    return df.loc[df["tipo"] == tipo, "valor"].abs().sum()


def resumo(df: pd.DataFrame) -> dict:
    receitas, despesas, investido = _soma(df, "Receita"), _soma(df, "Despesa"), _soma(df, "Investimento")
    return {
        "receitas": receitas,
        "despesas": despesas,
        "investido": investido,
        "saldo": receitas - despesas - investido,
        "taxa_poupanca": (receitas - despesas) / receitas if receitas else 0.0,
    }


def mensal(df: pd.DataFrame) -> pd.DataFrame:
    t = (df.assign(v=df["valor"].abs())
           .pivot_table(index="mes", columns="tipo", values="v", aggfunc="sum", fill_value=0.0))
    for c in TIPOS:
        if c not in t.columns:
            t[c] = 0.0
    t = t[["Receita", "Despesa", "Investimento"]]
    t["Saldo"] = t["Receita"] - t["Despesa"] - t["Investimento"]
    return t.sort_index()


def variacao_despesas_ultimo_mes(df: pd.DataFrame) -> float | None:
    m = mensal(df)["Despesa"]
    if len(m) < 2 or m.iloc[-2] == 0:
        return None
    return m.iloc[-1] / m.iloc[-2] - 1


def saldo_acumulado(df: pd.DataFrame) -> pd.Series:
    return df.groupby("data")["valor"].sum().cumsum()


# ---------------------------------------------------------------- categorias
def despesas(df):
    return df[df["tipo"] == "Despesa"].assign(gasto=lambda d: d["valor"].abs())


def por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    d = despesas(df).groupby("categoria")["gasto"].sum().sort_values(ascending=False).to_frame("total")
    d["percentual"] = d["total"] / d["total"].sum() if len(d) else 0.0
    return d


def evolucao_top(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    top = por_categoria(df).head(n).index
    d = despesas(df)
    d = d[d["categoria"].isin(top)]
    return d.pivot_table(index="mes", columns="categoria", values="gasto", aggfunc="sum", fill_value=0.0)[list(top)]


def orcamento(df_completo: pd.DataFrame, mes: pd.Timestamp, folga: float = 0.10) -> pd.DataFrame:
    """Limite de cada categoria = média dos 3 meses anteriores + folga (arredondado de 10 em 10)."""
    d = despesas(df_completo)
    por_mes = d.pivot_table(index="mes", columns="categoria", values="gasto", aggfunc="sum", fill_value=0.0)
    anteriores = por_mes[por_mes.index < mes].tail(3)
    if anteriores.empty:
        return pd.DataFrame(columns=["limite", "gasto", "uso", "status"])
    limite = (anteriores.mean() * (1 + folga) / 10).round() * 10
    gasto = por_mes.loc[mes] if mes in por_mes.index else pd.Series(0.0, index=por_mes.columns)
    t = pd.DataFrame({"limite": limite, "gasto": gasto.reindex(limite.index, fill_value=0.0)})
    t = t[t["limite"] > 0]
    t["uso"] = t["gasto"] / t["limite"]
    t["status"] = pd.cut(t["uso"], [-1, 0.8, 1.0, float("inf")], labels=["OK", "Atenção", "Estourou"])
    return t.sort_values("uso", ascending=False)


def maiores_gastos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return despesas(df).nlargest(n, "gasto")[["data", "descricao", "categoria", "gasto"]]


# ---------------------------------------------------------------- mercado
def acumulado(taxas_pct: pd.Series) -> float:
    return float((1 + taxas_pct / 100).prod() - 1)


def simulacoes(aportes: pd.Series, ind: pd.DataFrame) -> pd.DataFrame:
    """Quanto o dinheiro investido teria virado em cada aplicação.

    Cada mês: saldo = saldo anterior x (1 + taxa do mês) + aporte do mês.
    """
    ind = ind.reindex(aportes.index)
    cenarios = {
        "Dinheiro parado": pd.Series(0.0, index=aportes.index),
        "Poupança": ind["poupanca_pct"].fillna(0),
        "100% do CDI": ind["cdi_pct"].fillna(0),
        "Só repor a inflação": ind["ipca_pct"].fillna(0),
    }
    saida = {}
    for nome, taxa in cenarios.items():
        saldo, serie = 0.0, []
        for mes in aportes.index:
            saldo = saldo * (1 + taxa[mes] / 100) + aportes[mes]
            serie.append(saldo)
        saida[nome] = serie
    return pd.DataFrame(saida, index=aportes.index)


def gastos_corrigidos(desp_mensal: pd.Series, ipca_pct: pd.Series) -> float:
    """Leva cada mês de gasto para valores do último mês, usando o IPCA dos meses seguintes."""
    fator = (1 + ipca_pct.reindex(desp_mensal.index).fillna(0) / 100)
    # inflação acumulada DEPOIS de cada mês
    depois = fator[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    return float((desp_mensal * depois).sum())


def indice_gastos_vs_ipca(desp_mensal: pd.Series, ipca_pct: pd.Series) -> pd.DataFrame:
    mm3 = desp_mensal.rolling(3, min_periods=1).mean()
    gastos = mm3 / mm3.iloc[0] * 100
    ipca = (1 + ipca_pct.reindex(desp_mensal.index).fillna(0) / 100).cumprod()
    ipca = ipca / ipca.iloc[0] * 100
    return pd.DataFrame({"Seus gastos (média de 3 meses)": gastos, "IPCA": ipca})


def gastos_em_dolar(desp_mensal: pd.Series, dolar: pd.Series) -> pd.DataFrame:
    cot = dolar.reindex(desp_mensal.index)
    return pd.DataFrame({"usd": desp_mensal / cot, "cotacao": cot})
