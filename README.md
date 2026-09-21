# Case Vértice Retail — Entrega final

**Grupo 2** — Davi Cunha, Luanda Shibata. Mentoria: Gabriela Alves (EloGroup).

## O que esta entrega responde

O case pergunta como usar dados e IA para melhorar rentabilidade, eficiência operacional e qualidade da tomada de decisão nos próximos 90 dias. A hipótese de partida — a Vértice cresce em receita e perde rentabilidade — foi testada nos dados e refutada: a margem por pedido fica entre 53,2% e 54,9% ao longo de todo o 2023, sem tendência. Não há queda de margem a explicar.

A pergunta foi então reformulada a partir do que os dados mostraram. Decompondo a variação da margem item a item, 91,3% dela vem de duas linhas que são decisão da empresa, não característica do produto ou do cliente: desconto (49,84%) e frete (41,50%). E o desconto — R$ 1,35 milhão por ano — é concedido sem nenhum critério detectável (um modelo treinado para prever quem recebe acerta 0,4991, o mesmo que uma moeda) e sem contrapartida em volume, aprovação, devolução ou recompra. A entrega responde quanto vale instituir a regra que hoje não existe: um teto de desconto de 20% recupera R$ 345 mil/ano, e a correção da regra de frete, outros R$ 16 mil — cerca de 4,3% da margem anual, medidos sobre os 24.454 pedidos da base, não projetados.

## Como ler as pastas

```
01_planejamento_do_projeto/        → o que o case pedia, as etapas definidas e o que foi executado
02_perfilamento_e_qualidade_dados/ → as 5 bases, decisões de tratamento e premissas registradas
03_hipoteses_margem_e_receita/     → a árvore de hipóteses testada, com os vereditos
04_alavanca_definitiva/            → como se chegou ao desconto sem regra, sem partir de hipótese
05_documento_final/                → diagnóstico, solução, business case, roadmap e governança
solucao-proposta/                  → o esboço navegável da plataforma e o dashboard de gestão
```

As pastas 02 a 04 têm um `racional.md` com o raciocínio, os achados e a conclusão da etapa, e uma subpasta `scripts/` com os códigos que geraram os números citados. A ordem das pastas é a ordem em que o trabalho aconteceu: a pasta 03 fecha sem nenhum achado grande o bastante para justificar a consultoria (o maior ficava em ~0,8% da margem anual), e é por isso que a 04 existe.

Quem quiser só a conclusão pode ir direto a `05_documento_final/documento_final.md`, que consolida diagnóstico, solução, business case, roadmap 30-60-90 e governança num documento só. As frentes que foram testadas e não viraram a alavanca central — atendimento, estoque, clientes, gestão — estão resumidas em `03_hipoteses_margem_e_receita/outras_frentes_testadas.md`.

## A solução proposta

`solucao-proposta/index.html` é o esboço navegável da plataforma de inteligência de precificação, com as cinco telas de decisão mais a de administração de dados. `dashboard.html` é o dashboard de gestão, que abre sozinho e também aparece embutido na primeira tela da plataforma.

O modo mais confiável de abrir é servindo a pasta localmente, porque `index.html` carrega o dashboard num iframe e alguns navegadores bloqueiam isso em `file://`:

```
cd solucao-proposta
python -m http.server 8000
```

Depois, `http://localhost:8000/index.html`. Abrir o arquivo direto no navegador funciona para o `dashboard.html`; na plataforma, pode faltar o painel embutido.

É um esboço com dado estático da base deste case: serve para validar a experiência com quem vai decidir preço, não para operar. Não há integração com as bases da Vértice nem agente em execução — é exatamente essa distância que a Fase 1 do roadmap existe para fechar.

## Sobre os scripts

Os scripts são a rastreabilidade dos números, não um pipeline reexecutável nesta pasta: eles esperam o data room em `data/raw/` e `data/processed/`, que não acompanha a entrega. Rodam em Python com `pandas`, `numpy`, `scipy` e `scikit-learn`, e cada um grava o próprio log e as tabelas que sustentam o racional da etapa. Todo número citado nos documentos sai de um deles.
