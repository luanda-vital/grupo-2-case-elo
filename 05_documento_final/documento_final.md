# Vértice Retail — Inteligência de Precificação: Diagnóstico, Solução e Business Case

*"Vocês não perderam margem. Perderam a explicação dela."*

## 1. Diagnóstico executivo

A hipótese de partida deste case era que a Vértice Retail cresce em receita e perde rentabilidade. Os dados não sustentam essa hipótese: a margem por pedido fica estável, entre 53,2% e 54,9%, ao longo de todo o 2023. Não há queda de margem a explicar.

A margem não cai — mas também não é idêntica em todo pedido: ela varia dentro dessa faixa de 53,2% a 54,9%. Essa variação exige uma pergunta direta: o que mais impacta a margem por pedido? Decompor essa variação, pedido a pedido, aponta a origem, e ela está concentrada em só duas linhas.

| Componente | Participação na variação de margem por pedido |
|---|---|
| Desconto | 49,84% |
| Frete | 41,50% |
| **Total** | **91,34%** |

Essas duas linhas têm uma característica que nenhuma outra variável do pedido tem: são decisão da própria empresa, não característica de produto ou de cliente. Custo do produto, perfil do comprador, canal de venda — nenhum desses fatores concentra a variação de margem como desconto e frete. A causa não está no produto nem no cliente: está na política de preço da Vértice.

Das duas, o desconto nasce primeiro e é ele que arrasta a segunda. No varejo online, o desconto nasce na origem — cupom, campanha, regra de categoria — e, na Vértice, nasce sem nenhum critério detectável: R$ 1,35 milhão por ano é concedido sem padrão e sem retorno mensurável. É o problema central deste diagnóstico, e a seção 2 mostra, teste por teste, por que ele não tem critério nem retorno.

O desconto sem critério carrega um efeito colateral, numa linha diferente da sua:

```
Desconto aplicado no pedido
        │
        ▼
Valor do pedido cai
        │
        ▼
Pedido cruza abaixo do limiar de frete grátis (R$ 250)
        │
        ▼
Frete grátis é concedido — custo de logística
que só existe porque o preço mudou
```

Esse mecanismo é real, mas pequeno perto do problema central: vale R$ 15.970 por ano, menos de 5% do que a correção do próprio desconto recupera (R$ 345.244/ano, seção 4). O frete é consequência do desconto, não uma causa independente — o centro deste diagnóstico é o desconto.

Diagnosticado o mecanismo — desconto sem critério, com um efeito colateral pequeno em frete —, a pergunta que orienta o restante deste documento é direta: quanto vale dar à Vértice a inteligência que hoje falta sobre sua própria decisão de preço.

## 2. Análise e Insights

Responder essa pergunta exige entender por que o desconto de hoje não tem critério nem retorno. Três testes, aplicados à base de 24.454 pedidos, respondem em conjunto.

### O desconto não segue nenhum padrão

O primeiro teste pergunta se existe uma regra por trás do desconto: um modelo foi treinado para prever quem recebe desconto e quanto, usando todas as variáveis disponíveis do pedido — canal, categoria, fornecedor, cliente, mês, dia da semana. Se houvesse critério, o modelo acertaria acima do acaso.

Não acerta. A capacidade de prever **quem** recebe desconto ficou em 0,4991 numa escala em que 0,50 equivale a jogar uma moeda; a capacidade de prever **quanto** de desconto ficou pior do que simplesmente chutar a média de todo mundo. E a distribuição dos valores concedidos não tem nenhum degrau em números redondos (10%, 15%, 20%, 25%) — são 7.596 valores diferentes em 8.668 itens descontados, cada um com o seu. Uma tabela de desconto real produz picos nesses valores; esta distribuição não tem nenhum.

### O desconto não compra nada

O segundo teste pergunta se, mesmo sem critério, o desconto ainda assim funciona — se ele gera algum retorno. Quatro métricas foram comparadas entre pedidos com e sem desconto.

