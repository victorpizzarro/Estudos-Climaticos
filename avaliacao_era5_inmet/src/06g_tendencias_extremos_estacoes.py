from __future__ import annotations

import math
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

ALPHA = 0.05

MIN_ANOS_PRINCIPAL = 15
MIN_ANOS_SENSIBILIDADE = 10


UF_REGIAO = {
    # Norte
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",

    # Nordeste
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",

    # Centro-Oeste
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",

    # Sudeste
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",

    # Sul
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}


ORDEM_AREAS = [
    "Brasil",
    "Norte",
    "Nordeste",
    "Centro-Oeste",
    "Sudeste",
    "Sul",
]


VARIAVEIS = {
    "tmax_inmet": {
        "coluna": "tmax_inmet_anual_c",
        "descricao": "Máxima anual INMET",
    },
    "tmax_era5": {
        "coluna": "tmax_era5_anual_c",
        "descricao": "Máxima anual ERA5",
    },
    "delta_tmax": {
        "coluna": "diferenca_maximos_anuais_c",
        "descricao": "Diferença das máximas anuais ERA5 - INMET",
    },
}


REDES = {
    "principal_15a": {
        "flag": "rede_extremos_15a",
        "min_anos": MIN_ANOS_PRINCIPAL,
        "descricao": ">=15 anos válidos",
        "esperado": 45,
    },
    "sensibilidade_10a": {
        "flag": "rede_extremos_10a",
        "min_anos": MIN_ANOS_SENSIBILIDADE,
        "descricao": ">=10 anos válidos",
        "esperado": 214,
    },
}


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


ARQUIVO_ENTRADA = (
    ANNUAL_DIR
    / "maximas_anuais_estacoes_tendencia.parquet"
)


SAIDA_PARQUET = (
    ANNUAL_DIR
    / "tendencias_extremos_estacoes.parquet"
)


SAIDA_CSV = (
    TABLES_DIR
    / "tendencias_extremos_estacoes.csv"
)


SAIDA_RESUMO_REDE = (
    TABLES_DIR
    / "resumo_tendencias_extremos_rede.csv"
)


SAIDA_RESUMO_REGIAO = (
    TABLES_DIR
    / "resumo_tendencias_extremos_regiao.csv"
)


SAIDA_SIGNIFICATIVAS = (
    TABLES_DIR
    / "tendencias_extremos_significativas_fdr.csv"
)


SAIDA_COMPARACAO = (
    TABLES_DIR
    / "comparacao_tendencias_inmet_era5.csv"
)


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================


def converter_bool(serie: pd.Series) -> pd.Series:

    if serie.dtype == bool:
        return serie.fillna(False)

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
        .astype(bool)
    )



def primeiro_valido(serie: pd.Series):

    serie = serie.dropna()

    if serie.empty:
        return np.nan

    return serie.iloc[0]



def mediana_numerica(serie: pd.Series):

    valores = pd.to_numeric(
        serie,
        errors="coerce",
    ).dropna()

    if valores.empty:
        return np.nan

    return float(
        valores.median()
    )



