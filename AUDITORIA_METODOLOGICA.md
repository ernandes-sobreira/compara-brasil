# COMPARA BRASIL — Auditoria metodológica

Atualizado em 2026-10-06.

## Correções aplicadas

- removido o limite silencioso de 500 proposições no carregamento; a leitura agora pagina a coleção até um limite de segurança explícito de 10.000 registros;
- removido o limite silencioso de 2.000 votações pelo mesmo mecanismo;
- o gráfico anual agora usa o MESMO conjunto filtrado por tema/ano da análise;
- a interface deixou de apresentar os registros disponíveis como se fossem o total histórico da Câmara;
- partido ausente ou não reconhecido não é mais classificado automaticamente como “Centro”;
- a camada ideológica anterior e seus scores foram desativados até que haja fonte, versão, período e regra de harmonização auditáveis;
- status desconhecido não é mais convertido automaticamente em “tramitando”;
- temas inferidos por palavras-chave passam a ser identificados como heurísticos;
- posições agregadas S/N/D por partido são explicitamente separadas de orientações oficiais de bancada;
- incluída aba Auditoria com cobertura por ano, campos ausentes, concentração temporal e avisos de truncamento.

## Limitação ainda existente

O repositório contém a interface, mas não contém um pipeline reproduzível completo que demonstre como todas as coleções do Firestore foram originalmente preenchidas. Portanto, a aplicação agora trata o banco conectado como “registros disponíveis”, não como censo completo do período.

A próxima etapa técnica recomendada é construir um pipeline versionado de coleta da API oficial da Câmara, por ano, com temas oficiais, autores, tramitações, votações, votos e orientações, gravando também metadados de atualização e contagens de validação.

## Fonte oficial

- https://dadosabertos.camara.leg.br/api/v2
- endpoint de temas de proposições: /proposicoes/{id}/temas
- orientações de bancada: /votacoes/{id}/orientacoes
- votos individuais: /votacoes/{id}/votos