| O que se testou | Pedidos com desconto | Pedidos sem desconto |
|---|---|---|
| Volume por pedido | 3,52 unidades | 3,51 unidades |
| Aprovação do pagamento | 88,00% | 88,15% |
| Taxa de devolução | 14,48% | 15,10% |
| Recompra do cliente (pedidos seguintes) | 2,55 pedidos | 2,68 pedidos |

Nas quatro, a diferença é mínima, e em duas delas — aprovação e recompra — o grupo que recebeu desconto teve resultado levemente pior, não melhor. Não há sinal de retorno em nenhuma direção.

### O cliente provavelmente compraria de qualquer forma

O terceiro teste mede a elasticidade: o quanto a quantidade vendida reage ao preço, numa regressão que compara cada produto consigo mesmo ao longo do tempo, isolando o efeito do preço do resto do catálogo. O resultado é uma elasticidade praticamente zero, com intervalo de confiança estreito o bastante para excluir qualquer elasticidade relevante de varejo.

O mesmo aparece olhando só para o desconto, o jeito mais visível de o cliente perceber uma mudança de preço:

| Faixa de desconto | Quantidade média por pedido | Margem realizada |
|---|---|---|
| Sem desconto | 3,51 | 55,09% |
| Até 10% | 3,56 | 51,79% |
| 10% – 20% | 3,54 | 45,81% |
| 20% – 30% | 3,49 | 38,99% |
| 30% – 40% | 3,51 | 28,54% |

A quantidade fica praticamente constante — entre 3,49 e 3,56 unidades — em todas as faixas de desconto. A margem, no mesmo intervalo, cai 26,55 pontos percentuais. O desconto não move volume: ele só transfere margem do pedido para o cliente, sem trazer nada em troca. É o mesmo padrão que gera o custo de frete descrito no diagnóstico — outro sinal de que o desconto de hoje funciona como custo, não como incentivo.

### O calendário separa desconto de volume

Se o desconto não gera volume no pedido médio, a pergunta seguinte é se ele funciona em algum momento específico — nas datas de calendário comercial forte. A resposta separa duas situações que a empresa hoje trata como uma só.

| Data | Traz volume extra | Desconto aplicado | Margem |
|---|---|---|---|
| Dia das Mães | Sim | De rotina | Dentro do normal |
| Natal | Sim | De rotina | Dentro do normal |
| Dia do Consumidor | Sim | De rotina | Dentro do normal |
| Black Friday | Não é o que explica o desconto aplicado | Pesado | Sai do normal |

Nas três datas em que o volume de fato aumenta, o desconto usado é o de rotina — o volume vem de outro lugar, não do desconto. Na única data em que a empresa desconta pesado, a Black Friday, a margem também é a única que sai da faixa normal. A empresa desconta mais justamente na data em que descontar tem menos evidência de funcionar e mais evidência de custar.

### O mesmo vazamento se repete produto a produto

O padrão que aparece no agregado — desconto sem critério e sem retorno mensurável — se repete dentro do catálogo, produto por produto, sem que ninguém veja o conjunto. Cada perda isolada é pequena. Somada no catálogo inteiro, é uma fração relevante da margem, mas só aparece quando alguém olha SKU por SKU — o que hoje não é rotina de gestão.

O conjunto desses resultados converge para uma única leitura: não é "desconto alto demais". É a ausência de uma camada que veja, produto a produto e em tempo real, o preço, a resposta do cliente e o contexto de mercado juntos. Isso se resolve dando à Vértice inteligência de precificação.

## 3. Solução proposta: plataforma de inteligência de precificação

A plataforma ataca diretamente a ausência descrita na síntese anterior. Ela cruza dado interno — venda, custo, estoque, desconto aplicado — com dado externo — preço de concorrentes, tráfego do site, pesquisa de mercado, novos entrantes — para sugerir o preço ideal por produto, indicar o melhor momento para desconto ou cupom, e medir quanto da margem máxima possível está sendo de fato capturada em cada produto.

