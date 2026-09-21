# Outras frentes testadas (resumo)

Além das hipóteses de margem/receita, também testamos atendimento, estoque, clientes e gestão. Nenhuma virou a alavanca central (todas ficam abaixo da régua de materialidade de 1% da margem anual, isoladas), mas os achados qualificam o diagnóstico e evitam redescobrir o mesmo caminho depois.

## Atendimento

O atendimento roda sem triagem e o canal caro não compra desfecho melhor: o tema do ticket não prevê o canal usado (p=0,42) e a taxa de resolução é praticamente igual em todos os canais (64,9–65,7%, p=0,96). ChatBot custa R$ 2 e responde em 1 min; canal humano custa R$ 15–45 e responde em 14 min — não há trade-off entre custo e satisfação, o canal mais barato tem também o CSAT mais alto. Dimensionamento da deflexão: R$ 26–61 mil/ano (0,31–0,72% da margem) — abaixo da régua de 1%.

O CSAT, aliás, **não mede qualidade de atendimento**: a nota varia 1,75 ponto entre categorias de problema, mas só 0,03 ponto entre ticket resolvido e não resolvido, com correlação nula (0,015) com o tempo de resposta — o que ela reflete é o assunto do ticket, não o tratamento dado a ele. Pela mesma razão, um classificador de texto não resolve nada aqui: são só 30 textos-modelo em 35.840 tickets, 5 por categoria e sem sobreposição, e a coluna `categoria_problema` já vem preenchida em 100% dos registros.

## Estoque

94 das 99 rupturas se concentram numa única célula — Beleza × lead time 41–60 dias (581 SKUs, 16,18% de ruptura contra 0–0,39% no resto). Fornecedor individual como causa foi refutado (p=0,24) — a alavanca é o prazo de reposição, não a identidade do fornecedor. Olhando a base de estoque de forma mais estrutural, o lead time é **estritamente bimodal** (nenhum SKU entre 21 e 40 dias), e a separação é por fornecedor inteiro, não por produto — nenhum dos 100 fornecedores mistura os dois grupos. Fornecedores lentos (≥41 dias) têm 48× mais ruptura que os rápidos, mas a mesma proporção de "estoque crítico": o lead time longo não faz o estoque cair mais rápido, impede é a recuperação depois.

Exposição financeira: R$ 65.782 por ciclo (0,78% da margem anual) — abaixo da régua. E **não é possível medir perda de receita por ruptura** com esta base: o retrato de estoque é posterior à janela de vendas (62,8% das últimas entradas depois do fim de vendas) e os SKUs hoje em ruptura venderam de forma estável durante toda a janela, sem nenhum rastro de ruptura nas vendas analisadas.

## Clientes

Cobertura de 2,31% entre `clientes.csv` e `vendas.csv` (346 de 15.000) fecha esse ramo como limitação de dado (C1) — qualquer segmentação que cruze as duas bases fica sem lastro transacional real.

Olhando `clientes.csv` isoladamente, sem cruzar com vendas, o `segmento_rfm` já vem coerente e ordena bem por LTV, e aparece um critério de direcionamento que nenhum corte por vendas havia mostrado: **geografia prevê valor**. O LTV médio de SP é 2,5× o de PE, com intervalos de confiança de 95% que não se sobrepõem, e o mecanismo é composição de segmento — correlação de 0,932 entre % de clientes Campeão+Fiel e LTV do estado — e não renda (correlação de 0,143, renda praticamente uniforme entre estados). É um achado estatisticamente sólido, mas **vive inteiramente dentro de `clientes.csv`** e não foi validado contra comportamento de compra real: deve ser tratado como hipótese de direcionamento a confirmar, não como fato sobre o comportamento do cliente Vértice, dada a mesma limitação de cobertura (2,3%) que fecha o ramo C1.

## Atraso de entrega, fornecedor e gestão/produtividade

- **Atraso de entrega:** sobe no agregado (+0,07 p.p./dia, p=0,004), mas não dentro do Marketplace isoladamente (p=0,28) — a faixa de 15–18 dias é 100% Marketplace, então o sinal agregado é efeito de composição de canal, não de atraso em si. Inconclusiva.
- **Defeito por fornecedor:** devolução homogênea por fornecedor (p=0,91) — mesmo padrão de homogeneidade visto na devolução em geral. Não testada de forma independente.
- **Gestão & produtividade:** não testável com os dados disponíveis; a evidência é qualitativa (fragmentação entre as 5 bases, já documentada na etapa de perfilamento).
