import calendar

import duckdb
import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ANO_INICIAL = 2000
ANO_FINAL = 2025

COBERTURA_MENSAL_MINIMA = 0.80


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


PARES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
    / "horarios"
)


REDE_FILE = (
    ANNUAL_DIR
    / "rede_tendencia_estacao_ano.parquet"
)


SAIDA_MENSAL = (
    ANNUAL_DIR
    / "cobertura_mensal_rede_tendencia.parquet"
)


SAIDA_MAXIMAS = (
    ANNUAL_DIR
    / "maximas_anuais_estacoes_tendencia.parquet"
)


SAIDA_ESTACOES = (
    TABLES_DIR
    / "rede_extremos_anuais_estacoes.csv"
)


SAIDA_PAINEIS = (
    TABLES_DIR
    / "paineis_fixos_extremos_anuais.csv"
)


SAIDA_MAXIMAS_CSV = (
    TABLES_DIR
    / "maximas_anuais_estacoes_tendencia.csv"
)


# ==========================================================
# FUNÇÕES
# ==========================================================

def sql_path(caminho):

    return str(
        caminho.resolve()
    ).replace(
        "'",
        "''",
    )


def maior_sequencia(
    anos,
):

    anos = sorted(
        set(
            int(x)
            for x in anos
        )
    )

    if not anos:
        return 0

    maior = 1
    atual = 1

    for anterior, seguinte in zip(
        anos[:-1],
        anos[1:],
    ):

        if seguinte == anterior + 1:
            atual += 1

        else:
            atual = 1

        maior = max(
            maior,
            atual,
        )

    return maior


def primeiro_valido(
    serie,
):

    serie = serie.dropna()

    if serie.empty:
        return np.nan

    return serie.iloc[0]


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("PREPARAÇÃO DAS MÁXIMAS ANUAIS PARA ANÁLISE DE TENDÊNCIA")
print("=" * 90)


print(
    f"\nCobertura mínima mensal: "
    f"{COBERTURA_MENSAL_MINIMA * 100:.0f}%"
)


# ==========================================================
# 1. CARREGAR REDE
# ==========================================================

if not REDE_FILE.exists():

    raise FileNotFoundError(
        f"Rede não encontrada:\n"
        f"{REDE_FILE}"
    )


base = pd.read_parquet(
    REDE_FILE
)


print(
    f"\nRegistros estação-ano: "
    f"{len(base):,}"
)


print(
    f"Estações: "
    f"{base['codigo'].nunique():,}"
)


# ==========================================================
# 2. ESTAÇÃO-ANO JÁ APROVADOS PELO 06e
# ==========================================================

candidatos = (
    base[
        base[
            "ano_valido_tendencia"
        ]
    ][
        [
            "ano",
            "codigo",
        ]
    ]
    .copy()
)


print(
    f"Estação-ano aprovados pelo 06e: "
    f"{len(candidatos):,}"
)


# ==========================================================
# 3. DUCKDB
# ==========================================================

con = duckdb.connect(
    database=":memory:"
)


con.execute(
    "SET memory_limit = '4GB'"
)


con.execute(
    "SET threads = 4"
)


resultados_mensais = []
resultados_anuais = []


# ==========================================================
# 4. PROCESSAR ANO POR ANO
# ==========================================================

