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
st.markdown("**Acompanhamento em tempo real das assistências**")
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
            # Tentar diferentes codificações
            for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file, encoding=encoding)
                    break
                except:
                    continue
        else:
            df = pd.read_excel(file)
        
        # Remover colunas vazias
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

# Identificar coluna de status (case-insensitive)
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
    if any(keyword in col_lower for keyword in ['data', 'dt_', 'abertura', 'entrada', 'registro', 'entrada']):
        col_data = col
        break

# ============================================
# PROCESSAR STATUS - IDENTIFICAR TODOS OS STATUS ÚNICOS
# ============================================
# Normalizar status (tratar valores nulos e padronizar)
df['status_normalizado'] = df[col_status].fillna('').astype(str).str.strip()

# Identificar todos os status únicos da planilha (remover vazios)
todos_status = df['status_normalizado'].unique()
todos_status = sorted([s for s in todos_status if s and s != 'nan' and s != ''])

# Identificar todos os departamentos únicos (se existir)
todos_departamentos = []
if col_departamento:
    df['departamento_normalizado'] = df[col_departamento].fillna('Não especificado').astype(str).str.strip()
    todos_departamentos = df['departamento_normalizado'].unique()
    todos_departamentos = sorted([d for d in todos_departamentos if d and d != 'nan' and d != ''])
else:
    df['departamento_normalizado'] = 'Todos'

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros")

# ============================================
# FILTRO DE DEPARTAMENTO
# ============================================
if col_departamento:
    st.sidebar.subheader("🏢 Departamento")
    
    # Checkbox para selecionar todos
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
    dept_selecionados = todos_departamentos  # Todos (sem filtro)
    st.sidebar.info("⚠️ Coluna de departamento não identificada")

# ============================================
# FILTRO DE STATUS
# ============================================
st.sidebar.subheader("📊 Status")

# Checkbox para selecionar todos
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

# ============================================
# FILTRO DE PERÍODO
# ============================================
if col_data:
    st.sidebar.subheader("📅 Período")
    periodo = st.sidebar.selectbox(
        "Período",
        ["Todo o período", "Últimos 7 dias", "Últimos 15 dias", "Últimos 30 dias", "Últimos 90 dias"]
    )
else:
    periodo = "Todo o período"

# ============================================
# FILTRO DE BUSCA LIVRE
# ============================================
st.sidebar.subheader("🔍 Busca")
busca = st.sidebar.text_input("Buscar em qualquer campo", placeholder="Digite para filtrar...")

# ============================================
# APLICAR FILTROS
# ============================================

# Filtro de departamento
if col_departamento and dept_selecionados:
    df_filtrado = df[df['departamento_normalizado'].isin(dept_selecionados)].copy()
else:
    df_filtrado = df.copy()

# Filtro de status
if status_selecionados:
    df_filtrado = df_filtrado[df_filtrado['status_normalizado'].isin(status_selecionados)].copy()

# Filtro de período (com tratamento robusto de data)
if col_data and periodo != "Todo o período":
    # Converter coluna para datetime com tratamento robusto
    try:
        # Tentar converter com diferentes formatos
        df_filtrado['data_convertida'] = pd.to_datetime(
            df_filtrado[col_data], 
            errors='coerce',
            dayfirst=True  # Assume formato dia/mês/ano (comum no Brasil)
        )
        
        # Remover valores inválidos
        df_filtrado = df_filtrado.dropna(subset=['data_convertida'])
        
        # Calcular período
        dias_map = {
            "Últimos 7 dias": 7,
            "Últimos 15 dias": 15,
            "Últimos 30 dias": 30,
            "Últimos 90 dias": 90
        }
        dias_qtd = dias_map[periodo]
        data_limite = datetime.now() - timedelta(days=dias_qtd)
        
        # Filtrar por data
        df_filtrado = df_filtrado[df_filtrado['data_convertida'] >= data_limite]
        
    except Exception as e:
        st.sidebar.warning(f"⚠️ Não foi possível filtrar por data")

# Filtro de busca livre
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

