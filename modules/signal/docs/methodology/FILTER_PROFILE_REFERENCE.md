# Referencia de Perfis de Filtragem

## Proposito

Este documento descreve os perfis JSON de software utilizados pelo modulo `discord_filtering`, seus schemas e regras de versionamento.

O motor nao contem keywords de dominio. Ele recebe registros, aplica regras declaradas no perfil e preserva a evidencia responsavel por cada escore. Um escore e um indice de evidencia definido pelo perfil; nao e uma probabilidade, nem um rotulo binario por si so.

| Schema | Finalidade | Selecao de servidores | Canais |
| --- | --- | --- | --- |
| `1` | Selecionar servidores e pontuar canais. | Definida no perfil. | Obrigatorios. |
| `2` | Pontuar todos os servidores e estudar a distribuicao. | Nao definida. | Nao definidos. |

Use o schema `2` para a etapa exploratoria: congele regras e pesos, pontue todo o corpus, inspecione distribuicao e amostras, e so depois defina um cutoff. Use o schema `1` quando os limiares de selecao e a politica de canais ja estiverem justificados.

O validador e estrito: chaves obrigatorias nao podem faltar, e chaves desconhecidas sao rejeitadas. A implementacao de referencia esta em [`profile.py`](../../discord_filtering/profile.py); exemplos concretos ficam em [`configs/filtering`](../../configs/filtering).

## Convencoes Gerais

Todo perfil possui estas chaves na raiz:

| Campo | Tipo | Regra |
| --- | --- | --- |
| `schema_version` | inteiro | `1` ou `2`. |
| `profile_id` | string | Identificador estavel: inicia por letra minuscula e aceita letras, numeros, `.`, `_` e `-`. |
| `profile_version` | string | Versao da funcao de scoring, por exemplo `1.0.0`. Incremente-a quando regras, pesos, campos ou limiares mudarem. |
| `domain` | string | Identificador curto do dominio analisado. |
| `description` | string | Descricao metodologica do construto e do uso previsto. |
| `server` | objeto | Politica para metadados de servidor. |
| `channel` | objeto | Obrigatorio somente no schema `1`. |

Os textos sao normalizados com Unicode NFKC. As expressoes regulares usam `re.IGNORECASE` e `re.UNICODE`. Valores nulos, vazios, `NA`, `N/A` e `null` nao contam como evidencia. `keywords` pode ser string ou lista; outros campos tambem podem ser listas, cujos itens sao examinados separadamente.

Cada regra positiva ou negativa tem esta estrutura:

```json
{
  "id": "source-code",
  "label": "source code",
  "pattern": "\\bsource code\\b",
  "weight": 3,
  "group": "domain-artifact"
}
```

| Campo | Uso |
| --- | --- |
| `id` | Identificador unico na lista de regras. |
| `label` | Nome legivel que aparece na auditoria e pode ser referenciado por selecao. |
| `pattern` | Expressao regular Python. Em JSON, barras invertidas devem ser escapadas: `\\b`, nao `\b`. |
| `weight` | Numero positivo que representa a forca semantica da regra. |
| `group` | Identificador semantico usado para limitar sobreposicao. |

Agrupe sinonomos e variacoes da mesma evidencia. Por exemplo, linguagens de programacao podem compartilhar `programming-language`. Mantenha grupos distintos para intencao explicita, pratica, artefato e tecnologia quando essas evidencias tiverem significados metodologicos diferentes.

## Calculo do Score de Servidor

Para uma ocorrencia da regra $r$ no campo $f$, o peso preliminar e:

$$
w_{r,f} = w_r \times w_f
$$

onde $w_r$ e o peso da regra e $w_f$ e o peso do campo. O motor registra uma ocorrencia por regra em cada valor de campo; repeticoes da mesma palavra em um unico texto nao acumulam escore.

Com `"overlap_policy": "max_per_group"`, apenas o maior peso preliminar em cada grupo recebe credito. Outras ocorrencias ficam no campo de auditoria com `credited_weight: 0`, sem inflar o resultado.

No schema `2`, confirmacoes em campos diferentes podem acrescentar credito limitado ao mesmo grupo. A evidencia principal continua sendo o maior peso do grupo; cada campo adicional recebe um bonus, limitado por um teto do grupo.

As regras positivas e negativas sao calculadas separadamente:

$$
P = \sum_g P_g
$$

$$
N = \sum_g N_g
$$

$$
A = P - N
$$

`P` e evidencia a favor do dominio, `N` e evidencia de proposito concorrente, e `A` e a afinidade liquida. Analise os tres valores: dois servidores podem ter o mesmo $A$ com composicoes muito diferentes.

## Schema 2: Scoring Sem Selecao

O schema `2` serve para caracterizar todos os servidores antes de definir um cutoff. Ele nao aceita `selection` nem `channel`.

### Chaves de `server`

