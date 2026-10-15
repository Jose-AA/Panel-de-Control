import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import io
import unicodedata
import re

# Configuración de la página
st.set_page_config(
    page_title="Panel de Control Financiero", page_icon="📈", layout="wide"
)

st.title("📊 Panel de Control Financiero")
st.markdown(
    "**Enfoque:** Facturación, Cobros Pendientes, Deudas, Gastos y Tesorería"
)
st.divider()

# --- BARRA LATERAL PARA CARGAR EL EXCEL ---
st.sidebar.header("📁 Carga de Datos")
archivo_cargado = st.sidebar.file_uploader(
    "Sube tu archivo Excel o CSV con los datos", type=["xlsx", "xls", "csv"]
)

# Utilidades de normalización y parseo

def normalize_text(s: str) -> str:
    """Normaliza texto: mayúsculas, quitar acentos, signos y espacios extra."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    # quitar acentos
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # upper, quitar caracteres no alfanuméricos salvo espacios
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_monetary(val) -> float:
    """Convierte distintos formatos monetarios a float de forma robusta.

    Maneja: valores numéricos, strings con $ y separadores de miles ('.') y decimales (',').
    Si hay ambos '.' y ',' se asume que el separador más a la derecha es el decimal.
    También soporta paréntesis para negativos.
    """
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        try:
            return float(val)
        except Exception:
            return 0.0

    s = str(val).strip()
    if s == "":
        return 0.0

    # tratar paréntesis como negativo
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]

    # quitar moneda y espacios
    s = s.replace("$", "").replace("USD", "").replace("AR$", "")
    s = s.replace(" ", "")

    # si hay letras residuales, quitarlas salvo , . -
    s = re.sub(r"[^0-9,\.\-]", "", s)

    # si hay tanto '.' como ',' decidir según el separador más a la derecha
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            # coma como decimal
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            # punto como decimal
            s = s.replace(",", "")
    else:
        # solo coma
        if "," in s and s.count(",") == 1 and len(s.split(",")[-1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    # dejar solo dígitos, punto y signo menos
    s = re.sub(r"[^0-9\.-]", "", s)

    try:
        num = float(s) if s not in ["", ".", "-"] else 0.0
    except Exception:
        num = 0.0

    if negative:
        num = -num
    return num


@st.cache_data
def cargar_datos_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Carga el archivo desde bytes y devuelve un DataFrame crudo.

    - Para CSV intenta autodetección de separador y también prueba con 'latin-1' si falla.
    - Para Excel usa pandas.read_excel directamente.
    """
    bio = io.BytesIO(file_bytes)
    lname = filename.lower()
    if lname.endswith(".csv"):
        # intentar con engine python para detección automática
        try:
            df = pd.read_csv(bio, sep=None, engine="python")
            return df
        except Exception:
            # reintentar con diferentes encodings
            bio.seek(0)
            try:
                df = pd.read_csv(bio, sep=";", encoding="latin-1")
                return df
            except Exception:
                bio.seek(0)
                df = pd.read_csv(bio, encoding="utf-8", errors="replace")
                return df
    else:
        # Excel
        bio.seek(0)
        df = pd.read_excel(bio)
        return df


# 1. SI NO HAY ARCHIVO CARGADO: Inicializamos todo en 0 para evitar datos falsos
if archivo_cargado is None:
    st.sidebar.info(
        "👆 Sube tu archivo Excel o CSV para poblar el panel automáticamente."
    )
    df_datos = pd.DataFrame(
        {
            "Concepto": [
                "FACTURACION MES EN CURSO",
                "TOTAL POR COBRAR",
                "TOTAL POR PAGAR",
                "GASTOS FIJOS",
                "COBROS ESTIMADOS 10 DIAS",
                "COBROS ESTIMADOS 20 DIAS",
                "COBROS ESTIMADOS 30 DIAS",
                "COBROS ESTIMADOS +30 DIAS",
                "CH EMITIDOS 10 DIAS",
                "CH EMITIDOS 20 DIAS",
                "CH EMITIDOS 30 DIAS",
                "CH EMITIDOS +30 DIAS",
                "FACTURACION TOTAL ACUMULADA ANUAL",
                "FACTURACION TOTAL ANUAL ANTERIOR",
                "BANCO GALICIA",
                "FONDO COMUN",
                "BANCO PROV.",
                "BANCO CREDICOOP",
                "CH CARTERA",
                "FACTURACION MES ANTERIOR",
                "PEDIDOS PENDIENTES VALORIZADO",
                "PUNTO EQUILIBRIO",
                "RENTABILIDAD $",
            ],
            "Valor / Dato Referencial": [0.0] * 23,
        }
    )
else:
    # Leer bytes (se usa getvalue para poder reintentar sin problemas de puntero)
    file_bytes = archivo_cargado.getvalue()
    try:
        df_datos = cargar_datos_bytes(file_bytes, archivo_cargado.name)
        st.sidebar.success("¡Datos cargados con éxito desde el archivo!")
    except Exception as e:
        st.sidebar.error(f"Error al leer el archivo: {e}")
        df_datos = pd.DataFrame(columns=["Concepto", "Valor / Dato Referencial"])


