from pathlib import Path

import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# OBJETIVO
# ==========================================================
#
# Consolidar em poucas tabelas os números finais já
# validados ao longo do projeto.
#
# Este script NÃO recalcula os milhões de pares horários.
# Ele reúne os resultados dos blocos anteriores e gera:
#
# - resumo final da amostra;
# - resumo final da validação ERA5 x INMET;
# - resumo final das tendências;
# - resumo das redes de extremos;
# - síntese em Markdown para consulta e redação.
#
# ==========================================================


ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


DOCS_DIR = (
    PROJECT_DIR
    / "docs"
)


DOCS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==========================================================
# ENTRADAS OBRIGATÓRIAS
# ==========================================================

ARQUIVO_ROBUSTEZ = (
    TABLES_DIR
    / "robustez_tendencias_sintese.csv"
)


ARQUIVO_REDE = (
    TABLES_DIR
    / "distribuicao_rede_extremos_regiao.csv"
)


ARQUIVO_PAINEIS = (
    TABLES_DIR
    / "paineis_fixos_extremos_anuais_corrigido.csv"
)


ARQUIVO_TENDENCIAS_REGIAO = (
    TABLES_DIR
    / "resumo_tendencias_extremos_regiao.csv"
)


ARQUIVO_MK_MODIFICADO = (
    TABLES_DIR
    / "resumo_mk_modificado_rede.csv"
)


# ==========================================================
# SAÍDAS
# ==========================================================

SAIDA_AMOSTRA = (
    TABLES_DIR
    / "final_resumo_amostra.csv"
)


SAIDA_VALIDACAO = (
    TABLES_DIR
    / "final_resumo_validacao_era5_inmet.csv"
)


SAIDA_TENDENCIAS = (
    TABLES_DIR
    / "final_resumo_tendencias.csv"
)


SAIDA_REDES = (
    TABLES_DIR
    / "final_resumo_redes_extremos.csv"
)


SAIDA_INDICE = (
    TABLES_DIR
    / "final_indice_resultados.csv"
)


SAIDA_MD = (
    DOCS_DIR
    / "resultados_consolidados.md"
)


# ==========================================================
# NÚMEROS JÁ VALIDADOS NOS BLOCOS ANTERIORES
#
# Mantemos estes números explícitos para que a tabela final
# seja independente dos nomes intermediários usados pelos
# scripts 05/06.
# ==========================================================

AMOSTRA = [
    {
        "indicador":
            "Estacoes INMET totais processadas",
        "valor":
            648,
        "unidade":
            "estacoes",
    },
    {
        "indicador":
            "Estacoes elegiveis espacialmente pareadas",
        "valor":
            645,
        "unidade":
            "estacoes",
    },
    {
        "indicador":
            "Pares horarios completos antes do QC final",
        "valor":
            71927348,
        "unidade":
            "pares",
    },
    {
        "indicador":
            "Pares horarios na amostra analitica principal",
        "valor":
            71901988,
        "unidade":
            "pares",
    },
    {
        "indicador":
            "Pares excluidos por anomalias temporais",
        "valor":
            25360,
        "unidade":
            "pares",
    },
    {
        "indicador":
            "Percentual excluido da amostra pareada",
        "valor":
            0.035258,
        "unidade":
            "%",
    },
    {
        "indicador":
            "Estacao-ano aptas para extremos antes do criterio mensal",
        "valor":
            6551,
        "unidade":
            "estacao-ano",
    },
    {
        "indicador":
            "Estacao-ano aptas para extremos apos 12 meses >=80%",
        "valor":
            4462,
        "unidade":
            "estacao-ano",
    },
]