print("\n" + "=" * 90)
print("CALCULANDO COBERTURA MENSAL E MÁXIMAS")
print("=" * 90)


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    meta = (
        candidatos[
            candidatos[
                "ano"
            ]
            ==
            ano
        ][
            [
                "codigo",
            ]
        ]
        .copy()
    )


    if meta.empty:

        print(
            f"{ano}: nenhuma estação elegível"
        )

        continue


    arquivo = (
        PARES_DIR
        / f"era5_inmet_pares_{ano}.parquet"
    )


    if not arquivo.exists():

        raise FileNotFoundError(
            arquivo
        )


    con.register(
        "estacoes_ano",
        meta,
    )


    caminho_sql = sql_path(
        arquivo
    )


    # ======================================================
    # COBERTURA MENSAL
    # ======================================================

    mensal = con.execute(
        f"""
        SELECT

            CAST(
                {ano}
                AS INTEGER
            ) AS ano,

            CAST(
                p.codigo
                AS VARCHAR
            ) AS codigo,

            MONTH(
                p.datetime_utc
            ) AS mes,

            COUNT(*)
                AS n_pares_mes

        FROM read_parquet(
            '{caminho_sql}'
        ) AS p

        INNER JOIN estacoes_ano AS e

            ON p.codigo
                =
               e.codigo

        GROUP BY

            p.codigo,
            MONTH(
                p.datetime_utc
            )

        ORDER BY

            p.codigo,
            mes
        """
    ).fetchdf()


    resultados_mensais.append(
        mensal
    )


    # ======================================================
    # MÁXIMAS ANUAIS
    # ======================================================

    anual = con.execute(
        f"""
        SELECT

            CAST(
                {ano}
                AS INTEGER
            ) AS ano,

            CAST(
                p.codigo
                AS VARCHAR
            ) AS codigo,

            COUNT(*)
                AS n_pares_extremos,


            MAX(
                CAST(
                    p.temp_inmet_c
                    AS DOUBLE
                )
            )
                AS tmax_inmet_anual_c,


            ARG_MAX(
                p.datetime_utc,
                p.temp_inmet_c
            )
                AS data_tmax_inmet,


            ARG_MAX(
                CAST(
                    p.temp_era5_c
                    AS DOUBLE
                ),
                p.temp_inmet_c
            )
                AS era5_no_horario_tmax_inmet_c,


            ARG_MAX(
                CAST(
                    p.erro_c
                    AS DOUBLE
                ),
                p.temp_inmet_c
            )
                AS erro_no_tmax_inmet_c,


            MAX(
                CAST(
                    p.temp_era5_c
                    AS DOUBLE
                )
            )
                AS tmax_era5_anual_c,


            ARG_MAX(
                p.datetime_utc,
                p.temp_era5_c
            )
                AS data_tmax_era5,


            ARG_MAX(
                CAST(
                    p.temp_inmet_c
                    AS DOUBLE
                ),
                p.temp_era5_c
            )
                AS inmet_no_horario_tmax_era5_c


        FROM read_parquet(
            '{caminho_sql}'
        ) AS p


        INNER JOIN estacoes_ano AS e

            ON p.codigo
                =
               e.codigo


        GROUP BY
            p.codigo


        ORDER BY
            p.codigo
        """
    ).fetchdf()


    anual[
        "diferenca_maximos_anuais_c"
    ] = (
        anual[
            "tmax_era5_anual_c"
        ]
        -
        anual[
            "tmax_inmet_anual_c"
        ]
    )


    resultados_anuais.append(
        anual
    )


    con.unregister(
        "estacoes_ano"
    )


    print(
        f"{ano}: "
        f"{len(meta):,} estações"
    )


con.close()


# ==========================================================
# 5. CONSOLIDAR
# ==========================================================

mensal_real = pd.concat(
    resultados_mensais,
    ignore_index=True,
)


maximas = pd.concat(
    resultados_anuais,
    ignore_index=True,
)


# ==========================================================
# 6. CRIAR GRADE COMPLETA DE 12 MESES
# ==========================================================

meses = pd.DataFrame(
    {
        "mes":
            range(
                1,
                13,
            )
    }
)


grade_mensal = candidatos.merge(
    meses,
    how="cross",
)


mensal = grade_mensal.merge(
    mensal_real,
    on=[
        "ano",
        "codigo",
        "mes",
    ],
    how="left",
    validate="one_to_one",
)


mensal[
    "n_pares_mes"
] = (
    mensal[
        "n_pares_mes"
    ]
    .fillna(0)
    .astype(int)
)


# ==========================================================
# 7. HORAS ESPERADAS EM CADA MÊS
# ==========================================================

mensal[
    "horas_esperadas_mes"
] = mensal.apply(
    lambda linha:
        calendar.monthrange(
            int(
                linha[
                    "ano"
                ]
            ),
            int(
                linha[
                    "mes"
                ]
            ),
        )[1]
        *
        24,
    axis=1,
)


mensal[
    "cobertura_mes"
] = (
    mensal[
        "n_pares_mes"
    ]
    /
    mensal[
        "horas_esperadas_mes"
    ]
)


mensal[
    "mes_cobertura80"
] = (
    mensal[
        "cobertura_mes"
    ]
    >=
    COBERTURA_MENSAL_MINIMA
)


# ==========================================================
# 8. RESUMO MENSAL POR ESTAÇÃO-ANO
# ==========================================================