def mann_kendall(
    anos: np.ndarray,
    valores: np.ndarray,
) -> dict:
    """
    Teste de Mann-Kendall clássico, bicaudal.

    O teste usa a ordem temporal dos anos. A variância de S
    recebe a correção padrão para empates nos valores.
    """

    anos = np.asarray(
        anos,
        dtype=float,
    )

    valores = np.asarray(
        valores,
        dtype=float,
    )

    mascara = (
        np.isfinite(anos)
        &
        np.isfinite(valores)
    )

    anos = anos[mascara]
    valores = valores[mascara]

    ordem = np.argsort(
        anos
    )

    anos = anos[ordem]
    valores = valores[ordem]

    n = len(
        valores
    )

    if n < 3:

        return {
            "mk_s": np.nan,
            "mk_var_s": np.nan,
            "mk_z": np.nan,
            "mk_tau": np.nan,
            "mk_p": np.nan,
        }

    s = 0

    for i in range(
        n - 1
    ):

        diferencas = (
            valores[i + 1:]
            -
            valores[i]
        )

        s += int(
            np.sign(
                diferencas
            ).sum()
        )

    _, contagens = np.unique(
        valores,
        return_counts=True,
    )

    termos_empate = contagens[
        contagens > 1
    ]

    correcao_empates = float(
        np.sum(
            termos_empate
            *
            (termos_empate - 1)
            *
            (2 * termos_empate + 5)
        )
    )

    var_s = (
        n
        *
        (n - 1)
        *
        (2 * n + 5)
        -
        correcao_empates
    ) / 18.0

    if var_s <= 0:

        z = 0.0
        p = 1.0

    elif s > 0:

        z = (
            s - 1
        ) / math.sqrt(
            var_s
        )

        p = math.erfc(
            abs(z)
            /
            math.sqrt(2.0)
        )

    elif s < 0:

        z = (
            s + 1
        ) / math.sqrt(
            var_s
        )

        p = math.erfc(
            abs(z)
            /
            math.sqrt(2.0)
        )

    else:

        z = 0.0
        p = 1.0

    denominador_tau = (
        n
        *
        (n - 1)
        /
        2.0
    )

    tau = (
        s
        /
        denominador_tau
        if denominador_tau > 0
        else np.nan
    )

    return {
        "mk_s": float(s),
        "mk_var_s": float(var_s),
        "mk_z": float(z),
        "mk_tau": float(tau),
        "mk_p": float(p),
    }



def sen_slope(
    anos: np.ndarray,
    valores: np.ndarray,
) -> float:
    """
    Sen's Slope usando todas as inclinações pareadas:

        (y_j - y_i) / (ano_j - ano_i)

    O uso do ano real no denominador é importante porque
    algumas estações têm lacunas na série anual.
    """

    anos = np.asarray(
        anos,
        dtype=float,
    )

    valores = np.asarray(
        valores,
        dtype=float,
    )

    mascara = (
        np.isfinite(anos)
        &
        np.isfinite(valores)
    )

    anos = anos[mascara]
    valores = valores[mascara]

    ordem = np.argsort(
        anos
    )

    anos = anos[ordem]
    valores = valores[ordem]

    n = len(
        valores
    )

    if n < 2:
        return np.nan

    slopes = []

    for i in range(
        n - 1
    ):

        delta_ano = (
            anos[i + 1:]
            -
            anos[i]
        )

        delta_valor = (
            valores[i + 1:]
            -
            valores[i]
        )

        validos = (
            delta_ano
            !=
            0
        )

        if validos.any():

            slopes.extend(
                (
                    delta_valor[validos]
                    /
                    delta_ano[validos]
                ).tolist()
            )

    if not slopes:
        return np.nan

    return float(
        np.median(
            np.asarray(
                slopes,
                dtype=float,
            )
        )
    )



def autocorrelacao_lag1(
    anos: np.ndarray,
    valores: np.ndarray,
) -> tuple[float, int]:
    """
    Correlação lag-1 apenas para pares de anos consecutivos.

    É diagnóstica. O p-valor de Mann-Kendall abaixo continua
    sendo o clássico, sem correção de autocorrelação.
    """

    df = pd.DataFrame(
        {
            "ano": anos,
            "valor": valores,
        }
    ).dropna()

    if len(df) < 3:
        return np.nan, 0

    df = (
        df.sort_values(
            "ano"
        )
        .drop_duplicates(
            subset=[
                "ano",
            ],
            keep="last",
        )
    )

    mapa = dict(
        zip(
            df[
                "ano"
            ].astype(int),
            df[
                "valor"
            ].astype(float),
        )
    )

    x = []
    y = []

    for ano in sorted(
        mapa
    ):

        if (
            ano + 1
        ) in mapa:

            x.append(
                mapa[ano]
            )

            y.append(
                mapa[
                    ano + 1
                ]
            )

    n_pares = len(
        x
    )

    if n_pares < 3:
        return np.nan, n_pares

    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    if (
        np.std(x) == 0
        or
        np.std(y) == 0
    ):
        return np.nan, n_pares

    r = float(
        np.corrcoef(
            x,
            y,
        )[0, 1]
    )

    return r, n_pares



