import urllib.request
import json
import sys
from pathlib import Path

# Adicionar pasta raiz ao path para importar core
sys.path.append(str(Path(__file__).parent))

from core.exporter import export_fcpxml_multi, export_premiere_xml

job_id = "0aa06539"
url = f"http://localhost:5000/api/result/{job_id}"

try:
    print(f"Buscando resultados do job {job_id}...")
    req = urllib.request.urlopen(url)
    res = json.loads(req.read().decode('utf-8'))
    
    clips_by_video = res["clips_by_video"]
    
    # Criar pasta de exportações
    export_dir = Path("x:/PROGRAMACAO/SMART EDITOR/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Exportar FCPXML
    output_path_fcpxml = str(export_dir / "pt1_corrigido.fcpxml")
    print("Gerando FCPXML (.fcpxml)...")
    export_fcpxml_multi(clips_by_video, output_path_fcpxml, "pt1 Corrigido")
    print(f"Sucesso! FCPXML salvo em: {output_path_fcpxml}")
    
    # 2. Exportar Premiere XML (.xml)
    output_path_xml = str(export_dir / "pt1_corrigido.xml")
    print("Gerando Premiere XML (.xml)...")
    export_premiere_xml(clips_by_video, output_path_xml, "pt1 Corrigido")
    print(f"Sucesso! Premiere XML salvo em: {output_path_xml}")

except Exception as e:
    print(f"Erro ao gerar arquivos de exportação: {e}")
