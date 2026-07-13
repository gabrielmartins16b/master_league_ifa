# Master League - Gestão Financeira ⚽

App em Streamlit para controlar as finanças da sua Master League de eFootball:
clubes, elenco, transferências, patrocínios e histórico financeiro completo.

## Estrutura do projeto

```
eflm_app/
├── Home.py                        # ponto de entrada (streamlit run Home.py) = Dashboard
├── pages/
│   ├── 1_🏆_Ligas.py
│   ├── 2_🏟️_Clubes.py
│   ├── 3_👤_Jogadores.py
│   ├── 4_🔄_Transferencias.py
│   ├── 5_🤝_Patrocinios.py
│   └── 6_📒_Financeiro.py
├── core/
│   ├── __init__.py
│   ├── database.py     # conexão + criação de tabelas + migração
│   ├── queries.py       # todas as funções de leitura/escrita (regra de negócio)
│   └── state.py         # seletor de "liga ativa" (reutilizado em toda página)
├── data/
│   └── master_league.db  # criado sozinho na primeira execução
├── requirements.txt
├── .gitignore
└── README.md
```

## Como rodar

1. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

2. Rode o app (a partir da pasta `eflm_app/`):
   ```
   streamlit run Home.py
   ```

3. O navegador vai abrir automaticamente em `http://localhost:8501`. O menu de
   navegação entre as páginas aparece automaticamente na barra lateral (é o
   sistema nativo de multipágina do Streamlit, baseado na pasta `pages/`).

Os dados ficam salvos em `data/master_league.db` (SQLite), então tudo continua
salvo mesmo se você fechar o app.

## Fluxo de uso sugerido

0. **Ligas**: crie uma liga (ex: "Master League - Temporada 1"). Você pode ter quantas
   ligas quiser rodando em paralelo — cada uma com seus próprios clubes, jogadores e finanças,
   completamente isolados. Escolha a "Liga ativa" na barra lateral antes de mexer em qualquer outra aba.
1. **Clubes**: cadastre todos os clubes da liga ativa com o saldo inicial combinado entre os participantes.
2. **Jogadores**: registre o elenco atual de cada clube (ou deixe "Sem clube" para jogadores no mercado).
3. **Transferências**: quando um clube compra um jogador de outro (ou do mercado), registre aqui —
   o saldo dos dois clubes é ajustado automaticamente e o jogador muda de dono.
4. **Patrocínios**: lance os contratos de patrocínio de cada clube (o valor entra automaticamente no saldo).
5. **Financeiro**: veja o extrato completo de tudo que entrou e saiu, com filtro por clube,
   e baixe em CSV se quiser.
6. **Home (Dashboard)**: visão geral de saldos e últimas movimentações da liga selecionada.

### Sobre múltiplas ligas

A barra lateral sempre mostra um seletor "Liga ativa" (`core/state.py`). Tudo que
você faz nas outras páginas (Clubes, Jogadores, Transferências, Patrocínios,
Financeiro) é automaticamente filtrado e gravado dentro da liga selecionada —
então dá pra ter, por exemplo, uma "Liga A" e uma "Liga B" rodando na mesma
instalação do app, sem que os clubes ou o dinheiro de uma apareçam na outra.

Se você já tinha usado uma versão anterior do app (sem ligas), na primeira vez que
rodar essa versão o app cria automaticamente uma "Liga Padrão" e move todos os
clubes/jogadores existentes para dentro dela — nenhum dado é perdido (a migração
acontece em `core/database.py`, função `init_db()`).

### Sobre a organização do código

- `core/database.py`: conexão SQLite, criação das tabelas e migração automática.
- `core/queries.py`: todas as funções de leitura e escrita no banco — nenhuma
  página monta SQL diretamente, tudo passa por aqui.
- `core/state.py`: o seletor de "liga ativa" usado no topo de toda página.
- `Home.py` e cada arquivo em `pages/`: só cuidam da interface (formulários,
  tabelas, gráficos), chamando as funções de `core/`.

## Ideias para evoluir o app

- Adicionar autenticação simples (um "dono" por clube só edita seu próprio clube).
- Colocar limite de teto salarial (soma dos salários não pode passar de X).
- Registrar contratos de jogadores com duração (e alertar quando estiver perto de vencer).
- Hospedar no Streamlit Community Cloud (gratuito) para todo mundo da liga acessar
  pelo navegador, sem precisar rodar localmente — nesse caso, trocar o SQLite local
  por um banco externo (ex: Supabase/Postgres) para não perder dados a cada deploy.
- Adicionar gráficos de evolução de saldo ao longo do tempo (usando a tabela `financeiro`).