Essa inteligência chega ao usuário em cinco telas, cada uma respondendo a uma pergunta diferente sobre a mesma decisão de preço.

| Tela | Conteúdo |
|---|---|
| Dashboard | Visão executiva consolidada |
| Diagnóstico da Margem | Waterfall de receita/desconto/custo/frete, índice de aproveitamento de margem por categoria, e a leitura estratégica de anomalia — é aqui que mora o aprendizado do tipo Black Friday |
| Oportunidades | Consolidado único de tudo que a IA sugere: subir/reduzir preço, desconto, cupom, agendamento sazonal |
| Produtos | Catálogo navegável com custo, margem, preço de concorrente, pedidos, elasticidade, preço atual × sugerido e comparação com concorrentes |
| Regras, Descontos e Cupons | O que está vigente hoje, organizado em subabas |

```
Dashboard → Diagnóstico da Margem → Oportunidades → Produtos → Regras, Descontos e Cupons
  visão          causa              ação sugerida     detalhe      governança vigente
```

A essas cinco soma-se uma sexta, de administração — Dados e conexões —, onde as fontes que alimentam a plataforma são cadastradas e monitoradas. Ela não responde a nenhuma pergunta de preço; existe porque o dado precisa de um dono, e esse dono não é quem decide o preço.

A tela de Diagnóstico da Margem decompõe o resultado do jeito que a seção 1 exigiu: em cascata, do topo até a margem de fato capturada.

```
Receita
  − Desconto
  − Custo do produto (CMV)
  − Frete
  = Margem de contribuição
```

A leitura dessas cinco telas não é manual: duas frentes de IA processam o cruzamento de dado e entregam o conteúdo de cada uma.

| Agente | Função |
|---|---|
| Pesquisa de mercado | Monitora preço de concorrente, tráfego do site (referência de mercado: tipo SimilarWeb), pesquisa de mercado e novos players entrando na categoria |
| Análise de dados | Cruza dado externo e interno, gera as Oportunidades e a leitura de Diagnóstico da Margem, analisa pedido e estoque para sugerir preço por produto |

Nem todo time vê tudo isso. A plataforma tem três perfis de acesso, e a separação entre eles é o principal controle de governança da solução: quem decide preço não é quem alimenta o dado, e quem monta campanha consulta a regra sem poder mexer nela.

| Perfil | O que acessa | O que pode fazer |
|---|---|---|
| Comercial | As cinco telas de decisão | Decide sobre as sugestões, aplica preço e desconto, cria e altera regras e cupons |
| Dados/pricing | Dados e conexões | Insere e mantém as fontes que alimentam a plataforma; não decide preço |
| Marketing | Regras, Descontos e Cupons | Somente visualização — consulta o que está vigente antes de montar campanha, sem alterar nada |

Nenhuma sugestão de IA vira preço sem passar pelo Comercial, e a fonte de dado que gera essa sugestão é responsabilidade declarada de outro perfil.

## 4. Business Case

A plataforma descrita sustenta dois tipos de valor: um problema de desconto que existe agora e pode ser contido de imediato, e um ganho estrutural que só a operação contínua da plataforma entrega. Os dois juntos formam o business case.

### O quick win: por que um teto de 20%

O problema imediato já está medido na seção 2: o desconto concedido hoje tem mediana de 22,92% por item, varia de 5% a 40%, e não segue nenhum critério. Um teto de desconto ataca esse problema sem esperar a plataforma inteira: acima do teto, o excedente vira margem; abaixo dele, nada muda.

O valor de cada teto possível foi medido diretamente nos 24.454 pedidos da base — não é projeção de comportamento futuro, é a soma do que teria sido recuperado se o teto já estivesse em vigor.