def ajustar_fdr_bh(
    pvalores: pd.Series,
) -> pd.Series:
    """
    Benjamini-Hochberg para controle da taxa de falsas descobertas.
    """

    resultado = pd.Series(
        np.nan,
        index=pvalores.index,
        dtype=float,
    )

    validos = (
        pvalores
        .dropna()
        .astype(float)
    )

    m = len(
        validos
    )

    if m == 0:
        return resultado

    ordenados = validos.sort_values()

    ranks = np.arange(
        1,
        m + 1,
        dtype=float,
    )

    q_bruto = (
        ordenados.to_numpy()
        *
        m
        /
        ranks
    )

    q_monotono = np.minimum.accumulate(
        q_bruto[::-1]
    )[::-1]

    q_monotono = np.minimum(
        q_monotono,
        1.0,
    )

    resultado.loc[
        ordenados.index
    ] = q_monotono

    return resultado



def classificar_tendencia(
    slope: float,
    pvalor: float,
    alpha: float = ALPHA,
) -> str:

    if (
        pd.isna(slope)
        or
        pd.isna(pvalor)
    ):
        return "indeterminada"

    if pvalor >= alpha:
        return "sem_tendencia_significativa"

    if slope > 0:
        return "crescente"

    if slope < 0:
        return "decrescente"

    return "sem_tendencia_significativa"


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("MANN-KENDALL + SEN'S SLOPE DAS MÁXIMAS ANUAIS")
print("=" * 90)

print(
    "\nAnálise principal: "
    ">=15 anos válidos"
)

print(
    "Análise de sensibilidade: "
    ">=10 anos válidos"
)

print(
    f"\nNível de significância: "
    f"alpha = {ALPHA:.2f}"
)

print(
    "Correção de testes múltiplos: "
    "Benjamini-Hochberg (FDR)"
)

print(
    "\nIMPORTANTE: os p-valores de Mann-Kendall "
    "são do teste clássico."
)

print(
    "A autocorrelação lag-1 é calculada apenas "
    "como diagnóstico."
)


# ==========================================================
# 1. CARREGAR BASE
# ==========================================================

if not ARQUIVO_ENTRADA.exists():

    raise FileNotFoundError(
        f"Arquivo não encontrado:\n"
        f"{ARQUIVO_ENTRADA}"
    )


base = pd.read_parquet(
    ARQUIVO_ENTRADA
)


print(
    f"\nRegistros estação-ano: "
    f"{len(base):,}"
)

print(
    f"Estações totais: "
    f"{base['codigo'].nunique():,}"
)


# ==========================================================
# 2. VALIDAR COLUNAS
# ==========================================================

colunas_obrigatorias = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "ano_valido_extremos",
    "rede_extremos_10a",
    "rede_extremos_15a",
    "tmax_inmet_anual_c",
    "tmax_era5_anual_c",
    "diferenca_maximos_anuais_c",
]


faltantes = [
    coluna
    for coluna in colunas_obrigatorias
    if coluna not in base.columns
]


if faltantes:

    raise RuntimeError(
        "Colunas obrigatórias ausentes: "
        f"{faltantes}"
    )


# ==========================================================
# 3. NORMALIZAR TIPOS E REGIÕES
# ==========================================================

base[
    "ano"
] = pd.to_numeric(
    base[
        "ano"
    ],
    errors="raise",
).astype(int)


base[
    "codigo"
] = (
    base[
        "codigo"
    ]
    .astype(str)
    .str.strip()
)


base[
    "uf"
] = (
    base[
        "uf"
    ]
    .astype(str)
    .str.strip()
    .str.upper()
)


for coluna in [
    "ano_valido_extremos",
    "rede_extremos_10a",
    "rede_extremos_15a",
]:

    base[
        coluna
    ] = converter_bool(
        base[
            coluna
        ]
    )


base[
    "regiao_corrigida"
] = (
    base[
        "uf"
    ]
    .map(
        UF_REGIAO
    )
)


ufs_sem_regiao = (
    base.loc[
        base[
            "regiao_corrigida"
        ].isna(),
        "uf",
    ]
    .drop_duplicates()
    .tolist()
)