# Normalizar y detectar columnas de 'concepto' y 'valor'
concept_col = None
value_col = None
if not df_datos.empty:
    cols = list(df_datos.columns)
    norm_cols = [normalize_text(c) for c in cols]

    # tratar casos comunes
    for i, nc in enumerate(norm_cols):
        if "CONCEP" in nc or nc.startswith("CON") or nc in ["DESCRIPCION", "ITEM", "DETALLE"]:
            concept_col = cols[i]
            break

    # buscar columna de valor
    for i, nc in enumerate(norm_cols):
        if any(k in nc for k in ["VALOR", "MONTO", "IMPORTE", "SALDO", "CANTIDAD", "TOTAL"]):
            value_col = cols[i]
            break

    # heurística: si solo hay 2 columnas, usamos 0 y 1
    if concept_col is None or value_col is None:
        if len(cols) == 2:
            concept_col = cols[0]
            value_col = cols[1]
        else:
            # fallback: primera columna como concepto, la columna numérica más cercana como valor
            if concept_col is None:
                concept_col = cols[0]
            if value_col is None:
                # buscar columna numérica
                for i, c in enumerate(cols[1:], start=1):
                    sample = df_datos[c].dropna().astype(str)
                    # si la columna contiene mayoritariamente dígitos o símbolos monetarios
                    if sample.apply(lambda s: bool(re.search(r"[0-9]", s))).mean() > 0.5:
                        value_col = c
                        break

    # si seguimos sin value_col, crear una columna con 0.0
    if value_col is None:
        df_datos["_VALOR_GENERADO"] = 0.0
        value_col = "_VALOR_GENERADO"

# Construir DataFrame de lookup con columnas normalizadas
lookup_df = pd.DataFrame(columns=["concepto_norm", "valor_num", "concepto_raw"]) 
if not df_datos.empty:
    for idx, row in df_datos.iterrows():
        try:
            raw_concept = row[concept_col]
        except Exception:
            raw_concept = ""
        try:
            raw_val = row[value_col]
        except Exception:
            raw_val = 0.0
        cn = normalize_text(raw_concept)
        vn = parse_monetary(raw_val)
        lookup_df = lookup_df.append(
            {"concepto_norm": cn, "valor_num": vn, "concepto_raw": raw_concept},
            ignore_index=True,
        )


# Función segura para obtener valor por concepto
missing_concepts_shown = set()

def obtener_valor(df_lookup: pd.DataFrame, concepto: str) -> float:
    """Busca el concepto de forma normalizada. Prioriza coincidencia exacta, luego contains.

    Devuelve 0.0 si nada se encuentra.
    También muestra un aviso en la sidebar la primera vez que un concepto no se encuentra.
    """
    if df_lookup is None or df_lookup.empty:
        return 0.0
    key = normalize_text(concepto)

    # coincidencia exacta
    exact = df_lookup[df_lookup["concepto_norm"] == key]
    if not exact.empty:
        return float(exact.iloc[0]["valor_num"]) if pd.notnull(exact.iloc[0]["valor_num"]) else 0.0

    # coincidencia contiene
    contains = df_lookup[df_lookup["concepto_norm"].str.contains(key, na=False)]
    if not contains.empty:
        return float(contains.iloc[0]["valor_num"]) if pd.notnull(contains.iloc[0]["valor_num"]) else 0.0

    # intentar búsqueda por palabras claves (split key)
    parts = [p for p in key.split() if len(p) > 2]
    if parts:
        mask = df_lookup["concepto_norm"].apply(lambda x: all(p in x for p in parts))
        found = df_lookup[mask]
        if not found.empty:
            return float(found.iloc[0]["valor_num"]) if pd.notnull(found.iloc[0]["valor_num"]) else 0.0

    # si no encuentra, mostrar advertencia una vez por concepto
    if key not in missing_concepts_shown:
        st.sidebar.warning(f"No se encontró el concepto exacto: '{concepto}'. Se usará 0.0 como valor por defecto.")
        missing_concepts_shown.add(key)
    return 0.0


# Extracción de métricas clave
facturacion_actual = obtener_valor(lookup_df, "FACTURACION MES EN CURSO")
total_por_cobrar = obtener_valor(lookup_df, "TOTAL POR COBRAR")
total_por_pagar = obtener_valor(lookup_df, "TOTAL POR PAGAR")
gastos_fijos = obtener_valor(lookup_df, "GASTOS FIJOS")

# --- 1. TARJETAS KPI SUPERIORES ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="FACTURACIÓN MES EN CURSO", value=f"${facturacion_actual:,.0f}")
with col2:
    st.metric(label="TOTAL POR COBRAR", value=f"${total_por_cobrar:,.0f}")
with col3:
    st.metric(
        label="TOTAL POR PAGAR",
        value=f"${total_por_pagar:,.0f}",
        delta_color="inverse",
    )