| Teto de desconto | % dos itens com desconto afetados | Recuperado/ano | % da margem anual |
|---|---|---|---|
| 30% | 28,75% | R$ 85.555 | 1,01% |
| 25% | 43,42% | R$ 193.328 | 2,29% |
| 20% | 58,54% | R$ 345.244 | 4,08% |
| 15% | 72,25% | R$ 540.093 | 6,39% |
| 10% | 86,12% | R$ 776.466 | 9,18% |

Quanto mais apertado o teto, maior a margem recuperada — e maior o número de pedidos afetados de uma vez. Um teto de 10% recupera R$ 776 mil, mas mexe em 86% de todos os itens com desconto no primeiro dia: abrupto demais para ser o primeiro passo. Um teto de 30% é pouco abrupto, mas recupera pouco mais que o piso de materialidade usado neste case. O teto de 20% fica no meio: já recupera 4,08% da margem anual — mais de quatro vezes esse piso —, afetando 58,54% dos itens com desconto, sem zerar o desconto em nenhum deles, só cortando o que está acima da própria mediana da política atual.

O número converge por um segundo caminho, independente do primeiro: supondo que a empresa capture 25% de todo o desconto hoje concedido no ano (R$ 1,35 milhão), o resultado é R$ 338.411 — a menos de R$ 7 mil do valor do teto de 20%. Duas contas, feitas de formas diferentes, chegando perto do mesmo número.

O valor exato do teto — 20%, e não 25% ou 15% — é uma escolha de política comercial, não uma medição, e segue pendente de validação com a área comercial antes de ir ao ar.

| Componente | Impacto anual |
|---|---|
| Teto de desconto de 20% | R$ 345.244 |
| Correção da regra de frete (componente determinístico, grau B) | R$ 15.970 |
| **Total** | **≈ R$ 361 mil (≈ 4,3% da margem anual)** |

### O valor que só se mede com o uso

Os R$ 361 mil acima vêm de um catálogo fixo, numa janela de tempo fechada — o retrato de um período que já aconteceu. Eles não incluem o segundo tipo de valor da plataforma, que por definição não dá para calcular hoje: quanto ela vai gerar daqui para frente, mês a mês, à medida que o catálogo e as campanhas mudam.

O índice de aproveitamento de margem por produto, na tela Diagnóstico da Margem, existe para isso: recalcula todo mês, para cada SKU, quanto da margem que o preço de tabela promete está sendo de fato capturado. Um produto lançado no mês que vem, com um desconto de campanha que ninguém revisa depois, hoje só aparece como vazamento na próxima vez que alguém olhar o catálogo inteiro manualmente — o que, como mostrou a seção 2, não é rotina de gestão. Com o índice ativo, o mesmo produto aparece no mês em que o vazamento começa.

Por isso esse valor só se mensura com o uso: não é um número fixo como os R$ 361 mil, é uma taxa de detecção que se acumula mês a mês, e seu tamanho depende de quantos vazamentos novos aparecem no catálogo — o que só se sabe rodando a plataforma.

## 5. Roadmap — do esboço à operação em 90 dias

Capturar o valor do Business Case depende de duas coisas que andam juntas: construir a plataforma e fazer os times usarem. O que existe dela hoje é um esboço navegável — a solução de pé, tela a tela, com dado estático da base deste case. É o bastante para validar a experiência com quem vai decidir preço, e não é o bastante para operar: não há integração com as bases da Vértice, agente em execução nem teste com usuário. A primeira fase existe para fechar essa distância antes de qualquer investimento em construção.

O sequenciamento parte de um princípio: o dinheiro não espera o software. Dos R$ 361 mil medidos na seção 4, R$ 345 mil vêm de uma decisão comercial que entra em quinze dias, sem depender de nenhuma tela ficar pronta — é esse resultado que sustenta a construção do resto. Os prazos abaixo são uma premissa de sequenciamento proposta neste case, não um compromisso validado; o esforço e a equipe ganham número ao fim da Fase 1.

