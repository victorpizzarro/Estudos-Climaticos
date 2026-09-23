from pathlib import Path

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

MIN_PARES_ALERTA = 100

COBERTURA_MIN_ALERTA = 0.80

BIAS_ABS_ALERTA = 5.0
RMSE_ALERTA = 5.0
CORRELACAO_ALERTA = 0.50

DESVIO_BIAS_HISTORICO_ALERTA = 5.0
DESVIO_RMSE_HISTORICO_ALERTA = 5.0

MIN_ANOS_COMPARACAO_HISTORICA = 3


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


MATCHES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
)


PARES_DIR = (
    MATCHES_DIR
    / "horarios"
)


STATIONS_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
)


ARQUIVO_METRICAS = (
    ANNUAL_DIR
    / "metricas_era5_inmet_estacao_ano.parquet"
)


ARQUIVO_CATALOGO_ESTACOES = (
    STATIONS_DIR
    / "catalogo_estacoes_inmet.csv"
)


ARQUIVO_REVISAO = (
    ANNUAL_DIR
    / "metricas_era5_inmet_estacao_ano_revisadas.parquet"
)


ARQUIVO_REVISAO_CSV = (
    TABLES_DIR
    / "metricas_era5_inmet_estacao_ano_revisadas.csv"
)


ARQUIVO_FLAGS = (
    TABLES_DIR
    / "metricas_estacao_ano_suspeitas.csv"
)


ARQUIVO_METADATA_PENDENTE = (
    TABLES_DIR
    / "metricas_metadata_nao_resolvida.csv"
)


ARQUIVO_EVENTOS = (
    TABLES_DIR
    / "eventos_maior_erro_estacoes_suspeitas.csv"
)


ARQUIVO_MENSAL = (
    TABLES_DIR
    / "diagnostico_mensal_estacoes_suspeitas.csv"
)


# ==========================================================
# FUNÇÕES
# ==========================================================

def normalizar_bool(serie):

    if serie.dtype == bool:
        return serie

    return (
        serie
        .astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
    )