if ufs_sem_regiao:

    raise RuntimeError(
        "UFs sem região definida: "
        f"{ufs_sem_regiao}"
    )


# ==========================================================
# 4. VALIDAR AS DUAS REDES
# ==========================================================

print("\n" + "=" * 90)
print("VALIDAÇÃO DAS REDES")
print("=" * 90)


codigos_por_rede = {}


for nome_rede, config in REDES.items():

    flag = config[
        "flag"
    ]

    codigos = set(
        base.loc[
            base[
                flag
            ],
            "codigo",
        ].unique()
    )

    codigos_por_rede[
        nome_rede
    ] = codigos

    encontrado = len(
        codigos
    )

    esperado = config[
        "esperado"
    ]

    print(
        f"\n{nome_rede}: "
        f"{encontrado:,} estações"
    )

    if encontrado != esperado:

        raise RuntimeError(
            f"Rede {nome_rede}: "
            f"esperávamos {esperado} estações, "
            f"mas encontramos {encontrado}."
        )


if not codigos_por_rede[
    "principal_15a"
].issubset(
    codigos_por_rede[
        "sensibilidade_10a"
    ]
):

    raise RuntimeError(
        "A rede principal de 15 anos não é "
        "subconjunto da rede de 10 anos."
    )


# ==========================================================
# 5. METADADOS POR ESTAÇÃO
# ==========================================================

agregacoes_metadata = {
    "estacao": (
        "estacao",
        primeiro_valido,
    ),
    "uf": (
        "uf",
        primeiro_valido,
    ),
    "regiao": (
        "regiao_corrigida",
        primeiro_valido,
    ),
}


for coluna in [
    "latitude",
    "longitude",
    "altitude_m",
]:

    if coluna in base.columns:

        agregacoes_metadata[
            coluna
        ] = (
            coluna,
            mediana_numerica,
        )


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
        **agregacoes_metadata
    )
)


# ==========================================================
# 6. CALCULAR TENDÊNCIAS POR ESTAÇÃO
# ==========================================================

print("\n" + "=" * 90)
print("CALCULANDO TENDÊNCIAS")
print("=" * 90)


resultados = []


