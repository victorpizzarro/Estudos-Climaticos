from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


STATIONS_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
)


METRICAS_FILE = (
    ANNUAL_DIR
    / "metricas_era5_inmet_estacao_ano_revisadas.parquet"
)


CASOS_CRITICOS_FILE = (
    TABLES_DIR
    / "casos_criticos_era5_inmet.csv"
)


TENDENCIA_FILE = (
    STATIONS_DIR
    / "estacoes_inmet_candidatas_tendencia.csv"
)


SAIDA_PARQUET = (
    ANNUAL_DIR
    / "amostra_analitica_estacao_ano.parquet"
)


SAIDA_CSV = (
    TABLES_DIR
    / "amostra_analitica_estacao_ano.csv"
)


SAIDA_EXCLUIDOS = (
    TABLES_DIR
    / "estacao_ano_excluidos_validacao_principal.csv"
)


SAIDA_RESUMO = (
    TABLES_DIR
    / "resumo_amostra_analitica.csv"
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

MIN_PARES_ESTACAO_ANO = 100

COBERTURA_TENDENCIA = 0.80


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("DEFINIÇÃO DA AMOSTRA ANALÍTICA ERA5 × INMET")
print("=" * 90)


print(
    "\nAmostra completa = todos os pares válidos."
)

print(
    "Amostra principal = remove somente "
    "anomalias estação-ano temporais identificadas."
)

print(
    "Rede de tendência = aplica ainda critérios "
    "de estabilidade e cobertura."
)


# ==========================================================
# 1. VERIFICAR ARQUIVOS
# ==========================================================

for caminho in [
    METRICAS_FILE,
    CASOS_CRITICOS_FILE,
    TENDENCIA_FILE,
]:

    if not caminho.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado:\n"
            f"{caminho}"
        )


# ==========================================================
# 2. CARREGAR
# ==========================================================

metricas = pd.read_parquet(
    METRICAS_FILE
)


criticos = pd.read_csv(
    CASOS_CRITICOS_FILE
)


tendencia = pd.read_csv(
    TENDENCIA_FILE
)


print(
    f"\nRegistros estação-ano: "
    f"{len(metricas):,}"
)


print(
    f"Pares totais: "
    f"{metricas['n_pares'].sum():,}"
)


# ==========================================================
# 3. IDENTIFICAR ANOMALIAS TEMPORAIS
# ==========================================================

anomalias = (
    criticos[
        criticos[
            "categoria_diagnostico"
        ]
        ==
        "anomalia_temporal"
    ][
        [
            "ano",
            "codigo",
            "categoria_diagnostico",
        ]
    ]
    .drop_duplicates(
        subset=[
            "ano",
            "codigo",
        ]
    )
    .copy()
)


print(
    f"\nAnomalias estação-ano encontradas: "
    f"{len(anomalias):,}"
)


