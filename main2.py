# python -m streamlit run main2.py

import streamlit as st
from streamlit_folium import st_folium
from streamlit_calendar import calendar
import folium
import pandas as pd
import json
import os
import re
import textwrap
import base64
import plotly.express as px

# ---------------------------------------------------------
# 1. FUNÇÕES AUXILIARES E CONFIGURAÇÕES INICIAIS
# ---------------------------------------------------------

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
# 2. CARREGAMENTO INICIAL DA BASE DE DADOS (GLOBAL)
# ---------------------------------------------------------
caminho_json = "dados_locais.json"
df_locais = pd.DataFrame()

if os.path.exists(caminho_json):
    try:
        with open(caminho_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list) and len(dados) > 0:
            df_locais = pd.DataFrame(dados)
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
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar a base de dados '{caminho_json}': {e}")


# ---------------------------------------------------------
# 3. BARRA SUPERIOR (HEADER)
# ---------------------------------------------------------
link_drive_logo = "https://drive.google.com/file/d/1YAMa6Ume30aX75c-p0w9BV15bWlKZkeY/view?usp=drive_link"
logo_url = converter_link_drive(link_drive_logo)

tag_logo_html = f'<img src="{logo_url}" class="header-logo" alt="Logo AfirmaSUS">' if logo_url else ''

header_html = textwrap.dedent("""
    <div class="header-top-bar" id="apresentacao">
        <div class="header-brand">
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
# 4. BARRA LATERAL (FILTROS DE PESQUISA E GALERIA)
# ---------------------------------------------------------
link_drive_logo_sidebar = "https://drive.google.com/file/d/1Cj16wbR1lr1W9BFhbn-tZp9kC5f2QGeT/view?usp=drive_link"
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

st.sidebar.markdown("### 🗺️ Mapeamento e Camadas")

opcoes_camadas = [
    "📍 Territorialização (AfirmaSUS)",
    "🩺 Encontro de Saúde (Setores)",
    "🚧 Novo Filtro 3 (Em breve)"
]

camada_selecionada = st.sidebar.selectbox(
    "Selecione a Camada do Mapa",
    opcoes_camadas,
    help="Escolha qual conjunto de dados você deseja visualizar no mapa."
)

st.sidebar.markdown("---")

df_filtrado = pd.DataFrame()
poligonos_encontro = []

# LÓGICA DA CAMADA: TERRITORIALIZAÇÃO
if camada_selecionada == "📍 Territorialização (AfirmaSUS)":
    st.sidebar.markdown("### Filtros da Territorialização")
    
    if df_locais.empty:
        st.sidebar.error("⚠️ Nenhum dado de territorialização encontrado em 'dados_locais.json'.")
    else:
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

        if st.sidebar.button("✨ Exibir Todas", width="stretch"):
            st.session_state["categoria_selecionada"] = "Todas"
            st.rerun()

        categorias_existentes = sorted(list(df_locais["categoria"].dropna().unique())) if 'categoria' in df_locais.columns else []

        cols = st.sidebar.columns(4)
        for i, cat in enumerate(categorias_existentes):
            info = MAPA_CATEGORIAS.get(cat, {"cor": "#6c757d", "icone": "📍"})
            col_idx = i % 4
            with cols[col_idx]:
                if st.button(info["icone"], key=f"cat_btn_{cat}", help=cat, width="stretch"):
                    st.session_state["categoria_selecionada"] = cat
                    st.rerun()

        if st.session_state["categoria_selecionada"] != "Todas":
            st.sidebar.info(f"Filtro ativo: **{st.session_state['categoria_selecionada']}**")

        # Filtragem dos Dados
        df_filtrado = df_locais.copy()
        if distrito_selecionado != "Todos" and 'distrito' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["distrito"] == distrito_selecionado]
        if st.session_state["categoria_selecionada"] != "Todas" and 'categoria' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["categoria"] == st.session_state["categoria_selecionada"]]

# LÓGICA DA CAMADA: ENCONTRO DE SAÚDE
elif camada_selecionada == "🩺 Encontro de Saúde (Setores)":
    st.sidebar.markdown("### 🩺 Filtro: Encontro de Saúde")
    
    caminho_encontro = "encontrodesaude.json"
    if os.path.exists(caminho_encontro):
        try:
            with open(caminho_encontro, "r", encoding="utf-8") as f:
                poligonos_encontro = json.load(f)
            
            status_opcao = st.sidebar.radio("Filtrar por Situação:", ["Todos", "✅ Concluídos", "❌ Pendentes"])
            
            if status_opcao == "✅ Concluídos":
                poligonos_encontro = [p for p in poligonos_encontro if p.get("status") == "concluido"]
            elif status_opcao == "❌ Pendentes":
                poligonos_encontro = [p for p in poligonos_encontro if p.get("status") == "pendente"]
                
            st.sidebar.success(f"{len(poligonos_encontro)} setor(es) exibido(s).")
            
        except Exception as e:
            st.sidebar.error(f"Erro ao ler '{caminho_encontro}': {e}")
    else:
        st.sidebar.warning(f"Arquivo '{caminho_encontro}' não encontrado.")

# FILTRO DE GALERIA DE FOTOS NA BARRA LATERAL
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
    st.sidebar.warning("⚠️ Não foi possível acessar o caminho de fotos local.")


# ---------------------------------------------------------
# 5. SEÇÃO DE APRESENTAÇÃO DO PROJETO
# ---------------------------------------------------------
st.markdown('<div id="apresentacao"></div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    col_apresentacao_foto, col_apresentacao_info = st.columns([2.2, 1])

    link_drive_foto_apresentacao = "https://drive.google.com/file/d/1Ebu5KMqcD0qWbOpz80I1cERKx7z7RPoM/view?usp=drive_link" 
    link_drive_logo_apresentacao = "https://drive.google.com/file/d/1YD1pFzwf_FLuvoZIP1R0oSrGh8XLghfC/view?usp=drive_link"

    url_foto_apresentacao = converter_link_drive(link_drive_foto_apresentacao)
    url_logo_apresentacao = converter_link_drive(link_drive_logo_apresentacao)

    with col_apresentacao_foto:
        st.subheader("📌 Apresentação")
        if url_foto_apresentacao:
            st.markdown(
                f'''
                <div class="apresentacao-foto-container">
                    <img src="{url_foto_apresentacao}" alt="Foto de Apresentação" />
                </div>
                ''',
                unsafe_allow_html=True
            )
        else:
            st.info("Espaço reservado para a imagem de apresentação.")

    with col_apresentacao_info:
        st.subheader("ℹ️ Sobre o Projeto")
        if url_logo_apresentacao:
            st.markdown(
                f'''
                <div style="text-align: center; margin-bottom: 10px;">
                    <img src="{url_logo_apresentacao}" style="max-height: 270px; width: auto; object-fit: contain;" alt="Logo AfirmaSUS" />
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        st.markdown(
            """
            <div style="text-align: justify; font-size: 13.5px; color: #444444; line-height: 1.5;">
                O <b>AfirmaSUS</b> é o Programa Nacional de Apoio à Permanência, Diversidade e Visibilidade para Discentes na Área da Saúde. Criado pelo Ministério da Saúde, ele financia projetos em universidades públicas para apoiar estudantes de grupos vulnerabilizados e cotistas, promovendo uma cultura antirracista e inclusiva no Sistema Único de Saúde.
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)


