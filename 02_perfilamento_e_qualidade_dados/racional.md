# Perfilamento e qualidade de dados

_Scripts: `scripts/01_perfilamento.py`, `scripts/02_tratamento_anomalias.py`._

## As 5 bases

| Base | Linhas | Período | Grão |
|---|---:|---|---|
| vendas | 27.759 | 2023-01-01 → 2024-01-26 | 1 linha = 1 item de pedido |
| marketing | 3.500 | 2023-01-01 → 2025-12-31 | 1 linha = 1 campanha |
| clientes | 15.000 | 1985-01-01 → 2025-12-28 (nascimento) | 1 linha = 1 cliente cadastrado |
| atendimento | 35.841 | 2023-01-01 → 2025-12-31 | 1 linha = 1 ticket |
| estoque | 5.000 | snapshot | 1 linha = 1 SKU |

`vendas.csv` é a única base restrita a 13 meses — as demais se estendem até 2025. **Toda análise que cruza vendas com outra base usa a janela de vendas** (2023-01-01 a 2024-01-26); fora dela, as outras bases só podem ser lidas isoladamente.

## Decisões de tratamento (nenhum nulo foi preenchido)

- **2 linhas corrompidas removidas** (identificador preenchido, ≥70% das demais colunas vazias): 1 em vendas (`ORD-072219`), 1 em atendimento (`TKT`). São as únicas remoções da limpeza.
- **491 itens (1,8%) com margem negativa e 4.127 (14,9%) devolvidos**: mantidos como sinal de negócio, não como erro — investigados na fase de hipóteses.
- **Coluna derivada `pagamento_aprovado`**: 3.304 itens (11,9%) com status Cancelado/Aguardando. Premissa registrada: excluir esses itens do cálculo de receita/margem *realizada*, mantendo a linha na base para não perder o volume bruto.
- **Marketing 'Orgânico' não é tráfego grátis nesta base**: 100% das 495 campanhas desse canal têm investimento > 0, na mesma ordem de grandeza dos canais pagos. Premissa registrada para não zerar CAC desse canal por engano.
- **`status_atendimento` está dessincronizado do fechamento real em 34,8% dos tickets** (12.488 marcados "não resolvido" já têm data de fechamento e nota CSAT preenchidas). O campo não foi sobrescrito — foi criada a coluna derivada `status_inconsistente`, e análises de SLA/backlog devem preferir `fechamento_registrado`.
- **`tempo_primeira_resposta = 0`** em 1.790 tickets: confirmado por teste que é 100% ChatBot (resposta automática), não erro de registro.
- **Nenhum outlier estatístico foi removido**: caudas largas mas plausíveis em todas as variáveis numéricas testadas; nenhum valor logicamente impossível (negativo onde não devia, desconto maior que a receita, data de fechamento antes da abertura).

## Dois alertas confirmados em cortes diferentes da base

- **Cobertura `clientes.csv` × `vendas.csv`**: só 2,3% dos clientes cadastrados aparecem em vendas (346 de 15.000) — o mesmo número que limita a análise de clientes mais adiante.
- **`marketing.csv` não é comparável a `vendas.csv`**: medido na janela comum, a base de marketing registra 1.504× o volume de conversões e 16,7× a receita declarada contra vendas reais; medido sobre a base completa, a discrepância de receita chega a 47×. As escalas mudam com a janela usada, mas a conclusão é a mesma nos dois cortes: CAC e ROAS de `marketing.csv` só valem dentro da própria base.

## Conclusão da etapa

O data room está internamente consistente (chaves únicas, sem órfãos entre as bases centrais) mas tem descasamento de período entre vendas e as demais bases, e pelo menos 3 sinais de negócio (margem negativa, devolução, pagamento não aprovado) que precisam ser investigados, não descartados como ruído. Essas decisões de tratamento são o piso sobre o qual toda a análise de hipóteses (pasta seguinte) foi construída.
