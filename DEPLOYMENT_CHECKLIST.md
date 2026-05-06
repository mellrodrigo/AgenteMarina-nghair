# Marina - Deployment Checklist

Use este checklist para garantir que tudo está configurado corretamente antes de fazer deploy em produção.

---

## ✅ Pré-Deployment

### Preparação do Repositório
- [ ] Código está no Git
- [ ] `.gitignore` está configurado
- [ ] Não há credenciais no repositório
- [ ] README.md está atualizado
- [ ] Versão está documentada (v1.0.0)

### Verificação de Código
- [ ] Testes passam localmente (`python test_marina.py`)
- [ ] Sem erros de linting
- [ ] Sem warnings críticos
- [ ] Documentação de código está completa
- [ ] Variáveis de ambiente estão documentadas

### Dependências
- [ ] `requirements.txt` está atualizado
- [ ] Todas as dependências foram testadas
- [ ] Versões pinadas (não usar `>=`)
- [ ] Sem dependências não utilizadas

---

## 🖥️ Preparação do Servidor VPS

### Acesso e Segurança
- [ ] SSH configurado
- [ ] Firewall ativado (UFW)
- [ ] Portas 80, 443, 8000 abertas
- [ ] Chaves SSH configuradas
- [ ] Senha root alterada

### Sistema Operacional
- [ ] Ubuntu 20.04+ instalado
- [ ] Sistema atualizado (`apt update && apt upgrade`)
- [ ] Python 3.11 instalado
- [ ] Git instalado
- [ ] Curl/Wget instalado

### Dependências do Sistema
- [ ] Build tools instalados
- [ ] PostgreSQL instalado (se usar)
- [ ] Redis instalado (opcional)
- [ ] Docker instalado (se usar)
- [ ] Nginx instalado

---

## 🔧 Configuração da Aplicação

### Clonagem e Setup
- [ ] Repositório clonado
- [ ] Diretório de trabalho criado
- [ ] Ambiente virtual criado
- [ ] Dependências instaladas
- [ ] Banco de dados inicializado

### Variáveis de Ambiente
- [ ] `.env` criado (não no Git!)
- [ ] `OPENAI_API_KEY` configurada
- [ ] `EVOLUTION_API_KEY` configurada
- [ ] `TRINKS_EMAIL` e `TRINKS_PASSWORD` configuradas
- [ ] `DATABASE_URL` configurada
- [ ] `API_WEBHOOK_URL` configurada com domínio correto
- [ ] `SECRET_KEY` gerada (usar `openssl rand -hex 32`)

### Banco de Dados
- [ ] PostgreSQL criado (se usar)
- [ ] Usuário de banco criado
- [ ] Permissões configuradas
- [ ] Tabelas criadas
- [ ] Dados iniciais inseridos (se necessário)

---

## 🌐 Configuração do Nginx

### Instalação e Configuração
- [ ] Nginx instalado
- [ ] Configuração de site criada
- [ ] Reverse proxy configurado
- [ ] Timeouts ajustados
- [ ] Gzip habilitado
- [ ] Logs configurados

### SSL/TLS
- [ ] Domínio apontando para VPS
- [ ] Certificado Let's Encrypt obtido
- [ ] Certificado configurado no Nginx
- [ ] Redirecionamento HTTP→HTTPS ativo
- [ ] Renovação automática configurada (certbot)

### Headers de Segurança
- [ ] X-Frame-Options configurado
- [ ] X-Content-Type-Options configurado
- [ ] X-XSS-Protection configurado
- [ ] Strict-Transport-Security configurado

---

## 🚀 Configuração do Serviço

### Systemd Service
- [ ] Arquivo `/etc/systemd/system/marina.service` criado
- [ ] User/Group configurado
- [ ] WorkingDirectory correto
- [ ] ExecStart correto
- [ ] Restart policy configurado
- [ ] Serviço habilitado (`systemctl enable marina`)
- [ ] Serviço iniciado (`systemctl start marina`)

### Monitoramento
- [ ] Logs configurados
- [ ] Rotação de logs configurada
- [ ] Alertas configurados (opcional)
- [ ] Monitoramento de processo ativo

---

## 🐳 Evolution API (Docker)

### Docker Setup
- [ ] Docker instalado
- [ ] Docker Compose instalado
- [ ] `docker-compose.yml` configurado
- [ ] Volumes criados
- [ ] Rede Docker criada

### Evolution API
- [ ] Container iniciado
- [ ] Porta 8080 acessível
- [ ] Instância criada
- [ ] QR code obtido
- [ ] WhatsApp conectado
- [ ] Webhook configurado

### Verificação
- [ ] `curl http://localhost:8080/health` retorna 200
- [ ] Webhook recebe eventos
- [ ] Mensagens são recebidas