VALIDACAO = [
    {
        "escala":
            "Estacao - distribuicao geral",
        "area":
            "Brasil",
        "bias_c":
            -0.3665,
        "mae_c":
            1.4403,
        "rmse_c":
            1.8429,
        "correlacao":
            0.9357,
        "observacao":
            "Medianas das metricas por estacao na amostra principal",
    },
    {
        "escala":
            "Anual - todos os pares",
        "area":
            "Brasil",
        "bias_c":
            -0.4029,
        "mae_c":
            1.5256,
        "rmse_c":
            2.0031,
        "correlacao":
            0.9385,
        "observacao":
            "Mediana entre anos, agregacao por todos os pares horarios",
    },
    {
        "escala":
            "Anual - peso igual por estacao-ano",
        "area":
            "Brasil",
        "bias_c":
            -0.4086,
        "mae_c":
            None,
        "rmse_c":
            2.0009,
        "correlacao":
            0.9351,
        "observacao":
            "Mediana entre anos; correlacao = mediana das estacoes",
    },
    {
        "escala":
            "Anual - todos os pares",
        "area":
            "Norte",
        "bias_c":
            -0.4507,
        "mae_c":
            1.4946,
        "rmse_c":
            1.9407,
        "correlacao":
            0.8794,
        "observacao":
            "Mediana anual regional",
    },
    {
        "escala":
            "Anual - todos os pares",
        "area":
            "Nordeste",
        "bias_c":
            -0.5895,
        "mae_c":
            1.4030,
        "rmse_c":
            1.8292,
        "correlacao":
            0.9239,
        "observacao":
            "Mediana anual regional",
    },
    {
        "escala":
            "Anual - todos os pares",
        "area":
            "Centro-Oeste",
        "bias_c":
            -0.2171,
        "mae_c":
            1.5008,
        "rmse_c":
            1.9608,
        "correlacao":
            0.9290,
        "observacao":
            "Mediana anual regional",
    },
    {
        "escala":
            "Anual - todos os pares",
        "area":
            "Sudeste",
        "bias_c":
            -0.3224,
        "mae_c":
            1.7064,
        "rmse_c":
            2.2378,
        "correlacao":
            0.9097,
        "observacao":
            "Mediana anual regional",
    },
    {
        "escala":
            "Anual - todos os pares",
        "area":
            "Sul",
        "bias_c":
            -0.2857,
        "mae_c":
            1.4548,
        "rmse_c":
            1.9325,
        "correlacao":
            0.9494,
        "observacao":
            "Mediana anual regional",
    },
]


# ==========================================================
# AUXILIARES
# ==========================================================

def exigir(
    caminho,
):

    if not caminho.exists():

        raise FileNotFoundError(
            f"Arquivo obrigatório não encontrado:\n"
            f"{caminho}"
        )


def fmt(
    valor,
    casas=4,
):

    if pd.isna(
        valor
    ):

        return "NA"

    if isinstance(
        valor,
        (int,),
    ):

        return f"{valor:,}"

    try:

        return f"{float(valor):.{casas}f}"

    except Exception:

        return str(
            valor
        )


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("CONSOLIDAÇÃO FINAL DOS RESULTADOS")
print("=" * 90)


for arquivo in [
    ARQUIVO_ROBUSTEZ,
    ARQUIVO_REDE,
    ARQUIVO_PAINEIS,
    ARQUIVO_TENDENCIAS_REGIAO,
    ARQUIVO_MK_MODIFICADO,
]:

    exigir(
        arquivo
    )


# ==========================================================
# 1. AMOSTRA
# ==========================================================

df_amostra = pd.DataFrame(
    AMOSTRA
)


