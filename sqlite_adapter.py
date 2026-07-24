import os
import sqlite3
import json
from datetime import datetime

class PostgrestAPIResponse:
    def __init__(self, data):
        self.data = data

class SQLiteQueryBuilder:
    def __init__(self, db_path, table_name):
        self.db_path = db_path
        self.table_name = table_name
        self.select_fields = "*"
        self.filters = []
        self.params = []
        self.order_by_col = None
        self.order_desc = False
        self.limit_val = None
        self.offset_val = None
        self.action_type = "select"
        self.action_data = None
        self.conflict_cols = None

    def select(self, *fields):
        # Aceita múltiplos campos passados como argumentos posicionais ou uma lista/string padrão
        if len(fields) == 1:
            self.select_fields = fields[0]
        elif len(fields) > 1:
            self.select_fields = ", ".join(fields)
        else:
            self.select_fields = "*"
        self.action_type = "select"
        return self

    def eq(self, column, value):
        self.filters.append(f"{column} = ?")
        self.params.append(value)
        return self

    def neq(self, column, value):
        self.filters.append(f"{column} != ?")
        self.params.append(value)
        return self

    def gte(self, column, value):
        self.filters.append(f"{column} >= ?")
        self.params.append(value)
        return self

    def lte(self, column, value):
        self.filters.append(f"{column} <= ?")
        self.params.append(value)
        return self

    def like(self, column, value):
        self.filters.append(f"{column} LIKE ?")
        self.params.append(value)
        return self

    def ilike(self, column, value):
        self.filters.append(f"{column} LIKE ?")
        self.params.append(value)
        return self

    def in_(self, column, values_list):
        if not values_list:
            self.filters.append("1 = 0")  # match nothing
            return self
        placeholders = ", ".join(["?"] * len(values_list))
        self.filters.append(f"{column} IN ({placeholders})")
        self.params.extend(values_list)
        return self

    def or_(self, filter_str):
        # Parses simple or conditions like 'id.eq.1,id.eq.2'
        parts = filter_str.split(',')
        sub_filters = []
        for p in parts:
            p = p.strip()
            if '.eq.' in p:
                col, val = p.split('.eq.')
                sub_filters.append(f"{col} = ?")
                self.params.append(val)
            elif '.neq.' in p:
                col, val = p.split('.neq.')
                sub_filters.append(f"{col} != ?")
                self.params.append(val)
        if sub_filters:
            self.filters.append("(" + " OR ".join(sub_filters) + ")")
        return self

    def order(self, column, desc=False):
        self.order_by_col = column
        self.order_desc = desc
        return self

    def limit(self, val):
        self.limit_val = val
        return self

    def range(self, start, end):
        self.limit_val = int(end) - int(start) + 1
        self.offset_val = int(start)
        return self

    def insert(self, data):
        self.action_type = "insert"
        self.action_data = data
        return self

    def update(self, data):
        self.action_type = "update"
        self.action_data = data
        return self

    def delete(self):
        self.action_type = "delete"
        return self

    def upsert(self, data, on_conflict=None):
        self.action_type = "upsert"
        self.action_data = data
        self.conflict_cols = on_conflict
        return self

    def execute(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if self.action_type == "select":
                sql = f"SELECT {self.select_fields} FROM {self.table_name}"
                if self.filters:
                    sql += " WHERE " + " AND ".join(self.filters)
                if self.order_by_col:
                    direction = "DESC" if self.order_desc else "ASC"
                    sql += f" ORDER BY {self.order_by_col} {direction}"
                if self.limit_val is not None:
                    sql += f" LIMIT {self.limit_val}"
                    if self.offset_val is not None:
                        sql += f" OFFSET {self.offset_val}"

                cursor.execute(sql, self.params)
                rows = cursor.fetchall()
                data = [dict(row) for row in rows]
                return PostgrestAPIResponse(data)

            elif self.action_type == "insert":
                if isinstance(self.action_data, dict):
                    keys = list(self.action_data.keys())
                    placeholders = ", ".join(["?"] * len(keys))
                    sql = f"INSERT INTO {self.table_name} ({', '.join(keys)}) VALUES ({placeholders})"
                    cursor.execute(sql, list(self.action_data.values()))
                    conn.commit()
                    return PostgrestAPIResponse([self.action_data])
                elif isinstance(self.action_data, list):
                    inserted = []
                    for row in self.action_data:
                        keys = list(row.keys())
                        placeholders = ", ".join(["?"] * len(keys))
                        sql = f"INSERT INTO {self.table_name} ({', '.join(keys)}) VALUES ({placeholders})"
                        cursor.execute(sql, list(row.values()))
                        inserted.append(row)
                    conn.commit()
                    return PostgrestAPIResponse(inserted)

            elif self.action_type == "update":
                if not isinstance(self.action_data, dict):
                    raise ValueError("Update data must be a dictionary")
                keys = list(self.action_data.keys())
                sets = ", ".join([f"{k} = ?" for k in keys])
                sql = f"UPDATE {self.table_name} SET {sets}"
                params = list(self.action_data.values())
                if self.filters:
                    sql += " WHERE " + " AND ".join(self.filters)
                    params.extend(self.params)
                cursor.execute(sql, params)
                conn.commit()
                return PostgrestAPIResponse([self.action_data])

            elif self.action_type == "delete":
                sql = f"DELETE FROM {self.table_name}"
                params = []
                if self.filters:
                    sql += " WHERE " + " AND ".join(self.filters)
                    params.extend(self.params)
                cursor.execute(sql, params)
                conn.commit()
                return PostgrestAPIResponse([])

            elif self.action_type == "upsert":
                # General upsert helper
                data_list = self.action_data if isinstance(self.action_data, list) else [self.action_data]
                upserted = []
                
                # Deduce conflict columns if not specified
                conflicts = []
                if self.conflict_cols:
                    if isinstance(self.conflict_cols, str):
                        conflicts = [c.strip() for c in self.conflict_cols.split(',')]
                    else:
                        conflicts = self.conflict_cols

                for row in data_list:
                    # Check existence
                    exists = False
                    exist_filters = []
                    exist_params = []

                    if conflicts:
                        for col in conflicts:
                            if col in row:
                                exist_filters.append(f"{col} = ?")
                                exist_params.append(row[col])
                    else:
                        # Fallback: check if id or chave exists
                        for col in ['id', 'chave']:
                            if col in row:
                                exist_filters.append(f"{col} = ?")
                                exist_params.append(row[col])
                                break

                    if exist_filters:
                        check_sql = f"SELECT 1 FROM {self.table_name} WHERE " + " AND ".join(exist_filters)
                        cursor.execute(check_sql, exist_params)
                        exists = cursor.fetchone() is not None

                    if exists:
                        # Perform update
                        update_row = {k: v for k, v in row.items() if k not in conflicts}
                        keys = list(update_row.keys())
                        sets = ", ".join([f"{k} = ?" for k in keys])
                        sql = f"UPDATE {self.table_name} SET {sets} WHERE " + " AND ".join(exist_filters)
                        params = list(update_row.values()) + exist_params
                        cursor.execute(sql, params)
                    else:
                        # Perform insert
                        keys = list(row.keys())
                        placeholders = ", ".join(["?"] * len(keys))
                        sql = f"INSERT INTO {self.table_name} ({', '.join(keys)}) VALUES ({placeholders})"
                        cursor.execute(sql, list(row.values()))
                    upserted.append(row)
                conn.commit()
                return PostgrestAPIResponse(upserted)

        finally:
            conn.close()

class LocalSQLiteClient:
    def __init__(self, db_path="gabinete.db"):
        self.db_path = os.path.abspath(db_path)
        self._init_db()

    def table(self, table_name):
        return SQLiteQueryBuilder(self.db_path, table_name)

    def _init_db(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        TABLE_SCHEMAS = {
            'Alunos': '''
                CREATE TABLE IF NOT EXISTS Alunos (
                    id TEXT PRIMARY KEY,
                    numero_interno TEXT UNIQUE,
                    nome_guerra TEXT,
                    nome_completo TEXT,
                    pelotao TEXT,
                    status TEXT,
                    media_academica REAL,
                    endereco TEXT,
                    telefone_contato TEXT,
                    contato_emergencia_nome TEXT,
                    contato_emergencia_numero TEXT,
                    numero_armario TEXT,
                    url_foto TEXT,
                    nip TEXT,
                    especialidade TEXT,
                    ano_letivo TEXT
                )
            ''',
            'Acoes': '''
                CREATE TABLE IF NOT EXISTS Acoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id TEXT,
                    tipo_acao_id TEXT,
                    tipo TEXT,
                    descricao TEXT,
                    data TEXT,
                    usuario TEXT,
                    status TEXT
                )
            ''',
            'Tipos_Acao': '''
                CREATE TABLE IF NOT EXISTS Tipos_Acao (
                    id TEXT PRIMARY KEY,
                    nome TEXT,
                    pontuacao REAL
                )
            ''',
            'Config': '''
                CREATE TABLE IF NOT EXISTS Config (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                )
            ''',
            'Users': '''
                CREATE TABLE IF NOT EXISTS Users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    nome TEXT,
                    role TEXT,
                    telegram_id TEXT,
                    url_foto TEXT
                )
            ''',
            'RegistrationRequests': '''
                CREATE TABLE IF NOT EXISTS RegistrationRequests (
                    id TEXT PRIMARY KEY,
                    email TEXT,
                    nome_completo TEXT,
                    nome_guerra TEXT,
                    status TEXT,
                    created_at TEXT
                )
            ''',
            'Permissions': '''
                CREATE TABLE IF NOT EXISTS Permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_key TEXT UNIQUE,
                    feature_name TEXT,
                    allowed_roles TEXT
                )
            ''',
            'presenca_ausencia': '''
                CREATE TABLE IF NOT EXISTS presenca_ausencia (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_interno TEXT,
                    nome_guerra TEXT,
                    turma TEXT,
                    presente INTEGER,
                    motivo_ausencia TEXT,
                    data TEXT,
                    hora TEXT,
                    criado_em TEXT
                )
            ''',
            'escala_diaria': '''
                CREATE TABLE IF NOT EXISTS escala_diaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    cargo TEXT,
                    nome TEXT,
                    observacao TEXT,
                    criado_em TEXT
                )
            ''',
            'fila_atendimento': '''
                CREATE TABLE IF NOT EXISTS fila_atendimento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_interno TEXT,
                    nome_guerra TEXT,
                    turma TEXT,
                    motivo TEXT,
                    prioridade TEXT,
                    status TEXT,
                    data TEXT,
                    hora TEXT,
                    criado_em TEXT,
                    atualizado_em TEXT
                )
            ''',
            'avisos_criticos': '''
                CREATE TABLE IF NOT EXISTS avisos_criticos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    mensagem TEXT,
                    prioridade TEXT,
                    turma TEXT,
                    status TEXT,
                    data TEXT,
                    hora TEXT,
                    criado_em TEXT,
                    atualizado_em TEXT
                )
            ''',
            'tarefas_pendentes': '''
                CREATE TABLE IF NOT EXISTS tarefas_pendentes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    descricao TEXT,
                    responsavel TEXT,
                    prioridade TEXT,
                    status TEXT,
                    data TEXT,
                    hora TEXT,
                    criado_em TEXT,
                    atualizado_em TEXT,
                    prazo TEXT
                )
            ''',
            'pernoite': '''
                CREATE TABLE IF NOT EXISTS pernoite (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id TEXT,
                    data TEXT,
                    presente INTEGER
                )
            ''',
            'oficiais_servico': '''
                CREATE TABLE IF NOT EXISTS oficiais_servico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    cargo TEXT,
                    ajudante TEXT,
                    data TEXT
                )
            ''',
            'efetivo': '''
                CREATE TABLE IF NOT EXISTS efetivo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_guerra TEXT UNIQUE,
                    email TEXT,
                    senha_hash TEXT,
                    telegram_id TEXT,
                    role TEXT,
                    posto TEXT,
                    posto_grad TEXT,
                    data_nascimento TEXT,
                    url_foto TEXT,
                    setor TEXT,
                    origem TEXT,
                    categoria TEXT DEFAULT 'militar'
                )
            ''',
            'demandas_comunicacao': '''
                CREATE TABLE IF NOT EXISTS demandas_comunicacao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    solicitante_nome TEXT,
                    setor TEXT,
                    contato TEXT,
                    titulo_evento TEXT,
                    data_evento TEXT,
                    hora_evento TEXT,
                    local_evento TEXT,
                    tipo_cobertura TEXT,
                    autoridades TEXT,
                    score_esforco REAL,
                    sigiloso INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pendente',
                    notificar_militar_ids TEXT,
                    encarregado_id TEXT,
                    arquivo_url TEXT,
                    arquivo_nome TEXT
                )
            ''',
            'demandas_historico_tramitacao': '''
                CREATE TABLE IF NOT EXISTS demandas_historico_tramitacao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    demanda_id INTEGER,
                    data_hora TEXT,
                    usuario TEXT,
                    acao TEXT,
                    parecer TEXT
                )
            ''',
            'cautela_equipamentos': '''
                CREATE TABLE IF NOT EXISTS cautela_equipamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipamento TEXT,
                    retirado_por TEXT,
                    data_retirada TEXT,
                    data_devolucao TEXT,
                    pauta_id INTEGER,
                    status TEXT DEFAULT 'retirado',
                    e_pessoal INTEGER DEFAULT 0,
                    event_date TEXT
                )
            ''',
            'comsoc_brindes_estoque': '''
                CREATE TABLE IF NOT EXISTS comsoc_brindes_estoque (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_item TEXT UNIQUE,
                    quantidade_total INTEGER,
                    quantidade_disponivel INTEGER,
                    descricao TEXT
                )
            ''',
            'comsoc_brindes_distribuicao': '''
                CREATE TABLE IF NOT EXISTS comsoc_brindes_distribuicao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brinde_id INTEGER,
                    quantidade INTEGER,
                    destinatario_nome TEXT,
                    data_entrega TEXT,
                    demanda_id INTEGER,
                    entregue_por TEXT
                )
            ''',
            'comsoc_noticias': '''
                CREATE TABLE IF NOT EXISTS comsoc_noticias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    conteudo TEXT,
                    autor TEXT,
                    data TEXT,
                    tags TEXT
                )
            ''',
            'face_embeddings': '''
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    nome_guerra TEXT NOT NULL,
                    telegram_id TEXT UNIQUE,
                    embedding TEXT NOT NULL,
                    drive_folder_id TEXT,
                    criado_em TEXT
                )
            ''',
            'processed_photos': '''
                CREATE TABLE IF NOT EXISTS processed_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    drive_file_id TEXT,
                    drive_link TEXT,
                    criado_em TEXT
                )
            ''',
            'photo_matches': '''
                CREATE TABLE IF NOT EXISTS photo_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_id INTEGER,
                    militar_id TEXT,
                    similarity REAL NOT NULL,
                    status TEXT DEFAULT 'aprovado',
                    criado_em TEXT
                )
            ''',
            'comsoc_equipamentos': '''
                CREATE TABLE IF NOT EXISTS comsoc_equipamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE,
                    e_pessoal INTEGER DEFAULT 0,
                    descricao TEXT
                )
            ''',
            'datas_comemorativas': '''
                CREATE TABLE IF NOT EXISTS datas_comemorativas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dia TEXT NOT NULL,
                    mes TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    criado_em TEXT
                )
            ''',
            'presenca_diaria': '''
                CREATE TABLE IF NOT EXISTS presenca_diaria (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    telegram_id TEXT,
                    nome_guerra TEXT NOT NULL,
                    data TEXT NOT NULL,
                    hora_presenca TEXT,
                    status TEXT NOT NULL,
                    observacao TEXT,
                    criado_em TEXT
                )
            '''
        }
        
        try:
            for table, schema in TABLE_SCHEMAS.items():
                cursor.execute(schema)
            conn.commit()
            
            # Migração local: garante que colunas novas no efetivo existam se o BD já existia
            try:
                cursor.execute("ALTER TABLE efetivo ADD COLUMN posto_grad TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE efetivo ADD COLUMN data_nascimento TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE efetivo ADD COLUMN setor TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE efetivo ADD COLUMN origem TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE efetivo ADD COLUMN categoria TEXT DEFAULT 'militar'")
            except:
                pass
            # Migração local: garante que encarregado_id exista na tabela de demandas se o BD já existia
            try:
                cursor.execute("ALTER TABLE demandas_comunicacao ADD COLUMN encarregado_id TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE demandas_comunicacao ADD COLUMN arquivo_url TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE demandas_comunicacao ADD COLUMN arquivo_nome TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE demandas_comunicacao ADD COLUMN data_fim TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE demandas_comunicacao ADD COLUMN captacao_entrega TEXT DEFAULT 'apenas_captacao_bruto'")
            except:
                pass
            conn.commit()
            
            # Pre-populate defaults if table Config is empty
            cursor.execute("SELECT COUNT(*) FROM Config")
            if cursor.fetchone()[0] == 0:
                default_configs = [
                    ('linha_base_conceito', '8.5'),
                    ('impacto_max_acoes', '1.5'),
                    ('peso_academico', '1.0'),
                    ('fator_adaptacao', '0.25'),
                    ('periodo_adaptacao_inicio', '2026-02-01'),
                    ('periodo_adaptacao_fim', '2026-02-28'),
                    ('tempo_polling_tv', '300'),
                    ('cabecalho_tv_title', 'SITUAÇÃO CONSOLIDADA DO CORPO DE ALUNOS'),
                    ('cabecalho_tv_subtitle', 'CORPO DE ALUNOS • COMANDO TÁTICO'),
                    ('cargos_escala_lista', 'INSPETOR DO DIA, SUPERVISOR, AJOSCA, OSCA, OFICIAL DE SERVIÇO, ENFERMEIRO DE SERVIÇO'),
                    ('codigo_desbloqueio_tv', '1234'),
                    ('tempo_alerta_tv', '10')
                ]
                cursor.executemany("INSERT INTO Config (chave, valor) VALUES (?, ?)", default_configs)
                conn.commit()
                
            # Pre-populate default admin in Users and efetivo if empty
            cursor.execute("SELECT COUNT(*) FROM Users")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO Users (id, username, nome, role, telegram_id, url_foto) VALUES (?, ?, ?, ?, ?, ?)",
                    ('1', 'admin', 'Sargento Calaça', 'admin', '123456789', '')
                )
                conn.commit()
                
            cursor.execute("SELECT COUNT(*) FROM efetivo")
            if cursor.fetchone()[0] == 0:
                # sha-256 for 'admin' is '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918'
                cursor.execute(
                    "INSERT INTO efetivo (nome_guerra, email, senha_hash, telegram_id, role, posto, url_foto) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ('ADMIN', 'admin@marinha.mil.br', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', '123456789', 'admin', 'Administrador', '')
                )
                conn.commit()
                
            # Pre-popula datas comemorativas se tabela estiver vazia
            cursor.execute("SELECT COUNT(*) FROM datas_comemorativas")
            if cursor.fetchone()[0] == 0:
                default_dates = [
                    ('08', '01', 'Dia do Fotógrafo (COMSOC)', datetime.now().isoformat()),
                    ('07', '03', 'Aniversário do Corpo de Fuzileiros Navais (CFN)', datetime.now().isoformat()),
                    ('11', '06', 'Batalha Naval do Riachuelo (Data Magna da MB)', datetime.now().isoformat()),
                    ('21', '07', 'Dia da Comunicação Social da Marinha', datetime.now().isoformat()),
                    ('23', '10', 'Dia do Aviador / Força Aérea Brasileira', datetime.now().isoformat()),
                    ('19', '11', 'Dia da Bandeira', datetime.now().isoformat()),
                    ('13', '12', 'Dia do Marinheiro (Patrono da MB - Tamandaré)', datetime.now().isoformat()),
                    ('28', '12', 'Dia do Guarda-Marinha', datetime.now().isoformat())
                ]
                cursor.executemany("INSERT INTO datas_comemorativas (dia, mes, titulo, criado_em) VALUES (?, ?, ?, ?)", default_dates)
                conn.commit()
                
        except Exception as e:
            print(f"[SQLITE INITIALIZATION ERROR] {e}")
        finally:
            conn.close()
