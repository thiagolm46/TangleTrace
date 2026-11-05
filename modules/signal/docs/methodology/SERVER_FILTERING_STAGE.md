# Etapa 1 - Filtragem e Validacao de Servidores

## 1. Finalidade

A Etapa 1 teve como objetivo identificar, entre os servidores do catalogo Discord Unveiled, aqueles que constituem comunidades validas para a investigacao sobre engenharia de software, desenvolvimento, ferramentas, projetos e praticas relacionadas.

A etapa foi tratada como um processo em duas partes:

1. **Etapa 1A - Scoring:** atribuir a todos os servidores um indice continuo de afinidade com software, preservando as evidencias utilizadas.
2. **Etapa 1B - Auditoria manual:** inspecionar os servidores candidatos e registrar a decisao final de validade para o contexto da pesquisa.

A pontuacao automatica nao foi usada como substituta da revisao humana. Ela serviu para organizar o corpus, tornar a triagem reproduzivel e preservar uma explicacao auditavel para cada resultado.

Essa etapa operacionaliza o recorte de dominio da pesquisa: o corpus nao e
uma amostra indiferenciada de comunidades do Discord, mas um conjunto de
servidores relacionados a engenharia de software. As regras procuram
evidencias de desenvolvimento, manutencao, ferramentas, projetos e praticas
de software; a revisao manual verifica se essa relacao e central ao contexto
da comunidade, em vez de uma mencao incidental. Isso nao implica que todas
as mensagens de um servidor aceito sejam tecnicas, nem que todos os servidores
de software do catalogo tenham sido identificados. A adequacao dos canais
e tratada na etapa seguinte.

Neste procedimento, reproducibilidade tem dois niveis:

- **Computacional:** a mesma fonte congelada, o perfil versionado e a regra
  explicita de priorizacao permitem recalcular os scores e recuperar os
  mesmos 37 candidatos. Os hashes permitem conferir os artefatos utilizados.
- **Das decisoes registradas:** a lista manual corrigida permite reconstruir
  o conjunto de 31 servidores aceitos e restringir a extracao aos mesmos
  identificadores. Isso nao equivale a demonstrar concordancia entre
  avaliadores ou garantir que uma nova revisao de comunidades mutaveis
  produza as mesmas decisoes. As justificativas individuais nao preservadas
  limitam a auditabilidade da avaliacao humana.

## 2. Corpus e artefatos

O corpus de entrada continha **3.167 servidores** do Discord Unveiled, a partir do arquivo:

[`servers_metadata.txt`](../../data/raw/server_metadata/servers_metadata.txt)

A funcao de scoring foi definida no perfil:

[`software.engineering.v2.json`](../../configs/filtering/software.engineering.v2.json)

- `profile_id`: `software-engineering-server-scoring`
- `profile_version`: `2.2.0`
- `schema_version`: `2`
- `domain`: `software`
- selecao automatica: desativada
- pontuacao de canais: nao definida

O resultado integral da Etapa 1A foi gravado em:

[`servers_scored.parquet`](../../data/processed/filtering/software/affinity_v2/servers_scored.parquet)

O manifesto correspondente e:

[`servers_scored.parquet.manifest.json`](../../data/processed/filtering/software/affinity_v2/servers_scored.parquet.manifest.json)

O manifesto registra:

- 3.167 servidores avaliados;
- 3.167 linhas emitidas;
- nenhuma selecao automatica;
- `selection_applied: false`;
- fonte de entrada tratada como imutavel;
- hashes da fonte, do perfil e do resultado.

A lista utilizada para registrar a auditoria manual esta em:

[`selected_servers.txt`](../../data/processed/filtering/software/affinity_v2/selected_servers.txt)

## 3. Construto medido

O construto operacional foi definido como:

> Grau em que os metadados de um servidor apresentam evidencias de que sua comunidade esta relacionada a desenvolvimento, manutencao, evolucao, uso ou praticas de software.

O score nao representa probabilidade de um servidor ser de software. Ele e um indice ordinal/continuo derivado de regras semanticas, pesos de campos e evidencias textuais.

## 4. Metadados utilizados

A funcao analisou os seguintes campos:

- `name`
- `description`
- `about`
- `reasons_to_join`
- `keywords`

Os campos receberam os pesos:

| Campo | Peso |
| --- | ---: |
| `name` | 1,50 |
| `description` | 1,25 |
| `about` | 1,00 |
| `reasons_to_join` | 1,00 |
| `keywords` | 1,00 |

