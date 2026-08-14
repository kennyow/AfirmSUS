# python -m streamlit run main2.py

import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import json
import os

# Configuração da Página
st.set_page_config(
    layout="wide", 
    page_title="AfirmaSUSJP - Dashboard",
    page_icon="🏥"
)

# Estilização CSS personalizada
# Estilização CSS personalizada
st.markdown("""
    <style>
        h1, h2, h3 { color: #4C2059 !important; }
        hr { border-top: 2px solid #FF5364 !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. BARRA LATERAL (Logo + Marca)
# ---------------------------------------------------------
caminho_logo = "logo3.jpg"
if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, width="stretch")

st.sidebar.title("AfirmaSUS-JP")
st.sidebar.caption("Programa Nacional de Apoio à Permanência, Diversidade e Visibilidade para Discentes da Área da Saúde")
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 2. BASE DE DADOS (Leitura com DEBUG extensivo)
# ---------------------------------------------------------
caminho_json = "dados_locais.json"

if not os.path.exists(caminho_json):
    st.error(f"Arquivo '{caminho_json}' não encontrado na pasta do projeto.")
    st.stop()

df_locais = pd.DataFrame()

try:
    with open(caminho_json, "r", encoding="utf-8") as f:
        dados = json.load(f)

    
    if isinstance(dados, list) and len(dados) > 0:
    
        df_locais = pd.DataFrame(dados)
    
    
    # Se o DataFrame estiver vazio, tenta criar manualmente
    if df_locais.empty and isinstance(dados, list) and len(dados) > 0:
        st.sidebar.warning("DataFrame vazio! Criando manualmente...")
        df_locais = pd.DataFrame.from_dict(dados)

except json.JSONDecodeError as e:
    st.error(f"⚠️ Erro ao processar o arquivo JSON: {e}")
    st.stop()

except Exception as e:
    st.error(f"⚠️ Erro ao carregar a base de dados: {e}")
    st.stop()

# Verifica se o DataFrame está vazio
if df_locais.empty:
    st.error("⚠️ O DataFrame está vazio! Verifique o arquivo JSON.")
    st.stop()

# LIMPEZA dos nomes das colunas
df_locais.columns = df_locais.columns.astype(str).str.strip().str.lower()


# ---------------------------------------------------------
# 3. VERIFICAÇÃO E CORREÇÃO DAS COLUNAS
# ---------------------------------------------------------
# Lista de colunas que precisamos
colunas_necessarias = ['distrito', 'categoria', 'nome', 'lat', 'lon', 'status', 'cor', 'icone', 'foto', 'descricao']

# Verifica quais colunas existem
colunas_existentes = list(df_locais.columns)


# Tenta encontrar colunas mesmo com nomes diferentes
for col_necessaria in colunas_necessarias:
    if col_necessaria not in colunas_existentes:
        # Procura por colunas similares (case insensitive)
        for col_existente in colunas_existentes:
            if col_necessaria.lower() in col_existente.lower() or col_existente.lower() in col_necessaria.lower():
                st.sidebar.warning(f"⚠️ Coluna '{col_necessaria}' não encontrada, mas encontrei '{col_existente}'")
                # Renomeia a coluna encontrada
                df_locais.rename(columns={col_existente: col_necessaria}, inplace=True)
                break

# Atualiza lista de colunas após renomeação
colunas_existentes = list(df_locais.columns)


# Verifica se as colunas essenciais existem
colunas_essenciais = ['distrito', 'categoria', 'nome', 'lat', 'lon']
faltantes = [col for col in colunas_essenciais if col not in colunas_existentes]

if faltantes:
    st.error(f"❌ Colunas essenciais ainda faltando: {faltantes}")
    st.error(f"Colunas disponíveis: {colunas_existentes}")
    
    # Tenta uma abordagem alternativa: criar colunas vazias
    for col in faltantes:
        st.warning(f"Criando coluna '{col}' vazia como fallback...")
        df_locais[col] = None
    
    st.info("⚠️ Colunas foram criadas artificialmente. O mapa pode não funcionar corretamente.")

# Converte lat e lon para float (se necessário)
if 'lat' in df_locais.columns:
    df_locais['lat'] = pd.to_numeric(df_locais['lat'], errors='coerce')
if 'lon' in df_locais.columns:
    df_locais['lon'] = pd.to_numeric(df_locais['lon'], errors='coerce')

# Remove linhas com lat/lon inválidas
df_locais = df_locais.dropna(subset=['lat', 'lon'])


# ---------------------------------------------------------
# 4. FILTROS DA SIDEBAR (COM VALIDAÇÃO)
# ---------------------------------------------------------
try:
    # Verifica se a coluna 'distrito' existe antes de usar
    if 'distrito' in df_locais.columns and not df_locais['distrito'].isna().all():
        distritos_disponiveis = ["Todos"] + sorted(list(df_locais["distrito"].dropna().unique()))
        distrito_selecionado = st.sidebar.selectbox("Filtrar por Distrito Sanitário", distritos_disponiveis)
    else:
        st.sidebar.warning("⚠️ Coluna 'distrito' não encontrada ou vazia")
        distrito_selecionado = "Todos"
        distritos_disponiveis = ["Todos"]

    if 'categoria' in df_locais.columns and not df_locais['categoria'].isna().all():
        categorias_disponiveis = ["Todas"] + sorted(
            list(df_locais["categoria"].dropna().unique())
        )

        categoria_selecionada = st.sidebar.radio(
            "Filtrar por Categoria",
            categorias_disponiveis
        )

    else:
        st.sidebar.warning("⚠️ Coluna 'categoria' não encontrada ou vazia")
        categoria_selecionada = "Todas"
        categorias_disponiveis = ["Todas"]

except Exception as e:
    st.sidebar.error(f"❌ Erro nos filtros: {e}")
    distrito_selecionado = "Todos"
    categoria_selecionada = "Todas"
    distritos_disponiveis = ["Todos"]
    categorias_disponiveis = ["Todas"]

# Aplicando Filtros
df_filtrado = df_locais.copy()

if distrito_selecionado != "Todos" and 'distrito' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["distrito"] == distrito_selecionado]

if categoria_selecionada != "Todas" and 'categoria' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria_selecionada]

# ---------------------------------------------------------
# 5. ÁREA PRINCIPAL (Mapa + Detalhes)
# ---------------------------------------------------------
st.title("Mapeamento Participativo do SUS - João Pessoa")

# Verifica se há dados para mostrar no mapa
if df_filtrado.empty:
    st.warning("⚠️ Nenhum dado disponível para exibir no mapa.")
    st.info("Verifique se o arquivo JSON tem dados válidos com coordenadas (lat/lon).")
    st.stop()

col_mapa, col_detalhes = st.columns([2.2, 1])

with col_mapa:
    st.subheader("📍 Territorialização")
    st.info(f"Mostrando {len(df_filtrado)} local(is)")
    
    mapa_jp = folium.Map(location=[-7.135080186191312, -34.85575440327488], zoom_start=16, tiles="CartoDB voyager")
    
    for idx, row in df_filtrado.iterrows():
        # Verifica se lat/lon são válidos
        if pd.isna(row["lat"]) or pd.isna(row["lon"]):
            continue
            
        icone_nome = row.get("icone", "hospital")
        if pd.isna(icone_nome):
            icone_nome = "hospital"
            
        # Pega o nome do local (fallback se não existir)
        nome_local = row.get("nome", f"Local {idx}")
        if pd.isna(nome_local):
            nome_local = f"Local {idx}"
            
        categoria_local = row.get("categoria", "Não especificada")
        if pd.isna(categoria_local):
            categoria_local = "Não especificada"
            
        cor_local = row.get("cor", "purple")
        if pd.isna(cor_local):
            cor_local = "purple"
            
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=nome_local,
            tooltip=f"{nome_local} ({categoria_local})",
            icon=folium.Icon(
                color=cor_local, 
                icon=icone_nome, 
                prefix="fa"
            )
        ).add_to(mapa_jp)
    
    map_data = st_folium(mapa_jp, width="100%", height=480, key="mapa_folium")

with col_detalhes:
    st.subheader("🖼️ Detalhes do Local")
    
    ponto_encontrado = None
    
    if map_data and map_data.get("last_object_clicked"):
        lat_clicada = map_data["last_object_clicked"]["lat"]
        lon_clicada = map_data["last_object_clicked"]["lng"]
        
        # Verifica se há dados para comparar
        if not df_filtrado.empty:
            match = df_filtrado[
                (df_filtrado["lat"].round(3) == round(lat_clicada, 3)) & 
                (df_filtrado["lon"].round(3) == round(lon_clicada, 3))
            ]
            if not match.empty:
                ponto_encontrado = match.iloc[0]

    if ponto_encontrado is not None:
        if "foto" in ponto_encontrado and pd.notna(ponto_encontrado["foto"]):
            st.image(ponto_encontrado["foto"], use_container_width=True, caption=ponto_encontrado.get("nome", "Local"))
        st.markdown(f"### {ponto_encontrado.get('nome', 'Local sem nome')}")
        st.markdown(f"**Categoria:** `{ponto_encontrado.get('categoria', 'Não especificada')}`")
        st.markdown(f"**Distrito:** `{ponto_encontrado.get('distrito', 'Não especificado')}`")
        st.markdown(f"**Status de Infraestrutura:** `{ponto_encontrado.get('status', 'Não especificado')}`")
        if "descricao" in ponto_encontrado and pd.notna(ponto_encontrado["descricao"]):
            st.info(ponto_encontrado["descricao"])
    else:
        st.warning("👈 Clique em qualquer marcador no mapa para abrir as fotos, diagnósticos e descrições do local.")



# ---------------------------------------------------------
# 6. VÍDEOS
# ---------------------------------------------------------

st.divider()
st.subheader("🎥 Vídeos")

v_col1, v_col2, v_col3 = st.columns(3)

with v_col1:
    st.markdown("### Vídeo 1")
    
    st.video("https://www.youtube.com/watch?v=KWmfR6VExYs")
    
    st.markdown(
        "**Título do vídeo:** Apresentação do AfirmaSUS (UEMA - Caxias, Maranhão)"
    )
    
    st.write(
        "Vídeo de apresentação do projeto AfirmaSUS (UEMA - Caxias, Maranhão), "
        "seus objetivos e sua proposta de mapeamento participativo."
    )


with v_col2:
    st.markdown("### Vídeo 2")
    
    st.video("https://www.youtube.com/watch?v=SJQncTxsZL4")
    
    st.markdown(
        "**Título do vídeo:** IMUNIZAÇÃO NA SAÚDE INDÍGENA"
    )
    
    st.write(
        "Vídeo relacionado à territorialização da saúde e "
        "à identificação dos equipamentos e serviços públicos."
    )


with v_col3:
    st.markdown("### Vídeo 3")
    
    st.video("https://www.youtube.com/watch?v=6aHxgKfq01U")
    
    st.markdown(
        "**Título do vídeo:** SEMINÁRIO AFIRMASUS UNEMAT"
    )
    
    st.write(
        "Conteúdo relacionado às ações do programa, "
        "à permanência estudantil e à diversidade na área da saúde."
    )


# ---------------------------------------------------------
# 7. LINHA DO TEMPO
# ---------------------------------------------------------

st.divider()
st.subheader("🕐 Linha do Tempo AfirmaSUS")

st.iframe(
    "https://www.chronoflotimeline.com/timeline/shared/32199/AfirmaSUS/",
    height=800
)


# ---------------------------------------------------------
# 8. QUADRO DE GRÁFICOS (Estatísticas Inferiores)
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Resumo de Indicadores")

if not df_filtrado.empty:
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        st.markdown("**Pontos Mapeados por Distrito**")
        if 'distrito' in df_filtrado.columns and not df_filtrado['distrito'].isna().all():
            st.bar_chart(df_filtrado["distrito"].value_counts())
        else:
            st.info("Sem dados de distrito")

    with g_col2:
        st.markdown("**Distribuição por Status da Infraestrutura**")
        if 'status' in df_filtrado.columns and not df_filtrado['status'].isna().all():
            st.bar_chart(df_filtrado["status"].value_counts())
        else:
            st.info("Sem dados de status")
else:
    st.info("Nenhum local encontrado para os filtros selecionados.")