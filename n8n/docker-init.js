// Executado pelo serviço "n8n-init" do docker-compose, antes de o n8n subir.
// Gera os arquivos de importação a partir do workflow exportado + variáveis de ambiente:
//   - credenciais do Discord (URLs vindas do .env, nunca do repositório)
//   - workflow com id fixo, credenciais ligadas e URL da API do container
const fs = require('fs');

const WORKFLOW_ID = 'ClassMsgIA000001';
const API_URL = (process.env.API_URL_N8N || 'http://api:8000').replace(/\/$/, '');

const DISCORD = {
  'Discord - Atendimento': { id: 'discordAtend0001', env: 'DISCORD_WEBHOOK_ATENDIMENTO' },
  'Discord - SAC': { id: 'discordSac000001', env: 'DISCORD_WEBHOOK_SAC' },
  'Discord - Operações': { id: 'discordOper00001', env: 'DISCORD_WEBHOOK_OPERACOES' },
  'Discord - Triagem': { id: 'discordTriag0001', env: 'DISCORD_WEBHOOK_TRIAGEM' },
};

const wf = JSON.parse(fs.readFileSync('/workflows/workflow-classificacao.json', 'utf8'));
wf.id = WORKFLOW_ID;
wf.active = false;

const credenciais = [];
for (const node of wf.nodes) {
  if (node.type === 'n8n-nodes-base.httpRequest') {
    node.parameters.url = `${API_URL}/classificar`;
  }
  const d = DISCORD[node.name];
  if (!d) continue;
  const url = process.env[d.env];
  if (!url) {
    console.warn(`Aviso: ${d.env} vazio; o node "${node.name}" ficará sem credencial.`);
    continue;
  }
  const nome = `Webhook ${node.name}`;
  credenciais.push({ id: d.id, name: nome, type: 'discordWebhookApi', data: { webhookUri: url } });
  node.credentials = { discordWebhookApi: { id: d.id, name: nome } };
}

fs.writeFileSync('/tmp/credenciais.json', JSON.stringify(credenciais));
fs.writeFileSync('/tmp/workflow.json', JSON.stringify(wf));
console.log(`Preparado: ${credenciais.length} credenciais, workflow ${WORKFLOW_ID} -> ${API_URL}/classificar`);
