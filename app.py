import streamlit as st
import itertools
import time
import random
import math
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Optimización de Rutas de Delivery",
    page_icon="🚚",
    layout="wide"
)

# ── Estilos ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #F7F8FA; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; margin: 4px 0; }
    .metric-label { font-size: 0.8rem; color: #6B7280; text-transform: uppercase; letter-spacing: 0.05em; }
    .pedido-card {
        background: white;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border-left: 4px solid #F59E0B;
        margin-bottom: 8px;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.5rem;
    }
    .stAlert { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ── Datos de simulación: zonas y calles para generar direcciones ─────────────
DISTRITOS = ["Los Olivos", "San Isidro", "Miraflores", "La Victoria", "Surco",
             "Comas", "San Borja", "Barranco", "Jesús María", "Pueblo Libre"]
CALLES = ["Av. Los Álamos", "Jr. Las Flores", "Av. Universitaria", "Calle Real",
          "Av. Brasil", "Jr. Lima", "Av. Arequipa", "Calle Los Pinos", "Av. Salaverry"]

# ── Algoritmos ───────────────────────────────────────────────────────────────
def calcular_distancia_ruta(ruta, matriz):
    total = 0
    for i in range(len(ruta) - 1):
        total += matriz[ruta[i]][ruta[i+1]]
    total += matriz[ruta[-1]][ruta[0]]
    return total

def fuerza_bruta(matriz):
    n = len(matriz)
    nodos = list(range(1, n))
    mejor_dist = float('inf')
    mejor_ruta = None
    for perm in itertools.permutations(nodos):
        ruta = [0] + list(perm)
        d = calcular_distancia_ruta(ruta, matriz)
        if d < mejor_dist:
            mejor_dist = d
            mejor_ruta = ruta
    return mejor_ruta, mejor_dist

def algoritmo_voraz(matriz):
    n = len(matriz)
    visitadas = [False] * n
    ruta = [0]
    visitadas[0] = True
    actual = 0
    for _ in range(n - 1):
        menor = float('inf')
        siguiente = -1
        for i in range(n):
            if not visitadas[i] and matriz[actual][i] < menor:
                menor = matriz[actual][i]
                siguiente = i
        ruta.append(siguiente)
        visitadas[siguiente] = True
        actual = siguiente
    return ruta, calcular_distancia_ruta(ruta, matriz)

def programacion_dinamica(matriz):
    n = len(matriz)
    INF = float('inf')
    dp = [[INF] * n for _ in range(1 << n)]
    padre = [[-1] * n for _ in range(1 << n)]
    dp[1][0] = 0
    for mascara in range(1 << n):
        for u in range(n):
            if not (mascara >> u & 1) or dp[mascara][u] == INF:
                continue
            for v in range(n):
                if mascara >> v & 1:
                    continue
                nm = mascara | (1 << v)
                nd = dp[mascara][u] + matriz[u][v]
                if nd < dp[nm][v]:
                    dp[nm][v] = nd
                    padre[nm][v] = u
    mc = (1 << n) - 1
    mejor = INF
    ultima = -1
    for u in range(1, n):
        d = dp[mc][u] + matriz[u][0]
        if d < mejor:
            mejor = d
            ultima = u
    ruta = []
    mascara = mc
    cur = ultima
    while cur != -1:
        ruta.append(cur)
        prev = padre[mascara][cur]
        mascara ^= (1 << cur)
        cur = prev
    ruta.reverse()
    return ruta, mejor

def generar_matriz_aleatoria(n, seed=42):
    random.seed(seed)
    m = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1, n):
            d = random.randint(5, 50)
            m[i][j] = d
            m[j][i] = d
    return m

# ── Generación de pedidos simulados ───────────────────────────────────────────
def generar_pedidos(num_pedidos, seed=None):
    """Genera pedidos aleatorios con dirección simulada y coordenadas en el mapa."""
    if seed is not None:
        random.seed(seed)
    pedidos = []
    for i in range(num_pedidos):
        distrito = random.choice(DISTRITOS)
        calle = random.choice(CALLES)
        numero = random.randint(100, 2500)
        pedidos.append({
            "id": i + 1,
            "direccion": f"{calle} {numero}, {distrito}",
            "distrito": distrito,
            "x": random.uniform(0.1, 0.9),
            "y": random.uniform(0.1, 0.9)
        })
    return pedidos

def construir_matriz_desde_pedidos(pedidos):
    """Construye una matriz de distancias euclidianas a partir de coordenadas (almacén + pedidos)."""
    puntos = [(0.5, 0.95)] + [(p["x"], p["y"]) for p in pedidos]  # almacén arriba al centro
    n = len(puntos)
    matriz = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dx = puntos[i][0] - puntos[j][0]
                dy = puntos[i][1] - puntos[j][1]
                matriz[i][j] = round(((dx**2 + dy**2) ** 0.5) * 30, 1)  # escalado a "km" ficticios
    return matriz, puntos

# ── Visualización de ruta en mapa ─────────────────────────────────────────────
def graficar_pedidos(puntos, etiquetas):
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_facecolor('#F0F4F8')
    fig.patch.set_facecolor('#F0F4F8')
    for i, (x, y) in enumerate(puntos):
        c = '#1D4ED8' if i == 0 else '#F59E0B'
        s = 260 if i == 0 else 160
        ax.scatter(x, y, s=s, color=c, zorder=5, edgecolors='white', linewidths=1.5)
        ax.annotate(etiquetas[i], (x, y), textcoords="offset points",
                    xytext=(0, 12), ha='center', fontsize=9, fontweight='600', color='#111827')
    ax.set_title("📦 Pedidos generados", fontsize=12, fontweight='700', color='#111827', pad=10)
    ax.axis('off')
    plt.tight_layout()
    return fig

def graficar_ruta(ruta, etiquetas, coords, color, titulo):
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.set_facecolor('#F0F4F8')
    fig.patch.set_facecolor('#F0F4F8')
    ruta_completa = ruta + [ruta[0]]
    for i in range(len(ruta_completa) - 1):
        a, b = ruta_completa[i], ruta_completa[i+1]
        ax.annotate("", xy=coords[b], xytext=coords[a],
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.8))
    for i, (x, y) in enumerate(coords):
        c = '#1D4ED8' if i == 0 else '#F59E0B'
        ax.scatter(x, y, s=180, color=c, zorder=5, edgecolors='white', linewidths=1.5)
        ax.annotate(etiquetas[i], (x, y), textcoords="offset points",
                    xytext=(0, 10), ha='center', fontsize=8, fontweight='600', color='#111827')
    ax.set_title(titulo, fontsize=10, fontweight='700', color='#111827', pad=10)
    ax.axis('off')
    plt.tight_layout()
    return fig

