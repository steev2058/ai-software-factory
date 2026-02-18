/**
 * n8n Function/Code node: Smart Model Router
 * Input (item.json): { agent_type, task, messages? }
 * Output: model selection + fallback chain
 */

const rawType = ($json.agent_type || '').toString().trim().toLowerCase();

const modelMap = {
  pm: 'deepseek/deepseek-chat',
  frontend: 'anthropic/claude-3.5-sonnet',
  backend: 'mistral/devstral',
  db: 'deepseek/deepseek-chat',
  qa: 'mistral/devstral',
  devops: 'mistral/devstral',
  marketing: 'anthropic/claude',
};

const fallbackByModel = {
  'mistral/devstral': 'deepseek/deepseek-chat',
  'anthropic/claude-3.5-sonnet': 'deepseek/deepseek-chat',
  'anthropic/claude': 'deepseek/deepseek-chat',
  'deepseek/deepseek-chat': 'mimov2',
};

const selectedModel = modelMap[rawType] || 'deepseek/deepseek-chat';

const fallbackChain = [];
let current = selectedModel;
for (let i = 0; i < 3; i++) {
  const next = fallbackByModel[current];
  if (!next || fallbackChain.includes(next)) break;
  fallbackChain.push(next);
  current = next;
}

return [{
  json: {
    agent_type: rawType || 'pm',
    model: selectedModel,
    fallback: fallbackChain[0] || null,
    fallback_chain: fallbackChain,
    openrouter_url: 'https://openrouter.ai/api/v1/chat/completions',
    task: $json.task || '',
    messages: $json.messages || [
      { role: 'user', content: $json.task || 'No task provided' }
    ]
  }
}];
