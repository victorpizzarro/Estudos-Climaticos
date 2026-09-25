# Köppen–Geiger a partir do ERA5 (1995–2025)

Reprodução exploratória, com dados modernos do ERA5 (`reanalysis-era5-single-levels-monthly-means`), do mapa de classificação climática de Köppen apresentado em Alvares et al. (2013), *"Köppen's climate classification map for Brazil"*.

## Escopo

- **Área coberta pelos dados baixados** (recorte parcial, não o Brasil inteiro): lat -14° a -25.5°, lon -53.5° a -39.5° — cobre aproximadamente GO/DF/MS/MG/SP/parte do PR e TO/BA.
- **Variáveis:** `2t` (temperatura do ar a 2m) e `tp` (precipitação total), médias mensais, grade 0.1°, jan/1995–dez/2025 (31 anos).
- **Critérios de classificação:** os mesmos usados no artigo original (Köppen 1936), na formalização padrão de Kottek et al. (2006) / Peel et al. (2007), seguida também por Alvares et al. (2013).

## Conteúdo

```text
classificacao_koppen_era5/
├── cds_request.py                 # requisição à CDS API (ERA5) usada para gerar o GRIB de entrada
├── notebook.ipynb                 # notebook principal: análise, algoritmo de Köppen e mapas
├── Cópia_de_sudeste_2025.ipynb     # notebook auxiliar/exploratório (recorte Sudeste)
├── documentacao_koppen_era5.pdf    # relatório com metodologia e resultados
├── data/
│   └── brazil_states.geojson      # contorno dos estados brasileiros (fonte: click_that_hood)
├── doc_assets/                    # figuras e artefatos usados na documentação/relatório
└── output.png, output2.png        # figuras geradas pelo notebook
```

O GRIB de entrada (`93eefbba64a366960bd916ed34f628a3.grib`, baixado via `cds_request.py`) não é versionado por ser um arquivo climático pesado (ver `.gitignore` do repositório).

## Pipeline

1. Carregamento do GRIB (earthkit-data) e conversão para xarray.
2. Análise exploratória da série temporal e climatologia mensal (1995–2025).
3. Implementação vetorizada (numpy) do algoritmo de classificação de Köppen–Geiger, seguindo a Tabela 1 do artigo / Kottek et al. (2006) / Peel et al. (2007), com prioridade B → A → E → C/D.
4. Verificação do algoritmo com perfis sintéticos cobrindo todos os subtipos climáticos, inclusive os que não ocorrem na região.
5. Geração do mapa de classificação de Köppen (ERA5, 1995–2025) e validação ponto a ponto contra localidades da Figura 8 do artigo original.
6. Análise de sensibilidade temporal (1995–2010 vs. 2011–2025) para investigar migração de tipos climáticos.
7. Climogramas para as capitais de SP, RJ, ES e MG.

## Principais ressalvas metodológicas

- **Área parcial**: a bbox baixada não cobre o Brasil inteiro do artigo original. Para o mapa completo, refazer o request com `area=[6, -74, -34, -34]` (ver `cds_request.py`).
- **Resolução espacial**: ERA5 tem grade nativa de ~31 km (aqui reamostrada a 0.1°); o artigo original chega a 1 ha via krigagem de 2.950 estações + modelo de temperatura por altitude. Isso gera divergências pontuais esperadas em regiões de relevo acentuado (ex.: picos de montanha subestimados em altitude/resfriamento).
- O algoritmo passa 15/15 testes sintéticos, então divergências com o artigo vêm dos dados de entrada (ERA5 vs. estações), não das regras de classificação.

## Reprodutibilidade

Dependências principais: `numpy`, `pandas`, `xarray`, `earthkit-data`, `geopandas`, `matplotlib`, `cdsapi`.

Para baixar os dados de origem (requer conta e chave de API no [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/)):

```bash
python cds_request.py
```

Isso gera o arquivo GRIB usado pelo `notebook.ipynb` (`GRIB_PATH` no início do notebook).
