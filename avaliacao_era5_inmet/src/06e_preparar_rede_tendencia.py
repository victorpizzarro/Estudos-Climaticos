import calendar
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

COBERTURA_MINIMA = 0.80

ANO_INICIAL = 2000
ANO_FINAL = 2025


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


ARQUIVO_BASE = (
    ANNUAL_DIR
    / "amostra_analitica_estacao_ano.parquet"
)


SAIDA_PARQUET = (
    ANNUAL_DIR
    / "rede_tendencia_estacao_ano.parquet"
)


SAIDA_ESTACOES = (
    TABLES_DIR
    / "rede_tendencia_estacoes.csv"
)


SAIDA_ANOS = (
    TABLES_DIR
    / "rede_tendencia_por_ano.csv"
)


SAIDA_PAINEIS = (
    TABLES_DIR
    / "paineis_fixos_rede_tendencia.csv"
)


# ==========================================================
# FUNÇÕES
# ==========================================================

def converter_bool(serie):

    if serie.dtype == bool:
        return serie

    return (
        serie.astype(str)
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
        .fillna(False)
    )


def maior_sequencia_consecutiva(
    anos,
):

    anos = sorted(
        set(
            int(ano)
            for ano in anos
        )
    )


    if not anos:
        return 0


    maior = 1
    atual = 1


    for anterior, atual_ano in zip(
        anos[:-1],
        anos[1:],
    ):

        if atual_ano == anterior + 1:

            atual += 1

        else:

            atual = 1


        maior = max(
            maior,
            atual,
        )


    return maior


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("PREPARAÇÃO DA REDE DEFINITIVA DE TENDÊNCIA")
print("=" * 90)


print(
    "\nCritério de cobertura:"
)


print(
    "n_pares / número total de horas do ano"
)


print(
    f"\nCobertura mínima: "
    f"{COBERTURA_MINIMA * 100:.0f}%"
)


# ==========================================================
# 1. CARREGAR
# ==========================================================

if not ARQUIVO_BASE.exists():

    raise FileNotFoundError(
        f"Base analítica não encontrada:\n"
        f"{ARQUIVO_BASE}"
    )


base = pd.read_parquet(
    ARQUIVO_BASE
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
# 2. NORMALIZAR BOOLEANOS
# ==========================================================

for coluna in [
    "usar_validacao_principal",
    "coordenada_estavel_5km",
]:

    if coluna not in base.columns:

        raise RuntimeError(
            f"Coluna obrigatória ausente: "
            f"{coluna}"
        )


    base[
        coluna
    ] = converter_bool(
        base[
            coluna
        ]
    )


# ==========================================================
# 3. HORAS ESPERADAS POR ANO
# ==========================================================

base[
    "horas_esperadas_ano"
] = base[
    "ano"
].apply(
    lambda ano:
        8784
        if calendar.isleap(
            int(ano)
        )
        else 8760
)


# ==========================================================
# 4. COBERTURA CALENDÁRIO REAL
# ==========================================================

base[
    "cobertura_calendario"
] = (
    base[
        "n_pares"
    ]
    /
    base[
        "horas_esperadas_ano"
    ]
)


# Segurança contra algum absurdo inesperado.

if (
    base[
        "cobertura_calendario"
    ]
    >
    1.000001
).any():

    problema = base[
        base[
            "cobertura_calendario"
        ]
        >
        1.000001
    ]


    raise RuntimeError(
        "Foi encontrada cobertura "
        "superior a 100%:\n"
        f"{problema[['ano', 'codigo', 'n_pares']].head()}"
    )


# ==========================================================
# 5. ESTAÇÃO-ANO VÁLIDO PARA TENDÊNCIA
# ==========================================================

base[
    "ano_valido_tendencia"
] = (
    base[
        "usar_validacao_principal"
    ]
    &
    base[
        "coordenada_estavel_5km"
    ]
    &
    (
        base[
            "cobertura_calendario"
        ]
        >=
        COBERTURA_MINIMA
    )
)


# ==========================================================
# 6. METADADOS POR ESTAÇÃO
# ==========================================================

def primeiro_valido(
    serie,
):

    serie = serie.dropna()

    if serie.empty:
        return np.nan

    return serie.iloc[0]


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

        coordenada_estavel_5km=(
            "coordenada_estavel_5km",
            "all",
        ),
    )
)


# ==========================================================
# 7. ANOS VÁLIDOS POR ESTAÇÃO
# ==========================================================

validos = (
    base[
        base[
            "ano_valido_tendencia"
        ]
    ]
    .copy()
)


resumos = []


