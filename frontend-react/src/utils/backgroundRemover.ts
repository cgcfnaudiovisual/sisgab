import { removeBackground, type Config } from '@imgly/background-removal';

export interface RemoveBgProgressCallback {
  (progress: number, message: string): void;
}

/**
 * Remove o fundo de uma imagem usando modelo de IA de alta fidelidade no navegador (WebAssembly/ONNX).
 * Preserva canais alfa com recorte fino de cabelos, fardas e equipamentos.
 *
 * @param imageSource Data URL (base64), URL pública ou Blob/File da imagem
 * @param onProgress Callback opcional de progresso (0-100%)
 * @returns Promise com o Data URL (base64) da imagem com fundo transparente (PNG)
 */
export async function removeBackgroundAi(
  imageSource: string | Blob | File,
  onProgress?: RemoveBgProgressCallback
): Promise<string> {
  try {
    const config: Config = {
      progress: (key: string, current: number, total: number) => {
        if (total > 0 && onProgress) {
          const percent = Math.round((current / total) * 100);
          let label = 'Processando recorte com IA...';
          if (key.includes('fetch')) label = 'Carregando rede neural...';
          else if (key.includes('compute') || key.includes('inference')) label = 'Isolando sujeito e farda...';
          onProgress(percent, label);
        }
      },
      output: {
        format: 'image/png',
        quality: 1.0,
      },
    };

    onProgress?.(10, 'Iniciando modelo de segmentação IA...');
    const blob = await removeBackground(imageSource, config);
    onProgress?.(90, 'Finalizando canal de transparência...');

    // Converter Blob para Data URL base64
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === 'string') {
          onProgress?.(100, 'Recorte de alta fidelidade concluído!');
          resolve(reader.result);
        } else {
          reject(new Error('Falha ao converter resultado para base64.'));
        }
      };
      reader.onerror = () => reject(new Error('Erro ao ler blob resultante.'));
      reader.readAsDataURL(blob);
    });
  } catch (error: any) {
    console.error('Erro no processamento de remoção de fundo:', error);
    throw new Error(error.message || 'Falha ao remover fundo da imagem.');
  }
}
