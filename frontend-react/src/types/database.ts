export type UserRole = 
  | 'admin' 
  | 'supervisor' 
  | 'oficial_gab' 
  | 'oficial' 
  | 'praca_gab' 
  | 'comsoc' 
  | 'comsoc_design' 
  | 'operador' 
  | 'militar' 
  | 'compel' 
  | 'tv' 
  | 'tv_comcia';

export interface UserProfile {
  id: string;
  username: string;
  nome: string;
  nome_guerra: string;
  role: UserRole;
  email?: string;
  url_foto?: string;
  posto?: string;
  posto_grad?: string;
  setor?: string;
}

export interface DemandaComunicacao {
  id: number;
  solicitante_nome: string;
  setor: string;
  contato: string;
  titulo_evento: string;
  data_evento: string;
  data_fim?: string | null;
  hora_evento: string;
  local_evento: string;
  tipo_cobertura: string[];
  autoridades?: string | null;
  score_esforco: number;
  sigiloso: boolean;
  status: 'pendente' | 'aprovado' | 'ajustes' | 'rejeitado' | 'concluida' | 'cancelada';
  notificar_militar_ids?: string | null;
  encarregado_id?: string | null;
  arquivo_url?: string | null;
  arquivo_nome?: string | null;
  captacao_entrega?: string;
  criado_em?: string;
  drive_url?: string | null;
  categoria_demanda?: string | null;
  produto_especifico?: string | null;
  observacoes?: string | null;
}

export interface HistoricoTramitacao {
  id: number;
  demanda_id: number;
  autor_nome: string;
  tipo_acao: 'criacao' | 'aprovacao' | 'ajuste' | 'rejeicao' | 'comentario' | 'conclusao';
  mensagem: string;
  criado_em: string;
}

export type StatusPresenca = 'P' | 'SV' | 'FE' | 'LE' | 'LTS' | 'DS' | 'MIS' | 'OUT' | 'PEND';

export interface MilitarEfetivo {
  id: number;
  nome_guerra: string;
  email?: string;
  role: UserRole;
  posto?: string;
  posto_grad?: string;
  data_nascimento?: string;
  url_foto?: string;
  setor?: string;
  categoria?: 'militar' | 'civil';
}

export interface RegistroPresenca {
  id?: number;
  data_referencia: string;
  militar_id: number;
  nome_guerra: string;
  posto_grad: string;
  setor: string;
  status: StatusPresenca;
  detalhe?: string;
  atualizado_por?: string;
  atualizado_em?: string;
}

export type TarefaStatus = 'a_fazer' | 'em_andamento' | 'revisao' | 'concluido';
export type TarefaPrioridade = 'alta' | 'media' | 'baixa';
export type TarefaTipo = 
  | 'producao_arte' 
  | 'video_reels' 
  | 'faxina_rotina' 
  | 'manutencao_apoio' 
  | 'impressao' 
  | 'redacao' 
  | 'brindes' 
  | 'evento_cobertura' 
  | 'outro';

export interface TarefaAnexoMidia {
  id: string;
  nome: string;
  url: string;
  tipo: 'referencia' | 'previa_producao' | 'final_aprovada';
  enviado_por: string;
  enviado_em: string;
  formato?: 'imagem' | 'video' | 'documento' | 'outro';
  tamanho?: string;
  versao?: number;
}

export interface TarefaApontamento {
  id: string;
  autor: string;
  autor_posto?: string;
  autor_foto?: string;
  texto: string;
  criado_em: string;
  resolvido?: boolean;
}

export interface TarefaCOMSOC {
  id: number;
  titulo: string;
  descricao?: string;
  responsavel: string;
  responsavel_id?: number | string | null;
  solicitante_nome?: string;
  solicitante_posto?: string;
  solicitante_id?: number | string | null;
  solicitante_foto?: string;
  tipo_tarefa?: TarefaTipo;
  prioridade: TarefaPrioridade;
  status: TarefaStatus;
  ordem_prioridade?: number;
  prazo?: string | null;
  demanda_id?: number | null;
  anexos_midia?: TarefaAnexoMidia[];
  apontamentos_ajuste?: TarefaApontamento[];
  criado_em: string;
  atualizado_em?: string | null;
}

export interface JadeEvento {
  id: number;
  nome: string;
  data_evento: string;
  local?: string | null;
  tipo_layout: 'auditorio' | 'mesa_u' | 'banquete' | 'teatro';
  layout_json: {
    rows: number;
    cols: number;
    blocked_seats?: string[];
    labels?: Record<string, string>;
  };
  status: 'ativo' | 'arquivado';
  created_at: string;
}

export interface JadeConvidado {
  id: number;
  evento_id: number;
  nome: string;
  posto_graduacao?: string | null;
  cargo_funcao?: string | null;
  categoria: string;
  convidado_principal_id?: number | null;
  max_acompanhantes: number;
  assento_id?: string | null;
  status_confirmacao: 'confirmado' | 'pendente' | 'recusado';
  status_placa: 'pendente' | 'impressa' | 'necessaria' | 'nao_necessaria' | 'reimpressao' | string;
  checkin_at?: string | null;
  url_foto?: string | null;
  telefone?: string | null;
  email?: string | null;
  token_rsvp?: string | null;
}

// 📦 Bloco 3: Logística & Material
export interface BrindeEstoque {
  id: number;
  nome_item: string;
  quantidade_total: number;
  quantidade_disponivel: number;
  descricao?: string | null;
  criado_em: string;
}

export interface BrindeDistribuicao {
  id: number;
  brinde_id: number;
  brinde_nome?: string;
  quantidade: number;
  destinatario_nome: string;
  data_entrega: string;
  demanda_id?: number | null;
  entregue_por: string;
  criado_em: string;
}

export interface EquipamentoCOMSOC {
  id: number;
  nome: string;
  e_pessoal: boolean;
  descricao?: string | null;
  categoria?: 'camera' | 'lente' | 'drone' | 'audio' | 'iluminacao' | 'acessorio';
  status?: 'disponivel' | 'cautelado' | 'manutencao';
  cautelado_por?: string | null;
}

export interface CautelaItem {
  id: number;
  equipamento: string;
  retirado_por: string;
  data_retirada: string;
  data_devolucao?: string | null;
  pauta_id?: number | null;
  status: 'retirado' | 'devolvido' | 'avaria';
  e_pessoal: boolean;
  event_date?: string | null;
}

// 🎖️ Bloco 4: Cerimonial & Protocolo Naval (Almanaque de Autoridades)
export interface AutoridadeBase {
  id: string | number;
  posto_graduacao: string;
  nome_completo: string;
  nome_guerra_ou_tratamento: string;
  cargo_funcao?: string;
  orgao_om?: string;
  categoria_grupo:
    | 'almirantado'
    | 'oficiais_superiores'
    | 'oficiais'
    | 'governo'
    | 'judiciario_legislativo'
    | 'reitores'
    | 'ttc_veteranos'
    | 'diplomatico'
    | 'civil_vip';
  email_oficial?: string;
  email_ajudancia?: string;
  whatsapp_celular?: string;
  precedencia_ordem: number;
  antiguidade_data?: string;
  observacoes?: string;
  autoridade_vinculada_id?: string | number | null;
  tipo_vinculo?:
    | 'ajudante_ordens'
    | 'assessor'
    | 'chefe_gabinete'
    | 'conjuge_acompanhante'
    | 'secretario'
    | 'subordinado'
    | 'outro';
}
