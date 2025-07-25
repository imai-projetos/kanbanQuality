import streamlit as st
from connect import load_data
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import date, datetime, timedelta
import pytz

# Configuração da página
st.set_page_config(page_title="📦 Kanban de Pedidos", layout="wide")

# Atualização automática a cada 60 segundos
st_autorefresh(interval = 60 * 1000, key="auto_refresh")

# Conteúdo da página
st.title("📦 Kanban de Pedidos - Operacional")
br_tz = pytz.timezone("America/Sao_Paulo")
fuso_brasil = pytz.timezone('America/Sao_Paulo')
st.markdown(f"🕒 Última atualização: **{datetime.now(br_tz).strftime('%d/%m/%Y %H:%M:%S')}**")

# CARREGAMENTO E PRÉ-PROCESSAMENTO DOS DADOS
df = load_data(source="postgres")

# Converter colunas para datetime
for col in ['data_hora_pedido','data_hora_faturamento','inicio_separacao', 'fim_separacao', 'inicio_conferencia', 'fim_conferencia']:
    df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize('America/Sao_Paulo')

st.sidebar.header("🔍 Filtros")

# FILTRO DE FILIAL (empresa)
filiais_disponiveis = sorted(df['empresa'].dropna().unique().tolist())
filial_selecionada = st.sidebar.multiselect("Filial", filiais_disponiveis, default=filiais_disponiveis)

# FILTRO DE MODALIDADE
modalidades_disponiveis = sorted(df['modalidade'].dropna().unique().tolist())
modalidade_selecionada = st.sidebar.multiselect("Modalidade", modalidades_disponiveis, default=modalidades_disponiveis)

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Parâmetros de Tempo")

limite_vermelho = st.sidebar.slider("⛔ Tempo para alerta vermelho (minutos)", min_value=1, max_value=60, value=4)
limite_amarelo = st.sidebar.slider("⚠️ Tempo para alerta amarelo (minutos)", min_value=0, max_value=limite_vermelho, value=2)

# APLICAR FILTROS AO DATAFRAME
df = df[df['empresa'].isin(filial_selecionada) & df['modalidade'].isin(modalidade_selecionada)]

df['data_hora_pedido'] = pd.to_datetime(df['data_hora_pedido'], errors='coerce')
df['tempo_total_pedido'] = pd.to_timedelta(df['tempo_total_pedido'], errors='coerce')

# Normalizar status_pedido para garantir os filtros
df['status_pedido'] = df['status_pedido'].astype(str).str.strip().str.lower()

# INDICADORES GERAIS 
st.subheader("📊 Tempos Médios")

col1, col2, col3, col4, col5, col6 = st.columns(6)

# 1. Tempo médio de separação
tempo_sep = (df['fim_separacao'] - df['inicio_separacao']).mean()
tempo_sep_max = (df['fim_separacao'] - df['inicio_separacao']).max()

# 2. Tempo médio de conferência
tempo_conf = (df['fim_conferencia'] - df['inicio_conferencia']).mean()
tempo_conf_max = (df['fim_conferencia'] - df['inicio_conferencia']).max()

# 3. Tempo médio total do pedido
tempo_total = df['tempo_total_pedido'].mean()
tempo_total_max = df['tempo_total_pedido'].max()

# 4. Tempo médio até início da separação
tempo_ate_separacao = (df['inicio_separacao'] - df['data_hora_pedido'] ).mean()
tempo_ate_separacao_max = (df['inicio_separacao'] - df['data_hora_pedido'] ).max()

# 5. Tempo médio entre fim da separação e início da conferência
tempo_espera_conf = (df['inicio_conferencia'] - df['fim_separacao']).mean()
tempo_espera_conf_max = (df['inicio_conferencia'] - df['fim_separacao']).max()

# 6. Tempo médio para faturamento
tempo_para_faturamento = (df['data_hora_faturamento'] - df['data_hora_pedido']).mean()
tempo_para_faturamento_max = (df['data_hora_faturamento'] - df['data_hora_pedido']).max()

# 🚨 Indicador: Pedidos acima de 10 minutos
total_pedidos = df.shape[0]
acima_10min = df[df['tempo_total_pedido'] > pd.Timedelta(minutes=10)].shape[0]
percentual_acima_10min = (acima_10min / total_pedidos * 100) if total_pedidos > 0 else 0

st.markdown(f"📋 Total Pedidos: **{total_pedidos}**")
st.markdown(f"🚨 Pedidos acima de 10 minutos: **{acima_10min}** ({percentual_acima_10min:.1f}%)")

# Exibir indicadores
# Função para formatar timedelta para HH:MM:SS
def format_timedelta(td):
    if pd.isna(td):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    horas = total_seconds // 3600
    minutos = (total_seconds % 3600) // 60
    segundos = total_seconds % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

def render_card(col, titulo, valor, maximo, emoji=""):
    col.markdown(f"""
    <div style="
        background-color:#1239FF;
        border-radius:12px;
        padding:12px;
        text-align:center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        color:white;
    ">
        <div style="font-size:20px;font-weight:600;">{emoji} {titulo}</div>
        <div style="font-size:35px;font-weight:bold;margin-top:6px;">{valor}</div>
        <div style="font-size:18px;margin-top:4px;">Máx: {maximo}</div>
    </div>
    """, unsafe_allow_html=True)

