AfirmaSUS-JP — Mapeamento Participativo do SUS
O AfirmaSUS-JP é uma plataforma web interativa desenvolvida com Streamlit e Folium para o mapeamento colaborativo e territorialização da comunidade São Rafael (Distrito Sanitário I) em João Pessoa - PB.

A aplicação visa dar visibilidade aos pontos de atenção à saúde, equipamentos culturais, esportivos, sociais e comerciais do território, articulando ações do Programa Nacional de Apoio à Permanência, Diversidade e Visibilidade para Discentes na Área da Saúde (AfirmaSUS).

📌 Funcionalidades

    📍 Territorialização Interativa: Mapa dinâmico com marcadores categorizados por cores e ícones personalizados via FontAwesome.
    
    🖼️ Painel de Detalhes Dinâmico: Visualização de imagens, status de infraestrutura e informações detalhadas ao clicar nos marcadores do mapa.
    
    🎯 Filtros Avançados: Filtragem por categoria (Saúde, Educação, Esporte e Lazer, Religião, Cultura, Comércio, Administrativo) e por Distrito Sanitário.
    
    🎥 Central de Mídia: Exibição de vídeos e entrevistas sobre a memória e identidade do território.
    
    🕐 Linha do Tempo de Atividades: Carrossel interativo e animado com fotos e histórico de eventos da comunidade.
    
    📊 Dashboard e Indicadores: Gráficos interativos com a distribuição de equipamentos urbanos e estado de conservação/infraestrutura.
    
    🔗 Integração com Plataformas Externas: Conexão direta com ferramentas como Ushahidi, Partimap, ChronoFlo e redes sociais.

📂 Estrutura do Repositório

├── main2.py             # Código principal da aplicação Streamlit
├── style.css            # Estilização customizada em CSS (tema, cards e componentes)
├── dados_locais.json    # Base de dados contendo os pontos do mapa (geolocalização, descrições, etc.)
├── timeline.json       # Dados e imagens da linha do tempo
└── README.md            # Documentação do projeto

🗄️ Estrutura dos Dados (dados_locais.json)
O projeto utiliza um arquivo JSON estruturado para alimentar os marcadores do mapa e os detalhes de cada local. Exemplo de item:

{
  "id": 5,
  "nome": "USF São Rafael",
  "distrito": "Distrito I",
  "categoria": "Saúde",
  "lat": -7.1356746,
  "lon": -34.8551993,
  "foto": "https://.../usfsr.jpg",
  "descricao": "**Função:** Oferecer atendimento multiprofissional...",
  "status": "Crítico",
  "cor": "green",
  "icone": "heart-pulse"
}

🚀 Como Executar o Projeto
Pré-requisitos
Certifique-se de ter o Python 3.8+ instalado em sua máquina.

1. Clonar o repositório
    git clone https://github.com/seu-usuario/afirmasus-jp.git
    cd afirmasus-jp
2. Instalar as dependências
  pip install streamlit streamlit-folium folium pandas
3. Executar a aplicação
   python -m streamlit run main2.py

Acesse a aplicação no navegador em http://localhost:8501.

🎨 Categorias Mapeadas
Categoria,Ícone,Cor
Esporte e Lazer,person-running,Laranja (#FF8C00)
Saúde,user-md,Verde (#28A745)
Educação,user-graduate,Roxo (#856eaf)
Religião,place-of-worship,Azul Claro (#7BDCEB)
Cultura,landmark,Bege (#D1C7A5)
Comércio,shopping-cart,Vermelho (#DC3545)
Administrativo,briefcase,Rosa/Roxo (#CF68E3)

📄 Licença
Este projeto é disponibilizado sob a licença MIT.
