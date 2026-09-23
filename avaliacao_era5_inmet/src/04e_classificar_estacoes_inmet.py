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

ERA5_LAT_MIN = -34.0
ERA5_LAT_MAX = 6.0

ERA5_LON_MIN = -74.0
ERA5_LON_MAX = -34.0


COBERTURA_TENDENCIA = 0.80

MIN_ANOS_TENDENCIA_10 = 10
MIN_ANOS_TENDENCIA_15 = 15

MAX_DESLOCAMENTO_TENDENCIA_KM = 5.0


# Flags térmicas.
# Servem para identificar casos a investigar.
TEMP_MIN_FLAG = -20.0
TEMP_MAX_FLAG = 55.0


# ==========================================================
# CAMINHOS
# ==========================================================

PROCESSED_STATIONS_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
)


PROCESSED_STATIONS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


CATALOGO_ANUAL = (
    TABLES_DIR
    / "catalogo_estacoes_inmet_por_ano.csv"
)


QC_ESTACAO_ANO = (
    TABLES_DIR
    / "qc_inmet_estacoes_por_ano.csv"
)


CATALOGO_ESTACOES = (
    PROCESSED_STATIONS_DIR
    / "catalogo_estacoes_inmet.csv"
)


SAIDA_ELEGIBILIDADE = (
    PROCESSED_STATIONS_DIR
    / "estacoes_inmet_ano_elegibilidade.csv"
)


SAIDA_TENDENCIA = (
    PROCESSED_STATIONS_DIR
    / "estacoes_inmet_candidatas_tendencia.csv"
)


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("CLASSIFICAÇÃO DAS ESTAÇÕES INMET")
print("=" * 90)

print(
    "\nObjetivos:"
)

print(
    "1. Definir quais estação-ano podem ser "
    "pareadas com ERA5."
)

print(
    "2. Identificar candidatas para análises "
    "de tendência de longo prazo."
)

print(
    "\nNenhum dado horário será apagado."
)


# ==========================================================
# 1. VERIFICAR ARQUIVOS
# ==========================================================

for caminho in [
    CATALOGO_ANUAL,
    QC_ESTACAO_ANO,
    CATALOGO_ESTACOES,
]:

    if not caminho.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado:\n"
            f"{caminho}"
        )


# ==========================================================
# 2. CARREGAR
# ==========================================================

catalogo = pd.read_csv(
    CATALOGO_ANUAL
)


qc = pd.read_csv(
    QC_ESTACAO_ANO
)


estacoes = pd.read_csv(
    CATALOGO_ESTACOES
)


print(
    f"\nRegistros estação-ano no catálogo: "
    f"{len(catalogo):,}"
)


print(
    f"Registros estação-ano no QC: "
    f"{len(qc):,}"
)


print(
    f"Estações consolidadas: "
    f"{len(estacoes):,}"
)


# ==========================================================
# 3. CONVERSÕES NUMÉRICAS
# ==========================================================

for coluna in [
    "ano",
    "latitude",
    "longitude",
    "altitude_m",
    "temperaturas_validas",
    "datetime_validos",
    "duplicados_datetime",
]:

    if coluna in catalogo.columns:

        catalogo[coluna] = pd.to_numeric(
            catalogo[coluna],
            errors="coerce",
        )


for coluna in [
    "ano",
    "observacoes",
    "temperatura_min_c",
    "temperatura_max_c",
]:

    if coluna in qc.columns:

        qc[coluna] = pd.to_numeric(
            qc[coluna],
            errors="coerce",
        )


for coluna in [
    "latitude",
    "longitude",
    "deslocamento_max_coord_km",
]:

    if coluna in estacoes.columns:

        estacoes[coluna] = pd.to_numeric(
            estacoes[coluna],
            errors="coerce",
        )


# ==========================================================
# 4. JUNTAR CATÁLOGO + QC
# ==========================================================

base = catalogo.merge(
    qc[
        [
            "ano",
            "codigo",
            "observacoes",
            "temperatura_min_c",
            "temperatura_max_c",
            "primeiro_datetime",
            "ultimo_datetime",
        ]
    ],
    on=[
        "ano",
        "codigo",
    ],
    how="left",
    validate="one_to_one",
)


if len(base) != len(catalogo):

    raise RuntimeError(
        "Quantidade de registros mudou "
        "após merge catálogo × QC."
    )


# ==========================================================
# 5. COBERTURA DA TEMPERATURA
# ==========================================================

base[
    "cobertura_temp"
] = np.where(
    base[
        "datetime_validos"
    ] > 0,

    base[
        "temperaturas_validas"
    ]
    /
    base[
        "datetime_validos"
    ],

    np.nan,
)


base[
    "cobertura_temp_pct"
] = (
    base[
        "cobertura_temp"
    ]
    *
    100
)