df_amostra.to_csv(
    SAIDA_AMOSTRA,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 2. VALIDAÇÃO ERA5 x INMET
# ==========================================================

df_validacao = pd.DataFrame(
    VALIDACAO
)


df_validacao.to_csv(
    SAIDA_VALIDACAO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 3. TENDÊNCIAS E ROBUSTEZ
# ==========================================================

robustez = pd.read_csv(
    ARQUIVO_ROBUSTEZ
)


colunas_tendencias = [
    "rede",
    "nome_rede",
    "n_estacoes",
    "sen_inmet_mediana_c_decada",
    "sen_era5_mediana_c_decada",
    "sen_delta_mediana_c_decada",
    "pct_inmet_slope_positivo",
    "pct_era5_slope_positivo",
    "pct_mesmo_sinal_inmet_era5",
    "n_inmet_fdr05",
    "n_era5_fdr05",
    "n_delta_fdr05",
]


faltantes = [
    coluna
    for coluna in colunas_tendencias
    if coluna not in robustez.columns
]


if faltantes:

    raise RuntimeError(
        "robustez_tendencias_sintese.csv não possui "
        f"as colunas esperadas: {faltantes}"
    )


df_tendencias = (
    robustez[
        colunas_tendencias
    ]
    .copy()
)


df_tendencias.to_csv(
    SAIDA_TENDENCIAS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 4. REDES DE EXTREMOS
# ==========================================================

rede = pd.read_csv(
    ARQUIVO_REDE
)


df_redes = rede.copy()


df_redes.to_csv(
    SAIDA_REDES,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 5. ÍNDICE DOS RESULTADOS FINAIS
# ==========================================================

indice = pd.DataFrame(
    [
        {
            "categoria":
                "Amostra",
            "arquivo":
                str(
                    SAIDA_AMOSTRA
                ),
            "descricao":
                "Tamanho da amostra, pares e filtros principais",
        },
        {
            "categoria":
                "Validacao",
            "arquivo":
                str(
                    SAIDA_VALIDACAO
                ),
            "descricao":
                "Bias, MAE, RMSE e correlacao finais",
        },
        {
            "categoria":
                "Tendencias",
            "arquivo":
                str(
                    SAIDA_TENDENCIAS
                ),
            "descricao":
                "Sen slopes, concordancia e FDR nas quatro redes",
        },
        {
            "categoria":
                "Redes",
            "arquivo":
                str(
                    SAIDA_REDES
                ),
            "descricao":
                "Distribuicao espacial das redes de extremos",
        },
        {
            "categoria":
                "Robustez detalhada",
            "arquivo":
                str(
                    ARQUIVO_ROBUSTEZ
                ),
            "descricao":
                "Sintese produzida pelo 06j",
        },
        {
            "categoria":
                "MK modificado",
            "arquivo":
                str(
                    ARQUIVO_MK_MODIFICADO
                ),
            "descricao":
                "Resumo Hamed-Rao e autocorrelacao",
        },
        {
            "categoria":
                "Tendencias regionais",
            "arquivo":
                str(
                    ARQUIVO_TENDENCIAS_REGIAO
                ),
            "descricao":
                "Resumo das Sen slopes por regiao",
        },
        {
            "categoria":
                "Paineis fixos",
            "arquivo":
                str(
                    ARQUIVO_PAINEIS
                ),
            "descricao":
                "Paineis consecutivos terminando em 2025",
        },
    ]
)


indice.to_csv(
    SAIDA_INDICE,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 6. GERAR RESUMO MARKDOWN
# ==========================================================

principal = (
    df_tendencias[
        df_tendencias[
            "rede"
        ]
        ==
        "principal_15a"
    ]
    .iloc[0]
)


sensibilidade = (
    df_tendencias[
        df_tendencias[
            "rede"
        ]
        ==
        "sensibilidade_10a"
    ]
    .iloc[0]
)


consecutiva = (
    df_tendencias[
        df_tendencias[
            "rede"
        ]
        ==
        "principal_consecutiva_15a"
    ]
    .iloc[0]
)


texto = f"""# Resultados consolidados: avaliação ERA5 × INMET

## 1. Escopo

A validação usa estações automáticas do INMET no período disponível entre 2000 e 2025 e ERA5 em grade de 0,25°. A variável analisada é a temperatura máxima horária desde o pós-processamento anterior (`mx2t`), convertida de Kelvin para graus Celsius.

O erro foi definido como:

**ERA5 - INMET**

Valores negativos de bias indicam, portanto, subestimativa do ERA5 em relação ao INMET.

## 2. Amostra analítica

- Estações INMET processadas: **648**.
- Estações espacialmente elegíveis e pareadas: **645**.
- Pares horários completos: **71.927.348**.
- Pares horários na análise principal após QC: **71.901.988**.
- Pares excluídos por quatro anomalias temporais: **25.360**, equivalentes a aproximadamente **0,0353%** da amostra pareada.
- Estação-ano inicialmente aptas para análise de tendência: **6.551**.
- Após exigir cobertura >=80% em cada um dos 12 meses: **4.462 estação-ano**.

## 3. Desempenho ERA5 × INMET

Na distribuição das métricas por estação, as medianas foram:

- Bias: **-0,3665 °C**
- MAE: **1,4403 °C**
- RMSE: **1,8429 °C**
- Correlação de Pearson: **0,9357**

Na agregação anual nacional por todos os pares horários, as medianas entre 2000 e 2025 foram:

- Bias: **-0,4029 °C**
- MAE: **1,5256 °C**
- RMSE: **2,0031 °C**
- Correlação de Pearson: **0,9385**

Esses resultados indicam forte covariação entre ERA5 e INMET e uma pequena tendência média de subestimativa do ERA5, embora diferenças locais relevantes permaneçam, especialmente em estações de relevo complexo e em casos com mudanças históricas de localização/metadados.

## 4. Rede de extremos

A rede com cobertura mensal adequada resultou em:

- **214 estações** com pelo menos 10 anos válidos;
- **45 estações** com pelo menos 15 anos válidos;
- **27 estações** com pelo menos 10 anos consecutivos;
- **9 estações** com pelo menos 15 anos consecutivos.

A rede principal foi definida como as **45 estações com >=15 anos válidos**. A rede de **214 estações com >=10 anos válidos** foi usada como sensibilidade.

## 5. Tendências das máximas anuais

### Rede principal: >=15 anos válidos

- Sen's Slope mediana INMET: **{fmt(principal["sen_inmet_mediana_c_decada"])} °C/década**
- Sen's Slope mediana ERA5: **{fmt(principal["sen_era5_mediana_c_decada"])} °C/década**
- Sen's Slope mediana de ERA5-INMET: **{fmt(principal["sen_delta_mediana_c_decada"])} °C/década**
- Slopes positivas no INMET: **{fmt(principal["pct_inmet_slope_positivo"], 1)}%**
- Slopes positivas no ERA5: **{fmt(principal["pct_era5_slope_positivo"], 1)}%**
- Mesmo sinal INMET/ERA5: **{fmt(principal["pct_mesmo_sinal_inmet_era5"], 1)}%**

Nenhuma estação dessa rede permaneceu significativa após correção FDR no Mann-Kendall clássico.

### Rede de sensibilidade: >=10 anos válidos

- Sen's Slope mediana INMET: **{fmt(sensibilidade["sen_inmet_mediana_c_decada"])} °C/década**
- Sen's Slope mediana ERA5: **{fmt(sensibilidade["sen_era5_mediana_c_decada"])} °C/década**
- Sen's Slope mediana de ERA5-INMET: **{fmt(sensibilidade["sen_delta_mediana_c_decada"])} °C/década**
- Mesmo sinal INMET/ERA5: **{fmt(sensibilidade["pct_mesmo_sinal_inmet_era5"], 1)}%**

## 6. Autocorrelação e robustez

Para não aplicar correções de autocorrelação sobre séries com lacunas temporais, o Hamed-Rao foi avaliado apenas nos maiores segmentos anuais consecutivos.

Na rede consecutiva principal:

- estações: **{int(consecutiva["n_estacoes"])}**
- Sen's Slope mediana INMET: **{fmt(consecutiva["sen_inmet_mediana_c_decada"])} °C/década**
- Sen's Slope mediana ERA5: **{fmt(consecutiva["sen_era5_mediana_c_decada"])} °C/década**
- mesmo sinal INMET/ERA5: **{fmt(consecutiva["pct_mesmo_sinal_inmet_era5"], 1)}%**

A comparação entre Mann-Kendall clássico e Hamed-Rao nas mesmas séries não alterou nenhuma classificação de significância em p<0,05. Assim, a autocorrelação não modificou substancialmente a interpretação inferencial nesse subconjunto.

## 7. Interpretação integrada

Os resultados mostram três padrões consistentes:

1. O ERA5 acompanha fortemente a variabilidade horária observada pelo INMET.
2. Há pequena subestimativa média das temperaturas máximas pelo ERA5, com heterogeneidade espacial e maior discrepância em alguns ambientes complexos.
3. As tendências das máximas anuais são predominantemente positivas tanto no INMET quanto no ERA5, e a tendência mediana da diferença ERA5-INMET permanece próxima de zero.

A proximidade entre as Sen's Slopes de ERA5 e INMET e a elevada concordância de sinal sugerem que o ERA5 reproduz de forma coerente a direção temporal das máximas nas estações analisadas. Entretanto, a rede não possui distribuição espacial uniforme, especialmente na amostra de séries longas, e a ausência de significância após FDR na rede principal exige cautela ao transformar predominância de slopes positivas em afirmações inferenciais nacionais.

## 8. Limitações a registrar

- expansão e mudança temporal da rede automática do INMET;
- distribuição espacial desigual das estações;
- diferenças de altitude, relevo e representatividade entre ponto observado e célula ERA5;
- mudanças históricas de coordenadas/metadados em algumas estações;
- rede de séries consecutivas longa muito pequena;
- máximas anuais são estatisticamente ruidosas;
- correlação horária bruta inclui ciclos sazonais e diurnos;
- a máxima anual ERA5 usada na comparação pareada é restrita aos horários em que existe observação INMET válida;
- resultados de estações individuais após múltiplos testes não devem ser tratados como evidência nacional independente.

## 9. Conclusão operacional

Para o trabalho final, recomenda-se usar como resultado central:

- validação horária da amostra principal;
- métricas nacionais e regionais;
- rede de 45 estações com >=15 anos válidos para tendências;
- rede de 214 estações como sensibilidade;
- Hamed-Rao apenas como teste complementar de robustez;
- mapas das Sen's Slopes com limites estaduais;
- resultados de painéis fixos apenas como complemento, e não como representação principal do Brasil.
"""


SAIDA_MD.write_text(
    texto,
    encoding="utf-8",
)


# ==========================================================
# 7. TERMINAL
# ==========================================================

print("\nArquivos finais gerados:")


for arquivo in [
    SAIDA_AMOSTRA,
    SAIDA_VALIDACAO,
    SAIDA_TENDENCIAS,
    SAIDA_REDES,
    SAIDA_INDICE,
    SAIDA_MD,
]:

    print(
        arquivo
    )


print("\n" + "=" * 90)
print("CONSOLIDAÇÃO NUMÉRICA CONCLUÍDA")
print("=" * 90)
