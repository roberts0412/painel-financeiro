"""Gera um extrato fictício de 12 meses em dados/transacoes.csv.

Rode de novo quando quiser outra base de exemplo:
    python gerar_dados.py
"""
from datetime import date, timedelta
from pathlib import Path
import csv
import random

SEMENTE = 42
INICIO = date(2025, 10, 1)
MESES = 12
SAIDA = Path(__file__).parent / "dados" / "transacoes.csv"

# (descrição, categoria, valor mínimo, valor máximo, vezes por mês)
VARIAVEIS = [
    ("MERCADO EXTRA", "Mercado", 60, 260, 3),
    ("PADARIA", "Mercado", 12, 45, 3),
    ("IFOOD", "Alimentação", 35, 95, 3),
    ("RESTAURANTE", "Alimentação", 40, 120, 1),
    ("UBER", "Transporte", 15, 48, 6),
    ("POSTO SHELL", "Transporte", 150, 260, 2),
    ("FARMACIA", "Saúde", 25, 140, 1),
    ("CINEMA", "Lazer", 40, 90, 1),
    ("BAR", "Lazer", 60, 180, 1),
    ("MERCADO LIVRE", "Compras", 40, 300, 1),
    ("SHOPEE", "Compras", 20, 120, 1),
    ("DIVERSOS", "Outros", 10, 70, 1),
]

FIXAS = [  # dia, descrição, categoria, valor
    (10, "ALUGUEL APTO", "Moradia", 1250.00),
    (10, "CONDOMINIO", "Moradia", 320.00),
    (12, "ENEL ENERGIA", "Contas", None),      # varia um pouco
    (15, "VIVO INTERNET", "Contas", 119.90),
    (15, "SABESP", "Contas", None),
    (8, "NETFLIX", "Assinaturas", 44.90),
    (8, "SPOTIFY", "Assinaturas", 21.90),
    (20, "ACADEMIA", "Assinaturas", 91.90),
]


def dia_valido(ano, mes, dia):
    while True:
        try:
            return date(ano, mes, dia)
        except ValueError:
            dia -= 1


def main():
    rnd = random.Random(SEMENTE)
    linhas = []

    for i in range(MESES):
        ano = INICIO.year + (INICIO.month - 1 + i) // 12
        mes = (INICIO.month - 1 + i) % 12 + 1
        salario = 4850.00 if i < 7 else 5320.00          # reajuste em maio
        linhas.append((dia_valido(ano, mes, 5), "SALARIO EMPRESA", "Salário", "Receita", salario))

        if rnd.random() < 0.45:                            # freela de vez em quando
            linhas.append((dia_valido(ano, mes, rnd.randint(12, 26)), "PIX RECEBIDO FREELA", "Freela",
                           "Receita", round(rnd.uniform(600, 1600), 2)))
        if mes == 12:
            linhas.append((dia_valido(ano, mes, 18), "13o SALARIO", "Salário", "Receita", 2400.00))

        for dia, desc, cat, valor in FIXAS:
            if valor is None:
                valor = round(rnd.uniform(110, 210) if "ENEL" in desc else rnd.uniform(60, 95), 2)
            if mes in (1,) and desc == "ALUGUEL APTO":
                linhas.append((dia_valido(ano, mes, 25), "IPTU", "Moradia", "Despesa", -620.00))
            linhas.append((dia_valido(ano, mes, dia), desc, cat, "Despesa", -valor))

        for desc, cat, vmin, vmax, vezes in VARIAVEIS:
            n = max(0, vezes + rnd.choice([-1, 0, 0, 1]))
            for _ in range(n):
                d = dia_valido(ano, mes, rnd.randint(1, 28))
                linhas.append((d, desc, cat, "Despesa", -round(rnd.uniform(vmin, vmax), 2)))

        if mes in (11, 12, 7):                             # Black Friday, Natal, férias
            linhas.append((dia_valido(ano, mes, 24), "COMPRA PARCELADA", "Compras", "Despesa",
                           -round(rnd.uniform(400, 900), 2)))
        if mes == 3:
            linhas.append((dia_valido(ano, mes, 14), "OFICINA MECANICA", "Transporte", "Despesa", -640.00))

        aporte = rnd.choice([300, 400, 500, 600, 700, 800])
        linhas.append((dia_valido(ano, mes, 6), "APLICACAO CDB", "Investimento", "Investimento", -float(aporte)))

    linhas.sort(key=lambda l: l[0])
    SAIDA.parent.mkdir(exist_ok=True)
    with SAIDA.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "descricao", "categoria", "tipo", "valor"])
        for d, desc, cat, tipo, valor in linhas:
            w.writerow([d.isoformat(), desc, cat, tipo, f"{valor:.2f}"])
    print(f"{len(linhas)} transações salvas em {SAIDA}")


if __name__ == "__main__":
    main()