for nome_rede, config_rede in REDES.items():

    flag_rede = config_rede[
        "flag"
    ]

    min_anos = config_rede[
        "min_anos"
    ]

    codigos = sorted(
        codigos_por_rede[
            nome_rede
        ]
    )

    print(
        f"\n{nome_rede} "
        f"({len(codigos):,} estações)"
    )

    for codigo in codigos:

        dados_estacao = (
            base[
                (
                    base[
                        "codigo"
                    ]
                    ==
                    codigo
                )
                &
                base[
                    "ano_valido_extremos"
                ]
            ]
            .sort_values(
                "ano"
            )
            .copy()
        )

        if len(
            dados_estacao
        ) < min_anos:

            raise RuntimeError(
                f"{codigo} pertence à rede "
                f"{nome_rede}, mas possui apenas "
                f"{len(dados_estacao)} anos válidos."
            )

        anos_estacao = (
            dados_estacao[
                "ano"
            ]
            .astype(int)
            .to_numpy()
        )

        for nome_variavel, config_variavel in VARIAVEIS.items():

            coluna = config_variavel[
                "coluna"
            ]

            dados_variavel = (
                dados_estacao[
                    [
                        "ano",
                        coluna,
                    ]
                ]
                .dropna()
                .sort_values(
                    "ano"
                )
            )

            anos = (
                dados_variavel[
                    "ano"
                ]
                .astype(int)
                .to_numpy()
            )

            valores = (
                pd.to_numeric(
                    dados_variavel[
                        coluna
                    ],
                    errors="coerce",
                )
                .to_numpy(
                    dtype=float
                )
            )

            mascara = (
                np.isfinite(
                    valores
                )
            )

            anos = anos[
                mascara
            ]

            valores = valores[
                mascara
            ]

            n_anos = len(
                anos
            )

            if n_anos < min_anos:

                raise RuntimeError(
                    f"{codigo} / {nome_variavel} / "
                    f"{nome_rede}: apenas {n_anos} "
                    "valores anuais válidos."
                )

            mk = mann_kendall(
                anos,
                valores,
            )

            slope_ano = sen_slope(
                anos,
                valores,
            )

            rho1, n_pares_lag1 = autocorrelacao_lag1(
                anos,
                valores,
            )

            primeiro_ano = int(
                anos.min()
            )

            ultimo_ano = int(
                anos.max()
            )

            amplitude_anos = (
                ultimo_ano
                -
                primeiro_ano
                +
                1
            )

            anos_faltantes = (
                amplitude_anos
                -
                n_anos
            )

            resultados.append(
                {
                    "rede":
                        nome_rede,

                    "descricao_rede":
                        config_rede[
                            "descricao"
                        ],

                    "codigo":
                        codigo,

                    "variavel":
                        nome_variavel,

                    "descricao_variavel":
                        config_variavel[
                            "descricao"
                        ],

                    "n_anos":
                        n_anos,

                    "primeiro_ano":
                        primeiro_ano,

                    "ultimo_ano":
                        ultimo_ano,

                    "amplitude_anos":
                        amplitude_anos,

                    "anos_faltantes_na_amplitude":
                        anos_faltantes,

                    "valor_min_c":
                        float(
                            np.min(
                                valores
                            )
                        ),

                    "valor_mediano_c":
                        float(
                            np.median(
                                valores
                            )
                        ),

                    "valor_medio_c":
                        float(
                            np.mean(
                                valores
                            )
                        ),

                    "valor_max_c":
                        float(
                            np.max(
                                valores
                            )
                        ),

                    "sen_slope_c_ano":
                        slope_ano,

                    "sen_slope_c_decada":
                        (
                            slope_ano
                            *
                            10.0
                            if pd.notna(
                                slope_ano
                            )
                            else np.nan
                        ),

                    "mk_s":
                        mk[
                            "mk_s"
                        ],

                    "mk_var_s":
                        mk[
                            "mk_var_s"
                        ],

                    "mk_z":
                        mk[
                            "mk_z"
                        ],

                    "mk_tau":
                        mk[
                            "mk_tau"
                        ],

                    "mk_p":
                        mk[
                            "mk_p"
                        ],

                    "rho1_anos_consecutivos":
                        rho1,

                    "n_pares_rho1":
                        n_pares_lag1,
                }
            )


resultado = pd.DataFrame(
    resultados
)


# ==========================================================
# 7. ADICIONAR METADADOS
# ==========================================================

resultado = resultado.merge(
    metadata,
    on="codigo",
    how="left",
    validate="many_to_one",
)


# ==========================================================
# 8. CORREÇÃO FDR BENJAMINI-HOCHBERG
#
# A correção é feita separadamente para cada combinação:
# rede × variável.
# ==========================================================

resultado[
    "mk_p_fdr"
] = np.nan


for (
    nome_rede,
    nome_variavel,
), indices in resultado.groupby(
    [
        "rede",
        "variavel",
    ]
).groups.items():

    indices = list(
        indices
    )

    resultado.loc[
        indices,
        "mk_p_fdr",
    ] = ajustar_fdr_bh(
        resultado.loc[
            indices,
            "mk_p",
        ]
    )


resultado[
    "significativo_p05"
] = (
    resultado[
        "mk_p"
    ]
    <
    ALPHA
)


resultado[
    "significativo_fdr05"
] = (
    resultado[
        "mk_p_fdr"
    ]
    <
    ALPHA
)


resultado[
    "tendencia_mk_p05"
] = [
    classificar_tendencia(
        slope,
        pvalor,
        ALPHA,
    )
    for slope, pvalor in zip(
        resultado[
            "sen_slope_c_ano"
        ],
        resultado[
            "mk_p"
        ],
    )
]


resultado[
    "tendencia_mk_fdr05"
] = [
    classificar_tendencia(
        slope,
        pvalor,
        ALPHA,
    )
    for slope, pvalor in zip(
        resultado[
            "sen_slope_c_ano"
        ],
        resultado[
            "mk_p_fdr"
        ],
    )
]