print(
    anomalias
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


# Nossa investigação anterior encontrou exatamente quatro.
# Caso isso mude, queremos saber em vez de continuar
# silenciosamente com outro conjunto.

if len(anomalias) != 4:

    raise RuntimeError(
        "Esperávamos exatamente 4 "
        "anomalias temporais após o diagnóstico, "
        f"mas encontramos {len(anomalias)}."
    )


# ==========================================================
# 4. JUNTAR CLASSIFICAÇÃO
# ==========================================================

base = metricas.merge(
    anomalias,
    on=[
        "ano",
        "codigo",
    ],
    how="left",
    validate="one_to_one",
)


base[
    "anomalia_temporal"
] = (
    base[
        "categoria_diagnostico"
    ]
    ==
    "anomalia_temporal"
)


# ==========================================================
# 5. JUSTIFICATIVA ESPECÍFICA
# ==========================================================

def motivo_qc(
    linha,
):

    if not linha[
        "anomalia_temporal"
    ]:

        return "aprovado"


    codigo = str(
        linha[
            "codigo"
        ]
    )


    ano = int(
        linha[
            "ano"
        ]
    )


    if (
        codigo == "A316"
        and
        ano in [
            2014,
            2015,
        ]
    ):

        return (
            "descontinuidade_temporal_"
            "com_melhora_forte_em_lag_11h"
        )


    if (
        codigo == "A402"
        and
        ano == 2005
    ):

        return (
            "descontinuidade_isolada_extrema_"
            "nao_resolvida_por_lag"
        )


    if (
        codigo == "A355"
        and
        ano == 2015
    ):

        return (
            "descontinuidade_isolada_"
            "nao_resolvida_por_lag"
        )


    return (
        "anomalia_temporal_diagnosticada"
    )


base[
    "motivo_qc_principal"
] = base.apply(
    motivo_qc,
    axis=1,
)


# ==========================================================
# 6. CAMADAS ANALÍTICAS
# ==========================================================

# ----------------------------------------------------------
# Sensibilidade
#
# Absolutamente todos os pares válidos são mantidos.
# ----------------------------------------------------------

base[
    "usar_amostra_completa"
] = True


# ----------------------------------------------------------
# Validação principal
#
# Remove somente as quatro anomalias temporais.
# ----------------------------------------------------------

base[
    "usar_validacao_principal"
] = (
    ~base[
        "anomalia_temporal"
    ]
)


# ----------------------------------------------------------
# Estação-ano com amostra mínima
#
# Útil para análises em que cada estação-ano recebe
# o mesmo peso.
# ----------------------------------------------------------

base[
    "usar_resumo_estacao_ano"
] = (
    base[
        "usar_validacao_principal"
    ]
    &
    (
        base[
            "n_pares"
        ]
        >=
        MIN_PARES_ESTACAO_ANO
    )
)


# ==========================================================
# 7. ADICIONAR CLASSIFICAÇÃO DE TENDÊNCIA
# ==========================================================

colunas_tendencia = [
    "codigo",
    "coordenada_estavel_5km",
    "candidata_tendencia_10a",
    "candidata_tendencia_15a",
]


tendencia_aux = tendencia[
    colunas_tendencia
].copy()


base = base.merge(
    tendencia_aux,
    on="codigo",
    how="left",
    validate="many_to_one",
)


for coluna in [
    "coordenada_estavel_5km",
    "candidata_tendencia_10a",
    "candidata_tendencia_15a",
]:

    if base[
        coluna
    ].dtype != bool:

        base[
            coluna
        ] = (
            base[
                coluna
            ]
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
            .fillna(False)
        )


# ==========================================================
# 8. ANOS APROVADOS PARA TENDÊNCIA
# ==========================================================

base[
    "ano_cobertura_80"
] = (
    base[
        "cobertura_temp"
    ]
    >=
    COBERTURA_TENDENCIA
)


base[
    "usar_tendencia_10a"
] = (
    base[
        "usar_validacao_principal"
    ]
    &
    base[
        "ano_cobertura_80"
    ]
    &
    base[
        "candidata_tendencia_10a"
    ]
)


base[
    "usar_tendencia_15a"
] = (
    base[
        "usar_validacao_principal"
    ]
    &
    base[
        "ano_cobertura_80"
    ]
    &
    base[
        "candidata_tendencia_15a"
    ]
)


# ==========================================================
# 9. PARES EXCLUÍDOS
# ==========================================================

excluidos = (
    base[
        ~base[
            "usar_validacao_principal"
        ]
    ]
    .copy()
)


pares_totais = int(
    base[
        "n_pares"
    ].sum()
)


pares_excluidos = int(
    excluidos[
        "n_pares"
    ].sum()
)


pares_principal = (
    pares_totais
    -
    pares_excluidos
)


pct_excluido = (
    pares_excluidos
    /
    pares_totais
    *
    100
)


# ==========================================================
# 10. SALVAR EXCLUÍDOS
# ==========================================================

colunas_excluidos = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "n_pares",
    "cobertura_temp",
    "bias_c",
    "mae_c",
    "rmse_c",
    "correlacao_pearson",
    "motivo_qc_principal",
]


