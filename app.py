import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import plotly.express as px

# ============================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(
    page_title="Assistência Técnica - Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔧 Dashboard de Assistência Técnica")
st.markdown("**Acompanhamento em tempo real das assistências por Região**")
st.markdown("---")

# ============================================
# UPLOAD DO ARQUIVO
# ============================================
st.sidebar.header("📁 Upload da Planilha")

uploaded_file = st.sidebar.file_uploader(
    "Selecione sua planilha do Google Sheets",
    type=["xlsx", "xls", "csv"],
    help="Baixe sua planilha do Google Sheets (Arquivo → Baixar) e faça upload aqui"
)

if uploaded_file is None:
    st.info("""
    ### 📥 Como usar este dashboard:
    
    1. **Abra sua planilha no Google Sheets**
    2. Clique em **Arquivo → Baixar**
    3. Escolha **Planilha do Microsoft Excel (.xlsx)** ou **CSV**
    4. **Faça upload do arquivo** usando o botão acima
    
    ✅ **Totalmente seguro:** Seus dados nunca saem do seu computador
    ✅ **Atualização automática:** A página recarrega a cada 15 segundos
    
    📌 **Sua planilha deve conter uma coluna "Região" com valores: Região 1, Região 2, Região 3**
    """)
    st.stop()

# ============================================
# CARREGAR DADOS
# ============================================
@st.cache_data(ttl=15, show_spinner=False)
def carregar_dados(file):
    """Carrega dados do arquivo uploadado com tratamento de erro robusto"""
    try:
        if file.name.endswith('.csv'):
            for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file, encoding=encoding)
                    break
                except:
                    continue
        else:
            df = pd.read_excel(file)
        
        df = df.dropna(axis=1, how='all')
        return df, time.time()
    except Exception as e:
        st.error(f"❌ Erro ao carregar arquivo: {e}")
        return None, None

df, timestamp_atualizacao = carregar_dados(uploaded_file)

if df is None or df.empty:
    st.error("❌ Não foi possível carregar os dados da planilha.")
    st.stop()

# ============================================
# IDENTIFICAR COLUNAS IMPORTANTES
# ============================================

# Identificar coluna de status
col_status = None
for col in df.columns:
    col_lower = str(col).strip().lower().replace('ç', 'c').replace('ã', 'a').replace('õ', 'o')
    if any(keyword in col_lower for keyword in ['status', 'situacao', 'situacão', 'estado']):
        col_status = col
        break

if not col_status:
    st.error("❌ Coluna de status não encontrada! Verifique os nomes das colunas.")
    st.write("Colunas disponíveis:", list(df.columns))
    st.stop()

# Identificar coluna de região (ESPECÍFICO PARA REGIÃO 1/2/3)
col_regiao = None
for col in df.columns:
    col_lower = str(col).strip().lower().replace('ç', 'c').replace('ã', 'a').replace('õ', 'o')
    if any(keyword in col_lower for keyword in ['regiao', 'região', 'regional']):
        col_regiao = col
        break

# Identificar coluna de departamento/setor
col_departamento = None
for col in df.columns:
    col_lower = str(col).strip().lower().replace('ç', 'c').replace('ã', 'a').replace('õ', 'o')
    if any(keyword in col_lower for keyword in ['departamento', 'setor', 'area', 'área', 'dept', 'unidade', 'equipe', 'time']):
        col_departamento = col
        break

# Identificar coluna de data
col_data = None
for col in df.columns:
    col_lower = str(col).strip().lower()
    if any(keyword in col_lower for keyword in ['data', 'dt_', 'abertura', 'entrada', 'registro']):
        col_data = col
        break

# ============================================
# PROCESSAR COLUNAS - NORMALIZAÇÃO
# ============================================

# Normalizar status
df['status_normalizado'] = df[col_status].fillna('').astype(str).str.strip()

