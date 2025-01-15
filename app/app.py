import pandas as pd
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Inicializar LLM con Groq
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.7
)

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

# Función para analizar variación por clase
def analizar_clases(df):
    clases = df[df["Nivel"] == "Clase"]
    resumen = (
        clases.groupby(["Código cuenta contable", "Nombre cuenta contable"])[["Saldo inicial", "Saldo final"]]
        .sum()
        .reset_index()
    )
    resumen["Variación"] = resumen["Saldo final"] - resumen["Saldo inicial"]
    return resumen

# Función para generar un informe con LangChain y Groq
def generar_informe(resumen):
    # Convertir el resumen a un formato de texto legible para el modelo
    resumen_texto = resumen.to_string(index=False)

    # Crear el prompt para LangChain
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Analiza la tabla proporcionada y genera un informe con las siguientes secciones:
        1. Resumen general de las variaciones.
        2. Clases con mayores aumentos o disminuciones en el saldo.
        3. Observaciones clave sobre patrones o tendencias."""),
        ("user", f"Tabla de datos:\n{resumen_texto}")
    ])
    
    # Configurar el parser de JSON
    parser = JsonOutputParser(pydantic_object={
        "type": "object",
        "properties": {
            "resumen_general": {"type": "string"},
            "clases_relevantes": {"type": "array", "items": {"type": "string"}},
            "observaciones_clave": {"type": "string"}
        }
    })
    
    # Crear la cadena con el LLM y el parser
    chain = prompt | llm | parser
    
    # Generar el resultado
    try:
        result = chain.invoke({})
        return result
    except Exception as e:
        st.error(f"Error al generar el informe: {e}")
        return None

# Interfaz con Streamlit
st.title("Análisis de Variaciones en Clases Contables")
uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if uploaded_file:
    datos = cargar_y_limpiar_datos(uploaded_file)
    if datos is not None:
        st.markdown("### Datos cargados y limpiados:")
        st.dataframe(datos.head())

        # Resumen de variaciones por clase
        resumen_clases = analizar_clases(datos)
        st.markdown("### Resumen de variaciones por clase:")
        st.dataframe(resumen_clases)

        # Generar informe
        if st.button("Generar Informe"):
            with st.spinner("Generando informe..."):
                informe = generar_informe(resumen_clases)
                if informe:
                    st.markdown("### Informe generado:")
                    st.json(informe)

