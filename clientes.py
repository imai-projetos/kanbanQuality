import streamlit as st
from connect import load_data
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# Configuração da página
st.set_page_config(page_title="📦 Quadro de Pedidos", layout="wide")

# Atualização automática a cada 45 segundos
st_autorefresh(interval=45 * 1000, key="auto_refresh")

# Título e data/hora da última atualização
st.title("📦 Quadro de Pedidos - Clientes Quality")
fuso_brasil = pytz.timezone('America/Sao_Paulo')
agora = pd.Timestamp.now(tz=fuso_brasil)
st.markdown(f"🕒 Última atualização: **{agora.strftime('%d/%m/%Y %H:%M:%S')}**")

# Carregamento dos dados
df = load_data(source="postgres")

# Converter colunas para datetime
for col in ['data_hora_pedido','data_hora_faturamento','inicio_separacao', 'fim_separacao', 'inicio_conferencia', 'fim_conferencia']:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# Sidebar – filtros
st.sidebar.header("🔍 Filtros")

filiais_disponiveis = sorted(df['empresa'].dropna().unique().tolist())
filial_selecionada = st.sidebar.multiselect("Filial", filiais_disponiveis, default=filiais_disponiveis)

# Novos parâmetros na sidebar
st.sidebar.markdown("⏱️ Tempo máximo de exibição (em minutos):")
limite_caixa = st.sidebar.slider("Dirija-se ao Caixa", 1, 60, 10)
limite_retirada = st.sidebar.slider("Retire seu Pedido", 1, 60, 10)

# Aplicar filtros: apenas BALCAO e filiais selecionadas
df = df[(df['empresa'].isin(filial_selecionada)) & (df['modalidade'] == 'BALCAO')]

# Converter tipo da coluna tempo_total_pedido
df['tempo_total_pedido'] = pd.to_timedelta(df['tempo_total_pedido'], errors='coerce')

# Pedidos do dia atual
hoje = agora.normalize()
df['data_hora_pedido'] = pd.to_datetime(df['data_hora_pedido'], errors='coerce')
df['data_hora_pedido'] = df['data_hora_pedido'].dt.tz_localize(None).dt.tz_localize(fuso_brasil, ambiguous='NaT')
df_hoje = df[(df['data_hora_pedido'] >= hoje) & (df['data_hora_pedido'] < hoje + pd.Timedelta(days=1))]

# Atualização de timezone em colunas importantes
for col in ['inicio_separacao', 'fim_separacao', 'inicio_conferencia', 'fim_conferencia']:
    df_hoje[col] = pd.to_datetime(df_hoje[col], errors='coerce')
    df_hoje[col] = df_hoje[col].dt.tz_localize(None).dt.tz_localize(fuso_brasil, ambiguous='NaT')

# Mapeamento de status agrupados
status_grupos = {
    'em separacao': df_hoje[df_hoje['status_pedido'].str.lower().isin(['pendente', 'em separacao'])],
    'em conferencia': df_hoje[df_hoje['status_pedido'].str.lower() == 'separado'],
    'dirija-se ao caixa': df_hoje[df_hoje['fim_conferencia'].notna() & df_hoje['data_hora_faturamento'].isna()],
    'retire seu pedido': df_hoje[df_hoje['fim_conferencia'].notna() & df_hoje['data_hora_faturamento'].notna()]
}

# Aplicar limite de tempo para os status finais
hora_limite_caixa = agora - pd.Timedelta(minutes=limite_caixa)
hora_limite_retirada = agora - pd.Timedelta(minutes=limite_retirada)

status_grupos['dirija-se ao caixa'] = status_grupos['dirija-se ao caixa'][
    status_grupos['dirija-se ao caixa']['fim_conferencia'] >= hora_limite_caixa
]

status_grupos['retire seu pedido'] = status_grupos['retire seu pedido'][
    status_grupos['retire seu pedido']['fim_conferencia'] >= hora_limite_retirada
]

status_display = {
    'em separacao': 'Em Separação',
    'em conferencia': 'Em Conferência',
    'dirija-se ao caixa': 'Dirija-se ao Caixa',
    'retire seu pedido': 'Retire seu Pedido'
}

# Define a cor da tabela com base no status
tabela_cores = {
    'em separacao': {'bg': '#ffc107', 'header': '#e0a800', 'font': 'black'},
    'em conferencia': {'bg': '#fd7e14', 'header': '#e8590c', 'font': 'white'},
    'dirija-se ao caixa': {'bg': '#28a745', 'header': '#218838', 'font': 'white'},
    'retire seu pedido': {'bg': '#1239FF', 'header': "#0A26AF", 'font': 'white'}
}

# Criar colunas para exibição
col1, col2, col3, col4 = st.columns(4)
cols = [col1, col2, col3, col4]

for idx, (grupo_status, df_temp) in enumerate(status_grupos.items()):
    df_temp = df_temp[['id_pedido', 'nf', 'cliente', 'data_hora_pedido']].dropna(subset=['id_pedido']).copy()
    
    # Formatar NF
    df_temp['nf'] = df_temp['nf'].apply(lambda x: str(int(x)) if pd.notnull(x) else "")
    
    # Criar coluna com hora da emissão
    df_temp['hora_emissao'] = pd.to_datetime(df_temp['data_hora_pedido'], errors='coerce').dt.strftime('%H:%M')

    with cols[idx]:
        count = len(df_temp)
        display_name = status_display[grupo_status]

        # Cores e classe
        cor_fundo = tabela_cores[grupo_status]['bg']
        cor_header = tabela_cores[grupo_status]['header']
        cor_fonte = tabela_cores[grupo_status]['font']
        class_name = grupo_status.replace(' ', '-') + "-table"

        st.markdown(f"""
            <div style='background-color: white; padding:8px; border-radius:8px;
                        text-align:center; margin-bottom:10px; 
                        border: 2px solid black; box-shadow:0 2px 4px rgba(0,0,0,0.1);'>
                <h5 style='color: black; margin:1; font-size:22px; text-transform:uppercase;'>
                    {display_name}
                </h5>
                <p style='color: black; margin:0; font-size:20px'>{count} pedido(s)</p>
            </div>
        """, unsafe_allow_html=True)

        if not df_temp.empty:
            # CSS personalizado
            st.markdown(f"""
                <style>
                    .{class_name} {{
                        background-color: {cor_fundo};
                        color: {cor_fonte};
                        border-collapse: collapse;
                        width: 100%;
                        font-size: 16px;
                    }}
                    .{class_name} th, .{class_name} td {{
                        border: 1px solid #ffffff22;
                        padding: 5px;
                        text-align: center;
                    }}
                    .{class_name} th {{
                        background-color: {cor_header};
                        color: white;
                        text-transform: uppercase;
                    }}
                    .{class_name} td:nth-child(3) {{
                        text-align: left !important;
                        padding-left: 10px;
                    }}
                </style>
            """, unsafe_allow_html=True)

            # Ordenar e renomear
            df_temp = df_temp.sort_values(by='id_pedido', ascending=False)
            df_temp = df_temp.rename(columns={
                'id_pedido': 'PEDIDO',
                'nf': 'NF',
                'cliente': 'CLIENTE',
                'hora_emissao': 'HORA PEDIDO'
            })

            df_temp = df_temp[['PEDIDO', 'NF', 'CLIENTE', 'HORA PEDIDO']]

            html_table = df_temp.to_html(classes=class_name, index=False, escape=False)
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.markdown(
                "<div style='color:#888;padding:18px;text-align:center;'>Nenhum pedido.</div>",
                unsafe_allow_html=True
            )
