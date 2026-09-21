# A alavanca definitiva

_Scripts: `scripts/05_lanterna_dados.py`, `scripts/05_cadeias_e_intersecoes.py`, `scripts/05_dimensionamento_alavancas.py`, `scripts/06_decisoes_resolvidas.py`. Relatórios completos: `reports/05_alavanca_definitiva.md`, `reports/06_decisoes_resolvidas.md`._

## Por que ir direto aos dados

As hipóteses testadas (`03_hipoteses_margem_e_receita/` e `outras_frentes_testadas.md`) produziram achados válidos, mas nenhum grande o bastante para justificar a consultoria: o maior ficava em ~0,8% da margem anual. Esta etapa não partiu de hipótese nenhuma — os próprios dados (decomposição de variância, correlação, importância de variável com corte temporal, clustering) apontaram onde olhar, usando as hipóteses já testadas só como memória de becos sem saída.

## O que a lanterna acendeu

Decompondo a variância da margem por item nos seus componentes contábeis:

| Componente | Média (% da receita bruta) | Contribuição para a variância da margem |
|---|---:|---:|
| Desconto | 8,03% | **49,84%** |
| Frete | 5,25% | **41,50%** |
| CMV | 39,98% | 8,66% |

**91,3% da variação de margem entre itens vem de duas linhas que são decisão da empresa** (desconto e frete), não característica do produto ou do cliente.

## As 3 alavancas

| # | Alavanca | Mecanismo | Pool/ano | Captura central/ano | % da margem anual | Grau |
|:---:|---|---|---:|---:|---:|:---:|
| 1 | **Desconto sem regra** | R$ 1,35 mi/ano concedidos sem nenhum atributo que explique quem recebe (AUC 0,4991, uma moeda honesta) e sem contrapartida em volume, aprovação, devolução ou recompra (8 testes, 0 sobreviventes) | R$ 1.353.643 | **R$ 345.244** (teto de 20%) | 4,08% | A / C |
| 2 | **Frete: limiar de R$ 250** | Fora do Marketplace, `receita líquida < R$ 250 ⇔ paga frete` acerta 100,0000% de 19.139 linhas — e o limiar é calculado **depois** do desconto. 530 itens só pagam frete porque o desconto cruzou a linha | R$ 277.970 | **R$ 15.970** (elo determinístico) | 0,19% | A / **B** |
| 3 | **Taxa de contato no atendimento** | 0,51 ticket por pedido, 97% em canal humano que não compra desfecho melhor | R$ 174.725 | **R$ 43.277** | 0,51% | A / C |
| — | _sem endereço_: devolução | — | R$ 1.676.665 | — | 19,83% | B |
| — | _sem endereço_: pagamento não aprovado | — | R$ 1.131.415 | — | 13,38% | A |
| — | _sem endereço_: CMV/markup | — | R$ 6.826.488 | — | 80,73% | A |

**Soma dos centrais: R$ 404.490/ano = 4,78% da margem anual.**

Devolução e pagamento não aprovado são os dois maiores pools do data room depois do CMV, mas ficam **sem endereço**: importância de variável zero em 12 atributos testados, e nenhum dos 4 cortes novos testados aqui (25 maiores clientes, por dia, por SKU, por decil de valor) encontrou concentração. CMV é o maior número (80,73% da margem) e o menos endereçável — o estoque não reconcilia com vendas (20,9×) e o custo de vendas não correlaciona com o custo do estoque, como já visto na análise de preço de referência.

## A distinção entre desfecho e decisão

A análise das hipóteses (pasta anterior) tinha fechado com "tamanho sem endereço de um lado, endereço sem tamanho do outro". A distinção que faltava é entre **desfecho** e **decisão**: devolução e pagamento não aprovado são desfechos do cliente (sem alavanca, confirmado por dois métodos independentes); o desconto é uma **decisão da empresa**, do mesmo tamanho, tomada 8.668 vezes, e cabe numa regra aplicada a um número pequeno de contas.

## A cadeia de 2 elos (por que desconto e frete não são achados separados)

Desconto reduz a receita líquida do pedido → receita líquida abaixo de R$ 250 aciona o frete → existe frete pago **por causa do desconto**, mensurável item a item (R$ 15.970/ano). É por isso que o valor do frete não é somado duas vezes: o efeito do desconto já está contado na alavanca 1.

**Confirmado em outro corte:** olhando só margem por canal, sem essa cadeia, o pior desempenho do Marketplace já apontava para frete, não desconto — achado que a Fase 4 do dashboard confirmou de outro ângulo: o frete explica 109% do gap de margem do Marketplace (R$ 134 mil/ano), e sem ele o canal passaria de pior para 2º melhor margem dos 7.

## Decisões resolvidas em 15/09/2026 (o que mudou de número)

- **Robustez da alavanca 1:** descartando os 2 `customer_id` que concentram 61% dos itens (anomalia já declarada na etapa de qualidade), a captura central cai de R$ 345.244 para **R$ 141.013/ano** — e ainda passa na régua de materialidade de 1% nos dois denominadores possíveis. Os IDs não foram removidos da base (excluiria 61% da leitura de margem); mudou a narrativa: o eixo passou a ser a unicidade da regra, não a concentração de contas.
- **Alavanca 3 caiu para R$ 43.277/ano**, porque o eixo de redução de taxa de contato (20%) não tinha nenhum lastro na base — saiu do cenário central e virou meta de operação.
- **Headline da alavanca 2 passou a ser o componente determinístico** (R$ 15.970/ano, grau B) — a única captura do projeto que vem de regra testada, não de suposição de comportamento.

## A ressalva que não sai do slide

Todos os testes de eficácia do desconto são **condicionais ao pedido existir** — a base não tem sessão, carrinho abandonado nem venda perdida. Está demonstrado que, dado que o pedido existe, o desconto não se associa a nada; **não** está provada elasticidade zero. Por isso nenhum cenário de captura usa 100% do pool.

## Recomendação proposta

> Abrir pelo desconto (maior número com dono), executar pelo frete (única captura grau B do projeto), sustentar pelo atendimento (já tem módulo de IA associado e evidência de processo estável).

O desdobramento em solução (plataforma de precificação) e em dashboard de gestão não faz parte desta pasta — segue em entrega separada. O business case, o roadmap e a governança que decorrem desta alavanca estão consolidados em `../05_documento_final/`.