# ── Estado de sesión ───────────────────────────────────────────────────────────
if "pedidos" not in st.session_state:
    st.session_state.pedidos = None
if "resultados" not in st.session_state:
    st.session_state.resultados = None

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("## 🚚 Optimización de Rutas de Delivery")
st.markdown("Simula pedidos de clientes y compara **Fuerza Bruta**, **Algoritmo Voraz** y **Programación Dinámica** para encontrar la ruta más corta.")
st.divider()

# ── Sidebar: configuración ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    num_pedidos = st.slider("Número de pedidos a generar", 4, 9, 6)

    st.divider()
    st.markdown("### 1️⃣ Generar pedidos")
    if st.button("🎲 Generar pedidos", use_container_width=True, type="primary"):
        st.session_state.pedidos = generar_pedidos(num_pedidos)
        st.session_state.resultados = None  # limpiamos resultados anteriores

    st.divider()
    st.markdown("### 2️⃣ Calcular ruta")
    algoritmos_sel = st.multiselect(
        "Algoritmos a ejecutar",
        ["Fuerza Bruta", "Algoritmo Voraz", "Programación Dinámica"],
        default=["Fuerza Bruta", "Algoritmo Voraz", "Programación Dinámica"]
    )
    buscar_ruta = st.button(
        "🚀 Buscar ruta óptima",
        use_container_width=True,
        disabled=(st.session_state.pedidos is None)
    )
    if st.session_state.pedidos is None:
        st.caption("⚠️ Primero genera los pedidos.")

# ── Si no hay pedidos generados ────────────────────────────────────────────────
if st.session_state.pedidos is None:
    st.info("👈 Usa el panel izquierdo para **generar pedidos** y luego buscar la ruta óptima.")
    st.stop()

pedidos = st.session_state.pedidos
matriz, puntos = construir_matriz_desde_pedidos(pedidos)
etiquetas = ["Almacén"] + [f"Pedido {p['id']}" for p in pedidos]

# ── Mostrar pedidos generados ──────────────────────────────────────────────────
st.markdown("### 📦 Pedidos generados")
col_mapa, col_lista = st.columns([1.2, 1])

with col_mapa:
    fig = graficar_pedidos(puntos, etiquetas)
    st.pyplot(fig, use_container_width=True)

with col_lista:
    for p in pedidos:
        st.markdown(f"""
        <div class="pedido-card">
            <strong style="color:#333">Pedido #{p['id']}</strong><br>
            <span style="color:#6B7280; font-size:0.9rem;">{p['direccion']}</span>
        </div>
        """, unsafe_allow_html=True)

with st.expander("📋 Ver matriz de distancias generada (km estimados)", expanded=False):
    df_mat = pd.DataFrame(matriz, index=etiquetas, columns=etiquetas)
    st.dataframe(df_mat.style.highlight_min(axis=None, color='#D1FAE5'), use_container_width=True)

st.divider()

# ── Ejecutar algoritmos ────────────────────────────────────────────────────────
if buscar_ruta:
    resultados = {}
    if "Fuerza Bruta" in algoritmos_sel:
        t0 = time.time()
        ruta, dist = fuerza_bruta(matriz)
        resultados["Fuerza Bruta"] = {"ruta": ruta, "dist": round(dist,1), "tiempo": time.time()-t0, "color": "#EF4444"}
    if "Algoritmo Voraz" in algoritmos_sel:
        t0 = time.time()
        ruta, dist = algoritmo_voraz(matriz)
        resultados["Algoritmo Voraz"] = {"ruta": ruta, "dist": round(dist,1), "tiempo": time.time()-t0, "color": "#10B981"}
    if "Programación Dinámica" in algoritmos_sel:
        t0 = time.time()
        ruta, dist = programacion_dinamica(matriz)
        resultados["Programación Dinámica"] = {"ruta": ruta, "dist": round(dist,1), "tiempo": time.time()-t0, "color": "#3B82F6"}
    st.session_state.resultados = resultados