O nome e a descricao receberam maior peso como uma escolha heuristica: esses campos podem declarar a identidade e o proposito do servidor. Os multiplicadores nao foram calibrados empiricamente nem demonstram que o nome seja sempre mais informativo que a descricao. Nomes de marca podem nao conter evidencia tecnica, enquanto uma mencao tecnica isolada pode ser incidental. Por isso, os pesos foram usados para priorizar a inspecao, nao para determinar a validade da comunidade. A completude dos metadados foi registrada separadamente e nao foi usada para normalizar artificialmente o score.

O JSON e a configuracao versionada do metodo, nao um classificador treinado: define campos, regexes, pesos, grupos e bonus. As palavras-chave buscadas pelas regras sao distintas do campo `keywords`, que contem etiquetas presentes nos metadados do servidor. A busca inclui explicitamente a descricao, e nao apenas o nome ou essas etiquetas.

Antes da busca, os textos foram normalizados com Unicode NFKC. A comparacao das regexes e case-insensitive. Valores nulos, vazios e sentinelas como `NA`, `N/A` e `null` nao foram tratados como evidencia.

## 5. Evidencias positivas

As regras positivas foram organizadas em grupos semanticos:

| Grupo | Tipo de evidencia | Exemplos |
| --- | --- | --- |
| `software-intent` | Intencao explicita | software engineering, software development, programming, coding, desenvolvimento de software |
| `developer-community` | Comunidade de desenvolvedores | developer community, developers, devs, desenvolvedores |
| `open-source` | Software livre e codigo aberto | open source, codigo aberto, logiciel libre |
| `engineering-practice` | Praticas de engenharia | testing contextualizado, debugging, deployment de software, CI/CD, version control |
| `software-specialization` | Areas de software | frontend, backend, full-stack, mobile development, data engineering, game development |
| `software-artifact` | Artefatos e ecossistema | API, SDK, framework, library, package, plugin, extension, dependency, repository, source code, GitHub, GitLab |
| `programming-language` | Linguagens | Python, JavaScript, TypeScript, Java, Rust, Kotlin, Ruby, PHP, C++ e C# |
| `data-platform` | Dados e plataformas | databases, PostgreSQL, MySQL, MongoDB, Neo4j, Redis, Kafka |
| `infrastructure-tool` | Infraestrutura | Docker, Kubernetes, Terraform, Linux, AWS, Azure, GCP |

As evidencias explicitas receberam pesos maiores. Tecnologias isoladas receberam peso menor, pois a simples mencao de uma linguagem, plataforma ou ferramenta nao prova, sozinha, que o servidor seja uma comunidade de engenharia de software.

## 6. Evidencias negativas

As regras negativas nao foram usadas para excluir servidores durante a Etapa 1A. Elas foram registradas como evidencia de que o proposito principal do servidor pode estar em outro dominio.

Foram considerados, entre outros:

- conteudo adulto ou NSFW;
- financas, crypto, NFT e forex;
- jogos especificos;
- namoro e matchmaking;
- giveaways, airdrops e Twitch drops.

Essa separacao permitiu distinguir, por exemplo, dois servidores com afinidade liquida semelhante, mas composicoes diferentes:

```text
Servidor A: positivo = 15, negativo = 0, afinidade = 15
Servidor B: positivo = 30, negativo = 15, afinidade = 15
```

## 7. Agregacao dos matches

Para uma regra $r$ encontrada no campo $f$, o peso preliminar foi:

$$
W_{r,f} = W_r \times W_f
$$

Foi utilizada a politica `max_per_group`. Assim, regras que representam a mesma familia de evidencia nao foram somadas indefinidamente. Em cada grupo, somente o maior peso ajustado recebeu credito principal.

Portanto, ha uma soma de pontos por grupos de evidencia, nao uma contagem de frequencia das palavras. Repetir uma palavra no mesmo campo nao multiplica sua contribuicao. Os multiplicadores de campo se aplicam tanto as regras positivas quanto as negativas.

Quando a mesma evidencia apareceu em campos diferentes, foi aplicado um bonus de confirmacao limitado:

- `bonus_per_additional_field`: `0,5`;
- `max_bonus_per_group`: `1,0`.

O score final foi calculado como:

$$
P = \sum_g P_g
$$

