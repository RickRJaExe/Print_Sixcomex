import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# --- Dependências de Playwright e Mapeadores ---
from playwright.sync_api import sync_playwright
from di_mapeadores import mapear_xml_formato_1, mapear_xml_formato_2 

# --- SOLUÇÃO CRÍTICA PARA PYINSTALLER (PLAYWRIGHT FIX) ---
# Este bloco garante que, quando o código é executado como um .exe, 
# ele procure o navegador Chromium (na pasta 'chrome-win') no local correto.
import sys
import os

if getattr(sys, 'frozen', False):
    # 'frozen' é True quando rodando como executável (PyInstaller)
    base_path = os.path.dirname(sys.executable)
    
    # 1. Define o local onde o Playwright deve procurar os binários.
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(base_path, 'chrome-win')
    
    # 2. Define a variável global com o caminho COMPLETO do executável principal.
    # Isto corrige o erro de nome ("headless_shell.exe" vs "chrome.exe").
    GLOBAL_CHROME_PATH = os.path.join(os.environ['PLAYWRIGHT_BROWSERS_PATH'], 'chrome.exe')
else:
    # Se estiver rodando como script normal, usa o padrão do Playwright.
    GLOBAL_CHROME_PATH = None
# --------------------------------------------------------

# =================================================================
# FUNÇÕES DE MANIPULAÇÃO DE DADOS E CAPTURA
# =================================================================

def ler_dados_xml(caminho_xml):
    """Detecta o formato do XML e chama o mapeador correto."""
    
    try:
        tree = ET.parse(caminho_xml)
        root = tree.getroot()
        
        # --- LÓGICA DE DETECÇÃO ---
        
        # Formato 1: REGISTRO_DI_004294... (tag <listaDeclaracoesTransmissao>)
        if root.tag == 'listaDeclaracoesTransmissao':
            declaracao_element = root.find('./declaracao')
            if declaracao_element is not None:
                print("[Detectado: Formato XML 1 (Antigo)]")
                return mapear_xml_formato_1(declaracao_element)
            
        # Formato 2: DI XML 25_2240678-6.xml (tag <ListaDeclaracoes>)
        elif root.tag == 'ListaDeclaracoes':
            declaracao_element = root.find('./declaracaoImportacao')
            if declaracao_element is not None:
                print("[Detectado: Formato XML 2 (Novo)]")
                return mapear_xml_formato_2(declaracao_element)

        # Se não detectar, lança erro
        raise ValueError("Estrutura XML da DI não reconhecida. Adicione um novo mapeador para esta estrutura.")

    except ET.ParseError as e:
        raise Exception(f"Erro ao parsear XML. Arquivo corrompido ou formato inválido: {e}")
    except Exception as e:
        raise Exception(f"Erro na detecção ou mapeamento do XML: {e}")

def preencher_html(dados, caminho_html):
    """Carrega o template HTML e substitui os placeholders pelos dados."""
    html_content = Path(caminho_html).read_text(encoding='utf-8')
    
    html_preenchido = html_content
    for key, value in dados.items():
        placeholder = f"${{{key}}}"
        html_preenchido = html_preenchido.replace(placeholder, str(value))
        
    return html_preenchido

def capturar_secao(html_preenchido, nome_saida):
    """Renderiza o HTML e tira um screenshot da página completa (#pagina-consulta)."""
    temp_html_path = Path("temp_preenchido.html")
    temp_html_path.write_text(html_preenchido, encoding='utf-8')

    print("Renderizando HTML e capturando screenshot da página inteira...")
    with sync_playwright() as p:
        
        # --- A CORREÇÃO DE EXECUÇÃO ESTÁ AQUI: FORÇAMOS O CAMINHO CORRETO ---
        launch_args = {}
        if GLOBAL_CHROME_PATH and os.path.exists(GLOBAL_CHROME_PATH):
            launch_args['executable_path'] = GLOBAL_CHROME_PATH
            
        browser = p.chromium.launch(
            headless=True,
            **launch_args # Adiciona o caminho do executável se estiver definido
        ) 
        # -----------------------------------------------------------------
        
        page = browser.new_page()
        page.goto(f"file:///{temp_html_path.resolve()}")
        page.wait_for_timeout(500) 
        
        element = page.locator("#pagina-consulta") 
        element.screenshot(path=nome_saida)
        
        browser.close()
    
    temp_html_path.unlink()
    return nome_saida


# =================================================================
# INTERFACE GRÁFICA (Tkinter)
# =================================================================

class DIApp:
    def __init__(self, master):
        self.master = master
        master.title("Gerador de Comprovante DI")
        master.geometry("400x150") 
        
        self.label = tk.Label(master, text="Selecione o arquivo XML da Declaração de Importação:", font=('Arial', 10))
        self.label.pack(pady=10)

        self.btn_selecionar = tk.Button(master, text="Selecionar Arquivo DI (XML)", command=self.processar_di, font=('Arial', 12, 'bold'), bg='lightblue')
        self.btn_selecionar.pack(pady=10)

        self.status_label = tk.Label(master, text="Aguardando seleção...", fg="gray")
        self.status_label.pack(pady=5)

    def processar_di(self):
        """Função que gerencia o fluxo completo: Seleção -> Leitura -> Geração -> Screenshot."""
        
        caminho_xml = filedialog.askopenfilename(
            defaultextension=".xml",
            filetypes=[("Arquivos XML", "*.xml"), ("Todos os arquivos", "*.*")]
        )
        
        if not caminho_xml:
            self.status_label.config(text="Operação cancelada.", fg="gray")
            return

        caminho_html_template = 'index.html'
        nome_imagem_saida = Path(caminho_xml).stem + '_Capturado.png'
        
        self.status_label.config(text="Processando... (Pode levar alguns segundos)", fg="blue")
        self.master.update() 

        try:
            # 2. LER E PREENCHER DADOS
            dados_di = ler_dados_xml(caminho_xml)
            html_final = preencher_html(dados_di, caminho_html_template)
            
            # 3. CAPTURAR IMAGEM
            caminho_saida = capturar_secao(html_final, nome_imagem_saida)
            
            self.status_label.config(text=f"SUCESSO! Imagem salva como: {caminho_saida}", fg="green")
            messagebox.showinfo("Concluído", f"A imagem da DI foi salva com sucesso!\nArquivo: {caminho_saida}")

        except Exception as e:
            self.status_label.config(text="ERRO. Verifique o console.", fg="red")
            messagebox.showerror("Erro de Processamento", f"Ocorreu um erro: {e}")
            print(f"Erro detalhado: {e}")

# --- INICIAR A APLICAÇÃO ---
if __name__ == "__main__":
    root = tk.Tk()
    app = DIApp(root)
    root.mainloop()