resultado[
    "autocorrelacao_abs_ge_03"
] = (
    resultado[
        "rho1_anos_consecutivos"
    ]
    .abs()
    >=
    0.30
)


# ==========================================================
# 9. VALIDAR QUANTIDADE DE RESULTADOS
# ==========================================================

for nome_rede, config in REDES.items():

    esperado_estacoes = config[
        "esperado"
    ]

    for nome_variavel in VARIAVEIS:

        n = resultado[
            (
                resultado[
                    "rede"
                ]
                ==
                nome_rede
            )
            &
            (
                resultado[
                    "variavel"
                ]
                ==
                nome_variavel
            )
        ][
            "codigo"
        ].nunique()

        if n != esperado_estacoes:

            raise RuntimeError(
                f"{nome_rede} / {nome_variavel}: "
                f"esperávamos {esperado_estacoes} "
                f"estações, encontramos {n}."
            )


# ==========================================================
# 10. RESUMO POR REDE
# ==========================================================

resumo_rede = []


for nome_rede in REDES:

    for nome_variavel in VARIAVEIS:

        grupo = resultado[
            (
                resultado[
                    "rede"
                ]
                ==
                nome_rede
            )
            &
            (
                resultado[
                    "variavel"
                ]
                ==
                nome_variavel
            )
        ].copy()

        slopes = grupo[
            "sen_slope_c_decada"
        ].dropna()

        n_estacoes = len(
            grupo
        )

        n_pos = int(
            (
                grupo[
                    "sen_slope_c_decada"
                ]
                >
                0
            ).sum()
        )

        n_neg = int(
            (
                grupo[
                    "sen_slope_c_decada"
                ]
                <
                0
            ).sum()
        )

        n_zero = int(
            (
                grupo[
                    "sen_slope_c_decada"
                ]
                ==
                0
            ).sum()
        )

        n_sig = int(
            grupo[
                "significativo_p05"
            ].sum()
        )

        n_sig_fdr = int(
            grupo[
                "significativo_fdr05"
            ].sum()
        )

        n_cresc_fdr = int(
            (
                grupo[
                    "tendencia_mk_fdr05"
                ]
                ==
                "crescente"
            ).sum()
        )

        n_decresc_fdr = int(
            (
                grupo[
                    "tendencia_mk_fdr05"
                ]
                ==
                "decrescente"
            ).sum()
        )

        resumo_rede.append(
            {
                "rede":
                    nome_rede,

                "variavel":
                    nome_variavel,

                "n_estacoes":
                    n_estacoes,

                "sen_mediana_c_decada":
                    float(
                        slopes.median()
                    ),

                "sen_media_c_decada":
                    float(
                        slopes.mean()
                    ),

                "sen_p25_c_decada":
                    float(
                        slopes.quantile(
                            0.25
                        )
                    ),

                "sen_p75_c_decada":
                    float(
                        slopes.quantile(
                            0.75
                        )
                    ),

                "n_slope_positivo":
                    n_pos,

                "n_slope_negativo":
                    n_neg,

                "n_slope_zero":
                    n_zero,

                "pct_slope_positivo":
                    100.0
                    *
                    n_pos
                    /
                    n_estacoes,

                "n_significativo_p05":
                    n_sig,

                "pct_significativo_p05":
                    100.0
                    *
                    n_sig
                    /
                    n_estacoes,

                "n_significativo_fdr05":
                    n_sig_fdr,

                "pct_significativo_fdr05":
                    100.0
                    *
                    n_sig_fdr
                    /
                    n_estacoes,

                "n_crescente_fdr05":
                    n_cresc_fdr,

                "n_decrescente_fdr05":
                    n_decresc_fdr,

                "n_autocorr_abs_ge_03":
                    int(
                        grupo[
                            "autocorrelacao_abs_ge_03"
                        ].sum()
                    ),
            }
        )


resumo_rede = pd.DataFrame(
    resumo_rede
)


# ==========================================================
# 11. RESUMO POR REGIÃO
# ==========================================================

resumo_regiao = []


