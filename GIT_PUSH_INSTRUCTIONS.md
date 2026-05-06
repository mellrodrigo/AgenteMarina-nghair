# Marina - Instruções de Push para Git

Guia passo a passo para fazer push do código Marina para seu repositório GitHub.

---

## 📋 Pré-requisitos

- Git instalado localmente
- Conta GitHub
- Repositório criado: `AgenteMarina-nghair`
- SSH ou HTTPS configurado

---

## 🚀 Passo 1: Clonar o Repositório Localmente

Se ainda não tem o repositório localmente:

```bash
git clone https://github.com/seu-usuario/AgenteMarina-nghair.git
cd AgenteMarina-nghair
```

Ou, se já tem o repositório:

```bash
cd /caminho/para/marina
```

---

## 📁 Passo 2: Copiar Arquivos da Marina

Se estiver em um ambiente diferente, copie todos os arquivos:

```bash
# Copiar todos os arquivos do projeto Marina
cp -r /home/ubuntu/marina/* /caminho/para/AgenteMarina-nghair/

# Ou, se estiver no mesmo diretório
# Apenas continue para o próximo passo
```

---

## ✅ Passo 3: Verificar Status do Git

```bash
git status
```

Você deve ver algo como:

```
On branch main
Untracked files:
  (use "git add <file>..." to include in what will be committed)
        app/
        config.py
        requirements.txt
        README.md
        ...
```

---

## 📝 Passo 4: Adicionar Todos os Arquivos

```bash
# Adicionar todos os arquivos
git add .

# Ou adicionar seletivamente
git add app/
git add config.py
git add requirements.txt
# ... etc
```

---

## 💬 Passo 5: Criar Commit

```bash
git commit -m "feat: Implementar Marina - Agente de IA para NGHair

- Integração com WhatsApp via Evolution API
- Banco de dados com memória de clientes
- Sincronização com Trinks
- Agendamentos inteligentes
- IA com GPT-4
- Documentação completa
- Pronto para deployment em VPS Hostinger"
```

---

## 🔐 Passo 6: Configurar Remote (Se Necessário)

Se o remote ainda não está configurado:

```bash
# Adicionar remote
git remote add origin https://github.com/seu-usuario/AgenteMarina-nghair.git

# Ou, se já existe, verificar
git remote -v
```

---

## 🚀 Passo 7: Fazer Push

```bash
# Push para branch main
git push -u origin main

# Ou, se usar branch diferente
git push -u origin seu-branch
```

Se pedir autenticação:

**Opção 1: HTTPS (com token)**
```bash
# Usar seu token do GitHub como senha
# Gerar em: https://github.com/settings/tokens
```

**Opção 2: SSH (recomendado)**
```bash
# Configurar SSH
ssh-keygen -t ed25519 -C "seu-email@example.com"
# Adicionar chave pública em: https://github.com/settings/keys

# Depois fazer push normalmente
git push -u origin main
```

---

## 📊 Passo 8: Verificar no GitHub

1. Acesse: https://github.com/seu-usuario/AgenteMarina-nghair
2. Verifique se todos os arquivos estão lá
3. Confirme que o README.md aparece

---

## 🏷️ Passo 9: Criar Release (Opcional)

Para marcar uma versão estável:

```bash
# Criar tag
git tag -a v1.0.0 -m "Marina v1.0.0 - Release inicial"

# Push da tag
git push origin v1.0.0
```

Depois criar release no GitHub:
1. Vá para: https://github.com/seu-usuario/AgenteMarina-nghair/releases
2. Clique em "Create a new release"
3. Selecione a tag `v1.0.0`
4. Adicione descrição
5. Publique

---

## 📋 Checklist Final

Antes de considerar pronto:

- [ ] Todos os arquivos foram adicionados
- [ ] Commit foi criado com mensagem clara
- [ ] Push foi realizado com sucesso
- [ ] Arquivos aparecem no GitHub
- [ ] `.gitignore` está funcionando (`.env` não aparece)
- [ ] README.md está visível
- [ ] Nenhuma credencial no repositório

---

## 🔒 Segurança: Verificar Credenciais

**IMPORTANTE**: Certifique-se de que nenhuma credencial foi commitada:

```bash
# Procurar por credenciais
grep -r "OPENAI_API_KEY" .
grep -r "EVOLUTION_API_KEY" .
grep -r "TRINKS_PASSWORD" .

# Se encontrar, remover imediatamente!
git rm --cached .env
git commit --amend --no-edit
git push --force-with-lease origin main
```

---

## 📚 Estrutura do Repositório

Seu repositório `AgenteMarina-nghair` deve ter esta estrutura:

```
AgenteMarina-nghair/
├── app/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── main.py
├── data/
├── logs/
├── .env.example
├── .gitignore
├── config.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── test_marina.py
├── README.md
├── EXECUTIVE_SUMMARY.md
├── SETUP_HOSTINGER.md
├── DEPLOYMENT_CHECKLIST.md
├── QUICKSTART.md
├── TROUBLESHOOTING.md
└── GIT_PUSH_INSTRUCTIONS.md
```

---

## 🔄 Atualizações Futuras

Para fazer push de atualizações:

```bash
# Fazer mudanças no código
# ...

# Adicionar mudanças
git add .

# Criar commit
git commit -m "fix: Descrição da mudança"

# Fazer push
git push origin main
```

---

## 🆘 Problemas Comuns

### Erro: "fatal: not a git repository"

```bash
# Inicializar git (se necessário)
git init

# Adicionar remote
git remote add origin https://github.com/seu-usuario/AgenteMarina-nghair.git
```

### Erro: "Permission denied (publickey)"

```bash
# Configurar SSH
ssh-keygen -t ed25519
# Adicionar chave pública em GitHub Settings > SSH Keys
```

### Erro: "rejected ... non-fast-forward"

```bash
# Fazer pull primeiro
git pull origin main

# Depois push
git push origin main
```

### `.env` foi commitado acidentalmente

```bash
# Remover do histórico
git rm --cached .env
git commit -m "Remove .env from tracking"
git push origin main

# Adicionar ao .gitignore (já está)
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Update .gitignore"
git push origin main
```

---

## 📞 Próximos Passos

Após fazer push com sucesso:

1. **Compartilhar repositório** com sua equipe
2. **Documentar** como clonar e usar localmente
3. **Configurar CI/CD** (opcional) para testes automáticos
4. **Fazer deployment** seguindo `SETUP_HOSTINGER.md`
5. **Monitorar** e manter código atualizado

---

## 📖 Referências

- [Git Documentation](https://git-scm.com/doc)
- [GitHub Help](https://docs.github.com)
- [SSH Key Setup](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [Token Authentication](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

---

**Sucesso! 🚀 Seu repositório está pronto!**

---

**Última atualização**: Maio 2026  
**Versão**: 1.0.0
