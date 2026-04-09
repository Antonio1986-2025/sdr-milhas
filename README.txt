Arquivos corrigidos para a Lara

Incluídos:
- agent.py
- main.py
- whatsapp.py
- database.py

Ajustes:
- envio de áudio via sendMedia
- remoção da thread no webhook
- buscar_ou_criar_lead blindado contra duplicidade
- tratamento mais robusto no agent

Observação:
O database.py foi gerado com base no uso mostrado nos seus arquivos e logs.
Se seu esquema no Supabase tiver nomes de tabela ou coluna diferentes, ajuste:
- leads
- mensagens
- followups
- campos: id, whatsapp, nome, etapa, status, lead_id, papel, conteudo, mensagem, agendado_em
