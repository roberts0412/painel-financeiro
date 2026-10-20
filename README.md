# Painel Financeiro 💰

**[Ver o painel funcionando](https://painel-financeiro-robert.streamlit.app)**

Um painel pra acompanhar finanças pessoais: quanto entrou, quanto saiu, onde o dinheiro foi parar e se valeu mais a pena deixar parado ou investir. Fiz em Python com Streamlit e Plotly, e ele puxa os indicadores (CDI, IPCA, poupança e dólar) direto da API pública do Banco Central.

## O que tem nele

**Visão Geral**: receitas, despesas, quanto foi investido, quanto sobrou e a taxa de poupança. Tem também o gráfico de entradas e saídas mês a mês, a evolução do saldo e as categorias que mais pesam.

**Categorias & Orçamento**: despesas por categoria, como as 5 maiores evoluíram e um orçamento automático. O limite de cada categoria é a média dos 3 meses anteriores + 10%, e a tabela mostra o que está ok, o que pede atenção e o que estourou. Tem ainda a lista dos maiores gastos.

**Mercado & Investimentos**: inflação e CDI do período, quanto o dinheiro guardado teria rendido na poupança, no CDI ou só acompanhando a inflação, seus gastos comparados com o IPCA e quanto você gastou convertido em dólar.

Na barra lateral dá pra mudar o período, filtrar categorias e subir o seu próprio extrato.

## Como rodar

Precisa do Python 3.10 ou mais novo.

```bash
pip install -r requirements.txt
streamlit run app.py
```

O navegador abre sozinho em `http://localhost:8501`.

## Usando o seu extrato

Monte um CSV com estas colunas:

| data | descricao | categoria | tipo | valor |
|---|---|---|---|---|
| 2026-09-05 | SALARIO EMPRESA | Salário | Receita | 5320.00 |
| 2026-09-10 | ALUGUEL APTO | Moradia | Despesa | -1250.00 |
| 2026-09-06 | APLICACAO CDB | Investimento | Investimento | -700.00 |

- `tipo` precisa ser **Receita**, **Despesa** ou **Investimento**
- o valor pode vir com ou sem sinal, e também no formato `1.234,56`
- separador `,` ou `;`, tanto faz

Depois é só arrastar o arquivo na barra lateral.

## Arquivos

```
app.py               o painel (telas e gráficos)
calculos.py          todas as contas, só com pandas
bcb.py               busca os indicadores no Banco Central
gerar_dados.py       gera o extrato de exemplo (fictício)
dados/
  transacoes.csv     extrato de exemplo (criado sozinho na 1ª execução)
  indicadores_bcb.csv  cópia dos indicadores, usada se a API estiver fora
```

Pra atualizar a cópia dos indicadores: `python bcb.py`

## Publicar de graça

1. Suba a pasta num repositório no GitHub
2. Entre em [share.streamlit.io](https://share.streamlit.io), conecte o GitHub e escolha o repositório
3. Arquivo principal: `app.py`

Em poucos minutos ele ganha um link público.

> As transações de exemplo são inventadas. Não suba o seu extrato de verdade para um repositório público.