for codigo, grupo in base.groupby(
    "codigo"
):

    anos_validos = (
        grupo.loc[
            grupo[
                "ano_valido_tendencia"
            ],
            "ano",
        ]
        .astype(int)
        .sort_values()
        .tolist()
    )


    n_anos = len(
        anos_validos
    )


    if n_anos:

        primeiro_ano = min(
            anos_validos
        )

        ultimo_ano = max(
            anos_validos
        )

        amplitude = (
            ultimo_ano
            -
            primeiro_ano
            +
            1
        )

    else:

        primeiro_ano = np.nan
        ultimo_ano = np.nan
        amplitude = 0


    resumos.append(
        {
            "codigo":
                codigo,

            "anos_validos_tendencia":
                n_anos,

            "primeiro_ano_valido":
                primeiro_ano,

            "ultimo_ano_valido":
                ultimo_ano,

            "amplitude_anos":
                amplitude,

            "maior_sequencia_consecutiva":
                maior_sequencia_consecutiva(
                    anos_validos
                ),

            "cobertura_calendario_mediana":
                grupo.loc[
                    grupo[
                        "ano_valido_tendencia"
                    ],
                    "cobertura_calendario",
                ].median(),

            "cobertura_calendario_min":
                grupo.loc[
                    grupo[
                        "ano_valido_tendencia"
                    ],
                    "cobertura_calendario",
                ].min(),
        }
    )


resumo_estacoes = pd.DataFrame(
    resumos
)


resumo_estacoes = resumo_estacoes.merge(
    metadata,
    on="codigo",
    how="left",
    validate="one_to_one",
)


# ==========================================================
# 8. REDES 10 E 15 ANOS
# ==========================================================

resumo_estacoes[
    "rede_tendencia_10a"
] = (
    resumo_estacoes[
        "coordenada_estavel_5km"
    ]
    &
    (
        resumo_estacoes[
            "anos_validos_tendencia"
        ]
        >=
        10
    )
)


resumo_estacoes[
    "rede_tendencia_15a"
] = (
    resumo_estacoes[
        "coordenada_estavel_5km"
    ]
    &
    (
        resumo_estacoes[
            "anos_validos_tendencia"
        ]
        >=
        15
    )
)


# Também guardamos versões estritas consecutivas.

resumo_estacoes[
    "rede_consecutiva_10a"
] = (
    resumo_estacoes[
        "coordenada_estavel_5km"
    ]
    &
    (
        resumo_estacoes[
            "maior_sequencia_consecutiva"
        ]
        >=
        10
    )
)


resumo_estacoes[
    "rede_consecutiva_15a"
] = (
    resumo_estacoes[
        "coordenada_estavel_5km"
    ]
    &
    (
        resumo_estacoes[
            "maior_sequencia_consecutiva"
        ]
        >=
        15
    )
)


# ==========================================================
# 9. DEVOLVER FLAGS PARA ESTAÇÃO-ANO
# ==========================================================

flags = resumo_estacoes[
    [
        "codigo",
        "anos_validos_tendencia",
        "maior_sequencia_consecutiva",
        "rede_tendencia_10a",
        "rede_tendencia_15a",
        "rede_consecutiva_10a",
        "rede_consecutiva_15a",
    ]
]


base = base.merge(
    flags,
    on="codigo",
    how="left",
    validate="many_to_one",
)


base[
    "usar_tendencia_real_10a"
] = (
    base[
        "ano_valido_tendencia"
    ]
    &
    base[
        "rede_tendencia_10a"
    ]
)


base[
    "usar_tendencia_real_15a"
] = (
    base[
        "ano_valido_tendencia"
    ]
    &
    base[
        "rede_tendencia_15a"
    ]
)


# ==========================================================
# 10. RESUMO POR ANO
# ==========================================================

resumo_anos = (
    base
    .groupby(
        "ano",
        as_index=False,
    )
    .agg(
        estacoes_total=(
            "codigo",
            "nunique",
        ),

        estacoes_ano_cobertura80=(
            "ano_valido_tendencia",
            "sum",
        ),

        estacoes_rede10=(
            "usar_tendencia_real_10a",
            "sum",
        ),

        estacoes_rede15=(
            "usar_tendencia_real_15a",
            "sum",
        ),
    )
)


# ==========================================================
# 11. PAINÉIS FIXOS TERMINANDO EM 2025
# ==========================================================

# Aqui verificamos quantas estações possuem >=80%
# de cobertura em TODOS os anos de cada janela.
#
# Isso será importante para decidir se a tendência
# nacional poderá usar uma rede totalmente fixa.

