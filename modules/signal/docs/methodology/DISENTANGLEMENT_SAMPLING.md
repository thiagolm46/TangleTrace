# Amostragem para o Dataset de Conversas Desentrelaçadas

## Etapa 3: objetivo

Este documento define a etapa de amostragem para construir um dataset anotado de
conversas Discord desentrelaçadas. Ela ocorre depois da filtragem de servidores
de engenharia de software e dos canais relevantes para conversas, descritas em
[DISCORD_UNVEILED_FILTERING.md](DISCORD_UNVEILED_FILTERING.md). Seu objetivo e
selecionar intervalos em todos os canais considerados relevantes, preservando
variabilidade temporal e uma justificativa estatistica para a quantidade de
mensagens-alvo anotadas.

O objetivo nao e estimar toxicidade. A amostra deve representar, dentro dos
canais selecionados, a estrutura conversacional que sera anotada manualmente:
mensagens que respondem a antecedentes anteriores, mensagens sem resposta,
antecedentes fora do contexto e inicios de novas conversas.

A unidade anotada e a mensagem-alvo. Para cada mensagem-alvo, o anotador pode
registrar zero ou mais arestas semanticas para mensagens anteriores visiveis.
A mensagem-alvo e apresentada em uma janela continua para preservar o contexto;
essa separacao entre unidade de analise e unidade de apresentacao e essencial.

## Populacao e quadro amostral

A populacao de interesse e formada por mensagens nao-bot de canais relevantes
nos servidores selecionados. O quadro amostral deve ser congelado antes do
sorteio e conter, para cada canal:

- `guild_id`, `channel_id` e `channel_name`;
- intervalo temporal coberto pelo export;
- numero de mensagens nao-bot;
- classe do canal, escore e status de elegibilidade;
- identificadores e timestamps das mensagens em ordem cronologica.

O quadro atual mantem provisoriamente os 297 canais retidos na Etapa 2,
em 29 servidores, com pelo menos 500 registros brutos e cinco autores humanos
distintos por canal.
A inclusao de canais com conversas paralelas ao desenvolvimento de software
aguarda orientacao; nao se aplica agora uma nova restricao automatica a canais
de classe A. Canais com poucos dados nao sao considerados irrelevantes apenas
por terem baixo volume.

O cadastro separado `annotations/channel_frame_participants_v2.csv` registra
`provisional_eligible`, `eligible`, `pending_review` ou `excluded`, com motivo
em `eligibility_reason`. Os dois primeiros estados participam do piloto;
os demais permanecem na auditoria, mas nao no sorteio. Nenhuma dessas decisoes
altera o Parquet original. Antes de cada sorteio, revisar o cadastro e congelar
sua copia e hash na pasta da execucao. Uma mudanca posterior exige nova execucao,
sem substituir silenciosamente unidades da amostra anterior.

## Caracterizacao inicial dos canais mantidos

Antes de sortear janelas, execute a caracterizacao da populacao congelada:

```powershell
python -m discord_disentanglement.population
```

O padrao le `data/processed/filtering/software/participants_v2/messages.parquet`
e escreve em `data/processed/disentanglement/population_participants_v2`.
As execucoes anteriores sao somente arquivo historico.
Para outro corpus:

```powershell
python -m discord_disentanglement.population `
   --input <mensagens_mantidas.parquet> `
   --output <diretorio_novo> `
   --memory-limit 2GB
