# Curadoria do Discord Unveiled para Engenharia de Software

## Escopo Atual

Este repositorio demonstra a preparacao de dados de comunidades de Engenharia
de Software. Nao executa modelos de disentanglement nem um fluxo de pesquisa
de comunidades de jogos. Mencoes a jogos ou cripto em perfis de software sao
evidencias de exclusao ou de especializacao, nao outra pipeline.

## Etapa 1: Servidores

O scoring de metadados e a revisao humana selecionaram 31 servidores. O perfil
[software.engineering.v2.json](../../configs/filtering/software.engineering.v2.json)
e dedicado a servidores e nao tem politica de scoring de canais. Os perfis
de software anteriores permanecem como configuracoes de suporte e proveniencia,
nao como resultados de pesquisa independentes.

O registro vigente, as limitacoes da revisao e os artefatos estao em
[SERVER_FILTERING_STAGE.md](SERVER_FILTERING_STAGE.md).

## Etapa 2: Canais

A selecao vigente exige pelo menos 500 registros brutos e cinco autores humanos
distintos por canal, alem de nome fora da lista manual. Ela recalcula as duas
contagens diretamente da fonte original, sem exigir replies ou mencoes e sem
inferir conversas. Excluir quando qualquer um dos minimos nao for alcancado
equivale a usar OR nos criterios de exclusao.

O corpus `participants_v2` contem 297 canais, 29 servidores e 11.897.859
registros. Nao foi produzido pelo scoring generico A-D. Os limiares sao
operacionais, nao calibrados como garantia de relevancia. As razoes individuais
da lista manual herdada continuam nao registradas.

Procedimento e comandos: [CHANNEL_SELECTION_STAGE.md](CHANNEL_SELECTION_STAGE.md).
O schema dos perfis reutilizados esta em
[FILTER_PROFILE_REFERENCE.md](FILTER_PROFILE_REFERENCE.md).

## Etapas Seguintes

Caracterizacao, amostragem probabilistica e auditoria:
[DISENTANGLEMENT_SAMPLING.md](DISENTANGLEMENT_SAMPLING.md).
Preparacao e calibracao da anotacao: [ANNOTATION_CODEBOOK.md](ANNOTATION_CODEBOOK.md).
Visao completa: [DISENTANGLEMENT_DATASET_PIPELINE.md](DISENTANGLEMENT_DATASET_PIPELINE.md).