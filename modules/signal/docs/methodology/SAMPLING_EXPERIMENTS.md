# Desenho Amostral: Testes e Evidencias Atuais

## Escopo

Este documento descreve testes da implementacao e a execucao
`sampling_participants_v2`, realizada apos a selecao por volume e participantes.
Nao apresenta experimentos de modelos nem dados humanos ja classificados.
Os calculos estao em [sampling.py](../../discord_disentanglement/sampling.py)
e [sampling_audit.py](../../discord_disentanglement/sampling_audit.py).

## Quadro e Sorteio

O quadro atual tem 297 canais de 29 servidores. A selecao anterior de canais
exigiu ao menos 500 registros brutos e cinco autores humanos distintos,
sem condicao de reply ou mencao. O cadastro de elegibilidade e separado do
corpus; seu estado provisorio nao substitui revisao tematica humana.

Os canais sao estratificados por servidor e porte de mensagens utilizaveis;
meses ativos sao sorteados dentro dos canais, e blocos dentro dos meses.
Os tres niveis usam amostragem aleatoria sem reposicao. O ultimo bloco
incompleto permanece elegivel para preservar probabilidade positiva.
Probabilidades, pesos e semente sao registrados antes de anotar.

## Execucao e Verificacoes

Com semente 20261014 e cotas declaradas de ate dois canais por estrato,
tres meses por canal e um bloco por mes, a execucao produziu:

| Medida | Valor |
| --- | ---: |
| Canais no quadro | 297 |
| Canais sorteados | 107 |
| Servidores sorteados | 29 |
| Janelas | 317 |
| Mensagens-alvo | 17.921 |
| Janelas com menos de 100 alvos | 198 |
| Verificacoes aprovadas na auditoria | 38 de 38 |

A auditoria confere hashes, identidades, cotas, probabilidades, pesos,
contexto, alvos e distribuicoes. Verifica a reproducao com a mesma semente e
calcula a variancia exata de totais auxiliares conhecidos sob o desenho,
sem utilizar rotulos semanticos. Sua aprovacao nao e prova de representatividade
semantica ou de precisao para resultados ainda nao anotados.

O [relatorio gerado](SAMPLING_DESIGN_AUDIT.md) contem os valores completos,
denominadores, cenarios de sensibilidade, dispersao dos pesos e limitacoes.
Ele substitui, para a execucao atual, as tabelas das amostras anteriores.

## Testes Automatizados

[test_sampling.py](../../tests/test_sampling.py) cobre probabilidades conhecidas,
repeticao independente da ordem das entradas, limites de porte, estados de
elegibilidade, blocos curtos, contexto entre meses, preservacao de midia,
pacote de anotacao, auditoria independente, adulteracao de pesos e variancia
exata em desenhos pequenos enumeraveis.

[test_channel_selection.py](../../tests/test_channel_selection.py) cobre a regra
OR dos minimos, contagem distinta sem campos de reply/mencao, bots e status
desconhecido, limites inclusivos, exclusao manual, hashes e recusa de sobrescrita.
Os testes de populacao verificam disponibilidade de conteudo separadamente.

## Reproducao e Interpretacao

```powershell
discord-prepare draw --output <nova_amostra> --seed 20261014
discord-prepare audit-sampling --sample <nova_amostra> --output <nova_auditoria> --report <novo_relatorio.md>
```

O quadro padrao e `annotations/channel_frame_participants_v2.csv`. Use diretorios
novos; nao substitua uma amostra depois de examinar suas caracteristicas.
Sensibilidade nao e selecao automatica da configuracao mais favoravel.

O desenho nao e autoponderado. Janelas por contagem podem durar dias e conter
silencios longos. Replies nativos e suas sobreposicoes sao proxies observaveis,
nao verdade semantica. Essas limitacoes precisam de leitura e calibracao humana,
preservando tambem casos esparsos para avaliar especificidade.