| Campo | Tipo | Regra |
| --- | --- | --- |
| `fields` | lista de strings | Campos de entrada pesquisados; nao pode ser vazia. |
| `field_weights` | objeto | Deve conter exatamente as mesmas chaves de `fields`; valores sao maiores ou iguais a zero. |
| `overlap_policy` | string | Atualmente somente `max_per_group`. |
| `confirmation` | objeto | Contem `bonus_per_additional_field` e `max_bonus_per_group`; ambos sao maiores ou iguais a zero. |
| `positive_score_field` | string | Alias de saida para $P$. |
| `negative_score_field` | string | Alias de saida para $N$. |
| `affinity_score_field` | string | Alias de saida para $A = P - N$. |
| `positive_rules` | lista de regras | Nao pode ser vazia. |
| `negative_rules` | lista de regras | Nao pode ser vazia. |

Os tres aliases de score devem ser identificadores validos e distintos. A saida tambem preserva `positive_score`, `negative_score` e `score_margin` por compatibilidade.

### Template Executavel

Este perfil `v2` e completo e validavel. Troque campos, regras, grupos e pesos para o dominio estudado. Os termos `example` servem apenas como marcadores.

```json
{
  "schema_version": 2,
  "profile_id": "example-server-scoring",
  "profile_version": "1.0.0",
  "domain": "example",
  "description": "Indice exploratorio de afinidade de servidores com o dominio example.",
  "server": {
    "fields": ["name", "description", "about", "keywords"],
    "field_weights": {
      "name": 1.5,
      "description": 1.25,
      "about": 1.0,
      "keywords": 0.75
    },
    "overlap_policy": "max_per_group",
    "confirmation": {
      "bonus_per_additional_field": 0.5,
      "max_bonus_per_group": 1.0
    },
    "positive_score_field": "example_positive_score",
    "negative_score_field": "example_negative_score",
    "affinity_score_field": "example_affinity_score",
    "positive_rules": [
      {
        "id": "explicit-domain",
        "label": "explicit domain intent",
        "pattern": "\\bexample domain\\b",
        "weight": 5,
        "group": "domain-intent"
      },
      {
        "id": "domain-practice",
        "label": "domain practice",
        "pattern": "\\bexample practice\\b",
        "weight": 3,
        "group": "domain-practice"
      }
    ],
    "negative_rules": [
      {
        "id": "other-domain",
        "label": "other domain",
        "pattern": "\\bunrelated domain\\b",
        "weight": 4,
        "group": "other-domain"
      }
    ]
  }
}
```

Para esse schema, todos os registros de entrada sao emitidos e `is_selected` vale `null`. O comando ainda se chama `select-servers` por compatibilidade, mas o manifesto registra `score-servers` e `selection_applied: false`.

```powershell
python -m discord_filtering validate-profile `
  --profile configs/filtering/example.v2.json

python -m discord_filtering select-servers `
  --profile configs/filtering/example.v2.json `
  --input data/raw/server_metadata/servers_metadata.txt `
  --output data/processed/filtering/example/<run_id>/servers_scored.parquet
```

### Saida de Auditoria

Cada servidor pontuado preserva identidade e metadados de entrada, alem destes campos:

| Campo | Significado |
| --- | --- |
| `positive_score` e alias configurado | $P$, evidencia positiva agregada. |
| `negative_score` e alias configurado | $N$, evidencia negativa agregada. |
| `score_margin` e alias configurado | $A = P - N$, afinidade liquida. |
| `metadata_available_json` | Mapa de disponibilidade dos campos configurados. |
| `metadata_completeness` | Fracao de campos configurados com valor utilizavel; nao normaliza o score. |
| `positive_groups`, `negative_groups` | Grupos semanticos encontrados. |
| `positive_group_scores`, `negative_group_scores` | Credito final por grupo. |
| `matched_positive_terms`, `matched_negative_terms` | Labels das regras que encontraram evidencia. |
| `server_evidence_json` | Campo, regra, texto encontrado, span, peso e credito de cada match. |
| `is_selected` | `null` no schema `2`; booleano no schema `1`. |

Campos terminados em `_json` e listas de grupos sao serializados como JSON compacto para compatibilidade com CSV e Parquet.

## Schema 1: Selecao de Servidores e Canais

O schema `1` exige `server` e `channel`. Use-o quando os limiares de selecao forem parte da decisao metodologica e a classificacao de canais estiver pronta.

### Politica de Servidor

`server` no schema `1` exige estas chaves:

```text
fields
field_weights
positive_rules
negative_rules
overlap_policy
selection
```

As regras e pesos de campos seguem as convencoes anteriores. O objeto `selection` tem esta estrutura:

```json
{
  "min_positive_score": 7,
  "min_score_margin": 3,
  "max_negative_score": 3,
  "blocked_negative_labels": ["adult"],
  "required_positive_labels": []
}
```

