# Etapa 2: Selecao por Volume e Participantes

## Regra Vigente

Manter um canal somente quando satisfaz simultaneamente:

- pelo menos **500 registros de mensagens** no canal;
- pelo menos **5 autores humanos distintos**;
- nome fora da lista manual de exclusao.

Equivalente: excluir quando `total_messages < 500 OR distinct_human_authors < 5`,
ou quando houver correspondencia na lista manual. Os limites sao inclusivos
para permanencia: 500 mensagens e 5 autores passam. A unidade e o par
`(guild_id, channel_id)`, nao uma conversa inferida.

Nao se usa contador de autores condicionado a replies, mencoes ou eventos de
interacao. As execucoes anteriores sao apenas arquivo historico e nao fornecem
estatisticas nem decisoes para esta versao.

## Definicoes Operacionais

`total_messages` conta todas as linhas exportadas do canal, antes de filtrar
por conteudo ou tipo de autor. Nao e contagem deduplicada de mensagens nem
quantidade de mensagens anotaveis. A qualidade estrutural e verificada nas
etapas seguintes.

`distinct_human_authors` conta os valores distintos de `author_id`, convertidos
para texto e sem espacos nas extremidades, entre registros com `is_bot = false`.
IDs nulos/vazios sao ignorados. Bot e status de bot ausente nao sao presumidos
humanos. Cada ID conta uma vez por canal, independentemente do numero de
mensagens, do tipo Discord, da disponibilidade de conteudo ou de replies/mencoes.
Contamos contas/IDs observados, nao identidades civis verificadas.

A lista manual usa linhas UTF-8 nao vazias com espacos externos removidos e
correspondencia exata de `channel_name`, sensivel a maiusculas. Um nome igual
em varios servidores exclui todos os canais correspondentes. A lista herdada
nao preserva razoes individuais; essa limitacao permanece declarada.

500/5 sao requisitos operacionais de volume e participacao, nao limiares
estatisticamente calibrados de relevancia, qualidade conversacional ou
representatividade. Cumpri-los nao demonstra conversa semantica nem pertinencia
de todas as mensagens a Engenharia de Software.

## Implementacao e Reproducao

O codigo e os calculos estao em
[channel_selection.py](../../discord_filtering/channel_selection.py).
Ele calcula as estatisticas diretamente da fonte de mensagens original; nao
le a tabela de estatisticas usada pelas execucoes anteriores.

```powershell
python -m discord_filtering.channel_selection select
python -m discord_filtering.channel_selection verify
```

A fonte e `data/processed/filtering/software/affinity_v2/messages_2026-09-21.parquet`.
As exclusoes sao lidas de `canais_a_excluir.txt`, no mesmo diretorio.
O destino vigente e `data/processed/filtering/software/participants_v2`.
Para repetir, use `--output <novo_diretorio>`; o comando recusa substituir uma
execucao existente. `--source`, `--exclusions`, `--minimum-messages`,
`--minimum-human-authors` e `--memory-limit` sao parametros explicitos.

| Arquivo | Funcao |
| --- | --- |
| `messages.parquet` | Todas as linhas dos canais retidos, com o schema da fonte. |
| `channel_statistics.parquet` | Volume bruto e autores humanos distintos de todos os canais da fonte. |
| `decisions.csv` | Estatisticas, flags de exclusao por cada minimo, exclusao manual, decisao e motivo operacional. |
| `exclusions.txt` | Copia exata da lista aplicada. |
| `manifest.json` | Versao `participants_min500_min5.v2`, parametros, definicoes, limitacoes, contagens e hashes. |
| `messages.parquet.manifest.json` | Mesmo manifesto junto ao corpus para rastrear as etapas seguintes. |

A publicacao usa diretorio temporario e recusa sobrescrita. Antes de concluir,
a implementacao recalcula volume e autores no Parquet de saida e exige
igualdade com os canais selecionados. `verify` confere os hashes, repete as
decisoes sobre as estatisticas preservadas e reconta o corpus publicado.
Uma reproducao integral parte da fonte e executa `select` em outro diretorio.

## Resultado da Reexecucao

As contagens abaixo foram calculadas pela implementacao Python:

| Medida | Quantidade |
| --- | ---: |
| Servidores na fonte | 31 |
| Canais na fonte | 689 |
| Registros na fonte | 13.275.074 |
| Canais na lista manual | 66 |
| Canais abaixo de 500 mensagens | 335 |
| Canais abaixo de 5 autores humanos | 177 |
| Canais abaixo de pelo menos um minimo | 335 |
| Sobreposicao entre lista manual e criterio de atividade | 9 |
| Canais excluidos pela uniao | 392 |
| Canais mantidos | 297 |
| Servidores com canais mantidos | 29 |
| Registros removidos | 1.377.215 |
| Registros mantidos | 11.897.859 |

As flags podem se sobrepor. Nenhum canal mantido tem volume bruto abaixo de
500 ou menos de cinco participantes humanos. Mensagens utilizaveis por
conteudo sao contadas separadamente na caracterizacao.

## Etapas Dependentes

A populacao foi recalculada em `population_participants_v2`; o quadro separado
e [channel_frame_participants_v2.csv](../../annotations/channel_frame_participants_v2.csv).
O sorteio em `sampling_participants_v2` usou semente 20261014 e o desenho
hierarquico declarado, produzindo 107 canais, 317 janelas e 17.921 alvos.
`sampling_participants_audit_v2` passou nas 38 verificacoes independentes.
Execucoes anteriores nao foram sobrescritas nem usadas como quadro atual.

Veja [POPULATION_CHARACTERIZATION.md](POPULATION_CHARACTERIZATION.md),
[DISENTANGLEMENT_SAMPLING.md](DISENTANGLEMENT_SAMPLING.md) e
[SAMPLING_DESIGN_AUDIT.md](SAMPLING_DESIGN_AUDIT.md).