---

## 🔗 Integração com Trinks

### Credenciais
- [ ] Email Trinks configurado
- [ ] Senha Trinks configurada
- [ ] Acesso testado manualmente

### Sincronização
- [ ] Scraper testado localmente
- [ ] Dados sincronizados com sucesso
- [ ] Agendamento de sincronização configurado
- [ ] Logs de sincronização monitorados

---

## 🧪 Testes de Integração

### API
- [ ] `GET /health` retorna 200
- [ ] `GET /` retorna informações da API
- [ ] `POST /webhook/whatsapp` aceita dados

### WhatsApp
- [ ] Mensagem de teste enviada
- [ ] Webhook recebe mensagem
- [ ] Resposta enviada de volta
- [ ] Múltiplas mensagens testadas

### Banco de Dados
- [ ] Cliente criado com sucesso
- [ ] Conversa salva com sucesso
- [ ] Agendamento criado com sucesso
- [ ] Dados recuperados corretamente

### IA
- [ ] Resposta gerada com sucesso
- [ ] Intenção classificada corretamente
- [ ] Memória de cliente funcionando
- [ ] Recomendações personalizadas

---

## 📊 Monitoramento e Logs

### Logs
- [ ] Logs sendo gerados em `/home/marina/logs/`
- [ ] Rotação de logs configurada
- [ ] Nível de log apropriado (INFO em produção)
- [ ] Sem erros críticos nos logs

### Monitoramento
- [ ] Verificar uso de CPU
- [ ] Verificar uso de memória
- [ ] Verificar uso de disco
- [ ] Verificar conexões de rede

### Uptime
- [ ] Serviço iniciado automaticamente após reboot
- [ ] Sem crashes nos últimos testes
- [ ] Tempo de resposta aceitável

---

## 🔐 Segurança

### Credenciais
- [ ] Nenhuma credencial em arquivo de código
- [ ] Todas as credenciais em `.env`
- [ ] `.env` não está no Git
- [ ] Permissões de arquivo corretas (600)

### Firewall
- [ ] UFW ativado
- [ ] Apenas portas necessárias abertas
- [ ] SSH em porta não-padrão (opcional)
- [ ] Rate limiting configurado

### Backups
- [ ] Backup do banco de dados agendado
- [ ] Backup do `.env` agendado
- [ ] Local de backup seguro
- [ ] Teste de restauração realizado

---

## 📈 Performance

### Otimizações
- [ ] Caching configurado
- [ ] Compressão Gzip ativada
- [ ] Índices de banco de dados criados
- [ ] Queries otimizadas

### Testes de Carga
- [ ] Teste com 10 requisições simultâneas
- [ ] Teste com 100 requisições simultâneas
- [ ] Tempo de resposta aceitável
- [ ] Sem erros sob carga

---

## 📞 Suporte e Documentação

### Documentação
- [ ] README.md completo
- [ ] SETUP_HOSTINGER.md atualizado
- [ ] Troubleshooting.md criado
- [ ] Runbook operacional criado

### Contatos
- [ ] Email de suporte configurado
- [ ] Telefone de emergência documentado
- [ ] Escalação de problemas definida

---

## ✨ Pós-Deployment (Primeiras 24h)

### Monitoramento Intensivo
- [ ] Monitorar logs a cada 1 hora
- [ ] Verificar performance
- [ ] Testar funcionalidades principais
- [ ] Estar disponível para suporte

### Validação
- [ ] Clientes conseguem enviar mensagens
- [ ] Marina responde corretamente
- [ ] Agendamentos funcionam
- [ ] Nenhum erro crítico nos logs

### Comunicação
- [ ] Informar cliente que está online
- [ ] Fornecer instruções de uso
- [ ] Agendar treinamento (se necessário)
- [ ] Obter feedback inicial

---

## 🎯 Critérios de Sucesso

Antes de considerar o deployment bem-sucedido, verifique:

- ✅ Todos os itens desta checklist marcados
- ✅ Nenhum erro crítico nos logs
- ✅ Tempo de resposta < 2 segundos
- ✅ Taxa de sucesso de mensagens > 99%
- ✅ Uptime > 99.9%
- ✅ Cliente satisfeito e treinado

---

## 📋 Assinatura

| Item | Responsável | Data | Assinatura |
|------|-------------|------|-----------|
| Preparação | _____________ | ___/___/___ | _____________ |
| Deployment | _____________ | ___/___/___ | _____________ |
| Testes | _____________ | ___/___/___ | _____________ |
| Aprovação | _____________ | ___/___/___ | _____________ |

---

**Última atualização**: Maio 2026  
**Versão**: 1.0.0