excluidos[
    colunas_excluidos
].sort_values(
    [
        "codigo",
        "ano",
    ]
).to_csv(
    SAIDA_EXCLUIDOS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 11. VALIDAR CASOS ESPERADOS
# ==========================================================

esperados = {
    ("A316", 2014),
    ("A316", 2015),
    ("A355", 2015),
    ("A402", 2005),
}


encontrados = set(
    zip(
        excluidos[
            "codigo"
        ].astype(str),

        excluidos[
            "ano"
        ].astype(int),
    )
)


if encontrados != esperados:

    raise RuntimeError(
        "Conjunto de anomalias temporais "
        "não corresponde aos quatro casos "
        "diagnosticados.\n"
        f"Encontrado: {sorted(encontrados)}"
    )


# ==========================================================
# 12. SALVAR BASE ANALÍTICA
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


base.to_csv(
    SAIDA_CSV,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 13. RESUMO
# ==========================================================

resumo = pd.DataFrame(
    [
        {
            "registros_estacao_ano_total":
                len(base),

            "pares_amostra_completa":
                pares_totais,

            "anomalias_temporais_excluidas":
                len(excluidos),

            "pares_excluidos_principal":
                pares_excluidos,

            "percentual_pares_excluidos":
                pct_excluido,

            "pares_validacao_principal":
                pares_principal,

            "estacao_ano_resumo_min100":
                int(
                    base[
                        "usar_resumo_estacao_ano"
                    ].sum()
                ),

            "estacao_ano_tendencia_10a":
                int(
                    base[
                        "usar_tendencia_10a"
                    ].sum()
                ),

            "estacao_ano_tendencia_15a":
                int(
                    base[
                        "usar_tendencia_15a"
                    ].sum()
                ),

            "estacoes_tendencia_10a":
                int(
                    base.loc[
                        base[
                            "usar_tendencia_10a"
                        ],
                        "codigo",
                    ]
                    .nunique()
                ),

            "estacoes_tendencia_15a":
                int(
                    base.loc[
                        base[
                            "usar_tendencia_15a"
                        ],
                        "codigo",
                    ]
                    .nunique()
                ),
        }
    ]
)


resumo.to_csv(
    SAIDA_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 14. IMPRESSÃO
# ==========================================================

print("\n" + "=" * 90)
print("AMOSTRA PRINCIPAL")
print("=" * 90)


print(
    f"\nPares na amostra completa: "
    f"{pares_totais:,}"
)


print(
    f"Pares excluídos pelo QC principal: "
    f"{pares_excluidos:,}"
)


print(
    f"Percentual excluído: "
    f"{pct_excluido:.6f}%"
)


print(
    f"Pares na validação principal: "
    f"{pares_principal:,}"
)


print(
    "\nEstação-ano excluídos:"
)


print(
    excluidos[
        colunas_excluidos
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
# 15. REDE DE TENDÊNCIA
# ==========================================================

print("\n" + "=" * 90)
print("REDE DE TENDÊNCIA")
print("=" * 90)


print(
    f"\nEstações candidatas 10 anos: "
    f"{base.loc[base['usar_tendencia_10a'], 'codigo'].nunique():,}"
)


print(
    f"Estações candidatas 15 anos: "
    f"{base.loc[base['usar_tendencia_15a'], 'codigo'].nunique():,}"
)


print(
    f"\nRegistros estação-ano usados "
    f"na tendência 10 anos: "
    f"{base['usar_tendencia_10a'].sum():,}"
)


print(
    f"Registros estação-ano usados "
    f"na tendência 15 anos: "
    f"{base['usar_tendencia_15a'].sum():,}"
)


# ==========================================================
# 16. ARQUIVOS
# ==========================================================

print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    "\nBase analítica:"
)

print(
    SAIDA_PARQUET
)


print(
    "\nCSV da base analítica:"
)

print(
    SAIDA_CSV
)


print(
    "\nExclusões da validação principal:"
)

print(
    SAIDA_EXCLUIDOS
)


print(
    "\nResumo:"
)

print(
    SAIDA_RESUMO
)


print("\n" + "=" * 90)
print("AMOSTRA ANALÍTICA DEFINIDA")
print("=" * 90)