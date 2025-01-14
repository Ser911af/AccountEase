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

# Función para cargar y preprocesar datos
def cargar_datos(archivo):
    try:
        df = pd.read_excel(archivo, skiprows=7)
        for col in ["Saldo inicial", "Saldo final"]:
            df[col] = (
                df[col]
                .replace({',': '', '.': ''}, regex=True)
                .str.replace('.', '', regex=False)
                .astype(float)
            )
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

# Función para analizar las clases principales
def analizar_variacion(df):
    clases_principales = df[df["Código cuenta contable"].str.startswith(tuple(map(str, range(1, 8))))]
    resumen = (
        clases_principales.groupby("Código cuenta contable")[["Saldo inicial", "Saldo final"]]
        .sum()
        .reset_index()
    )
    resumen["Variación"] = resumen["Saldo final"] - resumen["Saldo inicial"]
    return resumen

# Función para generar un informe con LangChain y Groq
def generar_informe(resumen):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Analiza la tabla proporcionada y genera un informe con las siguientes secciones:
        1. Resumen general de las variaciones.
        2. Clases con mayores aumentos o disminuciones en el saldo.
        3. Observaciones clave sobre patrones o tendencias."""),
        ("user", f"Tabla de datos:\n{resumen.to_string(index=False)}")
    ])
    
    parser = JsonOutputParser(pydantic_object={
        "type": "object",
        "properties": {
            "resumen_general": {"type": "string"},
            "clases_relevantes": {"type": "array", "items": {"type": "string"}},
            "observaciones_clave": {"type": "string"}
        }
    })
    
    chain = prompt | llm | parser
    result = chain.invoke({})
    return result

# Interfaz con Streamlit
st.title("Análisis de Variaciones en Cuentas Contables")
uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if uploaded_file:
    datos = cargar_datos(uploaded_file)
    if datos is not None:
        st.markdown("### Datos cargados:")
        st.dataframe(datos.head())

        resumen_variacion = analizar_variacion(datos)
        st.markdown("### Resumen de variaciones por clase:")
        st.dataframe(resumen_variacion)

        if st.button("Generar Informe"):
            with st.spinner("Generando informe..."):
                informe = generar_informe(resumen_variacion)
                st.markdown("### Informe generado:")
                st.json(informe)