```

A rotina usa DuckDB em disco, nao altera a entrada e recusa substituir
relatorios existentes. Reserve espaco para o banco temporario e seus arquivos
de spill, que podem ser maiores que o Parquet comprimido. O limite informado
controla a memoria do DuckDB, nao toda a memoria do processo Python.

O documento detalhado [POPULATION_CHARACTERIZATION.md](POPULATION_CHARACTERIZATION.md)
e gerado a partir desses artefatos por um segundo arquivo Python executavel.
Todos os calculos adicionais, tabelas e interpretacoes numericas estao no
gerador, que verifica os hashes das entradas antes de escrever:

```powershell
python -m discord_disentanglement.population_report
```

Use `--overwrite` para regenerar explicitamente um documento existente.
O gerador aceita `--input-dir` e `--output` e cria um manifesto adjacente ao MD.

| Artefato | Conteudo |
| --- | --- |
| `channels.csv` | Volume, autores humanos distintos, cobertura temporal, dias ativos, replies e flags de qualidade por canal. |
| `servers.csv` | As mesmas medidas por servidor; autores distintos sao recalculados, nao somados entre canais. |
| `temporal_activity.csv` | Atividade mensal, por dia da semana ISO (1=segunda, 7=domingo) e hora, em UTC, por canal; separa registros totais de mensagens humanas utilizaveis. |
| `reply_distances.csv` | Replies por canal, utilizabilidade da origem e status do antecedente; quantis posicionais e temporais e contagens ate 10/100/200 registros. |
| `concentration.csv` | Canais e servidores ordenados por volume, participacao individual e acumulada; apresenta separadamente todos os registros e mensagens humanas utilizaveis. |
| `summary.json` | Totais globais, autores distintos no corpus, status dos antecedentes e quantidade de canais/servidores necessarios para atingir 80% do volume. |
| `manifest.json` | Hashes da entrada, da implementacao, do manifesto da entrada quando disponivel e dos relatorios; parametros e definicoes operacionais. |

Uma mensagem humana tem `is_bot = false`; valor ausente nao e tratado como
humano. Pela definicao `payload_v2`, nao utilizavel significa exclusivamente
registro sem texto nao vazio e sem anexo, embed ou sticker registrado. Havendo
conteudo, todos os tipos Discord sao utilizaveis nesta caracterizacao.
`usable_human_messages` exige conteudo e autor explicitamente nao-bot.
Bots com conteudo nao sao chamados de nao utilizaveis, mas ficam fora da
populacao humana. Utilizabilidade nao substitui revisao de relevancia ou
elegibilidade dos canais.

IDs ausentes, timestamps invalidos e duplicatas sao flags estruturais separadas,
nao motivos de nao utilizabilidade. A contagem
`human_messages_with_structural_issues` identifica mensagens humanas com
conteudo e algum desses problemas. Elas permanecem no volume utilizavel,
mas as distancias exigem uma base ordenavel com IDs unicos e timestamp valido.
As restricoes tecnicas do quadro amostral definitivo devem ser revisadas e
congeladas antes do sorteio de janelas.

As proporcoes de bots e registros nao utilizaveis usam todos os registros como
denominador. A proporcao de native replies e apresentada tanto nesse denominador
quanto nas mensagens humanas utilizaveis. As flags descritivas podem se
sobrepor e nao devem ser somadas para definir nao utilizabilidade:
`unusable_records` conta apenas ausencia simultanea de texto e midia.
Texto vazio sozinho nao prova mensagem ausente: mensagens com midia sao
utilizaveis. Falhas de timestamp incluem valores ausentes ou invalidos;
nao impedem utilizabilidade por conteudo, mas impedem agrupamento temporal.

Native reply significa `message_type = 19` com `referenced_message_id` nao vazio.
Referencias de outros tipos e replies sem ID do antecedente recebem contagens
separadas. A ausencia de native reply nao e evidencia de ausencia de resposta
semantica. Para cada reply com origem ordenavel, o antecedente e buscado por
servidor e ID. Sao separados `resolved`, `parent_not_found`, `different_channel`
e `not_preceding`; origens nao ordenaveis aparecem no resumo. Antecedente nao
encontrado pode estar fora do export, sem timestamp valido ou com ID duplicado;
nao demonstra que a mensagem foi apagada.

Distancias so sao calculadas para antecedentes anteriores no mesmo canal.
A distancia posicional e a posicao da origem menos a do antecedente na ordem
UTC/ID dos registros identificaveis, unicos e com timestamp valido, incluindo
bots e tipos de sistema. Uma distancia 1 indica mensagens adjacentes. Ha uma
segunda distancia posicional no quadro humano utilizavel, apenas para pares
em que ambos sao utilizaveis. A distancia temporal e dada em segundos.
As listas de quantis correspondem a 25%, 50%, 75%, 90%, 95% e 99%.
As contagens ate 10/100/200 usam a primeira ordem, nao o quadro humano.

A atividade temporal inclui somente buckets observados: meses sem registros
nao aparecem como linhas. O periodo coberto e o minimo/maximo observado, nao
uma garantia de completude do historico nem a data de criacao do canal.
Mensagens ausentes do proprio export nao podem ser quantificadas sem uma fonte
externa; a rotina mede campos ausentes, payload indisponivel e antecedentes
nao localizados no corpus.

### Definicao operacional de participantes

Usamos duas contagens explicitas:

- `distinct_human_authors`: autores distintos com pelo menos um registro
   explicitamente nao-bot, mesmo que esse registro nao seja utilizavel;
- `distinct_usable_human_authors`: autores distintos com ao menos uma mensagem
   com conteudo registrado.

A selecao usa a primeira contagem, sem exigir replies ou mencoes; a segunda
caracteriza a disponibilidade de conteudo. Nao inferimos conversas antes da
anotacao. Contamos contas humanas observadas por canal, nao pessoas verificadas.
Excluir canais com menos de 500 registros OU menos de cinco participantes
exige ambos os minimos para permanencia. A selecao, a populacao, o quadro e o
sorteio foram reexecutados em diretorios novos.

Na caracterizacao atual, 45 canais concentram pelo menos 80% das mensagens
humanas utilizaveis. Por isso, o desenho abaixo nao aloca janelas
proporcionalmente ao volume bruto do corpus. Usa cotas iguais por combinacao de
servidor e porte de canal, preservando cobertura de todos os estratos nao vazios.
A caracterizacao continua apenas descritiva; o sorteio e realizado pelo modulo
Python `discord_disentanglement.sampling`.

## Qual parametro a amostra estima

O tamanho de amostra somente tem significado depois de declarar a quantidade a
ser estimada. Para o dataset de desentrelaçamento, uma quantidade primária
adequada e:

$$
p = \Pr(\text{uma mensagem-alvo possui pelo menos uma resposta semantica})
$$

A classificacao humana considera que uma mensagem possui resposta semantica
quando recebe ao menos uma aresta humana `reply`. Os estados `no_reply`,
`outside_context`, `ambiguous` e `new_conversation` tambem devem ser contados e
publicados, pois descrevem cobertura e incerteza da anotacao.

Outras estatisticas relevantes, a serem relatadas com intervalos de confianca,
sao a taxa de multiplos antecedentes, a distancia temporal/posicional para o
antecedente, a frequencia de replies nativos e a taxa de ambiguidade. A formula
para proporcoes abaixo e apropriada para cada uma dessas medidas binarias.

## Tamanho nominal por canal

Esta secao fornece referencias sob amostragem aleatoria simples, nao determina
as cotas do piloto hierarquico. A quantidade final depende do piloto, do custo
de anotacao e da dependencia observada entre mensagens e janelas.

Para estimar uma proporcao em um canal com confianca de 95% e margem de erro
absoluta $e$, sob amostragem aleatoria simples de mensagens independentes, use:

$$
n_0 = \frac{z^2p(1-p)}{e^2}
$$

com $z = 1{,}96$. Quando a proporcao real ainda e desconhecida, use $p = 0{,}5$.
Esse e o caso conservador porque maximiza a variancia e, portanto, o tamanho
necessario.

| Margem de erro | Tamanho nominal $n_0$ a 95% |
| --- | ---: |
| $\pm 7$ pontos percentuais | 196 |
| $\pm 6$ pontos percentuais | 267 |
| $\pm 5$ pontos percentuais | 385 |

Portanto, 267 mensagens-alvo por canal e uma meta nominal defensavel para
estimar uma proporcao conversacional com 95% de confianca e erro aproximado de
$\pm6$ pontos percentuais. Tres intervalos de 100 mensagens produzem 300
mensagens-alvo e ultrapassam esse numero nominal.

Para um canal com populacao finita de $N$ mensagens nao-bot, aplique a correcao
de populacao finita antes de definir a meta:

$$
n = \left\lceil \frac{Nn_0}{N+n_0-1} \right\rceil
$$

Para $n_0 = 267$, exemplos de metas por canal sao:

| Mensagens nao-bot no canal ($N$) | Meta corrigida ($n$) |
| --- | ---: |
| 300 | 142 |
| 500 | 175 |
| 1.000 | 211 |
| 5.000 | 254 |
| Muito grande | 267 |

Se a meta corrigida for proxima do total do canal, anotar o censo do canal e
mais simples e metodologicamente superior a sortear quase todas as mensagens.

## Janelas e dependencia temporal

A formula anterior assume observacoes independentes. Mensagens consecutivas em
Discord nao sao independentes: pertencem a uma mesma conversa, evento ou grupo
de participantes. Isso e desejavel para anotacao de conversas, pois a janela
precisa preservar contexto, mas impede interpretar 300 mensagens contiguas como
300 observacoes aleatorias independentes.

Se cada janela tiver $m$ mensagens-alvo e a correlacao intraclasse aproximada
for $\rho$, uma aproximacao para o efeito de desenho e:

$$
DEFF = 1 + (m - 1)\rho
$$

O tamanho efetivo aproximado e $n_{efetivo} = n / DEFF$. Por exemplo, tres
janelas de 100 mensagens fornecem 300 mensagens-alvo, mas com $\rho = 0{,}01$
o tamanho efetivo seria aproximadamente 151; com $\rho = 0{,}02$, cerca de
101. Esses valores sao ilustrativos: $\rho$ deve ser estimado no piloto, nao
assumido como resultado do dataset.

Consequentemente, tres janelas de 100 sao uma meta operacional inicial de
cobertura, mas nao devem ser apresentadas como garantia de precisao de
$\pm6$ pontos percentuais. A precisao deve ser avaliada com estimadores
compativeis com os estratos, probabilidades e tres estagios do desenho.
Bootstrap de mensagens independentes, ou de janelas sem respeitar a hierarquia,
nao substitui replicacao nos estagios nao censitarios. A auditoria abaixo
identifica onde essa replicacao ainda falta no piloto.

## 3.2. Desenho hierarquico e estratificado executavel

O sorteio esta em `discord_disentanglement/sampling.py`; a auditoria estatistica
e de adequacao das janelas esta em `discord_disentanglement/sampling_audit.py`.
Os testes executaveis estao em `tests/test_sampling.py`. Nao ha sorteio manual
ou calculo que dependa de um comando avulso fora desses arquivos Python.

Os servidores retidos sao fixos: probabilidade 1, condicionada a este quadro.
Nao se pretende representar todos os servidores Discord. Os tres sorteios sao
aleatorios simples, sem reposicao:

1. **Canais dentro dos servidores:** estratos `guild_id x size_stratum`, com
   cota igual em cada estrato nao vazio. Porte e definido pelo volume humano
   utilizavel da caracterizacao: `small` ate 1.000, `medium` de 1.001 a 10.000,
   `large` acima de 10.000. Os limites sao parametros operacionais ajustaveis,
   nao categorias naturais inferidas dos dados. O padrao sorteia ate 2 canais
   por estrato, ou realiza censo quando houver menos.
2. **Periodos dentro dos canais:** ate 3 meses-calendario UTC distintos,
   uniformemente entre os meses com pelo menos uma mensagem-alvo valida.
   Meses sem atividade elegivel nao sao unidades do quadro. O sorteio mensal
   nao garante cobertura de cada tercil do historico.
3. **Janelas dentro dos periodos:** 1 janela por mes sorteado. Cada mes e
   particionado cronologicamente em blocos nao sobrepostos de ate 100
   mensagens-alvo. O ultimo bloco, mesmo incompleto, participa do sorteio:
   descarta-lo deixaria mensagens com probabilidade zero.

As cotas e tamanhos acima sao padroes do piloto, nao um tamanho amostral final
nem garantia de precisao estatistica. Canais sem mensagens tecnicamente validas
permanecem no cadastro com `technical_status = no_valid_targets`, sem participar
do denominador do sorteio de canais. Nao ha reposicao entre estratos.

Mensagens-alvo exigem conteudo segundo `payload_v2`, `is_bot = false`, IDs de
servidor, canal, mensagem e autor nao vazios, timestamp UTC valido e unicidade
de `(guild_id, message_id)` no corpus. Todas as ocorrencias duplicadas dessa
chave sao excluidas do quadro tecnico, nao apenas uma delas. As restricoes
tecnicas nao redefinem o volume utilizavel da caracterizacao.

Cada janela inclui ate 200 registros anteriores validos do mesmo canal como
contexto, inclusive de meses anteriores. Bots e outros registros nao alvo
entre a primeira e a ultima mensagem-alvo tambem sao preservados como contexto.
Por isso, a contagem total de contexto pode exceder 200. Contexto pode se
sobrepor entre janelas, mas nunca aumenta a contagem de mensagens-alvo.

Para um canal de um estrato com $N_h$ canais e $n_h$ sorteados, um canal com
$M_c$ meses ativos e $m_c$ sorteados, e um mes com $W_{ct}$ janelas e $w_{ct}$
sorteadas, a probabilidade marginal de uma janela e:

$$
\pi_{ctj} = \frac{n_h}{N_h}\frac{m_c}{M_c}\frac{w_{ct}}{W_{ct}},
\qquad d_{ctj} = \frac{1}{\pi_{ctj}}.
$$

Cada mensagem-alvo pertence a um unico bloco e recebe a mesma probabilidade e
peso desse bloco. Esses pesos permitem estimar totais ou razoes entre mensagens
do quadro tecnico; uma media entre canais requer estimador declarado proprio.
A incerteza deve respeitar estratos e agrupamentos, nao tratar mensagens
consecutivas como observacoes independentes. Para pertencimentos de contexto,
`target_inclusion_probability` fica ausente: nao e probabilidade de visualizacao.

### Executar e conferir

Na raiz do projeto, com o ambiente Python instalado:

```powershell
python -m discord_disentanglement.sampling prepare-frame
python -m discord_disentanglement.sampling draw
python -m pytest tests/test_sampling.py -q
```

O primeiro comando cria o cadastro separado com todos os canais como
`provisional_eligible` e recusa sobrescrita. Revise os estados e motivos nesse
CSV antes de sortear. O segundo usa os caminhos padrao da caracterizacao e
salva em `data/processed/disentanglement/sampling_participants_v2`. Uma nova execucao
exige diretorio novo; nenhum resultado anterior e sobrescrito.

Todos os parametros sao verificaveis com `--help`. Exemplo explicito:

```powershell
python -m discord_disentanglement.sampling draw `
  --frame annotations/disentanglement_channel_frame.csv `
   --output <nova_amostra> `
  --seed 20261014 `
  --channels-per-stratum 2 `
  --periods-per-channel 3 `
  --windows-per-period 1 `
  --target-messages 100 `
  --context-messages 200 `
  --memory-limit 2GB
```

