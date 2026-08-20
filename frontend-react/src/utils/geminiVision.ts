/**
 * geminiVision.ts
 * Motor de Visão Computacional e Tagueamento Semântico para o SisGAB (COMSOC)
 * Analisa fotografias e extrai elementos militares, veículos, ações, cenários e tags em português.
 */

export interface PhotoAiMetadata {
  descricao: string;
  elementos: string[];
  cenario: string;
  acoes: string[];
  tags: string[];
}

let lastWorkingVisionModel = 'gemini-3.7-flash';

/**
 * Converte uma URL de imagem ou Blob para base64 puro (com suporte a proxy para Google Drive)
 */
export async function imageToBase64(imageUrl: string, driveFileId?: string): Promise<{ base64: string; mimeType: string }> {
  let fetchUrl = imageUrl;

  // Se for imagem externa do Drive ou tiver driveFileId, usa o proxy do backend para contornar CORS
  if (driveFileId) {
    fetchUrl = `/api/proxy/image?drive_id=${driveFileId}`;
  } else if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
    if (imageUrl.includes('drive.google.com') || imageUrl.includes('googleusercontent.com')) {
      fetchUrl = `/api/proxy/image?url=${encodeURIComponent(imageUrl)}`;
    }
  }

  const response = await fetch(fetchUrl);
  if (!response.ok) {
    throw new Error(`Falha ao obter imagem (HTTP ${response.status})`);
  }
  const blob = await response.blob();
  const mimeType = blob.type || 'image/jpeg';

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      const base64Data = result.split(',')[1] || result;
      resolve({ base64: base64Data, mimeType });
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Envia uma foto para o Gemini Vision e extrai metadados semânticos
 */
export async function analyzePhotoWithVision(
  imageBase64: string,
  mimeType: string,
  apiKey: string
): Promise<PhotoAiMetadata> {
  const cleanKey = apiKey.trim();
  if (!cleanKey || cleanKey.length < 8) {
    throw new Error('Chave de API do Gemini não configurada.');
  }

  const prompt = `Você é um especialista em catalogação e inteligência visual militar da Marinha do Brasil (Corpo de Fuzileiros Navais).
Analise esta fotografia institucional e retorne ESTRITAMENTE um objeto JSON válido (sem blocos markdown extras) com o seguinte formato:
{
  "descricao": "Resumo de 1 frase do que está acontecendo na cena",
  "elementos": ["lancha", "fuzil", "microfone", "bandeira", "medalha", "blindado", "uniforme camuflado", "terno"],
  "cenario": "salão nobre, externa, baía de guanabara, fortaleza de são josé, pátio de formaturas, dia ensolarado, noite",
  "acoes": ["continência", "discurso", "aperto de mão", "desfile", "brinde", "corte de fita", "posando"],
  "tags": ["10 a 15 palavras-chave diretas em português para busca rápida"]
}`;

  const candidateModels = [
    lastWorkingVisionModel,
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-flash-latest',
  ];
  const models = Array.from(new Set(candidateModels));

  let lastError = 'Falha ao analisar imagem com Vision AI';

  for (const model of models) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${cleanKey}`;
    const payload = {
      contents: [
        {
          role: 'user',
          parts: [
            { text: prompt },
            {
              inlineData: {
                mimeType: mimeType || 'image/jpeg',
                data: imageBase64,
              },
            },
          ],
        },
      ],
      generationConfig: {
        temperature: 0.2,
        responseMimeType: 'application/json',
      },
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 12000);

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (res.ok) {
        const json = await res.json();
        const rawText = json.candidates?.[0]?.content?.parts?.[0]?.text;
        if (rawText) {
          lastWorkingVisionModel = model;
          const cleanedText = rawText.replace(/```json/g, '').replace(/```/g, '').trim();
          const parsed: PhotoAiMetadata = JSON.parse(cleanedText);
          return {
            descricao: parsed.descricao || 'Fotografia institucional CGCFN',
            elementos: Array.isArray(parsed.elementos) ? parsed.elementos : [],
            cenario: parsed.cenario || 'Instalações Navais',
            acoes: Array.isArray(parsed.acoes) ? parsed.acoes : [],
            tags: Array.isArray(parsed.tags) ? parsed.tags : [],
          };
        }
      } else {
        const err = await res.json().catch(() => ({}));
        lastError = err.error?.message || res.statusText;
      }
    } catch (e: any) {
      lastError = e.message || 'Timeout na análise de visão';
    }
  }

  throw new Error(lastError);
}
