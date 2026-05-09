/**
 * Marina - Agente de IA NGHair
 * Servidor unificado: WhatsApp + Gemini AI + Memória de Clientes
 * Versão 4.0 - Correção de mensagens duplicadas + Prompt aprimorado
 */

const makeWASocket = require('@whiskeysockets/baileys').default;
const { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, makeCacheableSignalKeyStore } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const pino = require('pino');

// ========== CONFIGURAÇÕES ==========
const SESSION_DIR = path.join(__dirname, 'sessions');
const DATA_DIR = path.join(__dirname, 'data');
const LOG_DIR = path.join(__dirname, 'logs');
const CLIENTS_FILE = path.join(DATA_DIR, 'clientes.json');

// API OpenAI-compatible (Gemini 2.5 Flash via Manus proxy)
const AI_API_KEY = 'sk-XbR65DLnm2wza2KsiXrXMV';
const AI_BASE_URL = 'https://api.manus.im/api/llm-proxy/v1';
const AI_MODEL = 'gemini-2.5-flash';
const PORT = 8080;

// Criar diretórios necessários
[SESSION_DIR, DATA_DIR, LOG_DIR].forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

// ========== LOGGER ==========
const logFile = path.join(LOG_DIR, 'marina.log');
function log(level, msg) {
    const ts = new Date().toISOString();
    const line = `[${ts}] [${level}] ${msg}\n`;
    process.stdout.write(line);
    try { fs.appendFileSync(logFile, line); } catch(e) {}
}

// ========== DEDUPLICAÇÃO DE MENSAGENS ==========
// Evita processar a mesma mensagem duas vezes (problema recorrente com Baileys)
const mensagensProcessadas = new Set();
function jaProcessou(msgId) {
    if (mensagensProcessadas.has(msgId)) return true;
    mensagensProcessadas.add(msgId);
    // Limpar cache após 5 minutos para não crescer indefinidamente
    setTimeout(() => mensagensProcessadas.delete(msgId), 5 * 60 * 1000);
    return false;
}

// ========== BANCO DE DADOS DE CLIENTES (JSON) ==========
let clientes = {};
if (fs.existsSync(CLIENTS_FILE)) {
    try { clientes = JSON.parse(fs.readFileSync(CLIENTS_FILE, 'utf8')); } catch(e) {}
}

function salvarClientes() {
    try { fs.writeFileSync(CLIENTS_FILE, JSON.stringify(clientes, null, 2)); } catch(e) {}
}

function obterCliente(numero, nome) {
    if (!clientes[numero]) {
        clientes[numero] = {
            numero,
            nome: nome || 'Cliente',
            primeiroContato: new Date().toISOString(),
            ultimoContato: new Date().toISOString(),
            totalMensagens: 0,
            historico: [],
            preferencias: [],
            servicosUsados: []
        };
        log('INFO', `Novo cliente: ${numero} (${nome})`);
    } else {
        clientes[numero].ultimoContato = new Date().toISOString();
        if (nome && nome !== 'Cliente') clientes[numero].nome = nome;
    }
    clientes[numero].totalMensagens++;
    salvarClientes();
    return clientes[numero];
}

function registrarConversa(numero, role, texto) {
    if (!clientes[numero]) return;
    const historico = clientes[numero].historico;
    historico.push({ role, texto, timestamp: new Date().toISOString() });
    // Manter apenas as últimas 20 mensagens
    if (historico.length > 20) historico.splice(0, historico.length - 20);
    salvarClientes();
}

// ========== AI (Gemini 2.5 Flash via API OpenAI-compatible) ==========
function chamarAI(messages) {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify({
            model: AI_MODEL,
            messages: messages,
            temperature: 0.7,
            max_tokens: 500
        });

        const url = new URL(AI_BASE_URL + '/chat/completions');
        const options = {
            method: 'POST',
            hostname: url.hostname,
            path: url.pathname,
            port: 443,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + AI_API_KEY,
                'Content-Length': Buffer.byteLength(body)
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const json = JSON.parse(data);
                    if (json.error) {
                        reject(new Error(json.error.message || JSON.stringify(json.error)));
                        return;
                    }
                    const text = json.choices?.[0]?.message?.content || '';
                    resolve(text.trim());
                } catch(e) {
                    reject(new Error('Erro ao parsear resposta: ' + data.substring(0, 200)));
                }
            });
        });

        req.on('error', reject);
        req.setTimeout(45000, () => { req.destroy(); reject(new Error('Timeout AI')); });
        req.write(body);
        req.end();
    });
}