# Normalizar região (PADRONIZAÇÃO PARA REGIÃO 1/2/3)
if col_regiao:
    df['regiao_normalizada'] = df[col_regiao].fillna('Não especificada').astype(str).str.strip()
    # Padronizar para "Região X" mesmo se vier como "regiao 1", "REGIÃO 1", etc.
    df['regiao_normalizada'] = df['regiao_normalizada'].str.lower()
    df['regiao_normalizada'] = df['regiao_normalizada'].str.replace('regiao', 'Região', regex=False)
    df['regiao_normalizada'] = df['regiao_normalizada'].str.replace('região', 'Região', regex=False)
    df['regiao_normalizada'] = df['regiao_normalizada'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # Garantir que só existam Região 1, 2, 3 ou "Não especificada"
    regioes_validas = ['Região 1', 'Região 2', 'Região 3']
    df['regiao_normalizada'] = df['regiao_normalizada'].apply(
        lambda x: x if x in regioes_validas else 'Não especificada'
    )
else:
    df['regiao_normalizada'] = 'Todas'

# Normalizar departamento
if col_departamento:
    df['departamento_normalizado'] = df[col_departamento].fillna('Não especificado').astype(str).str.strip()
else:
    df['departamento_normalizado'] = 'Todos'

# ============================================
# IDENTIFICAR VALORES ÚNICOS
# ============================================

todos_status = df['status_normalizado'].unique()
todos_status = sorted([s for s in todos_status if s and s != 'nan' and s != ''])

# Regiões fixas (Região 1, 2, 3) + Não especificada
todas_regioes = ['Região 1', 'Região 2', 'Região 3']
if 'Não especificada' in df['regiao_normalizada'].unique():
    todas_regioes.append('Não especificada')

todos_departamentos = []
if col_departamento:
    todos_departamentos = df['departamento_normalizado'].unique()
    todos_departamentos = sorted([d for d in todos_departamentos if d and d != 'nan' and d != ''])

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros")

# ============================================
# FILTRO DE REGIÃO (OTIMIZADO PARA REGIÃO 1/2/3)
# ============================================
st.sidebar.subheader("🌍 Região")

# Cores específicas para cada região
cores_regiao_map = {
    'Região 1': '#3498db',   # Azul
    'Região 2': '#2ecc71',   # Verde
    'Região 3': '#e74c3c',   # Vermelho
    'Não especificada': '#95a5a6'  # Cinza
}

selecionar_todas_regioes = st.sidebar.checkbox("Selecionar todas as regiões", value=True, key="regiao_todos")

if selecionar_todas_regioes:
    regioes_selecionadas = todas_regioes
else:
    # Exibir com cores visuais nos labels
    opcoes_regioes = []
    for reg in todas_regioes:
        cor = cores_regiao_map.get(reg, '#95a5a6')
        opcoes_regioes.append(f"{reg} •")
    
    regioes_selecionadas_nomes = st.sidebar.multiselect(
        "Selecione as regiões:",
        options=todas_regioes,
        default=todas_regioes[:min(3, len(todas_regioes))],
        help="Escolha uma ou mais regiões para filtrar"
    )
    regioes_selecionadas = regioes_selecionadas_nomes

# ============================================
# FILTROS RESTANTES (STATUS, DEPARTAMENTO, PERÍODO)
# ============================================

# Filtro de departamento
if col_departamento:
    st.sidebar.subheader("🏢 Departamento")
    selecionar_todos_dept = st.sidebar.checkbox("Selecionar todos os departamentos", value=True, key="dept_todos")
    if selecionar_todos_dept:
        dept_selecionados = todos_departamentos
    else:
        dept_selecionados = st.sidebar.multiselect(
            "Selecione os departamentos:",
            options=todos_departamentos,
            default=todos_departamentos[:min(3, len(todos_departamentos))],
            help="Escolha um ou mais departamentos para filtrar"
        )
else:
    dept_selecionados = todos_departamentos
    st.sidebar.info("⚠️ Coluna de departamento não identificada")

# Filtro de status
st.sidebar.subheader("📊 Status")
selecionar_todos_status = st.sidebar.checkbox("Selecionar todos os status", value=True, key="status_todos")
if selecionar_todos_status:
    status_selecionados = todos_status
else:
    status_selecionados = st.sidebar.multiselect(
        "Selecione os status:",
        options=todos_status,
        default=todos_status[:min(3, len(todos_status))],
        help="Escolha um ou mais status para filtrar"
    )

# Filtro de período
if col_data:
    st.sidebar.subheader("📅 Período")
    periodo = st.sidebar.selectbox(
        "Período",
        ["Todo o período", "Últimos 7 dias", "Últimos 15 dias", "Últimos 30 dias", "Últimos 90 dias"]
    )
else:
    periodo = "Todo o período"

# Filtro de busca livre
st.sidebar.subheader("🔍 Busca")
busca = st.sidebar.text_input("Buscar em qualquer campo", placeholder="Digite para filtrar...")

# ============================================
# APLICAR FILTROS
# ============================================

df_filtrado = df[df['regiao_normalizada'].isin(regioes_selecionadas)].copy()

if col_departamento and dept_selecionados:
    df_filtrado = df_filtrado[df_filtrado['departamento_normalizado'].isin(dept_selecionados)].copy()

if status_selecionados:
    df_filtrado = df_filtrado[df_filtrado['status_normalizado'].isin(status_selecionados)].copy()

if col_data and periodo != "Todo o período":
    try:
        df_filtrado['data_convertida'] = pd.to_datetime(
            df_filtrado[col_data], 
            errors='coerce',
            dayfirst=True
        )
        df_filtrado = df_filtrado.dropna(subset=['data_convertida'])
        
        dias_map = {"Últimos 7 dias": 7, "Últimos 15 dias": 15, "Últimos 30 dias": 30, "Últimos 90 dias": 90}
        dias_qtd = dias_map[periodo]
        data_limite = datetime.now() - timedelta(days=dias_qtd)
        df_filtrado = df_filtrado[df_filtrado['data_convertida'] >= data_limite]
        
    except Exception as e:
        st.sidebar.warning(f"⚠️ Não foi possível filtrar por data: {e}")

if busca:
    busca_lower = busca.lower()
    mask = df_filtrado.astype(str).apply(
        lambda row: row.str.lower().str.contains(busca_lower, na=False).any(), 
        axis=1
    )
    df_filtrado = df_filtrado[mask]

# ============================================
# MÉTRICAS PRINCIPAIS - CARDS POR STATUS
# ============================================
st.subheader("📊 Resumo por Status")

contagem_status = df_filtrado['status_normalizado'].value_counts().sort_index()

# Cores para status
cores_status = {
    'Aberta': '#27ae60', 'Aberto': '#27ae60',
    'Pendente': '#f39c12', 'Aguardando': '#f39800',
    'Em Análise': '#3498db', 'Análise': '#3498db',
    'Recusada': '#e74c3c', 'Recusado': '#e74c3c', 'Negada': '#c0392b',
    'Cancelada': '#95a5a6', 'Fechada': '#7f8c8d',
    'Concluída': '#16a085', 'Concluida': '#16a085',
    'Nova': '#3498db', 'Ativa': '#27ae60',
    'Em Andamento': '#f1c40f', 'Reparo': '#9b59b6', 'Teste': '#34495e',
}

if len(contagem_status) > 0:
    num_status = len(contagem_status)
    cols_por_linha = min(6, num_status)
    
    for i in range(0, num_status, cols_por_linha):
        cols = st.columns(cols_por_linha)
        for j, (status, quantidade) in enumerate(contagem_status.iloc[i:i+cols_por_linha].items()):
            with cols[j]:
                cor = '#95a5a6'
                for chave, valor in cores_status.items():
                    if chave.lower() in status.lower() or status.lower() in chave.lower():
                        cor = valor
                        break
                
                st.markdown(f"""
                    <div style="
                        background: linear-gradient(145deg, {cor}99, {cor});
                        color: white;
                        padding: 1.2rem;
                        border-radius: 12px;
                        text-align: center;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        margin: 8px;
                        border: 2px solid {cor}cc;
                    ">
                        <h3 style="margin: 0; font-size: 1.1rem; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">{status}</h3>
                        <h1 style="margin: 0.6rem 0 0 0; font-size: 2.8rem; font-weight: bold;">{quantidade}</h1>
                    </div>
                """, unsafe_allow_html=True)
else:
    st.warning("⚠️ Nenhum registro encontrado com os filtros selecionados.")

# ============================================
# MÉTRICAS POR REGIÃO (OTIMIZADO PARA REGIÃO 1/2/3)
# ============================================
st.markdown("---")
st.subheader("🌍 Análise por Região")

contagem_regiao = df_filtrado['regiao_normalizada'].value_counts().reindex(todas_regioes, fill_value=0)

if len(contagem_regiao) > 0:
    cols = st.columns(len(todas_regioes))
    
    for idx, (regiao, quantidade) in enumerate(contagem_regiao.items()):
        with cols[idx]:
            cor = cores_regiao_map.get(regiao, '#95a5a6')
            icone = "📍"
            if regiao == "Região 1":
                icone = "1️⃣"
            elif regiao == "Região 2":
                icone = "2️⃣"
            elif regiao == "Região 3":
                icone = "3️⃣"
            elif regiao == "Não especificada":
                icone = "❓"
            
            # Calcular percentual
            total = contagem_regiao.sum()
            percentual = (quantidade / total * 100) if total > 0 else 0
            
            st.markdown(f"""
                <div style="
                    background: linear-gradient(145deg, {cor}99, {cor});
                    color: white;
                    padding: 1.3rem;
                    border-radius: 15px;
                    text-align: center;
                    box-shadow: 0 6px 15px rgba(0,0,0,0.2);
                    margin: 10px;
                    border: 3px solid {cor}cc;
                    min-height: 160px;
                ">
                    <h2 style="margin: 0; font-size: 2.8rem; font-weight: bold; margin-bottom: 8px;">{icone}</h2>
                    <h3 style="margin: 0; font-size: 1.4rem; font-weight: bold; margin-bottom: 5px;">{regiao}</h3>
                    <h1 style="margin: 0.5rem 0 0 0; font-size: 3.0rem; font-weight: bold;">{quantidade}</h1>
                    <p style="margin: 8px 0 0 0; font-size: 1.1rem; opacity: 0.9;">({percentual:.1f}%)</p>
                </div>
            """, unsafe_allow_html=True)

# ============================================
# GRÁFICOS COM ANÁLISE POR REGIÃO
# ============================================
st.markdown("---")
st.subheader("📈 Análise Visual")

col_graf1, col_graf2 = st.columns(2)

# Gráfico 1: Distribuição por Região (Barras horizontais)
with col_graf1:
    df_regiao = contagem_regiao.reset_index()
    df_regiao.columns = ['Região', 'Quantidade']
    df_regiao = df_regiao[df_regiao['Quantidade'] > 0]
    
    if not df_regiao.empty:
        fig_regiao = px.bar(
            df_regiao,
            x='Quantidade',
            y='Região',
            orientation='h',
            title='Distribuição por Região',
            color='Região',
            color_discrete_map=cores_regiao_map,
            text='Quantidade',
            height=350
        )
        fig_regiao.update_traces(textposition='outside', textfont_size=14)
        fig_regiao.update_layout(
            title_x=0.5,
            xaxis_title='Quantidade de Assistências',
            yaxis_title=None,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_regiao, use_container_width=True)

# Gráfico 2: Distribuição por Status
with col_graf2:
    if len(contagem_status) > 0:
        df_grafico = contagem_status.reset_index()
        df_grafico.columns = ['Status', 'Quantidade']
        
        fig_pizza = px.pie(
            df_grafico,
            values='Quantidade',
            names='Status',
            title='Distribuição por Status',
            color='Status',
            color_discrete_map=cores_status,
            hole=0.4,
            height=350
        )
        fig_pizza.update_traces(textposition='inside', textinfo='percent+label', textfont_size=12)
        fig_pizza.update_layout(title_x=0.5, showlegend=False)
        st.plotly_chart(fig_pizza, use_container_width=True)

# ============================================
# GRÁFICO COMPARATIVO: STATUS POR REGIÃO (EMPILHADO)
# ============================================
st.markdown("---")
st.subheader("📊 Comparativo: Status por Região")

# Criar tabela pivô: Região x Status
df_pivot_regiao = df_filtrado.groupby(['regiao_normalizada', 'status_normalizado']).size().reset_index(name='Quantidade')
df_pivot_regiao.columns = ['Região', 'Status', 'Quantidade']

# Ordenar regiões na ordem correta
ordem_regioes = ['Região 1', 'Região 2', 'Região 3', 'Não especificada']
df_pivot_regiao['Região'] = pd.Categorical(df_pivot_regiao['Região'], categories=ordem_regioes, ordered=True)
df_pivot_regiao = df_pivot_regiao.sort_values('Região')

if len(df_pivot_regiao) > 0:
    fig_comparativo_regiao = px.bar(
        df_pivot_regiao,
        x='Região',
        y='Quantidade',
        color='Status',
        title='Distribuição de Status por Região',
        barmode='stack',
        color_discrete_map=cores_status,
        text='Quantidade',
        height=450
    )
    fig_comparativo_regiao.update_traces(textposition='inside', textfont_size=11)
    fig_comparativo_regiao.update_layout(
        title_x=0.5,
        title_font_size=20,
        xaxis_title='Região',
        yaxis_title='Quantidade de Assistências',
        hovermode='x unified',
        legend_title_text='Status',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_comparativo_regiao, use_container_width=True)

# ============================================
# GRÁFICO DE MAPA DE CALOR: REGIÃO VS STATUS
# ============================================
st.markdown("---")
st.subheader("🌡️ Mapa de Calor: Intensidade por Região e Status")

df_heatmap = df_filtrado.pivot_table(
    index='regiao_normalizada',
    columns='status_normalizado',
    aggfunc='size',
    fill_value=0
)

# Ordenar regiões
df_heatmap = df_heatmap.reindex(ordem_regioes, fill_value=0)
df_heatmap = df_heatmap.loc[:, (df_heatmap != 0).any(axis=0)]  # Remover colunas zeradas

if not df_heatmap.empty and df_heatmap.sum().sum() > 0:
    fig_heatmap = px.imshow(
        df_heatmap,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='Blues',
        title='Mapa de Calor: Região x Status',
        height=400
    )
    fig_heatmap.update_layout(
        title_x=0.5,
        xaxis_title='Status',
        yaxis_title='Região'
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

# ============================================
# GRÁFICO TEMPORAL POR REGIÃO (se houver data)
# ============================================
if col_data and 'data_convertida' in df_filtrado.columns and len(df_filtrado) > 0:
    st.markdown("---")
    st.subheader("📅 Evolução Temporal por Região")
    
    df_temporal = df_filtrado.copy()
    df_temporal['data_apenas'] = df_temporal['data_convertida'].dt.date
    
    df_evolucao_regiao = df_temporal.groupby(['data_apenas', 'regiao_normalizada']).size().reset_index(name='count')
    
    if not df_evolucao_regiao.empty and len(df_evolucao_regiao) > 5:
        # Filtrar apenas regiões 1, 2, 3 para o gráfico temporal
        df_evolucao_regiao = df_evolucao_regiao[df_evolucao_regiao['regiao_normalizada'].isin(['Região 1', 'Região 2', 'Região 3'])]
        
        if not df_evolucao_regiao.empty:
            fig_temporal_regiao = px.line(
                df_evolucao_regiao,
                x='data_apenas',
                y='count',
                color='regiao_normalizada',
                title='Evolução das Assistências por Região',
                labels={'data_apenas': 'Data', 'count': 'Quantidade', 'regiao_normalizada': 'Região'},
                color_discrete_map=cores_regiao_map,
                markers=True,
                line_shape='spline',
                height=400
            )
            fig_temporal_regiao.update_layout(
                title_x=0.5,
                xaxis_title='Data',
                yaxis_title='Quantidade de Assistências',
                hovermode='x unified'
            )
            st.plotly_chart(fig_temporal_regiao, use_container_width=True)

# ============================================
# TABELA DE DADOS
# ============================================
st.markdown("---")
st.subheader(f"📝 Dados Detalhados ({len(df_filtrado):,} registros)")

colunas_relevantes = []
for col in df_filtrado.columns:
    col_lower = str(col).lower()
    if any(palavra in col_lower for palavra in [
        'status', 'departamento', 'setor', 'data', 'cliente', 'produto', 'defeito', 
        'tecnico', 'observacao', 'observação', 'modelo', 'serie', 'número', 'telefone',
        'endereço', 'endereco', 'contato', 'razao', 'social', 'empresa', 'cliente',
        'regiao', 'região', 'regional'
    ]):
        colunas_relevantes.append(col)

colunas_exibir = [col for col in (colunas_relevantes or df_filtrado.columns.tolist()) 
                  if col not in ['status_normalizado', 'departamento_normalizado', 'regiao_normalizada', 'data_convertida']]

colunas_default = colunas_exibir[:min(8, len(colunas_exibir))]

# Priorizar Região e Status
if col_regiao and col_regiao in colunas_exibir:
    colunas_default = [col_regiao] + [c for c in colunas_default if c != col_regiao]
if col_status and col_status in colunas_exibir:
    colunas_default = [col_status] + [c for c in colunas_default if c != col_status]

colunas_selecionadas = st.multiselect(
    "Selecione as colunas para exibir:",
    options=colunas_exibir,
    default=colunas_default[:8],
    help="Escolha as colunas mais importantes para sua análise"
)

if colunas_selecionadas:
    df_exibir = df_filtrado[colunas_selecionadas].copy()
else:
    df_exibir = df_filtrado[colunas_exibir[:8]].copy()

# Estilo condicional para status
def destacar_status(val):
    if isinstance(val, str):
        val_stripped = val.strip()
        cor = '#95a5a6'
        for chave, valor in cores_status.items():
            if chave.lower() in val_stripped.lower() or val_stripped.lower() in chave.lower():
                cor = valor
                break
        return f'background-color: {cor}; color: white; font-weight: bold;'
    return ''

# Estilo condicional para região (cores suaves)
def destacar_regiao(val):
    if isinstance(val, str):
        cores_suaves = {
            'Região 1': '#e3f2fd',
            'Região 2': '#e8f5e9',
            'Região 3': '#ffebee',
            'Não especificada': '#f5f5f5'
        }
        return f'background-color: {cores_suaves.get(val, "#ffffff")}; font-weight: bold;'
    return ''

# Aplicar estilos
if col_status in df_exibir.columns:
    df_estilo = df_exibir.style.applymap(destacar_status, subset=[col_status])
    if col_regiao and col_regiao in df_exibir.columns:
        df_estilo = df_estilo.applymap(destacar_regiao, subset=[col_regiao])
    st.dataframe(df_estilo, use_container_width=True, height=400)
else:
    st.dataframe(df_exibir, use_container_width=True, height=400)

# ============================================
# DOWNLOAD DOS DADOS
# ============================================
st.markdown("---")
st.subheader("💾 Exportar Dados")

csv = df_filtrado.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 Download CSV (com acentos)",
    data=csv,
    file_name=f"assistencia_regioes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
    use_container_width=True
)

# ============================================
# ATUALIZAÇÃO AUTOMÁTICA
# ============================================
st.markdown("---")
st.caption(f"🔄 Atualização automática a cada 15 segundos | Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

st.components.v1.html(
    """
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 15000);
    </script>
    """,
    height=0
)

# Informações na sidebar
st.sidebar.markdown("---")
st.sidebar.success(f"✅ {len(df_filtrado):,} registros filtrados")
st.sidebar.info(f"""
📊 **Resumo dos Filtros:**
- Regiões: {', '.join(regioes_selecionadas) if regioes_selecionadas else 'Nenhuma'}
- Status: {len(status_selecionados)} selecionados
- {"Departamento: " + str(len(dept_selecionados)) + " selecionados" if col_departamento and dept_selecionados else "Sem filtro de departamento"}
- Período: {periodo}
""")