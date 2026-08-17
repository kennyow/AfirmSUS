# python -m streamlit run main2.py

import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import json
import os
import re
import streamlit as st



# Função auxiliar para tratar URLs do Google Drive
def converter_link_drive(url):
    if not url or not isinstance(url, str):
        return url
    padrao_drive = r'(?:file/d/|id=)([\w-]+)'
    match = re.search(padrao_drive, url)
    if match:
        file_id = match.group(1)
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url

# Configuração da Página
st.set_page_config(
    layout="wide", 
    page_title="AfirmaSUSJP - Dashboard",
    page_icon="🏥"
)

# Importação da Estilização CSS personalizada

# Função para carregar o arquivo CSS externo
def carregar_css(caminho_arquivo):
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Chama a função
carregar_css("style.css")

# ---------------------------------------------------------
# 1. BARRA LATERAL (Logo + Marca)
# ---------------------------------------------------------
caminho_logo = "logo3.jpg"
if os.path.exists(caminho_logo):
    st.sidebar.image(caminho_logo, width="content", )

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
# 4. FILTROS DA SIDEBAR (CÍRCULOS COLORIDOS COM ÍCONES)
# ---------------------------------------------------------

# Inicializa o estado da categoria selecionada caso não exista
if "categoria_selecionada" not in st.session_state:
    st.session_state["categoria_selecionada"] = "Todas"

# Mapeamento completo extraído dos dados do JSON (Cor, Ícone FontAwesome e Emoji fallback)
MAPA_CATEGORIAS = {
    "Esporte e Lazer": {"cor": "#FF8C00", "fa": "fa-running", "emoji": "🏃"},      # orange
    "Saúde":           {"cor": "#28A745", "fa": "fa-heart-pulse", "emoji": "🩺"},  # green
    "Educação":        {"cor": "#6f42c1", "fa": "fa-user-graduate", "emoji": "🎓"},# purple
    "Religião":        {"cor": "#17A2B8", "fa": "fa-hands-praying", "emoji": "🙏"},# lightblue
    "Cultura":         {"cor": "#D1C7A5", "fa": "fa-landmark", "emoji": "🏛️"},     # beige
    "Comércio":        {"cor": "#DC3545", "fa": "fa-cart-shopping", "emoji": "🛒"} # red
}

# 1. Filtro de Distrito Sanitário
if 'distrito' in df_locais.columns and not df_locais['distrito'].isna().all():
    distritos_disponiveis = ["Todos"] + sorted(list(df_locais["distrito"].dropna().unique()))
    distrito_selecionado = st.sidebar.selectbox("Filtrar por Distrito Sanitário", distritos_disponiveis)
else:
    distrito_selecionado = "Todos"

st.sidebar.markdown("### Filtrar por Categoria")

# Botão para limpar o filtro
if st.sidebar.button("✨ Exibir Todas as Categorias", width='stretch'):
    st.session_state["categoria_selecionada"] = "Todas"

st.sidebar.markdown("---")

# Renderização dos Ícones em Círculos Coloridos em Grade (2 Colunas)
cols_cat = st.sidebar.columns(2)

categorias_existentes = sorted(list(df_locais["categoria"].dropna().unique())) if 'categoria' in df_locais.columns else []

for idx, cat in enumerate(categorias_existentes):
    info = MAPA_CATEGORIAS.get(cat, {"cor": "#6c757d", "emoji": "📌"})
    col = cols_cat[idx % 2]
    
    with col:
        # Círculo colorido com o ícone dentro
        st.markdown(
            f'''
            <div style="text-align: center; margin-bottom: 5px;">
                <div class="circle-filter-btn" style="background-color: {info['cor']};">
                    <span>{info['emoji']}</span>
                </div>
            </div>
            ''', 
            unsafe_allow_html=True
        )
        
        # Botão de ação do filtro
        is_selected = (st.session_state["categoria_selecionada"] == cat)
        label_btn = f"✓ {cat}" if is_selected else cat
        
        if st.button(label_btn, key=f"btn_cat_{cat}", width='stretch'):
            st.session_state["categoria_selecionada"] = cat
            st.rerun()

# Categoria ativa atual
categoria_selecionada = st.session_state["categoria_selecionada"]

# Indicador visual de qual categoria está ativa
if categoria_selecionada != "Todas":
    st.sidebar.info(f"Filtro ativo: **{categoria_selecionada}**")

# Aplicando os Filtros no DataFrame
df_filtrado = df_locais.copy()

if distrito_selecionado != "Todos" and 'distrito' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["distrito"] == distrito_selecionado]

if categoria_selecionada != "Todas" and 'categoria' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria_selecionada]

# ---------------------------------------------------------
# 5. ÁREA PRINCIPAL (Mapa + Detalhes)
# ---------------------------------------------------------
st.title("Mapeamento Participativo do SUS - João Pessoa")
# BARRA DE NAVEGAÇÃO SUPERIOR (#F2EAD5)
st.markdown("""
    <div class="top-nav-bar">
        <a class="top-nav-btn" href="#territorio">📍 Território</a>
        <a class="top-nav-btn" href="#videos">🎥 Vídeos</a>
        <a class="top-nav-btn" href="#linha-do-tempo">🕐 Linha do Tempo</a>
        <a class="top-nav-btn" href="#relatorios">📊 Relatórios</a>
        <a class="top-nav-btn" href="#informacoes">ℹ️ Informações</a>
    </div>
""", unsafe_allow_html=True)



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
        if ponto_encontrado is not None:
            if "foto" in ponto_encontrado and pd.notna(ponto_encontrado["foto"]):
                # Converte o link do Drive antes de passar para o st.image
                foto_url = converter_link_drive(ponto_encontrado["foto"])
                st.image(foto_url, width='stretch', caption=ponto_encontrado.get("nome", "Local"))
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
st.markdown('<div id="videos"></div>', unsafe_allow_html=True) # Âncora de Vídeos