```
Quick win: teto de desconto de 20%                       dias 1–15
        │
        ▼
Fase 1 — validação do esboço com os três times           dias 1–30
        │
        ▼
Fase 2 — integração do dado e primeiro agente de IA      dias 30–90
        │
        ▼
Fase 3 — agente de mercado e sugestão de preço           após o dia 90
        │
        ▼
Fase 4 — cupom e agendamento sazonal                     após a Fase 3
```

No fim dos 90 dias a Vértice tem duas coisas que hoje não tem: o vazamento de desconto contido e a plataforma em operação, mostrando mês a mês, produto a produto, quanto da margem prometida pelo preço de tabela está sendo de fato capturada.

### O quick win não espera a plataforma

O primeiro resultado é o teto de desconto de 20%, com impacto de ~R$ 345 mil/ano (racional na seção 4). É uma regra comercial, não um software: acima do teto o excedente vira margem, abaixo dele nada muda. Por isso entra na segunda semana, enquanto o resto é validado e construído — e cada mês de espera custa cerca de R$ 29 mil da margem que ele recuperaria. A forma de aplicá-lo — regra na plataforma de venda, política de cupom, alçada de exceção — se define com Comercial e TI na primeira semana.

| KPI | Meta | Prazo de referência |
|---|---|---|
| % de pedidos com desconto acima de 20% | Zero | Dias 1–15 |
| Margem recuperada vs. baseline | Acompanhamento contínuo | A partir do dia 15 |

### Fase 1 — validar o esboço antes de construir

Roda em paralelo ao quick win, por uma razão comercial direta: plataforma que o time não usa não recupera margem nenhuma. O maior risco deste projeto não é técnico, é de adoção, e a forma mais barata de reduzi-lo é sentar com os três times na frente do esboço antes de a primeira linha ser escrita. Ajustar uma tela em protótipo custa horas; ajustar depois de construída custa semanas.

| O que se valida | Com quem |
|---|---|
| Se as telas respondem à decisão real de cada time — hierarquia da informação, navegação, nomes, leitura em celular | Comercial, Marketing e Dados/pricing, em tarefa real do próprio time |
| Se os três perfis de acesso cobrem quem de fato decide preço | Os três times e quem responde pela política comercial |
| Quais fontes internas existem, com que qualidade e frequência | TI |
| Se há fonte viável de preço de concorrente e tráfego, a que custo | TI e Compras |
| A evaluation dos agentes — o conjunto de testes e os limiares de aceite da saída da IA | Dados/pricing |

A fase entrega o escopo confirmado, o protótipo revisado e a estimativa de custo, equipe e prazo. É o ponto em que o projeto ganha número de investimento e a diretoria decide seguir, reduzir o escopo ou parar — com a conta na mesa, e não antes dela.

### Fase 2 — o dado da Vértice e o primeiro agente

É a fase que instala a capacidade que falta hoje, e ela tem uma ordem que não se inverte: o dado entra primeiro, o agente é construído em cima dele. Uma IA montada sobre base que ainda não reconcilia produz recomendação que ninguém consegue conferir, e recomendação que não se confere não vira decisão de preço.

| Etapa | O que entra | Prazo de referência |
|---|---|---|
| Integração | Conectores com a plataforma de e-commerce, o ERP e as bases de estoque e marketing; carga do histórico; tela Dados e conexões | Dias 30–60 |
| Conferência | Os indicadores recalculados dentro da plataforma, batendo com os números desta análise | Dias 50–75 |
| Inteligência | Agente de Análise de dados sobre dado interno; telas Diagnóstico da Margem, Regras e Dashboard; os três perfis de acesso | Dias 60–90 |

