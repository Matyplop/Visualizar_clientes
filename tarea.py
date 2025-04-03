import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import traceback
import tempfile
import os
import streamlit.components.v1 as components

# Intentar importar pyvis, con manejo de errores si no está disponible
try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    st.warning("La librería 'pyvis' no está instalada. El gráfico de red interactivo no estará disponible. Instálala con 'pip install pyvis'.")

# Función para crear y mostrar un gráfico de red con Plotly (como alternativa a pyvis)
def draw_network_plotly(antenna_person_data):
    # Crear nodos para antenas y personas
    nodes = []
    node_colors = []
    node_sizes = []
    
    # Agregar nodos de antenas
    antenna_nodes = list(antenna_person_data['CONECTADO'].unique())
    for _ in antenna_nodes:
        node_colors.append('#76b852')  # verde para antenas
        node_sizes.append(20)          # tamaño mayor para antenas
    
    # Agregar nodos de personas
    person_nodes = list(antenna_person_data['NOMBRE'].unique())
    for _ in person_nodes:
        node_colors.append('#3498db')  # azul para personas
        node_sizes.append(10)          # tamaño menor para personas
    
    # Combinar todos los nodos
    nodes = antenna_nodes + person_nodes
    
    # Crear conexiones (edges)
    edge_x = []
    edge_y = []
    
    # Crear un diccionario para almacenar las posiciones de los nodos
    # Ubicación circular para antenas y personas
    pos = {}
    import math
    
    # Posiciones para antenas (círculo externo)
    for i, node in enumerate(antenna_nodes):
        angle = 2 * math.pi * i / len(antenna_nodes) if len(antenna_nodes) > 0 else 0
        pos[node] = (math.cos(angle), math.sin(angle))
    
    # Posiciones para personas (círculo interno)
    for i, node in enumerate(person_nodes):
        angle = 2 * math.pi * i / len(person_nodes) if len(person_nodes) > 0 else 0
        pos[node] = (0.5 * math.cos(angle), 0.5 * math.sin(angle))
    
    # Crear los enlaces
    for _, row in antenna_person_data.iterrows():
        x0, y0 = pos[row['NOMBRE']]
        x1, y1 = pos[row['CONECTADO']]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Crear líneas para las conexiones
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.8, color='#888'),
        hoverinfo='none',
        mode='lines')
    
    # Crear puntos para los nodos
    node_x = [pos[node][0] for node in nodes]
    node_y = [pos[node][1] for node in nodes]
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=False,
            color=node_colors,
            size=node_sizes,
            line=dict(width=2, color='white')))
    
    # Añadir texto para mostrar en hover
    node_text = nodes
    node_trace.marker.color = node_colors
    node_trace.marker.size = node_sizes
    node_trace.text = node_text
    
    # Crear la figura
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20, l=5, r=5, t=40),
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                   )
    
    # Añadir anotaciones de texto para cada nodo
    for node, x, y in zip(nodes, node_x, node_y):
        fig.add_annotation(
            x=x, y=y,
            text=node,
            showarrow=False,
            font=dict(size=10)
        )
    
    fig.update_layout(title="Conexiones entre antenas y personas")
    st.plotly_chart(fig)

# Función para crear y mostrar un gráfico de red interactivo con Pyvis
def draw_network_pyvis(antenna_person_data):
    if not PYVIS_AVAILABLE:
        st.warning("No se puede mostrar el gráfico Pyvis porque la librería no está instalada.")
        return
    
    try:
        # Crear una red usando pyvis
        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#333333")
        
        # Configurar la física de la red para una mejor visualización
        net.barnes_hut(gravity=-5000, central_gravity=0.3, spring_length=150, spring_strength=0.05,
                       damping=0.09, overlap=0)
        
        # Agregar nodos de CONECTADO (antenas)
        added_nodes = set()
        for connected in antenna_person_data['CONECTADO'].unique():
            if connected not in added_nodes:
                net.add_node(str(connected), str(connected), title=str(connected), 
                             color="#76b852", shape="dot", size=25)
                added_nodes.add(connected)
        
        # Agregar nodos de NOMBRE (personas)
        for name in antenna_person_data['NOMBRE'].unique():
            if name not in added_nodes:
                net.add_node(str(name), str(name), title=str(name), 
                             color="#3498db", shape="dot", size=15)
                added_nodes.add(name)
        
        # Agregar las conexiones entre NOMBRE y CONECTADO
        for _, row in antenna_person_data.iterrows():
            net.add_edge(str(row['NOMBRE']), str(row['CONECTADO']), color="#999999", width=1.5)
        
        # Guardar y mostrar
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
            path = tmpfile.name
            net.save_graph(path)
        
        # Abrir el archivo, leer su contenido y renderizarlo
        with open(path, 'r', encoding='utf-8') as file:
            html = file.read()
        
        # Eliminar el archivo temporal
        os.unlink(path)
        
        # Mostrar el gráfico en Streamlit
        components.html(html, height=600)
    except Exception as e:
        st.error(f"Error al crear el gráfico Pyvis: {str(e)}")
        st.error("Mostrando gráfico alternativo...")
        draw_network_plotly(antenna_person_data)

