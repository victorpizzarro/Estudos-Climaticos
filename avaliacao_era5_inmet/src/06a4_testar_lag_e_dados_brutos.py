from pathlib import Path
import io
import re
import unicodedata
import zipfile

import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

LAG_MIN = -24
LAG_MAX = 24


CASOS = [
    # anomalias
    ("A402", 2005, "anomalia"),
    ("A355", 2015, "anomalia"),
    ("A316", 2014, "anomalia"),
    ("A316", 2015, "anomalia"),

    # anos-controle das mesmas estações
    ("A402", 2006, "controle"),
    ("A355", 2014, "controle"),
    ("A355", 2017, "controle"),
    ("A316", 2013, "controle"),
    ("A316", 2016, "controle"),

    # erro sistemático conhecido
    ("A610", 2012, "controle_sistematico"),
]


# ==========================================================
# CAMINHOS
# ==========================================================

INMET_RAW_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "inmet"
    / "automaticas"
)


PARES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
    / "horarios"
)


SAIDA_RAW = (
    TABLES_DIR
    / "diagnostico_raw_casos_criticos.csv"
)


SAIDA_LAGS = (
    TABLES_DIR
    / "diagnostico_lags_casos_criticos.csv"
)


SAIDA_RESUMO_LAGS = (
    TABLES_DIR
    / "resumo_lags_casos_criticos.csv"
)


# ==========================================================
# FUNÇÕES DE TEXTO
# ==========================================================

def normalizar(texto):

    texto = str(texto).strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    texto = texto.upper()

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def localizar_cabecalho(linhas):

    for indice, linha in enumerate(
        linhas[:30]
    ):

        texto = normalizar(
            linha
        )

        if (
            "TEMPERATURA MAXIMA NA HORA ANT"
            in texto
            and
            "HORA"
            in texto
        ):

            return indice


    raise RuntimeError(
        "Cabeçalho não encontrado."
    )


def identificar_colunas(colunas):

    resultado = {
        "data": None,
        "hora": None,
        "temp_max": None,
        "temp_inst": None,
        "temp_min": None,
    }


    for coluna in colunas:

        nome = normalizar(
            coluna
        )


        if nome.startswith(
            "DATA"
        ):

            resultado[
                "data"
            ] = coluna


        elif (
            "HORA"
            in nome
            and
            "UTC"
            in nome
        ):

            resultado[
                "hora"
            ] = coluna


        elif (
            "TEMPERATURA MAXIMA NA HORA ANT"
            in nome
        ):

            resultado[
                "temp_max"
            ] = coluna


        elif (
            "TEMPERATURA MINIMA NA HORA ANT"
            in nome
        ):

            resultado[
                "temp_min"
            ] = coluna


        elif (
            "TEMPERATURA DO AR"
            in nome
            and
            "BULBO SECO"
            in nome
        ):

            resultado[
                "temp_inst"
            ] = coluna


    return resultado


def converter_temperatura(serie):

    valores = (
        serie.astype(str)
        .str.strip()
        .str.replace(
            ",",
            ".",
            regex=False,
        )
    )


    valores = pd.to_numeric(
        valores,
        errors="coerce",
    )


    valores = valores.mask(
        valores <= -9990
    )


    return valores


# ==========================================================
# DATETIME
# ==========================================================

def construir_datetime(
    datas,
    horas,
):

    datas = (
        datas.astype(str)
        .str.strip()
        .str.replace(
            "/",
            "-",
            regex=False,
        )
    )


    data_convertida = pd.to_datetime(
        datas,
        errors="coerce",
        format="mixed",
    )


    horas = (
        horas.astype(str)
        .str.upper()
        .str.replace(
            "UTC",
            "",
            regex=False,
        )
        .str.strip()
    )


    digitos = (
        horas
        .str.replace(
            r"\D",
            "",
            regex=True,
        )
        .str.zfill(4)
    )


    hh = pd.to_numeric(
        digitos.str[:2],
        errors="coerce",
    )


    mm = pd.to_numeric(
        digitos.str[2:4],
        errors="coerce",
    )


    mascara_24 = (
        (hh == 24)
        &
        (mm == 0)
    )


    hh_corrigida = hh.copy()

    hh_corrigida.loc[
        mascara_24
    ] = 0


    resultado = (
        data_convertida
        +
        pd.to_timedelta(
            hh_corrigida,
            unit="h",
        )
        +
        pd.to_timedelta(
            mm,
            unit="m",
        )
    )


    resultado.loc[
        mascara_24
    ] = (
        resultado.loc[
            mascara_24
        ]
        +
        pd.Timedelta(
            days=1
        )
    )


    return resultado