| Artefato | Conferencia |
| --- | --- |
| `channel_frame.csv` | Copia exata do cadastro de elegibilidade usado. |
| `channel_selection.csv` | Todos os canais do cadastro, disponibilidade tecnica, selecao, denominadores e probabilidade do primeiro nivel. |
| `window_frame.csv` | Quadro de blocos tecnicos do Parquet, inclusive canais fora da elegibilidade atual; juntar ao cadastro para obter o quadro elegivel. |
| `period_selection.csv` | Meses candidatos nos canais sorteados, indicacao de selecao e probabilidades condicionais. |
| `selected_windows.csv` | IDs, limites temporais e posicionais, contagens, semente, tres probabilidades, produto e peso final. |
| `sampled_messages.parquet` | Registros originais por pertencimento a janela, papel contexto/alvo e probabilidades de alvo. |
| `annotation_windows.csv` | Janelas com `messages_json`, compativeis com `build-annotation-bundle`. |
| `manifest.json` | Definicoes, parametros, contagens, versoes e hashes da entrada, implementacao, cadastro e saidas. |

O DuckDB usa banco temporario em disco, removido ao terminar. O limite de memoria
nao inclui toda a memoria do Python; reserve tambem espaco para spill. O sorteio
nao usa replies nativos nem resultados de anotacao para definir fronteiras.

