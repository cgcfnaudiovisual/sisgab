import urllib.parse
import requests
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from google import genai
except ImportError:
    genai = None

# Dicionário local para tradução rápida de termos comuns de efeitos sonoros (SFX) em português para inglês.
# Garante o funcionamento da busca direta mesmo se a IA estiver desativada ou sem chave de API configurada.
PORTUGUESE_TO_ENGLISH_SFX = {
    "passo": "footstep",
    "passos": "footsteps",
    "pegada": "footstep",
    "pegadas": "footsteps",
    "passinhos": "footsteps",
    "passadas": "footsteps",
    "passada": "footstep",
    "madeira": "wood",
    "tabua": "wood",
    "tábua": "wood",
    "molhada": "wet",
    "molhado": "wet",
    "agua": "water",
    "água": "water",
    "chuva": "rain",
    "chover": "rain",
    "chuvisco": "drizzle",
    "tempestade": "storm",
    "vento": "wind",
    "brisa": "breeze",
    "porta": "door",
    "portas": "doors",
    "ranger": "creak",
    "rangendo": "creak",
    "velho": "old",
    "antiga": "old",
    "antigo": "old",
    "vidro": "glass",
    "quebrando": "breaking",
    "quebrar": "break",
    "batida": "hit",
    "batidas": "hits",
    "impacto": "impact",
    "soco": "punch",
    "chute": "kick",
    "tapa": "slap",
    "palmas": "clapping",
    "aplausos": "applause",
    "sorriso": "smile",
    "trovão": "thunder",
    "trovao": "thunder",
    "relâmpago": "lightning",
    "relampago": "lightning",
    "fogo": "fire",
    "fogueira": "campfire",
    "queima": "burning",
    "queimando": "burning",
    "fumaça": "smoke",
    "fumaca": "smoke",
    "faísca": "spark",
    "faisca": "spark",
    "explosão": "explosion",
    "explosao": "explosion",
    "explodir": "explode",
    "bomba": "bomb",
    "carro": "car",
    "motor": "engine",
    "freio": "brake",
    "buzina": "horn",
    "pneu": "tire",
    "derrapada": "screech",
    "moto": "motorcycle",
    "motocicleta": "motorcycle",
    "avião": "airplane",
    "aviao": "airplane",
    "helicóptero": "helicopter",
    "helicoptero": "helicopter",
    "trem": "train",
    "ônibus": "bus",
    "onibus": "bus",
    "bicicleta": "bicycle",
    "bike": "bike",
    "campainha": "doorbell",
    "telefone": "phone",
    "celular": "phone",
    "toque": "ringtone",
    "mensagem": "notification",
    "notificação": "notification",
    "notificacao": "notification",
    "teclado": "keyboard",
    "digitar": "typing",
    "digitando": "typing",
    "digitação": "typing",
    "digitacao": "typing",
    "mouse": "mouse",
    "clique": "click",
    "computador": "computer",
    "moeda": "coin",
    "dinheiro": "money",
    "grama": "grass",
    "terra": "dirt",
    "solo": "ground",
    "pedra": "stone",
    "pedras": "stones",
    "rocha": "rock",
    "cascalho": "gravel",
    "lama": "mud",
    "galho": "branch",
    "galhos": "branches",
    "árvore": "tree",
    "arvore": "tree",
    "folhas": "leaves",
    "folha": "leaf",
    "areia": "sand",
    "neve": "snow",
    "asfalto": "concrete",
    "concreto": "concrete",
    "salto": "heels",
    "bota": "boots",
    "botas": "boots",
    "arma": "gun",
    "tiro": "gunshot",
    "tiros": "gunshots",
    "espada": "sword",
    "lâmina": "blade",
    "lamina": "blade",
    "corte": "cut",
    "cortando": "cutting",
    "faca": "knife",
    "escorregar": "slide",
    "deslizar": "slide",
    "grito": "scream",
    "gritando": "screaming",
    "sussurro": "whisper",
    "choro": "crying",
    "chorando": "crying",
    "criança": "child",
    "crianca": "child",
    "bebe": "baby",
    "bebê": "baby",
    "cachorro": "dog",
    "latido": "bark",
    "latir": "bark",
    "gato": "cat",
    "miado": "meow",
    "miar": "meow",
    "pássaro": "bird",
    "passaro": "bird",
    "pássaros": "birds",
    "passaros": "birds",
    "cantar": "singing",
    "cantando": "singing",
    "floresta": "forest",
    "selva": "jungle",
    "leão": "lion",
    "leao": "lion",
    "rugido": "roar",
    "lobo": "wolf",
    "uivado": "howl",
    "uivando": "howling",
    "cavalo": "horse",
    "galope": "gallop",
    "vaca": "cow",
    "boi": "bull",
    "ovelha": "sheep",
    "porco": "pig",
    "monstro": "monster",
    "zumbi": "zombie",
    "fantasma": "ghost",
    "bruxa": "witch",
    "robô": "robot",
    "robo": "robot",
    "nave": "spaceship",
    "sintetizador": "synth",
    "baixo": "bass",
    "grave": "bass",
    "agudo": "high pitch",
    "transição": "transition",
    "transicao": "transition",
    "espacial": "space",
    "laser": "laser",
    "whoosh": "whoosh",
    "swoosh": "swoosh",
    "swish": "swish",
    "riscar": "scratch",
    "disco": "vinyl",
    "vinil": "vinyl",
    "relógio": "clock",
    "relogio": "clock",
    "tique": "tick",
    "alarme": "alarm",
    "sirene": "siren",
    "polícia": "police",
    "policia": "police",
    "ambulância": "ambulance",
    "ambulancia": "ambulance",
    "bombeiros": "fire truck",
    "multidão": "crowd",
    "multidao": "crowd",
    "aplausos": "applause",
    "palmas": "clapping",
    "vaias": "boos",
    "barulho": "noise",
    "ruído": "noise",
    "ruido": "noise",
    "chiado": "hiss",
    "estalo": "click",
    "estalos": "clicks",
    "sopro": "blow",
    "passos na grama": "footsteps grass",
    "passos na madeira": "footsteps wood",
    "passos na terra": "footsteps dirt",
    "forte": "strong",
    "uivando": "howling",
    "noite": "night",
    "passo-a-passo": "footsteps",
    "passos-na-madeira": "footsteps wood",
    "lento": "slow",
    "lentos": "slow",
    "rapido": "fast",
    "rápido": "fast",
    "rapidos": "fast",
    "rápidos": "fast"
}

