import streamlit as st
from connect import load_data
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import date, datetime, timedelta

# Configuração da página
st.set_page_config(page_title="📦 Kanban de Pedidos", layout="wide")

# Atualização automática a cada 60 segundos
st_autorefresh(interval = 60 * 1000, key="auto_refresh")

# Conteúdo da página
st.title("📦 Kanban de Pedidos")
st.markdown(f"🕒 Última atualização: **{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}**")

# CARREGAMENTO E PRÉ-PROCESSAMENTO DOS DADOS
df = load_data(source="postgres")

# Converter colunas para datetime
for col in ['data_hora_pedido','data_hora_faturamento','inicio_separacao', 'fim_separacao', 'inicio_conferencia', 'fim_conferencia']:
    df[col] = pd.to_datetime(df[col], errors='coerce')

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
render_card(col5, "Faturamentar", format_timedelta(tempo_para_faturamento), format_timedelta(tempo_para_faturamento_max), "💰")
render_card(col6, "Total Pedido", format_timedelta(tempo_total), format_timedelta(tempo_total_max), "📦")

# PEDIDOS POR STATUS (apenas do dia atual)
st.subheader("📋 Pedidos por Status (Hoje)")

# Filtrar apenas os pedidos do dia atual
hoje = pd.Timestamp(date.today())
df_hoje = df[df['data_hora_pedido'].dt.date == hoje.date()]

# Lista de status e rótulos amigáveis
status_selecionados = ['pendente', 'em separacao', 'separado','conferido']
status_display = {
    'pendente': 'Aguardando Separação',
    'em separacao': 'Em Separação',
    'separado': 'Aguardando Conferência',
    'conferido': 'Conferido'}

# Filtrar apenas os status desejados
df_status = df_hoje[df_hoje['status_pedido'].isin(status_selecionados)]

# Criar colunas lado a lado
col1, col2, col3, col4 = st.columns(4)
cols = [col1, col2, col3, col4]

# Preencher as colunas com visual profissional e formatação condicional
# Horário da última atualização 
ultima_atualizacao = pd.Timestamp.now()

for idx, status_key in enumerate(status_selecionados):
    df_temp = df_status[df_status['status_pedido'] == status_key].copy()
    df_temp = df_temp[['id_pedido', 'nf', 'cliente', 'data_hora_pedido', 'inicio_separacao', 'fim_separacao']].dropna(subset=['id_pedido'])

    # Garantir que 'nf' seja string (evita problemas com número decimal)
    # Ajuste o campo 'nf' para string sem decimais
    df_temp['nf'] = df_temp['nf'].apply(lambda x: str(int(x)) if pd.notnull(x) else "")

    # Cálculo do tempo no status (em minutos)
    if status_key != 'conferido' and not df_temp.empty:
        def calcular_duracao(row):
            try:
                if status_key == 'pendente':
                    if pd.notnull(row['data_hora_pedido']):
                        base = pd.to_datetime(row['data_hora_pedido'], errors='coerce')                     
                    else:
                        return None
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

        # Aplica cálculo
        df_temp['minutos_no_status'] = df_temp.apply(calcular_duracao, axis=1)

        # Formatação condicional por tempo decorrido
        def aplicar_cor(row):
            minutos = row['minutos_no_status']
            if pd.isnull(minutos):
                return ''
            if minutos > 4:
                return 'background-color: #dc3545; color: white; text-align: center; font-size: 12px;'  # vermelho forte
            elif minutos > 2:
                return 'background-color: #ffc107; color: black; text-align: center; font-size: 12px;'  # amarelo forte
            return ''

        # Aplica estilo condicional apenas às colunas visuais
        df_visual = df_temp[['id_pedido', 'cliente','nf']].copy()
        estilos = df_temp.apply(aplicar_cor, axis=1).tolist()
        styled_df = df_visual.style.apply(lambda _: estilos, axis=0)
    else:
        styled_df = df_temp[['id_pedido', 'cliente', 'nf']].style

    # Renderização visual por coluna
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
                hide_index=True,
                height=min(400, 40 + 40 * len(df_temp))
            )
        else:
            st.markdown(
                "<div style='color:#888;padding:10px;text-align:center;'>Nenhum pedido.</div>",
                unsafe_allow_html=True
            )

# EFICIÊNCIA OPERACIONAL (em stand-by)
# st.subheader("👷 Eficiência Operacional")
# tab1, tab2 = st.tabs(["Separador", "Conferente"])

# with tab1:
#     sep_df = df.copy()
#     sep_df['tempo_sep'] = sep_df['fim_separacao'] - sep_df['inicio_separacao']
#     sep_grouped = sep_df.groupby('separador').agg({
#         'id_pedido': 'count',
#         'tempo_sep': 'mean'
#     }).reset_index().rename(columns={'id_pedido': 'Qtd Pedidos', 'tempo_sep': 'Tempo Médio'})
#     st.dataframe(sep_grouped)

# with tab2:
#     conf_df = df.copy()
#     conf_df['tempo_conf'] = conf_df['fim_conferencia'] - conf_df['inicio_conferencia']
#     conf_grouped = conf_df.groupby('conferente').agg({
#         'id_pedido': 'count',
#         'tempo_conf': 'mean'
#     }).reset_index().rename(columns={'id_pedido': 'Qtd Pedidos', 'tempo_conf': 'Tempo Médio'})
#     st.dataframe(conf_grouped)