anos_validos_por_codigo = (
    base[
        base[
            "ano_valido_tendencia"
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


estacoes_estaveis = set(
    resumo_estacoes.loc[
        resumo_estacoes[
            "coordenada_estavel_5km"
        ],
        "codigo",
    ]
)


paineis = []


for inicio in range(
    ANO_INICIAL,
    ANO_FINAL - 8,
):

    anos_janela = set(
        range(
            inicio,
            ANO_FINAL + 1,
        )
    )


    codigos_painel = []


    for codigo in estacoes_estaveis:

        anos_codigo = (
            anos_validos_por_codigo.get(
                codigo,
                set(),
            )
        )


        if anos_janela.issubset(
            anos_codigo
        ):

            codigos_painel.append(
                codigo
            )


    paineis.append(
        {
            "ano_inicial":
                inicio,

            "ano_final":
                ANO_FINAL,

            "duracao_anos":
                ANO_FINAL - inicio + 1,

            "n_estacoes_painel_fixo":
                len(
                    codigos_painel
                ),
        }
    )


df_paineis = pd.DataFrame(
    paineis
)


# ==========================================================
# 12. SALVAR
# ==========================================================

base = base.sort_values(
    [
        "ano",
        "codigo",
    ]
).reset_index(
    drop=True
)


base.to_parquet(
    SAIDA_PARQUET,
    index=False,
)


resumo_estacoes.to_csv(
    SAIDA_ESTACOES,
    index=False,
    encoding="utf-8",
)


resumo_anos.to_csv(
    SAIDA_ANOS,
    index=False,
    encoding="utf-8",
)


df_paineis.to_csv(
    SAIDA_PAINEIS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 13. IMPRESSÃO
# ==========================================================

print("\n" + "=" * 90)
print("COBERTURA CALENDÁRIO")
print("=" * 90)


print(
    f"\nEstação-ano total: "
    f"{len(base):,}"
)


print(
    f"Estação-ano com cobertura >=80%, "
    f"QC e estabilidade espacial: "
    f"{base['ano_valido_tendencia'].sum():,}"
)


print("\n" + "=" * 90)
print("REDE DE TENDÊNCIA RECALCULADA")
print("=" * 90)


print(
    f"\nEstações >=10 anos válidos: "
    f"{resumo_estacoes['rede_tendencia_10a'].sum():,}"
)


print(
    f"Estações >=15 anos válidos: "
    f"{resumo_estacoes['rede_tendencia_15a'].sum():,}"
)


print(
    f"\nEstações >=10 anos consecutivos: "
    f"{resumo_estacoes['rede_consecutiva_10a'].sum():,}"
)


print(
    f"Estações >=15 anos consecutivos: "
    f"{resumo_estacoes['rede_consecutiva_15a'].sum():,}"
)


print("\n" + "=" * 90)
print("DISTRIBUIÇÃO DOS ANOS VÁLIDOS")
print("=" * 90)


print(
    resumo_estacoes[
        "anos_validos_tendencia"
    ]
    .describe(
        percentiles=[
            0.25,
            0.50,
            0.75,
            0.90,
        ]
    )
    .to_string()
)


print("\n" + "=" * 90)
print("ESTAÇÕES DISPONÍVEIS POR ANO")
print("=" * 90)


print(
    resumo_anos.to_string(
        index=False
    )
)


print("\n" + "=" * 90)
print("PAINÉIS FIXOS TERMINANDO EM 2025")
print("=" * 90)


print(
    df_paineis.to_string(
        index=False
    )
)


# ==========================================================
# 14. COMPARAÇÃO COM A CLASSIFICAÇÃO ANTIGA
# ==========================================================

if (
    "candidata_tendencia_10a"
    in base.columns
):

    antiga10 = (
        base.loc[
            converter_bool(
                base[
                    "candidata_tendencia_10a"
                ]
            ),
            "codigo",
        ]
        .nunique()
    )


    print(
        f"\nRede antiga >=10 anos: "
        f"{antiga10:,}"
    )


if (
    "candidata_tendencia_15a"
    in base.columns
):

    antiga15 = (
        base.loc[
            converter_bool(
                base[
                    "candidata_tendencia_15a"
                ]
            ),
            "codigo",
        ]
        .nunique()
    )


    print(
        f"Rede antiga >=15 anos: "
        f"{antiga15:,}"
    )


print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    SAIDA_PARQUET
)


print(
    SAIDA_ESTACOES
)


print(
    SAIDA_ANOS
)


print(
    SAIDA_PAINEIS
)


print("\n" + "=" * 90)
print("REDE DE TENDÊNCIA DEFINITIVA PREPARADA")
print("=" * 90)