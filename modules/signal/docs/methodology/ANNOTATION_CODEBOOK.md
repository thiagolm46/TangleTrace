# Codebook de anotação conversacional

**Versão:** 1.3  
**Unidade de anotação:** janela contínua de um canal Discord

**Estado do corpus de referência:** nenhuma anotação humana foi realizada.
As regras abaixo especificam o protocolo para as sessões futuras; não são
resultados de uma sessão executada nem confirmação independente das funções
do aplicativo.

A preparação e a construção do bundle estão implementadas no código disponível.
Importação, confirmação, persistência de decisões, adjudicação e exportação pelo
desktop são requisitos especificados aqui; sua implementação e operação não
foram estabelecidas pela evidência examinada. Em particular, a convenção
estruturada de candidatos abaixo não implica transferência automática já
implementada no aplicativo. O protocolo deve ser avaliado em piloto.

## 1. Estrutura de dados

O arquivo de janelas da execução, `annotation_windows.csv`, é o artefato de
preparação. Antes da anotação, ele deve ser achatado com
`build-annotation-bundle` em quatro tabelas Parquet: mensagens, participações
nas janelas, arestas humanas e estados das fontes.

### `messages.parquet`

Cada linha é uma mensagem canônica do servidor. `message_id` é único e `content`
aparece uma única vez, junto de seus metadados nativos.

```text
message_id, server_id, channel_id, author_id, timestamp, content,
native_reply_to, mentions, message_type, reaction_count, has_attachment, is_bot
```

O arquivo inclui também os metadados nativos preservados, como reactions,
attachments, embeds, thread, webhook, flags e payload de origem.

### `sample_messages.parquet`

Cada linha registra a participação de uma mensagem em uma janela de anotação:

```text
sample_id, message_id, is_context, sequence
```

Uma mensagem pode aparecer em várias amostras porque o contexto de uma janela
pode sobrepor o trecho anotado da próxima. A chave é `(sample_id, message_id)`.
`is_context=true` indica registros visíveis não alvo, anteriores ou intervenientes;
`is_context=false` indica trecho alvo. Uma mensagem alvo de uma janela pode ser
contexto em outra: o papel pertence à participação, não à mensagem canônica.
Para obter uma amostra completa, faça a junção por `message_id` entre esta tabela
e `messages.parquet`.

### `annotations.parquet`

Cada linha é uma aresta humana dirigida. A mesma `source_message_id` pode
aparecer em diversas linhas dentro de uma `sample_id`.

```text
sample_id, source_message_id, target_message_id, annotator_id, relation,
ambiguous, confidence, notes
```

`relation=reply` é a relação primária. O grafo aceito contém somente arestas
confirmadas, não ambíguas, de fontes `complete`. O campo `ambiguous` preservado
no esquema não torna um registro incerto uma aresta aceita. No protocolo
revisado, candidatos de decisões irresolvidas pertencem ao registro estruturado
da fonte, descrito na seção 4.1, e não à tabela de arestas aceitas.

### `source_statuses.parquet`

Esta quarta tabela é necessária para decisões humanas sem aresta. Cada fonte
do trecho alvo possui uma linha com `source_status`; assim, a ausência de uma
linha em `annotations.parquet` nunca significa `no_reply`.

Somente participações com `is_context=false` exigem decisão. Toda mensagem
anterior visível, inclusive `is_context=true`, é um antecedente elegível.

## 2. Evidência nativa do Discord

`native_reply_to_message_id` preserva a referência explícita da plataforma.

| Situação | Interpretação obrigatória |
|---|---|
| `native_reply_to_message_id != null` | evidência positiva observada de uma aresta nativa `(source, target)` |
| `native_reply_to_message_id == null` | relação sem observação nativa; não é negativa, não é `no_reply` e não inicia uma conversa |

Em particular, a ausência de reply nativo nunca deve gerar um par negativo,
excluir um pai semântico ou separar uma conversa. `native_reply_evidence` usa
somente `positive_observed` e `unknown` por esse motivo.

