# =============================================================================
# 1. IMPORTAR TODAS AS BIBLIOTECAS NECESSÁRIAS
# =============================================================================
import streamlit as st
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.colors import black, gray

# =============================================================================
# 2. FUNÇÕES AUXILIARES
# =============================================================================

@st.cache_data
def load_data():
    """Carrega os dados de configuração do ficheiro data.json."""
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("ERRO: Ficheiro 'data.json' não encontrado! Verifique se o ficheiro existe no projeto.")
        return {}
    except json.JSONDecodeError:
        st.error("ERRO: O ficheiro 'data.json' contém um erro de formatação. Verifique a sintaxe.")
        return {}

def gerar_pdf(product_ref, product_details):
    """Gera um PDF com um layout de etiqueta preciso, replicando a imagem."""
    buffer = io.BytesIO()
    largura_pagina, altura_pagina = A4
    p = canvas.Canvas(buffer, pagesize=A4)
    
    components = product_details.get('components', [])
    total_componentes = len(components)
    
    p.setTitle(f"Etiquetas para {product_ref}")

    for i, component in enumerate(components):
        label_width = 140*mm
        label_height = 95*mm
        x0 = (largura_pagina - label_width) / 2
        y0 = (altura_pagina - label_height) / 2
        
        p.saveState()
        p.setStrokeColor(black)
        
        p.setLineWidth(1)
        p.rect(x0, y0, label_width, label_height)

        p.setLineWidth(0.5)
        v_line_x = x0 + label_width * 0.65
        p.line(v_line_x, y0, v_line_x, y0 + label_height)

        h_line_y = y0 + label_height * 0.40
        p.line(x0, h_line_y, x0 + label_width, h_line_y)
        
        img_x, img_y, img_w, img_h = x0, h_line_y, v_line_x - x0, label_height - (h_line_y - y0)
        try:
            path_img_componente = component.get("imagem")
            if path_img_componente:
                p.drawImage(path_img_componente, img_x + 2*mm, img_y + 2*mm, width=img_w - 4*mm, height=img_h - 4*mm, preserveAspectRatio=True, anchor='c')
        except IOError:
            p.drawString(img_x + 5*mm, img_y + img_h/2, "Imagem não encontrada.")

        icon_x, icon_y, icon_w, icon_h = v_line_x, h_line_y, label_width - (v_line_x - x0), label_height - (h_line_y - y0)
        try:
            path_img_geral = product_details.get("imagem_geral")
            if path_img_geral:
                p.drawImage(path_img_geral, icon_x + 2*mm, icon_y + icon_h * 0.5, width=icon_w - 4*mm, height=icon_h * 0.5, preserveAspectRatio=True, anchor='n')
        except IOError:
            pass
        p.setFont("Helvetica-Bold", 36)
        p.drawCentredString(icon_x + icon_w/2, icon_y + icon_h * 0.25, f"{i + 1}/{total_componentes}")

        qr_x, qr_y, qr_w, qr_h = v_line_x, y0, label_width - (v_line_x - x0), h_line_y - y0
        qr_data = f"REF:{product_ref}, COMP:{component.get('name', '')}"
        qr_code = qr.QrCodeWidget(qr_data)
        qr_bounds = qr_code.getBounds()
        qr_code_width = qr_bounds[2] - qr_bounds[0]
        qr_size = min(qr_w, qr_h) - 4*mm
        escala = qr_size / qr_code_width
        desenho = Drawing(qr_size, qr_size, transform=[escala, 0, 0, escala, 0, 0])
        desenho.add(qr_code)
        renderPDF.draw(desenho, p, qr_x + (qr_w - qr_size) / 2, qr_y + (qr_h - qr_size) / 2)
        
        text_x = x0 + 3*mm
        text_y = h_line_y - 7*mm
        
        p.setFont("Helvetica-Bold", 10)
        p.drawString(text_x, text_y, "PRODUCT NAME")
        p.setFont("Helvetica-Bold", 9)
        p.drawString(text_x, text_y - 6*mm, product_ref)
        p.setFont("Helvetica", 9)
        p.drawString(text_x, text_y - 11*mm, product_details.get('description', ''))

        p.setLineWidth(1.5)
        sep_y = text_y - 15*mm
        p.line(x0, sep_y, v_line_x, sep_y)
        p.setLineWidth(0.5)

        p.setFont("Helvetica-Bold", 10)
        p.drawString(text_x, sep_y - 6*mm, "DIMENSION (component)")
        p.setFont("Helvetica", 9)
        p.drawString(text_x, sep_y - 11*mm, component.get('dims', ''))

        box_0_y = y0
        box_0_h = h_line_y - y0
        box_0_w = 10*mm
        box_0_x = v_line_x - box_0_w
        p.line(box_0_x, box_0_y, box_0_x, box_0_y + box_0_h)
        p.drawCentredString(box_0_x + box_0_w/2, y0 + qr_h/2, "0")

        p.restoreState()
        
        if i < total_componentes - 1:
            p.showPage()
            
    p.save()
    buffer.seek(0)
    return buffer

# =============================================================================
# 3. INTERFACE DO UTILIZADOR (CÓDIGO STREAMLIT)
# =============================================================================

st.set_page_config(page_title="Gerador de Etiquetas", layout="centered")
st.title('Gerador de Etiquetas de Produção')

data = load_data()

if data:
    level1_options = list(data.keys())
    selected_level1 = st.selectbox('Passo 1: Selecione a Categoria Principal', level1_options)

    level2_options = list(data.get(selected_level1, {}).keys())
    selected_level2 = st.selectbox('Passo 2: Selecione a Sub-Categoria', level2_options) # <-- LINHA CORRIGIDA

    ref_options = list(data.get(selected_level1, {}).get(selected_level2, {}).keys())
    selected_ref = st.selectbox('Passo 3: Selecione a Referência Final', ref_options)

    st.markdown("---")

    if st.button('Gerar Etiquetas em PDF', type="primary", use_container_width=True):
        if selected_ref:
            try:
                details = data[selected_level1][selected_level2][selected_ref]
                pdf_buffer = gerar_pdf(selected_ref, details)
                st.download_button(
                    label="✔️ Download do PDF pronto",
                    data=pdf_buffer,
                    file_name=f"etiquetas_{selected_ref}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o PDF: {e}")
                st.exception(e)
        else:
            st.warning("Por favor, selecione uma referência válida.")
else:
    st.warning("Não foi possível carregar os dados. Verifique o ficheiro 'data.json'.")
