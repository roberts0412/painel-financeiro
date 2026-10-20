"""Painel Financeiro pessoal em Streamlit.

Rodar:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import bcb
import calculos as c

PASTA = Path(__file__).parent
CORES = {"receita": "#0B7A55", "despesa": "#C23B2A", "invest": "#2D5BD0",
         "ambar": "#A86F02", "neutra": "#8A9792", "texto": "#5A6A64"}

st.set_page_config(page_title="Painel Financeiro", page_icon="💰", layout="wide")


# ---------------------------------------------------------------- formatação
def brl(v: float, casas: int = 2) -> str:
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def pct(v: float, casas: int = 1) -> str:
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def layout(fig: go.Figure, altura: int = 340, **kw) -> go.Figure:
    opcoes = dict(
        height=altura, margin=dict(l=8, r=8, t=30, b=8),
        legend=dict(orientation="h", y=1.12, x=0),
        hovermode="x unified", separators=",.",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    opcoes.update(kw)  # o que vier de cada gráfico tem prioridade
    fig.update_layout(**opcoes)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)", zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


REAIS = dict(tickprefix="R$ ", tickformat=",.0f")


# ---------------------------------------------------------------- dados
@st.cache_data
def ler_exemplo() -> pd.DataFrame:
    arquivo = PASTA / "dados" / "transacoes.csv"
    if not arquivo.exists():  # primeira execução: cria o extrato de exemplo
        import gerar_dados
        gerar_dados.main()
    return c.preparar_transacoes(pd.read_csv(arquivo))


@st.cache_data(ttl=60 * 60 * 12, show_spinner="Buscando indicadores no Banco Central…")
def ler_indicadores(inicio, fim):
    return bcb.carregar(inicio, fim)


with st.sidebar:
    st.header("💰 Painel Financeiro")
    enviado = st.file_uploader(
        "Usar meu próprio extrato (CSV)", type="csv",
        help="Colunas: data, descricao, categoria, tipo (Receita/Despesa/Investimento), valor",
    )
    if enviado:
        try:
            base = c.preparar_transacoes(pd.read_csv(enviado, sep=None, engine="python"))
            st.success(f"{len(base)} transações carregadas")
        except Exception as erro:
            st.error(f"Não consegui ler o arquivo: {erro}")
            st.stop()
    else:
        base = ler_exemplo()
        st.caption("Usando o extrato de exemplo (dados fictícios).")

    meses_disp = sorted(base["mes"].unique())
    rotulos = {m: c.rotulo_mes(pd.Timestamp(m)) for m in meses_disp}
    ini, fim = st.select_slider(
        "Período", options=meses_disp, value=(meses_disp[0], meses_disp[-1]),
        format_func=lambda m: rotulos[m],
    )
    categorias = sorted(base.loc[base["tipo"] == "Despesa", "categoria"].unique())
    escolhidas = st.multiselect("Categorias de despesa", categorias, default=categorias)

df = base[(base["mes"] >= ini) & (base["mes"] <= fim)]
df = df[(df["tipo"] != "Despesa") | df["categoria"].isin(escolhidas)]
if df.empty:
    st.warning("Nenhuma transação nesse filtro.")
    st.stop()

ind, origem_ind = ler_indicadores(pd.Timestamp(ini), pd.Timestamp(fim) + pd.offsets.MonthEnd(0))
mens = c.mensal(df)
eixo_mes = [c.rotulo_mes(m) for m in mens.index]

st.title("Painel Financeiro")
st.caption(f"{rotulos[ini]} a {rotulos[fim]} · {len(df)} transações")

aba1, aba2, aba3 = st.tabs(["📊 Visão Geral", "🗂️ Categorias & Orçamento", "📈 Mercado & Investimentos"])

# ================================================================ 1. VISÃO GERAL
with aba1:
    r = c.resumo(df)
    var = c.variacao_despesas_ultimo_mes(df)
    k = st.columns(5)
    k[0].metric("Receitas", brl(r["receitas"], 0))
    k[1].metric("Despesas", brl(r["despesas"], 0),
                delta=None if var is None else f"{pct(var)} no último mês", delta_color="inverse")
    k[2].metric("Investido", brl(r["investido"], 0))
    k[3].metric("Sobra em conta", brl(r["saldo"], 0))
    k[4].metric("Taxa de poupança", pct(r["taxa_poupanca"]),
                help="Quanto da receita não virou despesa: (receitas − despesas) ÷ receitas")

    esq, dir_ = st.columns([7, 5])
    with esq:
        st.subheader("Entradas e saídas por mês")
        fig = go.Figure([
            go.Bar(name="Receitas", x=eixo_mes, y=mens["Receita"], marker_color=CORES["receita"]),
            go.Bar(name="Despesas", x=eixo_mes, y=mens["Despesa"], marker_color=CORES["despesa"]),
            go.Bar(name="Investido", x=eixo_mes, y=mens["Investimento"], marker_color=CORES["invest"]),
        ])
        st.plotly_chart(layout(fig, 440, barmode="group", yaxis=REAIS))
    with dir_:
        st.subheader("Saldo em conta")
        acum = c.saldo_acumulado(df)
        fig = go.Figure(go.Scatter(x=acum.index, y=acum.values, mode="lines", line_shape="hv",
                                   fill="tozeroy", line_color=CORES["invest"], name="Saldo"))
        st.plotly_chart(layout(fig, 190, showlegend=False, yaxis=REAIS))

        st.subheader("Maiores categorias de despesa")
        top = c.por_categoria(df).head(5).iloc[::-1]
        fig = go.Figure(go.Bar(x=top["total"], y=top.index, orientation="h", marker_color=CORES["despesa"],
                               text=[pct(p) for p in top["percentual"]], textposition="outside",
                               cliponaxis=False))
        st.plotly_chart(layout(fig, 190, showlegend=False, hovermode="closest", xaxis=REAIS))

# ================================================================ 2. CATEGORIAS & ORÇAMENTO
with aba2:
    esq, dir_ = st.columns([4, 8])
    with esq:
        st.subheader("Despesas por categoria")
        cat = c.por_categoria(df).iloc[::-1]
        fig = go.Figure(go.Bar(x=cat["total"], y=cat.index, orientation="h", marker_color=CORES["despesa"],
                               text=[pct(p) for p in cat["percentual"]], textposition="outside",
                               cliponaxis=False))
        st.plotly_chart(layout(fig, 520, showlegend=False, hovermode="closest", xaxis=REAIS))
    with dir_:
        st.subheader("Evolução das 5 maiores categorias")
        evo = c.evolucao_top(df)
        paleta = [CORES["despesa"], CORES["invest"], CORES["ambar"], CORES["receita"], CORES["neutra"]]
        fig = go.Figure([go.Scatter(x=[c.rotulo_mes(m) for m in evo.index], y=evo[col], name=col,
                                    mode="lines+markers", line_color=paleta[i % 5])
                         for i, col in enumerate(evo.columns)])
        st.plotly_chart(layout(fig, 260, yaxis=REAIS))

        o1, o2 = st.columns(2)
        with o1:
            st.subheader("Orçamento x realizado")
            meses_orc = [m for m in meses_disp if ini <= m <= fim][1:]  # precisa de meses anteriores
            if not meses_orc:
                st.info("Escolha um período com pelo menos 2 meses para ver o orçamento.")
            else:
                mes_orc = st.selectbox("Mês", meses_orc[::-1], format_func=lambda m: rotulos[m])
                orc = c.orcamento(base[base["categoria"].isin(escolhidas) | (base["tipo"] != "Despesa")],
                                  pd.Timestamp(mes_orc))
                st.caption("Limite = média dos 3 meses anteriores + 10%")
                st.dataframe(
                    orc.reset_index().assign(
                        status=lambda t: t["status"].map({"OK": "🟢 OK", "Atenção": "🟡 Atenção",
                                                          "Estourou": "🔴 Estourou"}),
                        uso=lambda t: t["uso"] * 100),
                    hide_index=True,
                    column_config={
                        "categoria": "Categoria",
                        "limite": st.column_config.NumberColumn("Limite", format="R$ %.0f"),
                        "gasto": st.column_config.NumberColumn("Gasto", format="R$ %.0f"),
                        "uso": st.column_config.ProgressColumn("Uso", format="%.0f%%", min_value=0, max_value=150),
                        "status": "Situação",
                    },
                )
        with o2:
            st.subheader("Maiores gastos")
            sem_fixos = st.toggle("Esconder aluguel e condomínio", value=True)
            mg = df[~df["categoria"].eq("Moradia")] if sem_fixos else df
            st.dataframe(
                c.maiores_gastos(mg, 10).assign(data=lambda t: t["data"].dt.strftime("%d/%m/%y")),
                hide_index=True,
                column_config={
                    "data": "Data", "descricao": "Descrição", "categoria": "Categoria",
                    "gasto": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                },
            )

# ================================================================ 3. MERCADO & INVESTIMENTOS
with aba3:
    ind_p = ind.reindex(mens.index)
    if ind_p[["cdi_pct", "ipca_pct"]].isna().all().any():
        st.warning("Faltam indicadores do Banco Central para parte desse período; "
                   "rode 'python bcb.py' para atualizar a cópia local.")
    inflacao = c.acumulado(ind_p["ipca_pct"].dropna())
    cdi = c.acumulado(ind_p["cdi_pct"].dropna())
    ganho_real = (1 + cdi) / (1 + inflacao) - 1
    corrigido = c.gastos_corrigidos(mens["Despesa"], ind_p["ipca_pct"])

    k = st.columns(4)
    k[0].metric("Inflação no período", pct(inflacao, 2), help="IPCA acumulado")
    k[1].metric("CDI no período", pct(cdi, 2), help="100% do CDI acumulado")
    k[2].metric("Ganho real do CDI", pct(ganho_real, 2), help="Quanto o CDI rendeu acima da inflação")
    k[3].metric("Gastos em valores de hoje", brl(corrigido, 0),
                delta=f"+{brl(corrigido - mens['Despesa'].sum(), 0)} de inflação", delta_color="off")
    st.caption(f"Fonte dos indicadores: {origem_ind} · CDI (SGS 4391), IPCA (433), "
               f"Poupança (196), Dólar (3698)")

    sim = c.simulacoes(mens["Investimento"], ind_p)
    final = sim.iloc[-1]
    a, b = st.columns([7, 5])
    with a:
        st.subheader("E se o dinheiro guardado tivesse ido para…")
        texto = (f"Guardando {brl(final['Dinheiro parado'], 0)}, no CDI você teria "
                 f"{brl(final['100% do CDI'], 0)} (+{brl(final['100% do CDI'] - final['Dinheiro parado'], 0)})")
        st.caption(texto.replace("$", r"\$"))  # sem isso o Streamlit lê "$...$" como fórmula
        estilo = {"Dinheiro parado": (CORES["neutra"], "solid", 2), "Poupança": (CORES["ambar"], "solid", 2),
                  "100% do CDI": (CORES["receita"], "solid", 3.5), "Só repor a inflação": (CORES["despesa"], "dot", 2)}
        fig = go.Figure([go.Scatter(x=eixo_mes, y=sim[n], name=n, mode="lines+markers",
                                    line=dict(color=cor, dash=tr, width=w))
                         for n, (cor, tr, w) in estilo.items()])
        st.plotly_chart(layout(fig, 320, yaxis=REAIS))
    with b:
        st.subheader("Seus gastos x inflação (base 100)")
        vi = c.indice_gastos_vs_ipca(mens["Despesa"], ind_p["ipca_pct"])
        fig = go.Figure([
            go.Scatter(x=eixo_mes, y=vi.iloc[:, 0], name=vi.columns[0], mode="lines+markers", line_color=CORES["despesa"]),
            go.Scatter(x=eixo_mes, y=vi["IPCA"], name="IPCA", mode="lines+markers", line_color=CORES["neutra"]),
        ])
        fig.add_hline(y=100, line_dash="dot", line_color=CORES["neutra"])
        st.plotly_chart(layout(fig, 345))

    a, b = st.columns(2)
    with a:
        st.subheader("Juros e inflação mês a mês")
        fig = go.Figure([
            go.Bar(name="CDI", x=eixo_mes, y=ind_p["cdi_pct"], marker_color=CORES["receita"]),
            go.Bar(name="IPCA", x=eixo_mes, y=ind_p["ipca_pct"], marker_color=CORES["despesa"]),
            go.Bar(name="Poupança", x=eixo_mes, y=ind_p["poupanca_pct"], marker_color=CORES["ambar"]),
        ])
        st.plotly_chart(layout(fig, 300, barmode="group", yaxis=dict(ticksuffix="%")))
    with b:
        st.subheader("Gastos em dólar")
        usd = c.gastos_em_dolar(mens["Despesa"], ind_p["dolar_medio"])
        fig = go.Figure([
            go.Bar(name="Despesas em US$", x=eixo_mes, y=usd["usd"], marker_color=CORES["invest"]),
            go.Scatter(name="Dólar médio (R$)", x=eixo_mes, y=usd["cotacao"], yaxis="y2",
                       mode="lines+markers", line_color=CORES["texto"]),
        ])
        st.plotly_chart(layout(fig, 300, yaxis=dict(tickprefix="US$ ", tickformat=",.0f"),
                               yaxis2=dict(overlaying="y", side="right", showgrid=False, tickprefix="R$ ")))

st.caption("Transações de exemplo são fictícias. Indicadores: SGS / Banco Central do Brasil.")