Dos dois agentes da seção 3, só o de Análise de dados cabe aqui, e a diferença é a dependência externa: ele lê a cascata de margem, calcula o índice de aproveitamento por SKU e sinaliza a anomalia do tipo Black Friday usando apenas dado da casa. O de Pesquisa de mercado depende de uma fonte contratada, que é a parte mais incerta da solução, e por isso fica para a Fase 3. O corredor de desconto por categoria, que substitui o teto único por um limite calibrado para cada categoria, entra na última etapa, com o piloto rodando no Comercial sobre dado real.

Para seguir à fase seguinte, três coisas precisam estar provadas: os números da plataforma batem com os desta análise, o agente passa na evaluation desenhada na Fase 1, e o Comercial opera o piloto sem apoio do time técnico.

| KPI | Meta | Prazo de referência |
|---|---|---|
| Indicadores da plataforma conferidos contra esta análise | 100% dos indicadores-chave | Dia 75 |
| % de SKUs abaixo do piso de margem saudável (45%) | Redução vs. baseline | A partir do corredor |
| Comercial operando o piloto sem apoio técnico | Sim | Dia 90 |

### Fases 3 e 4 — do mercado ao calendário

A Fase 3 entra com o agente de Pesquisa de mercado, os conectores de dado externo e as telas de Oportunidades e Produtos completas — o momento em que a plataforma deixa de mostrar a margem e passa a recomendar preço. A reprecificação começa num subconjunto de SKUs contra um grupo de controle, e só é generalizada depois de comparar os dois: é assim que a Vértice descobre, com número próprio, como o cliente dela responde a preço. A Fase 4 fecha com cupom e agendamento sazonal, a camada que depende dos dois agentes estáveis, e cuja primeira prova vem na data de calendário forte seguinte — exatamente o ponto em que a seção 2 mostrou a empresa descontando pesado sem retorno.

| Fase | KPI | Prazo de referência |
|---|---|---|
| 3 | Cobertura de preço de concorrente sobre o catálogo | Na entrada da fase |
| 3 | % de sugestões aceitas · margem dos reprecificados vs. grupo de controle | Contínuo |
| 4 | Margem na próxima data forte vs. o mesmo período no ano anterior | Primeira data forte |

### Evaluation dos agentes

A plataforma vai sugerir preço a quem hoje decide por experiência, e essa confiança se constrói com evidência. É o que faz a evaluation dos agentes — o conjunto de testes que mede se a saída da IA presta antes de ela chegar a quem decide — ser requisito, e não etapa opcional de qualidade. A Vértice tem uma vantagem rara para montá-la: já existe gabarito. A base de 24.454 pedidos e os números desta análise dizem o que é verdade no período — a margem de 53,2% a 54,9%, os R$ 345.244 do teto de 20%, a anomalia da Black Friday. O agente roda contra esse período e é conferido contra o que já se sabe, antes de opinar sobre qualquer decisão futura. O que ele entrega, porém, não se avalia tudo do mesmo jeito.

| O que o agente entrega | Evaluation aplicada |
|---|---|
| Número — cascata de margem, índice por SKU | Bate com esta análise, ou é defeito; não há calibragem aqui |
| Alerta — "este produto está vazando margem" | Precisão e cobertura medidas contra casos conhecidos do histórico, calibradas para errar pouco para mais, porque alarme falso é o que faz o time parar de olhar a ferramenta |
| Recomendação e texto — "suba o preço para R$ X" | Revisão por amostra do time de Dados/pricing, com uma regra inegociável: toda afirmação numérica rastreável a um número da base |

A evaluation não acontece uma vez. Ela se repete a cada mudança de modelo, de instrução ou de fonte de dado — sem isso o agente degrada em silêncio — e em operação três indicadores mostram se ele continua entregando: quanto o Comercial rejeita, quanto aparece como sugestão incompleta por falta de lastro, e a margem dos produtos com sugestão aplicada contra o grupo de controle. O último é o que separa uso de resultado — taxa de aceite não prova qualidade, porque um time pode aceitar sugestão ruim justamente por confiar na ferramenta.

