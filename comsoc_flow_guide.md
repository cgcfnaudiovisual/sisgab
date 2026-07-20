# 🧭 Guia Orientador de Fluxo: COMSOC_IA

Este documento serve como a **diretriz mestre obrigatória** para qualquer Inteligência Artificial (ou desenvolvedor) que necessite realizar adições, modificações, correções ou refatorações no sistema **COMSOC_IA / COMCIA**.

---

## 🏗️ 1. Arquitetura Modular e Evitação de Arquivos Gigantes

Para garantir a facilidade de manutenção e evitar estouros de contexto ou lentidão em arquivos muito grandes:
1. **Limitação de Linhas:** Nenhum arquivo novo ou refatorado deve exceder **500 linhas de código**, a menos que seja estritamente inevitável.
2. **Pacotes e Módulos:** Funcionalidades complexas devem ser divididas em sub-arquivos. 
   - Exemplo: O bot do Telegram reside no pacote [telegram_bot](file:///x:/PROGRAMACAO/GABINETE/telegram_bot/) subdividido em lógica de comandos, layouts de teclado, tarefas agendadas e utilitários.
3. **Divisão de Responsabilidades:**
   - **Banco de Dados (Supabase):** Consultas complexas devem ser definidas em [database.py](file:///x:/PROGRAMACAO/GABINETE/database.py) ou no módulo correspondente de serviço.
   - **Telas NiceGUI:** Cada aba ou página principal do menu deve possuir seu próprio arquivo `.py` na raiz (ex: [comsoc_demandas.py](file:///x:/PROGRAMACAO/GABINETE/comsoc_demandas.py), [comsoc_cautela.py](file:///x:/PROGRAMACAO/GABINETE/comsoc_cautela.py), [comsoc_brindes.py](file:///x:/PROGRAMACAO/GABINETE/comsoc_brindes.py), [comsoc_noticias.py](file:///x:/PROGRAMACAO/GABINETE/comsoc_noticias.py)).

---

## 📂 2. Estrutura do Pacote Telegram Bot

O bot do Telegram foi fragmentado para evitar arquivos massivos. Qualquer alteração no bot deve seguir este mapeamento:

*   [telegram_bot/\_\_init\_\_.py](file:///x:/PROGRAMACAO/GABINETE/telegram_bot/__init__.py): Ponto de entrada do pacote. Inicializa e exporta as funções principais de controle de ciclo de vida (`init_bot` e `stop_bot`).
*   [telegram_bot/client.py](file:///x:/PROGRAMACAO/GABINETE/telegram_bot/client.py): Inicialização do `AsyncTeleBot` e configurações de conexão segura.
*   [telegram_bot/handlers_commands.py](file:///x:/PROGRAMACAO/GABINETE/telegram_bot/handlers_commands.py): Tratamento de comandos explícitos de texto (como `/start`, `/hoje`, `/cautelas`, `/ajuda`).
*   [telegram_bot/handlers_menu.py](file:///x:/PROGRAMACAO/GABINETE/telegram_bot/handlers_menu.py): Menus interativos, callbacks de botões inline e lógica de conversação/estado.
*   [telegram_bot/scheduled_jobs.py](file:///x:/PROGRAMACAO/GABINETE/telegram_bot/scheduled_jobs.py): Lógica do cron job diário ("Bom Dia") e o resumo semanal.
*   [telegram_bot/utils.py](file:///x:/PROGRAMACAO/GABINETE/telegram_bot/utils.py): Funções utilitárias como sanitização de texto, normalização de nomes de guerra e escape de caracteres markdown do Telegram.

---

## ⚡ 3. Convenções de Codificação

### NiceGUI & Frontend
*   **Restrição de Uploads:** O upload da página de "Entrega em Hot" ([comsoc_galeria.py](file:///x:/PROGRAMACAO/GABINETE/comsoc_galeria.py)) deve restringir e aceitar apenas formatos de imagem `.jpg` e `.jpeg` na propriedade de filtro do componente `ui.upload`.
*   **Estilo Premium:** Utilize a paleta de cores importada de [theme.py](file:///x:/PROGRAMACAO/GABINETE/theme.py). Evite cores HTML puras. Priorize elementos de tema escuro, bordas estilizadas (`rgba(0, 229, 255, 0.15)`) e tipografia moderna.
*   **Autenticação e Permissões:** Todas as novas páginas devem ser decoradas com o wrapper `build_layout` localizado em [main.py](file:///x:/PROGRAMACAO/GABINETE/main.py#L459-L478) para garantir que apenas usuários logados acessem a tela.

### Banco de Dados (Supabase)
*   **Consultas Seguras:** Sempre utilize a função `execute_query_safe` para rodar queries, garantindo retentativas automáticas e resiliência em caso de desconexão.
*   **Transição de Schema:** Não misture tabelas antigas em queries das novas tabelas diretamente sem garantir compatibilidade lógica de chaves estrangeiras.

---

## 🛠️ 4. Fluxo de Execução para a IA (Checklist de Modificações)

Sempre que receber uma tarefa de codificação:
1.  **Leia as tabelas necessárias** no Supabase e verifique se as migrações adequadas foram rodadas.
2.  **Verifique a existência do arquivo/módulo** correspondente. Se for modificar uma tela, faça-o em seu respectivo arquivo modular, nunca acumulando lógica em [main.py](file:///x:/PROGRAMACAO/GABINETE/main.py).
3.  **Use referências literais e caminhos absolutos** ao apontar para arquivos (`file:///x:/PROGRAMACAO/...`).
4.  **Execute testes unitários** no módulo modificado para garantir que não haja erros de importação ou de sintaxe.
5.  **Atualize o guia visual e o walkthrough** após a conclusão do trabalho para registrar o estado final.