async function gerarResposta(cliente, mensagem) {
    const hoje = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });
    const hora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' });

    const systemPrompt = `Você é a Marina, assistente virtual do salão de beleza NGHair.
Você é profissional, amigável, acolhedora e conhece muito sobre beleza. Fala em português brasileiro.

DATA E HORA ATUAL: ${hoje}, ${hora} (horário de Brasília)

SOBRE O NGHAIR:
- Salão moderno e descontraído, especializado em mulheres independentes
- Serviços disponíveis:
  * Cabelo: corte feminino, coloração, mechas, luzes, balayage, escova progressiva, escova modeladora, hidratação, botox capilar, cauterização, tratamentos capilares
  * Unhas: manicure, pedicure, gel, acrílico, fibra de vidro, nail art
  * Estética facial: design de sobrancelha, henna de sobrancelha, extensão de cílios, limpeza de pele, maquiagem
  * Depilação: cera quente, cera fria, linha
  * Relaxamento: massagem relaxante, massagem modeladora
- Horário de funcionamento: Segunda a Sábado, das 9h às 19h
- Agendamentos: pelo WhatsApp (aqui mesmo!) ou pelo app Trinks
- Para preços específicos: os valores variam conforme o profissional e complexidade do serviço

PERFIL DO CLIENTE:
- Nome: ${cliente.nome}
- Cliente desde: ${cliente.primeiroContato ? new Date(cliente.primeiroContato).toLocaleDateString('pt-BR') : 'hoje'}
- Total de interações: ${cliente.totalMensagens}
${cliente.servicosUsados.length > 0 ? '- Serviços que costuma fazer: ' + cliente.servicosUsados.join(', ') : ''}
${cliente.preferencias.length > 0 ? '- Preferências registradas: ' + cliente.preferencias.join(', ') : ''}

INSTRUÇÕES IMPORTANTES:
1. Responda de forma natural, calorosa e personalizada - use o nome do cliente quando adequado
2. Seja concisa: máximo 3 parágrafos curtos por resposta
3. Para agendamentos: colete serviço desejado, data e horário preferido, e nome completo
4. Para preços: informe que os valores variam e sugira entrar em contato para orçamento personalizado
5. Se o cliente perguntar algo fora do escopo do salão (viagens, política, etc.), redirecione gentilmente para o NGHair
6. Use emojis com moderação (máximo 2 por mensagem)
7. NUNCA invente preços específicos, nomes de profissionais ou horários disponíveis
8. Sempre termine com uma pergunta ou chamada para ação quando apropriado
9. Se o cliente demonstrar interesse em um serviço, registre mentalmente e personalize as próximas respostas`;

    // Montar mensagens com histórico
    const messages = [{ role: 'system', content: systemPrompt }];
    const historico = cliente.historico.slice(-8);
    for (const h of historico) {
        messages.push({ role: h.role === 'user' ? 'user' : 'assistant', content: h.texto });
    }
    messages.push({ role: 'user', content: mensagem });

    try {
        const resposta = await chamarAI(messages);
        log('INFO', `IA respondeu para ${cliente.numero}: ${resposta.substring(0, 60)}...`);
        return resposta;
    } catch(e) {
        log('ERROR', `AI error: ${e.message}`);
        return `Olá ${cliente.nome}! 😊 Sou a Marina, assistente do NGHair. No momento estou com uma instabilidade técnica, mas já vou te ajudar! Para agendar ou tirar dúvidas, pode me contar o que você precisa?`;
    }
}

// ========== WHATSAPP ==========
let sock = null;
let qrCode = null;
let connectionState = 'close';
let reconnectAttempts = 0;
const MAX_RECONNECT = 15;