# ==========================================================
# LER ESTAÇÃO DIRETAMENTE DO ZIP
# ==========================================================

def ler_estacao_raw(
    codigo,
    ano,
):

    arquivo_zip = (
        INMET_RAW_DIR
        / f"{ano}.zip"
    )


    if not arquivo_zip.exists():

        raise FileNotFoundError(
            arquivo_zip
        )


    with zipfile.ZipFile(
        arquivo_zip,
        "r",
    ) as zf:

        arquivos = [
            nome
            for nome in zf.namelist()
            if (
                nome.lower().endswith(
                    ".csv"
                )
                and
                f"_{codigo}_"
                in nome.upper()
            )
        ]


        if len(arquivos) != 1:

            raise RuntimeError(
                f"{codigo}/{ano}: "
                f"{len(arquivos)} arquivos encontrados."
            )


        nome_arquivo = arquivos[0]


        with zf.open(
            nome_arquivo
        ) as f:

            dados = f.read()


    texto = dados.decode(
        "latin-1"
    )


    linhas = texto.splitlines()


    cabecalho = localizar_cabecalho(
        linhas
    )


    df = pd.read_csv(
        io.StringIO(
            texto
        ),
        sep=";",
        skiprows=cabecalho,
        dtype=str,
        low_memory=False,
    )


    df = df.loc[
        :,
        ~df.columns.astype(str)
        .str.startswith(
            "Unnamed"
        )
    ]


    colunas = identificar_colunas(
        df.columns
    )


    obrigatorias = [
        "data",
        "hora",
        "temp_max",
    ]


    for coluna in obrigatorias:

        if colunas[
            coluna
        ] is None:

            raise RuntimeError(
                f"{codigo}/{ano}: "
                f"coluna {coluna} não encontrada."
            )


    resultado = pd.DataFrame()


    resultado[
        "datetime_utc"
    ] = construir_datetime(
        df[
            colunas[
                "data"
            ]
        ],
        df[
            colunas[
                "hora"
            ]
        ],
    )


    resultado[
        "temp_max_c"
    ] = converter_temperatura(
        df[
            colunas[
                "temp_max"
            ]
        ]
    )


    if colunas[
        "temp_inst"
    ] is not None:

        resultado[
            "temp_inst_c"
        ] = converter_temperatura(
            df[
                colunas[
                    "temp_inst"
                ]
            ]
        )

    else:

        resultado[
            "temp_inst_c"
        ] = np.nan


    if colunas[
        "temp_min"
    ] is not None:

        resultado[
            "temp_min_c"
        ] = converter_temperatura(
            df[
                colunas[
                    "temp_min"
                ]
            ]
        )

    else:

        resultado[
            "temp_min_c"
        ] = np.nan


    return (
        resultado,
        nome_arquivo,
    )


# ==========================================================
# RESUMO INTERNO DO ARQUIVO RAW
# ==========================================================

