import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

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
    "Sube tu archivo Excel con los datos", type=["xlsx", "xls", "csv"]
)

# 1. SI NO HAY ARCHIVO CARGADO: Inicializamos todo en 0 para evitar datos falsos
if archivo_cargado is None:
    st.sidebar.info(
        "👆 Sube tu archivo Excel para poblar el panel automáticamente."
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
  if archivo_cargado.name.endswith(".csv"):
    df_datos = pd.read_csv(archivo_cargado)
  else:
    df_datos = pd.read_excel(archivo_cargado)
  st.sidebar.success("¡Datos cargados con éxito desde el archivo!")


# Función auxiliar segura para extraer valores del DataFrame
def obtener_valor(df, concepto):
  try:
    resultado = df[
        df.iloc[:, 0]
        .astype(str)
        .str.upper()
        .str.contains(concepto.upper(), na=False)
    ]
    if not resultado.empty:
      val = resultado.iloc[0, 1]
      return float(val) if pd.notnull(val) else 0.0
  except Exception:
    pass
  return 0.0


# Extracción de métricas clave
facturacion_actual = obtener_valor(df_datos, "FACTURACION MES EN CURSO")
total_por_cobrar = obtener_valor(df_datos, "TOTAL POR COBRAR")
total_por_pagar = obtener_valor(df_datos, "TOTAL POR PAGAR")
gastos_fijos = obtener_valor(df_datos, "GASTOS FIJOS")

# --- 1. TARJETAS KPI SUPERIORES ---
col1, col2, col3, col4 = st.columns(4)

with col1:
  st.metric(label="FACTURACIÓN ACTUAL", value=f"${facturacion_actual:,.0f}")
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
      obtener_valor(df_datos, "COBROS ESTIMADOS 10 DIAS"),
      obtener_valor(df_datos, "COBROS ESTIMADOS 20 DIAS"),
      obtener_valor(df_datos, "COBROS ESTIMADOS 30 DIAS"),
      obtener_valor(df_datos, "COBROS ESTIMADOS +30 DIAS"),
  ]
  pagos = [
      obtener_valor(df_datos, "CH EMITIDOS 10 DIAS"),
      obtener_valor(df_datos, "CH EMITIDOS 20 DIAS"),
      obtener_valor(df_datos, "CH EMITIDOS 30 DIAS"),
      obtener_valor(df_datos, "CH EMITIDOS +30 DIAS"),
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

  ax.set_xticks(x)
  ax.set_xticklabels(dias, fontsize=11, fontweight="bold", color="#1e293b")
  ax.tick_params(axis="y", labelsize=11, labelcolor="#1e293b")
  ax.legend(fontsize=11, loc="upper right", frameon=True, facecolor="#f8fafc")
  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)

  plt.tight_layout()
  st.pyplot(fig)

with col_right:
  st.subheader("2. Resumen Anual y Facturación Histórica")

  categorias = ["Año Anterior", "Año Actual"]
  valores_anuales = [
      obtener_valor(df_datos, "FACTURACION TOTAL ANUAL ANTERIOR") / 1000,
      obtener_valor(df_datos, "FACTURACION TOTAL ACUMULADA ANUAL") / 1000,
  ]
  valores_reales = [
      obtener_valor(df_datos, "FACTURACION TOTAL ANUAL ANTERIOR"),
      obtener_valor(df_datos, "FACTURACION TOTAL ACUMULADA ANUAL"),
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
    val = obtener_valor(df_datos, b)
    bancos_filas.append({"Cuenta / Concepto": b, "Saldo ($)": f"${val:,.0f}"})
  st.dataframe(
      pd.DataFrame(bancos_filas), hide_index=True, use_container_width=True
  )

with col_rentabilidad:
  st.subheader("4. Rentabilidad y Estructura de Gastos")
  st.markdown(
      f"- **Facturación Mes Anterior:**"
      f" **${obtener_valor(df_datos, 'FACTURACION MES ANTERIOR'):,.0f}**"
  )
  st.markdown(
      f"- **Pedidos Pendientes (OC):**"
      f" **${obtener_valor(df_datos, 'PEDIDOS PENDIENTES VALORIZADO'):,.0f}**"
  )
  st.markdown(
      f"- **Punto de Equilibrio:**"
      f" **${obtener_valor(df_datos, 'PUNTO EQUILIBRIO'):,.0f}**"
  )
  st.markdown(
      f"- **Rentabilidad Neta ($):**"
      f" **${obtener_valor(df_datos, 'RENTABILIDAD $'):,.0f}**"
  )