async function conectarWhatsApp() {
    try {
        const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
        const { version } = await fetchLatestBaileysVersion();
        const logger = pino({ level: 'silent' });

        sock = makeWASocket({
            version,
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, logger)
            },
            logger,
            browser: ['NGHair Marina', 'Chrome', '120.0.0'],
            connectTimeoutMs: 60000,
            defaultQueryTimeoutMs: 60000,
            keepAliveIntervalMs: 25000,
            retryRequestDelayMs: 2000,
            markOnlineOnConnect: false,
            syncFullHistory: false,
            generateHighQualityLinkPreview: false,
            shouldIgnoreJid: jid => jid.includes('@g.us') || jid.includes('broadcast') || jid.includes('newsletter')
        });

        sock.ev.on('creds.update', async () => {
            await saveCreds();
        });

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                qrCode = qr;
                reconnectAttempts = 0;
                log('INFO', 'QR Code gerado! Aguardando escaneamento...');
            }

            if (connection === 'open') {
                connectionState = 'open';
                qrCode = null;
                reconnectAttempts = 0;
                log('INFO', `WhatsApp CONECTADO! Número: ${sock.user?.id}`);
            }

            if (connection === 'close') {
                connectionState = 'close';
                const statusCode = lastDisconnect?.error instanceof Boom
                    ? lastDisconnect.error.output?.statusCode : 0;

                log('WARN', `Conexão fechada. Status: ${statusCode}`);

                if (statusCode === DisconnectReason.loggedOut) {
                    log('INFO', 'Logout detectado. Limpando sessão...');
                    try { fs.rmSync(SESSION_DIR, { recursive: true, force: true }); fs.mkdirSync(SESSION_DIR); } catch(e) {}
                    reconnectAttempts = 0;
                    setTimeout(conectarWhatsApp, 3000);
                    return;
                }

                reconnectAttempts++;
                if (reconnectAttempts <= MAX_RECONNECT) {
                    const delay = Math.min(reconnectAttempts * 5000, 60000);
                    log('INFO', `Reconectando em ${delay/1000}s (tentativa ${reconnectAttempts}/${MAX_RECONNECT})...`);
                    setTimeout(conectarWhatsApp, delay);
                } else {
                    log('ERROR', 'Máximo de reconexões atingido. Aguardando 2min...');
                    reconnectAttempts = 0;
                    setTimeout(conectarWhatsApp, 120000);
                }
            }

            if (connection === 'connecting') {
                connectionState = 'connecting';
            }
        });

        // Processar mensagens recebidas
        sock.ev.on('messages.upsert', async ({ messages: msgs, type }) => {
            if (type !== 'notify') return;

            for (const msg of msgs) {
                // Ignorar mensagens enviadas por mim
                if (msg.key.fromMe) continue;
                if (!msg.key.remoteJid) continue;
                if (msg.key.remoteJid.includes('@g.us')) continue;
                if (msg.key.remoteJid.includes('broadcast')) continue;

                // DEDUPLICAÇÃO: ignorar mensagem já processada
                const msgId = msg.key.id;
                if (jaProcessou(msgId)) {
                    log('DEBUG', `Mensagem duplicada ignorada: ${msgId}`);
                    continue;
                }

                const texto = msg.message?.conversation
                    || msg.message?.extendedTextMessage?.text
                    || msg.message?.imageMessage?.caption
                    || msg.message?.videoMessage?.caption
                    || '';

                if (!texto.trim()) continue;

                const jid = msg.key.remoteJid;
                const numero = jid.replace('@s.whatsapp.net', '').replace(/\D/g, '');
                const nome = msg.pushName || 'Cliente';

                log('INFO', `MSG de ${numero} (${nome}): ${texto.substring(0, 80)}`);

                // Processar em background para não bloquear
                processarMensagem(jid, numero, nome, texto).catch(e => {
                    log('ERROR', `Erro ao processar mensagem: ${e.message}`);
                });
            }
        });

    } catch(e) {
        log('ERROR', `Erro ao conectar WhatsApp: ${e.message}`);
        setTimeout(conectarWhatsApp, 15000);
    }
}