for nome_rede in REDES:

    for nome_variavel in VARIAVEIS:

        dados_rv = resultado[
            (
                resultado[
                    "rede"
                ]
                ==
                nome_rede
            )
            &
            (
                resultado[
                    "variavel"
                ]
                ==
                nome_variavel
            )
        ].copy()

        for area in ORDEM_AREAS:

            if area == "Brasil":

                grupo = dados_rv.copy()

            else:

                grupo = dados_rv[
                    dados_rv[
                        "regiao"
                    ]
                    ==
                    area
                ].copy()

            if grupo.empty:
                continue

            slopes = grupo[
                "sen_slope_c_decada"
            ].dropna()

            n_estacoes = len(
                grupo
            )

            n_pos = int(
                (
                    grupo[
                        "sen_slope_c_decada"
                    ]
                    >
                    0
                ).sum()
            )

            n_sig_fdr = int(
                grupo[
                    "significativo_fdr05"
                ].sum()
            )

            resumo_regiao.append(
                {
                    "rede":
                        nome_rede,

                    "variavel":
                        nome_variavel,

                    "area":
                        area,

                    "n_estacoes":
                        n_estacoes,

                    "sen_mediana_c_decada":
                        float(
                            slopes.median()
                        ),

                    "sen_media_c_decada":
                        float(
                            slopes.mean()
                        ),

                    "sen_p25_c_decada":
                        float(
                            slopes.quantile(
                                0.25
                            )
                        ),

                    "sen_p75_c_decada":
                        float(
                            slopes.quantile(
                                0.75
                            )
                        ),

                    "n_slope_positivo":
                        n_pos,

                    "pct_slope_positivo":
                        100.0
                        *
                        n_pos
                        /
                        n_estacoes,

                    "n_significativo_fdr05":
                        n_sig_fdr,

                    "pct_significativo_fdr05":
                        100.0
                        *
                        n_sig_fdr
                        /
                        n_estacoes,
                }
            )


resumo_regiao = pd.DataFrame(
    resumo_regiao
)


# ==========================================================
# 12. COMPARAÇÃO INMET × ERA5 × DELTA POR ESTAÇÃO
# ==========================================================

indices_comparacao = [
    "rede",
    "codigo",
    "estacao",
    "uf",
    "regiao",
]


comparacao = resultado.pivot_table(
    index=indices_comparacao,
    columns="variavel",
    values=[
        "n_anos",
        "sen_slope_c_ano",
        "sen_slope_c_decada",
        "mk_tau",
        "mk_p",
        "mk_p_fdr",
        "significativo_fdr05",
    ],
    aggfunc="first",
)


comparacao.columns = [
    f"{metrica}_{variavel}"
    for metrica, variavel in comparacao.columns
]


comparacao = (
    comparacao
    .reset_index()
)


comparacao[
    "diferenca_sen_era5_menos_inmet_c_decada"
] = (
    comparacao[
        "sen_slope_c_decada_tmax_era5"
    ]
    -
    comparacao[
        "sen_slope_c_decada_tmax_inmet"
    ]
)


comparacao[
    "mesmo_sinal_sen_inmet_era5"
] = (
    np.sign(
        comparacao[
            "sen_slope_c_decada_tmax_inmet"
        ]
    )
    ==
    np.sign(
        comparacao[
            "sen_slope_c_decada_tmax_era5"
        ]
    )
)


comparacao[
    "ambos_significativos_fdr"
] = (
    comparacao[
        "significativo_fdr05_tmax_inmet"
    ].fillna(False)
    &
    comparacao[
        "significativo_fdr05_tmax_era5"
    ].fillna(False)
)


# ==========================================================
# 13. ORDENAR E SALVAR
# ==========================================================

resultado = (
    resultado
    .sort_values(
        [
            "rede",
            "variavel",
            "codigo",
        ]
    )
    .reset_index(
        drop=True
    )
)


resultado.to_parquet(
    SAIDA_PARQUET,
    index=False,
)


resultado.to_csv(
    SAIDA_CSV,
    index=False,
    encoding="utf-8",
)