# Contar registros por status no conjunto filtrado
contagem_status = df_filtrado['status_normalizado'].value_counts().sort_index()

# Definir cores para cada status (padrão brasileiro de assistência técnica)
cores_status = {
    'Aberta': '#27ae60',      # Verde escuro
    'Aberto': '#27ae60',
    'Pendente': '#f39c12',    # Laranja
    'Aguardando': '#f39800',
    'Em Análise': '#3498db',  # Azul
    'Análise': '#3498db',
    'Recusada': '#e74c3c',    # Vermelho
    'Recusado': '#e74c3c',
    'Negada': '#c0392b',
    'Cancelada': '#95a5a6',   # Cinza
    'Fechada': '#7f8c8d',
    'Concluída': '#16a085',   # Verde azulado
    'Concluida': '#16a085',
    'Nova': '#3498db',
    'Ativa': '#27ae60',
    'Em Andamento': '#f1c40f',
    'Reparo': '#9b59b6',      # Roxo
    'Teste': '#34495e',       # Azul escuro
}

# Criar cards para cada status
if len(contagem_status) > 0:
    # Calcular número de colunas (máximo 6 por linha)
    num_status = len(contagem_status)
    cols_por_linha = min(6, num_status if num_status > 0 else 1)
    
    # Criar linhas conforme necessário
    for i in range(0, num_status, cols_por_linha):
        cols = st.columns(cols_por_linha)
        for j, (status, quantidade) in enumerate(contagem_status.iloc[i:i+cols_por_linha].items()):
            with cols[j]:
                # Definir cor baseada no nome do status (case-insensitive)
                cor = '#95a5a6'  # Cinza padrão
                for chave, valor in cores_status.items():
                    if chave.lower() in status.lower() or status.lower() in chave.lower():
                        cor = valor
                        break
                
                # Card estilizado com HTML
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
                        <h1 style="margin: 0.6rem 0 0 0; font-size: 2.8rem; font-weight: bold; font-family: 'Arial', sans-serif;">{quantidade}</h1>
                    </div>
                """, unsafe_allow_html=True)
else:
    st.warning("⚠️ Nenhum registro encontrado com os filtros selecionados. Tente ajustar os filtros.")

# ============================================
# MÉTRICAS ADICIONAIS - CARDS POR DEPARTAMENTO
# ============================================
if col_departamento and len(df_filtrado) > 0:
    st.markdown("---")
    st.subheader("🏢 Resumo por Departamento")
    
    # Contar registros por departamento
    contagem_dept = df_filtrado['departamento_normalizado'].value_counts().sort_index()
    
    # Cores para departamentos (cíclicas)
    cores_base = ['#3498db', '#9b59b6', '#1abc9c', '#f1c40f', '#e74c3c', '#34495e', '#16a085', '#2980b9']
    
    if len(contagem_dept) > 0:
        num_dept = len(contagem_dept)
        cols_por_linha = min(5, num_dept if num_dept > 0 else 1)
        
        for i in range(0, num_dept, cols_por_linha):
            cols = st.columns(cols_por_linha)
            for j, (dept, quantidade) in enumerate(contagem_dept.iloc[i:i+cols_por_linha].items()):
                with cols[j]:
                    # Definir cor cíclica
                    cor = cores_base[j % len(cores_base)]
                    
                    st.markdown(f"""
                        <div style="
                            background: linear-gradient(145deg, {cor}99, {cor});
                            color: white;
                            padding: 1rem;
                            border-radius: 10px;
                            text-align: center;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                            margin: 8px;
                            border: 2px solid {cor}cc;
                        ">
                            <h4 style="margin: 0; font-size: 0.9rem; font-weight: bold;">{dept}</h4>
                            <h2 style="margin: 0.5rem 0 0 0; font-size: 2.2rem; font-weight: bold;">{quantidade}</h2>
                        </div>
                    """, unsafe_allow_html=True)

# ============================================
# GRÁFICOS
# ============================================
if len(df_filtrado) > 0:
    st.markdown("---")
    st.subheader("📈 Análise Visual")
    
    # Gráfico 1: Distribuição por Status
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
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
                hole=0.4
            )
            fig_pizza.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hoverinfo='label+value+percent',
                textfont_size=14
            )
            fig_pizza.update_layout(
                title_x=0.5,
                title_font_size=20,
                showlegend=True,
                height=400
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
    
    # Gráfico 2: Distribuição por Departamento
    with col_graf2:
        if col_departamento and len(df_filtrado['departamento_normalizado'].unique()) > 1:
            contagem_dept_graf = df_filtrado['departamento_normalizado'].value_counts().reset_index()
            contagem_dept_graf.columns = ['Departamento', 'Quantidade']
            
            # Cores cíclicas para departamentos
            cores_dept = [cores_base[i % len(cores_base)] for i in range(len(contagem_dept_graf))]
            
            fig_dept = px.pie(
                contagem_dept_graf,
                values='Quantidade',
                names='Departamento',
                title='Distribuição por Departamento',
                hole=0.4,
                color_discrete_sequence=cores_dept
            )
            fig_dept.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hoverinfo='label+value+percent',
                textfont_size=14
            )
            fig_dept.update_layout(
                title_x=0.5,
                title_font_size=20,
                showlegend=True,
                height=400
            )
            st.plotly_chart(fig_dept, use_container_width=True)
        else:
            # Se não houver departamento, mostrar gráfico de barras de status
            if len(contagem_status) > 0:
                df_barras = contagem_status.reset_index()
                df_barras.columns = ['Status', 'Quantidade']
                
                fig_barras = px.bar(
                    df_barras,
                    x='Quantidade',
                    y='Status',
                    orientation='h',
                    title='Ranking por Status',
                    color='Status',
                    color_discrete_map=cores_status,
                    text='Quantidade'
                )
                fig_barras.update_traces(
                    textposition='outside',
                    textfont_size=12
                )
                fig_barras.update_layout(
                    title_x=0.5,
                    title_font_size=20,
                    xaxis_title='Quantidade',
                    yaxis_title='Status',
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig_barras, use_container_width=True)

# ============================================
# GRÁFICO DE BARRAS COMPARATIVO (Status x Departamento)
# ============================================
if col_departamento and len(df_filtrado) > 0 and len(df_filtrado['departamento_normalizado'].unique()) > 1:
    st.markdown("---")
    st.subheader("📊 Comparativo: Status por Departamento")
    
    # Criar tabela pivô: Departamento x Status
    df_pivot = df_filtrado.groupby(['departamento_normalizado', 'status_normalizado']).size().reset_index(name='Quantidade')
    df_pivot.columns = ['Departamento', 'Status', 'Quantidade']
    
    if len(df_pivot) > 0:
        fig_comparativo = px.bar(
            df_pivot,
            x='Departamento',
            y='Quantidade',
            color='Status',
            title='Status por Departamento',
            barmode='group',
            color_discrete_map=cores_status,
            text='Quantidade'
        )
        fig_comparativo.update_traces(textposition='outside', textfont_size=10)
        fig_comparativo.update_layout(
            title_x=0.5,
            title_font_size=20,
            xaxis_title='Departamento',
            yaxis_title='Quantidade',
            height=500,
            hovermode='x unified'
        )
        st.plotly_chart(fig_comparativo, use_container_width=True)

# ============================================
# GRÁFICO TEMPORAL (se houver data)
# ============================================
if col_data and 'data_convertida' in df_filtrado.columns and len(df_filtrado) > 0:
    # Agrupar por data e status
    df_temporal = df_filtrado.copy()
    df_temporal['data_apenas'] = df_temporal['data_convertida'].dt.date
    
    # Contar por data e status
    df_evolucao = df_temporal.groupby(['data_apenas', 'status_normalizado']).size().reset_index(name='count')
    
    if not df_evolucao.empty and len(df_evolucao) > 1:
        st.markdown("---")
        st.subheader("📅 Evolução Temporal")
        
        fig_temporal = px.line(
            df_evolucao,
            x='data_apenas',
            y='count',
            color='status_normalizado',
            title='Evolução das Assistências por Dia',
            labels={
                'data_apenas': 'Data',
                'count': 'Quantidade',
                'status_normalizado': 'Status'
            },
            color_discrete_map=cores_status,
            markers=True,
            line_shape='spline'
        )
        fig_temporal.update_layout(
            title_x=0.5,
            title_font_size=20,
            xaxis_title='Data',
            yaxis_title='Quantidade de Assistências',
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_temporal, use_container_width=True)

# ============================================
# TABELA DE DADOS
# ============================================
st.markdown("---")
st.subheader(f"📝 Dados Detalhados ({len(df_filtrado)} registros)")

# Selecionar colunas relevantes para exibir
colunas_relevantes = []
for col in df_filtrado.columns:
    col_lower = str(col).lower()
    # Adicionamos 'razao' e 'social' para identificar a coluna de razão social
    if any(palavra in col_lower for palavra in [
        'status', 'departamento', 'setor', 'data', 'cliente', 'produto', 'defeito', 
        'tecnico', 'observacao', 'observação', 'modelo', 'serie', 'número', 'telefone',
        'endereço', 'endereco', 'contato', 'razao', 'social', 'empresa', 'cliente'
    ]):
        colunas_relevantes.append(col)

# Remover colunas de processamento interno
colunas_exibir = [col for col in (colunas_relevantes or df_filtrado.columns.tolist()) 
                  if col not in ['status_normalizado', 'departamento_normalizado', 'data_convertida']]

# Limitar a 8 colunas por padrão para não sobrecarregar
colunas_default = colunas_exibir[:min(8, len(colunas_exibir))]

# Garantir que "Razão Social" seja incluída por padrão se existir
if 'Razão Social' in colunas_exibir:
    colunas_default = ['Razão Social'] + [c for c in colunas_default if c != 'Razão Social']
elif 'Razao Social' in colunas_exibir:
    colunas_default = ['Razao Social'] + [c for c in colunas_default if c != 'Razao Social']
elif 'razão social' in [c.lower() for c in colunas_exibir]:
    colunas_default = [c for c in colunas_exibir if c.lower() == 'razão social'] + [c for c in colunas_default if c.lower() != 'razão social']

colunas_selecionadas = st.multiselect(
    "Selecione as colunas para exibir:",
    options=colunas_exibir,
    default=colunas_default,
    help="Escolha as colunas mais importantes para sua análise"
)

# Exibir tabela
if colunas_selecionadas:
    df_exibir = df_filtrado[colunas_selecionadas].copy()
else:
    df_exibir = df_filtrado[colunas_exibir].copy()

# Estilo condicional para status e departamento
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

# Exibir tabela com estilo
if col_status in df_exibir.columns:
    st.dataframe(
        df_exibir.style.applymap(destacar_status, subset=[col_status]),
        use_container_width=True,
        height=400
    )
else:
    st.dataframe(
        df_exibir,
        use_container_width=True,
        height=400
    )
# ============================================
# DOWNLOAD DOS DADOS (apenas CSV - sem dependência)
# ============================================
st.markdown("---")
st.subheader("💾 Exportar Dados")

csv = df_filtrado.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 Download CSV (com acentos)",
    data=csv,
    file_name=f"assistencia_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
    use_container_width=True
)

# ============================================
# ATUALIZAÇÃO AUTOMÁTICA
# ============================================
st.markdown("---")
st.caption(f"🔄 Atualização automática a cada 15 segundos | Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# Recarregar página automaticamente
st.components.v1.html(
    """
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 15000); // 15 segundos
    </script>
    """,
    height=0
)

# Informações na sidebar
st.sidebar.markdown("---")
st.sidebar.success(f"✅ {len(df_filtrado)} registros filtrados")
st.sidebar.info(f"""
📊 **Resumo dos Filtros:**
- Status: {len(status_selecionados) if status_selecionados else 0} selecionados
- {"Departamento: " + str(len(dept_selecionados)) + " selecionados" if col_departamento and dept_selecionados else "Sem filtro de departamento"}
- Período: {periodo}
""")