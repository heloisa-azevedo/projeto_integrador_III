#INFORMAÇÕES NOSSAS
import html

import requests
import streamlit as st

st.set_page_config(layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}

/* ---- Card marrom com texto branco ---- */
[class*="st-key-card-"] {
    background-color: #6d5b4f;
    border: none;
    border-radius: 24px;
    padding: 1.5rem;
    box-shadow: 0 8px 24px rgba(109, 91, 79, .35);
    font-size: 0.9rem;
}
[class*="st-key-card-"] *,
[class*="st-key-card-"] p,
[class*="st-key-card-"] span,
[class*="st-key-card-"] label,
[class*="st-key-card-"] h1,
[class*="st-key-card-"] h2,
[class*="st-key-card-"] h3,
[class*="st-key-card-"] li {
    color: white;
}
[class*="st-key-card-"] p,
[class*="st-key-card-"] li,
[class*="st-key-card-"] span {
    font-size: 0.9rem;
}

/* Divisor mais suave */
[class*="st-key-card-"] hr {
    border-color: rgba(255, 255, 255, .3);
}

/* Botões (GitHub e LinkedIn): brancos com texto marrom */
[class*="st-key-card-"] a[kind],
[class*="st-key-card-"] a[kind] * {
    background-color: white;
    color: #6d5b4f;
    border-color: white;
}

/* Expander transparente com borda clara */
[class*="st-key-card-"] [data-testid="stExpander"] {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, .4);
}

/* Blocos de código do README */
[class*="st-key-card-"] pre,
[class*="st-key-card-"] code {
    background-color: #4a3d34;
    color: white;
}

/* ---- Cabeçalho do card ---- */
.avatar {
    width: 140px; height: 140px;
    border-radius: 50%; object-fit: cover;
    border: 4px solid white;
    box-shadow: 0 6px 16px rgba(0, 0, 0, .3);
    display: block; margin: 8px auto 14px;
}
.chips {
    display: flex; gap: 8px; justify-content: center;
    flex-wrap: wrap; margin: 14px 0;
}

/* ---- Ajustes de fonte (no final, para sobrescrever as regras acima) ---- */
[class*="st-key-card-"] .nome {
    text-align: center; font-size: 1.3rem; font-weight: 700; margin: 0;
}
[class*="st-key-card-"] .bio {
    text-align: center; font-size: 0.85rem;
    opacity: .85; font-style: italic; margin: 4px 0 0;
}
[class*="st-key-card-"] .chip {
    padding: 5px 14px; border-radius: 999px;
    background: rgba(255, 255, 255, .15);
    border: 1px solid rgba(255, 255, 255, .4);
    font-size: 0.75rem; font-weight: 500;
}

/* Métricas */
[class*="st-key-card-"] [data-testid="stMetricValue"] {
    font-size: 1.5rem;
}
[class*="st-key-card-"] [data-testid="stMetricLabel"] p {
    font-size: 0.8rem;
}

/* README dentro do expander */
[class*="st-key-card-"] [data-testid="stExpander"] p,
[class*="st-key-card-"] [data-testid="stExpander"] li {
    font-size: 0.85rem;
}
[class*="st-key-card-"] [data-testid="stExpander"] h1 { font-size: 1.4rem; }
[class*="st-key-card-"] [data-testid="stExpander"] h2 { font-size: 1.2rem; }
[class*="st-key-card-"] [data-testid="stExpander"] h3 { font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)


# ---------- BUSCA DE DADOS (com cache) ----------
@st.cache_data(ttl=3600)
def buscar_dados_perfil(username):
    url = f"https://api.github.com/users/{username}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def buscar_readme(username):
    # README de perfil fica no repositório com o mesmo nome do usuário
    for branch in ("main", "master"):
        url = f"https://raw.githubusercontent.com/{username}/{username}/{branch}/README.md"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return res.text
        except Exception:
            pass
    return None


# ---------- CARD ----------
def renderizar_criador(username, container):
    dados = buscar_dados_perfil(username)
    readme_text = buscar_readme(username)

    if not dados:
        container.warning(
            f"Não foi possível carregar o perfil de @{username}. "
            "Verifique o username ou tente novamente em instantes."
        )
        return

    nome = html.escape(dados.get("name") or username)
    bio = html.escape(dados.get("bio") or "")
    avatar = html.escape(dados.get("avatar_url") or "")
    local = dados.get("location")
    empresa = dados.get("company")
    perfil_url = dados.get("html_url") or f"https://github.com/{username}"
    linkedin_url = f"https://www.linkedin.com/in/{username}/"

    with container.container(border=True, key=f"card-{username}"):
        # Cabeçalho
        if avatar:
            st.markdown(f'<img class="avatar" src="{avatar}">', unsafe_allow_html=True)
        st.markdown(f'<p class="nome">{nome}</p>', unsafe_allow_html=True)
        if bio:
            st.markdown(f'<p class="bio">{bio}</p>', unsafe_allow_html=True)

        # Chips (localização e empresa)
        chips = []
        if local:
            chips.append(f"📍 {html.escape(local)}")
        if empresa:
            chips.append(f"🏢 {html.escape(empresa)}")
        if chips:
            chips_html = "".join(f'<span class="chip">{c}</span>' for c in chips)
            st.markdown(f'<div class="chips">{chips_html}</div>', unsafe_allow_html=True)

        st.divider()

        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Repositórios", dados.get("public_repos", 0))
        m2.metric("Seguidores", dados.get("followers", 0))
        m3.metric("Seguindo", dados.get("following", 0))

        # Botões (GitHub e LinkedIn)
        b1, b2 = st.columns(2)
        b1.link_button("GitHub", perfil_url, use_container_width=True)
        b2.link_button("LinkedIn", linkedin_url, use_container_width=True)

        # README dentro de um expander
        with st.expander("📄 Ver README do perfil"):
            if readme_text:
                st.markdown(readme_text, unsafe_allow_html=True)
            else:
                st.info("README não disponível ou não configurado.")


# ---------- CONFIGURAÇÃO ----------
# Chave: nome de exibição | Valor: username (igual no GitHub e no LinkedIn)
criadores = {
    "Felipe Nunes": "finusz",
    "Heloísa Azevedo": "heloisa-azevedo",
    "Catharina Gato": "gatocatharinap",
}

# ---------- INTERFACE ----------
st.markdown(
    "<h1 style='text-align:center; font-weight:800'>Sobre o projeto</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align:center; max-width:800px; margin:0 auto 2rem'>"
    "Este app foi desenvolvido ao longo da disciplina de Projeto Integrador III, "
    "parte da grade do curso de Ciência de Dados da Faculdade de Tecnologia de Cotia (FATEC Cotia). "
    "Seu objetivo é analisar os dados financeiros públicos da grupo Petz Cobasi"
    "</p>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align:center'>Conheça os desenvolvedores responsáveis por este projeto:</p>",
    unsafe_allow_html=True,
)

colunas = st.columns(len(criadores), gap="large")
for coluna, username in zip(colunas, criadores.values()):
    renderizar_criador(username, coluna)