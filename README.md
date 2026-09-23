[README.md](https://github.com/user-attachments/files/32567583/README.md)
# Estudos Climáticos

Repositório dedicado a estudos de análise climática, validação de reanálises e comparação com observações meteorológicas no Brasil.

Atualmente, o projeto principal é a avaliação da temperatura máxima horária do **ERA5** em relação às estações meteorológicas automáticas do **INMET**, incluindo controle de qualidade, pareamento espaço-temporal, métricas de desempenho, extremos anuais e tendências climáticas.

## Projeto principal

### `avaliacao_era5_inmet`

O projeto avalia a capacidade do ERA5 de reproduzir as temperaturas máximas horárias observadas pelo INMET e investiga a coerência das tendências das máximas anuais entre as duas fontes.

Períodos analisados:

- **ERA5:** 1995–2025
- **INMET automático:** 2000–2025

A variável ERA5 utilizada é `mx2t`, correspondente à **temperatura máxima a 2 m desde o pós-processamento anterior**, escolhida por sua compatibilidade temporal com a variável do INMET **temperatura máxima na hora anterior**.

## Principais etapas do pipeline

O fluxo de trabalho foi organizado em etapas independentes e auditáveis:

1. inspeção e auditoria dos arquivos ERA5;
2. identificação e complementação de horários ausentes;
3. obtenção e preparação dos dados automáticos do INMET;
4. controle de qualidade de observações e metadados;
5. associação espacial entre estação e célula ERA5 mais próxima;
6. pareamento horário ERA5 × INMET;
7. cálculo de Bias, MAE, RMSE e correlação;
8. investigação de casos críticos e anomalias temporais;
9. construção da amostra analítica;
10. preparação das redes para análise de extremos;
11. cálculo das máximas anuais;
12. Mann-Kendall e Sen's Slope;
13. correção para múltiplos testes por FDR;
14. análise complementar de autocorrelação com Hamed-Rao;
15. análise de robustez;
16. geração de tabelas, gráficos e mapas finais.

## Resultados consolidados

Na amostra analítica principal foram utilizados aproximadamente **71,9 milhões de pares horários ERA5–INMET**.

As medianas das métricas por estação foram:

| Métrica | Valor |
|---|---:|
| Bias | -0,3665 °C |
| MAE | 1,4403 °C |
| RMSE | 1,8429 °C |
| Correlação de Pearson | 0,9357 |

A convenção adotada para o erro foi:

```text
ERA5 - INMET
```

Assim, Bias negativo indica subestimativa média do ERA5 em relação ao INMET.

Para tendências das máximas anuais, a rede principal foi composta por **45 estações com pelo menos 15 anos válidos**, enquanto uma rede ampliada de **214 estações com pelo menos 10 anos válidos** foi usada como análise de sensibilidade.

Na rede principal:

- Sen's Slope mediana INMET: **+0,875 °C/década**
- Sen's Slope mediana ERA5: **+0,903 °C/década**
- concordância de sinal entre ERA5 e INMET: **88,9%**

Esses resultados devem ser interpretados como evidência de coerência entre os produtos na amostra estudada. Eles não implicam que ERA5 substitua observações de estação nem que toda a variabilidade climática do território brasileiro seja representada de forma uniforme.

## Estrutura do projeto

```text
avaliacao_era5_inmet/
├── data/
│   ├── processed/
│   ├── raw/              # ignorado no GitHub
│   └── interim/          # ignorado no GitHub
├── docs/
│   ├── metodologia.md
│   └── resultados_consolidados.md
├── outputs/
│   ├── figures/
│   └── tables/
├── src/
│   ├── 00_check_environment.py
│   ├── 01_...
│   ├── ...
│   ├── 06j_robustez_tendencias_extremos.py
│   ├── 07a_consolidar_resultados.py
│   └── 07b_figuras_mapas_finais.py
├── requirements.txt
├── requirements_final.txt
└── README.md
```

## Dados

Os arquivos brutos e intermediários de grande volume **não são versionados no GitHub**.

Entre os formatos excluídos do versionamento estão:

- GRIB;
- NetCDF;
- ZIPs históricos;
- Parquet intermediários;
- arquivos temporários de download.

Essa decisão evita armazenar no Git arquivos de centenas de megabytes ou vários gigabytes.

As principais fontes de dados utilizadas foram:

- **ERA5 / Copernicus Climate Data Store / ECMWF**
- **INMET — Instituto Nacional de Meteorologia**
- **IBGE — malhas territoriais do Brasil e Unidades da Federação**

## Reprodutibilidade

O ambiente final utilizado no desenvolvimento foi:

```text
Python 3.14.4
```

As dependências congeladas ao final da análise estão disponíveis em:

```text
avaliacao_era5_inmet/requirements_final.txt
```

Para criar um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r avaliacao_era5_inmet/requirements_final.txt
```

Alguns scripts dependem de arquivos climáticos e observacionais que não estão incluídos no repositório por causa do tamanho. Consulte a documentação interna antes de reproduzir o pipeline completo.

## Figuras finais

Os principais produtos gráficos estão em:

```text
avaliacao_era5_inmet/outputs/figures/finais/
```

Entre eles:

- mapas de Sen's Slope das máximas anuais INMET;
- mapas de Sen's Slope das máximas anuais ERA5;
- mapas da tendência da diferença ERA5 − INMET;
- mapas de concordância do sinal das tendências;
- comparação das slopes ERA5 × INMET;
- RMSE regional.


## Documentação

A metodologia e os resultados consolidados podem ser consultados em:

```text
avaliacao_era5_inmet/docs/metodologia.md
avaliacao_era5_inmet/docs/resultados_consolidados.md
```

Esses arquivos registram as decisões metodológicas, critérios de controle de qualidade, definição das redes de análise e principais limitações do estudo.

## Observações metodológicas

Alguns pontos importantes para interpretação dos resultados:

- ERA5 representa uma célula de grade, enquanto o INMET mede condições pontuais;
- diferenças de altitude, relevo, exposição e proximidade do litoral podem gerar discrepâncias legítimas;
- a rede automática do INMET mudou ao longo do tempo;
- a distribuição espacial das séries longas não é uniforme;
- correlação horária elevada não deve ser interpretada isoladamente como evidência de tendência climática;
- os testes de tendência foram acompanhados por correção FDR;
- Hamed-Rao foi usado como análise complementar de robustez em séries consecutivas.

## Status

O pipeline principal de validação, extremos e tendências foi concluído.

Próximas extensões possíveis incluem:

- análise anual e sazonal de temperatura média;
- precipitação anual e sazonal;
- expansão para outros produtos de reanálise;
- comparação com outras redes observacionais;
- homogeneização climatológica mais aprofundada das séries de estação.

---

Este repositório prioriza **rastreabilidade, reprodutibilidade e transparência metodológica**. Resultados climáticos devem ser interpretados em conjunto com as limitações observacionais, espaciais e estatísticas do conjunto de dados utilizado.