resumo_mensal = (
    mensal
    .groupby(
        [
            "ano",
            "codigo",
        ],
        as_index=False,
    )
    .agg(
        meses_com_dados=(
            "n_pares_mes",
            lambda x:
                int(
                    (
                        x
                        >
                        0
                    ).sum()
                ),
        ),

        meses_cobertura80=(
            "mes_cobertura80",
            "sum",
        ),

        cobertura_mensal_min=(
            "cobertura_mes",
            "min",
        ),

        cobertura_mensal_mediana=(
            "cobertura_mes",
            "median",
        ),
    )
)


# ==========================================================
# 9. JUNTAR À BASE ORIGINAL
# ==========================================================

base = base.merge(
    resumo_mensal,
    on=[
        "ano",
        "codigo",
    ],
    how="left",
    validate="one_to_one",
)


base = base.merge(
    maximas,
    on=[
        "ano",
        "codigo",
    ],
    how="left",
    validate="one_to_one",
)


# ==========================================================
# 10. DEFINIR ANO VÁLIDO PARA EXTREMOS
# ==========================================================

base[
    "ano_valido_extremos"
] = (
    base[
        "ano_valido_tendencia"
    ]
    &
    (
        base[
            "meses_cobertura80"
        ]
        ==
        12
    )
)


print("\n" + "=" * 90)
print("COBERTURA PARA EXTREMOS")
print("=" * 90)


print(
    f"\nEstação-ano válidos antes "
    f"do critério mensal: "
    f"{base['ano_valido_tendencia'].sum():,}"
)


print(
    f"Estação-ano válidos após "
    f"12 meses >=80%: "
    f"{base['ano_valido_extremos'].sum():,}"
)


# ==========================================================
# 11. VALIDAR NÚMERO DE PARES
# ==========================================================

validar = base[
    base[
        "ano_valido_tendencia"
    ]
].copy()


diferencas = (
    validar[
        "n_pares"
    ].astype(int)
    !=
    validar[
        "n_pares_extremos"
    ].astype(int)
)


print(
    f"Inconsistências no número de pares: "
    f"{diferencas.sum():,}"
)


if diferencas.any():

    raise RuntimeError(
        "Há diferença entre a base analítica "
        "e os pares usados nas máximas."
    )


# ==========================================================
# 12. RESUMO POR ESTAÇÃO
# ==========================================================

metadata = (
    base
    .sort_values(
        [
            "codigo",
            "ano",
        ]
    )
    .groupby(
        "codigo",
        as_index=False,
    )
    .agg(
        estacao=(
            "estacao",
            primeiro_valido,
        ),

        uf=(
            "uf",
            primeiro_valido,
        ),

        regiao=(
            "regiao",
            primeiro_valido,
        ),
    )
)


resumos = []


for codigo, grupo in base.groupby(
    "codigo"
):

    anos = (
        grupo.loc[
            grupo[
                "ano_valido_extremos"
            ],
            "ano",
        ]
        .astype(int)
        .tolist()
    )


    resumos.append(
        {
            "codigo":
                codigo,

            "anos_validos_extremos":
                len(
                    anos
                ),

            "primeiro_ano":
                min(anos)
                if anos
                else np.nan,

            "ultimo_ano":
                max(anos)
                if anos
                else np.nan,

            "maior_sequencia_consecutiva":
                maior_sequencia(
                    anos
                ),
        }
    )


rede = pd.DataFrame(
    resumos
)


rede = rede.merge(
    metadata,
    on="codigo",
    how="left",
    validate="one_to_one",
)


rede[
    "rede_extremos_10a"
] = (
    rede[
        "anos_validos_extremos"
    ]
    >=
    10
)


rede[
    "rede_extremos_15a"
] = (
    rede[
        "anos_validos_extremos"
    ]
    >=
    15
)


rede[
    "rede_extremos_consecutiva_10a"
] = (
    rede[
        "maior_sequencia_consecutiva"
    ]
    >=
    10
)


rede[
    "rede_extremos_consecutiva_15a"
] = (
    rede[
        "maior_sequencia_consecutiva"
    ]
    >=
    15
)


# ==========================================================
# 13. PAINÉIS FIXOS TERMINANDO EM 2025
# ==========================================================

anos_por_codigo = (
    base[
        base[
            "ano_valido_extremos"
        ]
    ]
    .groupby(
        "codigo"
    )[
        "ano"
    ]
    .apply(
        lambda x:
            set(
                x.astype(int)
            )
    )
    .to_dict()
)


metadata_codigo = (
    rede
    .set_index(
        "codigo"
    )
)


paineis = []