### Auditoria do desenho amostral

O desenho foi investigado antes de acrescentar filtros ou refazer a amostra.
O relatorio completo, gerado exclusivamente pelo arquivo Python de auditoria,
esta em [SAMPLING_DESIGN_AUDIT.md](SAMPLING_DESIGN_AUDIT.md). A execucao completa
vigente esta em `data/processed/disentanglement/sampling_participants_audit_v2`, com
manifesto e hashes de cada saida. O cadastro e o piloto original foram mantidos.

O relato dos experimentos, cenarios sinteticos, nove testes automatizados,
achados do piloto e correcoes tecnicas esta em
[SAMPLING_EXPERIMENTS.md](SAMPLING_EXPERIMENTS.md). Esse relato distingue os
testes de software das verificacoes da amostra real e explicita os limites
de cada evidencia.

As verificacoes cobrem hashes, reproducao da semente, denominadores
recalculados independentemente, positividade, cotas dos tres niveis, pesos,
unicidade e nao sobreposicao de alvos e correspondencia dos blocos com o censo
tecnico do Parquet. As 38 verificacoes passaram. Isso sustenta a implementacao
do mecanismo probabilistico, nao prova que os cortes ou cotas sao otimos.

| Questao | Evidencia do piloto | Interpretacao |
| --- | --- | --- |
| Estratos | 75 combinacoes servidor x porte; 27 censitarias no nivel dos canais; sensibilidade a metade/dobro dos cortes e tercis documentada. | Cobertura e probabilidades conhecidas, mas cortes ainda operacionais; nao substitui-los apenas por equilibrio visual. |
| Distribuicao de janelas | 275 incompletas, contra 271,00 esperadas e DP de 7,37 sob o desenho. | Resultado esperado da selecao uniforme de meses e preservacao das caudas, nao falha de sorteio. |
| Duracao | Mediana de 143,61 horas entre alvos; 283 janelas acima de 24 horas e 186 acima de sete dias. | Contagem fixa nao garante episodio conversacional compacto; requer avaliacao humana, nao corte temporal automatico. |
| Entrelacamento observavel | 162 janelas com componentes nativos intercalados; 133 com arestas nativas cruzadas. | Proxies esparsos, nao rotulos semanticos nem criterio de elegibilidade. |
| Contexto | 200 registros anteriores mostram 2.991 de 3.006 antecedentes nativos resolvidos elegiveis (99,50%); 400 mostram 2.993. | Nao ha justificativa observada para dobrar contexto automaticamente; nao mede cobertura semantica desconhecida. |
| Incerteza | 148 meses com multiplos blocos disponiveis e somente uma janela sorteada. | Falta replicacao para estimar diretamente a variancia dentro desses meses sem suposicoes adicionais. |

