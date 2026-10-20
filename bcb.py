"""Indicadores do Banco Central (API pública do SGS).

Tenta buscar online; se não der (sem internet, API fora), usa a cópia em
dados/indicadores_bcb.csv. Rode "python bcb.py" para atualizar essa cópia.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

ARQUIVO = Path(__file__).parent / "dados" / "indicadores_bcb.csv"
SERIES = {               # código SGS -> coluna
    4391: "cdi_pct",     # CDI acumulado no mês (% a.m.)
    433: "ipca_pct",     # IPCA (% a.m.)
    196: "poupanca_pct", # Poupança - rentabilidade no período (% a.m.)
    3698: "dolar_medio", # Dólar venda - média mensal (R$)
}
URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados"


def _serie(cod: int, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.Series:
    r = requests.get(URL.format(cod=cod), timeout=10, params={
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    })
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["data"] = pd.to_datetime(df["data"], dayfirst=True)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["mes"] = df["data"].dt.to_period("M").dt.to_timestamp()
    return df.groupby("mes")["valor"].first()


def ler_copia() -> pd.DataFrame:
    return pd.read_csv(ARQUIVO, parse_dates=["mes"]).set_index("mes")


def carregar(inicio: pd.Timestamp, fim: pd.Timestamp) -> tuple[pd.DataFrame, str]:
    """Retorna (indicadores mensais, de onde vieram)."""
    copia = ler_copia()
    try:
        online = pd.DataFrame({col: _serie(cod, inicio, fim) for cod, col in SERIES.items()})
        juntos = online.combine_first(copia)  # online manda; cópia tapa buracos
        return juntos.sort_index(), "API do Banco Central (online)"
    except Exception:
        return copia, "cópia salva dos dados do Banco Central"


if __name__ == "__main__":
    fim = pd.Timestamp.today()
    inicio = (fim - pd.DateOffset(months=24)).replace(day=1)
    df = pd.DataFrame({col: _serie(cod, inicio, fim) for cod, col in SERIES.items()})
    df.index.name = "mes"
    df.dropna(how="all").to_csv(ARQUIVO, date_format="%Y-%m-%d")
    print(f"Indicadores salvos em {ARQUIVO}:\n{df.tail()}")
