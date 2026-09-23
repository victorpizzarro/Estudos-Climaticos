# Resultados consolidados: avaliação ERA5 × INMET

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

- Sen's Slope mediana INMET: **0.8750 °C/década**
- Sen's Slope mediana ERA5: **0.9031 °C/década**
- Sen's Slope mediana de ERA5-INMET: **0.0315 °C/década**
- Slopes positivas no INMET: **88.9%**
- Slopes positivas no ERA5: **100.0%**
- Mesmo sinal INMET/ERA5: **88.9%**

Nenhuma estação dessa rede permaneceu significativa após correção FDR no Mann-Kendall clássico.

### Rede de sensibilidade: >=10 anos válidos

- Sen's Slope mediana INMET: **0.8333 °C/década**
- Sen's Slope mediana ERA5: **0.7387 °C/década**
- Sen's Slope mediana de ERA5-INMET: **0.0382 °C/década**
- Mesmo sinal INMET/ERA5: **81.8%**

## 6. Autocorrelação e robustez

Para não aplicar correções de autocorrelação sobre séries com lacunas temporais, o Hamed-Rao foi avaliado apenas nos maiores segmentos anuais consecutivos.

Na rede consecutiva principal:

- estações: **9**
- Sen's Slope mediana INMET: **1.3333 °C/década**
- Sen's Slope mediana ERA5: **1.2787 °C/década**
- mesmo sinal INMET/ERA5: **88.9%**

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