def diagnosticar_raw(
    codigo,
    ano,
    classificacao,
):

    df, arquivo = ler_estacao_raw(
        codigo,
        ano,
    )


    maximos = (
        df[
            "temp_max_c"
        ]
        .dropna()
    )


    validos_max_inst = (
        df[
            [
                "temp_max_c",
                "temp_inst_c",
            ]
        ]
        .dropna()
    )


    validos_max_min = (
        df[
            [
                "temp_max_c",
                "temp_min_c",
            ]
        ]
        .dropna()
    )


    # A máxima da hora anterior normalmente
    # não deve ser substancialmente inferior
    # à temperatura instantânea.
    violacao_max_inst = int(
        (
            validos_max_inst[
                "temp_max_c"
            ]
            <
            validos_max_inst[
                "temp_inst_c"
            ]
            -
            0.2
        )
        .sum()
    )


    violacao_max_min = int(
        (
            validos_max_min[
                "temp_max_c"
            ]
            <
            validos_max_min[
                "temp_min_c"
            ]
        )
        .sum()
    )


    if not validos_max_inst.empty:

        delta_max_inst = (
            validos_max_inst[
                "temp_max_c"
            ]
            -
            validos_max_inst[
                "temp_inst_c"
            ]
        )

        mediana_delta = float(
            delta_max_inst.median()
        )

    else:

        mediana_delta = np.nan


    return {
        "codigo":
            codigo,

        "ano":
            ano,

        "classificacao":
            classificacao,

        "arquivo":
            arquivo,

        "n_temp_max":
            len(maximos),

        "temp_max_min_c":
            float(
                maximos.min()
            )
            if not maximos.empty
            else np.nan,

        "temp_max_p01_c":
            float(
                maximos.quantile(
                    0.01
                )
            )
            if not maximos.empty
            else np.nan,

        "temp_max_mediana_c":
            float(
                maximos.median()
            )
            if not maximos.empty
            else np.nan,

        "temp_max_p99_c":
            float(
                maximos.quantile(
                    0.99
                )
            )
            if not maximos.empty
            else np.nan,

        "temp_max_max_c":
            float(
                maximos.max()
            )
            if not maximos.empty
            else np.nan,

        "n_com_max_inst":
            len(
                validos_max_inst
            ),

        "violacao_max_inst":
            violacao_max_inst,

        "pct_violacao_max_inst":
            (
                100
                *
                violacao_max_inst
                /
                len(
                    validos_max_inst
                )
            )
            if len(
                validos_max_inst
            )
            else np.nan,

        "mediana_max_menos_inst_c":
            mediana_delta,

        "n_com_max_min":
            len(
                validos_max_min
            ),

        "violacao_max_min":
            violacao_max_min,

        "pct_violacao_max_min":
            (
                100
                *
                violacao_max_min
                /
                len(
                    validos_max_min
                )
            )
            if len(
                validos_max_min
            )
            else np.nan,
    }


# ==========================================================
# TESTE DE LAG
# ==========================================================

def testar_lags(
    codigo,
    ano,
    classificacao,
):

    arquivo = (
        PARES_DIR
        / f"era5_inmet_pares_{ano}.parquet"
    )


    df = pd.read_parquet(
        arquivo,
        columns=[
            "codigo",
            "datetime_utc",
            "temp_inmet_c",
            "temp_era5_c",
        ],
        filters=[
            (
                "codigo",
                "==",
                codigo,
            )
        ],
    )


    df[
        "datetime_utc"
    ] = pd.to_datetime(
        df[
            "datetime_utc"
        ]
    )


    inmet = df[
        [
            "datetime_utc",
            "temp_inmet_c",
        ]
    ].copy()


    resultados = []


    for lag in range(
        LAG_MIN,
        LAG_MAX + 1,
    ):

        era5 = df[
            [
                "datetime_utc",
                "temp_era5_c",
            ]
        ].copy()


        # Convenção:
        #
        # lag +12 significa:
        # INMET(t) comparado com ERA5(t+12h)
        #
        # Portanto deslocamos a chave ERA5
        # 12 horas para trás para fazer o merge.

        era5[
            "datetime_utc"
        ] = (
            era5[
                "datetime_utc"
            ]
            -
            pd.Timedelta(
                hours=lag
            )
        )


        pares = inmet.merge(
            era5,
            on="datetime_utc",
            how="inner",
        )


        pares = pares.dropna(
            subset=[
                "temp_inmet_c",
                "temp_era5_c",
            ]
        )


        if len(
            pares
        ) < 2:

            correlacao = np.nan

        else:

            correlacao = (
                pares[
                    "temp_inmet_c"
                ]
                .corr(
                    pares[
                        "temp_era5_c"
                    ]
                )
            )


        erro = (
            pares[
                "temp_era5_c"
            ]
            -
            pares[
                "temp_inmet_c"
            ]
        )


        bias = (
            float(
                erro.mean()
            )
            if not erro.empty
            else np.nan
        )


        rmse = (
            float(
                np.sqrt(
                    np.mean(
                        erro ** 2
                    )
                )
            )
            if not erro.empty
            else np.nan
        )


        resultados.append(
            {
                "codigo":
                    codigo,

                "ano":
                    ano,

                "classificacao":
                    classificacao,

                "lag_era5_h":
                    lag,

                "n_pares":
                    len(
                        pares
                    ),

                "bias_c":
                    bias,

                "rmse_c":
                    rmse,

                "correlacao":
                    correlacao,
            }
        )


    return pd.DataFrame(
        resultados
    )