def sql_path(caminho):

    return str(
        caminho.resolve()
    ).replace(
        "'",
        "''",
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("INVESTIGAÇÃO DAS MÉTRICAS ERA5 × INMET")
print("=" * 90)

print(
    "\nNenhuma observação será removida."
)

print(
    "Flags servem somente para diagnóstico."
)


# ==========================================================
# 1. CARREGAR MÉTRICAS
# ==========================================================

if not ARQUIVO_METRICAS.exists():

    raise FileNotFoundError(
        f"Métricas não encontradas:\n"
        f"{ARQUIVO_METRICAS}"
    )


metricas = pd.read_parquet(
    ARQUIVO_METRICAS
)


print(
    f"\nRegistros estação-ano: "
    f"{len(metricas):,}"
)


print(
    f"Pares: "
    f"{metricas['n_pares'].sum():,}"
)


# ==========================================================
# 2. CARREGAR CATÁLOGO CONSOLIDADO
# ==========================================================

catalogo = pd.read_csv(
    ARQUIVO_CATALOGO_ESTACOES
)


catalogo = (
    catalogo
    .sort_values(
        "codigo"
    )
    .drop_duplicates(
        subset=[
            "codigo"
        ]
    )
)


# ==========================================================
# 3. CORRIGIR METADADOS TEXTUAIS
# ==========================================================

print("\n" + "=" * 90)
print("METADADOS")
print("=" * 90)


print(
    f"\nNome da estação ausente antes: "
    f"{metricas['estacao'].isna().sum():,}"
)


catalogo_aux = catalogo[
    [
        "codigo",
        "estacao",
        "uf",
        "regiao",
    ]
].rename(
    columns={
        "estacao":
            "estacao_catalogo",

        "uf":
            "uf_catalogo",

        "regiao":
            "regiao_catalogo",
    }
)


metricas = metricas.merge(
    catalogo_aux,
    on="codigo",
    how="left",
    validate="many_to_one",
)


for coluna, auxiliar in [
    (
        "estacao",
        "estacao_catalogo",
    ),
    (
        "uf",
        "uf_catalogo",
    ),
    (
        "regiao",
        "regiao_catalogo",
    ),
]:

    metricas[
        coluna
    ] = (
        metricas[
            coluna
        ]
        .replace(
            "",
            np.nan,
        )
        .fillna(
            metricas[
                auxiliar
            ]
        )
    )


metricas = metricas.drop(
    columns=[
        "estacao_catalogo",
        "uf_catalogo",
        "regiao_catalogo",
    ]
)


metadata_pendente = metricas[
    metricas[
        [
            "estacao",
            "uf",
            "regiao",
        ]
    ]
    .isna()
    .any(
        axis=1
    )
].copy()


print(
    f"Nome da estação ausente depois: "
    f"{metricas['estacao'].isna().sum():,}"
)


print(
    f"Registros ainda com algum "
    f"metadado textual ausente: "
    f"{len(metadata_pendente):,}"
)


metadata_pendente.to_csv(
    ARQUIVO_METADATA_PENDENTE,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 4. COMPORTAMENTO HISTÓRICO DA ESTAÇÃO
# ==========================================================

historico = (
    metricas
    .groupby(
        "codigo"
    )
    .agg(
        anos_metricas=(
            "ano",
            "nunique",
        ),

        bias_mediana_estacao=(
            "bias_c",
            "median",
        ),

        rmse_mediana_estacao=(
            "rmse_c",
            "median",
        ),

        correlacao_mediana_estacao=(
            "correlacao_pearson",
            "median",
        ),
    )
    .reset_index()
)


metricas = metricas.merge(
    historico,
    on="codigo",
    how="left",
    validate="many_to_one",
)


metricas[
    "desvio_bias_mediana_estacao"
] = (
    metricas[
        "bias_c"
    ]
    -
    metricas[
        "bias_mediana_estacao"
    ]
)


metricas[
    "desvio_rmse_mediana_estacao"
] = (
    metricas[
        "rmse_c"
    ]
    -
    metricas[
        "rmse_mediana_estacao"
    ]
)


# ==========================================================
# 5. FLAGS
# ==========================================================

metricas[
    "flag_poucos_pares"
] = (
    metricas[
        "n_pares"
    ]
    <
    MIN_PARES_ALERTA
)


metricas[
    "flag_cobertura_baixa"
] = (
    metricas[
        "cobertura_temp"
    ]
    <
    COBERTURA_MIN_ALERTA
)


metricas[
    "flag_bias_extremo"
] = (
    metricas[
        "bias_c"
    ]
    .abs()
    >
    BIAS_ABS_ALERTA
)


metricas[
    "flag_rmse_extremo"
] = (
    metricas[
        "rmse_c"
    ]
    >
    RMSE_ALERTA
)


# Só interpretar correlação se houver um
# número minimamente razoável de observações.

metricas[
    "flag_correlacao_baixa"
] = (
    (
        metricas[
            "n_pares"
        ]
        >=
        MIN_PARES_ALERTA
    )
    &
    (
        metricas[
            "correlacao_pearson"
        ]
        <
        CORRELACAO_ALERTA
    )
)


metricas[
    "flag_salto_bias_historico"
] = (
    (
        metricas[
            "anos_metricas"
        ]
        >=
        MIN_ANOS_COMPARACAO_HISTORICA
    )
    &
    (
        metricas[
            "desvio_bias_mediana_estacao"
        ]
        .abs()
        >
        DESVIO_BIAS_HISTORICO_ALERTA
    )
)


metricas[
    "flag_salto_rmse_historico"
] = (
    (
        metricas[
            "anos_metricas"
        ]
        >=
        MIN_ANOS_COMPARACAO_HISTORICA
    )
    &
    (
        metricas[
            "desvio_rmse_mediana_estacao"
        ]
        >
        DESVIO_RMSE_HISTORICO_ALERTA
    )
)


colunas_flags = [
    "flag_poucos_pares",
    "flag_cobertura_baixa",
    "flag_bias_extremo",
    "flag_rmse_extremo",
    "flag_correlacao_baixa",
    "flag_salto_bias_historico",
    "flag_salto_rmse_historico",
]


metricas[
    "n_flags"
] = (
    metricas[
        colunas_flags
    ]
    .sum(
        axis=1
    )
)


metricas[
    "flag_investigar"
] = (
    metricas[
        "n_flags"
    ]
    >
    0
)


# ==========================================================
# 6. CLASSIFICAR MOTIVOS
# ==========================================================

def montar_motivos(
    linha,
):

    motivos = []


    mapa = {
        "flag_poucos_pares":
            "poucos_pares",

        "flag_cobertura_baixa":
            "cobertura_baixa",

        "flag_bias_extremo":
            "bias_extremo",

        "flag_rmse_extremo":
            "rmse_extremo",

        "flag_correlacao_baixa":
            "correlacao_baixa",

        "flag_salto_bias_historico":
            "salto_bias_historico",

        "flag_salto_rmse_historico":
            "salto_rmse_historico",
    }


    for coluna, texto in mapa.items():

        if bool(
            linha[
                coluna
            ]
        ):

            motivos.append(
                texto
            )


    return (
        "|".join(
            motivos
        )
        if motivos
        else
        "sem_flag"
    )


metricas[
    "motivos_flag"
] = metricas.apply(
    montar_motivos,
    axis=1,
)


# ==========================================================
# 7. SELECIONAR SUSPEITAS
# ==========================================================

suspeitas = (
    metricas[
        metricas[
            "flag_investigar"
        ]
    ]
    .copy()
)


# Prioridade puramente diagnóstica.
# Não é um score de qualidade científica.

suspeitas[
    "prioridade_diagnostico"
] = (
    suspeitas[
        "n_flags"
    ]
    *
    100
    +
    suspeitas[
        "bias_c"
    ].abs()
    +
    suspeitas[
        "rmse_c"
    ]
)


suspeitas = suspeitas.sort_values(
    [
        "prioridade_diagnostico",
        "rmse_c",
    ],
    ascending=[
        False,
        False,
    ],
)


# ==========================================================
# 8. SALVAR MÉTRICAS REVISADAS
# ==========================================================

metricas.to_parquet(
    ARQUIVO_REVISAO,
    index=False,
)


metricas.to_csv(
    ARQUIVO_REVISAO_CSV,
    index=False,
    encoding="utf-8",
)


suspeitas.to_csv(
    ARQUIVO_FLAGS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 9. RESUMO DAS FLAGS
# ==========================================================

print("\n" + "=" * 90)
print("FLAGS")
print("=" * 90)


print(
    f"\nEstação-ano investigadas: "
    f"{len(suspeitas):,}"
)


for coluna in colunas_flags:

    print(
        f"{coluna}: "
        f"{metricas[coluna].sum():,}"
    )


print(
    "\nMotivos mais frequentes:"
)


print(
    metricas.loc[
        metricas[
            "flag_investigar"
        ],
        "motivos_flag",
    ]
    .value_counts()
    .head(20)
    .to_string()
)


# ==========================================================
# 10. MOSTRAR PRINCIPAIS CASOS
# ==========================================================

colunas_impressao = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "n_pares",
    "cobertura_temp",
    "bias_c",
    "rmse_c",
    "correlacao_pearson",
    "bias_mediana_estacao",
    "rmse_mediana_estacao",
    "desvio_bias_mediana_estacao",
    "desvio_rmse_mediana_estacao",
    "motivos_flag",
]


print("\n" + "=" * 90)
print("30 CASOS DE MAIOR PRIORIDADE DIAGNÓSTICA")
print("=" * 90)


print(
    suspeitas[
        colunas_impressao
    ]
    .head(30)
    .to_string(
        index=False
    )
)


# ==========================================================
# 11. CASOS QUE QUEREMOS VER EXPLICITAMENTE
# ==========================================================

print("\n" + "=" * 90)
print("CASOS DE INTERESSE")
print("=" * 90)


casos = (
    (
        (
            metricas[
                "codigo"
            ]
            ==
            "A402"
        )
        &
        (
            metricas[
                "ano"
            ]
            ==
            2005
        )
    )
    |
    (
        metricas[
            "codigo"
        ]
        ==
        "A610"
    )
    |
    (
        (
            metricas[
                "codigo"
            ]
            ==
            "A316"
        )
        &
        (
            metricas[
                "ano"
            ]
            ==
            2015
        )
    )
    |
    (
        (
            metricas[
                "codigo"
            ]
            ==
            "A214"
        )
        &
        (
            metricas[
                "ano"
            ]
            ==
            2022
        )
    )
)


print(
    metricas.loc[
        casos,
        colunas_impressao,
    ]
    .sort_values(
        [
            "codigo",
            "ano",
        ]
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 12. DUCKDB PARA DIAGNÓSTICO DOS PARES
# ==========================================================

print("\n" + "=" * 90)
print("EXTRAINDO DIAGNÓSTICOS HORÁRIOS")
print("=" * 90)


con = duckdb.connect(
    database=":memory:"
)


con.execute(
    "SET memory_limit = '4GB'"
)


con.execute(
    "SET threads = 4"
)


eventos_total = []

mensal_total = []


for ano in sorted(
    suspeitas[
        "ano"
    ].unique()
):

    ano = int(
        ano
    )


    codigos = (
        suspeitas.loc[
            suspeitas[
                "ano"
            ]
            ==
            ano,
            "codigo",
        ]
        .drop_duplicates()
        .tolist()
    )


    if not codigos:

        continue


    caminho = (
        PARES_DIR
        / f"era5_inmet_pares_{ano}.parquet"
    )


    if not caminho.exists():

        raise FileNotFoundError(
            f"Parquet ausente:\n"
            f"{caminho}"
        )


    caminho_sql = sql_path(
        caminho
    )


    # Criar tabela temporária de códigos
    # para evitar montar IN (...) gigantesco.

    df_codigos = pd.DataFrame(
        {
            "codigo":
                codigos
        }
    )


    con.register(
        "codigos_suspeitos",
        df_codigos,
    )


    # ======================================================
    # TOP 20 ERROS ABSOLUTOS POR ESTAÇÃO
    # ======================================================

    eventos = con.execute(
        f"""
        WITH base AS (

            SELECT

                p.*,

                ABS(
                    CAST(
                        p.erro_c
                        AS DOUBLE
                    )
                ) AS erro_abs,

                ROW_NUMBER()
                OVER (
                    PARTITION BY
                        p.codigo

                    ORDER BY
                        ABS(
                            CAST(
                                p.erro_c
                                AS DOUBLE
                            )
                        ) DESC
                ) AS ranking

            FROM read_parquet(
                '{caminho_sql}'
            ) AS p

            INNER JOIN
                codigos_suspeitos AS c

                ON p.codigo
                    =
                   c.codigo
        )

        SELECT
            *
        FROM base
        WHERE ranking <= 20

        ORDER BY
            codigo,
            ranking
        """
    ).fetchdf()


    if not eventos.empty:

        eventos_total.append(
            eventos
        )


    # ======================================================
    # DIAGNÓSTICO MENSAL
    # ======================================================

    mensal = con.execute(
        f"""
        SELECT

            CAST(
                {ano}
                AS INTEGER
            ) AS ano,

            p.codigo,

            MONTH(
                p.datetime_utc
            ) AS mes,

            COUNT(*)
                AS n_pares,

            AVG(
                CAST(
                    p.temp_inmet_c
                    AS DOUBLE
                )
            )
                AS media_inmet_c,

            AVG(
                CAST(
                    p.temp_era5_c
                    AS DOUBLE
                )
            )
                AS media_era5_c,

            AVG(
                CAST(
                    p.erro_c
                    AS DOUBLE
                )
            )
                AS bias_c,

            AVG(
                ABS(
                    CAST(
                        p.erro_c
                        AS DOUBLE
                    )
                )
            )
                AS mae_c,

            SQRT(
                AVG(
                    POWER(
                        CAST(
                            p.erro_c
                            AS DOUBLE
                        ),
                        2
                    )
                )
            )
                AS rmse_c,

            CORR(
                CAST(
                    p.temp_era5_c
                    AS DOUBLE
                ),
                CAST(
                    p.temp_inmet_c
                    AS DOUBLE
                )
            )
                AS correlacao

        FROM read_parquet(
            '{caminho_sql}'
        ) AS p

        INNER JOIN
            codigos_suspeitos AS c

            ON p.codigo
                =
               c.codigo

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


    if not mensal.empty:

        mensal_total.append(
            mensal
        )


    con.unregister(
        "codigos_suspeitos"
    )


    print(
        f"{ano}: "
        f"{len(codigos):,} "
        "estações investigadas"
    )


# ==========================================================
# 13. SALVAR DIAGNÓSTICOS HORÁRIOS
# ==========================================================

if eventos_total:

    eventos_df = pd.concat(
        eventos_total,
        ignore_index=True,
    )


    eventos_df.to_csv(
        ARQUIVO_EVENTOS,
        index=False,
        encoding="utf-8",
    )

else:

    eventos_df = pd.DataFrame()


if mensal_total:

    mensal_df = pd.concat(
        mensal_total,
        ignore_index=True,
    )


    mensal_df.to_csv(
        ARQUIVO_MENSAL,
        index=False,
        encoding="utf-8",
    )

else:

    mensal_df = pd.DataFrame()


con.close()


# ==========================================================
# 14. RESUMO FINAL
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO FINAL")
print("=" * 90)


print(
    f"\nRegistros estação-ano: "
    f"{len(metricas):,}"
)


print(
    f"Com pelo menos uma flag: "
    f"{len(suspeitas):,}"
)


print(
    f"Sem flags: "
    f"{len(metricas) - len(suspeitas):,}"
)


print(
    f"\nMetadados não resolvidos: "
    f"{len(metadata_pendente):,}"
)


print(
    f"Eventos horários salvos: "
    f"{len(eventos_df):,}"
)


print(
    f"Resumos mensais salvos: "
    f"{len(mensal_df):,}"
)


print(
    "\nMétricas revisadas:"
)

print(
    ARQUIVO_REVISAO
)


print(
    "\nFlags:"
)

print(
    ARQUIVO_FLAGS
)


print(
    "\nEventos de maior erro:"
)

print(
    ARQUIVO_EVENTOS
)


print(
    "\nDiagnóstico mensal:"
)

print(
    ARQUIVO_MENSAL
)


print("\n" + "=" * 90)
print("INVESTIGAÇÃO CONCLUÍDA")
print("=" * 90)