# Hipóteses de margem e receita

_Scripts: `scripts/03_teste_hipoteses_h0_premissa.py`, `..._h9_margem_incompleta.py`, `..._h7_pagamento.py`, `..._h1_margem.py`, `..._h2_canais.py`, `..._h3a_devolucoes.py`, `..._h8_preco_referencia.py`._

> Esta pasta resume as questões testadas sobre margem e receita. Outras frentes testadas (atendimento, estoque, segmentos de cliente, gestão/produtividade) estão em `outras_frentes_testadas.md`, porque nenhuma delas se tornou a alavanca central. Todos os vereditos abaixo são **propostos** — a interpretação de negócio final é do Davi.

| O que foi testado | Veredito |
|---|---|
| A premissa "receita↑, margem%↓" se sustenta? | **Refutada** |
| A margem reportada é uma medida completa do resultado? | **Não** |
| Há vazamento de receita no pagamento (cancelado/aguardando)? | **Refutada como causa da queda** |
| A margem por pedido perde qualidade por desconto, frete ou mix? | **Refutada em tendência; frete estrutural confirmado** |
| Devoluções corroem a margem de forma concentrada? | **Refutada para a taxa** |
| Canais de aquisição diferem em qualidade (mídia × margem)? | **Parcial / inconclusiva** |
| O preço praticado se afasta do preço de referência? | **Inconclusiva** (limitação de dado) |

## A premissa de queda de margem não se sustenta

Margem de contribuição por pedido entre **53,21% e 54,90%** ao longo dos 13 meses de 2023, sem tendência (p=0,23). Comparando jan/2024 com o mesmo recorte de jan/2023: receita −1,56%, margem −0,22 p.p. Nenhum dos 7 canais nem das 4 categorias mostra queda. **A pergunta original do case não se sustenta nos dados** — é o achado que redireciona toda a análise para "onde a margem varia", não "por que ela caiu".

## A margem reportada esconde parte do resultado

A coluna `margem_contribuicao` é `receita_liquida − custo_produto − custo_frete`, e vale **identicamente** para pedidos aprovados, devolvidos e cancelados — a fórmula não abate nada disso. Depois de considerar só pedidos aprovados e não devolvidos, a margem efetiva cai de 54,34% para 43,57–45,96% (dependendo da premissa de tratamento da devolução), mas a ordem entre grupos e a ausência de tendência não mudam (teste de permutação, p ≥ 0,33).

**Confirmado em outro corte:** medindo pela mesma lógica, mas isolando só pedidos aprovados e não devolvidos, apenas 75,0% dos pedidos se concretizam, com uma superestimação de **R$ 2.563.716 em 13 meses** (devolvidos R$ 1.351.707 + cancelados R$ 809.612 + aguardando R$ 402.397). Esse número bate, na ordem de grandeza e na composição, com os pools sem endereço medidos mais adiante para devolução (R$ 1,68 mi/ano) e pagamento não aprovado (R$ 1,13 mi/ano) — dois recortes independentes chegando ao mesmo lugar.

## Vazamento no pagamento, mas sem causa concentrada

R$ 2,22 mi (11,75%) da receita registrada não se realiza (cancelado/aguardando), numa taxa **estável** (p=0,55) e **sem concentração** por método de pagamento, canal ou categoria (p ≥ 0,89 em todos os cortes). É grande, mas nenhum corte indica onde intervir.

## Desconto sem tendência; frete estrutural

Desconto médio de 8,0% da receita bruta, **sem tendência** fora de novembro (p=0,17); efeito de mudança de mix de produto ≤ 0,05 p.p. — nenhum dos dois explica queda de margem. O que se confirma como **estrutural** é o frete do Marketplace: 4,53% da receita bruta contra 0,87% nos demais canais, repetido nas 4 categorias e nos 13 meses. A margem por SKU também tem um componente estrutural de markup, mas de peso pequeno frente ao desconto/frete por item (dispersão maior que o acaso, p=0,0005, mas de efeito pequeno: 239 SKUs abaixo de 53% contra 182 esperados).

Esse é o mesmo mecanismo — margem explicada por desconto e frete, não por produto ou cliente — que a etapa seguinte (`04_alavanca_definitiva/`) decompõe e dimensiona.

## Devolução homogênea, sem alavanca de corte

Taxa de devolução de 14,88%, **homogênea** nos 11 cortes testados e nos 9 de interação — não há categoria, canal ou período concentrador. Um padrão específico se confirma (motivo "Não gostei" no canal Influenciador, 6,38% contra ~2% no resto, em 9 de 9 cortes), mas não muda a taxa total. A devolução acaba entrando, na etapa seguinte, como um dos dois grandes pools sem endereço (R$ 1,68 mi/ano).

## Canais: investimento parelho, margem desigual, mas sem explicação causal

Investimento de mídia dividido quase igualmente entre canais (12,9%–15,4%), com margem desigual (10,1%–20,1%) — confirmado. Mas o gasto de mídia não explica as vendas com efeito fixo de mês (r=0,11, p=0,32), e a base de marketing mede 3,66× a receita real na janela testada — não dá para atribuir causalidade entre investimento e margem por canal com esta base.

## Preço praticado não correlaciona com o preço de referência

Custo de vendas fica a ±10% do custo de estoque em apenas 4,6% dos itens; correlação SKU a SKU de 0,008. Limitação de dado, não um veredito de negócio — o `preco_venda_sugerido` do estoque não serve como referência confiável para avaliar o preço praticado.

## O que essas hipóteses, juntas, apontam

Nenhuma delas, isoladamente, chega perto do tamanho do problema. O padrão que se repete — margem explicada por decisão da empresa (desconto, frete), não por produto ou cliente — e os dois grandes pools sem endereço (devolução, pagamento) são exatamente o que a etapa seguinte (`04_alavanca_definitiva/`) retoma sem partir de hipótese nenhuma, e onde a alavanca real é encontrada.