# ==========================================================
# 6. VALIDADE DAS COORDENADAS
# ==========================================================

base[
    "coordenada_valida"
] = (
    np.isfinite(
        base[
            "latitude"
        ]
    )
    &
    np.isfinite(
        base[
            "longitude"
        ]
    )
    &
    (
        base[
            "latitude"
        ]
        >= -90
    )
    &
    (
        base[
            "latitude"
        ]
        <= 90
    )
    &
    (
        base[
            "longitude"
        ]
        >= -180
    )
    &
    (
        base[
            "longitude"
        ]
        <= 180
    )
)


# ==========================================================
# 7. ESTAÇÃO-ANO DENTRO DO DOMÍNIO ERA5
# ==========================================================

base[
    "dentro_dominio_era5"
] = (
    base[
        "coordenada_valida"
    ]
    &
    (
        base[
            "latitude"
        ]
        >= ERA5_LAT_MIN
    )
    &
    (
        base[
            "latitude"
        ]
        <= ERA5_LAT_MAX
    )
    &
    (
        base[
            "longitude"
        ]
        >= ERA5_LON_MIN
    )
    &
    (
        base[
            "longitude"
        ]
        <= ERA5_LON_MAX
    )
)


# ==========================================================
# 8. FLAG DE TEMPERATURA
# ==========================================================

base[
    "flag_temperatura_suspeita"
] = (
    (
        base[
            "temperatura_min_c"
        ]
        <
        TEMP_MIN_FLAG
    )
    |
    (
        base[
            "temperatura_max_c"
        ]
        >
        TEMP_MAX_FLAG
    )
)


# ==========================================================
# 9. OBSERVAÇÕES DISPONÍVEIS
# ==========================================================

base[
    "possui_observacoes"
] = (
    base[
        "observacoes"
    ]
    .fillna(0)
    >
    0
)


# ==========================================================
# 10. ELEGIBILIDADE PARA ERA5 × INMET
# ==========================================================

# Importante:
#
# não exigimos 80% de cobertura aqui.
#
# Uma estação com cobertura parcial ainda pode fornecer
# milhares de pares horários perfeitamente válidos.
#
# Cobertura rigorosa será usada nas análises de tendência.

base[
    "elegivel_pareamento"
] = (
    base[
        "coordenada_valida"
    ]
    &
    base[
        "dentro_dominio_era5"
    ]
    &
    base[
        "possui_observacoes"
    ]
)


# ==========================================================
# 11. MOTIVO DA EXCLUSÃO
# ==========================================================

def motivo_exclusao(
    linha,
):

    motivos = []


    if not linha[
        "coordenada_valida"
    ]:

        motivos.append(
            "coordenada_invalida"
        )


    elif not linha[
        "dentro_dominio_era5"
    ]:

        motivos.append(
            "fora_dominio_era5"
        )


    if not linha[
        "possui_observacoes"
    ]:

        motivos.append(
            "sem_observacoes_validas"
        )


    if not motivos:

        return "aprovada"


    return "|".join(
        motivos
    )


base[
    "motivo_elegibilidade"
] = base.apply(
    motivo_exclusao,
    axis=1,
)


# ==========================================================
# 12. ADICIONAR DESLOCAMENTO HISTÓRICO
# ==========================================================

dados_movimento = estacoes[
    [
        "codigo",
        "deslocamento_max_coord_km",
        "coordenada_suspeita",
    ]
].copy()


base = base.merge(
    dados_movimento,
    on="codigo",
    how="left",
    validate="many_to_one",
)


# ==========================================================
# 13. SALVAR ESTAÇÃO-ANO
# ==========================================================

colunas_saida = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "regiao",
    "latitude",
    "longitude",
    "altitude_m",
    "temperaturas_validas",
    "datetime_validos",
    "cobertura_temp",
    "cobertura_temp_pct",
    "observacoes",
    "temperatura_min_c",
    "temperatura_max_c",
    "primeiro_datetime",
    "ultimo_datetime",
    "coordenada_valida",
    "dentro_dominio_era5",
    "flag_temperatura_suspeita",
    "possui_observacoes",
    "elegivel_pareamento",
    "motivo_elegibilidade",
    "deslocamento_max_coord_km",
    "coordenada_suspeita",
]