# Función para mostrar la tabla detallada de qué personas están conectadas a cada antena
def show_detailed_connections(antenna_person_data):
    st.subheader("🔍 Detalle de personas por antena")
    
    # Agrupar por antena
    antennas = antenna_person_data['CONECTADO'].unique()
    
    # Crear pestañas para cada visualización
    tab1, tab2, tab3 = st.tabs(["Vista por antena", "Tabla completa", "Gráfico de barras"])
    
    with tab1:
        # Para cada antena, mostrar las personas conectadas
        for antenna in antennas:
            connected_people = antenna_person_data[antenna_person_data['CONECTADO'] == antenna]['NOMBRE'].tolist()
            with st.expander(f"📡 Antena: {antenna} - {len(connected_people)} personas conectadas"):
                if connected_people:
                    st.write("👥 Personas conectadas:")
                    for i, person in enumerate(connected_people, 1):
                        st.write(f"  {i}. {person}")
                else:
                    st.write("No hay personas conectadas a esta antena.")
    
    with tab2:
        # Mostrar una tabla completa con todas las conexiones
        st.write("📊 Tabla completa de conexiones:")
        st.dataframe(antenna_person_data)
    
    with tab3:
        # Crear un gráfico de barras que muestre cuántas personas hay por antena
        try:
            antenna_counts = antenna_person_data['CONECTADO'].value_counts().reset_index()
            antenna_counts.columns = ['Antena', 'Cantidad de personas']
            
            fig = go.Figure(data=[
                go.Bar(
                    x=antenna_counts['Antena'],
                    y=antenna_counts['Cantidad de personas'],
                    text=antenna_counts['Cantidad de personas'],
                    textposition='auto',
                    marker_color='rgba(118, 184, 82, 0.7)',
                    marker_line_color='rgba(118, 184, 82, 1)',
                    marker_line_width=1
                )
            ])
            
            fig.update_layout(
                title='Cantidad de personas por antena',
                xaxis_title='Antena',
                yaxis_title='Cantidad de personas',
                height=500,
                template="plotly_white",
                margin=dict(l=40, r=40, t=60, b=40)
            )
            
            st.plotly_chart(fig)
        except Exception as e:
            st.error(f"Error al crear el gráfico de barras: {str(e)}")

# Función para crear un gráfico de sunburst que muestre la distribución de personas por antena
def show_sunburst_chart(antenna_person_data):
    try:
        # Preparar datos para el gráfico sunburst
        labels = ["Conexiones"]  # El centro del sunburst
        parents = [""]  # El centro no tiene padre
        values = [len(antenna_person_data)]  # El valor total
        
        # Agregar antenas
        antennas = antenna_person_data['CONECTADO'].unique()
        for antenna in antennas:
            labels.append(str(antenna))
            parents.append("Conexiones")
            # El valor de cada antena es la cantidad de personas conectadas a ella
            values.append(len(antenna_person_data[antenna_person_data['CONECTADO'] == antenna]))
        
        # Agregar personas
        for _, row in antenna_person_data.iterrows():
            labels.append(str(row['NOMBRE']))
            parents.append(str(row['CONECTADO']))
            values.append(1)  # Cada persona tiene valor 1
        
        # Crear el gráfico sunburst
        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            insidetextorientation='radial',
            marker=dict(
                colors=['#3498db', '#76b852', '#f1c40f', '#e74c3c', '#9b59b6', '#1abc9c',
                        '#d35400', '#34495e', '#2ecc71', '#e67e22'],
                line=dict(width=0.5, color='white')
            ),
        ))
        
        fig.update_layout(
            title="Distribución de personas por antena",
            margin=dict(t=30, l=0, r=0, b=0),
            height=600,
        )
        
        st.plotly_chart(fig)
    except Exception as e:
        st.error(f"Error al crear el gráfico sunburst: {str(e)}")