Os pesos sao heterogeneos. Para o total conhecido de 11.884.832 mensagens-alvo
tecnicas, a estimativa Horvitz-Thompson desta realizacao e 18.888.286, com DP
exato do desenho de 4.760.858,14. O desvio de 1,471 DP e apenas descritivo, nao
p-valor nem certificacao de ausencia de vies. A variabilidade e relevante para
inferencias; essa conta auxiliar nao estima a precisao de arestas semanticas,
toxicidade ou desempenho de modelos. O tamanho de Kish baseado apenas em pesos
tambem nao deve ser confundido com tamanho efetivo apos conglomeracao temporal.

**Decisoes nesta etapa:** nao excluir caudas curtas, canais esparsos, janelas
longas ou casos sem reply nativo. Nao trocar os cortes de porte, aumentar
contexto ou refazer o sorteio automaticamente. Declarar o estimando e a forma
de ponderacao; se inferencia design-based com intervalos for requisito, rever
a replicacao de janelas por mes e o orcamento antes de uma nova rodada.
A adequacao semantica permanece pendente do piloto humano, incluindo casos
completos/incompletos e diferentes duracoes, sem remover os casos negativos.

Para reproduzir em nova pasta e regenerar explicitamente o documento:

```powershell
python -m discord_disentanglement.sampling_audit `
   --output <nova_auditoria> `
   --overwrite-report
python -m pytest tests/test_sampling.py -q
```

