import xml.etree.ElementTree as ET
from datetime import datetime

# --- FUNÇÕES DE FORMATAÇÃO (REUTILIZÁVEIS) ---

def formatar_valor(valor_str):
    if not valor_str or not valor_str.strip('0'):
        return '0,00'
    valor_limpo = valor_str.lstrip('0').zfill(3) 
    inteiro = valor_limpo[:-2]
    decimal = valor_limpo[-2:]
    inteiro_formatado = f"{int(inteiro):,}".replace(",", ".")
    return f"{inteiro_formatado},{decimal}"

def formatar_data(data_str):
    if not data_str or data_str == '00000000' or len(data_str) != 8:
        return ''
    ano = data_str[0:4]
    mes = data_str[4:6]
    dia = data_str[6:8]
    return f"{dia}/{mes}/{ano}"

# --- Mapeamento de Códigos para Nomes (para fins de demonstração) ---
TIPO_DOC_CARGA = {'03': 'House Bill of Lading', '01': 'Master Airway Bill'} 
UTILIZACAO = {'1': 'Total'} 

# ===================================================================
# MAPEADOR DO FORMATO 1 (Ex: REGISTRO_DI_004294_BNSK25090295.XML)
# ===================================================================

def mapear_xml_formato_1(declaracao_element):
    """Mapeia os dados do XML que usa tags como codigoBancoPagamentoTributo."""
    
    def get_text(tag, element=declaracao_element, default=''):
        return element.findtext(tag) or default
        
    pagamento = declaracao_element.find('./pagamento')
    
    # DADOS BÁSICOS (Mapeamento do primeiro XML, simplificado)
    dados = {
        'INFO_USUARIO': 'CELIOMAR GOMES DA SILVA - 385.342.402-30',
        'INFO_DATA_HORA': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'DI_NUMERO': get_text('numeroDocumentoCargaMaster'),
        'IMPORTADOR_CNPJ': get_text('numeroImportador'),
        'IMPORTADOR_NOME': 'LG ELECTRONICS DO BRASIL LTDA (F1)',
        'ENDERECO': 'SIMULADO ENDERECO FORMATO 1',
        'RESPONSAVEL_CPF': get_text('numeroCpfRepresentanteLegal'),
        'RESPONSAVEL_NOME': 'CELIOMAR GOMES DA SILVA (F1)',
        'LOCAL_EMBARQUE': get_text('nomeLocalEmbarque'),
        'DATA_EMBARQUE': formatar_data(get_text('dataEmbarque')),
        'TIPO_CONHECIMENTO_CODIGO': get_text('codigoTipoDocumentoCarga'),
        'TIPO_CONHECIMENTO_NOME': TIPO_DOC_CARGA.get(get_text('codigoTipoDocumentoCarga'), 'N/D'),
        'UTILIZACAO_NOME': UTILIZACAO.get(get_text('codigoUtilizacaoDocumentoCarga'), 'N/D'),
        'ID_CONHECIMENTO': get_text('numeroDocumentoCarga'),

        'REF_RECEITA': '00', 'TIPO_PAGAMENTO': 'Débito em Conta', 'ICONE_DADOS_BANCARIOS': '+',
        'VLR_RECEITA': '', 'DATA_PAGAMENTO': '',
        'VALOR_RECEITA_VALOR': '0,00', 'JUROS': '0,00', 'MULTA': '0,00', 'VALOR_TOTAL': '0,00',
        'BANCO': '', 'AGENCIA': '', 'CONTA_CORRENTE': '',
    }
    
    if pagamento is not None:
        def get_pagamento_text(tag, default=''):
             return pagamento.findtext(tag) or default

        dados.update({
            'VLR_RECEITA': get_pagamento_text('codigoReceitaPagamento', default='7811'),
            'DATA_PAGAMENTO': formatar_data(get_pagamento_text('dataPagamentoTributo')),
            
            'VALOR_RECEITA_VALOR': formatar_valor(get_pagamento_text('valorTributoPago')),
            'JUROS': formatar_valor(get_pagamento_text('valorJurosPagamentoTributo')),
            'MULTA': formatar_valor(get_pagamento_text('valorMultaPagamentoTributo')),
            'VALOR_TOTAL': formatar_valor(get_pagamento_text('valorTributoPago')), 

            'BANCO': get_pagamento_text('codigoBancoPagamentoTributo'),
            'AGENCIA': get_pagamento_text('numeroAgenciaPagamentoTributo'),
            'CONTA_CORRENTE': get_pagamento_text('numeroContaPagamentoTributario')[-9:].lstrip('0') or '', 
        })
    return dados


