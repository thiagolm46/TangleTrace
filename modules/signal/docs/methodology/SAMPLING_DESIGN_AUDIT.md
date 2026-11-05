# Desenho amostral: auditoria do piloto

Relatorio gerado por `python -m discord_disentanglement.sampling_audit`. Todos os calculos estao em `discord_disentanglement/sampling_audit.py`; os CSVs e hashes permitem conferir cada resultado. Nao houve alteracao da entrada, do cadastro ou do sorteio.

## 1. Escopo e verificacao do mecanismo

A inferencia e condicional aos servidores retidos e a elegibilidade provisoria. O mecanismo e estratificado no nivel dos canais (servidor x porte), com meses ativos e blocos sorteados nos niveis seguintes. Sortear meses nao e garantir cobertura de todos os segmentos temporais.

Resultado: **38/38 verificacoes aprovadas**. Os hashes das entradas e do corpus foram verificados antes da analise. A semente foi reexecutada e as probabilidades recalculadas independentemente do registro do sorteio.

| Medida | Valor |
| --- | --- |
| frame_channels | 297 |
| sampled_channels | 107 |
| sampled_servers | 29 |
| windows | 317 |
| target_messages | 17.921 |
| eligible_technical_targets | 11.864.848 |
| expected_windows | 316,44 |
| expected_targets | 18.127,91 |

A formula pi = (n_h/N_h)(m_c/M_c)(w_ct/W_ct) e o peso 1/pi sao validos para cada bloco e suas mensagens-alvo. A ultima janela incompleta deve continuar no quadro para manter probabilidade positiva. O produto nao transforma a amostra em autoponderada: medias brutas de mensagens nao estimam automaticamente a media do corpus.

A correspondencia entre os totais tecnicos do Parquet e os blocos tambem foi conferida. A estimativa Horvitz-Thompson do total observado na amostra nao precisa coincidir com o total conhecido em uma unica realizacao: essa diferenca nao e, isoladamente, erro de sorteio.

Como todos os tamanhos dos blocos sao conhecidos, e possivel calcular a variancia EXATA sob este desenho para essas quantidades auxiliares, sem usar rotulos humanos. A lei da variancia total e aplicada recursivamente aos tres sorteios SRS sem reposicao, incluindo as correcoes de populacao finita. Isso nao estima a variancia de toxicidade, arestas semanticas ou desempenho de modelos.

| Quantidade auxiliar | Observado | Esperanca exata | Desvio-padrao do desenho | Desvio padronizado |
| --- | --- | --- | --- | --- |
| ht_target_total | 17.500.055,33 | 11.864.848,00 | 4.760.850,48 | 1,184 |
| unweighted_target_count | 17.921,00 | 18.127,91 | 565,79 | -0,366 |
| short_window_count | 198,00 | 196,19 | 7,22 | 0,251 |

O desvio padronizado e descritivo, nao um p-valor ou teste normal: a distribuicao do estimador pode ser assimetrica. Uma discrepancia grande do total HT conhecido e alerta de instabilidade dos pesos, nao prova isolada de vies. Os componentes exatos por nivel estao em `known_total_variance.csv`.

A recursao para um sorteio de n entre N unidades com medias mu_i e variancias internas V_i usa Var(soma selecionada) = n(1-n/N) S_mu^2 + (n/N) soma V_i; para expansao HT, multiplica-se a media por N/n e a variancia por (N/n)^2. Estratos independentes sao somados.

## 2. Estratos e distribuicao resultante

Ha 64 estratos nao vazios; 29 sao censitarios no nivel dos canais. Os limites de porte sao operacionais, nao um resultado validado como otimo. Estratos preservam cobertura e probabilidades conhecidas; homogeneidade do volume nao demonstra homogeneidade dos resultados de disentanglement.

A tabela compara limites alternativos sem excluir canais nem refazer o sorteio. As cotas permanecem iguais, mas o custo esperado pode mudar. CV e apenas dispersao relativa do volume dentro de servidor x porte, nao variancia do estimador nem criterio suficiente para escolher cortes.

| Cenario | Corte pequeno | Corte medio | Canais previstos | Janelas esperadas | Alvos esperados | Fracao curta esperada | CV de volume | DP relativo HT auxiliar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frozen | 1.000,0 | 10.000,0 | 107 | 316,44 | 18.127,91 | 62,00% | 0,757 | 40,13% |
| half_cutpoints | 500,0 | 5.000,0 | 91 | 270,47 | 15.609,78 | 62,32% | 0,945 | 44,83% |
| double_cutpoints | 2.000,0 | 20.000,0 | 111 | 330,27 | 20.276,81 | 57,33% | 0,562 | 29,80% |
| volume_tertiles | 2.649,0 | 15.905,7 | 113 | 336,41 | 20.302,72 | 59,12% | 0,589 | 33,46% |