resumo_rede.to_csv(
    SAIDA_RESUMO_REDE,
    index=False,
    encoding="utf-8",
)


resumo_regiao.to_csv(
    SAIDA_RESUMO_REGIAO,
    index=False,
    encoding="utf-8",
)


significativas = (
    resultado[
        resultado[
            "significativo_fdr05"
        ]
    ]
    .copy()
)


significativas.to_csv(
    SAIDA_SIGNIFICATIVAS,
    index=False,
    encoding="utf-8",
)


comparacao.to_csv(
    SAIDA_COMPARACAO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 14. IMPRIMIR RESUMO PRINCIPAL
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO DAS TENDÊNCIAS POR REDE")
print("=" * 90)


print(
    resumo_rede.to_string(
        index=False,
        float_format=lambda x:
            f"{x:.4f}",
    )
)


print("\n" + "=" * 90)
print("REDE PRINCIPAL >=15 ANOS - RESUMO REGIONAL")
print("=" * 90)


principal_regional = resumo_regiao[
    resumo_regiao[
        "rede"
    ]
    ==
    "principal_15a"
]


print(
    principal_regional.to_string(
        index=False,
        float_format=lambda x:
            f"{x:.4f}",
    )
)


# ==========================================================
# 15. ESTAÇÕES FDR-SIGNIFICATIVAS DA REDE PRINCIPAL
# ==========================================================

print("\n" + "=" * 90)
print("ESTAÇÕES SIGNIFICATIVAS APÓS FDR - REDE PRINCIPAL")
print("=" * 90)


sig_principal = (
    resultado[
        (
            resultado[
                "rede"
            ]
            ==
            "principal_15a"
        )
        &
        resultado[
            "significativo_fdr05"
        ]
    ]
    .copy()
)


if sig_principal.empty:

    print(
        "\nNenhuma tendência permaneceu "
        "significativa após FDR."
    )

else:

    colunas_print = [
        "codigo",
        "estacao",
        "uf",
        "regiao",
        "variavel",
        "n_anos",
        "sen_slope_c_decada",
        "mk_tau",
        "mk_p",
        "mk_p_fdr",
        "tendencia_mk_fdr05",
        "rho1_anos_consecutivos",
    ]

    print(
        sig_principal[
            colunas_print
        ]
        .sort_values(
            [
                "variavel",
                "sen_slope_c_decada",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .to_string(
            index=False,
            float_format=lambda x:
                f"{x:.5f}",
        )
    )


# ==========================================================
# 16. COMPARAÇÃO DAS SLOPES INMET × ERA5
# ==========================================================

print("\n" + "=" * 90)
print("CONCORDÂNCIA DO SINAL DAS TENDÊNCIAS INMET × ERA5")
print("=" * 90)


for nome_rede in REDES:

    subset = comparacao[
        comparacao[
            "rede"
        ]
        ==
        nome_rede
    ]

    n = len(
        subset
    )

    mesmo_sinal = int(
        subset[
            "mesmo_sinal_sen_inmet_era5"
        ].sum()
    )

    ambos_sig = int(
        subset[
            "ambos_significativos_fdr"
        ].sum()
    )

    print(
        f"\n{nome_rede}:"
    )

    print(
        f"  estações: {n:,}"
    )

    print(
        f"  mesmo sinal Sen INMET/ERA5: "
        f"{mesmo_sinal:,} "
        f"({100 * mesmo_sinal / n:.1f}%)"
    )

    print(
        f"  INMET e ERA5 ambos significativos após FDR: "
        f"{ambos_sig:,}"
    )


# ==========================================================
# 17. ARQUIVOS GERADOS
# ==========================================================

print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


for caminho in [
    SAIDA_PARQUET,
    SAIDA_CSV,
    SAIDA_RESUMO_REDE,
    SAIDA_RESUMO_REGIAO,
    SAIDA_SIGNIFICATIVAS,
    SAIDA_COMPARACAO,
]:

    print(
        caminho
    )


print("\n" + "=" * 90)
print("TENDÊNCIAS DAS MÁXIMAS ANUAIS CONCLUÍDAS")
print("=" * 90)