for inicio in range(
    ANO_INICIAL,
    2017,
):

    janela = set(
        range(
            inicio,
            ANO_FINAL + 1,
        )
    )


    codigos = [
        codigo

        for codigo, anos in
        anos_por_codigo.items()

        if janela.issubset(
            anos
        )
    ]


    linha = {
        "ano_inicial":
            inicio,

        "ano_final":
            ANO_FINAL,

        "duracao_anos":
            ANO_FINAL
            -
            inicio
            +
            1,

        "n_estacoes":
            len(
                codigos
            ),
    }


    # ------------------------------------------------------
    # CONTAGEM REGIONAL
    # ------------------------------------------------------

    regioes = (
        metadata_codigo.loc[
            codigos,
            "regiao",
        ]
        if codigos
        else pd.Series(
            dtype=object
        )
    )


    contagem = (
        regioes
        .value_counts()
    )


    for regiao in [
        "Norte",
        "Nordeste",
        "Centro-Oeste",
        "Sudeste",
        "Sul",
    ]:

        linha[
            f"n_{regiao.lower().replace('-', '_')}"
        ] = int(
            contagem.get(
                regiao,
                0,
            )
        )


    paineis.append(
        linha
    )


df_paineis = pd.DataFrame(
    paineis
)


# ==========================================================
# 14. DEVOLVER FLAGS À BASE
# ==========================================================

flags = rede[
    [
        "codigo",
        "anos_validos_extremos",
        "maior_sequencia_consecutiva",
        "rede_extremos_10a",
        "rede_extremos_15a",
        "rede_extremos_consecutiva_10a",
        "rede_extremos_consecutiva_15a",
    ]
]


base = base.merge(
    flags,
    on="codigo",
    how="left",
    validate="many_to_one",
)


base[
    "usar_extremos_10a"
] = (
    base[
        "ano_valido_extremos"
    ]
    &
    base[
        "rede_extremos_10a"
    ]
)


base[
    "usar_extremos_15a"
] = (
    base[
        "ano_valido_extremos"
    ]
    &
    base[
        "rede_extremos_15a"
    ]
)


# ==========================================================
# 15. SALVAR
# ==========================================================

mensal.to_parquet(
    SAIDA_MENSAL,
    index=False,
)


base.to_parquet(
    SAIDA_MAXIMAS,
    index=False,
)


base.to_csv(
    SAIDA_MAXIMAS_CSV,
    index=False,
    encoding="utf-8",
)


rede.to_csv(
    SAIDA_ESTACOES,
    index=False,
    encoding="utf-8",
)


df_paineis.to_csv(
    SAIDA_PAINEIS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 16. RESULTADOS
# ==========================================================

print("\n" + "=" * 90)
print("REDE PARA EXTREMOS ANUAIS")
print("=" * 90)


print(
    f"\nEstações >=10 anos válidos: "
    f"{rede['rede_extremos_10a'].sum():,}"
)


print(
    f"Estações >=15 anos válidos: "
    f"{rede['rede_extremos_15a'].sum():,}"
)


print(
    f"\nEstações >=10 anos consecutivos: "
    f"{rede['rede_extremos_consecutiva_10a'].sum():,}"
)


print(
    f"Estações >=15 anos consecutivos: "
    f"{rede['rede_extremos_consecutiva_15a'].sum():,}"
)


print("\n" + "=" * 90)
print("PAINÉIS FIXOS PARA EXTREMOS")
print("=" * 90)


print(
    df_paineis.to_string(
        index=False
    )
)


# ==========================================================
# 17. EXEMPLO DAS MÁXIMAS
# ==========================================================

print("\n" + "=" * 90)
print("AMOSTRA DAS MÁXIMAS ANUAIS")
print("=" * 90)


colunas_print = [
    "ano",
    "codigo",
    "estacao",
    "uf",

    "cobertura_calendario",
    "cobertura_mensal_min",

    "tmax_inmet_anual_c",
    "data_tmax_inmet",

    "tmax_era5_anual_c",
    "data_tmax_era5",

    "diferenca_maximos_anuais_c",
]


print(
    base.loc[
        base[
            "ano_valido_extremos"
        ],
        colunas_print,
    ]
    .head(20)
    .to_string(
        index=False
    )
)


print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    SAIDA_MENSAL
)


print(
    SAIDA_MAXIMAS
)


print(
    SAIDA_MAXIMAS_CSV
)


print(
    SAIDA_ESTACOES
)


print(
    SAIDA_PAINEIS
)


print("\n" + "=" * 90)
print("BASE DE EXTREMOS ANUAIS PREPARADA")
print("=" * 90)