Distribuicao por porte; esperado significa soma das probabilidades no quadro elegivel, nao uma cota exata de mensagens:

| Porte | Alvos no quadro | Janelas esperadas | Janelas observadas | Alvos esperados | Alvos observados |
| --- | --- | --- | --- | --- | --- |
| large | 11.360.130 | 113,94 | 114 | 9.618,24 | 9.691 |
| medium | 476.545 | 131,17 | 132 | 6.538,94 | 6.493 |
| small | 28.173 | 71,33 | 71 | 1.970,74 | 1.737 |

Foram observadas 198 janelas incompletas; o desenho previa 196,19 em media. Ha 13 janelas com um alvo e 64 com ate dez. Meses uniformes e blocos finais tornam janelas curtas especialmente provaveis em canais pouco ativos; isso nao constitui falha automaticamente.

Distribuicoes completas por servidor, canal e mes estao em `allocation.csv`. A alocacao nao precisa reproduzir participacoes brutas do corpus: essa diferenca e intencional para evitar dominio dos maiores canais. Comparacoes aqui sao descritivas; proximidade ao valor esperado nao e teste de representatividade.

## 3. Adequacao das janelas ao disentanglement

Duracoes em horas; min/P25/mediana/media/P75/P90/P95/max. Mensagens singulares tem duracao zero, que nao demonstra troca rapida. Medidas abaixo descrevem somente a amostra realizada, nao estimativas ponderadas da populacao.

| Medida | Min | P25 | Mediana | Media | P75 | P90 | P95 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target_count | 1,00 | 15,00 | 57,00 | 56,53 | 100,00 | 100,00 | 100,00 | 100,00 |
| target_duration_hours | 0,00 | 23,17 | 192,81 | 256,96 | 457,63 | 627,05 | 690,84 | 739,76 |
| visible_duration_hours | 0,02 | 313,48 | 1.463,94 | 2.839,48 | 3.447,90 | 7.564,11 | 11.274,71 | 25.488,23 |
| max_target_gap_hours | 0,00 | 10,62 | 64,96 | 104,49 | 160,59 | 273,49 | 347,77 | 531,89 |
| distinct_target_authors | 1,00 | 5,00 | 9,00 | 11,20 | 14,00 | 25,00 | 30,40 | 59,00 |
| largest_target_author_share | 0,06 | 0,24 | 0,33 | 0,39 | 0,49 | 0,71 | 1,00 | 1,00 |

Comparacao dos dominios completos e incompletos, sem mudar sua elegibilidade:

| Dominio | Janelas | Mediana de alvos | Duracao-alvo mediana (h) | Mediana de autores-alvo | Com proxy de entrelacamento |
| --- | --- | --- | --- | --- | --- |
| completo | 119 | 100,0 | 76,48 | 13,0 | 75,63% |
| incompleto | 198 | 20,5 | 309,90 | 6,0 | 35,35% |

235 janelas-alvo duram mais de 24 horas e 169 mais de sete dias; 20 possuem um unico autor-alvo. Sao indicadores para leitura humana, nao limiares de exclusao. Cortar por duracao ou numero de autores sem redefinir o estimando mudaria a populacao e poderia remover conversas esparsas legitimamente relevantes.

Ha sobreposicao de spans de componentes nativos distintos em 160 janelas e arestas nativas cruzadas em 134. Sao proxies observaveis de entrelacamento: componentes nativos podem fragmentar a mesma conversa semantica, e conversas reais podem nao usar replies explicitos. Ausencia do proxy nao comprova ausencia de conversas paralelas; sua presenca nao valida os rotulos semanticos.

Os componentes sao calculados com arestas nativas anteriores e visiveis; contam-se somente componentes que recebem uma aresta de fonte-alvo. Sobreposicao significa spans cronologicos intercalados; cruzamento usa pos(pai1) < pos(pai2) < pos(filho1) < pos(filho2), ou simetrico. Multiplos autores ou alta atividade sozinhos nao comprovam entrelacamento.

Uma janela operacional por contagem nao e necessariamente um episodio conversacional compacto: spans longos podem reunir trocas separadas por dias. A sobreposicao de arestas de longa duracao tambem nao comprova simultaneidade local. Portanto, nao se deve afirmar que todas as janelas sao casos uteis de entrelacamento apenas porque passaram nas restricoes tecnicas. A duracao e os silencios devem ser confrontados com leitura humana, preservando tambem casos esparsos e sem entrelacamento para avaliar a especificidade do benchmark.

