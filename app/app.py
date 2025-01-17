import pandas as pd
import streamlit as st
from groq import Groq  # Asegúrate de que esta librería esté instalada

# Nueva función para leer la información de la empresa
def leer_informacion_empresa(archivo):
    """
    Lee la información de la empresa desde las primeras 7 filas del archivo Excel.

    Args:
        archivo: El archivo Excel cargado.

    Returns:
        dict: Un diccionario con la información de la empresa, incluyendo nombre y periodo.
    """
    try:
        # Leer las primeras 7 filas del archivo Excel sin encabezados
        info_empresa_df = pd.read_excel(archivo, nrows=7, header=None)

        # Extraer información clave
        informacion = {
            "Título": info_empresa_df.iloc[0, 0],  # Primera fila, columna 1
            "Nombre Empresa": info_empresa_df.iloc[1, 0],  # Segunda fila, columna 1
            "NIT": info_empresa_df.iloc[2, 0],  # Tercera fila, columna 1
            "Periodo": info_empresa_df.iloc[3, 0],  # Cuarta fila, columna 1
        }

        return informacion
    except Exception as e:
        # Manejar errores al leer la información
        st.error(f"Error al leer la información de la empresa: {e}")
        return None

# Función para cargar y limpiar datos
def cargar_y_limpiar_datos(archivo):
    try:
        # Leer el archivo Excel desde la fila 8
        df = pd.read_excel(archivo, skiprows=7, usecols="A:K")
        
        # Seleccionar solo columnas relevantes
        columnas_relevantes = ["Nivel", "Transaccional", "Código cuenta contable", "Nombre cuenta contable", 
                               "Identificación", "Nombre tercero", "Saldo inicial", "Movimiento débito", "Movimiento crédito", "Saldo final"]
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
    resumen["Variación %"] = ((resumen["Variación Total"] / resumen["Saldo inicial"].replace(0, pd.NA)) * 100)
    
    # Manejar valores nulos y redondear
    resumen["Variación %"] = resumen["Variación %"].fillna(0).round(0).astype(int)
    resumen["Saldo inicial"] = resumen["Saldo inicial"].round(0).astype(int)
    resumen["Saldo final"] = resumen["Saldo final"].round(0).astype(int)
    resumen["Variación Total"] = resumen["Variación Total"].round(0).astype(int)

    return resumen

# Función para analizar ponderación de subcuentas en la cuenta 1305 
def analizar_ponderacion_subcuentas(df):
    subcuentas = df[df["Código cuenta contable"].str.startswith("1305")].copy()
    saldo_final_principal = subcuentas.iloc[0]["Saldo final"]
    subcuentas["Porcentaje contribución"] = (
        subcuentas["Saldo final"] / saldo_final_principal * 100
    )
    subcuentas["Saldo final"] = subcuentas["Saldo final"].round(0)
    subcuentas["Porcentaje contribución"] = subcuentas["Porcentaje contribución"].round(2)
    resultado = subcuentas[["Código cuenta contable", "Nombre tercero", "Saldo final", "Porcentaje contribución"]]
    resultado = resultado.sort_values(by="Porcentaje contribución", ascending=False)
    return resultado
   
# Generar informe con Groq
def generar_informe(resumen_variacion, ponderacion_subcuentas, info_empresa):
    st.markdown("### Informe generado automáticamente:")
    try:
        client = Groq()

        resumen_variacion_datos = resumen_variacion.to_string(index=False)
        ponderacion_subcuentas_datos = ponderacion_subcuentas.to_string(index=False)

        nombre_empresa = info_empresa.get("Nombre Empresa", "Información no disponible")
        periodo = info_empresa.get("Periodo", "Información no disponible")

        prompt = (
            f"Eres un asistente financiero. Aquí tienes un resumen de las variaciones por clase y la ponderación de las subcuentas en la cuenta 1305:\n"
            f"Empresa: {nombre_empresa}\n"
            f"Periodo: {periodo}\n\n"
            f"Variaciones por clase:\n{resumen_variacion_datos}\n\n"
            f"Ponderación de subcuentas en la cuenta 1305:\n{ponderacion_subcuentas_datos}\n\n"
            "Tu tarea es generar un informe que destaque lo siguiente:\n"
            "1. Resumen general de las variaciones totales y porcentuales de las clases.\n"
            "2. Ponderación de las subcuentas más importantes dentro de la cuenta 1305.\n"
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
    info_empresa = leer_informacion_empresa(uploaded_file)
    datos = cargar_y_limpiar_datos(uploaded_file)
    if datos is not None:
        st.markdown("### Datos cargados:")
        st.dataframe(datos.head())

        # Análisis de variaciones por clase
        resumen_variacion = analizar_clases(datos)
        st.markdown("### Resumen de variaciones por clase:")
        st.dataframe(resumen_variacion)

        # Análisis de ponderación de subcuentas en la cuenta 1305
        ponderacion_subcuentas = analizar_ponderacion_subcuentas(datos)
        st.markdown("### Ponderación de subcuentas en la cuenta 1305:")
        st.dataframe(ponderacion_subcuentas)

        # Botón para generar el informe
        if st.button("Generar Informe"):
            generar_informe(resumen_variacion, ponderacion_subcuentas, info_empresa)
