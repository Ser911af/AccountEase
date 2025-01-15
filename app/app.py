import pandas as pd
import streamlit as st
from groq import Groq  # Asegúrate de que esta librería esté instalada

# Función para cargar y limpiar datos
def cargar_y_limpiar_datos(archivo):
    try:
        # Leer el archivo Excel desde la fila 8
        df = pd.read_excel(archivo, skiprows=7, usecols="A:K")
        
        # Seleccionar solo columnas relevantes
        columnas_relevantes = ["Nivel", "Transaccional", "Código cuenta contable", "Nombre cuenta contable", 
                               "Identificación", "Saldo inicial", "Movimiento débito", "Movimiento crédito", "Saldo final"]
        df = df[columnas_relevantes]

        # Convertir columnas relevantes a strings donde aplique
        columnas_a_convertir = ["Nivel", "Transaccional", "Código cuenta contable", "Nombre cuenta contable", "Identificación"]
        for columna in columnas_a_convertir:
            df[columna] = df[columna].astype(str)
        
        # Asegurar que las columnas numéricas estén correctamente formateadas
        columnas_numericas = ["Saldo inicial", "Movimiento débito", "Movimiento crédito", "Saldo final"]
        for columna in columnas_numericas:
            df[columna] = pd.to_numeric(df[columna], errors="coerce")

        return df
    except Exception as e:
        st.error(f"Error al cargar y limpiar los datos: {e}")
        return None

# Función para analizar variaciones por clase con formato ajustado
def analizar_clases(df):
    clases = df[df["Nivel"] == "Clase"]
    resumen = (
        clases.groupby(["Código cuenta contable", "Nombre cuenta contable"])[["Saldo inicial", "Saldo final"]]
        .sum()
        .reset_index()
    )
    resumen["Variación Total"] = resumen["Saldo final"] - resumen["Saldo inicial"]
    resumen["Variación %"] = (resumen["Variación Total"] / resumen["Saldo inicial"].replace(0, pd.NA)) * 100

    # Ajustar formato: sin decimales para los montos y 2 decimales para porcentajes
    resumen["Saldo inicial"] = resumen["Saldo inicial"].round(0).astype(int)
    resumen["Saldo final"] = resumen["Saldo final"].round(0).astype(int)
    resumen["Variación Total"] = resumen["Variación Total"].round(0).astype(int)
    resumen["Variación %"] = resumen["Variación %"].round(0)

    return resumen

# Generar informe con Groq
def generar_informe(tabla_df):
    st.markdown("### Informe generado automáticamente:")
    try:
        client = Groq()
        resumen_datos = tabla_df.to_string(index=False)
        prompt = (
            f"Eres un asistente financiero. Aquí tienes un resumen de clases con variaciones totales y porcentuales:\n{resumen_datos}\n\n"
            "Tu tarea es generar un informe que destaque lo siguiente:\n"
            "1. Resumen general de las variaciones totales y porcentuales de las clases.\n"
            "2. Listado de las clases con mayor aumento o disminución.\n"
            "3. Observaciones clave relacionadas con las variaciones, sin conclusiones adicionales.\n"
        )

        with st.spinner("Generando el informe, por favor espera..."):
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_tokens=1024,
                top_p=1,
                stream=True,
            )
            informe = ""
            for chunk in completion:
                informe += chunk.choices[0].delta.content or ""
            st.write(informe)
    except Exception as e:
        st.error(f"Error generando el informe: {e}")

# Interfaz con Streamlit
st.title("Análisis de Variaciones en Cuentas Contables")
uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if uploaded_file:
    datos = cargar_y_limpiar_datos(uploaded_file)
    if datos is not None:
        st.markdown("### Datos cargados:")
        st.dataframe(datos.head())

        resumen_variacion = analizar_clases(datos)
        st.markdown("### Resumen de variaciones por clase:")
        st.dataframe(resumen_variacion)

        if st.button("Generar Informe"):
            generar_informe(resumen_variacion)
