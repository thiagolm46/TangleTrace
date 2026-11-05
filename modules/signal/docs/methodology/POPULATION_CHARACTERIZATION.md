# Caracterizacao da populacao de canais mantidos

## 1. Escopo, fontes e reproducibilidade

Este documento descreve o corpus apos a selecao de canais da Etapa 2, antes do sorteio das janelas da Etapa 3. As estatisticas sao descritivas do export observado, nao estimativas de todas as mensagens das comunidades nem resultados de classificacao semantica ou toxicidade.

Extracao das estatisticas: `2026-10-27T21:29:23.040882+00:00`. Todos os horarios e agrupamentos temporais usam UTC.

Entrada congelada: `messages.parquet`.

Os calculos deste documento sao executados por `discord_disentanglement/population_report.py`, sobre os CSVs e o resumo produzidos por `discord_disentanglement/population.py`. O gerador verifica os hashes dos artefatos e a reconciliacao dos totais antes de escrever. Nao precisa reler os milhoes de mensagens para gerar o texto.

```powershell
python -m discord_disentanglement.population_report
```

Para regenerar explicitamente ou usar outros artefatos:

```powershell
python -m discord_disentanglement.population_report `
  --input-dir data/processed/disentanglement/population_participants_v2 `
  --output docs/methodology/POPULATION_CHARACTERIZATION.md `
  --overwrite