$$
N = \sum_g N_g
$$

$$
A = P - N
$$

onde:

- $P$ = `positive_score`;
- $N$ = `negative_score`;
- $A$ = `software_affinity_score`.

O resultado preservou tambem os aliases:

- `software_positive_score`;
- `software_negative_score`;
- `software_affinity_score`.

### 7.1 Priorizacao dos 37 candidatos

A reconstrucao a partir do Parquet de scores reproduziu exatamente os 37
`guild_id` da lista de revisao manual com o seguinte procedimento:

1. Pontuar todos os 3.167 servidores com o perfil 2.2.0.
2. Restringir o calculo dos quartis aos 282 servidores com afinidade
   **estritamente positiva** (`software_affinity_score > 0`).
3. Calcular Q1 e Q3 com interpolacao linear: 3,00 e 5,25, respectivamente.
4. Calcular IQR = Q3 - Q1 = 2,25 e o limite superior de Tukey:
   Q3 + 1,5 x IQR = 8,625.
5. Priorizar os 37 servidores com afinidade **maior que 8,625** para revisao.

O limite inferior e -0,375 e nao seleciona observacoes nesse subconjunto.
Incluir afinidades iguais a zero no calculo dos quartis produziria Q1 = Q3 = 0
e 282 candidatos, nao os 37 registrados. O notebook original nao foi localizado
no workspace nem no historico Git consultado; o procedimento acima e uma
reconstrucao verificada contra os identificadores preservados, nao uma
transcricao de suas celulas. Os scores e as evidencias dos 3.167 servidores
tambem foram reproduzidos a partir da fonte e do perfil, cujos hashes conferem
com o manifesto.

Esse corte organiza a fila de inspecao desta execucao. Nao e um limiar
validado de pertinencia ao dominio e nao substitui a decisao humana.

## 8. Auditoria e criterios de validade

A auditoria manual foi feita sobre os servidores candidatos produzidos pela etapa de scoring. A decisao considerou o contexto real da comunidade, e nao apenas a presenca de uma palavra-chave.

Um servidor foi marcado como **Sim** quando era valido para a investigacao de comunidades, projetos, ferramentas ou praticas de software. Foram aceitas comunidades de desenvolvimento de jogos e modding quando a atividade tecnica era parte central da comunidade.

Um servidor foi marcado como **Nao** quando os sinais tecnicos eram incidentais ou quando o foco principal nao correspondia ao escopo definido.

A lista final nao deve ser interpretada como um cutoff estatistico universal. Ela representa a decisao manual documentada para esta execucao e este contexto de pesquisa.

## 9. Resultado final da auditoria

Dos 37 servidores apresentados para auditoria manual:

- **31 foram validados como Sim**;
- **6 foram classificados como Nao**;
- proporcao validada: **83,78%**.

Em 2026-10-28, o pesquisador corrigiu um erro de transcricao: Firebelly
Studios (`135844298527735818`) havia sido registrado como Sim, mas nao passou
na validacao manual. A correcao e de registro, nao uma nova exclusao por falta
de mensagens. A justificativa especifica dessa rejeicao nao foi informada.
Os registros individuais preservam a decisao, mas nao justificativas por
servidor; nao se deve inferi-las a partir do nome, do score ou da ausencia
de mensagens.

### 9.1 Servidores selecionados

A tabela abaixo e o conjunto final de servidores validos para a proxima etapa:

| # | Servidor | `guild_id` |
| ---: | --- | --- |
| 1 | WWebJS | `698610475432411196` |
| 2 | MonoGame Discord | `355231098122272778` |
| 3 | Fermyon | `926888690310053918` |
| 4 | Montano Community | `561997286087852118` |
| 5 | Neo4j | `787399249741479977` |
| 6 | Sapphire - Imagine a framework | `737141877803057244` |
| 7 | OpenRCT2 | `264137540670324737` |
| 8 | GameDevSG | `558680594498977792` |
| 9 | Terasology | `270264625419911192` |
| 10 | Oxylabs | `1128239127687598080` |
| 11 | Andy's Development | `857672921912836116` |
| 12 | Rectify11 Community | `1077324213142175744` |
| 13 | Cyberpunk 2077 Modding Community | `717692382849663036` |
| 14 | LuaCore Framework | `1078542362793492490` |
| 15 | Kindred Games Community | `398282199788552193` |
| 16 | ImperialPlugins.com | `284399832385191936` |
| 17 | CodingWallah | `1056895641676152852` |
| 18 | Ouckah Lair | `519640186167099402` |
| 19 | L'Ordre des Devs | `706640777450881114` |
| 20 | Evolution Software Inc | `806713690182385695` |
| 21 | Touhou Game Dev | `933089313405685760` |
| 22 | TikTok Shop Developer Hub | `1204537856870191114` |
| 23 | Docker | `460871933748183040` |
| 24 | Kavita | `821879810934439936` |
| 25 | Shardeum | `933959587462254612` |
| 26 | OpenVic - Community | `1062018115275325480` |
| 27 | Tech Haven | `455345206481518593` |
| 28 | TheScostumati | `516564332440584221` |
| 29 | Penusbmic's Server | `894976658229063731` |
| 30 | Return Community | `1080829289412432032` |
| 31 | Rosebud AI | `773712199729414144` |

