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


REGIOES = [
    "Norte",
    "Nordeste",
    "Centro-Oeste",
    "Sudeste",
    "Sul",
]


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


ARQUIVO = (
    ANNUAL_DIR
    / "maximas_anuais_estacoes_tendencia.parquet"
)


SAIDA_PAINEIS = (
    TABLES_DIR
    / "paineis_fixos_extremos_anuais_corrigido.csv"
)


SAIDA_REDE = (
    TABLES_DIR
    / "rede_extremos_por_regiao.csv"
)


SAIDA_DISTRIBUICAO = (
    TABLES_DIR
    / "distribuicao_rede_extremos_regiao.csv"
)


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

    serie = (
        serie
        .dropna()
        .astype(str)
        .str.strip()
    )

    serie = serie[
        serie != ""
    ]

    if serie.empty:
        return None

    return serie.iloc[0]


def maior_sequencia_consecutiva(anos):

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


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("CORREÇÃO DAS REGIÕES DA REDE DE EXTREMOS")
print("=" * 90)


if not ARQUIVO.exists():

    raise FileNotFoundError(
        f"Arquivo não encontrado:\n"
        f"{ARQUIVO}"
    )


base = pd.read_parquet(
    ARQUIVO
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
# 1. VALIDAR COLUNAS OBRIGATÓRIAS
# ==========================================================

colunas_obrigatorias = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "ano_valido_extremos",
]


faltantes = [
    coluna
    for coluna in colunas_obrigatorias
    if coluna not in base.columns
]


if faltantes:

    raise RuntimeError(
        "Colunas obrigatórias ausentes no Parquet: "
        f"{faltantes}"
    )


# ==========================================================
# 2. NORMALIZAR TIPOS
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


# ==========================================================
# 3. RECONSTRUIR REGIÕES A PARTIR DA UF
# ==========================================================

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
        ]
        .isna(),
        "uf",
    ]
    .drop_duplicates()
    .tolist()
)


if ufs_sem_regiao:

    raise RuntimeError(
        "Existem UFs não reconhecidas: "
        f"{ufs_sem_regiao}"
    )


print(
    "\nRegiões identificadas:"
)


print(
    base[
        "regiao_corrigida"
    ]
    .value_counts()
    .to_string()
)


# ==========================================================
# 4. METADADOS BÁSICOS POR ESTAÇÃO
# ==========================================================

metadata_basico = (
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
            "regiao_corrigida",
            primeiro_valido,
        ),
    )
)


# ==========================================================
# 5. RECALCULAR A REDE DE EXTREMOS POR ESTAÇÃO
#
# Fazemos o cálculo diretamente de ano_valido_extremos.
# Assim o script não depende das colunas automáticas
# maior_sequencia_consecutiva_x / _y criadas em merges
# anteriores.
# ==========================================================

resumos_rede = []


