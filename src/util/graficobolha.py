"""Mapa de bolhas do Brasil: uma bolha por loja (aba Lista de Lojas).
Cor = bandeira (Petz azul, Cobasi verde); tamanho da bolha proporcional à área (m²).

A planilha traz só cidade e UF, sem latitude/longitude. As coordenadas abaixo são as
da sede de cada município (base pública do IBGE, repositório kelvins/municipios-brasileiros).
Lojas da mesma cidade são espalhadas numa pequena espiral em volta da sede para que
cada loja apareça como uma bolha própria (a posição dentro da cidade é ilustrativa).
"""
import math
import unicodedata

import pandas as pd
import plotly.graph_objects as go

from src.util.estilo import COR_EMPRESA, MARINHO, _br

# (cidade, UF) -> (latitude, longitude) da sede do município
COORDENADAS = {
    ("Maceió", "AL"): (-9.6660, -35.7350),
    ("Manaus", "AM"): (-3.1187, -60.0212),
    ("Feira de Santana", "BA"): (-12.2664, -38.9663),
    ("Lauro de Freitas", "BA"): (-12.8978, -38.3210),
    ("Salvador", "BA"): (-12.9718, -38.5011),
    ("Vitoria Da Conquista", "BA"): (-14.8615, -40.8442),
    ("Eusebio", "CE"): (-3.8925, -38.4559),
    ("Fortaleza", "CE"): (-3.7166, -38.5423),
    ("Maracanau", "CE"): (-3.8670, -38.6259),
    ("Brasília", "DF"): (-15.7795, -47.9297),
    ("Serra", "ES"): (-20.1210, -40.3074),
    ("Vila Velha", "ES"): (-20.3417, -40.2875),
    ("Vitória", "ES"): (-20.3155, -40.3128),
    ("Goiania", "GO"): (-16.6864, -49.2643),
    ("Goiânia", "GO"): (-16.6864, -49.2643),
    ("Rio Verde", "GO"): (-17.7923, -50.9192),
    ("Valparaíso de Goiás", "GO"): (-16.0651, -47.9757),
    ("São Luís", "MA"): (-2.5387, -44.2825),
    ("Andradas", "MG"): (-22.0695, -46.5724),
    ("Belo Horizonte", "MG"): (-19.9102, -43.9266),
    ("Betim", "MG"): (-19.9668, -44.2008),
    ("Contagem", "MG"): (-19.9321, -44.0539),
    ("Divinópolis", "MG"): (-20.1446, -44.8912),
    ("Governador Valadares", "MG"): (-18.8545, -41.9555),
    ("Ipatinga", "MG"): (-19.4703, -42.5476),
    ("Juiz de Fora", "MG"): (-21.7595, -43.3398),
    ("Poços de Caldas", "MG"): (-21.7800, -46.5692),
    ("Sete Lagoas", "MG"): (-19.4569, -44.2413),
    ("Uberaba", "MG"): (-19.7472, -47.9381),
    ("Uberlandia", "MG"): (-18.9141, -48.2749),
    ("Uberlândia", "MG"): (-18.9141, -48.2749),
    ("Campo Grande", "MS"): (-20.4486, -54.6295),
    ("Dourados", "MS"): (-22.2231, -54.8120),
    ("Cuiabá", "MT"): (-15.6010, -56.0974),
    ("Varzea Grande", "MT"): (-15.6458, -56.1322),
    ("Várzea Grande", "MT"): (-15.6458, -56.1322),
    ("Belém", "PA"): (-1.4554, -48.4898),
    ("Bélem", "PA"): (-1.4554, -48.4898),
    ("João Pessoa", "PB"): (-7.1151, -34.8641),
    ("Jaboatão dos Guararapes", "PE"): (-8.1130, -35.0150),
    ("Olinda", "PE"): (-8.0102, -34.8545),
    ("Recife", "PE"): (-8.0467, -34.8771),
    ("Teresina", "PI"): (-5.0919, -42.8034),
    ("Cascavel", "PR"): (-24.9573, -53.4590),
    ("Curitiba", "PR"): (-25.4195, -49.2646),
    ("Foz do Iguaçu", "PR"): (-25.5427, -54.5827),
    ("Londrina", "PR"): (-23.3040, -51.1691),
    ("Maringá", "PR"): (-23.4205, -51.9333),
    ("Ponta Grossa", "PR"): (-25.0916, -50.1668),
    ("São José dos Pinhais", "PR"): (-25.5313, -49.2031),
    ("Belford Roxo", "RJ"): (-22.7640, -43.3992),
    ("Niteroi", "RJ"): (-22.8832, -43.1034),
    ("Niterói", "RJ"): (-22.8832, -43.1034),
    ("Nova Iguaçu", "RJ"): (-22.7556, -43.4603),
    ("Rio de Janeiro", "RJ"): (-22.9129, -43.2003),
    ("São Gonçalo", "RJ"): (-22.8268, -43.0634),
    ("São João de Meriti", "RJ"): (-22.8058, -43.3729),
    ("Natal", "RN"): (-5.7936, -35.1986),
    ("Porto Velho", "RO"): (-8.7608, -63.8999),
    ("Bento Gonçalves", "RS"): (-29.1662, -51.5165),
    ("Canoas", "RS"): (-29.9128, -51.1857),
    ("Caxias do Sul", "RS"): (-29.1629, -51.1792),
    ("Gravataí", "RS"): (-29.9413, -50.9869),
    ("Novo Hamburgo", "RS"): (-29.6875, -51.1328),
    ("Passo Fundo", "RS"): (-28.2576, -52.4091),
    ("Pelotas", "RS"): (-31.7649, -52.3371),
    ("Porto Alegre", "RS"): (-30.0318, -51.2065),
    ("Rio Grande", "RS"): (-32.0349, -52.1071),
    ("Santa Maria", "RS"): (-29.6868, -53.8149),
    ("São Leopoldo", "RS"): (-29.7545, -51.1498),
    ("Viamão", "RS"): (-30.0819, -51.0194),
    ("Balneário Camboriú", "SC"): (-26.9926, -48.6352),
    ("Blumenau", "SC"): (-26.9155, -49.0709),
    ("Brusque", "SC"): (-27.0977, -48.9107),
    ("Chapecó", "SC"): (-27.1004, -52.6152),
    ("Criciuma", "SC"): (-28.6723, -49.3729),
    ("Florianópolis", "SC"): (-27.5945, -48.5477),
    ("Itajaí", "SC"): (-26.9101, -48.6705),
    ("Joinville", "SC"): (-26.3045, -48.8487),
    ("São José", "SC"): (-27.6136, -48.6366),
    ("Aracaju", "SE"): (-10.9091, -37.0677),
    ("Americana", "SP"): (-22.7374, -47.3331),
    ("Araraquara", "SP"): (-21.7845, -48.1780),
    ("Araçatuba", "SP"): (-21.2076, -50.4401),
    ("Aruja", "SP"): (-23.3965, -46.3200),
    ("Atibaia", "SP"): (-23.1171, -46.5563),
    ("Barretos", "SP"): (-20.5531, -48.5698),
    ("Barueri", "SP"): (-23.5057, -46.8790),
    ("Bauru", "SP"): (-22.3246, -49.0871),
    ("Birigui", "SP"): (-21.2910, -50.3432),
    ("Botucatu", "SP"): (-22.8837, -48.4437),
    ("Bragança Paulista", "SP"): (-22.9527, -46.5419),
    ("Campinas", "SP"): (-22.9053, -47.0659),
    ("Caraguatatuba", "SP"): (-23.6125, -45.4125),
    ("Carapicuiba", "SP"): (-23.5235, -46.8407),
    ("Carapicuíba", "SP"): (-23.5235, -46.8407),
    ("Cotia", "SP"): (-23.6022, -46.9190),
    ("Diadema", "SP"): (-23.6813, -46.6205),
    ("Embu das Artes", "SP"): (-23.6437, -46.8579),
    ("Ferraz de Vasconcelos", "SP"): (-23.5411, -46.3710),
    ("Franca", "SP"): (-20.5352, -47.4039),
    ("Guarujá", "SP"): (-23.9888, -46.2580),
    ("Guarulhos", "SP"): (-23.4538, -46.5333),
    ("Hortolândia", "SP"): (-22.8529, -47.2143),
    ("Indaiatuba", "SP"): (-23.0816, -47.2101),
    ("Itanhaém", "SP"): (-24.1736, -46.7880),
    ("Itapecerica da Serra", "SP"): (-23.7161, -46.8572),
    ("Itapetininga", "SP"): (-23.5886, -48.0483),
    ("Itaquaquecetuba", "SP"): (-23.4835, -46.3457),
    ("Itatiba", "SP"): (-23.0035, -46.8464),
    ("Itu", "SP"): (-23.2544, -47.2927),
    ("Jacarei", "SP"): (-23.2983, -45.9658),
    ("Jacareí", "SP"): (-23.2983, -45.9658),
    ("Jandira", "SP"): (-23.5275, -46.9023),
    ("Jaú", "SP"): (-22.2936, -48.5592),
    ("Jundiaí", "SP"): (-23.1852, -46.8974),
    ("Limeira", "SP"): (-22.5660, -47.3970),
    ("Marilia", "SP"): (-22.2171, -49.9501),
    ("Marília", "SP"): (-22.2171, -49.9501),
    ("Mauá", "SP"): (-23.6677, -46.4613),
    ("Mogi Guaçu", "SP"): (-22.3675, -46.9428),
    ("Mogi das Cruzes", "SP"): (-23.5208, -46.1854),
    ("Osasco", "SP"): (-23.5324, -46.7916),
    ("Paulinia", "SP"): (-22.7542, -47.1488),
    ("Pindamonhangaba", "SP"): (-22.9246, -45.4613),
    ("Piracicaba", "SP"): (-22.7338, -47.6476),
    ("Praia Grande", "SP"): (-24.0084, -46.4121),
    ("Presidente Prudente", "SP"): (-22.1207, -51.3925),
    ("Ribeirão Preto", "SP"): (-21.1699, -47.8099),
    ("Rio Claro", "SP"): (-22.3984, -47.5546),
    ("Salto", "SP"): (-23.1996, -47.2931),
    ("Santo André", "SP"): (-23.6737, -46.5432),
    ("Santos", "SP"): (-23.9535, -46.3350),
    ("Sorocaba", "SP"): (-23.4969, -47.4451),
    ("Sumaré", "SP"): (-22.8204, -47.2728),
    ("Suzano", "SP"): (-23.5448, -46.3112),
    ("São Bernardo do Campo", "SP"): (-23.6914, -46.5646),
    ("São Caetano do Sul", "SP"): (-23.6229, -46.5548),
    ("São Carlos", "SP"): (-22.0174, -47.8860),
    ("São José do Rio Preto", "SP"): (-20.8113, -49.3758),
    ("São José dos Campos", "SP"): (-23.1896, -45.8841),
    ("São Paulo", "SP"): (-23.5329, -46.6395),
    ("São Vicente", "SP"): (-23.9574, -46.3883),
    ("Taboão da Serra", "SP"): (-23.6019, -46.7526),
    ("Tatuí", "SP"): (-23.3487, -47.8461),
    ("Taubate", "SP"): (-23.0104, -45.5593),
    ("Valinhos", "SP"): (-22.9698, -46.9974),
    ("Vinhedo", "SP"): (-23.0302, -46.9833),
    ("Votorantim", "SP"): (-23.5446, -47.4388),
    ("Palmas", "TO"): (-10.2400, -48.3558),
    ("S. C. do Sul", "SP"): (-23.6229, -46.5548),             # São Caetano do Sul
    ("S. J. Rio Preto", "SP"): (-20.8113, -49.3758),          # São José do Rio Preto
    ("Santa Barbara", "SP"): (-22.7553, -47.4143),            # Santa Bárbara d'Oeste
    ("Santa Bárbara d´Oeste", "SP"): (-22.7553, -47.4143),
    ("Cuibá", "MT"): (-15.6010, -56.0974),                    # Cuiabá
    ("Riviera de São Lourenço", "SP"): (-23.8486, -46.1396),  # bairro de Bertioga
    ("Planaltina", "DF"): (-15.6200, -47.6500),               # região administrativa do DF
    ("Brasília", "SP"): (-15.7795, -47.9297),                 # UF errada na planilha (loja do DF)
}