As arestas em `native_reply_edges_json` são evidência silver parcial. Elas não
limitam as anotações humanas: uma mensagem sem reply nativo pode receber um pai
semântico anotado.

Exemplo: se apenas `M5` cita `M1` explicitamente, a anotação pode registrar
`M2 -> M1`, `M3 -> M1`, `M4 -> M1` e `M5 -> M1` quando o conteúdo sustentar
essas relações.

## 3. Preservação de metadados

O silver preserva identificadores, canal/servidor, autor, timestamps original e
de edição, conteúdo, tipo de mensagem, replies nativos, menções, reactions,
attachments, embeds, stickers, roles mencionados, flags, estado de bot/webhook,
fixação e thread nativa. `native_fields_json` retém campos adicionais da origem.
`native_available_fields` identifica quais campos estavam presentes na origem de
cada mensagem: um campo ausente da origem não deve ser interpretado como uma
lista vazia, valor falso ou evidência negativa.

Esses campos são evidência de anotação e material para estudo posterior. Nenhum
campo vira feature, gold ou label negativo automaticamente.

## 4. Arestas humanas primárias

O anotador não atribui `conversation_id` e não preenche um pai singular. A
unidade primária é uma linha de `annotations.parquet`. A mesma fonte pode
aparecer em uma ou mais arestas:

```json
[
  {
    "source_message_id": "M20",
    "target_message_id": "M17",
    "target_location": "context"
  },
  {
    "source_message_id": "M20",
    "target_message_id": "M18",
    "target_location": "annotated"
  }
]
```

Cada aresta aceita afirma que o ato comunicativo da fonte responde diretamente
ou dá continuidade à contribuição do antecedente, com apoio no conteúdo e no
contexto visível. Tema, adjacência, autoria comum, menção ou reply nativo não
bastam isoladamente. Uma continuação do mesmo autor exige dependência da
contribuição anterior. Múltiplas arestas aceitas são conjunção: a fonte responde
a todos os antecedentes, não a um candidato indeterminado entre eles.

A fonte deve estar no trecho `annotated`; o antecedente deve ser visível e
anterior na mesma janela e no mesmo canal. A identidade usa a chave
`(server_id, message_id)`, sem presumir unicidade entre servidores. A ordem é
timestamp UTC seguido de `message_id` como desempate determinístico. Em um
empate, essa ordem permite uma direção e impede a outra por convenção, não por
evidência de criação. O ID pseudonimizado não reconstrói cronologia; se a direção
for incerta, registre a incerteza, sem deduzi-la do desempate. Não se aceitam
self-links. O papel de contexto ou alvo é determinado por `is_context` na
participação em `sample_messages.parquet`.

Uma recontagem direta dos artefatos preservados encontrou 184 grupos de empate
no mesmo canal, envolvendo 368 mensagens elegíveis da população. Nas tarefas
amostradas, existe apenas um par empatado, composto por mensagens de contexto;
nenhum alvo compartilha timestamp com outra mensagem visível na sua janela.
Assim, o desempate não restringiu as escolhas de antecedentes dos alvos da
amostra realizada. Isso não demonstra que o ID represente a ordem real.

`source_statuses.parquet` contém uma decisão para cada fonte do trecho alvo,
mas não uma relação pai-filho. Valores permitidos em `source_status`:

- `pending`: nenhuma decisão foi confirmada; seleções em rascunho não são
  arestas aceitas, e rascunho vazio não significa ausência de resposta.
- `complete`: pelo menos um antecedente visível foi confirmado e a avaliação
  da fonte foi concluída, sem alternativas ou relações necessárias pendentes.
- `no_reply`: a inspeção não sustenta uma relação de resposta nem fornece
  evidência específica de dependência irresolvida, e não há evidência positiva
  de abertura explícita de tópico. A decisão diz respeito às mensagens
  anteriores, não à ausência de respostas posteriores; ela não certifica que
  inexista um antecedente fora da janela.