for codigo, grupo in base.groupby(
    "codigo",
    sort=True,
):

    anos_validos = (
        grupo.loc[
            grupo[
                "ano_valido_extremos"
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


    sequencia = maior_sequencia_consecutiva(
        anos_validos
    )


    if anos_validos:

        primeiro_ano = min(
            anos_validos
        )

        ultimo_ano = max(
            anos_validos
        )

    else:

        primeiro_ano = None
        ultimo_ano = None


    resumos_rede.append(
        {
            "codigo":
                codigo,

            "anos_validos_extremos":
                n_anos,

            "primeiro_ano_valido_extremos":
                primeiro_ano,

            "ultimo_ano_valido_extremos":
                ultimo_ano,

            "maior_sequencia_consecutiva":
                sequencia,

            "rede_extremos_10a":
                n_anos >= 10,

            "rede_extremos_15a":
                n_anos >= 15,

            "rede_extremos_consecutiva_10a":
                sequencia >= 10,

            "rede_extremos_consecutiva_15a":
                sequencia >= 15,
        }
    )


resumo_rede = pd.DataFrame(
    resumos_rede
)


metadata = metadata_basico.merge(
    resumo_rede,
    on="codigo",
    how="left",
    validate="one_to_one",
)


metadata.to_csv(
    SAIDA_REDE,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 6. VALIDAR CONTAGENS GLOBAIS ESPERADAS DO 06f
# ==========================================================

contagem_10a = int(
    metadata[
        "rede_extremos_10a"
    ].sum()
)


contagem_15a = int(
    metadata[
        "rede_extremos_15a"
    ].sum()
)


contagem_consec_10a = int(
    metadata[
        "rede_extremos_consecutiva_10a"
    ].sum()
)


contagem_consec_15a = int(
    metadata[
        "rede_extremos_consecutiva_15a"
    ].sum()
)


print("\n" + "=" * 90)
print("VALIDAÇÃO DA REDE DE EXTREMOS")
print("=" * 90)


print(
    f"\nEstações >=10 anos válidos: "
    f"{contagem_10a:,}"
)


print(
    f"Estações >=15 anos válidos: "
    f"{contagem_15a:,}"
)


print(
    f"Estações >=10 anos consecutivos: "
    f"{contagem_consec_10a:,}"
)


print(
    f"Estações >=15 anos consecutivos: "
    f"{contagem_consec_15a:,}"
)


# Valores já produzidos e validados pelo 06f.
# Se mudarem, paramos em vez de gerar tabelas incoerentes.

esperados = {
    "10a": 214,
    "15a": 45,
    "consecutiva_10a": 27,
    "consecutiva_15a": 9,
}


encontrados = {
    "10a": contagem_10a,
    "15a": contagem_15a,
    "consecutiva_10a": contagem_consec_10a,
    "consecutiva_15a": contagem_consec_15a,
}


if encontrados != esperados:

    raise RuntimeError(
        "As contagens recalculadas não correspondem "
        "ao resultado validado do 06f.\n"
        f"Esperado: {esperados}\n"
        f"Encontrado: {encontrados}"
    )


# ==========================================================
# 7. DISTRIBUIÇÃO DAS REDES POR REGIÃO
# ==========================================================

linhas = []


for nome_rede, coluna in [

    (
        ">=10 anos válidos",
        "rede_extremos_10a",
    ),

    (
        ">=15 anos válidos",
        "rede_extremos_15a",
    ),

    (
        ">=10 anos consecutivos",
        "rede_extremos_consecutiva_10a",
    ),

    (
        ">=15 anos consecutivos",
        "rede_extremos_consecutiva_15a",
    ),
]:

    selecionadas = (
        metadata[
            metadata[
                coluna
            ]
        ]
        .copy()
    )


    linha = {
        "rede":
            nome_rede,

        "Brasil":
            len(
                selecionadas
            ),
    }


    soma_regioes = 0


    for regiao in REGIOES:

        quantidade = int(
            (
                selecionadas[
                    "regiao"
                ]
                ==
                regiao
            )
            .sum()
        )


        linha[
            regiao
        ] = quantidade


        soma_regioes += quantidade


    if soma_regioes != linha[
        "Brasil"
    ]:

        raise RuntimeError(
            f"A soma regional da rede "
            f"'{nome_rede}' não corresponde "
            f"ao total Brasil."
        )


    linhas.append(
        linha
    )


distribuicao = pd.DataFrame(
    linhas
)


distribuicao.to_csv(
    SAIDA_DISTRIBUICAO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 8. ANOS VÁLIDOS DE CADA ESTAÇÃO
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
        lambda serie:
            set(
                serie.astype(int)
            )
    )
    .to_dict()
)


regiao_por_codigo = (
    metadata
    .set_index(
        "codigo"
    )[
        "regiao"
    ]
    .to_dict()
)


print(
    f"\nEstações com pelo menos "
    f"um ano válido para extremos: "
    f"{len(anos_por_codigo):,}"
)


# ==========================================================
# 9. PAINÉIS FIXOS TERMINANDO EM 2025
# ==========================================================

paineis = []


for inicio in range(
    ANO_INICIAL,
    2017,
):

    anos_janela = set(
        range(
            inicio,
            ANO_FINAL + 1,
        )
    )


    codigos = [
        codigo

        for codigo, anos
        in anos_por_codigo.items()

        if anos_janela.issubset(
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


    for regiao in REGIOES:

        nome_coluna = (
            "n_"
            +
            regiao.lower()
            .replace(
                "-",
                "_",
            )
        )


        linha[
            nome_coluna
        ] = int(
            sum(
                regiao_por_codigo.get(
                    codigo
                )
                ==
                regiao

                for codigo in codigos
            )
        )


    paineis.append(
        linha
    )


df_paineis = pd.DataFrame(
    paineis
)


# ==========================================================
# 10. VALIDAR SOMA DAS REGIÕES NOS PAINÉIS
# ==========================================================

for _, linha in df_paineis.iterrows():

    soma_regioes = int(
        linha[
            "n_norte"
        ]
        +
        linha[
            "n_nordeste"
        ]
        +
        linha[
            "n_centro_oeste"
        ]
        +
        linha[
            "n_sudeste"
        ]
        +
        linha[
            "n_sul"
        ]
    )


    if (
        soma_regioes
        !=
        int(
            linha[
                "n_estacoes"
            ]
        )
    ):

        raise RuntimeError(
            "A soma regional não corresponde "
            "ao total do painel.\n"
            f"Ano inicial: {int(linha['ano_inicial'])}\n"
            f"Total: {int(linha['n_estacoes'])}\n"
            f"Soma regional: {soma_regioes}"
        )


# ==========================================================
# 11. VALIDAR CONTAGENS DOS PAINÉIS JÁ CONHECIDAS
# ==========================================================

esperado_paineis = {
    2007: 1,
    2008: 3,
    2009: 6,
    2010: 6,
    2011: 8,
    2012: 8,
    2013: 8,
    2014: 8,
    2015: 11,
    2016: 14,
}


for inicio, esperado in esperado_paineis.items():

    valor = (
        df_paineis.loc[
            df_paineis[
                "ano_inicial"
            ]
            ==
            inicio,
            "n_estacoes",
        ]
        .iloc[0]
    )


    if int(
        valor
    ) != esperado:

        raise RuntimeError(
            f"Painel {inicio}-{ANO_FINAL}: "
            f"esperávamos {esperado} estações, "
            f"mas encontramos {int(valor)}."
        )


# ==========================================================
# 12. SALVAR PAINÉIS
# ==========================================================

df_paineis.to_csv(
    SAIDA_PAINEIS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 13. RESULTADOS
# ==========================================================

print("\n" + "=" * 90)
print("DISTRIBUIÇÃO DAS REDES")
print("=" * 90)


print(
    distribuicao.to_string(
        index=False
    )
)


print("\n" + "=" * 90)
print("PAINÉIS FIXOS CORRIGIDOS")
print("=" * 90)


print(
    df_paineis.to_string(
        index=False
    )
)


# ==========================================================
# 14. PAINÉIS DE INTERESSE
# ==========================================================

print("\n" + "=" * 90)
print("PAINÉIS DE INTERESSE")
print("=" * 90)


interesse = (
    df_paineis[
        df_paineis[
            "duracao_anos"
        ]
        .isin(
            [
                10,
                15,
                16,
                17,
            ]
        )
    ]
)


print(
    interesse.to_string(
        index=False
    )
)


# ==========================================================
# 15. ARQUIVOS
# ==========================================================

print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    SAIDA_REDE
)


print(
    SAIDA_DISTRIBUICAO
)


print(
    SAIDA_PAINEIS
)


print("\n" + "=" * 90)
print("REGIÕES CORRIGIDAS")
print("=" * 90)
