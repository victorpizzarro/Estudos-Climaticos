from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# OBJETIVO
# ==========================================================
#
# Este script NÃO substitui o 06g.
#
# O 06g continua sendo a análise principal:
# - 45 estações com >=15 anos válidos
# - 214 estações com >=10 anos válidos
#
# Aqui fazemos uma ANÁLISE DE SENSIBILIDADE para
# autocorrelação usando somente trechos anuais consecutivos.
#
# Isso é necessário porque métodos de correção da
# autocorrelação pressupõem uma série temporal regularmente
# espaçada. Não é metodologicamente correto simplesmente
# "colar" anos separados por lacunas e tratá-los como
# observações anuais consecutivas.
#
# Método usado:
# Hamed-Rao Modified Mann-Kendall
#
# Referência metodológica:
# - Mann-Kendall clássico para direção/significância
# - Sen's Slope para magnitude
# - Hamed-Rao para corrigir a variância do MK em função
#   da autocorrelação significativa dos ranks detrendidos
#
# ==========================================================


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ALPHA = 0.05

MIN_ANOS_PRINCIPAL = 15
MIN_ANOS_SENSIBILIDADE = 10


# Contagens já verificadas no 06f / 06f1.
ESPERADO_PRINCIPAL_CONSECUTIVA = 9
ESPERADO_SENSIBILIDADE_CONSECUTIVA = 27


# ==========================================================
# REGIÕES
# ==========================================================

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


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


ARQUIVO_MAXIMAS = (
    ANNUAL_DIR
    / "maximas_anuais_estacoes_tendencia.parquet"
)


SAIDA_PARQUET = (
    ANNUAL_DIR
    / "tendencias_extremos_mk_modificado.parquet"
)


SAIDA_CSV = (
    TABLES_DIR
    / "tendencias_extremos_mk_modificado.csv"
)


SAIDA_RESUMO_REDE = (
    TABLES_DIR
    / "resumo_mk_modificado_rede.csv"
)


SAIDA_RESUMO_REGIAO = (
    TABLES_DIR
    / "resumo_mk_modificado_regiao.csv"
)


SAIDA_COMPARACAO = (
    TABLES_DIR
    / "comparacao_mk_classico_modificado.csv"
)


SAIDA_SEGMENTOS = (
    TABLES_DIR
    / "segmentos_consecutivos_extremos.csv"
)


# ==========================================================
# VARIÁVEIS
# ==========================================================

VARIAVEIS = {

    "tmax_inmet": {
        "coluna":
            "tmax_inmet_anual_c",

        "nome":
            "Tmax INMET",
    },

    "tmax_era5": {
        "coluna":
            "tmax_era5_anual_c",

        "nome":
            "Tmax ERA5",
    },

    "delta_tmax": {
        "coluna":
            "diferenca_maximos_anuais_c",

        "nome":
            "Delta Tmax (ERA5 - INMET)",
    },
}


# ==========================================================
# FUNÇÕES AUXILIARES
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


def primeiro_valido(serie):

    serie = serie.dropna()

    if serie.empty:

        return None

    return serie.iloc[0]