### Contexto e truncamento observavel

| Status de antecedente nativo | Referencias de alvos |
| --- | --- |
| before_visible_context | 14 |
| parent_not_in_corpus | 69 |
| visible | 3.089 |

A sensibilidade abaixo mantem as mesmas fontes-alvo e varia apenas o numero de registros anteriores visiveis. O denominador de cobertura e restrito a antecedentes resolvidos, anteriores, no mesmo canal e tecnicamente ordenaveis. Nao inclui referencias ausentes do corpus, duplicadas ou de outros canais como se fossem falha de contexto.

| Registros anteriores | Referencias nativas | Resolvidas elegiveis | Visiveis | Cobertura das resolvidas |
| --- | --- | --- | --- | --- |
| 0 | 3172 | 3103 | 2935 | 94,59% |
| 50 | 3172 | 3103 | 3068 | 98,87% |
| 100 | 3172 | 3103 | 3082 | 99,32% |
| 200 | 3172 | 3103 | 3089 | 99,55% |
| 400 | 3172 | 3103 | 3093 | 99,68% |

Essa cobertura nao mede recuperacao de antecedentes semanticos desconhecidos nem determina automaticamente um contexto ideal. Aumentar contexto pode recuperar evidencia observada, mas tambem aumentar muito o custo e a duracao visivel em canais esparsos.

## 4. Ajustes necessarios e decisoes pendentes

1. **Correcoes do mecanismo:** corrigir qualquer verificacao reprovada antes de aceitar a amostra. Se todas passarem, nao ha evidencia nesta auditoria de erro de denominador, peso, cota, sobreposicao de alvos ou reproducao da semente.
2. **Estimando e pesos:** declarar se o objetivo e benchmark com cobertura entre canais, media entre canais ou media entre mensagens. Preservar as tres probabilidades e nao substituir pesos por volume bruto. Separar avaliacao do benchmark de inferencia populacional.
3. **Incerteza:** 147 meses sorteados tem uma unica janela observada apesar de multiplos blocos disponiveis. Nesse nivel nao ha replicacao para estimar diretamente a variancia dentro do mes sem suposicoes adicionais. Se intervalos design-based forem requisito, avaliar pelo menos duas janelas nos meses nao censitarios e rebalancear o orcamento antes de novo sorteio. Nao e necessario aumentar a amostra apenas para produzir um benchmark descritivo.
4. **Estratos:** manter os cortes atuais como provisao auditavel; nao adotar novos cortes apenas por parecerem mais equilibrados em volume. Comparar custo, cobertura e variacao dos resultados anotados antes de alegar eficiencia superior.
5. **Adequacao semantica:** usar o piloto humano para medir conversas simultaneas reais, antecedentes fora do contexto, ambiguidade e tempo de anotacao. Comparar blocos completos, caudas curtas e janelas de diferentes duracoes como dominios de analise, sem descarta-los antecipadamente.
6. **Elegibilidade:** a decisao sobre canais paralelos ao desenvolvimento permanece com a revisao tematica. Nao introduzir filtros por reply, autores ou duracao para resolver uma decisao de escopo.

O tamanho de Kish calculado apenas pelos pesos das mensagens e 1.813,91 para 17921 alvos. Nao e tamanho efetivo inferencial: ignora dependencia temporal, estratificacao e conglomerados. Bootstrap ingenuo de mensagens, ou de janelas sem respeitar os niveis do desenho, nao resolve a ausencia de replicacao.

## 5. Reproducao e artefatos

```powershell
python -m discord_disentanglement.sampling_audit
python -m pytest tests/test_sampling.py -q
```

A execucao recusa substituir a pasta de auditoria. Para repetir, use `--output <pasta_nova> --overwrite-report`; `--sample` permite auditar outro sorteio. `--report` permite escolher o documento gerado. Os artefatos incluem checks, probabilidades de todos os blocos, estratos, alocacao, sensibilidade dos cortes, diagnosticos de janelas, referencias nativas, sensibilidade de contexto, censo tecnico, resumo e manifesto.

Diretorio desta auditoria: `data\processed\disentanglement\sampling_participants_audit_v2`. Semente do sorteio: `20261014`. As distribuicoes por porte e por tamanho de bloco estao em `window_distribution.csv`; cada janela pode ser inspecionada por `annotation_id` em `window_diagnostics.csv` e nos artefatos originais.

**Conclusao:** probabilidades corretas e utilidade semantica sao questoes distintas. O desenho pode ser executavel e probabilistico sem que todas as janelas mostrem entrelacamento. Esta auditoria nao certifica rotulos inexistentes e nao aplica novos filtros.
