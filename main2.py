# python -m streamlit run main2.py

import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import json
import os
import re
import textwrap
import base64

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
    page_title="AfirmaSUS-JP",
    page_icon="🏥"
)

# Função para carregar o arquivo CSS externo
def carregar_css(caminho_arquivo):
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

carregar_css("style.css")

# ---------------------------------------------------------
# BARRA SUPERIOR ROXA (COM LOGO)
# ---------------------------------------------------------
link_drive_logo = "https://drive.google.com/file/d/1YAMa6Ume30aX75c-p0w9BV15bWlKZkeY/view?usp=drive_link"
logo_url = converter_link_drive(link_drive_logo)

tag_logo_html = f'<img src="{logo_url}" class="header-logo" alt="Logo AfirmaSUS">' if logo_url else ''

header_html = textwrap.dedent(f"""
    <div class="header-top-bar" id="territorio">
        <div class="header-brand">
            {tag_logo_html}
            <h1 class="header-title">AfirmaSUS–JP</h1>
            <span class="header-subtitle">Mapeamento Participativo do SUS</span>
        </div>
        <div class="header-nav">
            <a class="header-nav-btn active" href="#territorio">Território</a>
            <a class="header-nav-btn" href="#videos">Vídeos</a>
            <a class="header-nav-btn" href="#linha-do-tempo">Linha do Tempo</a>
            <a class="header-nav-btn" href="#relatorios">Relatórios</a>
            <a class="header-nav-btn" href="#integrantes">Integrantes</a>
            <a class="header-nav-btn" href="#informacoes">Informações</a>
        </div>
    </div>
""")

st.markdown(header_html, unsafe_allow_html=True)

# LINHA LARANJA SEPARADORA
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. BARRA LATERAL (Filtros de Pesquisa)
# ---------------------------------------------------------

link_drive_logo_sidebar = "https://drive.google.com/file/d/1YD1pFzwf_FLuvoZIP1R0oSrGh8XLghfC/view?usp=drive_link"
logo_sidebar_url = converter_link_drive(link_drive_logo_sidebar)

if logo_sidebar_url:
    st.sidebar.markdown(
        f'''
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="{logo_sidebar_url}" style="max-width: 100%; height: auto; object-fit: contain;" alt="Logo AfirmaSUS" />
        </div>
        ''',
        unsafe_allow_html=True
    )