### Quem aprende o quê, e quando

Cada time é treinado no perfil de acesso que tem na seção 3, e só quando a tela que ele usa está no ar — o que mantém o treinamento curto, porque ninguém aprende função que não vai exercer. A ordem segue a construção, não a hierarquia: Dados/pricing vem primeiro porque é esse time que liga as fontes e confere a IA antes de qualquer outra pessoa ver uma recomendação.

| Time | O que aprende | Prazo de referência |
|---|---|---|
| Dados/pricing | Conectar e manter as fontes internas, e revisar a saída da IA antes de ela chegar ao Comercial | Dias 30–60 |
| Comercial/Gerência | Sustentar o teto; depois, ler o índice de aproveitamento de margem, decidir sobre as sugestões e calibrar o corredor por categoria | Teto: dias 1–15. Plataforma: a partir do dia 60 |
| Marketing | Consultar o que está vigente antes de montar campanha, e por onde pedir alteração | A partir do dia 90 |

## 6. Governança e Riscos

O rollout gradual da seção anterior já é, em si, resposta ao maior risco de adoção — mas a plataforma carrega outros riscos, de dado, de viés, de comportamento dos agentes e de dependência externa, que também precisam de controle declarado. O mapeamento abaixo é a primeira versão dessa governança, ainda em validação com as áreas de negócio envolvidas.

| Risco | Descrição | Controle |
|---|---|---|
| Qualidade de dado | Bases internas não reconciliam entre si (marketing, estoque) | Conector sem lastro aparece vazio e visível, nunca preenchido com estimativa |
| Viés | Sugestão de preço/desconto pode replicar um desequilíbrio já existente no histórico — ex.: categoria que sempre teve desconto alto continuar recebendo desconto alto por inércia | Corredor por categoria revisado periodicamente pelo time Comercial, não decidido só pela IA |
| Alucinação | Os agentes de IA podem gerar sugestão de preço ou leitura de mercado sem lastro real, sobretudo quando falta dado externo (concorrência, tráfego) para parte do catálogo | Três camadas, porque evaluation mede e não impede. Prevenção: o número exibido vem do cálculo da plataforma, não da geração do modelo, e produto sem dado suficiente aparece como sugestão incompleta em vez de estimada. Detecção: a evaluation da seção 5 mede a taxa em que isso ainda falha e decide se o agente entra e permanece em operação. Contenção: a plataforma recomenda e não altera preço no canal de venda, então nem uma alucinação que escape das duas primeiras vira preço sem decisão do Comercial |
| Agente sem critério de aceite | Um agente pode entrar em operação sem que ninguém tenha definido o que é uma saída boa, e aí não há como saber se ele ajuda ou atrapalha | A evaluation da seção 5 define como cada tipo de saída é medido; o conjunto de testes e os limiares de aceite são entregáveis da Fase 1, antes de qualquer construção, e a passagem para as fases seguintes depende deles |
| Degradação silenciosa | Um agente que funcionava pode piorar depois de uma troca de modelo, de instrução ou de fonte — e o primeiro sinal seria o time deixando de aceitar as sugestões, tarde demais | A evaluation se repete a cada uma dessas mudanças, e três indicadores acompanham o agente em operação: rejeição pelo Comercial, sugestão incompleta por falta de lastro, e margem dos reprecificados contra o grupo de controle |
| Dependência de terceiro | Fonte de dado externo (tipo SimilarWeb) pode mudar de preço, cobertura ou ficar indisponível | A plataforma segue operando com o restante do dado interno se o conector externo cair |
| Adoção | Os times passam a operar com apoio de dado onde antes decidiam por instinto — maior risco é organizacional | O roadmap da seção 5 é gradual, por time, começando pelo quick win já comprovado |
| Privacidade/regulatório | A plataforma sugere preço/desconto por produto e categoria | Nunca personalizado por perfil individual de cliente — evita conflito com CDC/LGPD |