base[
    colunas_saida
].to_csv(
    SAIDA_ELEGIBILIDADE,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 14. CANDIDATAS PARA TENDÊNCIA
# ==========================================================

print("\n" + "=" * 90)
print("CLASSIFICAÇÃO PARA TENDÊNCIAS")
print("=" * 90)


candidatas = []


for codigo, grupo in base.groupby(
    "codigo"
):

    # Somente anos espacialmente elegíveis
    elegiveis = grupo[
        grupo[
            "elegivel_pareamento"
        ]
    ].copy()


    anos_elegiveis = int(
        elegiveis[
            "ano"
        ].nunique()
    )


    anos_80 = elegiveis[
        elegiveis[
            "cobertura_temp"
        ]
        >= COBERTURA_TENDENCIA
    ]


    numero_anos_80 = int(
        anos_80[
            "ano"
        ].nunique()
    )


    if not anos_80.empty:

        primeiro_ano_80 = int(
            anos_80[
                "ano"
            ].min()
        )

        ultimo_ano_80 = int(
            anos_80[
                "ano"
            ].max()
        )

        amplitude_anos = (
            ultimo_ano_80
            -
            primeiro_ano_80
            +
            1
        )

    else:

        primeiro_ano_80 = np.nan
        ultimo_ano_80 = np.nan
        amplitude_anos = 0


    registro_estacao = estacoes[
        estacoes[
            "codigo"
        ]
        ==
        codigo
    ]


    if registro_estacao.empty:

        deslocamento = np.nan

        estavel = False

        nome = None
        uf = None
        regiao = None

    else:

        registro = (
            registro_estacao.iloc[0]
        )


        deslocamento = registro[
            "deslocamento_max_coord_km"
        ]


        nome = registro[
            "estacao"
        ]

        uf = registro[
            "uf"
        ]

        regiao = registro[
            "regiao"
        ]


        estavel = bool(
            pd.notna(
                deslocamento
            )
            and
            deslocamento
            <=
            MAX_DESLOCAMENTO_TENDENCIA_KM
        )


    candidata_10 = bool(
        estavel
        and
        numero_anos_80
        >= MIN_ANOS_TENDENCIA_10
    )


    candidata_15 = bool(
        estavel
        and
        numero_anos_80
        >= MIN_ANOS_TENDENCIA_15
    )


    candidatas.append(
        {
            "codigo":
                codigo,

            "estacao":
                nome,

            "uf":
                uf,

            "regiao":
                regiao,

            "anos_elegiveis":
                anos_elegiveis,

            "anos_cobertura_80":
                numero_anos_80,

            "primeiro_ano_80":
                primeiro_ano_80,

            "ultimo_ano_80":
                ultimo_ano_80,

            "amplitude_periodo_anos":
                amplitude_anos,

            "deslocamento_max_coord_km":
                deslocamento,

            "coordenada_estavel_5km":
                estavel,

            "candidata_tendencia_10a":
                candidata_10,

            "candidata_tendencia_15a":
                candidata_15,
        }
    )


df_candidatas = pd.DataFrame(
    candidatas
)


df_candidatas = (
    df_candidatas
    .sort_values(
        "codigo"
    )
    .reset_index(
        drop=True
    )
)


df_candidatas.to_csv(
    SAIDA_TENDENCIA,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 15. RESUMO
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO DE ELEGIBILIDADE")
print("=" * 90)


print(
    f"\nRegistros estação-ano: "
    f"{len(base):,}"
)


print(
    f"Elegíveis para pareamento: "
    f"{base['elegivel_pareamento'].sum():,}"
)


print(
    f"Excluídos do pareamento: "
    f"{(~base['elegivel_pareamento']).sum():,}"
)


print(
    "\nMotivos:"
)


print(
    base[
        "motivo_elegibilidade"
    ]
    .value_counts()
    .to_string()
)


print(
    f"\nEstação-ano com flag térmica: "
    f"{base['flag_temperatura_suspeita'].sum():,}"
)


print(
    "\nFlags térmicas:"
)


flags = base[
    base[
        "flag_temperatura_suspeita"
    ]
][
    [
        "ano",
        "codigo",
        "estacao",
        "latitude",
        "longitude",
        "temperatura_min_c",
        "temperatura_max_c",
        "dentro_dominio_era5",
    ]
]


if flags.empty:

    print(
        "Nenhuma."
    )

else:

    print(
        flags.to_string(
            index=False
        )
    )


print("\n" + "=" * 90)
print("REDE DE TENDÊNCIA")
print("=" * 90)


print(
    f"\nEstações únicas: "
    f"{len(df_candidatas):,}"
)


print(
    f"Coordenada estável <=5 km: "
    f"{df_candidatas['coordenada_estavel_5km'].sum():,}"
)


print(
    f"Candidatas >=10 anos com cobertura >=80%: "
    f"{df_candidatas['candidata_tendencia_10a'].sum():,}"
)


print(
    f"Candidatas >=15 anos com cobertura >=80%: "
    f"{df_candidatas['candidata_tendencia_15a'].sum():,}"
)


print(
    "\nArquivo estação-ano:"
)

print(
    SAIDA_ELEGIBILIDADE
)


print(
    "\nArquivo de candidatas à tendência:"
)

print(
    SAIDA_TENDENCIA
)


print("\n" + "=" * 90)
print("CLASSIFICAÇÃO CONCLUÍDA")
print("=" * 90)