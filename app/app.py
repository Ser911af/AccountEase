import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages

# Título de la aplicación
st.title("Análisis Financiero de Cuentas Contables")
st.subheader("Carga tu archivo de cuentas y obtén análisis detallados")

# Subida del archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if uploaded_file:
    try:
        # Leer el archivo Excel desde la fila 8
        df = pd.read_excel(uploaded_file, skiprows=7)

        # Validar columnas necesarias
        required_columns = [
            "Código cuenta contable", "Nombre cuenta contable", "Identificación",
            "Sucursal", "Nombre tercero", "Saldo inicial", "Movimiento débito",
            "Movimiento crédito", "Saldo final"
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"El archivo no contiene las columnas requeridas: {', '.join(missing_columns)}")
        else:
            # Limpieza y conversión de datos
            for col in ["Saldo inicial", "Movimiento débito", "Movimiento crédito", "Saldo final"]:
                df[col] = (
                    df[col]
                    .replace({',': '', '.': ''}, regex=True)
                    .str.replace('.', '', regex=False)
                    .astype(float)
                )

            # Crear columnas derivadas
            df["Movimiento neto"] = df["Movimiento débito"] - df["Movimiento crédito"]
            df["Cambio saldo"] = df["Saldo final"] - df["Saldo inicial"]

            # Mostrar los primeros datos
            st.markdown("### Datos cargados:")
            st.dataframe(df.head())

            # Agrupaciones y Resúmenes
            st.markdown("### Resumen por Niveles:")
            niveles = ["Clase", "Grupo", "Cuenta", "Subcuenta"]
            for nivel in niveles:
                if nivel in df.columns:
                    resumen = (
                        df.groupby(nivel)[["Saldo inicial", "Movimiento débito", "Movimiento crédito", "Saldo final"]]
                        .sum()
                        .reset_index()
                    )
                    st.markdown(f"#### Resumen por {nivel}:")
                    st.dataframe(resumen)

            # Generar gráficos
            st.markdown("### Gráficos:")
            fig, ax = plt.subplots(figsize=(10, 6))
            resumen_nivel = df.groupby("Clase")["Saldo final"].sum().sort_values(ascending=False)
            ax.bar(resumen_nivel.index, resumen_nivel.values, color="skyblue")
            ax.set_title("Saldo final por Clase")
            ax.set_ylabel("Saldo final")
            ax.set_xlabel("Clase")
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
else:
    st.write("Por favor, sube un archivo Excel para comenzar.")