st.sidebar.markdown(
    """
    <hr style="border: none; border-top: 1px solid #FF8C00; margin: 12px 0; opacity: 0.6;" />
    
    <div style="text-align: justify; font-size: 13px; color: #555555; line-height: 1.4;">
        O <b>AfirmaSUS</b> é o Programa Nacional de Apoio à Permanência, Diversidade e Visibilidade para Discentes na Área da Saúde. Criado pelo Ministério da Saúde, ele financia projetos em universidades públicas para apoiar estudantes de grupos vulnerabilizados e cotistas, promovendo uma cultura antirracista e inclusiva no Sistema Único de Saúde.
    </div>
    
    <hr style="border: none; border-top: 1px solid #FF8C00; margin: 12px 0 20px 0; opacity: 0.6;" />
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("### Filtros de Pesquisa")

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
except Exception as e:
    st.error(f"⚠️ Erro ao carregar a base de dados: {e}")
    st.stop()

if df_locais.empty:
    st.error("⚠️ O DataFrame está vazio! Verifique o arquivo JSON.")
    st.stop()

df_locais.columns = df_locais.columns.astype(str).str.strip().str.lower()

colunas_necessarias = ['distrito', 'categoria', 'nome', 'lat', 'lon', 'status', 'cor', 'icone', 'foto', 'descricao']
for col_necessaria in colunas_necessarias:
    if col_necessaria not in df_locais.columns:
        for col_existente in list(df_locais.columns):
            if col_necessaria.lower() in col_existente.lower() or col_existente.lower() in col_necessaria.lower():
                df_locais.rename(columns={col_existente: col_necessaria}, inplace=True)
                break

if 'lat' in df_locais.columns:
    df_locais['lat'] = pd.to_numeric(df_locais['lat'], errors='coerce')
if 'lon' in df_locais.columns:
    df_locais['lon'] = pd.to_numeric(df_locais['lon'], errors='coerce')

df_locais = df_locais.dropna(subset=['lat', 'lon'])

if "categoria_selecionada" not in st.session_state:
    st.session_state["categoria_selecionada"] = "Todas"

MAPA_CATEGORIAS = {
    "Esporte e Lazer": {"cor": "#FF8C00", "icone": "🏃"},
    "Saúde":           {"cor": "#28A745", "icone": "🩺"},
    "Educação":        {"cor": "#856eaf", "icone": "🎓"},
    "Religião":        {"cor": "#7BDCEB", "icone": "️⛪"},
    "Cultura":         {"cor": "#D1C7A5", "icone": "🏛️"},
    "Comércio":        {"cor": "#DC3545", "icone": "🛒"},
    "Administrativo":  {"cor": "#CF68E3", "icone": "💼"}
}

if 'distrito' in df_locais.columns and not df_locais['distrito'].isna().all():
    distritos_disponiveis = ["Todos"] + sorted(list(df_locais["distrito"].dropna().unique()))
    distrito_selecionado = st.sidebar.selectbox("Distrito Sanitário", distritos_disponiveis)
else:
    distrito_selecionado = "Todos"

st.sidebar.markdown("**Categorias**")

if st.sidebar.button("✨ Exibir Todas", use_container_width=True):
    st.session_state["categoria_selecionada"] = "Todas"
    st.rerun()

categorias_existentes = sorted(list(df_locais["categoria"].dropna().unique())) if 'categoria' in df_locais.columns else []

cols = st.sidebar.columns(4)
for i, cat in enumerate(categorias_existentes):
    info = MAPA_CATEGORIAS.get(cat, {"cor": "#6c757d", "icone": "📍"})
    col_idx = i % 4
    with cols[col_idx]:
        if st.button(info["icone"], key=f"cat_btn_{cat}", help=cat, use_container_width=True):
            st.session_state["categoria_selecionada"] = cat
            st.rerun()

if st.session_state["categoria_selecionada"] != "Todas":
    st.sidebar.info(f"Filtro ativo: **{st.session_state['categoria_selecionada']}**")

# ---------------------------------------------------------
# APLICAÇÃO DOS FILTROS NO DATAFRAME
# ---------------------------------------------------------
categoria_selecionada = st.session_state["categoria_selecionada"]

df_filtrado = df_locais.copy()
if distrito_selecionado != "Todos" and 'distrito' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["distrito"] == distrito_selecionado]
if categoria_selecionada != "Todas" and 'categoria' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria_selecionada]

# ---------------------------------------------------------
# FILTRO DE GALERIA DE FOTOS NA BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.markdown('<hr style="border: none; border-top: 1px solid #FF8C00; margin: 4px 0 4px 0; opacity: 0.6;" />', unsafe_allow_html=True)
st.sidebar.markdown("<h3 style='margin-bottom: 2px; padding-bottom: 0px;'>🖼️ Galeria de Fotos</h3>", unsafe_allow_html=True)

caminho_base_imagens = r"G:\.shortcut-targets-by-id\1etsHUqyiieSU_ujw74Wnk7YCxp4Td8gI\AfirmAções JampaSUS SR\AfirmaSUS\Imagens"

def obter_pastas_e_imagens(caminho_raiz):
    pastas_dict = {}
    if os.path.exists(caminho_raiz):
        for item in sorted(os.listdir(caminho_raiz)):
            caminho_completo = os.path.join(caminho_raiz, item)
            if os.path.isdir(caminho_completo):
                imagens = [
                    os.path.join(caminho_completo, f) 
                    for f in sorted(os.listdir(caminho_completo)) 
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
                ]
                if imagens:
                    pastas_dict[f"📁 {item}"] = {
                        "titulo": item,
                        "caminho_pasta": caminho_completo,
                        "fotos": imagens
                    }
    return pastas_dict

@st.dialog("🖼️ Galeria de Fotos", width="large")
def exibir_modal_fotos_locais(dados_pasta):
    st.markdown(f"### {dados_pasta['titulo']}")
    fotos = dados_pasta['fotos']

    if len(fotos) == 1:
        st.markdown(f'''
            <div class="foto-modal-frame">
                <img src="data:image/jpeg;base64,{base64.b64encode(open(fotos[0], "rb").read()).decode()}" />
            </div>
        ''', unsafe_allow_html=True)
    else:
        abas = st.tabs([f"📷 Foto {i+1}" for i in range(len(fotos))])
        for idx, tab in enumerate(abas):
            with tab:
                with open(fotos[idx], "rb") as f_img:
                    encoded_img = base64.b64encode(f_img.read()).decode()
                st.markdown(f'''
                    <div class="foto-modal-frame">
                        <img src="data:image/jpeg;base64,{encoded_img}" />
                    </div>
                ''', unsafe_allow_html=True)

pastas_encontradas = obter_pastas_e_imagens(caminho_base_imagens)

if pastas_encontradas:
    opcoes = ["Selecione uma pasta..."] + list(pastas_encontradas.keys())
    
    pasta_selecionada = st.sidebar.selectbox(
        "Escolha a pasta de imagens:", 
        options=opcoes,
        key="select_galeria_drive_local"
    )

    if pasta_selecionada != "Selecione uma pasta...":
        dados_da_pasta = pastas_encontradas[pasta_selecionada]
        exibir_modal_fotos_locais(dados_da_pasta)
else:
    st.sidebar.warning("⚠️ Não foi possível acessar o caminho de fotos. Verifique se a pasta 'Imagens' está no repositório.")

# ---------------------------------------------------------
# 2. ÁREA PRINCIPAL (JANELA 1: MAPA + DETALHES)
# ---------------------------------------------------------
st.markdown('<div id="territorio"></div>', unsafe_allow_html=True)

if df_filtrado.empty:
    st.warning("⚠️ Nenhum dado disponível para exibir no mapa.")
    st.info("Verifique se o arquivo JSON tem dados válidos com coordenadas (lat/lon).")
    st.stop()

with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    col_mapa, col_detalhes = st.columns([2.2, 1])

    with col_mapa:
        st.subheader("📍 Territorialização")
        st.info(f"Mostrando {len(df_filtrado)} local(is)")
        
        mapa_jp = folium.Map(location=[-7.135080186191312, -34.85575440327488], zoom_start=16, tiles="CartoDB voyager")
        
        for idx, row in df_filtrado.iterrows():
            if pd.isna(row["lat"]) or pd.isna(row["lon"]):
                continue
            
            icone_nome = row.get("icone", "hospital")
            if pd.isna(icone_nome): icone_nome = "hospital"
            
            nome_local = row.get("nome", f"Local {idx}")
            if pd.isna(nome_local): nome_local = f"Local {idx}"
            
            categoria_local = row.get("categoria", "Não especificada")
            if pd.isna(categoria_local): categoria_local = "Não especificada"
            
            cor_local = row.get("cor", "purple")
            if pd.isna(cor_local): cor_local = "purple"
                
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=nome_local,
                tooltip=f"{nome_local} ({categoria_local})",
                icon=folium.Icon(color=cor_local, icon=icone_nome, prefix="fa")
            ).add_to(mapa_jp)
        
        map_data = st_folium(mapa_jp, width="100%", height=480, key="mapa_folium")

    with col_detalhes:
        st.subheader("🖼️ Detalhes do Local")
        ponto_encontrado = None
        
        if map_data and map_data.get("last_object_clicked"):
            lat_clicada = map_data["last_object_clicked"]["lat"]
            lon_clicada = map_data["last_object_clicked"]["lng"]
            
            if not df_filtrado.empty:
                df_temp = df_filtrado.copy()
                df_temp["distancia"] = (
                    (df_temp["lat"] - lat_clicada) ** 2 + 
                    (df_temp["lon"] - lon_clicada) ** 2
                )
                ponto_mais_proximo = df_temp.sort_values("distancia").iloc[0]
                
                if ponto_mais_proximo["distancia"] < 0.0005:
                    ponto_encontrado = ponto_mais_proximo

        if ponto_encontrado is not None:
            if "foto" in ponto_encontrado and pd.notna(ponto_encontrado["foto"]):
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

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. VÍDEOS (JANELA 2 - CARROSSEL HORIZONTAL)
# ---------------------------------------------------------
st.markdown('<div id="videos"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("🎥 Vídeos da Comunidade")

    def extrair_youtube_id(url):
        match = re.search(r'(?:v=|\/live\/|\/embed\/|youtu\.be\/|\/v\/)([\w-]{11})', url)
        return match.group(1) if match else url

    lista_videos = [
        {
            "url": "https://youtu.be/dOvOjLi99WE",
            "titulo": "São Rafael: Memória e Identidade",
            "descricao": "Apresentação da comunidade São Rafael em João Pessoa."
        },
        {
            "url": "https://www.youtube.com/watch?v=1zlLovtiBd4",
            "titulo": "Entrevista: Prof. Allef Santana",
            "descricao": "Territorialização e dinâmicas sócio-territoriais da saúde."
        },
        {
            "url": "https://www.youtube.com/watch?v=5MPQ0RQoEmw",
            "titulo": "Clínica Ampliada e Participação",
            "descricao": "Entrevista com Lidiane Tributino e Vitor Marinho."
        },
        {
            "url": "https://www.youtube.com/watch?v=oTKGjQPs4s8&t=8s",
            "titulo": "Entrevista: Professor Marlon Nilton",
            "descricao": "Entrevista com docente Marlon Nilton sobre saúde e educação."
        }
    ]

    videos_cards_html = []
    for vid in lista_videos:
        video_id = extrair_youtube_id(vid["url"])
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        
        card = (
            f'<div class="video-card-h">'
            f'  <div class="video-card-iframe-container">'
            f'    <iframe src="{embed_url}" title="{vid["titulo"]}" allowfullscreen></iframe>'
            f'  </div>'
            f'  <div class="video-card-title">{vid["titulo"]}</div>'
            f'  <div class="video-card-caption">{vid["descricao"]}</div>'
            f'</div>'
        )
        videos_cards_html.append(card)

    st.markdown(f'<div class="videos-horizontal-scroll">{"".join(videos_cards_html)}</div>', unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. LINHA DO TEMPO HORIZONTAL (JANELA 3 - COM CARROSSEL)
# ---------------------------------------------------------
st.markdown('<div id="linha-do-tempo"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("🕐 Linha do Tempo de Atividades")

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

    try:
        with open("timeline.json", "r", encoding="utf-8") as f:
            eventos_timeline = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar timeline.json: {e}")
        eventos_timeline = []

    cards_html = []
    for ev in eventos_timeline:
        lista_fotos_raw = ev.get("fotos", [])
        if not lista_fotos_raw and ev.get("foto"):
            lista_fotos_raw = [ev["foto"]]
        
        fotos_convertidas = [converter_link_drive(url) for url in lista_fotos_raw]
        
        if len(fotos_convertidas) > 1:
            total_fotos = len(fotos_convertidas)
            imgs_html = []
            for idx, img_url in enumerate(fotos_convertidas):
                delay = idx * (12 / total_fotos)
                imgs_html.append(f'<img src="{img_url}" class="timeline-img-h" style="animation-delay: {delay}s;">')
            tag_foto = f'<div class="timeline-slider">{"".join(imgs_html)}</div>'
        elif len(fotos_convertidas) == 1:
            tag_foto = f'<img src="{fotos_convertidas[0]}" class="timeline-img-h">'
        else:
            tag_foto = ''

        card = (
            f'<div class="timeline-card-h" style="border-top: 5px solid {ev.get("cor_borda", "#4C2059")};">'
            f'<div>'
            f'<div class="timeline-date-h">📅 {ev["data"]}</div>'
            f'<div class="timeline-title-h">{ev["titulo"]}</div>'
            f'<div class="timeline-desc-h">{ev["descricao"]}</div>'
            f'</div>'
            f'{tag_foto}'
            f'</div>'
        )
        cards_html.append(card)

    st.markdown(f'<div class="timeline-horizontal-scroll">{"".join(cards_html)}</div>', unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. INDICADORES (JANELA 4)
# ---------------------------------------------------------
st.markdown('<div id="relatorios"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("📊 Indicadores do Mapeamento")

    if not df_filtrado.empty:
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.markdown("**Pontos por Distrito**")
            st.bar_chart(df_filtrado["distrito"].value_counts())
        with g_col2:
            st.markdown("**Distribuição por Infraestrutura**")
            st.bar_chart(df_filtrado["status"].value_counts())

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. INTEGRANTES (JANELA 5 - CARROSSEL HORIZONTAL)
# ---------------------------------------------------------
st.markdown('<div id="integrantes"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("👥 Integrantes do Projeto")

    caminho_integrantes = "integrantes.json"
    lista_integrantes = []

    # Carrega os dados diretamente do arquivo JSON local
    if os.path.exists(caminho_integrantes):
        try:
            with open(caminho_integrantes, "r", encoding="utf-8") as f:
                lista_integrantes = json.load(f)
        except Exception as e:
            st.error(f"⚠️ Erro ao carregar o arquivo '{caminho_integrantes}': {e}")
    else:
        st.warning(f"⚠️ Arquivo '{caminho_integrantes}' não encontrado no diretório do projeto.")

    if lista_integrantes:
        integrantes_cards_html = []
        for intg in lista_integrantes:
            # Trata o link do Google Drive se necessário
            foto_url = converter_link_drive(intg.get("foto", ""))
            
            # Pega a situação (Bolsista, Voluntário, etc.) se existir no JSON
            situacao_texto = intg.get("situacao", "")
            html_situacao = f'<div class="timeline-desc-h" style="font-size: 12px; color: #777; margin-top: 2px;">{situacao_texto}</div>' if situacao_texto else ''

            card = (
                f'<div class="timeline-card-h" style="border-top: 5px solid #FF8C00; display: flex; flex-direction: column; align-items: center; text-align: center;">'
                f'  <div style="width: 100%; height: 180px; display: flex; align-items: center; justify-content: center; background-color: #f8f9fa; border-radius: 6px; margin-bottom: 12px; overflow: hidden;">'
                f'      <img src="{foto_url}" style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 4px;" />'
                f'  </div>'
                f'  <div class="timeline-title-h"><b>{intg.get("nome", "")}</b></div>'
                f'  <div class="timeline-desc-h" style="font-weight: normal; color: #555;">{intg.get("curso", "")}</div>'
                f'  {html_situacao}'
                f'</div>'
            )
            integrantes_cards_html.append(card)

        st.markdown(f'<div class="timeline-horizontal-scroll">{"".join(integrantes_cards_html)}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. INFORMAÇÕES E PLATAFORMAS (JANELA 6)
# ---------------------------------------------------------
st.markdown('<div id="informacoes"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("ℹ️ Informações e Plataformas")

    links_info = [
        {"nome": "Ushahidi", "desc": "Mapeamento colaborativo.", "url": "https://kennyow.ushahidi.io/map", "logo": "https://drive.google.com/file/d/1Y7DiHORMbXRFZfM-v3jTHC07aSl6sYse/view?usp=drive_link"},
        {"nome": "Partimap", "desc": "Cartografia comunitária.", "url": "https://www.partimap.eu/en/p/AfirmaSUSJP/0?force=1", "logo": "https://drive.google.com/file/d/1UJOoYTfH2HXFPEzPurd_gCE3qmqirWgp/view?usp=drive_link"},
        {"nome": "ChronoFlo", "desc": "Linha do tempo interativa.", "url": "https://www.chronoflotimeline.com/timeline/shared/32199/AfirmaSUS/", "logo": "https://drive.google.com/file/d/1z3b8OyQeX2PMXoCLO3g-_pFtsNdhUi0G/view?usp=drive_link"},
        {"nome": "Instagram", "desc": "Perfil oficial do projeto.", "url": "https://www.instagram.com/afirmasusjp/", "logo": "https://drive.google.com/file/d/1P6sTla2_5gbSwTpraremHHL9uGRAQ7Vp/view?usp=drive_link"}
    ]

    cols_info = st.columns(4)
    for idx, item in enumerate(links_info):
        with cols_info[idx]:
            logo_path = item["logo"]
            
            if "drive.google.com" in logo_path:
                img_src = converter_link_drive(logo_path)
            elif logo_path.startswith("./"):
                if 'carregar_imagem_base64' in globals():
                    img_src = carregar_imagem_base64(logo_path)
                else:
                    if os.path.exists(logo_path):
                        with open(logo_path, "rb") as f:
                            dados = f.read()
                        img_src = f"data:image/png;base64,{base64.b64encode(dados).decode()}"
                    else:
                        img_src = ""
            else:
                img_src = logo_path

            st.markdown(f'''
                <div style="text-align: center;">
                    <a href="{item['url']}" target="_blank">
                        <img src="{img_src}" style="height: 80px; object-fit: contain;" />
                    </a>
                    <h4 style="margin-top: 8px;">{item['nome']}</h4>
                </div>
            ''', unsafe_allow_html=True)
            st.caption(item["desc"])