# Conectivos e termos comuns que devem ser ignorados para evitar buscas excessivamente específicas no Freesound
STOP_WORDS = {
    # Português
    "de", "do", "da", "dos", "das", "com", "para", "em", "no", "na", "nos", "nas", 
    "um", "uma", "uns", "umas", "e", "o", "a", "os", "as", "por", "num", "numa", 
    "sob", "sobre", "atras", "atrás", "dentro", "fora", "ao", "aos", "à", "ao",
    # Inglês
    "on", "in", "at", "with", "of", "the", "a", "an", "for", "to", "by", "from", 
    "and", "or", "is", "are", "was", "were", "be", "about", "into", "over", 
    "under", "behind", "through", "out"
}

def clean_and_translate_query(query):
    """
    Remove caracteres especiais, elimina stop words em português/inglês e traduz
    os termos em português para inglês usando o dicionário local.
    """
    if not query:
        return ""
    # Substituir pontuações e caracteres especiais por espaço
    cleaned = re.sub(r'[^\w\s,]', ' ', query.lower())
    words = cleaned.split()
    
    translated_words = []
    for word in words:
        if word in STOP_WORDS:
            continue
        # Traduz se o termo estiver no dicionário local; caso contrário, mantém original (inglês ou não mapeado)
        translated_words.append(PORTUGUESE_TO_ENGLISH_SFX.get(word, word))
        
    return " ".join(translated_words)

