import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# --- (Playwright é usado para renderizar o HTML e tirar a foto) ---
from playwright.sync_api import sync_playwright

# =================================================================
# FUNÇÕES DE FORMATAÇÃO E MANIPULAÇÃO DE DADOS
# =================================================================

def formatar_valor(valor_str):
    """
    Formata valores de string zero-padded (ex: '000000000019279') para moeda (ex: '192,79').
    """
    if not valor_str or not valor_str.strip('0'):
        return '0,00'
    
    valor_limpo = valor_str.lstrip('0').zfill(3) 
    inteiro = valor_limpo[:-2]
    decimal = valor_limpo[-2:]
    
    inteiro_formatado = f"{int(inteiro):,}".replace(",", ".")
    
    return f"{inteiro_formatado},{decimal}"

def formatar_data(data_str):
    """
    Formata data de string AAAAMMDD (ex: '20251013') para DD/MM/AAAA.
    """
    if not data_str or data_str == '00000000' or len(data_str) != 8:
        return ''
        
    ano = data_str[0:4]
    mes = data_str[4:6]
    dia = data_str[6:8]
    return f"{dia}/{mes}/{ano}"

# Mantenha as funções de formatação (formatar_valor e formatar_data) como estão!

def ler_dados_xml(caminho_xml):
    """Lê o XML com o novo formato e extrai todos os dados necessários."""
    
    try:
        tree = ET.parse(caminho_xml)
        declaracao = tree.find('./declaracaoImportacao') # NÓ RAIZ MUDOU
        if declaracao is None:
             raise ValueError("Tag <declaracaoImportacao> não encontrada.")

        # --- FUNÇÕES DE BUSCA SEGURA ---
        def get_text(tag, element=declaracao, default=''):
            return element.findtext(tag) or default
        
        # Mapeamento de Códigos (Valores de Carga)
        UTILIZACAO = {'1': 'Total'} 

        # --- DADOS EXTRAÍDOS ---
        
        # A. DADOS GERAIS e CABEÇALHO
        # Usamos o nome do representante legal no cabeçalho
        dados = {
            'INFO_USUARIO': f"{get_text('importadorNomeRepresentanteLegal')} - {get_text('importadorCpfRepresentanteLegal')[:3]}.***.***-{get_text('importadorCpfRepresentanteLegal')[-2:]}",
            'INFO_DATA_HORA': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'DI_NUMERO': f"{get_text('numeroDI')[:2]}/{get_text('numeroDI')[2:]}-{get_text('sequencialRetificacao')} 00", # Formata a DI: 25/2240678-6 00
            
            # B. DADOS DO IMPORTADOR
            'IMPORTADOR_CNPJ': f"{get_text('importadorNumero')[:2]}.{get_text('importadorNumero')[2:5]}.{get_text('importadorNumero')[5:8]}/{get_text('importadorNumero')[8:12]}-{get_text('importadorNumero')[12:]}",
            'IMPORTADOR_NOME': get_text('importadorNome'),
            'ENDERECO': f"{get_text('importadorEnderecoLogradouro')}, {get_text('importadorEnderecoNumero')}, {get_text('importadorEnderecoBairro')}, CEP: {get_text('importadorEnderecoCep')}, {get_text('importadorEnderecoMunicipio')}, {get_text('importadorEnderecoUf')}",
            'RESPONSAVEL_CPF': get_text('importadorCpfRepresentanteLegal'),
            'RESPONSAVEL_NOME': get_text('importadorNomeRepresentanteLegal'),
            
            # C. DADOS DO CONHECIMENTO DE CARGA
            'LOCAL_EMBARQUE': get_text('conhecimentoCargaEmbarqueLocal'),
            'DATA_EMBARQUE': formatar_data(get_text('conhecimentoCargaEmbarqueData')),
            'TIPO_CONHECIMENTO_CODIGO': get_text('conhecimentoCargaTipoCodigo'),
            'TIPO_CONHECIMENTO_NOME': get_text('conhecimentoCargaTipoNome'),
            'UTILIZACAO_NOME': UTILIZACAO.get(get_text('conhecimentoCargaUtilizacao'), 'N/D'),
            'ID_CONHECIMENTO': get_text('conhecimentoCargaIdMaster'), # ID do Master

            # D. DADOS DO PAGAMENTO (Novo formato de tags)
            'REF_RECEITA': '00', # Fixo
            'TIPO_PAGAMENTO': 'Débito em Conta', # Fixo
            'ICONE_DADOS_BANCARIOS': '+', # Fixo
        }

        pagamento = declaracao.find('./pagamento')
        if pagamento is not None:
            # Busca do pagamento
            def get_pagamento_text(tag, default=''):
                 return pagamento.findtext(tag) or default
            
            dados.update({
                # Tabela de Pagamento (com formatação):
                'VLR_RECEITA': get_pagamento_text('codigoReceita', default='7811'), # Tag diferente
                'DATA_PAGAMENTO': formatar_data(get_pagamento_text('dataPagamento')), # Tag diferente
                
                # Valores Monetários
                'VALOR_RECEITA_VALOR': formatar_valor(get_pagamento_text('valorReceita')), # Tag diferente
                'JUROS': formatar_valor(get_pagamento_text('valorJurosEncargos')), # Tag diferente
                'MULTA': formatar_valor(get_pagamento_text('valorMulta')), # Tag diferente
                # O Valor Total é a soma dos três, mas como juros/multa são 0, o valor é o valorReceita
                'VALOR_TOTAL': formatar_valor(get_pagamento_text('valorReceita')), 

                # Dados Bancários
                'BANCO': get_pagamento_text('bancoPagamento'), # Tag diferente
                'AGENCIA': get_pagamento_text('agenciaPagamento'), # Tag diferente
                # Pega os 9 últimos dígitos e remove zeros à esquerda
                'CONTA_CORRENTE': get_pagamento_text('contaPagamento').strip()[-9:].lstrip('0') or '', 
            })
        
        return dados
        
    except Exception as e:
        raise Exception(f"Erro ao ler ou mapear o XML: {e}")

# Mantenha o restante do di_app.py (preencher_html, capturar_secao, DIApp e if __name__)

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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file:///{temp_html_path.resolve()}")
        page.wait_for_timeout(500) 
        
        # Captura o elemento principal da página
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
        master.geometry("400x150") # Tamanho da janela
        
        # Estilo para os labels
        self.label = tk.Label(master, text="Selecione o arquivo XML da Declaração de Importação:", font=('Arial', 10))
        self.label.pack(pady=10)

        # Botão de Ação
        self.btn_selecionar = tk.Button(master, text="Selecionar Arquivo DI (XML)", command=self.processar_di, font=('Arial', 12, 'bold'), bg='lightblue')
        self.btn_selecionar.pack(pady=10)

        # Label de Status
        self.status_label = tk.Label(master, text="Aguardando seleção...", fg="gray")
        self.status_label.pack(pady=5)

    def processar_di(self):
        """Função que gerencia o fluxo completo: Seleção -> Leitura -> Geração -> Screenshot."""
        
        # 1. SELEÇÃO DO ARQUIVO
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
        self.master.update() # Atualiza a UI para mostrar a mensagem de status

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