```

O Markdown tem um manifesto adjacente com hashes dos artefatos utilizados, do gerador e do documento. A validacao de hashes cobre os relatorios; o Parquet original nao e relido por este gerador. Valores sao formatados com ponto para milhares e virgula para decimais; NA indica denominador nulo ou medida indisponivel. Arredondamento ocorre apenas na apresentacao.

## 2. Populacao observada e quadro utilizavel

| Medida | Valor |
| --- | --- |
| Servidores com registros | 29 |
| Canais com registros | 297 |
| Registros totais | 11.897.859 |
| Registros explicitamente humanos | 11.897.859 |
| Registros com texto ou midia (qualquer autor) | 11.864.848 |
| Mensagens humanas utilizaveis | 11.864.848 |
| Nao utilizaveis: sem texto nem midia registrada | 33.011 |
| Mensagens humanas com conteudo e problemas estruturais | 0 |
| Autores humanos distintos no corpus | 159.773 |
| Autores humanos distintos no quadro utilizavel | 145.780 |
| Primeiro timestamp observado (UTC) | 2017-01-15 18:56:22.736+00 |
| Ultimo timestamp observado (UTC) | 2025-01-12 20:41:07.048+00 |
| Dias com atividade observada no corpus | 2.892 |

Neste projeto, nao utilizavel significa exclusivamente um registro sem texto nao vazio e sem anexo, embed ou sticker registrado. Texto composto apenas por espacos e considerado vazio. Havendo texto ou midia, o registro e utilizavel nesta caracterizacao, independentemente do tipo Discord. Uma mensagem humana utilizavel tem conteudo registrado e `is_bot = false`; status de bot ausente nao e presumido humano. Bots com conteudo nao sao classificados como nao utilizaveis, mas nao pertencem a populacao humana.

IDs ausentes, timestamp invalido e chave duplicada sao problemas estruturais separados, nao motivos de nao utilizabilidade pela definicao adotada. Registros com conteudo e essas flags permanecem no volume utilizavel; calculos que exigem identificacao e ordem cronologica precisam exclui-los de sua base especifica. Todos os tipos de mensagem sao aceitos para volume quando ha conteudo. Utilizabilidade nao garante relevancia tematica ou elegibilidade final para anotacao. O quadro amostral definitivo ainda deve ser congelado apos revisar as restricoes tecnicas das janelas.

Autores sao deduplicados globalmente por ID no resumo. A soma de autores distintos por canal/servidor nao e uma contagem global, pois a mesma pessoa pode aparecer em varios canais. Dias ativos globais tambem nao sao somas dos dias ativos dos canais.

Registros com texto ou midia representam 99,72% do total; 0,28% nao possuem conteudo registrado. Mensagens humanas utilizaveis representam 99,72% do total. Dos autores humanos observados, 91,24% possuem ao menos uma mensagem utilizavel. A diferenca entre autores observados e autores do quadro decorre da disponibilidade de conteudo em suas mensagens, nao do tipo Discord.

A definicao `payload_v2` substitui a regra inicial que tambem rejeitava tipos diferentes de 0/19 e problemas estruturais. Os artefatos anteriores permanecem em `data/processed/disentanglement/population`; as estatisticas abaixo foram recalculadas pela nova regra. Mensagens totalmente ausentes do export continuam sendo uma perda desconhecida, distinta de registros presentes sem conteudo.

## 3. Distribuicao de volume e concentracao

### 3.1. Distribuicao entre canais e servidores

| Unidade | Medida | Min | Q25 | Mediana | Media | Q75 | Q90 | Q95 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Canal | Registros | 500,00 | 1.604,00 | 6.448,00 | 40.060,13 | 25.419,00 | 94.397,60 | 221.191,00 | 790.223,00 |
| Canal | Mensagens utilizaveis | 2,00 | 1.601,00 | 6.433,00 | 39.948,98 | 25.414,00 | 94.346,40 | 221.152,20 | 790.141,00 |
| Canal | Autores humanos distintos | 10,00 | 83,00 | 196,00 | 803,02 | 484,00 | 1.508,60 | 2.508,80 | 57.005,00 |
| Servidor | Registros | 519,00 | 30.784,00 | 210.709,00 | 410.271,00 | 662.537,00 | 1.024.294,80 | 1.300.469,80 | 2.440.549,00 |
| Servidor | Mensagens utilizaveis | 519,00 | 30.758,00 | 210.673,00 | 409.132,69 | 662.397,00 | 1.022.648,80 | 1.299.898,20 | 2.439.555,00 |
| Servidor | Autores humanos distintos | 105,00 | 853,00 | 2.187,00 | 5.538,45 | 3.729,00 | 8.885,20 | 24.606,00 | 57.465,00 |

Os quantis acima sao entre unidades: cada canal ou servidor tem peso um. Usam interpolacao linear (`pandas.Series.quantile`). Nao sao quantis entre mensagens.

### 3.2. Concentracao acumulada

| Unidade | Populacao | Meta de volume | Unidades necessarias | % das unidades | Volume efetivamente coberto |
| --- | --- | --- | --- | --- | --- |
| channel | all_records | 50,00% | 14 | 4,71% | 51,67% |
| channel | all_records | 80,00% | 46 | 15,49% | 80,34% |
| channel | all_records | 90,00% | 81 | 27,27% | 90,07% |
| channel | all_records | 95,00% | 118 | 39,73% | 95,02% |
| channel | usable_human | 50,00% | 14 | 4,71% | 51,68% |
| channel | usable_human | 80,00% | 45 | 15,15% | 80,02% |
| channel | usable_human | 90,00% | 81 | 27,27% | 90,15% |
| channel | usable_human | 95,00% | 117 | 39,39% | 95,01% |
| server | all_records | 50,00% | 4 | 13,79% | 50,39% |
| server | all_records | 80,00% | 9 | 31,03% | 80,82% |
| server | all_records | 90,00% | 13 | 44,83% | 90,73% |
| server | all_records | 95,00% | 16 | 55,17% | 96,02% |
| server | usable_human | 50,00% | 4 | 13,79% | 50,49% |
| server | usable_human | 80,00% | 9 | 31,03% | 80,93% |
| server | usable_human | 90,00% | 13 | 44,83% | 90,84% |
| server | usable_human | 95,00% | 16 | 55,17% | 96,13% |

As unidades sao ordenadas por volume decrescente. O limiar e o menor numero de unidades cuja soma atinge a meta; a participacao efetiva pode exceder a meta devido a indivisibilidade dos canais. `all_records` usa todos os registros; `usable_human` usa o quadro utilizavel.

| Unidade | Populacao | Gini | HHI | Numero efetivo de unidades |
| --- | --- | --- | --- | --- |
| channel | all_records | 0,8021 | 0,0254 | 39,33 |
| channel | usable_human | 0,8029 | 0,0255 | 39,25 |
| server | all_records | 0,6351 | 0,0958 | 10,44 |
| server | usable_human | 0,6364 | 0,0961 | 10,41 |

Gini mede desigualdade de volume (0 indica volumes iguais). HHI e a soma dos quadrados das participacoes, na escala 0 a 1; seu inverso e o numero de unidades de igual volume com concentracao equivalente. Estes indices descrevem volume, nao qualidade ou importancia cientifica.

$$G = \frac{2\sum_{i=1}^{k} i x_{(i)}}{k\sum_{i=1}^{k}x_i}-\frac{k+1}{k}, \qquad HHI=\sum_{i=1}^{k}s_i^2, \qquad k_{efetivo}=\frac{1}{HHI}$$

Na formula de Gini, os volumes sao ordenados de forma crescente; $s_i=x_i/\sum_jx_j$.

| Unidade | Populacao | Maiores unidades | % das mensagens |
| --- | --- | --- | --- |
| channel | all_records | 1 | 6,64% |
| channel | all_records | 5 | 26,65% |
| channel | all_records | 10 | 42,84% |
| channel | all_records | 20 | 61,09% |
| channel | all_records | 50 | 81,85% |
| channel | usable_human | 1 | 6,66% |
| channel | usable_human | 5 | 26,70% |
| channel | usable_human | 10 | 42,83% |
| channel | usable_human | 20 | 61,12% |
| channel | usable_human | 50 | 81,94% |
| server | all_records | 1 | 20,51% |
| server | all_records | 5 | 58,28% |
| server | all_records | 10 | 83,41% |
| server | all_records | 20 | 99,04% |
| server | all_records | 29 | 100,00% |
| server | usable_human | 1 | 20,56% |
| server | usable_human | 5 | 58,40% |
| server | usable_human | 10 | 83,53% |
| server | usable_human | 20 | 99,04% |
| server | usable_human | 29 | 100,00% |

Na populacao utilizavel, 45 de 297 canais (15,15%) atingem 80% do volume, cobrindo efetivamente 80,02%. A unidade de maior volume concentra 6,66% das mensagens utilizaveis.

Na populacao utilizavel, 9 de 29 servidores (31,03%) atingem 80% do volume, cobrindo efetivamente 80,93%. A unidade de maior volume concentra 20,56% das mensagens utilizaveis.

### 3.3. Faixas de tamanho dos canais

| Mensagens utilizaveis por canal | Canais | % dos canais | Mensagens | % das mensagens |
| --- | --- | --- | --- | --- |
| 0 a 499 | 1 | 0,34% | 2 | 0,00% |
| 500 a 999 | 40 | 13,47% | 28.171 | 0,24% |
| 1.000 a 4.999 | 97 | 32,66% | 230.001 | 1,94% |
| 5.000 a 9.999 | 34 | 11,45% | 246.544 | 2,08% |
| 10.000 a 49.999 | 81 | 27,27% | 1.913.029 | 16,12% |
| 50.000 a 99.999 | 15 | 5,05% | 1.118.881 | 9,43% |
| 100.000 ou mais | 29 | 9,76% | 8.328.220 | 70,19% |

As faixas usam mensagens utilizaveis, nao o volume bruto empregado na selecao de canais. O corpus atual exige pelo menos 500 registros brutos e cinco autores humanos distintos por canal. Um canal pode ter menos de 500 mensagens utilizaveis se parte de seus registros nao tiver conteudo.

### 3.4. Todos os servidores, por volume utilizavel

| Servidor | guild_id | Canais | Registros | Utilizaveis | % do quadro | Autores humanos | Primeiro UTC | Ultimo UTC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cyberpunk 2077 Modding Community | 717692382849663036 | 51 | 2.440.549 | 2.439.555 | 20,56% | 32.726 | 2020-12-09 07:17:00.54+00 | 2025-01-07 02:22:06.002+00 |
| MonoGame Discord | 355231098122272778 | 13 | 1.312.931 | 1.312.697 | 11,06% | 3.683 | 2017-09-07 08:39:49.32+00 | 2024-12-25 02:35:41.416+00 |
| Kindred Games Community | 398282199788552193 | 14 | 1.281.778 | 1.280.700 | 10,79% | 5.617 | 2018-01-04 01:50:57.564+00 | 2025-01-06 19:56:45.864+00 |
| Sapphire - Imagine a framework | 737141877803057244 | 19 | 959.924 | 958.136 | 8,08% | 2.106 | 2020-07-27 23:21:46.246+00 | 2025-01-01 19:33:32.725+00 |
| Tech Haven | 455345206481518593 | 14 | 938.522 | 938.437 | 7,91% | 3.806 | 2019-06-16 00:36:16.581+00 | 2024-12-21 23:42:36.655+00 |
| Touhou Game Dev | 933089313405685760 | 33 | 849.501 | 849.092 | 7,16% | 853 | 2022-01-18 20:27:23.069+00 | 2025-01-07 08:50:23.073+00 |
| ImperialPlugins\.com | 284399832385191936 | 7 | 773.163 | 764.246 | 6,44% | 5.854 | 2017-02-23 19:18:59.741+00 | 2025-01-07 03:04:56.565+00 |
| Rectify11 Community | 1077324213142175744 | 10 | 662.537 | 662.397 | 5,58% | 2.303 | 2023-02-28 23:11:31.147+00 | 2024-12-19 04:19:39.637+00 |
| Return Community | 1080829289412432032 | 7 | 396.701 | 396.628 | 3,34% | 3.194 | 2023-06-30 13:40:10.092+00 | 2024-12-28 17:00:44.496+00 |
| OpenRCT2 | 264137540670324737 | 10 | 308.562 | 308.504 | 2,60% | 3.195 | 2020-03-24 21:48:02.745+00 | 2025-01-11 05:05:01.437+00 |
| Docker | 460871933748183040 | 7 | 298.676 | 298.528 | 2,52% | 8.000 | 2018-06-25 18:25:07.59+00 | 2025-01-09 02:15:34.443+00 |
| L'Ordre des Devs | 706640777450881114 | 2 | 289.013 | 286.028 | 2,41% | 2.533 | 2020-05-04 21:52:31.273+00 | 2025-01-04 22:47:11.578+00 |
| Shardeum | 933959587462254612 | 2 | 283.322 | 282.792 | 2,38% | 57.465 | 2022-01-21 05:46:57.828+00 | 2025-01-08 16:27:40.895+00 |
| Terasology | 270264625419911192 | 27 | 228.028 | 227.938 | 1,92% | 888 | 2017-01-15 18:56:22.736+00 | 2025-01-07 04:44:05.86+00 |
| OpenVic - Community | 1062018115275325480 | 11 | 210.709 | 210.673 | 1,78% | 1.650 | 2023-01-09 17:01:43.292+00 | 2025-01-11 04:53:01.239+00 |
| Kavita | 821879810934439936 | 10 | 189.886 | 189.456 | 1,60% | 2.187 | 2021-03-20 16:22:40.316+00 | 2024-12-22 03:55:00.556+00 |
| TheScostumati | 516564332440584221 | 6 | 107.436 | 107.406 | 0,91% | 323 | 2019-01-22 17:25:06.815+00 | 2025-01-08 20:16:27.496+00 |
| Andy’s Development | 857672921912836116 | 2 | 94.314 | 94.238 | 0,79% | 3.729 | 2021-06-25 01:15:46.636+00 | 2025-01-12 20:41:07.048+00 |
| WWebJS | 698610475432411196 | 6 | 96.708 | 82.247 | 0,69% | 12.426 | 2020-04-11 19:36:54.376+00 | 2025-01-08 23:49:21.539+00 |
| 💻 Ouckah Lair | 519640186167099402 | 4 | 61.035 | 61.022 | 0,51% | 993 | 2023-04-05 18:12:51.796+00 | 2025-01-09 02:45:44.216+00 |
| GameDevSG | 558680594498977792 | 8 | 35.634 | 35.386 | 0,30% | 1.030 | 2019-04-07 07:29:16.051+00 | 2024-12-19 16:46:26.402+00 |
| Neo4j | 787399249741479977 | 15 | 30.784 | 30.758 | 0,26% | 2.671 | 2021-03-04 09:00:53.812+00 | 2024-12-24 16:07:50.037+00 |
| Penusbmic's Server | 894976658229063731 | 9 | 30.116 | 30.019 | 0,25% | 868 | 2021-10-08 18:54:51.003+00 | 2025-01-06 18:00:25.479+00 |
| Fermyon | 926888690310053918 | 3 | 5.947 | 5.892 | 0,05% | 430 | 2022-01-01 17:25:48.352+00 | 2025-01-08 10:18:49.792+00 |
| CodingWallah | 1056895641676152852 | 2 | 4.515 | 4.514 | 0,04% | 501 | 2022-12-26 11:26:35.28+00 | 2024-12-15 15:49:33.655+00 |
| Montano Community | 561997286087852118 | 1 | 2.772 | 2.772 | 0,02% | 367 | 2020-04-28 18:17:10.218+00 | 2024-11-20 06:13:19.91+00 |
| Oxylabs | 1128239127687598080 | 1 | 2.187 | 2.183 | 0,02% | 511 | 2023-09-15 09:02:22.631+00 | 2025-01-04 22:27:37.992+00 |
| TikTok Shop Developer Hub | 1204537856870191114 | 2 | 2.090 | 2.085 | 0,02% | 601 | 2024-02-06 21:27:58.8+00 | 2024-12-27 09:15:47.151+00 |
| Rosebud AI | 773712199729414144 | 1 | 519 | 519 | 0,00% | 105 | 2022-03-09 04:00:31.609+00 | 2024-12-03 09:18:05.716+00 |

### 3.5. Os 20 canais de maior volume utilizavel

| Servidor | Canal | channel_id | Utilizaveis | % do quadro | % acumulado | Autores humanos |
| --- | --- | --- | --- | --- | --- | --- |
| Tech Haven | general | 593063949067485204 | 790.141 | 6,66% | 6,66% | 2.734 |
| Sapphire - Imagine a framework | off-topic | 737142209639350343 | 675.805 | 5,70% | 12,36% | 1.740 |
| Rectify11 Community | casual-chat | 1080264228247719977 | 584.267 | 4,92% | 17,28% | 1.352 |
| Cyberpunk 2077 Modding Community | general-chat | 789711087158820864 | 569.877 | 4,80% | 22,08% | 11.967 |
| Kindred Games Community | general-chat | 398282200287543297 | 547.581 | 4,62% | 26,70% | 3.073 |
| Cyberpunk 2077 Modding Community | game-chat | 727800569158434827 | 496.443 | 4,18% | 30,88% | 8.836 |
| MonoGame Discord | off-topic | 357384790158213120 | 478.591 | 4,03% | 34,92% | 800 |
| ImperialPlugins\.com | general | 284399832385191936 | 364.467 | 3,07% | 37,99% | 5.792 |
| Cyberpunk 2077 Modding Community | mod-dev-chat | 727800260486758410 | 290.874 | 2,45% | 40,44% | 6.528 |
| L'Ordre des Devs | discussion | 706642662937067580 | 284.011 | 2,39% | 42,83% | 2.532 |
| Shardeum | 💬・general | 933959587462254615 | 278.422 | 2,35% | 45,18% | 57.005 |
| MonoGame Discord | help | 402546044274999299 | 276.211 | 2,33% | 47,51% | 2.499 |
| MonoGame Discord | monogame-discussion | 355231098122272779 | 251.205 | 2,12% | 49,62% | 1.785 |
| Touhou Game Dev | touhou | 933089316547219558 | 244.327 | 2,06% | 51,68% | 313 |
| MonoGame Discord | programming | 402546188198608897 | 224.841 | 1,90% | 53,58% | 1.246 |
| Kindred Games Community | swords-n-magic-and-chat | 632274671370502145 | 220.230 | 1,86% | 55,44% | 2.660 |
| Return Community | 💬┇chat-here | 1136202840499572736 | 215.679 | 1,82% | 57,25% | 2.363 |
| Return Community | 🔨┇creations | 1124314155990667396 | 167.746 | 1,41% | 58,67% | 1.152 |
| Touhou Game Dev | general | 933089314965970991 | 150.740 | 1,27% | 59,94% | 484 |
| OpenVic - Community | 💬general | 1062021872545447936 | 140.820 | 1,19% | 61,12% | 1.282 |

## 4. Autores e participacao

`distinct_human_authors` conta IDs humanos distintos presentes no canal, sem exigir replies ou mencoes. `distinct_usable_human_authors` exige pelo menos uma mensagem com conteudo registrado. Ambas sao contagens de participantes; nao inferem conversas semanticas. A selecao usa a primeira contagem, juntamente com o volume bruto do canal.

| Medida por canal | Min | Q25 | Mediana | Media | Q75 | Q90 | Q95 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| distinct_human_authors | 10,00 | 83,00 | 196,00 | 803,02 | 484,00 | 1.508,60 | 2.508,80 | 57.005,00 |
| distinct_usable_human_authors | 2,00 | 79,00 | 191,00 | 741,75 | 466,00 | 1.392,60 | 2.246,00 | 56.846,00 |

A regra vigente exclui o canal quando `total_messages < 500 OR distinct_human_authors < 5`, alem das exclusoes manuais. As duas contagens sao calculadas diretamente das mensagens originais. A selecao, a caracterizacao e a amostra foram versionadas novamente; resultados anteriores nao definem o quadro atual. Consulte `docs/methodology/CHANNEL_SELECTION_STAGE.md` para o protocolo.

Nao ha contagens por autor nos artefatos agregados; portanto este documento nao estima distribuicao individual de produtividade, participacao do autor dominante ou concentracao entre autores.

## 5. Cobertura e distribuicao temporal

### 5.1. Cobertura por canal

| Medida por canal | Min | Q25 | Mediana | Media | Q75 | Q90 | Q95 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Amplitude em dias calendario (inclusive) | 5,00 | 661,00 | 1.181,00 | 1.223,09 | 1.687,00 | 2.183,80 | 2.516,40 | 2.910,00 |
| Dias ativos (todos os registros) | 3,00 | 172,00 | 358,00 | 587,21 | 824,00 | 1.452,60 | 1.742,80 | 2.853,00 |
| Dias ativos (quadro utilizavel) | 2,00 | 171,00 | 357,00 | 582,48 | 819,00 | 1.452,00 | 1.742,80 | 2.783,00 |
| Mensagens utilizaveis por dia ativo | 1,00 | 9,65 | 19,55 | 48,87 | 39,37 | 107,45 | 208,86 | 883,91 |

Amplitude e diferenca entre as datas UTC extremas mais um dia; nao garante coleta continua. Mensagens por dia ativo divide o volume utilizavel pelos dias com ao menos uma mensagem utilizavel no canal. Nao e media por dia calendario nem intensidade corrigida pela disponibilidade do export.

### 5.2. Atividade por ano

| Ano UTC | Registros | % dos registros | Utilizaveis | % do quadro |
| --- | --- | --- | --- | --- |
| 2017 | 96.193 | 0,81% | 96.072 | 0,81% |
| 2018 | 228.618 | 1,92% | 227.141 | 1,91% |
| 2019 | 428.063 | 3,60% | 426.612 | 3,60% |
| 2020 | 1.863.111 | 15,66% | 1.859.839 | 15,68% |
| 2021 | 1.941.222 | 16,32% | 1.935.016 | 16,31% |
| 2022 | 1.675.116 | 14,08% | 1.670.634 | 14,08% |
| 2023 | 2.721.731 | 22,88% | 2.716.454 | 22,89% |
| 2024 | 2.900.446 | 24,38% | 2.889.846 | 24,36% |
| 2025 | 43.359 | 0,36% | 43.234 | 0,36% |

Anos e meses nas extremidades podem ser parciais. Contagens anuais nao sao taxas anualizadas; diferencas podem refletir cobertura do export, entrada/saida de canais ou mudancas reais de atividade.

### 5.3. Dez meses de maior volume utilizavel

| Mes UTC | Registros | Utilizaveis | % do quadro |
| --- | --- | --- | --- |
| 2024-01 | 374.176 | 373.650 | 3,15% |
| 2023-10 | 323.351 | 322.791 | 2,72% |
| 2020-12 | 318.966 | 318.566 | 2,68% |
| 2023-09 | 284.359 | 283.871 | 2,39% |
| 2023-04 | 259.300 | 258.954 | 2,18% |
| 2024-04 | 258.227 | 256.829 | 2,16% |
| 2021-01 | 250.880 | 250.501 | 2,11% |
| 2024-03 | 250.577 | 249.764 | 2,11% |
| 2024-02 | 248.251 | 247.690 | 2,09% |
| 2020-09 | 247.272 | 247.054 | 2,08% |

### 5.4. Atividade por dia da semana

| Periodo UTC | Registros | Utilizaveis | % do quadro |
| --- | --- | --- | --- |
| Segunda | 1.670.352 | 1.665.581 | 14,04% |
| Terca | 1.765.866 | 1.760.889 | 14,84% |
| Quarta | 1.793.665 | 1.788.514 | 15,07% |
| Quinta | 1.752.853 | 1.747.856 | 14,73% |
| Sexta | 1.737.405 | 1.732.721 | 14,60% |
| Sabado | 1.588.690 | 1.584.358 | 13,35% |
| Domingo | 1.589.028 | 1.584.929 | 13,36% |

### 5.5. Atividade por hora UTC

| Periodo UTC | Registros | Utilizaveis | % do quadro |
| --- | --- | --- | --- |
| 00:00 a 00:59 | 445.397 | 444.242 | 3,74% |
| 01:00 a 01:59 | 401.968 | 400.850 | 3,38% |
| 02:00 a 02:59 | 365.147 | 364.060 | 3,07% |
| 03:00 a 03:59 | 330.521 | 329.489 | 2,78% |
| 04:00 a 04:59 | 300.122 | 299.219 | 2,52% |
| 05:00 a 05:59 | 285.521 | 284.673 | 2,40% |
| 06:00 a 06:59 | 292.699 | 291.771 | 2,46% |
| 07:00 a 07:59 | 298.678 | 297.695 | 2,51% |
| 08:00 a 08:59 | 306.045 | 305.001 | 2,57% |
| 09:00 a 09:59 | 325.376 | 324.268 | 2,73% |
| 10:00 a 10:59 | 340.067 | 338.935 | 2,86% |
| 11:00 a 11:59 | 376.826 | 375.369 | 3,16% |
| 12:00 a 12:59 | 433.968 | 432.531 | 3,65% |
| 13:00 a 13:59 | 515.094 | 513.456 | 4,33% |
| 14:00 a 14:59 | 585.240 | 583.493 | 4,92% |
| 15:00 a 15:59 | 666.815 | 665.036 | 5,61% |
| 16:00 a 16:59 | 723.736 | 721.885 | 6,08% |
| 17:00 a 17:59 | 735.014 | 733.194 | 6,18% |
| 18:00 a 18:59 | 761.322 | 759.495 | 6,40% |
| 19:00 a 19:59 | 771.427 | 769.532 | 6,49% |
| 20:00 a 20:59 | 777.432 | 775.626 | 6,54% |
| 21:00 a 21:59 | 713.793 | 712.127 | 6,00% |
| 22:00 a 22:59 | 628.712 | 627.227 | 5,29% |
| 23:00 a 23:59 | 516.939 | 515.674 | 4,35% |

Dias da semana e horas agregam todos os periodos e canais. As participacoes nao sao corrigidas pelo numero de ocorrencias de cada dia no historico, nem pelo fuso local dos participantes. A rotina original exporta apenas buckets observados; dias da semana/horas ausentes sao preenchidos com zero nesta apresentacao, sem supor completude da coleta. Mensagens com timestamp ausente/invalido nao podem ser agrupadas temporalmente, mesmo se tiverem conteudo; as participacoes usam todo o volume como denominador.

## 6. Native replies, antecedentes e distancias

### 6.1. Frequencia e denominadores

| Medida | Contagem | Denominador | Proporcao |
| --- | --- | --- | --- |
| Native replies | 1.704.619 | Todos os registros | 14,33% |
| Native replies utilizaveis | 1.704.613 | Mensagens utilizaveis | 14,37% |
| Qualquer referencia nativa | 1.706.991 | Todos os registros | 14,35% |
| Reply sem ID do antecedente | 0 | Todos os registros | 0,00% |

Native reply exige tipo Discord 19 e ID de referencia nao vazio. Referencias de outros tipos nao sao incluidas como replies. Ausencia de reply nativo nao significa ausencia de resposta semantica.

### 6.2. Resolucao de antecedentes

| Populacao de replies | Status | Replies | Denominador | Proporcao |
| --- | --- | --- | --- | --- |
| Todas as origens ordenaveis | parent_not_found | 30.012 | 1.704.619 | 1,76% |
| Todas as origens ordenaveis | resolved | 1.674.607 | 1.704.619 | 98,24% |
| Origens utilizaveis | parent_not_found | 30.012 | 1.704.613 | 1,76% |
| Origens utilizaveis | resolved | 1.674.601 | 1.704.613 | 98,24% |

Replies com origem nao ordenavel, fora da tabela de distancias: 0.

`resolved`: antecedente identificado, unico, com timestamp valido e anterior no mesmo canal; `parent_not_found`: nao localizado na base ordenavel; `different_channel`: encontrado em outro canal; `not_preceding`: origem igual ao antecedente ou antecedente posterior na ordem. Nao encontrado nao demonstra exclusao: pode ser mensagem fora do export ou registro nao ordenavel.

### 6.3. Alcance posicional agregado

Todas as origens: 1.667.470 pares com origem e antecedente utilizaveis entre 1.674.607 replies resolvidos (99,57%).

Origens utilizaveis: 1.667.470 pares com origem e antecedente utilizaveis entre 1.674.601 replies resolvidos (99,57%).

| Populacao | Distancia ate (registros) | Replies cobertos | Replies resolvidos | Cobertura |
| --- | --- | --- | --- | --- |
| Todas as origens | 10 | 1.445.185 | 1.674.607 | 86,30% |
| Todas as origens | 100 | 1.654.714 | 1.674.607 | 98,81% |
| Todas as origens | 200 | 1.664.011 | 1.674.607 | 99,37% |
| Origens utilizaveis | 10 | 1.445.179 | 1.674.601 | 86,30% |
| Origens utilizaveis | 100 | 1.654.708 | 1.674.601 | 98,81% |
| Origens utilizaveis | 200 | 1.664.005 | 1.674.601 | 99,37% |

Estas proporcoes globais sao calculadas pela soma das contagens dos canais dividida pela soma dos replies resolvidos, nao pela media das proporcoes. A distancia e posicao da origem menos posicao do antecedente; 1 indica adjacencia. A ordem inclui todos os registros unicos e identificaveis com timestamp valido, incluindo bots e tipos de sistema. Ha uma ordem alternativa somente de mensagens utilizaveis para pares utilizaveis.

Cobertura ate 200 registros e um diagnostico de alcance dos native replies, nao garantia de contexto suficiente para arestas semanticas. A posicao da mensagem-alvo dentro da janela e a ordem usada na geracao de janelas tambem alteram o contexto disponivel.

### 6.4. Quantis por canal de maior volume

| Servidor | Canal | channel_id | Replies resolvidos utilizaveis | Mediana posicional | Q95 posicional | Mediana temporal (min) | Q95 temporal (h) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tech Haven | general | 593063949067485204 | 83.192 | 3,00 | 30,00 | 1,24 | 2,38 |
| Sapphire - Imagine a framework | off-topic | 737142209639350343 | 96.646 | 3,00 | 33,00 | 1,23 | 2,14 |
| Rectify11 Community | casual-chat | 1080264228247719977 | 149.189 | 3,00 | 32,00 | 0,66 | 1,04 |
| Cyberpunk 2077 Modding Community | general-chat | 789711087158820864 | 138.670 | 3,00 | 19,00 | 0,90 | 0,87 |
| Kindred Games Community | general-chat | 398282200287543297 | 11.596 | 3,00 | 25,00 | 4,78 | 6,61 |
| Cyberpunk 2077 Modding Community | game-chat | 727800569158434827 | 75.819 | 3,00 | 25,00 | 1,15 | 2,19 |
| MonoGame Discord | off-topic | 357384790158213120 | 60.063 | 3,00 | 30,00 | 1,46 | 2,87 |
| ImperialPlugins\.com | general | 284399832385191936 | 13.069 | 3,00 | 31,00 | 2,64 | 9,16 |
| Cyberpunk 2077 Modding Community | mod-dev-chat | 727800260486758410 | 42.528 | 3,00 | 33,00 | 2,74 | 4,93 |
| L'Ordre des Devs | discussion | 706642662937067580 | 52.536 | 3,00 | 21,00 | 0,72 | 1,01 |
| Shardeum | 💬・general | 933959587462254615 | 108.224 | 3,00 | 29,00 | 2,89 | 2,86 |
| MonoGame Discord | help | 402546044274999299 | 21.970 | 2,00 | 31,00 | 3,39 | 6,81 |
| MonoGame Discord | monogame-discussion | 355231098122272779 | 17.332 | 3,00 | 30,00 | 2,75 | 8,26 |
| Touhou Game Dev | touhou | 933089316547219558 | 34.958 | 5,00 | 41,00 | 1,40 | 3,41 |
| MonoGame Discord | programming | 402546188198608897 | 18.626 | 3,00 | 30,00 | 2,05 | 7,10 |
| Kindred Games Community | swords-n-magic-and-chat | 632274671370502145 | 17.435 | 3,00 | 28,00 | 4,39 | 7,00 |
| Return Community | 💬┇chat-here | 1136202840499572736 | 53.311 | 3,00 | 20,00 | 0,37 | 0,78 |
| Return Community | 🔨┇creations | 1124314155990667396 | 55.703 | 2,00 | 30,00 | 0,71 | 3,26 |
| Touhou Game Dev | general | 933089314965970991 | 20.662 | 4,00 | 37,00 | 1,27 | 3,96 |
| OpenVic - Community | 💬general | 1062021872545447936 | 31.870 | 3,00 | 30,00 | 1,30 | 4,40 |

Quantis sao calculados sobre replies de origem utilizavel resolvidos no respectivo canal. O antecedente pode nao ser utilizavel. Minutos e horas sao conversoes de segundos por divisao por 60 e 3.600. O CSV original preserva Q25, Q50, Q75, Q90, Q95 e Q99, inclusive na ordem alternativa utilizavel. Nao e possivel recuperar quantis globais exatos apenas desses quantis por canal; este documento nao os inventa nem calcula medias de quantis.

## 7. Bots, campos ausentes e registros nao utilizaveis

| Flag | Registros | % de todos os registros |
| --- | --- | --- |
| Bots registrados | 0 | 0,00% |
| Status de bot ausente | 0 | 0,00% |
| ID da mensagem ausente | 0 | 0,00% |
| ID do autor ausente | 0 | 0,00% |
| Servidor/canal ausente | 0 | 0,00% |
| Timestamp ausente/invalido | 0 | 0,00% |
| Registros com chave duplicada | 0 | 0,00% |
| Texto vazio ou ausente | 317.588 | 2,67% |
| Mensagens humanas com conteudo e problemas estruturais | 0 | 0,00% |
| Tipo diferente de 0/19 ou ausente (nao implica nao utilizabilidade) | 35.709 | 0,30% |
| Nao utilizaveis: sem texto nem midia registrada | 33.011 | 0,28% |

As flags sao descritivas, podem se sobrepor e nao devem ser somadas. Somente a ausencia simultanea de texto e midia define nao utilizabilidade. Tipos diferentes de 0/19, bots e problemas estruturais nao sao incluidos nessa contagem pelo simples fato de apresentarem essas caracteristicas. Texto vazio sozinho nao torna uma mensagem inutilizavel quando ha anexo, embed ou sticker. Nao se presume que a disponibilidade de midia significa que seu conteudo foi baixado ou sera visivel ao anotador.

Uma proporcao zero de bots descreve apenas a entrada analisada, que pode ter passado por exclusao previa de bots. Nao demonstra que os servidores nao possuem bots. Mensagens completamente ausentes do export nao podem ser contadas sem fonte externa; antecedentes nao localizados e campos ausentes sao indicadores diferentes dessa perda desconhecida.

## 8. Implicacoes para a construcao de janelas

A concentracao deve ser avaliada sobre `usable_human` ao planejar mensagens-alvo. A amostragem proporcional ao volume favorece canais grandes. Isso e coerente para estimar uma media entre mensagens, mas pode deixar poucos exemplos dos canais pequenos para comparacoes entre canais. Uma media entre canais e uma media entre mensagens sao estimandos distintos.

Uma alternativa a avaliar e estabelecer cobertura minima por canal e distribuir o restante proporcionalmente ao volume. As probabilidades de inclusao e os pesos precisam ser registrados quando o desenho for definido. Esta caracterizacao nao determina tamanho amostral, nao estima efeito de desenho e nao sorteia janelas.

Estratificar temporalmente dentro de cada canal evita selecionar apenas inicio/fim do historico ou meses de maior atividade. O volume global por ano nao deve substituir a avaliacao do periodo disponivel de cada canal. Periodos sem registros nao provam inatividade nem falha de coleta.

O piloto deve confrontar alcance posicional dos native replies com antecedentes semanticos anotados, registrar casos fora do contexto e verificar mensagens de midia. Nao interpretar ausencia de reply nativo como rotulo negativo, nem quantidade de participantes como medida completa de sociabilidade.

## 9. Inventario completo dos canais

Uma linha por par `(guild_id, channel_id)`, ordenada pelo volume utilizavel. Autores H sao distintos humanos; autores U sao distintos com mensagens utilizaveis. Replies % divide native replies utilizaveis por mensagens utilizaveis do canal. Flags detalhadas e quantis adicionais permanecem nos CSVs.

| Servidor | guild_id | Canal | channel_id | Registros | Utilizaveis | % do quadro | Autores H | Autores U | Replies % | Dias ativos U | Primeiro UTC | Ultimo UTC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tech Haven | 455345206481518593 | general | 593063949067485204 | 790.223 | 790.141 | 6,66% | 2.734 | 2.734 | 10,81% | 2.007 | 2019-06-25 13:15:53.231+00 | 2024-12-21 22:43:13.07+00 |
| Sapphire - Imagine a framework | 737141877803057244 | off-topic | 737142209639350343 | 677.544 | 675.805 | 5,70% | 1.740 | 914 | 14,45% | 1.620 | 2020-07-27 23:21:51.218+00 | 2025-01-01 19:33:32.725+00 |
| Rectify11 Community | 1077324213142175744 | casual-chat | 1080264228247719977 | 584.378 | 584.267 | 4,92% | 1.352 | 1.352 | 25,91% | 661 | 2023-02-28 23:11:31.147+00 | 2024-12-19 04:19:39.637+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | general-chat | 789711087158820864 | 569.915 | 569.877 | 4,80% | 11.967 | 11.967 | 24,76% | 1.458 | 2020-12-19 04:30:10.299+00 | 2025-01-07 00:36:38.602+00 |
| Kindred Games Community | 398282199788552193 | general-chat | 398282200287543297 | 548.515 | 547.581 | 4,62% | 3.073 | 2.616 | 2,13% | 2.497 | 2018-01-04 04:18:51.301+00 | 2025-01-06 19:27:35.474+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | game-chat | 727800569158434827 | 496.477 | 496.443 | 4,18% | 8.836 | 8.836 | 15,60% | 1.488 | 2020-12-09 07:17:00.54+00 | 2025-01-06 22:41:06.838+00 |
| MonoGame Discord | 355231098122272778 | off-topic | 357384790158213120 | 478.631 | 478.591 | 4,03% | 800 | 800 | 13,11% | 2.379 | 2018-01-11 16:34:39.926+00 | 2024-12-25 01:28:11.539+00 |
| ImperialPlugins\.com | 284399832385191936 | general | 284399832385191936 | 373.307 | 364.467 | 3,07% | 5.792 | 2.217 | 3,63% | 2.783 | 2017-02-23 19:18:59.741+00 | 2025-01-06 23:25:10.929+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | mod-dev-chat | 727800260486758410 | 290.922 | 290.874 | 2,45% | 6.528 | 6.528 | 14,84% | 1.464 | 2020-12-10 08:19:11.786+00 | 2025-01-06 23:17:55.481+00 |
| L'Ordre des Devs | 706640777450881114 | discussion | 706642662937067580 | 286.996 | 284.011 | 2,39% | 2.532 | 1.783 | 19,23% | 1.066 | 2020-05-04 21:52:31.273+00 | 2025-01-04 22:47:11.578+00 |
| Shardeum | 933959587462254612 | 💬・general | 933959587462254615 | 278.951 | 278.422 | 2,35% | 57.005 | 56.846 | 39,85% | 1.074 | 2022-01-21 05:46:57.828+00 | 2025-01-08 16:27:40.895+00 |
| MonoGame Discord | 355231098122272778 | help | 402546044274999299 | 276.231 | 276.211 | 2,33% | 2.499 | 2.499 | 8,08% | 2.421 | 2018-01-20 20:39:37.883+00 | 2024-12-24 22:43:41.149+00 |
| MonoGame Discord | 355231098122272778 | monogame-discussion | 355231098122272779 | 251.367 | 251.205 | 2,12% | 1.785 | 1.725 | 7,04% | 2.477 | 2017-09-07 08:39:49.32+00 | 2024-12-24 13:45:01.848+00 |
| Touhou Game Dev | 933089313405685760 | touhou | 933089316547219558 | 244.413 | 244.327 | 2,06% | 313 | 313 | 14,34% | 1.081 | 2022-01-18 20:31:53.073+00 | 2025-01-07 08:50:23.073+00 |
| MonoGame Discord | 355231098122272778 | programming | 402546188198608897 | 224.847 | 224.841 | 1,90% | 1.246 | 1.246 | 8,35% | 2.076 | 2018-02-06 20:05:46.427+00 | 2024-12-24 21:39:01.262+00 |
| Kindred Games Community | 398282199788552193 | swords-n-magic-and-chat | 632274671370502145 | 220.277 | 220.230 | 1,86% | 2.660 | 2.660 | 7,95% | 1.818 | 2019-10-11 17:55:12.368+00 | 2025-01-06 19:56:45.864+00 |
| Return Community | 1080829289412432032 | 💬┇chat-here | 1136202840499572736 | 215.720 | 215.679 | 1,82% | 2.363 | 2.362 | 25,52% | 352 | 2024-01-07 02:23:26.117+00 | 2024-12-28 16:04:20.632+00 |
| Return Community | 1080829289412432032 | 🔨┇creations | 1124314155990667396 | 167.772 | 167.746 | 1,41% | 1.152 | 1.151 | 34,06% | 527 | 2023-06-30 13:40:10.092+00 | 2024-12-28 16:32:13.812+00 |
| Touhou Game Dev | 933089313405685760 | general | 933089314965970991 | 150.807 | 150.740 | 1,27% | 484 | 484 | 13,74% | 1.040 | 2022-01-18 20:27:23.069+00 | 2025-01-07 05:43:00.511+00 |
| OpenVic - Community | 1062018115275325480 | 💬general | 1062021872545447936 | 140.849 | 140.820 | 1,19% | 1.282 | 1.282 | 22,75% | 733 | 2023-01-09 17:01:43.292+00 | 2025-01-11 03:59:51.909+00 |
| ImperialPlugins\.com | 284399832385191936 | dev | 663524633563103233 | 138.319 | 138.295 | 1,17% | 550 | 550 | 11,62% | 1.689 | 2020-01-07 17:47:23.354+00 | 2025-01-07 03:04:56.565+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | spoilers-chat | 790730432437157898 | 129.041 | 129.032 | 1,09% | 1.690 | 1.689 | 13,36% | 1.186 | 2020-12-22 00:00:36.352+00 | 2025-01-06 23:30:02.931+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | textures-and-models | 786891742829215745 | 122.357 | 122.314 | 1,03% | 1.733 | 1.733 | 14,94% | 1.340 | 2020-12-11 14:04:21.465+00 | 2025-01-06 21:39:29.296+00 |
| Docker | 460871933748183040 | docker | 460871933748183042 | 120.796 | 120.651 | 1,02% | 4.682 | 4.638 | 19,19% | 2.248 | 2018-06-25 18:25:07.59+00 | 2025-01-08 23:28:32.017+00 |
| Kindred Games Community | 398282199788552193 | spoiler-chat | 753173823406342175 | 118.870 | 118.846 | 1,00% | 1.377 | 1.377 | 8,55% | 1.263 | 2020-09-09 08:43:59.646+00 | 2025-01-06 05:53:46.117+00 |
| ImperialPlugins\.com | 284399832385191936 | unturned-support | 284402775071260672 | 117.993 | 117.974 | 0,99% | 1.104 | 1.104 | 4,09% | 2.596 | 2017-02-24 20:01:07.892+00 | 2025-01-03 16:56:30.419+00 |
| OpenRCT2 | 264137540670324737 | openrct2-talk | 691736850980667514 | 117.247 | 117.231 | 0,99% | 2.012 | 2.012 | 12,25% | 1.726 | 2020-03-28 11:08:42.427+00 | 2025-01-11 03:21:37.202+00 |
| Touhou Game Dev | 933089313405685760 | jam-discussion | 933089316035506242 | 107.434 | 107.393 | 0,91% | 399 | 399 | 13,55% | 712 | 2022-01-18 21:32:24.75+00 | 2025-01-07 04:17:34.159+00 |
| Terasology | 270264625419911192 | terasology | 270264625419911192 | 104.219 | 104.206 | 0,88% | 616 | 616 | 1,74% | 1.766 | 2017-01-15 18:56:22.736+00 | 2025-01-02 12:56:42.273+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | cet-troubleshooting | 795037292955172895 | 97.244 | 97.197 | 0,82% | 9.256 | 9.256 | 17,15% | 1.455 | 2021-01-02 21:24:01.967+00 | 2025-01-07 01:39:22.282+00 |
| Andy’s Development | 857672921912836116 | general-support | 857802803229360138 | 92.500 | 92.446 | 0,78% | 3.694 | 3.694 | 20,27% | 1.262 | 2021-06-25 02:03:15.941+00 | 2025-01-12 20:41:07.048+00 |
| Sapphire - Imagine a framework | 737141877803057244 | old-coding-den | 737142325217722478 | 91.209 | 91.199 | 0,77% | 320 | 320 | 11,71% | 819 | 2020-07-27 23:21:46.246+00 | 2022-12-12 17:39:02.389+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | wolvenkit-dev | 717720094196760760 | 89.091 | 88.916 | 0,75% | 123 | 123 | 11,20% | 1.217 | 2020-12-11 09:16:18.748+00 | 2025-01-06 17:50:31.549+00 |
| Docker | 460871933748183040 | docker-compose | 581537102244610058 | 80.347 | 80.347 | 0,68% | 2.503 | 2.503 | 20,87% | 1.716 | 2019-05-24 17:42:34.228+00 | 2025-01-09 01:41:02.39+00 |
| Touhou Game Dev | 933089313405685760 | gaming | 933089316547219559 | 79.913 | 79.901 | 0,67% | 211 | 211 | 10,83% | 1.032 | 2022-01-18 20:41:55.541+00 | 2025-01-07 07:30:30.194+00 |
| Kavita | 821879810934439936 | support | 840693141082341406 | 74.929 | 74.927 | 0,63% | 1.626 | 1.626 | 12,25% | 1.219 | 2021-05-11 19:53:48.073+00 | 2024-12-22 03:55:00.556+00 |
| Sapphire - Imagine a framework | 737141877803057244 | old-sapphire-support | 737142503043498015 | 73.479 | 73.468 | 0,62% | 684 | 684 | 14,42% | 716 | 2020-07-27 23:22:45.027+00 | 2022-11-28 17:09:17.44+00 |
| ImperialPlugins\.com | 284399832385191936 | unturned-help | 572969584127377419 | 73.423 | 73.414 | 0,62% | 1.629 | 1.629 | 8,60% | 1.904 | 2019-05-01 02:27:53.944+00 | 2025-01-07 02:54:48.516+00 |
| Kindred Games Community | 398282199788552193 | off-topic-n-stuff | 400191665119428608 | 71.944 | 71.941 | 0,61% | 740 | 740 | 1,82% | 1.737 | 2018-01-23 08:36:04.435+00 | 2025-01-04 18:13:57.977+00 |
| Kindred Games Community | 398282199788552193 | showcase | 399153251141812235 | 68.619 | 68.618 | 0,58% | 885 | 885 | 2,77% | 2.012 | 2018-01-06 10:56:42.089+00 | 2025-01-06 01:57:18.909+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | wolvenkit-support | 808086068023918603 | 60.503 | 60.450 | 0,51% | 1.806 | 1.806 | 18,33% | 1.245 | 2021-02-07 21:52:39.981+00 | 2025-01-07 01:07:28.833+00 |
| 💻 Ouckah Lair | 519640186167099402 | ╮general | 1092864102440906803 | 58.913 | 58.900 | 0,50% | 758 | 758 | 21,63% | 620 | 2023-04-08 19:41:28.033+00 | 2025-01-09 02:45:44.216+00 |
| TheScostumati | 516564332440584221 | 🙊vocal-chat | 765144707696689152 | 54.841 | 54.828 | 0,46% | 194 | 194 | 5,13% | 1.334 | 2020-10-12 09:33:42.827+00 | 2025-01-08 13:31:52.815+00 |
| Kindred Games Community | 398282199788552193 | game-dev-chat | 447512313378111509 | 52.335 | 52.329 | 0,44% | 803 | 803 | 3,97% | 1.663 | 2018-05-19 21:35:33.456+00 | 2025-01-06 19:38:50.09+00 |
| Touhou Game Dev | 933089313405685760 | voice-text | 933089316547219563 | 47.573 | 47.540 | 0,40% | 159 | 159 | 6,15% | 345 | 2022-04-18 15:43:58.837+00 | 2025-01-06 07:41:15.574+00 |
| OpenRCT2 | 264137540670324737 | development | 691735032531779684 | 46.938 | 46.916 | 0,40% | 679 | 666 | 9,50% | 1.450 | 2020-03-24 21:48:02.745+00 | 2025-01-10 03:41:48.977+00 |
| Kindred Games Community | 398282199788552193 | gaming | 508238138209075201 | 45.918 | 45.906 | 0,39% | 451 | 451 | 2,18% | 1.312 | 2018-11-03 11:17:32.801+00 | 2025-01-04 15:33:59.644+00 |
| Touhou Game Dev | 933089313405685760 | jam-games-discussion | 933089316035506243 | 45.458 | 45.446 | 0,38% | 274 | 274 | 12,79% | 424 | 2022-01-19 01:27:40.958+00 | 2025-01-04 21:13:42.707+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | lore-talk | 889600112492437594 | 45.223 | 45.209 | 0,38% | 887 | 887 | 14,17% | 924 | 2021-09-20 19:53:35.606+00 | 2025-01-07 00:07:53.058+00 |
| Kindred Games Community | 398282199788552193 | ideas | 398288504066670602 | 44.169 | 44.165 | 0,37% | 1.211 | 1.211 | 7,43% | 1.446 | 2018-01-04 01:50:57.564+00 | 2024-12-26 00:08:42.144+00 |
| ImperialPlugins\.com | 284399832385191936 | memes | 407952543835226137 | 43.828 | 43.809 | 0,37% | 398 | 397 | 2,72% | 1.706 | 2018-01-30 17:38:58.509+00 | 2025-01-04 11:43:51.215+00 |
| Rectify11 Community | 1077324213142175744 | rectify11-chat | 1077324214555656194 | 41.921 | 41.907 | 0,35% | 1.439 | 1.439 | 26,26% | 652 | 2023-02-28 23:54:16.225+00 | 2024-12-19 02:52:02.045+00 |
| WWebJS | 698610475432411196 | general | 698610475931271249 | 43.898 | 41.599 | 0,35% | 4.444 | 2.970 | 30,99% | 1.601 | 2020-04-11 19:36:54.376+00 | 2025-01-08 18:28:58.621+00 |
| Kavita | 821879810934439936 | lounge | 842537562363134003 | 41.323 | 41.321 | 0,35% | 237 | 237 | 7,36% | 824 | 2021-05-13 23:29:57.147+00 | 2024-12-22 03:21:02.652+00 |
| Docker | 460871933748183040 | discussion | 669474776393187328 | 41.318 | 41.318 | 0,35% | 2.105 | 2.105 | 22,52% | 1.505 | 2020-01-22 09:40:17.654+00 | 2025-01-08 22:11:01.096+00 |
| Kavita | 821879810934439936 | general | 821879810934439939 | 40.817 | 40.432 | 0,34% | 1.114 | 919 | 9,52% | 1.136 | 2021-03-20 16:22:40.316+00 | 2024-12-18 15:31:28.853+00 |
| OpenRCT2 | 264137540670324737 | open-graphics | 691752238057783356 | 38.362 | 38.355 | 0,32% | 308 | 308 | 13,25% | 859 | 2020-03-26 12:32:54.082+00 | 2025-01-10 18:42:04.229+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | cet-lua-scripting | 795037494106128434 | 38.166 | 38.139 | 0,32% | 886 | 886 | 16,07% | 1.238 | 2021-01-02 21:22:09.313+00 | 2025-01-07 00:30:00.977+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | redscript-scripting | 804399334246187038 | 36.015 | 35.992 | 0,30% | 566 | 566 | 18,70% | 1.007 | 2021-01-28 17:17:45.421+00 | 2025-01-06 22:45:26.096+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | archived-cet-scripting | 794613856948322344 | 34.663 | 34.652 | 0,29% | 127 | 127 | 6,01% | 347 | 2021-01-01 17:14:52.845+00 | 2023-08-28 10:44:50.706+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | texture-modding | 717721370519142573 | 32.463 | 32.430 | 0,27% | 711 | 711 | 8,79% | 418 | 2020-12-10 03:12:40.693+00 | 2022-06-20 07:33:34.612+00 |
| WWebJS | 698610475432411196 | help-archive | 698612530985173002 | 32.234 | 32.232 | 0,27% | 1.106 | 1.106 | 24,48% | 862 | 2020-04-12 05:29:10.868+00 | 2022-09-25 21:49:26.929+00 |
| OpenVic - Community | 1062018115275325480 | 📚history | 1084770470685052938 | 31.930 | 31.929 | 0,27% | 204 | 204 | 19,06% | 344 | 2023-03-13 09:35:35.264+00 | 2025-01-09 04:21:46.102+00 |
| Kindred Games Community | 398282199788552193 | bots | 632280302781464595 | 31.780 | 31.776 | 0,27% | 1.363 | 1.363 | 0,22% | 1.187 | 2019-10-11 18:16:50.39+00 | 2024-12-18 04:56:27.955+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | animations | 813768799358156880 | 31.623 | 31.583 | 0,27% | 342 | 342 | 17,78% | 841 | 2021-02-23 13:46:51.326+00 | 2025-01-05 15:58:44.335+00 |
| Tech Haven | 455345206481518593 | political | 736661899936137246 | 29.292 | 29.291 | 0,25% | 141 | 141 | 10,98% | 1.145 | 2020-07-25 19:13:54.076+00 | 2024-12-18 03:28:05.391+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | cyanidex-mods | 1198976262765564018 | 28.161 | 28.151 | 0,24% | 310 | 310 | 17,13% | 333 | 2024-01-22 18:54:34.309+00 | 2025-01-07 02:00:21.446+00 |
| OpenVic - Community | 1062018115275325480 | 🤣memes | 1062140718791004301 | 28.013 | 28.009 | 0,24% | 685 | 685 | 28,64% | 734 | 2023-01-09 22:48:53.44+00 | 2025-01-11 04:53:01.239+00 |
| MonoGame Discord | 355231098122272778 | showcase-discussion | 502292592789028874 | 27.908 | 27.908 | 0,24% | 304 | 304 | 3,32% | 769 | 2018-10-18 01:46:56.357+00 | 2022-01-04 18:31:02.938+00 |
| OpenRCT2 | 264137540670324737 | off-topic | 736534008296505344 | 27.600 | 27.599 | 0,23% | 604 | 604 | 9,25% | 1.253 | 2020-07-25 10:44:13.635+00 | 2025-01-11 05:05:01.437+00 |
| TheScostumati | 516564332440584221 | 💥game-news | 537315904908820490 | 27.302 | 27.296 | 0,23% | 146 | 146 | 4,83% | 1.480 | 2019-01-22 17:25:06.815+00 | 2025-01-08 20:16:27.496+00 |
| Touhou Game Dev | 933089313405685760 | dev-touhou | 933089315297312880 | 26.985 | 26.972 | 0,23% | 236 | 235 | 11,33% | 799 | 2022-01-18 20:55:40.001+00 | 2025-01-07 02:58:58.35+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | save-editing | 789565732726767636 | 26.491 | 26.459 | 0,22% | 1.613 | 1.613 | 13,20% | 713 | 2020-12-18 19:03:37.414+00 | 2025-01-06 23:02:51.396+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | red4ext-support | 1015378649547026462 | 25.557 | 25.552 | 0,22% | 2.634 | 2.633 | 21,69% | 670 | 2022-09-02 21:52:20.349+00 | 2025-01-07 00:39:20.175+00 |
| ImperialPlugins\.com | 284399832385191936 | waywo | 636284605166649344 | 25.419 | 25.414 | 0,21% | 226 | 226 | 9,32% | 966 | 2019-10-22 19:39:20.354+00 | 2025-01-06 20:44:31.375+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | redscript-support | 867329707787550751 | 25.137 | 25.132 | 0,21% | 2.093 | 2.092 | 19,76% | 945 | 2021-07-21 12:25:29.479+00 | 2025-01-06 22:46:45.202+00 |
| OpenRCT2 | 264137540670324737 | help | 875468371884380210 | 24.889 | 24.885 | 0,21% | 1.375 | 1.375 | 13,26% | 1.122 | 2021-08-12 20:01:17.844+00 | 2025-01-11 02:11:41.489+00 |
| Terasology | 270264625419911192 | destination-sol | 389093174921920512 | 24.810 | 24.798 | 0,21% | 152 | 152 | 4,17% | 971 | 2017-12-09 16:37:27.547+00 | 2025-01-07 01:21:44.571+00 |
| Tech Haven | 455345206481518593 | general-it-chat | 594961464603705365 | 23.752 | 23.752 | 0,20% | 803 | 803 | 8,30% | 1.089 | 2019-07-02 03:21:56.513+00 | 2024-12-10 19:57:30.971+00 |
| Kindred Games Community | 398282199788552193 | game-jams | 508238341058199562 | 23.447 | 23.423 | 0,20% | 544 | 544 | 4,09% | 595 | 2018-11-03 11:18:52.12+00 | 2025-01-05 00:36:44.039+00 |
| Tech Haven | 455345206481518593 | memes | 589611193665191936 | 21.943 | 21.943 | 0,18% | 298 | 298 | 12,88% | 1.870 | 2019-06-16 00:36:16.581+00 | 2024-12-21 23:42:36.655+00 |
| Touhou Game Dev | 933089313405685760 | art | 933089315737731114 | 20.766 | 20.727 | 0,17% | 317 | 317 | 12,99% | 1.067 | 2022-01-18 20:50:30.034+00 | 2025-01-07 05:21:32.236+00 |
| Sapphire - Imagine a framework | 737141877803057244 | old-gaming-den | 878754511483723826 | 20.329 | 20.328 | 0,17% | 67 | 67 | 12,05% | 440 | 2021-08-21 21:39:14.039+00 | 2022-12-05 17:21:16.826+00 |
| Kindred Games Community | 398282199788552193 | food | 564536484942708736 | 19.993 | 19.993 | 0,17% | 331 | 331 | 2,53% | 881 | 2019-04-07 19:54:48.135+00 | 2025-01-06 14:42:39.172+00 |
| Rectify11 Community | 1077324213142175744 | desktops-and-setups | 1077324214555656199 | 19.928 | 19.928 | 0,17% | 637 | 637 | 32,03% | 639 | 2023-03-01 00:28:38.896+00 | 2024-12-19 00:34:55.798+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | audio | 789391457282031616 | 19.487 | 19.450 | 0,16% | 741 | 740 | 14,48% | 846 | 2020-12-18 07:23:14.979+00 | 2025-01-06 19:12:07.653+00 |
| MonoGame Discord | 355231098122272778 | libraries-discussion | 424621790363648021 | 18.590 | 18.588 | 0,16% | 487 | 487 | 10,93% | 976 | 2018-03-17 17:36:04.025+00 | 2024-12-24 11:54:27.319+00 |
| Kavita | 821879810934439936 | nightly-testing | 851515194185744464 | 18.475 | 18.473 | 0,16% | 123 | 123 | 6,93% | 720 | 2021-09-08 19:19:19.596+00 | 2024-12-17 14:03:03.701+00 |
| OpenRCT2 | 264137540670324737 | plugin | 696130778618396683 | 18.107 | 18.105 | 0,15% | 325 | 325 | 11,16% | 926 | 2020-04-16 00:59:52.096+00 | 2025-01-10 20:11:00.829+00 |
| Kindred Games Community | 398282199788552193 | fan-content | 650215395890036746 | 17.904 | 17.889 | 0,15% | 429 | 429 | 3,29% | 607 | 2019-11-30 06:04:38.206+00 | 2024-11-15 18:28:57.503+00 |
| Tech Haven | 455345206481518593 | nsfw | 638477563324268553 | 17.417 | 17.416 | 0,15% | 174 | 174 | 15,42% | 1.338 | 2019-10-30 01:15:47.994+00 | 2024-12-19 02:10:51.901+00 |
| OpenRCT2 | 264137540670324737 | additional-content | 992015068197814272 | 17.241 | 17.238 | 0,15% | 196 | 196 | 23,65% | 335 | 2022-06-30 10:36:35.034+00 | 2025-01-11 03:48:15.104+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | quests-and-scenes | 803201431657250857 | 17.102 | 17.024 | 0,14% | 213 | 213 | 15,32% | 503 | 2021-01-25 09:57:53.899+00 | 2025-01-07 01:48:16.636+00 |
| Docker | 460871933748183040 | reverse-proxy | 478468481386545171 | 16.998 | 16.997 | 0,14% | 466 | 466 | 16,61% | 786 | 2018-10-04 13:13:31.95+00 | 2025-01-08 23:51:18.67+00 |
| Docker | 460871933748183040 | kubernetes | 478470860806815745 | 16.805 | 16.805 | 0,14% | 607 | 607 | 24,33% | 939 | 2018-08-29 22:27:58.915+00 | 2025-01-09 00:18:49.45+00 |
| Sapphire - Imagine a framework | 737141877803057244 | framework-development | 737142774738190377 | 16.655 | 16.652 | 0,14% | 184 | 184 | 6,40% | 530 | 2020-07-27 23:22:36.998+00 | 2024-12-29 15:37:33.364+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | tweakdb-modding | 953004282142163014 | 16.316 | 16.310 | 0,14% | 423 | 423 | 15,54% | 546 | 2022-03-14 18:59:37.163+00 | 2025-01-06 03:32:29.94+00 |
| GameDevSG | 558680594498977792 | ♦👥main-hangout-chat♦ | 558680594498977795 | 16.416 | 16.172 | 0,14% | 716 | 556 | 6,17% | 996 | 2019-04-07 07:29:16.051+00 | 2024-12-19 05:09:12.633+00 |
| Touhou Game Dev | 933089313405685760 | jam-wip-sharing | 933089316035506245 | 16.051 | 16.023 | 0,14% | 249 | 249 | 11,98% | 234 | 2022-04-14 19:46:02.218+00 | 2024-11-05 11:19:42.6+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | blender-add-on | 1033120509216444550 | 15.863 | 15.847 | 0,13% | 350 | 350 | 18,99% | 519 | 2022-10-21 20:52:44.895+00 | 2025-01-06 21:36:38.796+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | red4ext-cpp | 839400251680227339 | 15.807 | 15.800 | 0,13% | 137 | 137 | 13,84% | 557 | 2021-05-05 12:52:09.223+00 | 2025-01-07 00:50:52.137+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | world-editing | 814064062815141909 | 15.637 | 15.599 | 0,13% | 197 | 197 | 21,77% | 431 | 2021-02-24 09:22:00.59+00 | 2025-01-07 00:10:38.193+00 |
| Terasology | 270264625419911192 | off-topic | 503491338465968138 | 15.132 | 15.131 | 0,13% | 182 | 182 | 4,35% | 1.155 | 2018-10-26 14:24:31.654+00 | 2025-01-01 05:26:12.786+00 |
| Touhou Game Dev | 933089313405685760 | technology | 933089316547219560 | 15.035 | 15.032 | 0,13% | 117 | 117 | 10,26% | 621 | 2022-01-18 20:34:31.428+00 | 2025-01-07 04:50:11.07+00 |
| Docker | 460871933748183040 | docker-desktop | 502736293810274305 | 15.000 | 15.000 | 0,13% | 927 | 927 | 22,71% | 965 | 2018-10-19 07:33:53.19+00 | 2025-01-09 02:15:34.443+00 |
| MonoGame Discord | 355231098122272778 | showcase | 402545804776046592 | 14.170 | 14.169 | 0,12% | 678 | 678 | 0,18% | 2.035 | 2018-01-26 05:29:52.946+00 | 2024-12-25 02:35:41.416+00 |
| Touhou Game Dev | 933089313405685760 | general-advice | 933089315737731118 | 14.071 | 14.068 | 0,12% | 149 | 149 | 11,36% | 352 | 2022-01-18 20:56:52.962+00 | 2025-01-07 03:52:03.354+00 |
| Sapphire - Imagine a framework | 737141877803057244 | old-technology-den | 914235414041202758 | 13.970 | 13.970 | 0,12% | 59 | 59 | 13,55% | 288 | 2021-11-27 19:25:17.633+00 | 2022-12-05 17:41:29.865+00 |
| Kindred Games Community | 398282199788552193 | bug-support | 941584884403675177 | 13.908 | 13.904 | 0,12% | 570 | 570 | 20,49% | 623 | 2022-02-11 06:47:49.866+00 | 2025-01-06 13:36:25.704+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | vortex-extension-support | 946698855976681473 | 13.748 | 13.733 | 0,12% | 849 | 849 | 19,29% | 748 | 2022-02-25 09:58:33.433+00 | 2025-01-07 01:28:16.126+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | pc-tech-talk | 1244690869756498020 | 13.603 | 13.597 | 0,11% | 330 | 330 | 19,73% | 177 | 2024-05-27 16:40:07.608+00 | 2025-01-07 02:22:06.002+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | psiberstuff | 1171003964200853594 | 13.311 | 13.305 | 0,11% | 88 | 88 | 21,06% | 327 | 2023-11-06 08:50:59.919+00 | 2025-01-07 01:52:10.94+00 |
| Touhou Game Dev | 933089313405685760 | unity | 933089315737731119 | 13.301 | 13.295 | 0,11% | 104 | 104 | 10,77% | 460 | 2022-01-18 20:49:37.066+00 | 2025-01-06 21:33:00.429+00 |
| Sapphire - Imagine a framework | 737141877803057244 | utilities-development | 759750007087431721 | 13.177 | 13.175 | 0,11% | 100 | 100 | 8,02% | 444 | 2020-09-27 12:15:20.297+00 | 2024-12-18 15:06:44.864+00 |
| TheScostumati | 516564332440584221 | 🍕master-chef | 712650717789421648 | 12.504 | 12.495 | 0,11% | 124 | 124 | 9,10% | 853 | 2020-05-20 13:02:21.631+00 | 2025-01-02 00:56:38.376+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | scripting | 717721316186390528 | 12.388 | 12.382 | 0,10% | 110 | 110 | 3,21% | 45 | 2020-12-10 11:09:03.292+00 | 2021-04-15 14:17:45.941+00 |
| Terasology | 270264625419911192 | logistics | 633681387995660303 | 11.637 | 11.625 | 0,10% | 39 | 39 | 6,34% | 675 | 2019-10-15 15:44:07.905+00 | 2024-12-30 04:51:37.942+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | archive-xl | 955663052903178270 | 11.631 | 11.610 | 0,10% | 369 | 369 | 17,63% | 514 | 2022-03-22 03:04:31.506+00 | 2025-01-06 21:54:48.276+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | mod-troubleshooting | 788213273530335233 | 11.376 | 11.373 | 0,10% | 754 | 754 | 34,41% | 16 | 2024-12-23 17:20:15.492+00 | 2025-01-07 00:44:18.578+00 |
| Terasology | 270264625419911192 | stabilization | 696830442065625118 | 11.297 | 11.273 | 0,10% | 38 | 38 | 7,94% | 482 | 2020-04-06 21:23:03.511+00 | 2024-11-17 15:32:29.291+00 |
| Tech Haven | 455345206481518593 | linux_unix-chat | 719555554321629186 | 11.243 | 11.243 | 0,09% | 358 | 358 | 10,26% | 612 | 2020-06-08 14:20:38.575+00 | 2024-10-19 09:20:40.87+00 |
| Touhou Game Dev | 933089313405685760 | dev-other | 933089315297312881 | 10.739 | 10.739 | 0,09% | 150 | 150 | 9,34% | 560 | 2022-01-18 21:10:55.327+00 | 2025-01-06 19:30:16.616+00 |
| Penusbmic's Server | 894976658229063731 | general-chat | 1132134739856334898 | 10.507 | 10.502 | 0,09% | 375 | 375 | 22,86% | 451 | 2023-07-22 02:19:51.736+00 | 2025-01-05 19:13:55.485+00 |
| Sapphire - Imagine a framework | 737141877803057244 | mature-chat | 792132881903386664 | 10.453 | 10.451 | 0,09% | 123 | 123 | 17,37% | 662 | 2020-12-25 20:53:20.79+00 | 2024-12-20 11:24:05.289+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | reverse-engineering | 786134713227935785 | 10.365 | 10.353 | 0,09% | 96 | 96 | 3,72% | 96 | 2020-12-09 07:39:37.632+00 | 2023-02-25 15:41:33.093+00 |
| Tech Haven | 455345206481518593 | programming-chat | 594961505380991039 | 9.984 | 9.984 | 0,08% | 406 | 406 | 7,98% | 717 | 2019-08-01 02:41:15.661+00 | 2024-12-11 17:21:51.44+00 |
| Sapphire - Imagine a framework | 737141877803057244 | old-application-commands-and-interactions | 889973175583133717 | 9.948 | 9.941 | 0,08% | 251 | 251 | 15,31% | 304 | 2021-09-21 20:41:09.651+00 | 2022-11-21 08:13:34.593+00 |
| Tech Haven | 455345206481518593 | cybersecurity-chat | 594961554701680640 | 9.675 | 9.675 | 0,08% | 500 | 500 | 10,69% | 722 | 2019-07-02 11:49:57.849+00 | 2024-11-27 12:44:51.223+00 |
| Sapphire - Imagine a framework | 737141877803057244 | plugins-development | 737142940777971773 | 9.413 | 9.412 | 0,08% | 92 | 92 | 7,72% | 334 | 2020-07-27 23:22:44.192+00 | 2024-11-05 21:33:05.905+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | cet-commands | 1157727395076391043 | 8.730 | 8.725 | 0,07% | 1.622 | 1.622 | 26,57% | 406 | 2023-09-30 17:17:43.08+00 | 2025-01-06 19:24:01.773+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | djkovrik-mods | 858635881275195401 | 8.627 | 8.624 | 0,07% | 534 | 534 | 16,49% | 628 | 2021-06-27 18:02:25.919+00 | 2025-01-06 21:28:22.813+00 |
| OpenRCT2 | 264137540670324737 | open-sound-and-music | 694586451500859469 | 8.611 | 8.610 | 0,07% | 198 | 198 | 10,59% | 581 | 2020-03-31 16:39:08.673+00 | 2025-01-11 03:40:28.068+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | redengine-research | 786902567778910229 | 8.492 | 8.482 | 0,07% | 283 | 282 | 6,59% | 190 | 2020-12-11 10:56:14.666+00 | 2024-12-02 21:40:14.362+00 |
| Neo4j | 787399249741479977 | cypher | 818578585194594334 | 8.477 | 8.476 | 0,07% | 751 | 751 | 24,49% | 944 | 2021-03-11 10:13:55.464+00 | 2024-12-24 10:29:41.533+00 |
| MonoGame Discord | 355231098122272778 | non-programming | 490325877117157392 | 8.346 | 8.345 | 0,07% | 247 | 247 | 6,04% | 475 | 2018-09-15 22:26:13.642+00 | 2024-12-24 11:57:35.956+00 |
| Tech Haven | 455345206481518593 | networking-chat | 594961585206722560 | 7.982 | 7.982 | 0,07% | 250 | 250 | 8,56% | 452 | 2019-07-10 14:03:07.296+00 | 2024-11-13 23:21:24.265+00 |
| MonoGame Discord | 355231098122272778 | gaming | 484428606542577674 | 7.842 | 7.842 | 0,07% | 163 | 163 | 5,88% | 468 | 2018-08-31 13:22:11.141+00 | 2024-11-07 12:33:51.613+00 |
| Touhou Game Dev | 933089313405685760 | touhou-spoilers | 1136052830260707458 | 7.640 | 7.635 | 0,06% | 52 | 52 | 11,28% | 24 | 2023-08-01 21:48:43.215+00 | 2023-08-31 03:05:26.72+00 |
| Touhou Game Dev | 933089313405685760 | anime-manga | 933089316547219557 | 7.507 | 7.506 | 0,06% | 85 | 85 | 12,64% | 357 | 2022-01-18 20:33:37.405+00 | 2025-01-05 09:24:54.807+00 |
| Docker | 460871933748183040 | offtopic | 532556917432647685 | 7.412 | 7.410 | 0,06% | 444 | 444 | 21,13% | 675 | 2019-01-09 13:52:51.543+00 | 2025-01-07 16:06:08.035+00 |
| WWebJS | 698610475432411196 | off-topic | 698622612523188285 | 7.391 | 7.390 | 0,06% | 255 | 255 | 24,84% | 543 | 2020-06-05 19:17:35.764+00 | 2024-12-25 00:45:26.217+00 |
| OpenRCT2 | 264137540670324737 | open-scenarios | 1093263778814116022 | 7.212 | 7.211 | 0,06% | 105 | 105 | 15,02% | 223 | 2023-04-05 20:05:06.844+00 | 2025-01-10 22:02:24.383+00 |
| Terasology | 270264625419911192 | web-stuff | 559240070062800906 | 7.204 | 7.198 | 0,06% | 44 | 44 | 8,02% | 360 | 2019-03-24 05:00:35.021+00 | 2024-05-15 19:50:31.358+00 |
| Sapphire - Imagine a framework | 737141877803057244 | old-discordjs-support | 750799332445519884 | 7.060 | 7.060 | 0,06% | 222 | 222 | 13,70% | 347 | 2020-10-21 19:23:49.55+00 | 2022-11-26 18:23:52.951+00 |
| Touhou Game Dev | 933089313405685760 | cirno-mc-chat | 1163908653091397662 | 6.965 | 6.949 | 0,06% | 34 | 34 | 5,07% | 203 | 2023-10-17 18:41:50.536+00 | 2025-01-06 12:49:41.24+00 |
| GameDevSG | 558680594498977792 | 🎨art-and-vfx | 676484825628278846 | 6.693 | 6.693 | 0,06% | 281 | 281 | 12,89% | 761 | 2020-02-10 17:52:15.893+00 | 2024-12-02 16:14:03.582+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | edgerunners | 1014540824882729000 | 6.480 | 6.479 | 0,05% | 270 | 270 | 16,02% | 106 | 2022-08-31 14:44:58.408+00 | 2023-01-28 11:07:37.797+00 |
| Touhou Game Dev | 933089313405685760 | gamemaker | 933089315737731120 | 6.448 | 6.445 | 0,05% | 71 | 71 | 7,39% | 228 | 2022-01-19 07:50:51.817+00 | 2024-12-29 17:08:47.95+00 |
| Touhou Game Dev | 933089313405685760 | godot | 933089316035506236 | 6.434 | 6.433 | 0,05% | 91 | 91 | 8,77% | 304 | 2022-01-19 01:46:25.067+00 | 2025-01-05 17:49:00.135+00 |
| Kavita | 821879810934439936 | komf | 1037456434822127717 | 6.092 | 6.076 | 0,05% | 156 | 156 | 12,11% | 367 | 2022-11-02 20:01:47.373+00 | 2024-12-20 21:52:25.036+00 |
| Return Community | 1080829289412432032 | 👑┇royal-chat | 1168556243024101516 | 5.979 | 5.976 | 0,05% | 99 | 99 | 33,17% | 345 | 2023-10-30 14:27:01.481+00 | 2024-12-28 15:31:55.309+00 |
| Neo4j | 787399249741479977 | graphql | 818578492723036210 | 5.936 | 5.926 | 0,05% | 376 | 376 | 27,89% | 787 | 2021-03-08 21:04:11.977+00 | 2024-12-20 17:27:06.949+00 |
| Sapphire - Imagine a framework | 737141877803057244 | website-development | 795723882556162058 | 5.917 | 5.911 | 0,05% | 68 | 68 | 8,68% | 228 | 2021-01-04 18:42:43.701+00 | 2024-11-16 02:03:29.762+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | mlsetup-builder | 1082772930892664943 | 5.639 | 5.630 | 0,05% | 126 | 126 | 21,10% | 268 | 2023-03-07 21:13:08.597+00 | 2025-01-05 18:43:35.922+00 |
| Penusbmic's Server | 894976658229063731 | itch-chat | 894976658229063737 | 5.539 | 5.451 | 0,05% | 306 | 288 | 21,72% | 498 | 2021-10-08 18:54:51.003+00 | 2024-12-31 15:47:09.6+00 |
| Rectify11 Community | 1077324213142175744 | shitpost-spam | 1077332778980479076 | 5.405 | 5.403 | 0,05% | 159 | 159 | 14,23% | 403 | 2023-02-28 23:12:19.123+00 | 2024-12-17 17:17:45.395+00 |
| TheScostumati | 516564332440584221 | 🎨wip-2d | 541985837265453066 | 5.359 | 5.359 | 0,05% | 120 | 120 | 3,97% | 541 | 2019-02-24 20:04:42.593+00 | 2024-05-01 15:38:06.185+00 |
| Terasology | 270264625419911192 | rendering | 591982628476026891 | 5.260 | 5.259 | 0,04% | 47 | 47 | 6,08% | 365 | 2019-06-22 13:35:28.773+00 | 2024-12-01 15:14:03.657+00 |
| Penusbmic's Server | 894976658229063731 | project-game-showcase | 917172543729844244 | 5.047 | 5.046 | 0,04% | 262 | 262 | 24,89% | 621 | 2021-12-09 19:44:43.682+00 | 2024-12-31 15:15:06.109+00 |
| Terasology | 270264625419911192 | math-n-physics | 701818347238588561 | 4.636 | 4.634 | 0,04% | 23 | 23 | 4,23% | 166 | 2020-04-20 15:37:05.732+00 | 2024-04-07 08:47:48.087+00 |
| Rectify11 Community | 1077324213142175744 | memes | 1077324214832476272 | 4.567 | 4.565 | 0,04% | 268 | 268 | 28,85% | 541 | 2023-02-28 23:42:14.143+00 | 2024-12-19 02:52:31.987+00 |
| Tech Haven | 455345206481518593 | windows-chat | 719555492757897276 | 4.539 | 4.539 | 0,04% | 155 | 155 | 9,74% | 294 | 2020-06-10 09:27:56.093+00 | 2024-10-28 05:16:08.247+00 |
| Touhou Game Dev | 933089313405685760 | jam-voice-text | 1068126758253117517 | 4.435 | 4.428 | 0,04% | 92 | 92 | 7,02% | 44 | 2023-01-26 11:30:09.685+00 | 2024-10-31 05:32:54.301+00 |
| Fermyon | 926888690310053918 | spin | 950022897160839248 | 4.389 | 4.389 | 0,04% | 303 | 303 | 19,30% | 670 | 2022-03-07 19:27:38.541+00 | 2025-01-06 22:01:51.93+00 |
| TheScostumati | 516564332440584221 | 💭movies-comics | 669239879334363170 | 4.372 | 4.372 | 0,04% | 79 | 79 | 6,38% | 659 | 2020-01-21 18:10:43.997+00 | 2025-01-07 16:20:27.06+00 |
| Shardeum | 933959587462254612 | 🤣・memes | 938397846510653440 | 4.371 | 4.370 | 0,04% | 1.416 | 1.416 | 9,73% | 801 | 2022-02-02 15:32:43.988+00 | 2025-01-08 15:21:10.258+00 |
| Terasology | 270264625419911192 | ai | 552216356364222469 | 4.289 | 4.288 | 0,04% | 33 | 33 | 3,78% | 240 | 2019-03-04 19:53:01.727+00 | 2023-05-04 20:00:13.602+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | visual-modding | 789457082712981524 | 4.137 | 4.129 | 0,03% | 191 | 191 | 8,19% | 165 | 2020-12-18 11:41:03.459+00 | 2021-10-26 10:58:38.377+00 |
| Kindred Games Community | 398282199788552193 | community-streams | 405205466910818305 | 4.099 | 4.099 | 0,03% | 317 | 317 | 2,17% | 1.488 | 2018-01-23 11:54:26.198+00 | 2024-12-29 23:08:54.139+00 |
| Terasology | 270264625419911192 | ephermeral-discussions | 1125013678966710342 | 3.988 | 3.986 | 0,03% | 14 | 14 | 22,58% | 146 | 2023-07-02 13:46:47.848+00 | 2024-12-23 03:05:07.086+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | null-morb-land | 1172804635061395456 | 3.916 | 3.908 | 0,03% | 83 | 83 | 8,75% | 181 | 2023-11-11 07:47:35.796+00 | 2025-01-06 15:43:17.844+00 |
| Terasology | 270264625419911192 | play-terasology | 713903952764207164 | 3.905 | 3.904 | 0,03% | 201 | 201 | 13,11% | 322 | 2020-06-04 21:50:36.357+00 | 2024-12-27 04:03:02.318+00 |
| Tech Haven | 455345206481518593 | pc-builds | 870388964475953182 | 3.899 | 3.899 | 0,03% | 103 | 103 | 11,34% | 240 | 2021-07-29 19:44:49.493+00 | 2024-11-04 18:58:54.876+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | cet-chat | 795037478229901322 | 3.838 | 3.837 | 0,03% | 97 | 97 | 5,68% | 110 | 2021-01-02 21:16:23.966+00 | 2022-10-23 14:54:09.466+00 |
| Terasology | 270264625419911192 | biology | 577139912474886157 | 3.793 | 3.793 | 0,03% | 26 | 26 | 0,24% | 190 | 2019-05-12 14:28:08.754+00 | 2024-01-07 02:03:34.244+00 |
| Tech Haven | 455345206481518593 | failtesters-den | 947700068729905203 | 3.688 | 3.687 | 0,03% | 57 | 57 | 9,74% | 402 | 2022-02-28 04:07:42.758+00 | 2024-12-17 04:56:55.783+00 |
| Penusbmic's Server | 894976658229063731 | feedback-and-constructive-criticism | 1017958075283542057 | 3.640 | 3.637 | 0,03% | 187 | 186 | 29,91% | 350 | 2022-09-10 07:52:37.68+00 | 2025-01-06 18:00:25.479+00 |
| Touhou Game Dev | 933089313405685760 | jam-team-forming | 933089316035506241 | 3.578 | 3.576 | 0,03% | 312 | 312 | 21,22% | 301 | 2022-03-25 14:05:48.364+00 | 2024-10-31 05:53:06.181+00 |
| GameDevSG | 558680594498977792 | 👾game-design | 676615865675808808 | 3.408 | 3.408 | 0,03% | 147 | 147 | 4,96% | 286 | 2020-02-11 15:08:44.756+00 | 2024-12-04 02:47:35.342+00 |
| Terasology | 270264625419911192 | outreach | 714188700141224036 | 3.350 | 3.347 | 0,03% | 26 | 26 | 1,14% | 160 | 2020-05-25 14:58:28.271+00 | 2025-01-07 04:44:05.86+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | deceptious-mods | 1097844044022956032 | 3.353 | 3.347 | 0,03% | 240 | 240 | 24,83% | 338 | 2023-04-18 11:20:41.67+00 | 2025-01-06 12:24:09.733+00 |
| Sapphire - Imagine a framework | 737141877803057244 | voice-context | 750105399172137011 | 3.311 | 3.311 | 0,03% | 56 | 56 | 2,87% | 123 | 2020-08-31 21:31:30.237+00 | 2022-05-19 06:06:13.907+00 |
| GameDevSG | 558680594498977792 | 🧮programming-and-tech | 676484881508859905 | 3.231 | 3.229 | 0,03% | 118 | 118 | 5,45% | 258 | 2020-02-10 17:52:31.082+00 | 2024-11-28 17:17:05.551+00 |
| Terasology | 270264625419911192 | ui-ux | 703047991430217728 | 3.228 | 3.226 | 0,03% | 30 | 30 | 4,90% | 202 | 2020-04-24 01:06:05.11+00 | 2024-05-30 20:29:28.303+00 |
| CodingWallah | 1056895641676152852 | 🎀│general-chat | 1056895642628276256 | 3.186 | 3.185 | 0,03% | 388 | 388 | 16,30% | 194 | 2022-12-26 11:26:35.28+00 | 2024-12-14 08:43:09.528+00 |
| Terasology | 270264625419911192 | architecture | 577194115725262912 | 3.164 | 3.163 | 0,03% | 28 | 28 | 8,44% | 254 | 2019-05-12 18:09:36.109+00 | 2023-05-01 10:00:44.451+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | psiberx-mods | 1171107143076806767 | 3.118 | 3.118 | 0,03% | 242 | 242 | 22,48% | 265 | 2023-11-06 17:31:24.559+00 | 2025-01-07 02:16:45.795+00 |
| TheScostumati | 516564332440584221 | 🌀inspiration | 721321990207701052 | 3.058 | 3.056 | 0,03% | 96 | 96 | 3,44% | 760 | 2020-06-13 12:41:15.627+00 | 2025-01-07 15:11:10.349+00 |
| Terasology | 270264625419911192 | world-generation | 702893102481932308 | 3.030 | 3.030 | 0,03% | 31 | 31 | 8,78% | 244 | 2020-04-23 14:48:35.577+00 | 2024-05-22 01:34:09.89+00 |
| Penusbmic's Server | 894976658229063731 | general | 1059937532479029308 | 2.804 | 2.804 | 0,02% | 181 | 181 | 19,33% | 260 | 2023-01-03 20:54:16.074+00 | 2024-11-29 14:03:07.448+00 |
| Kavita | 821879810934439936 | melvor-idle | 1292838448104734751 | 2.802 | 2.800 | 0,02% | 10 | 10 | 3,57% | 62 | 2024-10-07 13:18:39.017+00 | 2024-12-21 17:51:44.916+00 |
| Montano Community | 561997286087852118 | 📚┃english-only | 704757495100342372 | 2.772 | 2.772 | 0,02% | 367 | 367 | 6,96% | 331 | 2020-04-28 18:17:10.218+00 | 2024-11-20 06:13:19.91+00 |
| Touhou Game Dev | 933089313405685760 | toho-station-jam | 1293617429821394954 | 2.767 | 2.760 | 0,02% | 63 | 62 | 20,58% | 13 | 2024-10-09 16:54:32.715+00 | 2024-10-23 01:13:51.95+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | blender-add-on-dev | 1141547129794478080 | 2.722 | 2.716 | 0,02% | 21 | 21 | 12,52% | 139 | 2023-08-17 02:07:20.997+00 | 2025-01-06 12:42:55.163+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | rmk-mods | 858646966019817482 | 2.699 | 2.696 | 0,02% | 157 | 157 | 17,32% | 295 | 2021-06-29 01:54:47.736+00 | 2025-01-05 15:29:04.22+00 |
| Terasology | 270264625419911192 | launcher | 591979528432386068 | 2.691 | 2.691 | 0,02% | 38 | 38 | 2,97% | 216 | 2019-06-22 13:36:23.788+00 | 2024-08-29 23:36:48.729+00 |
| Tech Haven | 455345206481518593 | servers-chat | 733027648841842739 | 2.681 | 2.681 | 0,02% | 100 | 100 | 7,91% | 178 | 2020-07-15 18:34:03.434+00 | 2024-12-16 02:35:19.772+00 |
| Terasology | 270264625419911192 | gestalt | 714313228271747152 | 2.670 | 2.669 | 0,02% | 20 | 20 | 8,80% | 171 | 2020-05-25 03:11:38.965+00 | 2024-12-24 21:57:49.982+00 |
| Kavita | 821879810934439936 | development | 1009566589663850536 | 2.609 | 2.609 | 0,02% | 66 | 66 | 8,39% | 206 | 2022-08-17 22:13:10.936+00 | 2024-12-21 17:49:50.93+00 |
| Return Community | 1080829289412432032 | 🗿┇meme | 1136203088601034764 | 2.440 | 2.440 | 0,02% | 384 | 384 | 28,52% | 397 | 2023-08-05 06:45:31.11+00 | 2024-12-28 14:53:25.77+00 |
| OpenRCT2 | 264137540670324737 | localisation | 691736823378083882 | 2.355 | 2.354 | 0,02% | 113 | 113 | 7,73% | 298 | 2020-04-04 19:25:52.929+00 | 2024-12-28 20:59:41.622+00 |
| Return Community | 1080829289412432032 | 📷┇medi̇a | 1160264181233225799 | 2.320 | 2.318 | 0,02% | 378 | 378 | 26,49% | 344 | 2023-10-07 17:15:42.057+00 | 2024-12-28 15:17:42.558+00 |
| MonoGame Discord | 355231098122272778 | suggestions | 355231151272624138 | 2.213 | 2.211 | 0,02% | 157 | 157 | 9,77% | 266 | 2017-09-17 19:06:02.754+00 | 2024-11-12 21:19:47.936+00 |
| Tech Haven | 455345206481518593 | electronics-chat | 594961729889370124 | 2.204 | 2.204 | 0,02% | 100 | 100 | 5,90% | 150 | 2019-10-03 14:00:48.255+00 | 2024-12-18 16:34:57.035+00 |
| GameDevSG | 558680594498977792 | 💗emotional-support | 1075785552290398359 | 2.192 | 2.192 | 0,02% | 107 | 107 | 23,27% | 262 | 2023-02-16 15:00:20.07+00 | 2024-12-19 16:46:26.402+00 |
| Oxylabs | 1128239127687598080 | ┠💬-general | 1128324284754968637 | 2.187 | 2.183 | 0,02% | 511 | 511 | 35,04% | 358 | 2023-09-15 09:02:22.631+00 | 2025-01-04 22:27:37.992+00 |
| Sapphire - Imagine a framework | 737141877803057244 | shapeshift-development-⚡ | 934614121687687179 | 2.137 | 2.137 | 0,02% | 32 | 32 | 9,97% | 118 | 2022-01-23 15:33:47.902+00 | 2024-10-01 11:32:13.037+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | tweakdb-editing | 826506889117302875 | 2.050 | 2.046 | 0,02% | 62 | 62 | 10,36% | 90 | 2021-04-01 01:55:57.065+00 | 2022-07-17 21:22:39.597+00 |
| L'Ordre des Devs | 706640777450881114 | cmd | 1045347041909420032 | 2.017 | 2.017 | 0,02% | 61 | 61 | 11,95% | 244 | 2022-11-26 00:09:49.568+00 | 2025-01-04 21:35:50.164+00 |
| Neo4j | 787399249741479977 | app-dev | 816630778505986058 | 1.981 | 1.981 | 0,02% | 366 | 366 | 29,78% | 550 | 2021-03-24 08:57:26.664+00 | 2024-12-24 16:07:50.037+00 |
| OpenVic - Community | 1062018115275325480 | 🏅discussion | 1094718769546416278 | 1.960 | 1.960 | 0,02% | 70 | 70 | 20,56% | 141 | 2023-04-09 20:40:58.149+00 | 2024-10-10 00:20:54.791+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | wolvenkit-scripts | 1036574451237662780 | 1.913 | 1.908 | 0,02% | 57 | 57 | 21,70% | 145 | 2022-10-31 09:38:00.745+00 | 2025-01-06 22:27:41.172+00 |
| Neo4j | 787399249741479977 | data-science | 816630747136786484 | 1.904 | 1.904 | 0,02% | 222 | 222 | 25,74% | 465 | 2021-03-17 15:13:14.976+00 | 2024-12-09 04:53:18.714+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | wolvenkit-github | 717721419529584723 | 1.873 | 1.871 | 0,02% | 39 | 39 | 15,55% | 333 | 2020-12-21 23:14:09.642+00 | 2024-12-11 14:49:08.449+00 |
| Terasology | 270264625419911192 | vc-general | 710527864872632421 | 1.836 | 1.836 | 0,02% | 53 | 53 | 9,91% | 218 | 2020-05-25 17:30:41.874+00 | 2024-08-18 19:08:04.12+00 |
| Andy’s Development | 857672921912836116 | suggestions | 857791068393308170 | 1.814 | 1.792 | 0,02% | 122 | 122 | 15,68% | 206 | 2021-06-25 01:15:46.636+00 | 2023-08-31 03:37:59.825+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | modding-showcases | 796493553924440084 | 1.779 | 1.779 | 0,01% | 259 | 259 | 18,04% | 354 | 2021-01-06 21:49:35.479+00 | 2022-09-17 07:48:52.528+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | merchants-of-death | 1206340528158019634 | 1.779 | 1.778 | 0,01% | 73 | 73 | 20,92% | 142 | 2024-02-11 20:50:49.152+00 | 2025-01-03 10:47:01.177+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | manually_archived_tweak-modding | 1016766213755523213 | 1.780 | 1.772 | 0,01% | 115 | 115 | 16,37% | 74 | 2022-09-06 17:46:06.135+00 | 2022-12-25 21:54:24.985+00 |
| Neo4j | 787399249741479977 | product | 816627121732059146 | 1.721 | 1.720 | 0,01% | 423 | 423 | 25,93% | 535 | 2021-03-29 08:00:11.754+00 | 2024-12-20 11:00:35.809+00 |
| Neo4j | 787399249741479977 | graph-academy | 816956538512998440 | 1.710 | 1.708 | 0,01% | 417 | 417 | 21,66% | 516 | 2021-03-04 09:00:53.812+00 | 2024-12-24 00:59:00.189+00 |
| Sapphire - Imagine a framework | 737141877803057244 | @plugin-subcommands Chat Input support | 934916302651412512 | 1.604 | 1.602 | 0,01% | 37 | 37 | 11,30% | 58 | 2022-01-23 23:01:38.52+00 | 2022-08-12 02:29:12.154+00 |
| Touhou Game Dev | 933089313405685760 | help-wanted | 933089315297312882 | 1.602 | 1.601 | 0,01% | 116 | 116 | 13,55% | 177 | 2022-01-18 22:30:08.808+00 | 2024-12-31 20:37:22.221+00 |
| GameDevSG | 558680594498977792 | 📝writing | 677487756464619530 | 1.601 | 1.599 | 0,01% | 71 | 71 | 8,51% | 202 | 2020-02-13 14:05:46.136+00 | 2024-10-01 20:08:33.933+00 |
| Neo4j | 787399249741479977 | apoc | 831067735499866152 | 1.569 | 1.569 | 0,01% | 238 | 238 | 28,30% | 396 | 2021-04-12 07:27:48.923+00 | 2024-12-19 14:14:10.724+00 |
| Terasology | 270264625419911192 | playtest | 698959573523890197 | 1.558 | 1.555 | 0,01% | 38 | 38 | 6,43% | 49 | 2020-04-12 18:16:23.389+00 | 2024-12-26 02:41:24.265+00 |
| Return Community | 1080829289412432032 | 🎨┇art | 1162389494515900446 | 1.532 | 1.532 | 0,01% | 131 | 131 | 34,33% | 256 | 2023-10-13 14:01:00.304+00 | 2024-12-28 17:00:44.496+00 |
| OpenVic - Community | 1062018115275325480 | 🧠showcase-discussion | 1097347652510826506 | 1.521 | 1.521 | 0,01% | 144 | 144 | 29,65% | 147 | 2023-04-17 02:32:51.765+00 | 2024-11-24 18:37:27.685+00 |
| Rectify11 Community | 1077324213142175744 | installer | 1163243209384808559 | 1.457 | 1.457 | 0,01% | 224 | 224 | 36,99% | 200 | 2023-10-16 05:57:43.039+00 | 2024-12-18 00:37:00.806+00 |
| Touhou Game Dev | 933089313405685760 | resources-and-talks | 933089315297312883 | 1.469 | 1.457 | 0,01% | 77 | 77 | 7,69% | 201 | 2022-02-08 04:55:10.643+00 | 2025-01-06 02:35:34.482+00 |
| Touhou Game Dev | 933089313405685760 | rpg-maker | 933089316035506237 | 1.454 | 1.454 | 0,01% | 57 | 57 | 6,26% | 83 | 2022-01-27 02:30:58.799+00 | 2024-12-23 22:39:36.21+00 |
| GameDevSG | 558680594498977792 | ⏳animation | 676484919303864343 | 1.425 | 1.425 | 0,01% | 121 | 121 | 6,18% | 247 | 2020-02-10 17:53:07.164+00 | 2024-10-31 09:12:38.807+00 |
| Rectify11 Community | 1077324213142175744 | theme | 1077324214832476275 | 1.392 | 1.390 | 0,01% | 96 | 96 | 31,01% | 144 | 2023-03-01 11:45:41.348+00 | 2024-12-05 21:29:03.983+00 |
| Terasology | 270264625419911192 | play-ark | 409116216322686976 | 1.385 | 1.383 | 0,01% | 19 | 19 | 1,16% | 117 | 2018-02-03 03:30:12.947+00 | 2022-08-27 04:30:15.597+00 |
| Terasology | 270264625419911192 | lost | 708801708545015809 | 1.369 | 1.368 | 0,01% | 18 | 18 | 0,73% | 59 | 2020-05-09 22:05:57.294+00 | 2021-12-10 09:13:13.982+00 |
| Sapphire - Imagine a framework | 737141877803057244 | pieces-development | 737142871622156369 | 1.358 | 1.357 | 0,01% | 36 | 36 | 5,75% | 84 | 2020-07-27 23:22:42.07+00 | 2024-07-24 20:52:27.032+00 |
| MonoGame Discord | 355231098122272778 | voice-general | 775019135121227797 | 1.338 | 1.338 | 0,01% | 73 | 73 | 2,99% | 60 | 2020-11-08 16:24:29.652+00 | 2024-11-15 07:32:00.816+00 |
| Touhou Game Dev | 933089313405685760 | films-and-games | 1311998626515390525 | 1.340 | 1.336 | 0,01% | 35 | 35 | 7,11% | 24 | 2024-11-29 10:15:16.24+00 | 2024-12-29 20:26:49.975+00 |
| CodingWallah | 1056895641676152852 | 😊chat-room | 1271778126275543040 | 1.329 | 1.329 | 0,01% | 138 | 138 | 18,74% | 88 | 2024-08-10 13:58:40.307+00 | 2024-12-15 15:49:33.655+00 |
| Rectify11 Community | 1077324213142175744 | startify | 1163242529471336539 | 1.322 | 1.319 | 0,01% | 97 | 97 | 32,22% | 131 | 2023-10-15 22:38:29.569+00 | 2024-12-18 00:54:25.924+00 |
| Neo4j | 787399249741479977 | 🌞banter | 788809846949412878 | 1.277 | 1.274 | 0,01% | 226 | 226 | 22,53% | 443 | 2021-03-09 09:07:19.707+00 | 2024-12-24 09:26:25+00 |
| OpenVic - Community | 1062018115275325480 | 🤖dev-diary-discussion | 1074055648687435796 | 1.232 | 1.232 | 0,01% | 125 | 125 | 24,27% | 109 | 2023-02-11 19:56:37.723+00 | 2025-01-10 06:49:23.379+00 |
| OpenVic - Community | 1062018115275325480 | 🏆submissions | 1094714102569517207 | 1.184 | 1.184 | 0,01% | 158 | 158 | 1,69% | 171 | 2023-04-09 20:37:45.581+00 | 2024-10-28 14:29:13.599+00 |
| Neo4j | 787399249741479977 | dev-ops | 854675261635428353 | 1.162 | 1.162 | 0,01% | 246 | 246 | 27,80% | 381 | 2021-06-16 16:18:30.832+00 | 2024-12-16 09:44:49.049+00 |
| Sapphire - Imagine a framework | 737141877803057244 | cli-development | 1249350647443361803 | 1.127 | 1.126 | 0,01% | 16 | 16 | 20,60% | 20 | 2024-06-09 13:13:32.907+00 | 2024-11-24 04:51:00.881+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | _server-competition-discussion | 1123223580675670026 | 1.119 | 1.105 | 0,01% | 16 | 16 | 13,39% | 27 | 2023-06-27 12:10:17.041+00 | 2023-08-08 11:09:12.097+00 |
| Rectify11 Community | 1077324213142175744 | your-art | 1095818717327282298 | 1.106 | 1.102 | 0,01% | 138 | 138 | 36,03% | 192 | 2023-04-12 21:14:47.656+00 | 2024-12-19 00:41:42.723+00 |
| Neo4j | 787399249741479977 | aura | 854674503668990032 | 1.094 | 1.093 | 0,01% | 221 | 221 | 25,25% | 386 | 2021-06-17 12:35:51.402+00 | 2024-12-21 13:33:26.117+00 |
| OpenVic - Community | 1062018115275325480 | submissions-general | 1093214935066095686 | 1.083 | 1.082 | 0,01% | 62 | 62 | 24,31% | 74 | 2023-04-05 16:54:15.091+00 | 2024-09-25 11:08:06.272+00 |
| OpenVic - Community | 1062018115275325480 | 🖥technical-discussion | 1105124380612247582 | 1.066 | 1.065 | 0,01% | 51 | 51 | 22,63% | 72 | 2023-05-08 13:33:24.215+00 | 2024-10-23 12:02:27.878+00 |
| TikTok Shop Developer Hub | 1204537856870191114 | general | 1204537856870191117 | 1.068 | 1.063 | 0,01% | 404 | 400 | 40,36% | 224 | 2024-02-06 21:27:58.8+00 | 2024-12-27 09:15:47.151+00 |
| Rectify11 Community | 1077324213142175744 | bootlegs | 1099322850147586099 | 1.061 | 1.059 | 0,01% | 83 | 83 | 26,35% | 130 | 2023-04-22 13:17:10.255+00 | 2024-12-15 06:37:19.482+00 |
| OpenVic - Community | 1062018115275325480 | openvic-discussion | 1288761356127961149 | 1.047 | 1.047 | 0,01% | 50 | 50 | 20,73% | 58 | 2024-09-26 09:07:50.716+00 | 2025-01-10 02:21:09.225+00 |
| TikTok Shop Developer Hub | 1204537856870191114 | general-discussions | 1209061602796634132 | 1.022 | 1.022 | 0,01% | 315 | 315 | 44,62% | 207 | 2024-02-28 17:41:54.202+00 | 2024-12-21 09:05:26.22+00 |
| Kavita | 821879810934439936 | media-suggest | 973964508374638672 | 1.021 | 1.021 | 0,01% | 61 | 61 | 11,26% | 127 | 2022-05-11 15:09:01.461+00 | 2024-12-22 01:42:55.946+00 |
| Fermyon | 926888690310053918 | general | 926888690310053921 | 1.058 | 1.003 | 0,01% | 199 | 171 | 23,93% | 284 | 2022-01-01 17:25:48.352+00 | 2025-01-08 10:18:49.792+00 |
| Neo4j | 787399249741479977 | graphrag | 1161686426476351530 | 997 | 997 | 0,01% | 131 | 131 | 28,99% | 213 | 2023-10-11 15:59:01.999+00 | 2024-12-23 09:09:18.669+00 |
| Return Community | 1080829289412432032 | 💼┇hiring | 1253401749235044393 | 938 | 937 | 0,01% | 242 | 242 | 13,45% | 183 | 2024-06-20 17:31:13.872+00 | 2024-12-28 15:26:40.952+00 |
| Touhou Game Dev | 933089313405685760 | 3d-works | 1231377195956572210 | 936 | 936 | 0,01% | 34 | 34 | 8,01% | 54 | 2024-04-20 22:53:36.275+00 | 2024-12-24 12:55:09.946+00 |
| Kavita | 821879810934439936 | share-your-own | 933858494560481360 | 933 | 912 | 0,01% | 98 | 98 | 16,45% | 159 | 2022-01-23 15:16:34.81+00 | 2024-12-12 22:58:33.847+00 |
| Kavita | 821879810934439936 | show-off-your-server | 936974355777327114 | 885 | 885 | 0,01% | 102 | 102 | 13,67% | 144 | 2022-01-29 16:47:07.971+00 | 2024-12-15 00:32:38.963+00 |
| ImperialPlugins\.com | 284399832385191936 | rust-support | 741451835193163867 | 874 | 873 | 0,01% | 64 | 64 | 13,52% | 129 | 2020-11-16 15:17:44.97+00 | 2024-03-16 17:21:18.166+00 |
| 💻 Ouckah Lair | 519640186167099402 | 》code | 1092906566379896982 | 843 | 843 | 0,01% | 61 | 61 | 19,22% | 74 | 2023-04-05 23:06:31.702+00 | 2024-09-07 18:05:35.159+00 |
| OpenVic - Community | 1062018115275325480 | 💻tech-support | 1104094378550632538 | 824 | 824 | 0,01% | 52 | 52 | 18,93% | 61 | 2023-05-05 17:35:44.178+00 | 2025-01-05 15:20:37.804+00 |
| Cyberpunk 2077 Modding Community | 717692382849663036 | krat0es-mods | 984010932013371393 | 822 | 820 | 0,01% | 79 | 79 | 15,12% | 114 | 2022-06-08 08:29:48.621+00 | 2025-01-07 01:31:47.263+00 |
| Terasology | 270264625419911192 | game-lobby | 411879557247795201 | 811 | 810 | 0,01% | 38 | 38 | 0,00% | 78 | 2018-02-12 09:04:26.328+00 | 2021-12-19 15:09:00.88+00 |
| Neo4j | 787399249741479977 | visualization | 859317168851779604 | 806 | 805 | 0,01% | 156 | 156 | 25,84% | 300 | 2021-06-30 10:13:44.337+00 | 2024-11-29 13:26:08.795+00 |
| MonoGame Discord | 355231098122272778 | hobby | 487351382987243541 | 803 | 803 | 0,01% | 103 | 103 | 10,09% | 121 | 2018-09-06 20:28:40.666+00 | 2024-12-11 14:42:41.095+00 |
| Neo4j | 787399249741479977 | data-models | 872013648707588136 | 801 | 801 | 0,01% | 206 | 206 | 22,85% | 289 | 2021-08-03 07:16:29.941+00 | 2024-12-16 11:06:44.284+00 |
| Terasology | 270264625419911192 | artwork | 736668510582734940 | 795 | 795 | 0,01% | 27 | 27 | 2,89% | 83 | 2020-07-25 19:39:42.388+00 | 2024-04-07 16:10:32.491+00 |
| Penusbmic's Server | 894976658229063731 | creative-ideas | 1060558407024775188 | 765 | 765 | 0,01% | 52 | 52 | 20,26% | 133 | 2023-01-07 15:56:25.494+00 | 2024-08-14 13:43:29.776+00 |
| Neo4j | 787399249741479977 | error | 930032449679925278 | 758 | 758 | 0,01% | 265 | 265 | 15,17% | 310 | 2022-01-19 20:50:26.459+00 | 2024-12-21 20:36:12.185+00 |
| 💻 Ouckah Lair | 519640186167099402 | 》questions | 1093313287824879647 | 744 | 744 | 0,01% | 111 | 111 | 17,74% | 98 | 2023-04-23 05:44:01.317+00 | 2024-12-17 15:43:55.304+00 |
| Touhou Game Dev | 933089313405685760 | showcase-committee | 1301095373628248074 | 744 | 741 | 0,01% | 29 | 29 | 13,90% | 10 | 2024-10-30 08:08:35.822+00 | 2025-01-02 11:00:49.965+00 |
| Penusbmic's Server | 894976658229063731 | highscores | 1090600226110324756 | 726 | 726 | 0,01% | 38 | 38 | 15,70% | 76 | 2023-05-06 10:07:43.809+00 | 2024-12-23 22:28:33.588+00 |
| Touhou Game Dev | 933089313405685760 | music-links | 1287449658364268676 | 702 | 700 | 0,01% | 48 | 47 | 8,29% | 96 | 2024-09-22 16:25:44.752+00 | 2025-01-06 23:47:39.59+00 |
| Terasology | 270264625419911192 | play-valheim | 811692749292175380 | 698 | 697 | 0,01% | 13 | 13 | 5,31% | 68 | 2021-02-17 20:20:24.885+00 | 2023-09-25 05:00:18.016+00 |
| Terasology | 270264625419911192 | play-dest-sol | 713904031562727445 | 679 | 679 | 0,01% | 36 | 36 | 18,85% | 84 | 2020-08-17 13:58:06.622+00 | 2024-12-30 13:08:10.03+00 |
| GameDevSG | 558680594498977792 | 🎙audio | 676737759674630144 | 668 | 668 | 0,01% | 72 | 72 | 10,78% | 206 | 2020-02-11 15:27:35.332+00 | 2024-12-14 17:31:23.01+00 |
| Sapphire - Imagine a framework | 737141877803057244 | sapphire-esm-only | 1012413247011422409 | 650 | 649 | 0,01% | 92 | 92 | 28,97% | 5 | 2022-08-25 17:29:36.595+00 | 2022-08-29 08:58:34.376+00 |
| MonoGame Discord | 355231098122272778 | commercial | 453768164476715010 | 645 | 645 | 0,01% | 100 | 100 | 8,84% | 94 | 2018-06-28 11:39:26.977+00 | 2024-09-21 11:08:21.819+00 |
| Touhou Game Dev | 933089313405685760 | shame | 1224130852469084221 | 624 | 624 | 0,01% | 57 | 57 | 0,00% | 3 | 2024-03-31 23:00:03.19+00 | 2024-07-13 19:43:04.974+00 |
| Touhou Game Dev | 933089313405685760 | jam-submission-help | 1193629430166339624 | 606 | 604 | 0,01% | 58 | 58 | 10,26% | 17 | 2024-01-07 18:58:04.403+00 | 2024-11-05 20:20:26.972+00 |
| Touhou Game Dev | 933089313405685760 | renpy | 933089316035506238 | 598 | 598 | 0,01% | 28 | 28 | 7,53% | 38 | 2022-02-27 09:09:04.073+00 | 2024-12-28 03:55:34.638+00 |
| Terasology | 270264625419911192 | performance | 882575244215341097 | 594 | 594 | 0,01% | 18 | 18 | 23,74% | 45 | 2021-09-01 10:43:06.517+00 | 2024-07-14 17:39:57.171+00 |
| Neo4j | 787399249741479977 | 💌suggestions | 819928762107822100 | 591 | 584 | 0,00% | 153 | 153 | 26,20% | 228 | 2021-03-12 14:10:10.914+00 | 2024-12-23 17:04:31.009+00 |
| Sapphire - Imagine a framework | 737141877803057244 | sapphire-v4-only-djs-v14-or-more | 1021836029520515152 | 583 | 582 | 0,00% | 40 | 40 | 15,98% | 11 | 2022-09-21 17:03:02.044+00 | 2022-10-01 15:20:51.265+00 |
| Touhou Game Dev | 933089313405685760 | jam-game-release | 933089316035506244 | 563 | 563 | 0,00% | 196 | 196 | 6,22% | 145 | 2022-04-18 00:01:37.237+00 | 2024-12-05 11:05:35.26+00 |
| Penusbmic's Server | 894976658229063731 | bugs-and-crashes | 1059947040794230945 | 560 | 560 | 0,00% | 56 | 56 | 19,64% | 88 | 2023-01-03 21:43:01.125+00 | 2024-12-31 13:37:55.382+00 |
| Touhou Game Dev | 933089313405685760 | unreal | 933089315737731121 | 543 | 543 | 0,00% | 41 | 41 | 6,08% | 40 | 2022-01-19 00:40:47.337+00 | 2024-09-03 08:04:35.715+00 |
| 💻 Ouckah Lair | 519640186167099402 | ：introductions | 1092866443609124892 | 535 | 535 | 0,00% | 344 | 344 | 15,51% | 172 | 2023-04-05 18:12:51.796+00 | 2024-12-17 18:16:46.521+00 |
| Penusbmic's Server | 894976658229063731 | upcoming-pack-ideas-and-feedback | 894976658711400500 | 528 | 528 | 0,00% | 61 | 61 | 19,70% | 96 | 2021-12-21 15:15:10.701+00 | 2024-10-30 15:49:34.896+00 |
| Rosebud AI | 773712199729414144 | 🗣┃tokkingheads | 945756857706885181 | 519 | 519 | 0,00% | 105 | 105 | 31,98% | 187 | 2022-03-09 04:00:31.609+00 | 2024-12-03 09:18:05.716+00 |
| WWebJS | 698610475432411196 | suggestions | 698618511798567014 | 515 | 515 | 0,00% | 133 | 133 | 24,47% | 243 | 2020-04-14 16:35:50.408+00 | 2024-11-27 19:36:10.932+00 |
| WWebJS | 698610475432411196 | hebrew | 995711591905513602 | 509 | 509 | 0,00% | 58 | 58 | 28,09% | 104 | 2022-07-11 20:35:07.869+00 | 2025-01-05 11:16:57.381+00 |
| Fermyon | 926888690310053918 | cloud | 1024646765149950022 | 500 | 500 | 0,00% | 94 | 94 | 24,40% | 164 | 2022-10-24 13:36:58.958+00 | 2024-11-29 14:45:56.935+00 |
| WWebJS | 698610475432411196 | wwebjs | 904443786548113488 | 12.161 | 2 | 0,00% | 10.426 | 2 | 0,00% | 2 | 2021-10-31 22:56:57.594+00 | 2025-01-08 23:49:21.539+00 |

## 10. Fontes auditaveis

Os arquivos de entrada deste documento estao em `data/processed/disentanglement/population_participants_v2`.

| Arquivo | SHA-256 |
| --- | --- |
| channels.csv | `2c113b0600400f5a9a3ca46732391ba90d3f44650532f2c11a061e4007b29cc4` |
| servers.csv | `2494ef84439d28ef0afc43a04aa01e2dad9cb7e97234e077b2eb95964d2c35f1` |
| temporal_activity.csv | `7c2b1a9e03c31f43e1ad2dffa1c936931bf4a6a623b3e108058004d3a7246355` |
| reply_distances.csv | `7aa8c0a5e19f418277af09395ba22e1701197d94009d8769c57aaeafaf9dbda3` |
| concentration.csv | `04e767f3641f813d1d2530ce84ae96988724531d63f09d9f7d0bcada8c26bcfb` |
| summary.json | `5b943b1b54d90c85a3e08cc13853d8828fcabdded95d91a20ef6af49c16f45c0` |

Os numeradores, denominadores, agrupamentos, faixas e formulas adicionais estao no gerador Python. A extracao original, suas definicoes e a proveniencia do Parquet estao no manifesto da populacao. Nao foram adicionados calculos manuais fora desses arquivos executaveis.