def get_fallback_queries(query):
    """
    Gera combinações mais simples a partir de uma busca de múltiplas palavras-chave.
    Se a busca retornar 0 resultados, tentamos estas simplificações progressivamente.
    """
    words = [w.strip() for w in query.split() if w.strip()]
    fallbacks = []
    if len(words) >= 3:
        # Tenta combinações de duas palavras
        fallbacks.append(f"{words[0]} {words[1]}")
        fallbacks.append(f"{words[0]} {words[2]}")
        fallbacks.append(f"{words[1]} {words[2]}")
        # Tenta a primeira palavra isolada (termo principal)
        fallbacks.append(words[0])
    elif len(words) == 2:
        fallbacks.append(words[0])
        fallbacks.append(words[1])
    return fallbacks


class SFXSearcher:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key

    def set_api_key(self, api_key):
        self.gemini_api_key = api_key

    def smart_optimize_query(self, user_query):
        """
        Usa o Gemini para traduzir o termo de busca para o inglês e sugerir termos alternativos.
        """
        if not self.gemini_api_key:
            return None, [], None

        try:
            client = genai.Client(api_key=self.gemini_api_key)
            prompt = f"""
            Você é um assistente de edição de vídeo e sonoplastia.
            O editor de vídeo digitou a seguinte descrição ou termo para buscar efeitos sonoros: "{user_query}"
            
            1. Traduza e simplifique o termo de busca para os 2 termos de busca em inglês mais eficientes para sites de sound effects (ex: "glass breaking", "laser gun").
               ATENÇÃO (MUITO IMPORTANTE): Sites de busca de efeitos sonoros como Freesound são extremamente sensíveis a termos excessivos e conectivos. 
               - NÃO inclua conectivos ou stop-words (como "on", "in", "with", "at", "of", "a", "the", "for", "to", "from").
               - Limite a busca a no máximo 1 a 3 palavras simples de impacto (apenas substantivos e adjetivos essenciais).
               - Exemplo: para "passos de madeira molhada", use "footsteps wet wood" ou "wet footsteps".
            2. Sugira 3 outros efeitos de áudio complementares que enriqueceriam essa mesma cena (em português).
            
            Responda EXATAMENTE no seguinte formato JSON (sem markdown):
            {{
                "english_search": "termo principal em ingles simplificado",
                "alternative_english_search": "segundo termo em ingles simplificado",
                "suggestions": ["sugestão 1", "sugestão 2", "sugestão 3"]
            }}
            """
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text.split("```json")[1].split("```")[0].strip()
            elif text.startswith("```"):
                text = text.split("```")[1].split("```")[0].strip()

            import json
            data = json.loads(text)
            return data.get("english_search"), data.get("suggestions", []), data.get("alternative_english_search")
        except Exception as e:
            print(f"Erro na chamada do Gemini API: {e}")
            return None, [], None

    def search_myinstants(self, query):
        """
        Busca efeitos sonoros/memes no site MyInstants.
        """
        results = []
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.myinstants.com/pt/search/?name={encoded_query}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                sound_divs = soup.find_all('div', class_='instant')
                for div in sound_divs:
                    button = div.find('button', class_='small-button')
                    if button:
                        onclick = button.get('onclick', '')
                        match = re.search(r"play\('([^']+)'", onclick)
                        if match:
                            audio_url = "https://www.myinstants.com" + match.group(1)
                            link_elem = div.find('a', class_='instant-link')
                            title = link_elem.text.strip() if link_elem else "Som sem nome"
                            
                            results.append({
                                'title': title,
                                'url': audio_url,
                                'source': 'MyInstants',
                                'duration': 'Curto (Meme/Efeito)'
                            })
        except Exception as e:
            print(f"Erro ao buscar no MyInstants para '{query}': {e}")
        return results

    def search_freesound_public(self, query):
        """
        Busca efeitos sonoros de alta fidelidade diretamente no Freesound,
        extraindo links de prévia de áudio MP3 oficiais a partir dos atributos de dados do site.
        """
        results = []
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://freesound.org/search/?q={encoded_query}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Encontrar os elementos do player que contêm o link direto do MP3 nas tags data-mp3
                for elem in soup.find_all(attrs={"data-mp3": True}):
                    audio_url = elem.get('data-mp3')
                    title = elem.get('data-title') or f"Freesound SFX ({query})"
                    if audio_url:
                        results.append({
                            'title': title,
                            'url': audio_url,
                            'source': 'Freesound (Prévia)',
                            'duration': 'Variável'
                        })
        except Exception as e:
            print(f"Erro ao buscar no Freesound para '{query}': {e}")
        return results

    def search_all(self, query, use_gemini=False):
        """
        Busca efeitos em múltiplos bancos. Suporta termos de busca compostos
        ou múltiplos termos separados por vírgula (ex: "wind drone, whoosh").
        """
        # Separar termos por vírgula para permitir busca múltipla
        raw_terms = [t.strip() for t in query.split(",") if t.strip()]
        if not raw_terms:
            return [], [], query
            
        results = []
        all_suggestions = []
        optimized_terms_used = []
        
        for term in raw_terms:
            # 1. Tradução e limpeza local básica (sempre calculada)
            local_cleaned = clean_and_translate_query(term)
            opt_term = local_cleaned if local_cleaned else term
            alt_term = None
            
            # 2. Otimização por IA se ativada
            if use_gemini and self.gemini_api_key:
                smart_q, sug, alt_q = self.smart_optimize_query(term)
                if smart_q:
                    opt_term = clean_and_translate_query(smart_q)
                if alt_q:
                    alt_term = clean_and_translate_query(alt_q)
                if sug:
                    all_suggestions.extend(sug)
            
            # 3. Buscar termo principal
            term_results = []
            term_results.extend(self.search_myinstants(opt_term))
            term_results.extend(self.search_freesound_public(opt_term))
            
            # Buscar termo alternativo sugerido pela IA se houver
            if alt_term:
                term_results.extend(self.search_myinstants(alt_term))
                term_results.extend(self.search_freesound_public(alt_term))
                optimized_terms_used.append(f"{opt_term} / {alt_term}")
            else:
                optimized_terms_used.append(opt_term)
                
            # Se o termo original em português foi traduzido e não obtivemos resultados,
            # buscamos também a versão limpa básica traduzida localmente.
            if len(term_results) == 0 and opt_term.lower() != term.lower():
                local_fallback_term = clean_and_translate_query(term)
                if local_fallback_term and local_fallback_term != opt_term:
                    term_results.extend(self.search_myinstants(local_fallback_term))
                    term_results.extend(self.search_freesound_public(local_fallback_term))
            
            # 4. Fallback Progressivo Multi-Tier (se zero resultados encontrados para este termo)
            if len(term_results) == 0:
                fallbacks = get_fallback_queries(opt_term)
                for f_term in fallbacks:
                    if not f_term.strip():
                        continue
                    fallback_res = []
                    fallback_res.extend(self.search_myinstants(f_term))
                    fallback_res.extend(self.search_freesound_public(f_term))
                    if fallback_res:
                        term_results.extend(fallback_res)
                        # Parar se já tivermos resultados suficientes
                        if len(term_results) >= 5:
                            break
                            
            results.extend(term_results)
            
        # Remover duplicados (pela URL do áudio) mantendo a relevância da ordem
        seen = set()
        unique_results = []
        for r in results:
            url = r['url']
            if url not in seen:
                seen.add(url)
                unique_results.append(r)
                
        # Obter sugestões de IA únicas
        unique_suggestions = list(dict.fromkeys(all_suggestions))[:6]
        
        # String de feedback para exibir o que foi pesquisado pela IA
        opt_feedback = ", ".join(optimized_terms_used)
        
        return unique_results, unique_suggestions, opt_feedback