- `outside_context`: a evidência visível sustenta dependência de uma contribuição
  anterior indisponível. Exige nota com essa evidência; mera possibilidade de
  contexto ausente não basta, e nenhum ID externo é inventado.
- `ambiguous`: há evidência específica de uma decisão relacional irresolvida,
  como candidatos concorrentes ou interpretação insuficiente de uma expressão
  dependente de resposta. Exige justificativa e registro dos candidatos
  conhecidos; estes não entram no grafo aceito.
- `new_conversation`: há evidência positiva de abertura independente de tópico,
  em vez de resposta a uma contribuição anterior. É uma decisão sem aresta mais
  específica que `no_reply`; não cria self-link nem implica isolamento futuro.

Os seis estados são mutuamente exclusivos por fonte. Somente `complete` admite
arestas aceitas, sempre não ambíguas. Os demais estados não geram arestas aceitas;
fontes sem antecedente não podem ser confirmadas como `complete`.
Quando um vínculo é defensável, mas outro vínculo necessário continua incerto
ou externo, a fonte permanece `ambiguous` ou `outside_context`, respectivamente.
O grafo é conservador no nível da fonte: uma relação individual defensável pode
ficar de fora quando a avaliação completa de antecedentes continua irresolvida.
Sua ausência não é um julgamento negativo sobre essa relação. Mídia inacessível
que impede interpretação relacional exige registrar incerteza, não inferir seu
conteúdo.

A fronteira entre os estados depende da evidência, não apenas da ausência de
um antecedente selecionado. Para uma confirmação curta como "ok", evidência
de dependência com antecedente não identificado requer `ambiguous`; evidência
específica de dependência anterior externa requer `outside_context`. A falta
de seleção, isoladamente, não estabelece nenhum desses estados. `no_reply`
exige ausência de suporte à relação e de indício específico de dependência
irresolvida.

### 4.1. Ciclo de vida e candidatos preservados

Rascunhos são exclusivamente trabalho não confirmado. Pelo procedimento
especificado, confirmar uma disposição requer gravar o estado da fonte, os
candidatos e a justificativa em um registro durável antes de encerrar o
rascunho de trabalho. Candidatos são informação de suporte separada de
arestas aceitas; uma relação defensável não deve ser confundida com uma
mera alternativa.

O esquema atual de `source_statuses.parquet` possui `notes`, mas não campos
próprios para candidatos. Sem alterar esse esquema, o protocolo especifica um
objeto JSON no campo `notes`, com `candidates` e `rationale`. Cada candidato
possui `message_id` e `evidence_class`, com valores `defensible` ou `alternative`.
Uma dependência externa é descrita na justificativa, sem inventar seu ID.
A estrutura abaixo é uma convenção especificada, não uma saída observada:

```json
{
  "candidates": [
    {"message_id": "M17", "evidence_class": "defensible"}
  ],
  "rationale": "Há um vínculo visível defensável e evidência específica de outra dependência anterior externa."
}
```

Uma fonte `outside_context` pode, assim, conservar o candidato visível no
registro confirmado sem admiti-lo no grafo aceito. A exportação conforme o
protocolo deve preservar estado e conteúdo JSON de `notes`, e identificar
fonte, janela e anotador. Não há evidência aqui de que o desktop faça a
transferência ou a serialização automaticamente. Uma implementação deve
demonstrar essa preservação na confirmação e na exportação antes de declarar
conformidade. O publicador de datasets de preparação copia as tabelas recebidas;
isso não comprova o ciclo de confirmação do desktop.

Confirmar requer estado explícito e cumprimento das restrições de fonte, canal,
ordem e evidência; disposições externas ou incertas exigem justificativa.
Revisar a janela requer uma disposição confirmada para cada alvo, ausência de
rascunhos de trabalho não confirmados e inspeção das arestas e estados.
Candidatos preservados em registros confirmados não são rascunhos pendentes.
Uma disposição externa ou ambígua pode estar revisada e continuar
semanticamente irresolvida. Essa revisão não certifica suficiência de contexto,
correção ou concordância entre anotadores. A adjudicação é especificada como
uma camada separada, com revisor e sessões de origem, preservando as decisões
independentes.