# Renderizar os indicadores padronizados
render_card(col1, "Até Início Separação", format_timedelta(tempo_ate_separacao), format_timedelta(tempo_ate_separacao_max), "🚚")
render_card(col2, "Separação", format_timedelta(tempo_sep), format_timedelta(tempo_sep_max), "⏱️")
render_card(col3, "Espera Conferência", format_timedelta(tempo_espera_conf), format_timedelta(tempo_espera_conf_max), "⏳")
render_card(col4, "Conferência", format_timedelta(tempo_conf), format_timedelta(tempo_conf_max), "🧪")
render_card(col5, "Faturar", format_timedelta(tempo_para_faturamento), format_timedelta(tempo_para_faturamento_max), "💰")
render_card(col6, "Total Pedido", format_timedelta(tempo_total), format_timedelta(tempo_total_max), "📦")

# PEDIDOS POR STATUS 
st.subheader("📋 Pedidos por Status")

# Filtrar apenas os pedidos do dia atual
agora_brasil = pd.Timestamp.now(tz=fuso_brasil)
hoje = agora_brasil.normalize()  # exemplo: 2025-07-17 00:00:00-03:00

# Converter data_hora_pedido para timezone America/Sao_Paulo, se ainda não estiver com timezone
if df['data_hora_pedido'].dt.tz is None:
    # Se timezone-naive, localiza para o fuso correto (assume que a hora está no horário de SP)
    df['data_hora_pedido'] = df['data_hora_pedido'].dt.tz_localize(fuso_brasil)
else:
    # Se já tem timezone, converte para o fuso correto
    df['data_hora_pedido'] = df['data_hora_pedido'].dt.tz_convert(fuso_brasil)

# Filtrar apenas os pedidos que ocorreram no dia atual, no fuso Brasil
df_hoje = df[(df['data_hora_pedido'] >= hoje) & (df['data_hora_pedido'] < hoje + pd.Timedelta(days=1))]

# Lista de status e rótulos amigáveis
status_selecionados = ['pendente', 'em separacao', 'separado']
status_display = {
    'pendente': 'Aguardando Separação',
    'em separacao': 'Em Separação',
    'separado': 'Aguardando Conferência'}

# Filtrar apenas os status desejados
df_status = df_hoje[df_hoje['status_pedido'].isin(status_selecionados)]

# Criar colunas lado a lado
col1, col2, col3= st.columns(3)
cols = [col1, col2, col3]

# Ajustar timezone nas colunas de data/hora usadas no cálculo
for col in ['data_hora_pedido', 'inicio_separacao', 'fim_separacao']:
    if df_status[col].dt.tz is None:
        df_status[col] = df_status[col].dt.tz_localize(fuso_brasil)
    else:
        df_status[col] = df_status[col].dt.tz_convert(fuso_brasil)

# Definir a última atualização com timezone correto
ultima_atualizacao = pd.Timestamp.now(tz=fuso_brasil)

for idx, status_key in enumerate(status_selecionados):
    df_temp = df_status[df_status['status_pedido'] == status_key].copy()
    df_temp = df_temp[['id_pedido', 'nf', 'cliente', 'modalidade', 'data_hora_pedido', 'inicio_separacao', 'fim_separacao']].dropna(subset=['id_pedido'])

    # Garantir que 'nf' seja string (evita problemas com número decimal)
    df_temp['nf'] = df_temp['nf'].apply(lambda x: str(int(x)) if pd.notnull(x) else "")

    if status_key != 'conferido' and not df_temp.empty:
        def calcular_duracao(row):
            try:
                if status_key == 'pendente':
                    base = row['data_hora_pedido']
                elif status_key == 'em separacao':
                    base = row['inicio_separacao']
                elif status_key == 'separado':
                    base = row['fim_separacao']
                else:
                    return None

                if pd.notnull(base):
                    return (ultima_atualizacao - base).total_seconds() / 60
                return None
            except:
                return None

        df_temp['minutos_no_status'] = df_temp.apply(calcular_duracao, axis=1)

        def aplicar_cor(row):
            minutos = row['minutos_no_status']
            if pd.isnull(minutos):
                return ''
            if minutos > limite_vermelho:
                return 'background-color: #dc3545; color: white; text-align: center; font-size: 12px;'
            elif minutos > limite_amarelo:
                return 'background-color: #ffc107; color: black; text-align: center; font-size: 12px;'
            return ''

        df_visual = df_temp[['data_hora_pedido', 'cliente', 'nf', 'modalidade']].copy()

        # Extrair só HH:MM
        df_visual['data_hora_pedido'] = pd.to_datetime(df_visual['data_hora_pedido']).dt.strftime('%H:%M')

        # Renomear colunas para o display
        df_visual = df_visual.rename(columns={
            'data_hora_pedido': 'EMISSÃO',
            'cliente': 'CLIENTE',
            'nf': 'NF',
            'modalidade': 'MODALIDADE'
        })
        estilos = df_temp.apply(aplicar_cor, axis=1).tolist()
        styled_df = df_visual.style.apply(lambda _: estilos, axis=0)
    else:
        styled_df = df_temp[['id_pedido', 'cliente', 'nf','modalidade']].style

    with cols[idx]:
        count = len(df_temp)
        st.markdown(f"""
            <div style='background-color:#1239FF;padding:8px;border-radius:8px;
                        text-align:center;margin-bottom:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>
                <h5 style='color:white;margin:0;font-size:22px'>{status_display[status_key]}</h5>
                <p style='color:white;margin:0;font-size:20px'>{count} pedido(s)</p>
            </div>
        """, unsafe_allow_html=True)

        if not df_temp.empty:
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True
            )

            df_temp = df_temp.sort_values(by='id_pedido', ascending=False)
        else:
            st.markdown(
                "<div style='color:white;padding:15px;text-align:center;'>Nenhum pedido.</div>",
                unsafe_allow_html=True
            )