def maior_segmento_consecutivo(df):

    """
    Recebe os anos válidos de uma estação e retorna o
    maior trecho totalmente consecutivo.

    Em caso de empate no tamanho, mantém o trecho mais
    antigo. Assim não favorecemos deliberadamente os anos
    mais recentes.
    """

    if df.empty:

        return df.copy()


    df = (
        df
        .sort_values(
            "ano"
        )
        .drop_duplicates(
            subset=[
                "ano",
            ]
        )
        .reset_index(
            drop=True
        )
    )


    anos = (
        df[
            "ano"
        ]
        .astype(int)
        .to_numpy()
    )


    melhor_inicio = 0
    melhor_fim = 0

    inicio_atual = 0


    for i in range(
        1,
        len(
            anos
        ),
    ):

        if anos[i] == anos[i - 1] + 1:

            continue


        fim_atual = i - 1


        tamanho_atual = (
            fim_atual
            -
            inicio_atual
            +
            1
        )


        tamanho_melhor = (
            melhor_fim
            -
            melhor_inicio
            +
            1
        )


        if tamanho_atual > tamanho_melhor:

            melhor_inicio = inicio_atual
            melhor_fim = fim_atual


        inicio_atual = i


    # Último bloco
    fim_atual = (
        len(
            anos
        )
        -
        1
    )


    tamanho_atual = (
        fim_atual
        -
        inicio_atual
        +
        1
    )


    tamanho_melhor = (
        melhor_fim
        -
        melhor_inicio
        +
        1
    )


    if tamanho_atual > tamanho_melhor:

        melhor_inicio = inicio_atual
        melhor_fim = fim_atual


    return (
        df.iloc[
            melhor_inicio:
            melhor_fim + 1
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )


def mk_score(valores):

    x = np.asarray(
        valores,
        dtype=float,
    )


    n = len(
        x
    )


    s = 0


    for i in range(
        n - 1
    ):

        diferencas = (
            x[
                i + 1:
            ]
            -
            x[i]
        )


        s += int(
            np.sign(
                diferencas
            )
            .sum()
        )


    return s


def mk_variance(valores):

    """
    Variância do S do Mann-Kendall com correção para ties.
    """

    x = np.asarray(
        valores,
        dtype=float,
    )


    n = len(
        x
    )


    _, contagens = np.unique(
        x,
        return_counts=True,
    )


    ties = contagens[
        contagens
        >
        1
    ]


    termo_ties = float(
        np.sum(
            ties
            *
            (
                ties
                -
                1
            )
            *
            (
                2
                *
                ties
                +
                5
            )
        )
    )


    var_s = (
        n
        *
        (
            n
            -
            1
        )
        *
        (
            2
            *
            n
            +
            5
        )
        -
        termo_ties
    ) / 18.0


    return float(
        var_s
    )


def z_mk(
    s,
    var_s,
):

    if (
        not np.isfinite(
            var_s
        )
        or
        var_s <= 0
    ):

        return np.nan


    if s > 0:

        return (
            s
            -
            1
        ) / np.sqrt(
            var_s
        )


    if s < 0:

        return (
            s
            +
            1
        ) / np.sqrt(
            var_s
        )


    return 0.0


def p_bilateral_normal(z):

    if not np.isfinite(
        z
    ):

        return np.nan


    normal = NormalDist()


    return float(
        2.0
        *
        (
            1.0
            -
            normal.cdf(
                abs(
                    z
                )
            )
        )
    )


def kendall_tau_mk(
    s,
    n,
):

    denominador = (
        0.5
        *
        n
        *
        (
            n
            -
            1
        )
    )


    if denominador == 0:

        return np.nan


    return float(
        s
        /
        denominador
    )


def sen_slope(
    anos,
    valores,
):

    anos = np.asarray(
        anos,
        dtype=float,
    )


    x = np.asarray(
        valores,
        dtype=float,
    )


    slopes = []


    for i in range(
        len(
            x
        )
        -
        1
    ):

        delta_anos = (
            anos[
                i + 1:
            ]
            -
            anos[i]
        )


        delta_valores = (
            x[
                i + 1:
            ]
            -
            x[i]
        )


        validos = (
            delta_anos
            !=
            0
        )


        slopes.extend(
            (
                delta_valores[
                    validos
                ]
                /
                delta_anos[
                    validos
                ]
            )
            .tolist()
        )


    if not slopes:

        return np.nan


    return float(
        np.median(
            slopes
        )
    )


def autocorrelacao(
    valores,
    lag,
):

    valores = np.asarray(
        valores,
        dtype=float,
    )


    n = len(
        valores
    )


    if (
        lag <= 0
        or
        lag >= n
    ):

        return np.nan


    media = float(
        np.mean(
            valores
        )
    )


    centrado = (
        valores
        -
        media
    )


    denominador = float(
        np.sum(
            centrado ** 2
        )
    )


    if denominador == 0:

        return 0.0


    numerador = float(
        np.sum(
            centrado[
                :-lag
            ]
            *
            centrado[
                lag:
            ]
        )
    )


    return (
        numerador
        /
        denominador
    )


def hamed_rao_mk(
    anos,
    valores,
    alpha=0.05,
):

    """
    Mann-Kendall modificado de Hamed-Rao.

    Passos:
    1. Calcula MK clássico.
    2. Calcula Sen's Slope.
    3. Remove a tendência linear de Sen.
    4. Converte a série detrendida em ranks.
    5. Calcula autocorrelação dos ranks detrendidos.
    6. Mantém apenas lags fora do intervalo aproximado
       +/- z_(1-alpha/2) / sqrt(n).
    7. Ajusta a variância de S.
    """

    anos = np.asarray(
        anos,
        dtype=float,
    )


    x = np.asarray(
        valores,
        dtype=float,
    )


    n = len(
        x
    )


    if n < 4:

        return None


    # ------------------------------------------------------
    # MK clássico
    # ------------------------------------------------------

    s = mk_score(
        x
    )


    var_classica = mk_variance(
        x
    )


    z_classico = z_mk(
        s,
        var_classica,
    )


    p_classico = p_bilateral_normal(
        z_classico
    )


    tau = kendall_tau_mk(
        s,
        n,
    )


    # ------------------------------------------------------
    # Sen's Slope
    # ------------------------------------------------------

    slope = sen_slope(
        anos,
        x,
    )


    # Centralizamos o tempo para melhorar estabilidade
    # numérica do detrending.
    tempo = (
        anos
        -
        anos[0]
    )


    detrendida = (
        x
        -
        slope
        *
        tempo
    )


    # ------------------------------------------------------
    # Ranks detrendidos
    # ------------------------------------------------------

    ranks = (
        pd.Series(
            detrendida
        )
        .rank(
            method="average"
        )
        .to_numpy(
            dtype=float
        )
    )


    # ------------------------------------------------------
    # ACF dos ranks detrendidos
    # ------------------------------------------------------

    z_critico = (
        NormalDist()
        .inv_cdf(
            1
            -
            alpha
            /
            2
        )
    )


    limite_acf = (
        z_critico
        /
        np.sqrt(
            n
        )
    )


    soma_correcao = 0.0

    n_lags_significativos = 0

    acfs = {}


    for lag in range(
        1,
        n
    ):

        rho = autocorrelacao(
            ranks,
            lag,
        )


        acfs[
            lag
        ] = rho


        if (
            np.isfinite(
                rho
            )
            and
            abs(
                rho
            )
            >
            limite_acf
        ):

            peso = (
                (
                    n
                    -
                    lag
                )
                *
                (
                    n
                    -
                    lag
                    -
                    1
                )
                *
                (
                    n
                    -
                    lag
                    -
                    2
                )
            )


            soma_correcao += (
                peso
                *
                rho
            )


            n_lags_significativos += 1


    fator_correcao = (
        1.0
        +
        (
            2.0
            /
            (
                n
                *
                (
                    n
                    -
                    1
                )
                *
                (
                    n
                    -
                    2
                )
            )
        )
        *
        soma_correcao
    )


    # Uma variância corrigida <= 0 não possui interpretação
    # estatística. Em vez de forçar um valor arbitrário,
    # marcamos o resultado modificado como indisponível.
    if (
        not np.isfinite(
            fator_correcao
        )
        or
        fator_correcao <= 0
    ):

        var_modificada = np.nan
        z_modificado = np.nan
        p_modificado = np.nan

    else:

        var_modificada = (
            var_classica
            *
            fator_correcao
        )


        z_modificado = z_mk(
            s,
            var_modificada,
        )


        p_modificado = p_bilateral_normal(
            z_modificado
        )


    rho1 = (
        acfs.get(
            1,
            np.nan,
        )
    )


    return {
        "n":
            n,

        "mk_s":
            s,

        "mk_tau":
            tau,

        "mk_var_classica":
            var_classica,

        "mk_z_classico":
            z_classico,

        "mk_p_classico":
            p_classico,

        "sen_slope_c_ano":
            slope,

        "sen_slope_c_decada":
            slope
            *
            10.0,

        "rho1_rank_detrendido":
            rho1,

        "limite_acf_aprox":
            limite_acf,

        "n_lags_acf_significativos":
            n_lags_significativos,

        "fator_correcao_hamed_rao":
            fator_correcao,

        "mk_var_modificada":
            var_modificada,

        "mk_z_modificado":
            z_modificado,

        "mk_p_modificado":
            p_modificado,
    }


def benjamini_hochberg(
    pvalores,
):

    """
    Ajuste FDR Benjamini-Hochberg.

    Mantém NaNs como NaN.
    """

    serie = pd.Series(
        pvalores,
        dtype=float,
    )


    resultado = pd.Series(
        np.nan,
        index=serie.index,
        dtype=float,
    )


    validos = (
        serie
        .dropna()
    )


    m = len(
        validos
    )


    if m == 0:

        return resultado


    ordem = (
        validos
        .sort_values()
    )


    p_ordenados = (
        ordem
        .to_numpy(
            dtype=float
        )
    )


    ranks = np.arange(
        1,
        m + 1,
        dtype=float,
    )


    ajustados = (
        p_ordenados
        *
        m
        /
        ranks
    )


    # monotonicidade BH de trás para frente
    ajustados = np.minimum.accumulate(
        ajustados[
            ::-1
        ]
    )[
        ::-1
    ]


    ajustados = np.clip(
        ajustados,
        0,
        1,
    )


    resultado.loc[
        ordem.index
    ] = ajustados


    return resultado


def classificacao_tendencia(
    slope,
    p,
    alpha=0.05,
):

    if (
        not np.isfinite(
            slope
        )
        or
        not np.isfinite(
            p
        )
    ):

        return "indefinida"


    if p >= alpha:

        return "sem_tendencia_significativa"


    if slope > 0:

        return "crescente"


    if slope < 0:

        return "decrescente"


    return "sem_tendencia_significativa"


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("MANN-KENDALL MODIFICADO PARA AUTOCORRELAÇÃO")
print("=" * 90)


print(
    "\nMétodo: Hamed-Rao Modified Mann-Kendall"
)


print(
    "Aplicação: somente ao maior trecho anual consecutivo "
    "de cada estação"
)


print(
    f"\nRede principal consecutiva: "
    f">={MIN_ANOS_PRINCIPAL} anos"
)


print(
    f"Rede de sensibilidade consecutiva: "
    f">={MIN_ANOS_SENSIBILIDADE} anos"
)


print(
    f"\nAlpha: {ALPHA}"
)


print(
    "FDR: Benjamini-Hochberg aplicado aos "
    "p-valores modificados"
)


# ==========================================================
# 1. CARREGAR
# ==========================================================

if not ARQUIVO_MAXIMAS.exists():

    raise FileNotFoundError(
        f"Arquivo não encontrado:\n"
        f"{ARQUIVO_MAXIMAS}"
    )


base = pd.read_parquet(
    ARQUIVO_MAXIMAS
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
]


for config in VARIAVEIS.values():

    colunas_obrigatorias.append(
        config[
            "coluna"
        ]
    )


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
# 3. NORMALIZAR
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


base[
    "ano_valido_extremos"
] = converter_bool(
    base[
        "ano_valido_extremos"
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


ufs_desconhecidas = (
    base.loc[
        base[
            "regiao_corrigida"
        ]
        .isna(),
        "uf",
    ]
    .drop_duplicates()
    .tolist()
)


if ufs_desconhecidas:

    raise RuntimeError(
        "UFs sem região definida: "
        f"{ufs_desconhecidas}"
    )


# ==========================================================
# 4. ENCONTRAR O MAIOR SEGMENTO CONSECUTIVO POR ESTAÇÃO
# ==========================================================

validos = (
    base[
        base[
            "ano_valido_extremos"
        ]
    ]
    .copy()
)


segmentos = []

segmentos_dados = {}


for codigo, grupo in validos.groupby(
    "codigo",
    sort=True,
):

    segmento = maior_segmento_consecutivo(
        grupo
    )


    if segmento.empty:

        continue


    segmentos_dados[
        codigo
    ] = segmento


    segmentos.append(
        {
            "codigo":
                codigo,

            "estacao":
                primeiro_valido(
                    segmento[
                        "estacao"
                    ]
                ),

            "uf":
                primeiro_valido(
                    segmento[
                        "uf"
                    ]
                ),

            "regiao":
                primeiro_valido(
                    segmento[
                        "regiao_corrigida"
                    ]
                ),

            "n_anos_consecutivos":
                len(
                    segmento
                ),

            "ano_inicio_segmento":
                int(
                    segmento[
                        "ano"
                    ]
                    .min()
                ),

            "ano_fim_segmento":
                int(
                    segmento[
                        "ano"
                    ]
                    .max()
                ),
        }
    )


df_segmentos = pd.DataFrame(
    segmentos
)


df_segmentos[
    "rede_consecutiva_15a"
] = (
    df_segmentos[
        "n_anos_consecutivos"
    ]
    >=
    MIN_ANOS_PRINCIPAL
)


df_segmentos[
    "rede_consecutiva_10a"
] = (
    df_segmentos[
        "n_anos_consecutivos"
    ]
    >=
    MIN_ANOS_SENSIBILIDADE
)


n_15 = int(
    df_segmentos[
        "rede_consecutiva_15a"
    ].sum()
)


n_10 = int(
    df_segmentos[
        "rede_consecutiva_10a"
    ].sum()
)


print("\n" + "=" * 90)
print("VALIDAÇÃO DAS REDES CONSECUTIVAS")
print("=" * 90)


print(
    f"\n>=15 anos consecutivos: "
    f"{n_15:,}"
)


print(
    f">=10 anos consecutivos: "
    f"{n_10:,}"
)


if n_15 != ESPERADO_PRINCIPAL_CONSECUTIVA:

    raise RuntimeError(
        f"Esperávamos "
        f"{ESPERADO_PRINCIPAL_CONSECUTIVA} "
        f"estações >=15 anos consecutivos, "
        f"mas encontramos {n_15}."
    )


if n_10 != ESPERADO_SENSIBILIDADE_CONSECUTIVA:

    raise RuntimeError(
        f"Esperávamos "
        f"{ESPERADO_SENSIBILIDADE_CONSECUTIVA} "
        f"estações >=10 anos consecutivos, "
        f"mas encontramos {n_10}."
    )


df_segmentos.to_csv(
    SAIDA_SEGMENTOS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 5. CALCULAR TENDÊNCIAS
# ==========================================================

redes = {

    "principal_consecutiva_15a":
        df_segmentos.loc[
            df_segmentos[
                "rede_consecutiva_15a"
            ],
            "codigo",
        ]
        .tolist(),

    "sensibilidade_consecutiva_10a":
        df_segmentos.loc[
            df_segmentos[
                "rede_consecutiva_10a"
            ],
            "codigo",
        ]
        .tolist(),
}


resultados = []


print("\n" + "=" * 90)
print("CALCULANDO MK CLÁSSICO E HAMED-RAO")
print("=" * 90)


for nome_rede, codigos in redes.items():

    print(
        f"\n{nome_rede}: "
        f"{len(codigos)} estações"
    )


    for codigo in codigos:

        segmento = (
            segmentos_dados[
                codigo
            ]
            .sort_values(
                "ano"
            )
            .copy()
        )


        anos = (
            segmento[
                "ano"
            ]
            .astype(int)
            .to_numpy()
        )


        # Segurança: o segmento precisa ser realmente
        # consecutivo.
        if len(
            anos
        ) > 1:

            if not np.all(
                np.diff(
                    anos
                )
                ==
                1
            ):

                raise RuntimeError(
                    f"O segmento de {codigo} "
                    f"não é totalmente consecutivo."
                )


        estacao = primeiro_valido(
            segmento[
                "estacao"
            ]
        )


        uf = primeiro_valido(
            segmento[
                "uf"
            ]
        )


        regiao = primeiro_valido(
            segmento[
                "regiao_corrigida"
            ]
        )


        for variavel, config in VARIAVEIS.items():

            coluna = config[
                "coluna"
            ]


            serie = (
                segmento[
                    [
                        "ano",
                        coluna,
                    ]
                ]
                .dropna()
                .copy()
            )


            # Como ano_valido_extremos foi calculado apenas
            # em anos com dados válidos, não esperamos NaN
            # aqui. Mesmo assim, não fingimos que um buraco
            # não existe.
            if len(
                serie
            ) != len(
                segmento
            ):

                print(
                    f"AVISO: {codigo} | {variavel} "
                    f"possui valores ausentes dentro "
                    f"do segmento consecutivo. "
                    f"Resultado ignorado."
                )

                continue


            resultado = hamed_rao_mk(
                serie[
                    "ano"
                ].to_numpy(),
                serie[
                    coluna
                ].to_numpy(),
                alpha=ALPHA,
            )


            if resultado is None:

                continue


            resultados.append(
                {
                    "rede":
                        nome_rede,

                    "variavel":
                        variavel,

                    "nome_variavel":
                        config[
                            "nome"
                        ],

                    "codigo":
                        codigo,

                    "estacao":
                        estacao,

                    "uf":
                        uf,

                    "regiao":
                        regiao,

                    "n_anos":
                        resultado[
                            "n"
                        ],

                    "ano_inicio":
                        int(
                            serie[
                                "ano"
                            ]
                            .min()
                        ),

                    "ano_fim":
                        int(
                            serie[
                                "ano"
                            ]
                            .max()
                        ),

                    "valor_inicial_c":
                        float(
                            serie[
                                coluna
                            ]
                            .iloc[0]
                        ),

                    "valor_final_c":
                        float(
                            serie[
                                coluna
                            ]
                            .iloc[-1]
                        ),

                    **resultado,
                }
            )


resultados = pd.DataFrame(
    resultados
)


# ==========================================================
# 6. FDR DOS P-VALORES MODIFICADOS
# ==========================================================

resultados[
    "mk_p_modificado_fdr"
] = np.nan


for (
    nome_rede,
    variavel
), indices in resultados.groupby(
    [
        "rede",
        "variavel",
    ]
).groups.items():

    p_ajustados = benjamini_hochberg(
        resultados.loc[
            indices,
            "mk_p_modificado",
        ]
    )


    resultados.loc[
        indices,
        "mk_p_modificado_fdr",
    ] = (
        p_ajustados
        .to_numpy()
    )


# ==========================================================
# 7. FLAGS E CLASSIFICAÇÕES
# ==========================================================

resultados[
    "significativo_classico_p05"
] = (
    resultados[
        "mk_p_classico"
    ]
    <
    ALPHA
)


resultados[
    "significativo_modificado_p05"
] = (
    resultados[
        "mk_p_modificado"
    ]
    <
    ALPHA
)


resultados[
    "significativo_modificado_fdr05"
] = (
    resultados[
        "mk_p_modificado_fdr"
    ]
    <
    ALPHA
)


resultados[
    "classificacao_classica"
] = resultados.apply(
    lambda linha:
        classificacao_tendencia(
            linha[
                "sen_slope_c_ano"
            ],
            linha[
                "mk_p_classico"
            ],
            ALPHA,
        ),
    axis=1,
)


resultados[
    "classificacao_modificada"
] = resultados.apply(
    lambda linha:
        classificacao_tendencia(
            linha[
                "sen_slope_c_ano"
            ],
            linha[
                "mk_p_modificado"
            ],
            ALPHA,
        ),
    axis=1,
)


resultados[
    "classificacao_modificada_fdr"
] = resultados.apply(
    lambda linha:
        classificacao_tendencia(
            linha[
                "sen_slope_c_ano"
            ],
            linha[
                "mk_p_modificado_fdr"
            ],
            ALPHA,
        ),
    axis=1,
)


resultados[
    "mudou_significancia_com_correcao"
] = (
    resultados[
        "significativo_classico_p05"
    ]
    !=
    resultados[
        "significativo_modificado_p05"
    ]
)


resultados[
    "delta_p_modificado_menos_classico"
] = (
    resultados[
        "mk_p_modificado"
    ]
    -
    resultados[
        "mk_p_classico"
    ]
)


# ==========================================================
# 8. ORDENAR E SALVAR
# ==========================================================

resultados = (
    resultados
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


resultados.to_parquet(
    SAIDA_PARQUET,
    index=False,
)


resultados.to_csv(
    SAIDA_CSV,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 9. RESUMO POR REDE
# ==========================================================

resumo_rede = (
    resultados
    .groupby(
        [
            "rede",
            "variavel",
        ],
        as_index=False,
    )
    .agg(
        n_estacoes=(
            "codigo",
            "nunique",
        ),

        n_anos_mediana=(
            "n_anos",
            "median",
        ),

        sen_mediana_c_decada=(
            "sen_slope_c_decada",
            "median",
        ),

        sen_media_c_decada=(
            "sen_slope_c_decada",
            "mean",
        ),

        rho1_mediana=(
            "rho1_rank_detrendido",
            "median",
        ),

        fator_correcao_mediano=(
            "fator_correcao_hamed_rao",
            "median",
        ),

        n_classico_p05=(
            "significativo_classico_p05",
            "sum",
        ),

        n_modificado_p05=(
            "significativo_modificado_p05",
            "sum",
        ),

        n_modificado_fdr05=(
            "significativo_modificado_fdr05",
            "sum",
        ),

        n_mudou_significancia=(
            "mudou_significancia_com_correcao",
            "sum",
        ),

        n_slope_positivo=(
            "sen_slope_c_decada",
            lambda x:
                int(
                    (
                        x
                        >
                        0
                    )
                    .sum()
                ),
        ),

        n_slope_negativo=(
            "sen_slope_c_decada",
            lambda x:
                int(
                    (
                        x
                        <
                        0
                    )
                    .sum()
                ),
        ),
    )
)


for coluna in [
    "n_classico_p05",
    "n_modificado_p05",
    "n_modificado_fdr05",
    "n_mudou_significancia",
    "n_slope_positivo",
    "n_slope_negativo",
]:

    resumo_rede[
        coluna
    ] = (
        resumo_rede[
            coluna
        ]
        .astype(int)
    )


resumo_rede[
    "pct_classico_p05"
] = (
    resumo_rede[
        "n_classico_p05"
    ]
    /
    resumo_rede[
        "n_estacoes"
    ]
    *
    100
)


resumo_rede[
    "pct_modificado_p05"
] = (
    resumo_rede[
        "n_modificado_p05"
    ]
    /
    resumo_rede[
        "n_estacoes"
    ]
    *
    100
)


resumo_rede[
    "pct_modificado_fdr05"
] = (
    resumo_rede[
        "n_modificado_fdr05"
    ]
    /
    resumo_rede[
        "n_estacoes"
    ]
    *
    100
)


resumo_rede.to_csv(
    SAIDA_RESUMO_REDE,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 10. RESUMO REGIONAL
# ==========================================================

resumo_regiao = (
    resultados
    .groupby(
        [
            "rede",
            "variavel",
            "regiao",
        ],
        as_index=False,
    )
    .agg(
        n_estacoes=(
            "codigo",
            "nunique",
        ),

        sen_mediana_c_decada=(
            "sen_slope_c_decada",
            "median",
        ),

        rho1_mediana=(
            "rho1_rank_detrendido",
            "median",
        ),

        n_classico_p05=(
            "significativo_classico_p05",
            "sum",
        ),

        n_modificado_p05=(
            "significativo_modificado_p05",
            "sum",
        ),

        n_modificado_fdr05=(
            "significativo_modificado_fdr05",
            "sum",
        ),
    )
)


resumo_regiao.to_csv(
    SAIDA_RESUMO_REGIAO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 11. COMPARAÇÃO ESTAÇÃO A ESTAÇÃO
# ==========================================================

comparacao = resultados[
    [
        "rede",
        "variavel",
        "codigo",
        "estacao",
        "uf",
        "regiao",
        "n_anos",
        "ano_inicio",
        "ano_fim",
        "sen_slope_c_decada",
        "rho1_rank_detrendido",
        "n_lags_acf_significativos",
        "fator_correcao_hamed_rao",
        "mk_p_classico",
        "mk_p_modificado",
        "mk_p_modificado_fdr",
        "significativo_classico_p05",
        "significativo_modificado_p05",
        "significativo_modificado_fdr05",
        "mudou_significancia_com_correcao",
        "delta_p_modificado_menos_classico",
    ]
].copy()


comparacao.to_csv(
    SAIDA_COMPARACAO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 12. IMPRESSÃO DOS RESULTADOS
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO POR REDE")
print("=" * 90)


print(
    resumo_rede.to_string(
        index=False,
        float_format=lambda x:
            f"{x:.4f}"
    )
)


print("\n" + "=" * 90)
print("CASOS EM QUE A CORREÇÃO MUDOU A SIGNIFICÂNCIA")
print("=" * 90)


mudancas = (
    resultados[
        resultados[
            "mudou_significancia_com_correcao"
        ]
    ]
    .copy()
)


print(
    f"\nTotal: "
    f"{len(mudancas):,}"
)


if mudancas.empty:

    print(
        "\nNenhum caso mudou de classificação "
        "p<0,05 após a correção Hamed-Rao."
    )

else:

    print(
        mudancas[
            [
                "rede",
                "variavel",
                "codigo",
                "estacao",
                "uf",
                "n_anos",
                "sen_slope_c_decada",
                "rho1_rank_detrendido",
                "fator_correcao_hamed_rao",
                "mk_p_classico",
                "mk_p_modificado",
            ]
        ]
        .to_string(
            index=False,
            float_format=lambda x:
                f"{x:.5f}"
        )
    )


print("\n" + "=" * 90)
print("SIGNIFICATIVOS APÓS HAMED-RAO + FDR")
print("=" * 90)


significativos = (
    resultados[
        resultados[
            "significativo_modificado_fdr05"
        ]
    ]
    .copy()
)


if significativos.empty:

    print(
        "\nNenhuma tendência permaneceu "
        "significativa após Hamed-Rao + FDR."
    )

else:

    print(
        significativos[
            [
                "rede",
                "variavel",
                "codigo",
                "estacao",
                "uf",
                "regiao",
                "n_anos",
                "sen_slope_c_decada",
                "mk_p_modificado",
                "mk_p_modificado_fdr",
            ]
        ]
        .to_string(
            index=False,
            float_format=lambda x:
                f"{x:.5f}"
        )
    )


# ==========================================================
# 13. CONCORDÂNCIA INMET × ERA5
# ==========================================================

print("\n" + "=" * 90)
print("CONCORDÂNCIA INMET × ERA5 NAS REDES CONSECUTIVAS")
print("=" * 90)


for nome_rede in redes:

    pivot = (
        resultados[
            (
                resultados[
                    "rede"
                ]
                ==
                nome_rede
            )
            &
            (
                resultados[
                    "variavel"
                ]
                .isin(
                    [
                        "tmax_inmet",
                        "tmax_era5",
                    ]
                )
            )
        ][
            [
                "codigo",
                "variavel",
                "sen_slope_c_decada",
                "mk_p_modificado",
            ]
        ]
        .pivot(
            index="codigo",
            columns="variavel",
        )
    )


    slope_inmet = (
        pivot[
            "sen_slope_c_decada"
        ][
            "tmax_inmet"
        ]
    )


    slope_era5 = (
        pivot[
            "sen_slope_c_decada"
        ][
            "tmax_era5"
        ]
    )


    mesmo_sinal = int(
        (
            np.sign(
                slope_inmet
            )
            ==
            np.sign(
                slope_era5
            )
        )
        .sum()
    )


    total = len(
        pivot
    )


    print(
        f"\n{nome_rede}:"
    )


    print(
        f"  estações: "
        f"{total}"
    )


    print(
        f"  mesmo sinal Sen INMET/ERA5: "
        f"{mesmo_sinal} "
        f"({mesmo_sinal / total * 100:.1f}%)"
    )


# ==========================================================
# 14. ARQUIVOS
# ==========================================================

print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    SAIDA_PARQUET
)


print(
    SAIDA_CSV
)


print(
    SAIDA_RESUMO_REDE
)


print(
    SAIDA_RESUMO_REGIAO
)


print(
    SAIDA_COMPARACAO
)


print(
    SAIDA_SEGMENTOS
)


print("\n" + "=" * 90)
print("ANÁLISE DE AUTOCORRELAÇÃO CONCLUÍDA")
print("=" * 90)
