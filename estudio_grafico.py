# estudio_grafico.py
import os
from nicegui import app, ui
from fastapi.responses import HTMLResponse

def get_polotno_estudio_html():
    """
    Retorna o Estúdio Gráfico limpo e moderno (Estilo Canva / Polotno)
    100% em Português, sem marcas chinesas, com fontes do Google, uploads,
    formatos de impressão A4/A3, dimensões customizadas, salvamento de projetos,
    múltiplas páginas, biblioteca de símbolos navais e exportação PNG/JPG/PDF HD.
    """
    html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estúdio Gráfico - SisGAB COMSOC</title>
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Inter:wght@400;500;600;700&family=Montserrat:wght@700;900&family=Bebas+Neue&family=Outfit:wght@500;700&display=swap" rel="stylesheet">
    
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Fabric.js para manipulação rica de canvas -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.1/fabric.min.js"></script>

    <!-- jsPDF para exportação nativa em PDF de alta qualidade -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: #0b0f19;
            color: #e2e8f0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }

        /* BARRA SUPERIOR (HEADER) */
        header {
            height: 56px;
            background-color: #131a26;
            border-bottom: 1px solid rgba(197, 160, 89, 0.2);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 10;
        }
        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            color: #c5a059;
            font-size: 1.1rem;
            letter-spacing: 1px;
        }
        .btn-action {
            background: #c5a059;
            color: #0b0f19;
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.8rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }
        .btn-action:hover {
            background: #d4af37;
            box-shadow: 0 0 12px rgba(197, 160, 89, 0.4);
        }
        .btn-secondary {
            background: rgba(255,255,255,0.08);
            color: #e2e8f0;
            border: 1px solid rgba(255,255,255,0.15);
            padding: 8px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .btn-secondary:hover {
            background: rgba(255,255,255,0.15);
        }

        /* CONTAINER PRINCIPAL */
        .app-container {
            display: flex;
            flex: 1;
            height: calc(100vh - 56px);
        }

        /* PAINEL LATERAL ESQUERDO */
        .sidebar {
            width: 340px;
            background-color: #131a26;
            border-right: 1px solid rgba(197, 160, 89, 0.15);
            display: flex;
            flex-direction: column;
        }
        .sidebar-tabs {
            display: flex;
            background-color: #0c1018;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            overflow-x: auto;
        }
        .tab-btn {
            flex: 1;
            padding: 10px 6px;
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 0.7rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .tab-btn.active {
            color: #c5a059;
            border-bottom: 2px solid #c5a059;
            background: rgba(197, 160, 89, 0.05);
        }
        .tab-btn i { font-size: 1.1rem; }
        .sidebar-content {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
        }
        .section-title {
            font-size: 0.78rem;
            font-weight: 700;
            color: #c5a059;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* CONTROLES DO PAINEL LATERAL */
        .preset-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 16px;
        }
        .preset-card {
            background: #1b2535;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px;
            padding: 10px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s;
        }
        .preset-card:hover {
            border-color: #c5a059;
            background: rgba(197, 160, 89, 0.1);
        }
        .preset-card i { font-size: 1.2rem; color: #c5a059; margin-bottom: 4px; }
        .preset-card div { font-size: 0.75rem; font-weight: 600; }
        .preset-card span { font-size: 0.65rem; color: #64748b; }

        .input-group {
            margin-bottom: 12px;
        }
        .input-group label {
            display: block;
            font-size: 0.75rem;
            color: #94a3b8;
            margin-bottom: 4px;
        }
        .input-control {
            width: 100%;
            background: #1b2535;
            border: 1px solid rgba(255,255,255,0.1);
            color: #fff;
            padding: 8px 10px;
            border-radius: 4px;
            font-size: 0.85rem;
        }
        .input-control:focus {
            outline: none;
            border-color: #c5a059;
        }

        /* ÁREA CENTRAL DO CANVAS */
        .canvas-area {
            flex: 1;
            background-color: #080b12;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: auto;
            background-image: radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 0);
            background-size: 24px 24px;
        }
        .canvas-wrapper {
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
            border: 1px solid rgba(197, 160, 89, 0.3);
            border-radius: 4px;
            overflow: hidden;
            background: #ffffff;
            margin-top: 10px;
        }

        /* BARRA FERRAMENTAS DO ELEMENTO SELECIONADO */
        .toolbar-top {
            position: absolute;
            top: 16px;
            left: 50%;
            transform: translateX(-50%);
            background: #131a26;
            border: 1px solid rgba(197, 160, 89, 0.3);
            padding: 6px 14px;
            border-radius: 30px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            z-index: 5;
        }
        .tool-btn {
            background: none;
            border: none;
            color: #e2e8f0;
            font-size: 0.9rem;
            cursor: pointer;
            padding: 6px;
            border-radius: 4px;
        }
        .tool-btn:hover { color: #c5a059; background: rgba(255,255,255,0.05); }

        /* BARRA DE PÁGINAS NO RODAPÉ DO CANVAS */
        .page-bar-bottom {
            position: absolute;
            bottom: 16px;
            left: 50%;
            transform: translateX(-50%);
            background: #131a26;
            border: 1px solid rgba(197, 160, 89, 0.3);
            padding: 6px 16px;
            border-radius: 30px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            z-index: 5;
        }
        .page-indicator {
            font-size: 0.8rem;
            font-weight: 700;
            color: #c5a059;
            font-family: 'Rajdhani', sans-serif;
            letter-spacing: 1px;
        }

        /* UPLOAD ZONE */
        .upload-zone {
            border: 2px dashed rgba(197, 160, 89, 0.3);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            background: rgba(197, 160, 89, 0.02);
            transition: all 0.2s;
        }
        .upload-zone:hover {
            border-color: #c5a059;
            background: rgba(197, 160, 89, 0.08);
        }

        .color-picker-wrapper {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .color-picker-btn {
            width: 32px;
            height: 32px;
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.2);
            cursor: pointer;
        }

        /* MODAL DE PROJETOS */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 100;
        }
        .modal-card {
            width: 500px;
            background: #131a26;
            border: 1px solid #c5a059;
            border-radius: 12px;
            padding: 20px;
        }
    </style>
</head>
<body>

    <header>
        <div class="header-title">
            <i class="fa-solid fa-palette"></i>
            <span>ESTÚDIO GRÁFICO TÁTICO COMSOC</span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <button class="btn-secondary" onclick="salvarProjeto()"><i class="fa-solid fa-floppy-disk"></i> Salvar</button>
            <button class="btn-secondary" onclick="abrirModalProjetos()"><i class="fa-solid fa-folder-open"></i> Meus Projetos</button>
            <button class="btn-secondary" onclick="limparCanvas()"><i class="fa-solid fa-rotate-left"></i> Limpar</button>
            <button class="btn-action" onclick="exportarImagem('png')"><i class="fa-solid fa-download"></i> PNG HD</button>
            <button class="btn-action" style="background: #00e5ff;" onclick="exportarImagem('jpeg')"><i class="fa-solid fa-file-image"></i> JPG</button>
            <button class="btn-action" style="background: #ef4444; color: #fff;" onclick="exportarPDF()"><i class="fa-solid fa-file-pdf"></i> PDF Impressão</button>
        </div>
    </header>

    <div class="app-container">
        <!-- PAINEL LATERAL DE FERRAMENTAS -->
        <div class="sidebar">
            <div class="sidebar-tabs">
                <button class="tab-btn active" onclick="switchTab('templates', this)">
                    <i class="fa-solid fa-layer-group"></i> Formatos
                </button>
                <button class="tab-btn" onclick="switchTab('texto', this)">
                    <i class="fa-solid fa-font"></i> Texto
                </button>
                <button class="tab-btn" onclick="switchTab('elementos', this)">
                    <i class="fa-solid fa-shapes"></i> Formas
                </button>
                <button class="tab-btn" onclick="switchTab('simbolos', this)">
                    <i class="fa-solid fa-anchor"></i> Símbolos
                </button>
                <button class="tab-btn" onclick="switchTab('uploads', this)">
                    <i class="fa-solid fa-upload"></i> Imagens
                </button>
            </div>

            <div class="sidebar-content">
                <!-- TAB TEMPLATES / FORMATOS E DIMENSÕES CUSTOMIZADAS -->
                <div id="tab-templates" class="tab-content">
                    <div class="section-title"><i class="fa-solid fa-ruler-combined"></i> Mídias Sociais & Telas</div>
                    <div class="preset-grid">
                        <div class="preset-card" onclick="setCanvasSize(1080, 1080)">
                            <i class="fa-solid fa-border-all"></i>
                            <div>Feed Instagram</div>
                            <span>1080 x 1080 px</span>
                        </div>
                        <div class="preset-card" onclick="setCanvasSize(1080, 1920)">
                            <i class="fa-solid fa-mobile-screen"></i>
                            <div>Stories / Reels</div>
                            <span>1080 x 1920 px</span>
                        </div>
                        <div class="preset-card" onclick="setCanvasSize(1920, 1080)">
                            <i class="fa-solid fa-tv"></i>
                            <div>Banner Full HD</div>
                            <span>1920 x 1080 px</span>
                        </div>
                        <div class="preset-card" onclick="setCanvasSize(1200, 400)">
                            <i class="fa-solid fa-id-badge"></i>
                            <div>Placa JADE</div>
                            <span>1200 x 400 px</span>
                        </div>
                    </div>

                    <div class="section-title"><i class="fa-solid fa-print"></i> Formatos de Impressão Oficiais</div>
                    <div class="preset-grid">
                        <div class="preset-card" onclick="setCanvasSize(2480, 3508)">
                            <i class="fa-regular fa-file"></i>
                            <div>Folha A4 Vertical</div>
                            <span>2480 x 3508 px (300DPI)</span>
                        </div>
                        <div class="preset-card" onclick="setCanvasSize(3508, 2480)">
                            <i class="fa-regular fa-file" style="transform: rotate(90deg);"></i>
                            <div>Folha A4 Horiz.</div>
                            <span>3508 x 2480 px (300DPI)</span>
                        </div>
                        <div class="preset-card" onclick="setCanvasSize(3508, 4960)">
                            <i class="fa-solid fa-scroll"></i>
                            <div>Cartaz A3</div>
                            <span>3508 x 4960 px</span>
                        </div>
                        <div class="preset-card" onclick="setCanvasSize(3508, 2480)">
                            <i class="fa-solid fa-vihara"></i>
                            <div>Prisma Mesa A4</div>
                            <span>3508 x 2480 px</span>
                        </div>
                    </div>

                    <div class="section-title"><i class="fa-solid fa-sliders"></i> Tamanho Personalizado (px)</div>
                    <div class="preset-grid" style="grid-template-columns: 1fr 1fr;">
                        <div class="input-group">
                            <label>Largura (px):</label>
                            <input type="number" id="customWidth" value="1200" class="input-control">
                        </div>
                        <div class="input-group">
                            <label>Altura (px):</label>
                            <input type="number" id="customHeight" value="800" class="input-control">
                        </div>
                    </div>
                    <button class="btn-action" style="width: 100%; justify-content: center;" onclick="applyCustomSize()"><i class="fa-solid fa-check"></i> Redimensionar Canvas</button>

                    <div class="section-title" style="margin-top: 16px;"><i class="fa-solid fa-fill-drip"></i> Fundo do Canvas</div>
                    <div class="input-group">
                        <label>Cor de Fundo:</label>
                        <div class="color-picker-wrapper">
                            <input type="color" id="bgColor" value="#131a26" class="color-picker-btn" onchange="setBgColor(this.value)">
                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 0.7rem;" onclick="setBgColor('#0b0f19')">Escuro SisGAB</button>
                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 0.7rem;" onclick="setBgColor('#ffffff')">Branco</button>
                        </div>
                    </div>
                </div>

                <!-- TAB TEXTO -->
                <div id="tab-texto" class="tab-content" style="display: none;">
                    <div class="section-title"><i class="fa-solid fa-plus"></i> Adicionar Texto</div>
                    <button class="btn-action" style="width: 100%; margin-bottom: 8px; font-family: 'Rajdhani', sans-serif; font-size: 1rem;" onclick="addText('TÍTULO DA COMSOC', 38, 'bold')">+ Título Imponente</button>
                    <button class="btn-secondary" style="width: 100%; margin-bottom: 8px;" onclick="addText('Subtítulo do Evento Militar', 24, 'normal')">+ Subtítulo</button>
                    <button class="btn-secondary" style="width: 100%; margin-bottom: 16px;" onclick="addText('Texto detalhado da solenidade militar.', 16, 'normal')">+ Texto Simples</button>

                    <div class="section-title"><i class="fa-solid fa-sliders"></i> Estilo do Texto</div>
                    <div class="input-group">
                        <label>Fonte:</label>
                        <select id="fontFamily" class="input-control" onchange="updateSelectedText('fontFamily', this.value)">
                            <option value="Rajdhani">Rajdhani (Cyber Military)</option>
                            <option value="Inter">Inter (Limpa)</option>
                            <option value="Montserrat">Montserrat (Forte)</option>
                            <option value="Bebas Neue">Bebas Neue (Impacto)</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label>Cor do Texto:</label>
                        <input type="color" id="textColor" value="#c5a059" class="color-picker-btn" onchange="updateSelectedText('fill', this.value)">
                    </div>
                </div>

                <!-- TAB ELEMENTOS / FORMAS -->
                <div id="tab-elementos" class="tab-content" style="display: none;">
                    <div class="section-title"><i class="fa-solid fa-shapes"></i> Formas Geométricas</div>
                    <div class="preset-grid">
                        <div class="preset-card" onclick="addShape('rect')">
                            <i class="fa-regular fa-square"></i>
                            <div>Retângulo</div>
                        </div>
                        <div class="preset-card" onclick="addShape('circle')">
                            <i class="fa-regular fa-circle"></i>
                            <div>Círculo</div>
                        </div>
                        <div class="preset-card" onclick="addShape('line')">
                            <i class="fa-solid fa-minus"></i>
                            <div>Linha Divisória</div>
                        </div>
                        <div class="preset-card" onclick="addShape('badge')">
                            <i class="fa-solid fa-shield-halved"></i>
                            <div>Moldura Tática</div>
                        </div>
                    </div>
                </div>

                <!-- TAB SÍMBOLOS NAVAIS & INSÍGNIAS -->
                <div id="tab-simbolos" class="tab-content" style="display: none;">
                    <div class="section-title"><i class="fa-solid fa-anchor"></i> Insígnias & Brasões MB</div>
                    <div class="preset-grid">
                        <div class="preset-card" onclick="addNavalSymbol('⚓')">
                            <span style="font-size: 1.8rem;">⚓</span>
                            <div>Âncora MB</div>
                        </div>
                        <div class="preset-card" onclick="addNavalSymbol('★ ★ ★ ★')">
                            <span style="font-size: 1.2rem; color: #d4af37;">★ ★ ★ ★</span>
                            <div>Almirante Esquadra</div>
                        </div>
                        <div class="preset-card" onclick="addNavalSymbol('★ ★ ★')">
                            <span style="font-size: 1.2rem; color: #d4af37;">★ ★ ★</span>
                            <div>Vice-Almirante</div>
                        </div>
                        <div class="preset-card" onclick="addNavalSymbol('★ ★')">
                            <span style="font-size: 1.2rem; color: #d4af37;">★ ★</span>
                            <div>Contra-Almirante</div>
                        </div>
                    </div>
                </div>

                <!-- TAB UPLOADS -->
                <div id="tab-uploads" class="tab-content" style="display: none;">
                    <div class="section-title"><i class="fa-solid fa-cloud-arrow-up"></i> Upload de Imagem</div>
                    <div class="upload-zone" onclick="document.getElementById('imgUploader').click()">
                        <i class="fa-solid fa-image" style="font-size: 2rem; color: #c5a059; margin-bottom: 8px;"></i>
                        <div style="font-size: 0.8rem; font-weight: 600;">Clique para escolher foto</div>
                        <div style="font-size: 0.7rem; color: #64748b;">PNG, JPG, SVG do computador</div>
                    </div>
                    <input type="file" id="imgUploader" accept="image/*" style="display: none;" onchange="handleImageUpload(this)">
                </div>
            </div>
        </div>

        <!-- ÁREA DO CANVAS CENTRAL -->
        <div class="canvas-area">
            <!-- Barra Superior Flutuante de Atalhos -->
            <div class="toolbar-top">
                <button class="tool-btn" onclick="bringToFront()" title="Traz para Frente"><i class="fa-solid fa-layer-group"></i></button>
                <button class="tool-btn" onclick="sendToBack()" title="Envia para Trás"><i class="fa-solid fa-layer-group" style="transform: rotate(180deg);"></i></button>
                <button class="tool-btn" onclick="duplicateSelected()" title="Duplicar"><i class="fa-regular fa-copy"></i></button>
                <button class="tool-btn" style="color: #ff1744;" onclick="deleteSelected()" title="Excluir Elemento"><i class="fa-regular fa-trash-can"></i></button>
            </div>

            <div class="canvas-wrapper">
                <canvas id="mainCanvas"></canvas>
            </div>

            <!-- BARRA FLUTUANTE DE GESTÃO DE PÁGINAS NO RODAPÉ -->
            <div class="page-bar-bottom">
                <button class="tool-btn" onclick="changePage(-1)" title="Página Anterior"><i class="fa-solid fa-chevron-left"></i></button>
                <span class="page-indicator" id="pageIndicator">PÁGINA 1 DE 1</span>
                <button class="tool-btn" onclick="changePage(1)" title="Próxima Página"><i class="fa-solid fa-chevron-right"></i></button>
                <button class="btn-action" style="padding: 4px 10px; font-size: 0.7rem;" onclick="addPage()"><i class="fa-solid fa-plus"></i> Nova Página</button>
            </div>
        </div>
    </div>

    <!-- MODAL MEUS PROJETOS SALVOS -->
    <div class="modal-overlay" id="modalProjetos">
        <div class="modal-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <span style="font-family: 'Rajdhani', sans-serif; font-weight: 700; color: #c5a059; font-size: 1.1rem;"><i class="fa-solid fa-folder-open"></i> Meus Projetos Salvos</span>
                <button class="tool-btn" onclick="fecharModalProjetos()"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div id="projetosList" style="max-height: 300px; overflow-y: auto; margin-bottom: 16px;"></div>
            <div style="display: flex; justify-end: flex-end;">
                <button class="btn-secondary" onclick="fecharModalProjetos()">Fechar</button>
            </div>
        </div>
    </div>

    <script>
        let canvas;
        let pagesData = [null]; // Array de estados de páginas
        let currentPageIndex = 0;

        window.onload = function() {
            canvas = new fabric.Canvas('mainCanvas', {
                width: 700,
                height: 700,
                backgroundColor: '#131a26'
            });

            // Boas-vindas inicial
            const title = new fabric.Text('GABINETE COMSOC', {
                left: 170,
                top: 260,
                fontFamily: 'Rajdhani',
                fontSize: 42,
                fontWeight: 'bold',
                fill: '#c5a059'
            });

            const subtitle = new fabric.Text('Edição Gráfica de Banners e Mídias', {
                left: 190,
                top: 320,
                fontFamily: 'Inter',
                fontSize: 20,
                fill: '#e2e8f0'
            });

            canvas.add(title, subtitle);
            canvas.renderAll();
            saveCurrentPageState();
        };

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            
            btn.classList.add('active');
            document.getElementById('tab-' + tabId).style.display = 'block';
        }

        function setCanvasSize(w, h) {
            const maxDim = 680;
            let displayW = w;
            let displayH = h;

            if (w > h) {
                displayW = maxDim;
                displayH = Math.round((h / w) * maxDim);
            } else {
                displayH = maxDim;
                displayW = Math.round((w / h) * maxDim);
            }

            canvas.setWidth(displayW);
            canvas.setHeight(displayH);
            canvas.renderAll();
        }

        function applyCustomSize() {
            const w = parseInt(document.getElementById('customWidth').value || 1200);
            const h = parseInt(document.getElementById('customHeight').value || 800);
            setCanvasSize(w, h);
        }

        function setBgColor(color) {
            canvas.setBackgroundColor(color, canvas.renderAll.bind(canvas));
        }

        function addText(str, size, weight) {
            const text = new fabric.IText(str, {
                left: 100,
                top: 100,
                fontFamily: 'Rajdhani',
                fontSize: size,
                fontWeight: weight,
                fill: '#c5a059'
            });
            canvas.add(text);
            canvas.setActiveObject(text);
            canvas.renderAll();
        }

        function addNavalSymbol(symbolStr) {
            const text = new fabric.Text(symbolStr, {
                left: 200,
                top: 150,
                fontFamily: 'Rajdhani',
                fontSize: 48,
                fill: '#d4af37'
            });
            canvas.add(text);
            canvas.setActiveObject(text);
            canvas.renderAll();
        }

        function updateSelectedText(prop, val) {
            const active = canvas.getActiveObject();
            if (active && active.set) {
                active.set(prop, val);
                canvas.renderAll();
            }
        }

        function addShape(type) {
            let shape;
            if (type === 'rect') {
                shape = new fabric.Rect({ left: 150, top: 150, fill: '#1b2535', width: 200, height: 120, rx: 6, ry: 6, stroke: '#c5a059', strokeWidth: 2 });
            } else if (type === 'circle') {
                shape = new fabric.Circle({ left: 150, top: 150, fill: '#c5a059', radius: 60 });
            } else if (type === 'line') {
                shape = new fabric.Rect({ left: 100, top: 200, fill: '#c5a059', width: 300, height: 3 });
            } else if (type === 'badge') {
                shape = new fabric.Rect({ left: 150, top: 150, fill: 'rgba(197, 160, 89, 0.1)', width: 250, height: 140, stroke: '#c5a059', strokeWidth: 2, rx: 10, ry: 10 });
            }
            if (shape) {
                canvas.add(shape);
                canvas.setActiveObject(shape);
                canvas.renderAll();
            }
        }

        function handleImageUpload(input) {
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    fabric.Image.fromURL(e.target.result, function(img) {
                        img.scaleToWidth(300);
                        img.set({ left: 100, top: 100 });
                        canvas.add(img);
                        canvas.setActiveObject(img);
                        canvas.renderAll();
                    });
                };
                reader.readAsDataURL(input.files[0]);
            }
        }

        function bringToFront() {
            const active = canvas.getActiveObject();
            if (active) { active.bringToFront(); canvas.renderAll(); }
        }

        function sendToBack() {
            const active = canvas.getActiveObject();
            if (active) { active.sendToBack(); canvas.renderAll(); }
        }

        function duplicateSelected() {
            const active = canvas.getActiveObject();
            if (active) {
                active.clone(function(cloned) {
                    cloned.set({ left: active.left + 20, top: active.top + 20 });
                    canvas.add(cloned);
                    canvas.setActiveObject(cloned);
                    canvas.renderAll();
                });
            }
        }

        function deleteSelected() {
            const active = canvas.getActiveObjects();
            if (active && active.length) {
                active.forEach(obj => canvas.remove(obj));
                canvas.discardActiveObject();
                canvas.renderAll();
            }
        }

        function limparCanvas() {
            if (confirm("Deseja realmente limpar a página atual?")) {
                canvas.clear();
                canvas.setBackgroundColor('#131a26', canvas.renderAll.bind(canvas));
            }
        }

        /* GESTÃO DE MÚLTIPLAS PÁGINAS DO PROJETO */
        function saveCurrentPageState() {
            pagesData[currentPageIndex] = JSON.stringify(canvas);
        }

        function updatePageUI() {
            document.getElementById('pageIndicator').innerText = `PÁGINA ${currentPageIndex + 1} DE ${pagesData.length}`;
        }

        function addPage() {
            saveCurrentPageState();
            pagesData.push(null);
            currentPageIndex = pagesData.length - 1;
            canvas.clear();
            canvas.setBackgroundColor('#131a26', canvas.renderAll.bind(canvas));
            updatePageUI();
        }

        function changePage(dir) {
            const newIndex = currentPageIndex + dir;
            if (newIndex >= 0 && newIndex < pagesData.length) {
                saveCurrentPageState();
                currentPageIndex = newIndex;
                if (pagesData[currentPageIndex]) {
                    canvas.loadFromJSON(pagesData[currentPageIndex], function() {
                        canvas.renderAll();
                    });
                } else {
                    canvas.clear();
                    canvas.setBackgroundColor('#131a26', canvas.renderAll.bind(canvas));
                }
                updatePageUI();
            }
        }

        /* PERSISTÊNCIA E PROJETOS SALVOS */
        function salvarProjeto() {
            saveCurrentPageState();
            const nome = prompt("Digite o nome do projeto para salvar:", "Arte COMSOC " + new Date().toLocaleDateString());
            if (nome) {
                const projetos = JSON.parse(localStorage.getItem('sisgab_projetos_graficos') || '{}');
                projetos[nome] = {
                    date: new Date().toISOString(),
                    pages: pagesData
                };
                localStorage.setItem('sisgab_projetos_graficos', JSON.stringify(projetos));
                alert("✅ Projeto '" + nome + "' salvo com sucesso!");
            }
        }

        function abrirModalProjetos() {
            const projetos = JSON.parse(localStorage.getItem('sisgab_projetos_graficos') || '{}');
            const container = document.getElementById('projetosList');
            container.innerHTML = '';

            const keys = Object.keys(projetos);
            if (keys.length === 0) {
                container.innerHTML = '<div style="font-size: 0.8rem; color: #64748b;">Nenhum projeto salvo no histórico.</div>';
            } else {
                keys.forEach(k => {
                    const item = document.createElement('div');
                    item.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.08);';
                    item.innerHTML = `
                        <div>
                            <div style="font-size: 0.85rem; font-weight: 700; color: #fff;">${k}</div>
                            <div style="font-size: 0.7rem; color: #64748b;">${new Date(projetos[k].date).toLocaleString()}</div>
                        </div>
                        <div style="display: flex; gap: 4px;">
                            <button class="btn-action" style="padding: 4px 8px; font-size: 0.7rem;" onclick="carregarProjeto('${k}')">Abrir</button>
                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 0.7rem; color: #ff1744;" onclick="excluirProjeto('${k}')">Excluir</button>
                        </div>
                    `;
                    container.appendChild(item);
                });
            }
            document.getElementById('modalProjetos').style.display = 'flex';
        }

        function fecharModalProjetos() {
            document.getElementById('modalProjetos').style.display = 'none';
        }

        function carregarProjeto(nome) {
            const projetos = JSON.parse(localStorage.getItem('sisgab_projetos_graficos') || '{}');
            if (projetos[nome]) {
                pagesData = projetos[nome].pages || [null];
                currentPageIndex = 0;
                if (pagesData[0]) {
                    canvas.loadFromJSON(pagesData[0], function() {
                        canvas.renderAll();
                    });
                }
                updatePageUI();
                fecharModalProjetos();
                alert("📂 Projeto '" + nome + "' carregado!");
            }
        }

        function excluirProjeto(nome) {
            if (confirm("Excluir projeto '" + nome + "'?")) {
                const projetos = JSON.parse(localStorage.getItem('sisgab_projetos_graficos') || '{}');
                delete projetos[nome];
                localStorage.setItem('sisgab_projetos_graficos', JSON.stringify(projetos));
                abrirModalProjetos();
            }
        }

        function exportarImagem(format) {
            const dataURL = canvas.toDataURL({
                format: format,
                quality: 1.0,
                multiplier: 2
            });
            const link = document.createElement('a');
            link.download = 'arte_comsoc_' + new Date().getTime() + '.' + format;
            link.href = dataURL;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        function exportarPDF() {
            saveCurrentPageState();
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({
                orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
                unit: 'px',
                format: [canvas.width, canvas.height]
            });

            const imgData = canvas.toDataURL({ format: 'png', quality: 1.0, multiplier: 2 });
            pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
            pdf.save('documento_comsoc_' + new Date().getTime() + '.pdf');
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.get('/estudio_grafico')
def render_estudio_grafico():
    """Rota principal do Estúdio Gráfico Tático COMSOC."""
    return get_polotno_estudio_html()

@app.get('/assets/estudio_grafico/estudio_grafico')
@app.get('/assets/estudio_grafico/index.html')
@app.get('/assets/estudio_grafico/')
def render_estudio_grafico_alias():
    return get_polotno_estudio_html()