# ===================================================================
# MAPEADOR DO FORMATO 2 (Ex: DI XML 25_2240678-6.xml)
# ===================================================================

def mapear_xml_formato_2(declaracao_element):
    """Mapeia os dados do XML que usa tags como bancoPagamento."""
    
    def get_text(tag, element=declaracao_element, default=''):
        return element.findtext(tag) or default

    pagamento = declaracao_element.find('./pagamento')

    # DADOS BÁSICOS (Mapeamento do último XML)
    dados = {
        'INFO_USUARIO': f"{get_text('importadorNomeRepresentanteLegal')} - {get_text('importadorCpfRepresentanteLegal')[:3]}.***.***-{get_text('importadorCpfRepresentanteLegal')[-2:]}",
        'INFO_DATA_HORA': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'DI_NUMERO': f"{get_text('numeroDI')[:2]}/{get_text('numeroDI')[2:]}-{get_text('sequencialRetificacao')} 00",
        
        'IMPORTADOR_CNPJ': f"{get_text('importadorNumero')[:2]}.{get_text('importadorNumero')[2:5]}.{get_text('importadorNumero')[5:8]}/{get_text('importadorNumero')[8:12]}-{get_text('importadorNumero')[12:]}",
        'IMPORTADOR_NOME': get_text('importadorNome'),
        'ENDERECO': f"{get_text('importadorEnderecoLogradouro')}, {get_text('importadorEnderecoNumero')}, {get_text('importadorEnderecoBairro')}, CEP: {get_text('importadorEnderecoCep')}, {get_text('importadorEnderecoMunicipio')}, {get_text('importadorEnderecoUf')}",
        'RESPONSAVEL_CPF': get_text('importadorCpfRepresentanteLegal'),
        'RESPONSAVEL_NOME': get_text('importadorNomeRepresentanteLegal'),
        
        'LOCAL_EMBARQUE': get_text('conhecimentoCargaEmbarqueLocal'),
        'DATA_EMBARQUE': formatar_data(get_text('conhecimentoCargaEmbarqueData')),
        'TIPO_CONHECIMENTO_CODIGO': get_text('conhecimentoCargaTipoCodigo'),
        'TIPO_CONHECIMENTO_NOME': get_text('conhecimentoCargaTipoNome'),
        'UTILIZACAO_NOME': UTILIZACAO.get(get_text('conhecimentoCargaUtilizacao'), 'N/D'),
        'ID_CONHECIMENTO': get_text('conhecimentoCargaIdMaster'),
        
        'REF_RECEITA': '00', 'TIPO_PAGAMENTO': 'Débito em Conta', 'ICONE_DADOS_BANCARIOS': '+',
        'VLR_RECEITA': '', 'DATA_PAGAMENTO': '',
        'VALOR_RECEITA_VALOR': '0,00', 'JUROS': '0,00', 'MULTA': '0,00', 'VALOR_TOTAL': '0,00',
        'BANCO': '', 'AGENCIA': '', 'CONTA_CORRENTE': '',
    }

    if pagamento is not None:
        def get_pagamento_text(tag, default=''):
             return pagamento.findtext(tag) or default
        
        dados.update({
            'VLR_RECEITA': get_pagamento_text('codigoReceita', default='7811'),
            'DATA_PAGAMENTO': formatar_data(get_pagamento_text('dataPagamento')),
            
            'VALOR_RECEITA_VALOR': formatar_valor(get_pagamento_text('valorReceita')),
            'JUROS': formatar_valor(get_pagamento_text('valorJurosEncargos')),
            'MULTA': formatar_valor(get_pagamento_text('valorMulta')),
            'VALOR_TOTAL': formatar_valor(get_pagamento_text('valorReceita')), 

            'BANCO': get_pagamento_text('bancoPagamento'),
            'AGENCIA': get_pagamento_text('agenciaPagamento'),
            'CONTA_CORRENTE': get_pagamento_text('contaPagamento').strip()[-9:].lstrip('0') or '', 
        })
    return dados