# ==========================================================
# EXECUÇÃO
# ==========================================================

print("=" * 90)
print("TESTE DE LAG E CONSISTÊNCIA DOS DADOS BRUTOS")
print("=" * 90)


resultados_raw = []
resultados_lag = []


for codigo, ano, classificacao in CASOS:

    print("\n" + "=" * 90)

    print(
        f"{codigo} | {ano} | "
        f"{classificacao}"
    )

    print("=" * 90)


    # ------------------------------------------------------
    # RAW
    # ------------------------------------------------------

    raw = diagnosticar_raw(
        codigo,
        ano,
        classificacao,
    )


    resultados_raw.append(
        raw
    )


    print(
        "\nRAW:"
    )


    print(
        f"  temperatura máxima:"
        f" {raw['temp_max_min_c']:.2f}"
        f" a {raw['temp_max_max_c']:.2f} °C"
    )


    print(
        f"  mediana:"
        f" {raw['temp_max_mediana_c']:.2f} °C"
    )


    print(
        f"  violações max < instantânea:"
        f" {raw['violacao_max_inst']:,}"
        f" ({raw['pct_violacao_max_inst']:.2f}%)"
    )


    print(
        f"  violações max < mínima:"
        f" {raw['violacao_max_min']:,}"
        f" ({raw['pct_violacao_max_min']:.2f}%)"
    )


    print(
        f"  mediana(max - instantânea):"
        f" {raw['mediana_max_menos_inst_c']:.3f} °C"
    )


    # ------------------------------------------------------
    # LAGS
    # ------------------------------------------------------

    lags = testar_lags(
        codigo,
        ano,
        classificacao,
    )


    resultados_lag.append(
        lags
    )


    lag_zero = (
        lags[
            lags[
                "lag_era5_h"
            ]
            ==
            0
        ]
        .iloc[0]
    )


    melhor_corr = (
        lags
        .dropna(
            subset=[
                "correlacao"
            ]
        )
        .sort_values(
            "correlacao",
            ascending=False,
        )
        .iloc[0]
    )


    melhor_rmse = (
        lags
        .dropna(
            subset=[
                "rmse_c"
            ]
        )
        .sort_values(
            "rmse_c"
        )
        .iloc[0]
    )


    print(
        "\nLAG 0:"
    )

    print(
        f"  r = "
        f"{lag_zero['correlacao']:.4f}"
    )

    print(
        f"  RMSE = "
        f"{lag_zero['rmse_c']:.4f} °C"
    )


    print(
        "\nMelhor correlação:"
    )

    print(
        f"  lag = "
        f"{int(melhor_corr['lag_era5_h']):+d} h"
    )

    print(
        f"  r = "
        f"{melhor_corr['correlacao']:.4f}"
    )

    print(
        f"  RMSE = "
        f"{melhor_corr['rmse_c']:.4f} °C"
    )


    print(
        "\nMenor RMSE:"
    )

    print(
        f"  lag = "
        f"{int(melhor_rmse['lag_era5_h']):+d} h"
    )

    print(
        f"  r = "
        f"{melhor_rmse['correlacao']:.4f}"
    )

    print(
        f"  RMSE = "
        f"{melhor_rmse['rmse_c']:.4f} °C"
    )