# ---------------------------------------------------------
# 6. SEÇÃO PRINCIPAL (MAPA INTERATIVO E DETALHES)
# ---------------------------------------------------------
st.markdown('<div id="territorio"></div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    col_mapa, col_detalhes = st.columns([2.2, 1])

    with col_mapa:
        st.subheader("📍 MAPA INTERATIVO")
        
        mapa_jp = folium.Map(location=[-7.135080186191312, -34.85575440327488], zoom_start=16, tiles="CartoDB voyager")
        
        # CAMADA 1: PONTOS DE TERRITORIALIZAÇÃO
        if camada_selecionada == "📍 Territorialização (AfirmaSUS)" and not df_filtrado.empty:
            st.info(f"Mostrando {len(df_filtrado)} local(is)")
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

        # CAMADA 2: POLÍGONOS ENCONTRO DE SAÚDE
        elif camada_selecionada == "🩺 Encontro de Saúde (Setores)" and poligonos_encontro:
            st.info(f"Exibindo {len(poligonos_encontro)} região(ões) mapeada(s)")
            for setor in poligonos_encontro:
                cor_area = setor.get("cor", "blue")
                vertices = setor.get("vertices", [])
                status = setor.get("status", "pendente")
                
                emoji_status = "✅" if status == "concluido" else "❌"
                
                folium.Polygon(
                    locations=vertices,
                    color=cor_area,
                    fill=True,
                    fill_color=cor_area,
                    fill_opacity=0.35,
                    weight=3,
                    popup=f"<b>{setor.get('nome')}</b><br>{setor.get('descricao')}",
                    tooltip=f"{emoji_status} {setor.get('nome')}"
                ).add_to(mapa_jp)
                
                centroide = setor.get("centroide")
                if centroide:
                    folium.Marker(
                        location=centroide,
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 24px; text-align: center;">{emoji_status}</div>'
                        ),
                        popup=f"Status: {status.capitalize()}"
                    ).add_to(mapa_jp)
        else:
            st.warning("Nenhum dado ativo para exibir nesta camada.")

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
                st.image(foto_url, width="stretch", caption=ponto_encontrado.get("nome", "Local"))
            
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
# 7. SEÇÃO DE VÍDEOS DA COMUNIDADE
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
# 8. SEÇÃO DA LINHA DO TEMPO DE ATIVIDADES
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
# 9. SEÇÃO DE FORMAÇÕES REALIZADAS
# ---------------------------------------------------------
st.markdown('<div id="formacoes"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("🎓 Formações Realizadas")

    caminho_formacoes = "formacoes.json"
    lista_formacoes = []

    if os.path.exists(caminho_formacoes):
        try:
            with open(caminho_formacoes, "r", encoding="utf-8") as f:
                lista_formacoes = json.load(f)
        except Exception as e:
            st.error(f"⚠️ Erro ao carregar o arquivo '{caminho_formacoes}': {e}")
    else:
        st.warning(f"⚠️ Arquivo '{caminho_formacoes}' não encontrado no diretório do projeto.")

    if lista_formacoes:
        formacoes_cards_html = []
        for item in lista_formacoes:
            foto_url = converter_link_drive(item.get("foto", ""))
            
            card = (
                f'<div class="timeline-card-h" style="border-top: 5px solid #FF8C00; padding: 0; overflow: hidden; display: flex; align-items: center; justify-content: center;">'
                f'  <img src="{foto_url}" alt="{item.get("titulo", "Formação")}" class="formacao-card-img" style="width: 100%; height: 100%; object-fit: cover;" />'
                f'</div>'
            )
            formacoes_cards_html.append(card)

        st.markdown(f'<div class="timeline-horizontal-scroll">{"".join(formacoes_cards_html)}</div>', unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)


# ---------------------------------------------------------
# 10. SEÇÃO DE INDICADORES DE PROCESSOS DE TRABALHO E FORMAÇÃO
# ---------------------------------------------------------
st.markdown('<div id="relatorios"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("📊 Indicadores de Processos de Trabalho e Formação - (CronoFloTimeline)")

    # --- 1. CARDS DE MÉTRICAS EDITÁVEIS ---

    st.markdown("##### 📌 Indicadores Gerais de Impacto e Saúde")
        
    # Formulário / Expander opcional para alterar os valores rapidamente
    with st.expander("⚙️ Clique para editar os valores dos Indicadores", expanded=False):
        c_ed1, c_ed2, c_ed3 = st.columns(3)  # Alterado de 4 para 3 colunas
        with c_ed1:
            qtd_acoes = st.number_input("Total de Ações Realizadas", min_value=0, value=77, key="inp_qtd1")  # Soma total de eventos
        with c_ed2:
            qtd_participantes = st.number_input("Participantes Impactados", min_value=0, value=150, key="inp_qtd2")
        with c_ed3:
            qtd_formacoes = st.number_input("Formações e Oficinas Realizadas", min_value=0, value=22, key="inp_qtd3")  # 16 formações + 6 oficinas de teatro

    # Exibição dos Cards organizados
    m_col1, m_col2, m_col3 = st.columns(3)  # Alterado de 4 para 3 colunas
    with m_col1:
        st.metric(label="Total de Ações Realizadas", value=f"{qtd_acoes}", delta="eventos cadastrados")
    with m_col2:
        st.metric(label="Participantes Impactados", value=f"{qtd_participantes}", delta="pessoas")
    with m_col3:
        st.metric(label="Formações e Oficinas", value=f"{qtd_formacoes}", delta="atividades formativas")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 2. GRÁFICOS ESTATÍSTICOS BASEADOS NO CHRONOFLO ---
    st.markdown("##### 📈 Panorama das Atividades do ChronoFlo")

    # --- DADOS ATUALIZADOS DO CHRONOFLO ---

    # 1. Evolução Mensal (dados de Dez/25 a Ago/26)
    dados_mensais = pd.DataFrame({
        "Mês": ["Dez/25", "Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26"],
        "Quantidade": [5, 6, 7, 20, 7, 9, 11, 4, 2]
    })

    # 2. Distribuição por Categoria
    dados_categorias = pd.DataFrame({
        "Categoria": [
            "Rodas de Afirmações e Conversa",
            "Territorialização / Campo",
            "Formações, Cursos e Oficinas",
            "Oficinas Culturais/Teatro",
            "Gestão e Comunicação",
            "Eventos Institucionais"
        ],
        "Eventos": [24, 12, 16, 6, 9, 10]
    })

    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.markdown("**Evolução Mensal de Atividades**")
        fig_linha = px.line(
            dados_mensais, 
            x="Mês", 
            y="Quantidade", 
            markers=True,
            text="Quantidade",
            labels={"Quantidade": "Nº de Eventos", "Mês": "Mês / Ano"},
            color_discrete_sequence=["#FF8C00"]
        )
        fig_linha.update_traces(textposition="top center", fill='tozeroy')
        fig_linha.update_layout(height=330, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_linha, use_container_width=True)

    with col_graf2:
        st.markdown("**Distribuição por Eixo de Atuação**")
        fig_rosca = px.pie(
            dados_categorias, 
            values="Eventos", 
            names="Categoria", 
            hole=0.45,
            color_discrete_sequence=["#856eaf", "#28A745", "#FF8C00", "#7BDCEB", "#CF68E3", "#DC3545"]
        )
        fig_rosca.update_traces(textinfo="percent+value")
        fig_rosca.update_layout(height=330, margin=dict(l=10, r=10, t=30, b=10), showlegend=True)
        st.plotly_chart(fig_rosca, use_container_width=True)

# APRESENTAÇÕES CANVA
st.markdown('<div id="apresentacoes"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# 11. SEÇÃO DE CALENDÁRIO DE ATIVIDADES
# ---------------------------------------------------------
@st.dialog("📌 Detalhes da Atividade")
def exibir_modal_evento(evento_info):
    titulo = evento_info.get("title", "Sem título")
    inicio = evento_info.get("start", "")
    descricao = evento_info.get("extendedProps", {}).get("description", "Nenhuma descrição informada.")
    
    st.markdown(f"### {titulo}")
    st.markdown(f"**📅 Data:** {inicio}")
    st.markdown("---")
    st.markdown(f"**📝 Descrição:**\n\n{descricao}")

st.markdown('<div id="calendario"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("📅 Calendário de Atividades")

    caminho_eventos = "eventos.json"
    lista_eventos = []

    if os.path.exists(caminho_eventos):
        try:
            with open(caminho_eventos, "r", encoding="utf-8") as f:
                eventos_brutos = json.load(f)
                
                for ev in eventos_brutos:
                    evento_fmt = ev.copy()
                    evento_fmt["extendedProps"] = {
                        "description": ev.get("description", "Sem descrição disponível.")
                    }
                    lista_eventos.append(evento_fmt)
        except Exception as e:
            st.error(f"⚠️ Erro ao carregar o arquivo '{caminho_eventos}': {e}")
    else:
        st.warning(f"⚠️ Arquivo '{caminho_eventos}' não encontrado no diretório do projeto.")

    calendar_options = {
        "editable": False,
        "selectable": True,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek"
        },
        "initialView": "dayGridMonth",
        "locale": "pt-br",
        "buttonText": {
            "today": "Hoje",
            "month": "Mês",
            "week": "Semana"
        }
    }

    state = calendar(
        options=calendar_options, 
        events=lista_eventos, 
        key="cal_afirmasus_json"
    )

    if state.get("eventClick"):
        evento_clicado = state["eventClick"]["event"]
        exibir_modal_evento(evento_clicado)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)


# ---------------------------------------------------------
# 12. SEÇÃO DE INTEGRANTES E PLATAFORMAS
# ---------------------------------------------------------
st.markdown('<div id="integrantes"></div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="floating-window"></div>', unsafe_allow_html=True)
    st.subheader("👥 Integrantes do Projeto")

    caminho_integrantes = "integrantes.json"
    lista_integrantes = []

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
            foto_url = converter_link_drive(intg.get("foto", ""))
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