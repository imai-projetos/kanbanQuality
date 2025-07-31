import streamlit as st
from connect import load_data
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# Configuração da página
st.set_page_config(page_title="📦 Quadro de Pedidos", layout="wide")

# CSS para ocupar altura total da janela
st.markdown("""
    <style>
        html, body, [data-testid="stApp"] {
            height: 100%;
        }
        .main {
            min-height: 100vh;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .block-container {
            padding-top: 0rem;
            flex: 1 0 auto;
        }
        header[data-testid="stHeader"] {
            margin: 0;
        }
    </style>
""", unsafe_allow_html=True)

# Atualização automática a cada 10 segundos
refresh_interval = 10 * 1000  # 10 segundos
count = st_autorefresh(interval=refresh_interval, key="auto_refresh_toggle")

# Alternância entre os status
if "mostrar_separacao" not in st.session_state:
    st.session_state.mostrar_separacao = True
else:
    st.session_state.mostrar_separacao = not st.session_state.mostrar_separacao

# Título e hora da última atualização
st.title("📦 Quadro de Pedidos - Clientes Quality")
fuso_brasil = pytz.timezone('America/Sao_Paulo')
agora = pd.Timestamp.now(tz=fuso_brasil)
st.markdown(f"🕒 Última atualização: **{agora.strftime('%d/%m/%Y %H:%M:%S')}**")

# Carregamento dos dados
df = load_data(source="postgres")

# Conversão para datetime
for col in ['data_hora_pedido', 'data_hora_faturamento', 'inicio_separacao', 'fim_separacao', 'inicio_conferencia', 'fim_conferencia']:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# Sidebar – filtros
st.sidebar.header("🔍 Filtros")
filiais_disponiveis = sorted(df['empresa'].dropna().unique().tolist())
filial_selecionada = st.sidebar.multiselect("Filial", filiais_disponiveis, default=filiais_disponiveis)

# Aplicar filtros
df = df[(df['empresa'].isin(filial_selecionada)) & (df['modalidade'] == 'BALCAO')]
df['tempo_total_pedido'] = pd.to_timedelta(df['tempo_total_pedido'], errors='coerce')

# Pedidos do dia
hoje = agora.normalize()
df['data_hora_pedido'] = pd.to_datetime(df['data_hora_pedido'], errors='coerce')
df['data_hora_pedido'] = df['data_hora_pedido'].dt.tz_localize(None).dt.tz_localize(fuso_brasil, ambiguous='NaT')
df_hoje = df[(df['data_hora_pedido'] >= hoje) & (df['data_hora_pedido'] < hoje + pd.Timedelta(days=1))]

# Ajuste de timezone
for col in ['inicio_separacao', 'fim_separacao', 'inicio_conferencia', 'fim_conferencia']:
    df_hoje[col] = pd.to_datetime(df_hoje[col], errors='coerce')
    df_hoje[col] = df_hoje[col].dt.tz_localize(None).dt.tz_localize(fuso_brasil, ambiguous='NaT')

# Mapeamento dos status
status_grupos = {
    'em separacao': df_hoje[df_hoje['status_pedido'].str.lower().isin(['pendente', 'em separacao'])],
    'em conferencia': df_hoje[df_hoje['status_pedido'].str.lower() == 'separado'],
}

status_display = {
    'em separacao': 'Em Separação',
    'em conferencia': 'Em Conferência'
}

tabela_cores = {
    'em separacao': {'bg': '#fd7e14', 'header': '#e8590c', 'font': 'black'},
    'em conferencia': {'bg': '#ffc107', 'header': '#e0a800', 'font': 'black'},
}

# Determinar qual status exibir
status_chave = 'em separacao' if st.session_state.mostrar_separacao else 'em conferencia'
df_temp = status_grupos[status_chave][['id_pedido', 'nf', 'cliente', 'data_hora_pedido']].dropna(subset=['id_pedido']).copy()

# Processamento dos dados
df_temp['cliente'] = df_temp['cliente'].str.split(' - ', n=1).str[1]
df_temp['nf'] = df_temp['nf'].apply(lambda x: str(int(x)) if pd.notnull(x) else "")
df_temp['hora_emissao'] = pd.to_datetime(df_temp['data_hora_pedido'], errors='coerce').dt.strftime('%H:%M')

# Exibição
with st.container():
    count = len(df_temp)
    display_name = status_display[status_chave]
    cor_fundo = tabela_cores[status_chave]['bg']
    cor_header = tabela_cores[status_chave]['header']
    cor_fonte = tabela_cores[status_chave]['font']
    class_name = status_chave.replace(' ', '-') + "-table"

    st.markdown(f"""
        <div style='background-color: black; padding:8px; border-radius:8px;
                    text-align:center; margin-bottom:10px; 
                    border: 2px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.1);'>
            <h5 style='color: white; margin:1; font-size:28px; text-transform:uppercase;'>
                {display_name}
            </h5>
            <p style='color: white; margin:0; font-size:25px'>{count} pedido(s)</p>
        </div>
    """, unsafe_allow_html=True)

    if not df_temp.empty:
        st.markdown(f"""
            <style>
                .{class_name} {{
                    background-color: {cor_fundo};
                    color: {cor_fonte};
                    border-collapse: collapse;
                    width: 100%;
                    font-size: 28px;
                    font-weight: bold;
                }}
                .{class_name} th, .{class_name} td {{
                    border: 1px solid #ffffff22;
                    padding: 1px;
                    text-align: center;
                }}
                .{class_name} th {{
                    background-color: {cor_header};
                    color: black;
                    text-transform: uppercase;
                }}
                .{class_name} td:nth-child(2) {{
                    text-align: left !important;
                    padding-left: 10px;
                }}
            </style>
        """, unsafe_allow_html=True)

        df_temp = df_temp.sort_values(by='cliente', ascending=True)
        df_temp = df_temp.rename(columns={
            'hora_emissao': 'EMISSÃO',
            'cliente': 'CLIENTE',
            'nf': 'NF'
        })
        df_temp = df_temp[['EMISSÃO', 'CLIENTE', 'NF']]
        html_table = df_temp.to_html(classes=class_name, index=False, escape=False)
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='color:#888;padding:15px;text-align:center;'>Nenhum pedido.</div>",
            unsafe_allow_html=True
        )