PASSO_ESPIRAL = 0.045            # graus entre lojas vizinhas da mesma cidade
ANGULO_DOURADO = math.pi * (3 - math.sqrt(5))
TAMANHO_MAX_PX = 30              # diâmetro da maior loja


def _chave(texto):
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return texto.lower().replace("-", " ").replace("'", "").replace("´", "").strip()


_COORD_NORMALIZADA = {(_chave(c), uf): xy for (c, uf), xy in COORDENADAS.items()}


def posicionar_lojas(lojas):
    """Devolve a lista de lojas com lat/lon (espiral por cidade). Lojas sem coordenada ficam de fora
    e são listadas em .attrs['sem_coordenada']."""
    df = lojas.copy()
    xy = [_COORD_NORMALIZADA.get((_chave(c), str(u).upper())) for c, u in zip(df["cidade"], df["uf"])]
    df["lat_cidade"] = [p[0] if p else None for p in xy]
    df["lon_cidade"] = [p[1] if p else None for p in xy]
    sem = df[df["lat_cidade"].isna()][["cidade", "uf"]].drop_duplicates()
    df = df.dropna(subset=["lat_cidade"]).copy()

    # ordem dentro da cidade: maiores primeiro, no centro
    df = df.sort_values(["lat_cidade", "lon_cidade", "area_m2"], ascending=[True, True, False])
    i = df.groupby(["lat_cidade", "lon_cidade"]).cumcount()
    raio = PASSO_ESPIRAL * i.pow(0.5)
    ang = i * ANGULO_DOURADO
    df["lat"] = df["lat_cidade"] + raio * ang.map(math.sin)
    df["lon"] = df["lon_cidade"] + raio * ang.map(math.cos) / df["lat_cidade"].map(lambda la: math.cos(math.radians(la)))
    df = df.reset_index(drop=True)
    df.attrs["sem_coordenada"] = sem
    return df