# Función principal para la interfaz en Streamlit
def main():
    try:
        st.set_page_config(
            page_title="Conexiones Antenas-Personas",
            page_icon="📡",
            layout="wide",
        )
    except:
        pass  # Si falla la configuración de página, continuar de todos modos
    
    st.title('📡 Visualización de Conexiones entre Personas y Antenas')
    
    # Cargar archivo Excel
    uploaded_file = st.file_uploader("Cargar archivo Excel", type=["xlsx"])
    
    if uploaded_file is not None:
        # Leer el archivo Excel
        try:
            st.info("Procesando archivo...")
            antenna_person_data = pd.read_excel(uploaded_file)
            
            # Verificar que el DataFrame tiene las columnas necesarias
            if 'CONECTADO' not in antenna_person_data.columns or 'NOMBRE' not in antenna_person_data.columns:
                st.error("El archivo Excel debe contener las columnas 'CONECTADO' y 'NOMBRE'")
                return
            
            # Convertir a string para evitar problemas con tipos de datos
            antenna_person_data['CONECTADO'] = antenna_person_data['CONECTADO'].astype(str)
            antenna_person_data['NOMBRE'] = antenna_person_data['NOMBRE'].astype(str)

            if 'CLAVE' in antenna_person_data.columns:
                antenna_person_data['CLAVE'] = antenna_person_data['CLAVE'].astype(str)

            if 'FECHA INCORPORACION' in antenna_person_data.columns:
                antenna_person_data['FECHA INCORPORACION'] = antenna_person_data['FECHA INCORPORACION'].astype(str)

            if 'TELEFONO' in antenna_person_data.columns:
                antenna_person_data['TELEFONO'] = antenna_person_data['TELEFONO'].astype(str)
            
            # Mostrar los primeros registros para verificar
            st.write("Primeros 5 registros del archivo:")
            st.dataframe(antenna_person_data.head())
            
            # Mostrar estadísticas básicas
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de personas", len(antenna_person_data['NOMBRE'].unique()))
            with col2:
                st.metric("Total de antenas", len(antenna_person_data['CONECTADO'].unique()))
            
            # Crear pestañas para las diferentes visualizaciones
            tab1, tab2, tab3 = st.tabs(["Gráfico de red", "Gráfico Sunburst", "Detalle de conexiones"])
            
            with tab1:
                st.subheader("🕸️ Gráfico de red interactivo")
                st.info("Este gráfico es interactivo. Puedes hacer zoom, mover nodos y ver detalles.")
                draw_network_pyvis(antenna_person_data)
            
            with tab2:
                st.subheader("🔄 Gráfico Sunburst")
                show_sunburst_chart(antenna_person_data)
            
            with tab3:
                # Mostrar la vista detallada de conexiones
                show_detailed_connections(antenna_person_data)
            
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")
            st.error(f"Detalles del error: {traceback.format_exc()}")
            st.error("Por favor, verifica que el archivo tiene el formato correcto y contiene las columnas 'CONECTADO' y 'NOMBRE'.")
    else:
        # Si no se carga un archivo, mostrar un mensaje informativo
        st.info("📤 No se ha cargado ningún archivo Excel. Por favor, carga un archivo para visualizar las conexiones.")
        antenna_person_data = pd.DataFrame(columns=["CONECTADO", "NOMBRE"])

    # Entradas de usuario para agregar nuevas conexiones
    st.subheader("➕ Agregar nueva conexión")
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Nombre de la persona", "")
    with col2:
        new_connected = st.text_input("Nombre de la antena", "")
    
    if st.button("✅ Agregar conexión"):
        if new_name and new_connected:
            try:
                # Agregar nueva conexión
                if 'antenna_person_data' in locals() and not antenna_person_data.empty:
                    new_data = pd.DataFrame({'CONECTADO': [new_connected], 'NOMBRE': [new_name]})
                    antenna_person_data = pd.concat([antenna_person_data, new_data], ignore_index=True)
                    
                    # Guardar los datos actualizados en el archivo Excel
                    with st.spinner('Guardando archivo...'):
                        # Crear un archivo Excel de salida con los nuevos datos
                        output_file = "conexion_conectados_nombres_actualizada.xlsx"
                        antenna_person_data.to_excel(output_file, index=False)
                        st.success(f"✅ Se ha agregado la conexión entre {new_name} y {new_connected} y se ha guardado el archivo Excel.")
                        
                        # Botón para descargar
                        with open(output_file, "rb") as file:
                            btn = st.download_button(
                                label="📥 Descargar archivo actualizado", 
                                data=file, 
                                file_name=output_file, 
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    
                    # Recargar la página para actualizar las visualizaciones
                    st.success("Conexión agregada correctamente. Para ver los cambios en los gráficos, recarga la página.")
                else:
                    st.error("⚠️ Primero debes cargar un archivo Excel o agregar datos.")
            except Exception as e:
                st.error(f"Error al agregar conexión: {str(e)}")
        else:
            st.error("⚠️ Por favor ingresa tanto el nombre de la persona como el nombre de la antena")

if __name__ == "__main__":
    main()