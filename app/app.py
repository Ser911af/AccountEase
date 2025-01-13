import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages
from groq import Groq

# Título de la aplicación
st.title("DIAN Report Analyzer")
st.subheader("Carga tu reporte DIAN y obtén un análisis detallado del archivo")

# Subida del archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if uploaded_file:
    try:
        # Leer el archivo Excel
        df = pd.read_excel(uploaded_file)

        # Validar columnas necesarias
        required_columns = ["Fecha Emisión", "Total", "IVA", "Tipo de documento", "Grupo"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"El archivo no contiene las columnas requeridas: {', '.join(missing_columns)}")
        else:
            # Convertir y limpiar datos
            df["Fecha Emisión"] = pd.to_datetime(df["Fecha Emisión"], format='%d-%m-%Y', errors="coerce")
            df["Total"] = pd.to_numeric(df["Total"], errors='coerce')
            df["IVA"] = pd.to_numeric(df["IVA"], errors='coerce')
            df["Base"] = (df["Total"].fillna(0) - df["IVA"].fillna(0)).round(0)

            # Extraer el nombre del mes
            month_mapping = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            df["Mes"] = df["Fecha Emisión"].dt.month.map(month_mapping)
            meses_orden = list(month_mapping.values())
            df["Mes"] = pd.Categorical(df["Mes"], categories=meses_orden, ordered=True)

            # Crear tabla consolidada
            tabla_resultados = []
            tipo_documentos = df["Tipo de documento"].unique()
            grados = ["Emitido", "Recibido"]
            for tipo_doc in tipo_documentos:
                for grado in grados:
                    df_filtro = df[(df["Tipo de documento"] == tipo_doc) & (df["Grupo"] == grado)]
                    suma_por_mes = (
                        df_filtro.groupby("Mes")["Base"].sum()
                        .reindex(meses_orden, fill_value=0)
                    )
                    total_anual = suma_por_mes.sum()
                    fila = [tipo_doc, grado] + list(suma_por_mes.values) + [total_anual]
                    tabla_resultados.append(fila)

            columnas = ["Tipo Doc", "Grado"] + meses_orden + ["Total Anual"]
            tabla_df = pd.DataFrame(tabla_resultados, columns=columnas).round(0)

            # Mostrar tabla en la aplicación
            st.markdown("### Tabla consolidada:")
            st.dataframe(tabla_df)

            # Crear gráficos de barras
            st.markdown("### Gráficos de barras: porcentaje relativo del valor por tipo de documento")
            all_figures = []
            for tipo_doc in tipo_documentos:
                fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
                fig.suptitle(f"Porcentaje relativo de {tipo_doc}", fontsize=16)

                for ax, grado in zip(axes, grados):
                    df_filtro = tabla_df[(tabla_df["Tipo Doc"] == tipo_doc) & (tabla_df["Grado"] == grado)]
                    total_anual = df_filtro["Total Anual"].values[0]
                    porcentajes = (df_filtro[meses_orden].values.flatten() / total_anual) * 100

                    ax.bar(meses_orden, porcentajes, color='skyblue', width=0.6)
                    ax.set_title(grado, fontsize=14)
                    ax.set_xlabel("Mes", fontsize=12)
                    ax.set_ylabel("Porcentaje (%)", fontsize=12)
                    ax.set_ylim(0, 100)
                    ax.set_xticklabels(meses_orden, rotation=45)

                    for i, porcentaje in enumerate(porcentajes):
                        ax.text(i, porcentaje + 1, f"{porcentaje:.1f}%", ha='center', va='bottom', fontsize=10)

                st.pyplot(fig)
                all_figures.append(fig)

            # Guardar gráficos en PDF
            def crear_pdf(figures):
                pdf_output = BytesIO()
                with PdfPages(pdf_output) as pdf:
                    for fig in figures:
                        pdf.savefig(fig)
                        plt.close(fig)
                return pdf_output.getvalue()

            pdf_data = crear_pdf(all_figures)
            st.download_button(
                label="Descargar gráficos en PDF",
                data=pdf_data,
                file_name="gráficos_dian.pdf",
                mime="application/pdf"
            )

            # Generar archivo Excel
            @st.cache_data
            def convertir_a_excel(dataframe):
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    dataframe.to_excel(writer, index=False, sheet_name="Resultados")
                return output.getvalue()

            excel_data = convertir_a_excel(tabla_df)
            st.download_button(
                label="Descargar tabla consolidada en Excel",
                data=excel_data,
                file_name="analisis_dian.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Generar informe con Groq
            st.markdown("### Informe generado automáticamente:")
            try:
                client = Groq()
                resumen_datos = tabla_df.to_string(index=False)
                prompt = (
                    f"Genera un informe analítico basado en la siguiente tabla:\n{resumen_datos}\n\n"
                    f"Eres un asistente experto en análisis de datos financieros. A continuación, se te proporciona una tabla con datos consolidados de ingresos por tipo de documento y meses. Tu tarea es analizar esta tabla y generar un informe detallado con las siguientes observaciones:

1. Identifica los tipos de documentos que generaron los mayores ingresos totales.
2. Analiza la suma total mensual y resalta cuáles son los meses con los mayores ingresos.
3. Incluye observaciones clave sobre patrones notables, como tendencias mensuales o distribuciones desbalanceadas entre los tipos de documento.
4. Presenta el análisis de manera clara y estructurada, utilizando listas o párrafos según sea necesario.

Tabla de datos:
{tabla}

Nota: En la tabla, la columna "Tipo Doc" indica el tipo de documento, las columnas "Meses" representan los ingresos por mes, y "Total Anual" contiene el total de ingresos anuales para cada fila.

Por favor, genera un informe detallado con base en esta información.
Incluye observaciones clave, porcentajes destacados y análisis general de las cifras."
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

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
else:
    st.write("Por favor, sube un archivo Excel para comenzar.")