def grafico_bolhas_lojas(lojas, titulo="Lojas Petz e Cobasi no Brasil", altura=620):
    """Mapa de bolhas: cada bolha é uma loja, cor pela bandeira e tamanho pela área (m²)."""
    df = posicionar_lojas(lojas)
    area_max = df["area_m2"].max()
    sizeref = 2.0 * area_max / (TAMANHO_MAX_PX ** 2)

    fig = go.Figure()
    for bandeira in ["Petz", "Cobasi"]:
        parte = df[df["bandeira"].str.casefold() == bandeira.casefold()]
        if parte.empty:
            continue
        area_txt = [_br(a, 0) for a in parte["area_m2"]]
        fig.add_trace(go.Scattergeo(
            lat=parte["lat"], lon=parte["lon"], mode="markers",
            name=f"{bandeira}: {len(parte)} lojas ",
            marker=dict(size=parte["area_m2"], sizemode="area", sizeref=sizeref, sizemin=3,
                        color=COR_EMPRESA[bandeira], opacity=0.65, line=dict(width=0.6, color="white")),
            customdata=list(zip(parte["nome"], parte["cidade"], parte["uf"], area_txt)),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} – %{customdata[2]}"
                          "<br>Área: %{customdata[3]} m²<extra>" + bandeira + "</extra>",
        ))

    fig.update_geos(
        scope="south america", projection_type="mercator", lataxis_range=[-34.5, 6], lonaxis_range=[-75, -33.5],
        showcountries=True, countrycolor="rgba(29,40,88,.35)", showcoastlines=True, coastlinecolor="rgba(29,40,88,.35)",
        showland=True, landcolor="#F6F4EA", showocean=True, oceancolor="rgba(79,124,172,.06)",
        showlakes=False, showframe=False, bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        title=dict(text=titulo, x=0, xanchor="left",
                   font=dict(family="Outfit, Source Sans 3, sans-serif", size=17, color=MARINHO)) if titulo else None,
        height=altura, margin=dict(l=8, r=8, t=56 if titulo else 10, b=8),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Figtree, Source Sans 3, sans-serif", color=MARINHO, size=13),
        separators=",.", legend=dict(orientation="h", y=-0.02, x=0, title=None, itemsizing="constant"),
        hoverlabel=dict(bgcolor="white", font_color=MARINHO),
    )
    return fig