# ── Mostrar resultados si existen ──────────────────────────────────────────────
if st.session_state.resultados:
    resultados = st.session_state.resultados

    st.markdown("### 📊 Resultados")
    cols = st.columns(len(resultados))
    dist_optima = min(v["dist"] for v in resultados.values())

    for col, (nombre, datos) in zip(cols, resultados.items()):
        es_optima = datos["dist"] == dist_optima
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{nombre}</div>
                <div class="metric-value" style="color:{'#10B981' if es_optima else '#111827'}">
                    {datos['dist']} km
                </div>
                <div style="font-size:0.85rem; color:#6B7280;">⏱ {datos['tiempo']:.6f}s</div>
                <div style="margin-top:8px">{'✅ Óptima' if es_optima else '⚠️ Subóptima'}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🗺️ Rutas encontradas")
    map_cols = st.columns(len(resultados))
    for col, (nombre, datos) in zip(map_cols, resultados.items()):
        with col:
            fig = graficar_ruta(datos["ruta"], etiquetas, puntos, datos["color"], nombre)
            st.pyplot(fig, use_container_width=True)
            ruta_texto = " → ".join([etiquetas[i] for i in datos["ruta"]]) + f" → {etiquetas[0]}"
            st.caption(ruta_texto)

    st.divider()

    st.markdown("### 📋 Tabla comparativa")
    tabla = []
    for nombre, datos in resultados.items():
        diferencia = round(datos["dist"] - dist_optima, 1)
        tabla.append({
            "Algoritmo": nombre,
            "Distancia (km)": datos["dist"],
            "Tiempo (s)": f"{datos['tiempo']:.6f}",
            "Diferencia vs óptimo (km)": diferencia,
            "Solución óptima": "✅ Sí" if diferencia == 0 else f"❌ No (+{diferencia} km)"
        })
    st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("### 📈 Análisis empírico: tiempo vs número de pedidos")
    st.caption("Matrices de distancias aleatorias — fuerza bruta limitada por su complejidad O(n!)")

    tamanos = [4, 5, 6, 7, 8, 9, 10]
    filas = []
    prog = st.progress(0, text="Calculando...")
    for idx, n in enumerate(tamanos):
        m = generar_matriz_aleatoria(n)
        fila = {"n": n, "Permutaciones (n-1)!": math.factorial(n-1)}
        if "Fuerza Bruta" in algoritmos_sel:
            t0 = time.time(); fuerza_bruta(m); fila["Fuerza Bruta (s)"] = round(time.time()-t0, 6)
        if "Algoritmo Voraz" in algoritmos_sel:
            t0 = time.time(); algoritmo_voraz(m); fila["Voraz (s)"] = round(time.time()-t0, 6)
        if "Programación Dinámica" in algoritmos_sel:
            t0 = time.time(); programacion_dinamica(m); fila["Prog. Dinámica (s)"] = round(time.time()-t0, 6)
        filas.append(fila)
        prog.progress((idx+1)/len(tamanos), text=f"Calculando n={n}...")
    prog.empty()

    df_emp = pd.DataFrame(filas)
    st.dataframe(df_emp, use_container_width=True, hide_index=True)

    fig2, ax2 = plt.subplots(figsize=(9, 4))
    ax2.set_facecolor('#F7F8FA')
    fig2.patch.set_facecolor('#F7F8FA')
    colores = {"Fuerza Bruta (s)": "#EF4444", "Voraz (s)": "#10B981", "Prog. Dinámica (s)": "#3B82F6"}
    marcadores = {"Fuerza Bruta (s)": "o", "Voraz (s)": "s", "Prog. Dinámica (s)": "^"}
    labels = {"Fuerza Bruta (s)": "Fuerza Bruta", "Voraz (s)": "Algoritmo Voraz", "Prog. Dinámica (s)": "Prog. Dinámica"}
    for col_name, color in colores.items():
        if col_name in df_emp.columns:
            ax2.plot(df_emp["n"], df_emp[col_name], marker=marcadores[col_name],
                     label=labels[col_name], color=color, linewidth=2.2, markersize=7)
    ax2.set_xlabel("Número de pedidos (n)", fontsize=11)
    ax2.set_ylabel("Tiempo de ejecución (s)", fontsize=11)
    ax2.set_title("Comparativa de tiempos de ejecución", fontsize=13, fontweight='700')
    ax2.legend(fontsize=10)
    ax2.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    st.pyplot(fig2, use_container_width=True)
else:
    st.info("👆 Pedidos listos. Ahora presiona **🚀 Buscar ruta óptima** en el panel izquierdo.")