### 9.2 Servidores excluidos na auditoria

| Servidor | `guild_id` |
| --- | --- |
| Island Adventures | `278017358692352000` |
| mastercomfig | `389089828249010188` |
| /g/ - technology: CIA edition | `887040128898453584` |
| Rigs of Rods | `136544456244461568` |
| Glitches and Tricks | `364220567190241280` |
| Firebelly Studios | `135844298527735818` |

## 10. Artefato para extracao

Para que a proxima etapa extraia mensagens somente dos servidores validados, foi criado o arquivo:

[`manual_selected_servers.parquet`](../../data/processed/filtering/software/affinity_v2/manual_selected_servers.parquet)

Esse artefato, corrigido para refletir a decisao manual, contem 31 linhas e as colunas:

- `guild_id`;
- `name`;
- `is_selected`;
- `manual_decision`.

O arquivo de mensagens deve ser gerado em um caminho novo, sem sobrescrever fontes ou resultados anteriores:

```powershell
.\.venv\Scripts\python.exe -m discord_data extract-remote `
  --selected-servers-path data\processed\filtering\software\affinity_v2\manual_selected_servers.parquet `
  --output-path data\processed\filtering\software\affinity_v2\messages_manual_2026-09-21.parquet
```

A extracao existente contem 13.275.074 registros dos 31 servidores aceitos.
Firebelly Studios nao aparece nesse corpus; portanto, a correcao da lista
nao exige reescrever as mensagens. O comando acima documenta a operacao;
para reexecuta-lo, deve-se escolher uma saida ainda inexistente.

A extracao remota percorre o arquivo comprimido em streaming, descomprime
sequencialmente e converte em Parquet apenas as mensagens dos servidores
selecionados, em lotes. Isso evita armazenar o arquivo bruto completo e
materializar mensagens fora do escopo. Nao significa baixar pela rede
somente os servidores selecionados: o fluxo atual percorre o arquivo
comprimido, de modo que a economia e de armazenamento e materializacao
local, nao necessariamente de trafego.

## 11. Limites e interpretacao

1. A validade foi definida para o escopo desta pesquisa; nao significa que os servidores sejam exclusivamente de software.
2. Comunidades hibridas podem conter jogos, educacao, infraestrutura, blockchain ou criacao de conteudo junto com atividade tecnica.
3. Metadados ausentes reduzem a observabilidade, mas nao foram usados para penalizar automaticamente o servidor.
4. O conjunto final foi definido por auditoria manual apos a priorizacao por score. O limite de Tukey reproduz a lista de candidatos, nao a decisao de validade.
5. A proxima etapa deve avaliar os canais e mensagens apenas dentro dos 31 servidores validados.
6. Qualquer revisao futura da lista deve registrar data, motivo, decisao anterior e nova decisao, preservando o artefato original.

## 12. Conclusao da Etapa 1

A Etapa 1 foi concluida como um procedimento de identificacao e validacao de comunidades de software:

1. os 3.167 servidores foram pontuados com a mesma funcao;
2. scores positivos, negativos e de afinidade foram preservados;
3. as evidencias, grupos e completude dos metadados foram mantidos para auditoria;
4. 37 candidatos foram avaliados manualmente;
5. 31 servidores foram validados para a pesquisa;
6. a lista manual foi materializada em Parquet para a extracao controlada de mensagens.

O conjunto de 31 servidores e, portanto, a base operacional para a Etapa 2, que analisara canais, mensagens e adequacao conversacional dentro desse escopo validado.