v_col1, v_col2, v_col3 = st.columns(3)

with v_col1:
    st.markdown("### Vídeo 1")
    
    st.video("https://youtu.be/dOvOjLi99WE")
    
    st.markdown(
        "**Título do vídeo:** São Rafael: Memória, Identidade e Território"
    )
    
    st.write(
        "Vídeo de apresentação da comunidade São Rafael em João Pessoa, "
        "a fim de mostrar a importância da preservação da memória e da identidade local."
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
# 7. LINHA DO TEMPO HORIZONTAL (VIA JSON COM DRIVE SLIDESHOW)
# ---------------------------------------------------------
st.divider()
st.markdown('<div id="linha-do-tempo"></div>', unsafe_allow_html=True)
st.subheader("🕐 Linha do Tempo - Programa AfirmaSUS")

# CSS para animação do carrossel/slideshow automático dentro do card
st.markdown("""
<style>
.timeline-slider {
    position: relative;
    width: 100%;
    height: 180px;
    overflow: hidden;
    border-radius: 8px;
}
.timeline-slider img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    animation: fadeSlider 12s infinite;
}
@keyframes fadeSlider {
    0% { opacity: 0; }
    10% { opacity: 1; }
    40% { opacity: 1; }
    50% { opacity: 0; }
    100% { opacity: 0; }
}
</style>
""", unsafe_allow_html=True)

# Carrega os dados do arquivo JSON externo
try:
    with open("timeline.json", "r", encoding="utf-8") as f:
        eventos_timeline = json.load(f)
except Exception as e:
    st.error(f"Erro ao carregar timeline.json: {e}")
    eventos_timeline = []

# Construção do HTML em linha única
cards_html = []
for ev in eventos_timeline:
    # Trata lista de fotos ou fallback para foto única
    lista_fotos_raw = ev.get("fotos", [])
    if not lista_fotos_raw and ev.get("foto"):
        lista_fotos_raw = [ev["foto"]]
    
    # Converte links do Drive
    fotos_convertidas = [converter_link_drive(url) for url in lista_fotos_raw]
    
    # Gera a tag da imagem/carrossel
    if len(fotos_convertidas) > 1:
        # Se tem mais de uma foto, gera o container slider
        total_fotos = len(fotos_convertidas)
        imgs_html = []
        for idx, img_url in enumerate(fotos_convertidas):
            delay = idx * (12 / total_fotos)
            imgs_html.append(f'<img src="{img_url}" class="timeline-img-h" style="animation-delay: {delay}s;">')
        tag_foto = f'<div class="timeline-slider">{"".join(imgs_html)}</div>'
    elif len(fotos_convertidas) == 1:
        # Se tem apenas uma foto
        tag_foto = f'<img src="{fotos_convertidas[0]}" class="timeline-img-h">'
    else:
        tag_foto = ''

    # HTML do Card
    card = (
        f'<div class="timeline-card-h" style="border-top: 5px solid {ev.get("cor_borda", "#28A745")};">'
        f'<div>'
        f'<div class="timeline-date-h">📅 {ev["data"]}</div>'
        f'<div class="timeline-title-h">{ev["titulo"]}</div>'
        f'<div class="timeline-desc-h">{ev["descricao"]}</div>'
        f'</div>'
        f'{tag_foto}'
        f'</div>'
    )
    cards_html.append(card)

# Junta todos os cards dentro do container flex com scroll horizontal
html_timeline = f'<div class="timeline-horizontal-scroll">{"".join(cards_html)}</div>'

st.markdown(html_timeline, unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. QUADRO DE GRÁFICOS (Estatísticas Inferiores)
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Resumo de Indicadores")
st.markdown('<div id="relatorios"></div>', unsafe_allow_html=True) # Âncora de Relatórios/Indicadores

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

# ---------------------------------------------------------
# 9. INFORMAÇÕES E LINKS DO PROJETO
# ---------------------------------------------------------
st.divider()
st.markdown('<div id="informacoes"></div>', unsafe_allow_html=True) # Âncora de Informações
st.subheader("ℹ️ Informações e Plataformas do Projeto")

st.write(
    "Acesse abaixo as plataformas e ferramentas utilizadas em outras etapas e "
    "atividades do mapeamento participativo do projeto **AfirmaSUS-JP**:"
)

i_col1, i_col2, i_col3 = st.columns(3)

with i_col1:
    st.markdown("### 🗺️ Ushahidi")
    st.write("Plataforma de mapeamento colaborativo e geolocalização de pontos de interesse do SUS.")
    st.link_button("Acessar Ushahidi", "https://kennyow.ushahidi.io/map", width='stretch')

with i_col2:
    st.markdown("### 📍 Partimap")
    st.write("Ferramenta de participação cidadã e cartografia comunitária interativa.")
    st.link_button("Acessar Partimap", "https://www.partimap.eu/en/p/AfirmaSUSJP/0?force=1", width='stretch')

with i_col3:
    st.markdown("### ⏳ ChronoFlo Timeline")
    st.write("Linha do tempo cronológica detalhada das ações e marcos do projeto AfirmaSUS.")
    st.link_button("Acessar ChronoFlo", "https://www.chronoflotimeline.com/timeline/shared/32199/AfirmaSUS/", width='stretch')