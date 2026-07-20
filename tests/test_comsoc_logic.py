import os
import sys
import unittest

# Insere a raiz do projeto no path para importação
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlite_adapter import LocalSQLiteClient

class TestCOMSOCLogic(unittest.TestCase):
    
    def test_sqlite_adapter_basics(self):
        """Valida gravação e leitura básica do adaptador SQLite local."""
        db_path = "test_gabinete.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
            
        client = LocalSQLiteClient(db_path)
        
        # 1. Teste de inserção
        item = {
            'nome_item': 'MOEDA INSTITUCIONAL',
            'quantidade_total': 20,
            'quantidade_disponivel': 20,
            'descricao': 'Moeda de bronze'
        }
        insert_res = client.table('comsoc_brindes_estoque').insert(item).execute()
        self.assertEqual(len(insert_res.data), 1)
        self.assertEqual(insert_res.data[0]['nome_item'], 'MOEDA INSTITUCIONAL')
        
        # 2. Teste de seleção e filtros
        select_res = client.table('comsoc_brindes_estoque').select('*').eq('nome_item', 'MOEDA INSTITUCIONAL').execute()
        self.assertEqual(len(select_res.data), 1)
        self.assertEqual(select_res.data[0]['quantidade_total'], 20)
        
        # 3. Teste de update
        update_res = client.table('comsoc_brindes_estoque').update({'quantidade_disponivel': 15}).eq('nome_item', 'MOEDA INSTITUCIONAL').execute()
        self.assertEqual(len(update_res.data), 1)
        
        # Valida atualização
        check_res = client.table('comsoc_brindes_estoque').select('*').eq('nome_item', 'MOEDA INSTITUCIONAL').execute()
        self.assertEqual(check_res.data[0]['quantidade_disponivel'], 15)
        
        # Limpa banco de testes
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    def test_score_esforco_calculation(self):
        """Valida a fórmula lógica do score de esforço do checklist."""
        def calcular_score(coberturas_selecionadas, itens_viabilidade):
            if itens_viabilidade == 4:
                score_base = 1.0
            elif itens_viabilidade == 3:
                score_base = 2.5
            elif itens_viabilidade == 2:
                score_base = 4.0
            else:
                score_base = 5.0
                
            score_final = score_base + (coberturas_selecionadas * 0.5)
            return min(round(score_final, 1), 5.0)

        # 4 viabilidades, 0 coberturas -> esforço mínimo = 1.0
        self.assertEqual(calcular_score(0, 4), 1.0)
        # 4 viabilidades, 3 coberturas (foto, video, redes) -> esforço 2.5
        self.assertEqual(calcular_score(3, 4), 2.5)
        # 2 viabilidades, 2 coberturas -> esforço 5.0 (crítico)
        self.assertEqual(calcular_score(2, 2), 5.0)

if __name__ == '__main__':
    unittest.main()
