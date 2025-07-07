# =============================================================================
# 1. IMPORTAR TODAS AS BIBLIOTECAS NECESSÁRIAS
# =============================================================================
import streamlit as st
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.graphics.barcode import qr, code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.colors import black

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
        st.error("ERRO: Ficheiro 'data.json' não encontrado! Verifique se o ficheiro existe no seu repositório GitHub.")
        return {}
    except json.JSONDecodeError:
        st.error("ERRO: O ficheiro 'data.json' contém um erro de formatação. Verifique a sintaxe (ex: vírgulas, aspas).")
        return {}

# =============================================================================
# VERSÃO 3: FUNÇÃO GERAR_PDF COM LAYOUT DE ALTA PRECISÃO
# =============================================================================
def gerar_pdf_preciso(product_ref, product_details, quantity):
    """Gera um PDF com um layout de etiqueta preciso, replicando a imagem final."""
    buffer = io.BytesIO()
    largura_pagina, altura_pagina = A4
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setTitle(f"Etiquetas para {product_ref}")

    for i in range(quantity):
        # --- Definições Globais da Etiqueta ---
        label_width = 140*mm
        label_height = 80*mm
        x0 = (largura_pagina - label_width) / 2
        y0 = (altura_pagina - label_height) / 2
        
        p.saveState()
        p.setStrokeColor(black)
        
        # --- Desenho da Grelha Estrutural ---
        # Borda Exterior
        p.setLineWidth(1)
        p.rect(x0, y0, label_width, label_height)

        # Divisões Internas
        p.setLineWidth(0.3)
        # Coordenadas das linhas divisórias
        v_line1_x = x0 + 25*mm
        v_line2_x = x0 + label_width - 35*mm
        h_line_y = y0 + 35*mm
        
        p.line(v_line1_x, y0, v_line1_x, y0 + label_height) # Linha vertical esquerda
        p.line(v_line2_x, y0, v_line2_x, y0 + label_height) # Linha vertical direita
        p.line(v_line1_x, h_line_y, v_line2_x, h_line_y)   # Linha horizontal central
        
        # --- Secção Esquerda: "Made in Portugal" e Código de Barras ---
        # Texto no topo
        p.setFont("Helvetica", 6)
        p.drawString(x0 + 2*mm, y0 + label_height - 5*mm, "Made in Portugal")
        p.drawString(x0 + 2*mm, y0 + label_height - 8*mm, "© Chanel")
        
        # Código de Barras
        barcode_value = product_ref
        barcode = code128.Code128(barcode_value, barHeight=45*mm, barWidth=0.25*mm, humanReadable=False)
        # Desenhar o código de barras rodado
        p.saveState()
        p.translate(x0 + 15*mm, y0 + label_height - 15*mm) # Mover a origem para o ponto de rotação
        p.rotate(90) # Rodar
        barcode.drawOn(p, 0, 0) # Desenhar na nova origem (0,0)
        p.restoreState() # Voltar ao estado normal
        
        # Texto vertical abaixo do código de barras
        p.setFont("Helvetica", 7)
        p.drawCentredString(x0 + 12.5*mm, y0 + 10*mm, barcode_value)

        # --- Secção Central Superior: Imagem do Produto ---
        img_x, img_y = v_line1_x, h_line_y
        img_w, img_h = v_line2_x - v_line1_x, label_height - (h_line_y - y0)
        try:
            path_img = product_details.get("imagem", "images/placeholder.png")
            # Desenhar a imagem centrada dentro do seu contentor
            p.drawImage(path_img, img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True, anchor='c')
        except IOError:
            p.drawCentredString(img_x + img_w/2, img_y + img_h/2, "Imagem não encontrada.")

        # --- Secção Central Inferior: Bloco de Texto ---
        text_x = v_line1_x + 4*mm
        text_y = h_line_y - 8*mm
        
        p.setFont("Helvetica-Bold", 10)
        p.drawString(text_x, text_y, "PRODUCT NAME")
        p.setLineWidth(1)
        p.line(text_x, text_y - 1.5*mm, v_line2_x - 4*mm, text_y - 1.5*mm)
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(text_x, text_y - 8*mm, product_ref)
        
        p.setFont("Helvetica", 10)
        p.drawString(text_x, text_y - 13*mm, product_details.get('description', ''))

        # --- Secção Direita: QR Code e Caixa "0" ---
        # Caixa "0"
        box_x, box_y = v_line2_x, h_line_y
        box_w, box_h = label_width - (v_line2_x - x0), label_height - (h_line_y - y0)
        p.setLineWidth(0.3)
        p.rect(box_x, box_y, box_w, box_h, fill=0) # Desenha a caixa à volta do 0
        p.setFont("Helvetica", 12)
        p.drawCentredString(box_x + box_w/2, box_y + box_h/2, "0")

        # QR Code
        qr_x, qr_y = v_line2_x, y0
        qr_w, qr_h = box_w, h_line_y - y0
        
        qr_data = f"REF:{product_ref}" # O QR code contém a referência
        qr_code = qr.QrCodeWidget(qr_data)
        qr_bounds = qr_code.getBounds()
        qr_code_width = qr_bounds[2] - qr_bounds[0]
        qr_size = min(qr_w, qr_h) - 4*mm # O tamanho do QR será o máximo possível na célula
        escala = qr_size / qr_code_width
        
        desenho = Drawing(qr_size, qr_size, transform=[escala, 0, 0, escala, 0, 0])
        desenho.add(qr_code)
        renderPDF.draw(desenho, p, qr_x + (qr_w - qr_size)/2, qr_y + (qr_h - qr_size)/2)

        p.restoreState()
        
        # Adiciona nova página para a próxima etiqueta
        if i < quantity - 1:
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
    selected_level2 = st.selectbox('Passo 2: Selecione a Sub-Categoria', level2_options)

    ref_options = list(data.get(selected_level1, {}).get(selected_level2, {}).keys())
    selected_ref = st.selectbox('Passo 3: Selecione a Referência Final', ref_options)

    quantity = st.number_input("Quantidade de etiquetas a imprimir", min_value=1, value=1, step=1)

    st.markdown("---")

    if st.button('Gerar Etiquetas em PDF', type="primary", use_container_width=True):
        if selected_ref:
            try:
                details = data[selected_level1][selected_level2][selected_ref]
                
                # Adicionar um campo 'imagem' placeholder se não existir
                if 'imagem' not in details:
                    details['imagem'] = "images/placeholder.png"

                # Chamar a nova função de PDF de alta precisão
                pdf_buffer = gerar_pdf_preciso(selected_ref, details, quantity)

                st.download_button(
                    label=f"✔️ Download de {quantity} Etiqueta(s) em PDF",
                    data=pdf_buffer,
                    file_name=f"etiquetas_{selected_ref}x{quantity}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o PDF: {e}")
                st.exception(e)
        else:
            st.warning("Por favor, selecione uma referência válida.")
else:
    st.warning("Não foi possível carregar os dados. Verifique o ficheiro 'data.json'.")
