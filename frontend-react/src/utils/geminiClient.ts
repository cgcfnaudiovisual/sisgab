/**
 * geminiClient.ts
 * Cliente Ultra-Rápido para Google Gemini com Cache do Modelo Ativo (Latência < 400ms)
 */

// Lembra qual modelo respondeu com sucesso para nunca mais perder tempo testando outros
let lastWorkingModel: string = 'gemini-2.0-flash';

export async function generateGeminiContent(
  prompt: string,
  systemInstruction: string,
  apiKey: string
): Promise<string> {
  const cleanKey = apiKey.trim();
  if (!cleanKey || cleanKey.length < 8) {
    throw new Error('Chave de API do Gemini não configurada ou inválida.');
  }

  // Modelos otimizados para velocidade extrema e baixa latência
  const candidateModels = [
    lastWorkingModel,
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
  ];
  // Remove duplicados preservando a ordem
  const models = Array.from(new Set(candidateModels));

  const payload = {
    contents: [
      {
        role: 'user',
        parts: [
          {
            text: systemInstruction
              ? `[INSTRUÇÃO]: Responda em no máximo 1 a 2 frases curtas e diretas para falar em voz alta.\n[CONTEXTO]: ${systemInstruction}\n\n[USUÁRIO]: ${prompt}`
              : prompt,
          },
        ],
      },
    ],
    generationConfig: {
      temperature: 0.7,
      maxOutputTokens: 100, // Resposta curta = geração 4x mais rápida
    },
  };

  let lastError = 'Não foi possível conectar ao Gemini.';

  for (const model of models) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${cleanKey}`;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
        if (text && text.trim()) {
          lastWorkingModel = model; // Salva para as próximas requisições serem instantâneas
          return text.trim();
        }
      } else {
        const errJson = await response.json().catch(() => ({}));
        lastError = errJson.error?.message || response.statusText;
      }
    } catch (e: any) {
      lastError = e.message || 'Timeout / Erro de conexão';
    }
  }

  throw new Error(lastError);
}