## 5. Agrupamento conversacional

A derivação de componentes é posterior à anotação. Ela não integra o executável
atual de preparação e não foi realizada sobre rótulos humanos do experimento.
Não há treinamento ou inferência nesta etapa. A implementação futura deve
versionar a regra de derivação junto dos dados anotados.

Para inspeção local, o grafo de uma janela contém todas as suas mensagens
visíveis e somente as arestas humanas aceitas, conforme a seção anterior.
Os componentes são fracamente conexos: ignora-se a direção das arestas.
Evidência nativa, rascunhos e candidatos incertos não acrescentam arestas.
Para as arestas
`M10 -> M4`, `M11 -> M4`, `M12 -> M7`, `M13 -> M10` e `M13 -> M11`, as mensagens
`M4`, `M10`, `M11` e `M13` pertencem ao mesmo componente; `M7` e `M12` pertencem
a outro. Acrescentar uma resposta confirmada ligada aos dois componentes os
funde: a regra produz uma partição do grafo, não pertencimentos sobrepostos.

Mensagens de contexto não são fontes de anotação; portanto, relações entre elas
podem estar ausentes. Dois alvos ligados a contextos diferentes podem aparecer
separados mesmo quando uma relação não observada uniria suas conversas.
Relações além das bordas e continuações posteriores também podem faltar.
Assim, os componentes são apoio local à inspeção, não fronteiras completas de
conversas. Um vértice isolado não é automaticamente uma conversa singleton
confirmada. Inícios explicitamente julgados permanecem distinguíveis.

Os componentes são locais à janela, sem consolidação automática entre janelas
sobrepostas. A revisão é especificada como inspeção; alterar um agrupamento
requer revisar as decisões subjacentes e derivar novamente o grafo.

## 6. Regras iniciais de decisão

| Caso | Decisão |
|---|---|
| Reply explícito nativo | Forte evidência positiva; revisar e registrar a aresta humana quando semanticamente compatível. |
| `@menção` | Evidência de destinatário, não antecedente automático. |
| Resposta sem menção ou reply nativo | Permitir aresta semântica quando conteúdo e contexto a sustentarem. |
| Várias respostas para uma mensagem | Todas podem apontar para o mesmo antecedente. |
| Mensagem respondendo várias anteriores | Registrar uma linha `reply` por antecedente. |
| Início claro de tópico | Marcar `source_status=new_conversation`; não criar self-link manualmente. |
| Continuação do próprio autor | Examinar conteúdo e contexto; mesma autoria não é ligação automática. |
| "sim", "não", "obrigado" | Procurar antecedente no contexto; não assumir a mensagem imediatamente anterior. |
| Antecedente anterior ao trecho alvo | Buscar no contexto; usar `outside_context` apenas com evidência específica de dependência externa. |
| Sem suporte à resposta, dependência irresolvida ou abertura explícita | Usar `no_reply`, sem afirmar que inexiste contexto não observado. |
| Evidência de dependência de antecedente indisponível | Usar `outside_context` e justificar em nota; não inventar o ID. |
| Alternativas ou interpretação irresolvidas | Usar `source_status=ambiguous`; candidatos retidos são incertos, não arestas aceitas. |

## 7. Piloto e revisão

Nenhuma rodada de anotação foi realizada. Antes da anotação em escala, executar
três rodadas piloto. Após cada rodada,
comparar discordâncias, registrar decisões de consenso e acrescentar exemplos
anônimos de casos difíceis ao codebook. Casos prioritários: perguntas repetidas,
múltiplos antecedentes, interjeições, respostas curtas, respostas sem menção e
fronteiras entre tópicos.

## 8. Revisão e privacidade

Registre identidade do anotador, data, ambiguidade e observações no registro da
janela. Conteúdo bruto e payloads de mensagens permanecem nos artefatos locais
ignorados pelo Git; não devem ser copiados para planilhas ou documentos
versionados.