// Processar mensagem e responder
async function processarMensagem(jid, numero, nome, texto) {
    try {
        // Obter/criar cliente
        const cliente = obterCliente(numero, nome);

        // Registrar mensagem do cliente
        registrarConversa(numero, 'user', texto);

        // Gerar resposta com Gemini
        log('INFO', `Gerando resposta para ${numero}...`);
        const resposta = await gerarResposta(cliente, texto);

        // Registrar resposta da Marina
        registrarConversa(numero, 'assistant', resposta);

        // Enviar resposta
        if (sock && connectionState === 'open') {
            await sock.sendMessage(jid, { text: resposta });
            log('INFO', `Resposta enviada para ${numero}: ${resposta.substring(0, 60)}...`);
        } else {
            log('WARN', `WhatsApp não conectado. Resposta não enviada para ${numero}`);
        }
    } catch(e) {
        log('ERROR', `Erro em processarMensagem: ${e.message}`);
    }
}

// ========== SERVIDOR HTTP (API) ==========
const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/json');

    if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

    // Health check
    if (req.url === '/' || req.url === '/health') {
        res.writeHead(200);
        res.end(JSON.stringify({
            status: 'ok',
            agente: 'Marina',
            salao: 'NGHair',
            whatsapp: connectionState,
            clientes: Object.keys(clientes).length,
            versao: '4.0.0',
            timestamp: new Date().toISOString()
        }));
        return;
    }

    // QR Code
    if (req.url === '/qr') {
        if (connectionState === 'open') {
            res.writeHead(200);
            res.end(JSON.stringify({ status: 'connected', message: 'WhatsApp já conectado!' }));
        } else if (qrCode) {
            res.writeHead(200);
            res.end(JSON.stringify({ status: 'qr', code: qrCode }));
        } else {
            res.writeHead(200);
            res.end(JSON.stringify({ status: 'connecting', message: 'Aguardando QR Code...' }));
        }
        return;
    }

    // Status detalhado
    if (req.url === '/status') {
        res.writeHead(200);
        res.end(JSON.stringify({
            whatsapp: connectionState,
            numero: sock?.user?.id || null,
            clientes: Object.keys(clientes).length,
            reconnectAttempts
        }));
        return;
    }

    // Compatibilidade com Evolution API
    if (req.url === '/instance/connectionState/NGHair') {
        res.writeHead(200);
        res.end(JSON.stringify({ instance: { instanceName: 'NGHair', state: connectionState } }));
        return;
    }

    if (req.url === '/instance/connect/NGHair') {
        if (connectionState === 'open') {
            res.writeHead(200);
            res.end(JSON.stringify({ instance: { state: 'open' } }));
        } else if (qrCode) {
            res.writeHead(200);
            res.end(JSON.stringify({ code: qrCode, base64: '' }));
        } else {
            res.writeHead(200);
            res.end(JSON.stringify({ message: 'Aguardando...', state: connectionState }));
        }
        return;
    }

    if (req.url === '/message/sendText/NGHair' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const data = JSON.parse(body);
                const number = (data.number || '').replace(/\D/g, '');
                const jid = number.includes('@') ? number : `${number}@s.whatsapp.net`;
                if (!sock || connectionState !== 'open') throw new Error('WhatsApp desconectado');
                await sock.sendMessage(jid, { text: data.text || '' });
                res.writeHead(200);
                res.end(JSON.stringify({ status: 'SENT' }));
            } catch(e) {
                res.writeHead(500);
                res.end(JSON.stringify({ error: e.message }));
            }
        });
        return;
    }

    // Listar clientes (para debug/admin)
    if (req.url === '/clientes') {
        const lista = Object.values(clientes).map(c => ({
            numero: c.numero,
            nome: c.nome,
            totalMensagens: c.totalMensagens,
            ultimoContato: c.ultimoContato,
            servicosUsados: c.servicosUsados
        }));
        res.writeHead(200);
        res.end(JSON.stringify({ total: lista.length, clientes: lista }));
        return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, '0.0.0.0', () => {
    log('INFO', `Marina NGHair v4.0 iniciada na porta ${PORT}`);
    log('INFO', `Clientes carregados: ${Object.keys(clientes).length}`);
    conectarWhatsApp();
});

process.on('uncaughtException', e => log('ERROR', `Uncaught: ${e.message}`));
process.on('unhandledRejection', r => log('ERROR', `Unhandled: ${r}`));
process.on('SIGTERM', () => { salvarClientes(); server.close(); process.exit(0); });
process.on('SIGINT', () => { salvarClientes(); server.close(); process.exit(0); });