# ==========================================================
# CONSOLIDAR
# ==========================================================

df_raw = pd.DataFrame(
    resultados_raw
)


df_lags = pd.concat(
    resultados_lag,
    ignore_index=True,
)


# ==========================================================
# RESUMO DOS LAGS
# ==========================================================

resumo_lags = []


for (
    codigo,
    ano,
    classificacao
), grupo in df_lags.groupby(
    [
        "codigo",
        "ano",
        "classificacao",
    ]
):

    zero = (
        grupo[
            grupo[
                "lag_era5_h"
            ]
            ==
            0
        ]
        .iloc[0]
    )


    melhor_corr = (
        grupo
        .dropna(
            subset=[
                "correlacao"
            ]
        )
        .sort_values(
            "correlacao",
            ascending=False,
        )
        .iloc[0]
    )


    melhor_rmse = (
        grupo
        .dropna(
            subset=[
                "rmse_c"
            ]
        )
        .sort_values(
            "rmse_c"
        )
        .iloc[0]
    )


    resumo_lags.append(
        {
            "codigo":
                codigo,

            "ano":
                ano,

            "classificacao":
                classificacao,

            "r_lag0":
                zero[
                    "correlacao"
                ],

            "rmse_lag0_c":
                zero[
                    "rmse_c"
                ],

            "melhor_lag_correlacao_h":
                int(
                    melhor_corr[
                        "lag_era5_h"
                    ]
                ),

            "melhor_correlacao":
                melhor_corr[
                    "correlacao"
                ],

            "rmse_no_melhor_r":
                melhor_corr[
                    "rmse_c"
                ],

            "melhor_lag_rmse_h":
                int(
                    melhor_rmse[
                        "lag_era5_h"
                    ]
                ),

            "menor_rmse_c":
                melhor_rmse[
                    "rmse_c"
                ],

            "r_no_menor_rmse":
                melhor_rmse[
                    "correlacao"
                ],

            "ganho_correlacao":
                (
                    melhor_corr[
                        "correlacao"
                    ]
                    -
                    zero[
                        "correlacao"
                    ]
                ),

            "reducao_rmse_c":
                (
                    zero[
                        "rmse_c"
                    ]
                    -
                    melhor_rmse[
                        "rmse_c"
                    ]
                ),
        }
    )


df_resumo = pd.DataFrame(
    resumo_lags
)


# ==========================================================
# SALVAR
# ==========================================================

df_raw.to_csv(
    SAIDA_RAW,
    index=False,
    encoding="utf-8",
)


df_lags.to_csv(
    SAIDA_LAGS,
    index=False,
    encoding="utf-8",
)


df_resumo.to_csv(
    SAIDA_RESUMO_LAGS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# RESULTADO FINAL
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO DOS LAGS")
print("=" * 90)


print(
    df_resumo[
        [
            "codigo",
            "ano",
            "classificacao",
            "r_lag0",
            "rmse_lag0_c",
            "melhor_lag_correlacao_h",
            "melhor_correlacao",
            "melhor_lag_rmse_h",
            "menor_rmse_c",
            "ganho_correlacao",
            "reducao_rmse_c",
        ]
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


print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    "\nConsistência raw:"
)

print(
    SAIDA_RAW
)


print(
    "\nTodos os lags:"
)

print(
    SAIDA_LAGS
)


print(
    "\nResumo:"
)

print(
    SAIDA_RESUMO_LAGS
)


print("\n" + "=" * 90)
print("DIAGNÓSTICO CONCLUÍDO")
print("=" * 90)