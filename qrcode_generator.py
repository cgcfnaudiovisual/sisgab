import qrcode
import io
import base64
from nicegui import ui, app
from database import get_db_connection, get_service_db_connection

THEME = {
    'bg_main': '#040d1a',
    'bg_panel': '#091326',
    'border': 'rgba(0, 229, 255, 0.15)',
    'accent': '#00e5ff'
}

def render_page():
    # Page header
    ui.label('📱 Gerador de QR Code').classes('text-xl font-bold text-white cyber-title q-mb-md')
    
    # Main card
    with ui.card().classes('w-full max-w-[600px] q-pa-lg no-shadow rounded-xl q-mx-auto items-center').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
        
        # Input field for URL/text
        url_input = ui.input('Link ou Texto para o QR Code', placeholder='https://...').props('dark outlined dense w-full').classes('w-full q-mb-sm')
        
        # Optional title field  
        titulo_input = ui.input('Legenda (opcional)', placeholder='Ex: Galeria Solenidade').props('dark outlined dense w-full').classes('w-full q-mb-sm')
        
        # Size selector
        size_select = ui.select({200: 'Pequeno (200px)', 400: 'Médio (400px)', 600: 'Grande (600px)'}, value=400, label='Tamanho').props('dark outlined dense option-dark').classes('w-full q-mb-md')
        
        # Preview container
        preview_container = ui.column().classes('w-full items-center justify-center q-my-md min-h-[200px]')
        
        def gerar_qrcode():
            if not url_input.value:
                ui.notify('Digite um link ou texto!', color='warning')
                return
            
            preview_container.clear()
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(url_input.value)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode('utf-8')
            img_src = f'data:image/png;base64,{b64}'
            
            with preview_container:
                if titulo_input.value:
                    ui.label(titulo_input.value.upper()).classes('text-sm font-bold text-cyan-4 tracking-wider q-mb-sm text-center')
                
                # Image
                ui.image(img_src).style(f'width: {size_select.value}px; height: {size_select.value}px; max-width: 100%; border-radius: 8px; border: 2px solid {THEME["accent"]};')
                
                # Download button
                def download():
                    ui.download(img_src, 'qrcode.png')
                
                ui.button('Baixar QR Code', on_click=download, icon='download').props('unelevated color=cyan-8 text-color=white').classes('q-mt-md full-width')
        
        def limpar():
            url_input.value = ''
            titulo_input.value = ''
            size_select.value = 400
            preview_container.clear()
            
        with ui.row().classes('w-full justify-between gap-4'):
            ui.button('Limpar', on_click=limpar, icon='clear').props('flat color=grey').classes('flex-grow')
            ui.button('Gerar QR Code', on_click=gerar_qrcode, icon='qr_code').props('unelevated color=cyan').classes('flex-grow')

