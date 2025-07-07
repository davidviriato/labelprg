# =============================================================================
# 1. IMPORTAR TODAS AS BIBLIOTECAS NECESSÁRIAS
# =============================================================================
import streamlit as st
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6, landscape # MUDANÇA: Importar A6 e landscape
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
# VERSÃO FINAL: FUNÇÃO GERAR_PDF
# =============================================================================
def gerar_pdf_final(product_ref, product_details, quantity):
    """Gera um PDF com o layout final e tamanho de página A6 (1/4 de A4)."""
    buffer = io.BytesIO()
    
    # MUDANÇA: Usar A6 em modo paisagem para o tamanho da página/etiqueta
    label_width, label_height = landscape(A6)
    
    p = canvas.Canvas(buffer, pagesize=(label_width, label_height))
    p.setTitle(f"Etiquetas para {product_ref}")

    for i in range(quantity):
        # Como a página é a etiqueta, as coordenadas são diretas (origem no canto inferior esquerdo)
        # Deixar uma pequena margem interna
        margem = 1 * mm 
        x0 = margem
        y0 = margem
        
        p.saveState()
        p.setStrokeColor(black)
        
        # --- Desenho da Grelha Estrutural ---
        p.setLineWidth(1)
        p.rect(x0, y0, label_width - 2 * margem, label_height - 2 * margem)

        p.setLineWidth(0.3)
        v_line1_x = x0 + 25*mm
        v_line2_x = x0 + label_width - 35*mm
        h_line_y = y0 + 35*mm
        
        p.line(v_line1_x, y0, v_line1_x, y0 + label_height - 2*margem)
        p.line(v_line2_x, y0, v_line2_x, y0 + label_height - 2*margem)
        p.line(v_line1_x, h_line_y, v_line2_x, h_line_y)
        
        # --- Secção Esquerda: "Made in Portugal" e Código de Barras ---
        p.setFont("Helvetica", 6)
        p.drawString(x0 + 2*mm, y0 + label_height - 7*mm, "Made in Portugal")
        p.drawString(x0 + 2*mm, y0 + label_height - 10*mm, "© Chanel")
        
        # ## --- CÓDIGO DE BARRAS: CORREÇÃO FINAL DE CONTEÚDO E DIMENSÕES --- ##
        
        # MUDANÇA 1: O valor a ser codificado é apenas a referência, sem prefixos.
        barcode_value = product_ref
        
        # MUDANÇA 2: Reduzir drasticamente a largura das barras (barWidth) e ajustar a altura (barHeight)
        # para que o código de barras total seja alto e fino.
        barcode = code128.Code128(barcode_value, barHeight=20*mm, barWidth=0.14*mm, humanReadable=False)
        
        barcode_width = barcode.width
        barcode_height = barcode.height

        center_x = x0 + 12.5*mm
        center_y = y0 + 38*mm # Ajustado para caber melhor na célula
        
        p.saveState()
        p.translate(center_x, center_y)
        p.rotate(90)
        barcode.drawOn(p, -barcode_width/2, -barcode_height/2)
        p.restoreState()
        
        p.setFont("Helvetica", 7)
        p.drawCentredString(center_x, y0 + 10*mm, barcode_value)
        
        # --- Secção Central Superior: Imagem ---
        img_x, img_y = v_line1_x, h_line_y
        img_w, img_h = v_line2_x - v_line1_x, (y0 + label_height - 2*margem) - h_line_y
        try:
            path_img = product_details.get("imagem", "images/placeholder.png")
            p.drawImage(path_img, img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True, anchor='c')
        except IOError:
            p.drawCentredString(img_x + img_w/2, img_y + img_h/2, "Imagem não encontrada.")

        # --- Secção Central Inferior: Texto ---
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
        box_x, box_y = v_line2_x, h_line_y
        box_w, box_h = (x0 + label_width - 2*margem) - v_line2_x, (y0 + label_height - 2*margem) - h_line_y
        p.setLineWidth(0.3)
        p.rect(box_x, box_y, box_w, box_h, fill=0)
        p.setFont("Helvetica", 12)
        p.drawCentredString(box_x + box_w/2, box_y + box_h/2, "0")

        qr_x, qr_y = v_line2_x, y0
        qr_w, qr_h = box_w, h_line_y - y0
        
        # MUDANÇA 3: Garantir que o QR Code também só tem a referência.
        qr_data = product_ref
        qr_code = qr.QrCodeWidget(qr_data)
        qr_bounds = qr_code.getBounds()
        qr_code_width = qr_bounds[2] - qr_bounds[0]
        qr_size = min(qr_w, qr_h) - 2*mm
        escala = qr_size / qr_code_width
        
        desenho = Drawing(qr_size, qr_size, transform=[escala, 0, 0, escala, 0, 0])
        desenho.add(qr_code)
        renderPDF.draw(desenho, p, qr_x + (qr_w - qr_size)/2, qr_y + (qr_h - qr_size)/2)

        p.restoreState()
        
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
    # ... (o resto do código da interface mantém-se igual)
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
                if 'imagem' not in details:
                    details['imagem'] = "images/placeholder.png"
                # Chamar a nova função de PDF final
                pdf_buffer = gerar_pdf_final(selected_ref, details, quantity)
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