| Campo | Efeito |
| --- | --- |
| `min_positive_score` | Exige $P$ maior ou igual ao limiar. |
| `min_score_margin` | Exige $A = P - N$ maior ou igual ao limiar. |
| `max_negative_score` | Exige $N$ menor ou igual ao limiar; use `null` para desativar. |
| `blocked_negative_labels` | Rejeita se qualquer label negativa listada for encontrada. Cada label deve existir em `negative_rules`. |
| `required_positive_labels` | Quando nao vazia, exige ao menos uma label positiva listada. Cada label deve existir em `positive_rules`. |

### Politica de Canal

`channel` no schema `1` exige estas chaves:

```text
metadata_fields
positive_rules
negative_rules
overlap_policy
metadata_normalization
signals
component_weights
classification
conversation_suitability
exclude_bot_messages
max_evidence_examples
score_field
domain_score_field
```

As regras de canal pontuam `metadata_fields`. O componente de metadados e:

$$
E_m = \min\left(\frac{\max(P_m - N_m, 0)}{\text{metadata_normalization}}, 1\right)
$$

Cada item de `signals` exige:

```json
{
  "id": "technical",
  "label": "technical discussion",
  "pattern": "\\bexample technical term\\b",
  "count_field": "technical_messages",
  "lexical_weight": 1.0,
  "lexical_saturation_ratio": 0.1,
  "domain_weight": 1.0,
  "domain_saturation_ratio": 0.1
}
```

`id` e `count_field` devem ser unicos. As somas de todos os `lexical_weight` e de todos os `domain_weight` devem ser exatamente `1.0`. Para um sinal com contagem $c$, total de mensagens $T$ e saturacao $q$, a contribuicao antes do peso e:

$$
\min\left(\frac{c}{Tq}, 1\right)
$$

`component_weights` possui `metadata`, `lexical` e `domain`; seus valores estao em $[0, 1]$ e devem somar `1.0`. O escore composto do canal e:

$$
S = w_mE_m + w_lE_l + w_dE_d
$$

`classification` exige `high_confidence_score`, `review_score`, `high_min_lexical_score`, `fallback_min_lexical_score`, `fallback_min_domain_score`, `admin_max_lexical_score`, `admin_max_domain_score`, `social_max_lexical_score`, `admin_negative_labels`, `social_negative_labels`, `class_high`, `class_review`, `class_social`, `class_admin`, `include_classes` e `manual_review_classes`. As quatro classes devem ser distintas; labels administrativas e sociais devem existir entre as regras negativas de canal.

`conversation_suitability` exige estes seis limites:

```json
{
  "min_human_users": 5,
  "min_interaction_ratio": 0.05,
  "min_author_transition_ratio": 0.2,
  "max_dominant_author_ratio": 0.7,
  "max_bot_message_ratio": 0.25
}
```

`exclude_bot_messages` remove mensagens de bot da evidencia lexical, `max_evidence_examples` limita exemplos preservados por sinal, e `score_field` e `domain_score_field` definem aliases de saida para o escore composto e a evidencia de dominio.

## Versionamento dos Perfis de Software

1. Defina o construto: escreva o que o score mede, sem transforma-lo em rotulo binario prematuro.
2. Comece com um perfil `v2`. Configure somente campos existentes na fonte e escolha pesos de campo por qualidade semantica.
3. Divida regras positivas em grupos semanticos. Mantenha tecnologias com peso menor que intencoes explicitas.
4. Adicione regras negativas como evidencia de proposito concorrente, nao como exclusoes na etapa exploratoria. Verifique palavras polissemas no corpus.
5. Escreva testes para exemplos positivos, negativos, ambiguos e fronteiras de regex, inclusive duas regras do mesmo grupo.
6. Pontue todos os registros, guarde o artefato e o manifesto, e analise $P$, $N$, $A$, grupos e completude.
7. Use percentis e amostras estratificadas para justificar um cutoff. So depois crie ou atualize um perfil `v1` com `selection` e, se necessario, canais.

## Checklist e Verificacao

- `id`, `group`, `profile_id`, `domain` e aliases seguem o formato aceito.
- Cada regra possui `id` unico, label nao vazia, regex compilavel, peso positivo e grupo coerente.
- `field_weights` cobre exatamente os campos de `fields`.
- Grupos impedem que sinonomos ou listas longas de termos inflem o score.
- Termos ambiguos foram confrontados com exemplos reais do corpus.
- A versao do perfil mudou quando a funcao de scoring mudou.
- A saida e o manifesto sao gravados fora do caminho da fonte imutavel.

```powershell
python -m discord_filtering validate-profile `
  --profile configs/filtering/<perfil>.json

python -m pytest tests/test_filtering_profiles.py -q
```

A validacao confere formato, chaves, regex, pesos, referencias entre labels e regras de soma. Ela nao prova a qualidade semantica das regras; isso exige inspecao de exemplos e revisao humana do dominio.