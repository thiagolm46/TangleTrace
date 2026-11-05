# Pipeline de Dados de Engenharia de Software

## Escopo

O pipeline atual prepara mensagens Discord para futura anotacao humana de
relacoes de resposta. A pesquisa de jogos, os modelos de disentanglement,
treinamento e avaliacao de desempenho nao fazem parte desta etapa. O nome
interno do pacote e mantido para preservar os registros de proveniencia.

## 1. Selecionar Servidores

O perfil de scoring [software.engineering.v2.json](../../configs/filtering/software.engineering.v2.json)
produz evidencia por metadados para apoiar revisao humana; afinidade nao e
probabilidade de pertinencia. A execucao atual reteve 31 servidores.

Registro: [SERVER_FILTERING_STAGE.md](SERVER_FILTERING_STAGE.md).

## 2. Selecionar Canais

O filtro combina a lista manual com exclusao por
`total_messages < 500 OR distinct_human_authors < 5`. O resultado e de 297
canais, 29 servidores e 11.897.859 registros. O scoring A-D disponivel no motor
nao produziu esse corpus e nao e uma etapa adicional obrigatoria.

As duas contagens sao calculadas diretamente das mensagens originais.
Participantes sao IDs distintos de autores explicitamente nao-bot, sem condicao
de reply ou mencao. As execucoes anteriores sao somente arquivo historico.

Registro: [CHANNEL_SELECTION_STAGE.md](CHANNEL_SELECTION_STAGE.md).

## 3. Caracterizar, Sortear e Auditar

`discord-prepare population` descreve volumes, autores, cobertura temporal,
replies, antecedentes, ausencia de conteudo e concentracao. A definicao atual
de nao utilizavel e exclusivamente ausencia simultanea de texto e midia.

`prepare-frame` cria um cadastro separado para revisar elegibilidade. `draw`
sorteia canais por servidor/porte, meses dentro dos canais e blocos dentro
dos meses, sem reposicao. Preserva probabilidades, pesos, semente, contexto
anterior e registros intervenientes; nao infere conversas nem usa predicoes.

`audit-sampling` verifica os artefatos congelados, sem filtrar ou substituir
janelas. A execucao vigente e `sampling_participants_v2`, com auditoria
`sampling_participants_audit_v2`. O sorteio piloto produziu 107 canais, 317 janelas
e 17.921 alvos. Testes e auditoria de probabilidades nao demonstram, por si,
adequacao semantica ou acordo entre anotadores.

Registros: [DISENTANGLEMENT_SAMPLING.md](DISENTANGLEMENT_SAMPLING.md),
[POPULATION_CHARACTERIZATION.md](POPULATION_CHARACTERIZATION.md),
[SAMPLING_DESIGN_AUDIT.md](SAMPLING_DESIGN_AUDIT.md) e
[SAMPLING_EXPERIMENTS.md](SAMPLING_EXPERIMENTS.md).

## 4. Preparar e Calibrar a Anotacao

`build-annotation-bundle` transforma as janelas sorteadas em tabelas de
mensagens, pertencimentos, arestas humanas e estados das fontes.
`publish-annotation-dataset` reune os insumos de anotacao em um diretorio
autocontido, com manifesto e codebook. Nenhuma anotacao humana e inventada.

O codebook ainda deve ser calibrado por anotadores. Native replies sao silver
positivo observado, nao ground truth semantico; ausencia de reply nao e
evidencia negativa. Modelos e avaliacao so serao reconsiderados quando os dados
e rotulos estiverem prontos e versionados.

Registro: [ANNOTATION_CODEBOOK.md](ANNOTATION_CODEBOOK.md).

## Reproducibilidade e Limpeza

As fontes, manifestos e snapshots que sustentam o resultado atual permanecem
preservados. `scripts/cleanup_legacy.py` registra a remocao de resultados
obsoletos sem tocar no corpus, na amostra atual ou na auditoria vigente.
O historico Git permite consultar o codigo experimental removido; ele nao e
uma dependencia para executar as etapas acima.