O gerador recusa substituir diretorios de auditoria e verifica os hashes do
piloto antes de calcular. As saidas detalham probabilidades de todo o quadro,
alocacao por servidor/canal/porte/mes, sensibilidade dos cortes, duracao e autores
por janela, componentes e arestas nativas observadas, antecedentes nao visiveis,
sensibilidade de contexto e variancia exata de totais auxiliares conhecidos.

## Relacao com a ferramenta de anotacao

O comando `discord-prepare draw` sorteia as janelas probabilisticas do desenho
atual. Os padroes sao blocos de ate 100 alvos e ate 200 registros anteriores
de contexto; registros intervenientes tambem sao preservados. Apenas os alvos
recebem tarefa de anotacao. Replies nativos nao determinam as fronteiras.

```powershell
discord-prepare draw `
  --input <mensagens.parquet> `
   --frame <quadro_revisado.csv> `
  --output <diretorio_de_janelas> `
   --target-messages 100 `
   --context-messages 200

discord-prepare build-annotation-bundle `
   --annotation-windows <diretorio_de_janelas>/annotation_windows.csv `
   --output <novo_bundle>
```

A selecao e suas probabilidades ficam registradas antes da anotacao. O
enumerador legado `gold-standard`, que nao fazia sorteio probabilistico,
foi removido junto com o executor de experimentos. As janelas da amostra atual
nao foram redesenhadas durante essa limpeza.

## Piloto, recalibracao e relato

Antes da coleta final, anote um piloto temporalmente estratificado. O piloto
deve estimar: proporcao de mensagens com aresta semantica, taxa de ambiguidade,
taxa de antecedentes fora do contexto, distribuicao do tamanho das conversas e
correlacao entre mensagens de uma mesma janela. Esses resultados permitem
recalcular o tamanho de amostra com uma estimativa de $p$ menos conservadora e
um efeito de desenho observado.

O relatorio final deve informar o canal, seu tamanho populacional $N$, classe,
periodo coberto, meta nominal, correcao finita, numero de janelas, mensagens
alvo anotadas, mensagens de contexto, distribuicao temporal, criterios de
substituicao e taxa de conclusao. Para estimativas agregadas entre mensagens,
use os pesos inversos das probabilidades efetivas do desenho, nao apenas pesos
proporcionais ao tamanho do canal. Declare separadamente estimadores de medias
entre canais e de medias entre mensagens, alem do tratamento da nao resposta.

O resultado esperado e um dataset com contexto suficiente para anotar arestas
semanticas e com justificativa estatistica transparente para a quantidade e a
distribuicao das mensagens classificadas.

## Etapa 4: codebook e classificacao piloto

Depois de selecionar os intervalos, a proxima etapa define e calibra o
codebook por meio de classificacao piloto. O piloto verifica se as regras para
`reply`, `no_reply`, `outside_context`, `ambiguous` e `new_conversation` sao
aplicaveis de forma consistente antes da anotacao em escala. Consulte
[ANNOTATION_CODEBOOK.md](ANNOTATION_CODEBOOK.md) para a unidade de anotacao,
os estados de decisao e o protocolo de revisao.
