# Planejamento do projeto — Case Vértice Retail

## O que o case pedia

**Desafio central**, colocado pela diretoria da Vértice (CEO, CFO, CMO, COO):

> "Como podemos usar dados e IA para melhorar rentabilidade, eficiência operacional e qualidade da tomada de decisão nos próximos 90 dias?"

**Entregáveis esperados:** diagnóstico executivo, análises e insights, dashboard de gestão, protótipo de IA, business case, roadmap 30-60-90 e governança/riscos, consolidados numa Apresentação Final.

## As etapas que definimos no início

Estruturamos o trabalho em 5 macro-etapas:

1. **Entender o problema e formular a pergunta central.**
2. **Analisar os dados** — perfilar o data room, tratar anomalias, montar a árvore de hipóteses, testar cada hipótese cruzando as bases, dimensionar a oportunidade financeira dos achados priorizados.
3. **Construir a solução de IA** — escolher e montar o módulo conectado ao achado priorizado.
4. **Consolidar a entrega** — dashboard de KPIs, business case, roadmap, governança/riscos.
5. **Montar a Apresentação Final**, seguindo o roteiro do case.

Regras de trabalho fixadas desde o início e mantidas até o fim: não inferir dado ausente (nulo é reportado, nunca preenchido), tratar outliers antes de qualquer média/taxa, testar um padrão em outro corte antes de aceitá-lo como explicação, todo número rastreável a um script, e premissas de dimensionamento sempre declaradas.

## O que foi de fato executado

**Etapa 1 — pergunta central.** A pergunta de partida do case ("por que a Vértice cresce em receita/pedidos mas perde rentabilidade, e essa perda é generalizada ou concentrada?") foi testada nos dados e **refutada**: a margem por pedido é estável (53,2%–54,9% ao longo de 2023, sem tendência). Essa refutação é o achado que reorienta toda a análise — não um erro de partida.

A pergunta foi então **reformulada**, a partir do que os dados de fato mostraram:

> A margem por pedido é estável, mas a maior decisão de preço da empresa — o desconto, R$ 1,35 mi/ano — é tomada sem regra e sem retorno mensurável, e ainda dispara um custo de frete escondido. Quanto vale instituir essa regra?

**Etapa 2 — análise dos dados.** Perfilamos as 5 bases e tratamos as anomalias (`02_perfilamento_e_qualidade_dados/`), depois testamos uma árvore de hipóteses ligada ao case, com foco em margem e receita (`03_hipoteses_margem_e_receita/`) e, de forma complementar, em atendimento, estoque e clientes (`03_hipoteses_margem_e_receita/outras_frentes_testadas.md`). Nenhuma isoladamente chegou perto do tamanho do problema — o maior achado ficava abaixo de 1% da margem anual. Por isso a análise foi além da árvore de hipóteses: olhando diretamente para a estrutura dos dados (decomposição de variância, correlação, importância de variável, clustering), sem partir de hipótese nenhuma, a alavanca real apareceu — o desconto concedido sem regra (`04_alavanca_definitiva/`).

**Etapa 3 e 4 — solução e consolidação.** A pesquisa de precificação, o MVP da plataforma e o dashboard de gestão foram construídos, mas **não fazem parte desta entrega** — vão em arquivo(s) separado(s), por decisão do Davi. O business case e o roadmap 30-60-90 foram consolidados no documento final, em `05_documento_final/` desta pasta.

**Etapa 5 — Apresentação Final.** Tem entrega em data posterior à desta pasta e **ainda não foi produzida** na versão final; por isso fica fora desta entrega.

## Como ler esta pasta

```
01_planejamento_do_projeto/        → este documento
02_perfilamento_e_qualidade_dados/ → as 5 bases, tratamento, premissas
03_hipoteses_margem_e_receita/     → a árvore de hipóteses testada, focada em margem/receita
04_alavanca_definitiva/            → como se chegou ao desconto sem regra, direto nos dados
05_documento_final/                → diagnóstico, business case, roadmap e governança consolidados
```

Cada pasta de 02 a 04 tem um `racional.md` com o raciocínio, os achados e a conclusão da etapa, e uma subpasta `scripts/` com os códigos que geraram os números citados.