with col4:
    st.metric(label="GASTOS FIJOS", value=f"${gastos_fijos:,.0f}")

st.markdown("")

# --- 2. BLOQUE CENTRAL: GRÁFICOS CON FUENTES GRANDES Y OSCURAS ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("1. Flujo de Caja: Cobros vs Pagos (Plazos)")

    dias = ["10 Días", "20 Días", "30 Días", "+30 Días"]
    cobros = [
        obtener_valor(lookup_df, "COBROS ESTIMADOS 10 DIAS"),
        obtener_valor(lookup_df, "COBROS ESTIMADOS 20 DIAS"),
        obtener_valor(lookup_df, "COBROS ESTIMADOS 30 DIAS"),
        obtener_valor(lookup_df, "COBROS ESTIMADOS +30 DIAS"),
    ]
    pagos = [
        obtener_valor(lookup_df, "CH EMITIDOS 10 DIAS"),
        obtener_valor(lookup_df, "CH EMITIDOS 20 DIAS"),
        obtener_valor(lookup_df, "CH EMITIDOS 30 DIAS"),
        obtener_valor(lookup_df, "CH EMITIDOS +30 DIAS"),
    ]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(dias))
    width = 0.35

    ax.bar(
        [p - width / 2 for p in x],
        cobros,
        width,
        label="Cobros Est. ($)",
        color="#16a34a",
    )
    ax.bar(
        [p + width / 2 for p in x],
        pagos,
        width,
        label="Cheques Emitidos ($)",
        color="#dc2626",
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(dias, fontsize=12, fontweight="bold", color="#1e293b")
    ax.tick_params(axis="y", labelsize=12, labelcolor="#1e293b")
    ax.legend(fontsize=11, loc="upper right", frameon=True, facecolor="#f8fafc")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    st.pyplot(fig)

with col_right:
    st.subheader("2. Resumen Anual y Facturación Histórica")

    categorias = ["Año Anterior", "Año Actual"]
    valores_anuales = [
        obtener_valor(lookup_df, "FACTURACION TOTAL ANUAL ANTERIOR") / 1000,
        obtener_valor(lookup_df, "FACTURACION TOTAL ACUMULADA ANUAL") / 1000,
    ]
    valores_reales = [
        obtener_valor(lookup_df, "FACTURACION TOTAL ANUAL ANTERIOR"),
        obtener_valor(lookup_df, "FACTURACION TOTAL ACUMULADA ANUAL"),
    ]

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    barras = ax2.bar(
        categorias, valores_anuales, color=["#94a3b8", "#2563eb"], width=0.4
    )

    for barra, val_real in zip(barras, valores_reales):
        altura = barra.get_height()
        ax2.text(
            barra.get_x() + barra.get_width() / 2,
            altura + (max(valores_anuales) * 0.02 if max(valores_anuales) > 0 else 5),
            f"${val_real:,.0f}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color="#1e293b",
        )

    ax2.set_ylabel(
        "Miles de ($)", fontsize=10, fontweight="bold", color="#1e293b"
    )
    ax2.tick_params(axis="x", labelsize=11, labelcolor="#1e293b")
    ax2.tick_params(axis="y", labelsize=11, labelcolor="#1e293b")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.set_ylim(0, max(valores_anuales) * 1.25 if max(valores_anuales) > 0 else 100)

    plt.tight_layout()
    st.pyplot(fig2)

st.divider()

# --- 3. BLOQUE INFERIOR: BANCOS Y RENTABILIDAD ---
col_bancos, col_rentabilidad = st.columns(2)

with col_bancos:
    st.subheader("3. Disponibilidad Bancaria y Liquidez")
    bancos_nombres = [
        "BANCO GALICIA",
        "FONDO COMUN",
        "BANCO PROV.",
        "BANCO CREDICOOP",
        "CH CARTERA",
    ]
    bancos_filas = []
    for b in bancos_nombres:
        val = obtener_valor(lookup_df, b)
        bancos_filas.append({"Cuenta / Concepto": b, "Saldo ($)": f"${val:,.0f}"})
    st.dataframe(pd.DataFrame(bancos_filas), hide_index=True, use_container_width=True)

with col_rentabilidad:
    st.subheader("4. Rentabilidad y Estructura de Gastos")
    st.markdown(
        f"- **Facturación Mes Anterior:**"
        f" **${obtener_valor(lookup_df, 'FACTURACION MES ANTERIOR'):,.0f}**"
    )
    st.markdown(
        f"- **Pedidos Pendientes (OC):**"
        f" **${obtener_valor(lookup_df, 'PEDIDOS PENDIENTES VALORIZADO'):,.0f}**"
    )
    st.markdown(
        f"- **Punto de Equilibrio:**"
        f" **${obtener_valor(lookup_df, 'PUNTO EQUILIBRIO'):,.0f}**"
    )
    st.markdown(
        f"- **Rentabilidad Neta ($):**"
        f" **${obtener_valor(lookup_df, 'RENTABILIDAD $'):,.0f}**"
    )
