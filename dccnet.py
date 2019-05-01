#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
UFMG - ICEx - DCC - Redes de Computadores - 2019/1

TP1: DCCNET -- Camada de Enlace

Aluna: Scarlet Gianasi Viana
Matrícula: 2016006891

Versão utilizada: Python 3.6.7

'''
import sys
import socket

SOF = 204
EOF = 205
DLE = 27
flagDados = 127
flagAck = 128

def leDados(entrada):    
    dados = []
    tamanho = 0    
    while tamanho < 512:
        segmento = entrada.read(1)
        if segmento == b'':
            print("Fim de arquivo")
            break
        # Bytestuffing
        elif (ord(segmento) == EOF) | (ord(segmento) == DLE):
            if tamanho < 511:
                dados.append(DLE)
                dados.append(ord(segmento))
                tamanho += 2
            else:
                entrada.seek(-1, 1)
                break
        else:
            dados.append(ord(segmento))
            tamanho += 1  
    return tamanho, dados

def constroiQuadroDados(entrada, ID):    
    quadro = []
    cabecalho = [SOF, ID, flagDados, 0, 0]    
    tam, dados = leDados(entrada)    
    if tam > 0:
        quadro = cabecalho + dados + [EOF]        
        b1, b2 = checksum(quadro)       
        quadro[3] = b1
        quadro[4] = b2   
    else:
        entrada.close()
        print("Fim do arquivo.")       
    return quadro

def constroiQuadroAck(ID): 
    quadro = [SOF, ID, flagAck, 0, 0, EOF]   
    b1, b2 = checksum(quadro)    
    quadro[3] = b1
    quadro[4] = b2    
    return quadro

def encode16 (hexList):
    tabela = '0123456789abcdef'
    frame = ''   
    for byte in hexList:
        nibbleH = tabela[(byte >> 4) & 0x0f]
        nibbleL = tabela[(byte & 0x0f)]        
        frame = frame + nibbleH + nibbleL    
    return frame

def decode16(quadro):   
    quadroDecoded = [eval('0x'+quadro[i:i+2]) for i in range(0, len(quadro), 2)]    
    return quadroDecoded

def unstuff (quadro):
    unstuffingList = []
    i = 5
    shift = 0
    while i < len(quadro)-1:
        if quadro[i] == DLE:
            unstuffingList.append(i)
            i += 1
        i += 1
    for item in unstuffingList:
        quadro.pop(item-shift)
        shift += 1

def checksum(quadro):
    tamanho = len(quadro)
    posicao = 0
    soma = 0      
    while tamanho > 1:
        bh = quadro[posicao]
        bl = quadro[posicao+1]
        posicao += 2
        tamanho -= 2
        soma += (bh << 8) + bl         
    if tamanho > 0:
        soma += quadro[posicao]         
    while (soma >> 16):
        soma = (soma & 0xffff) + (soma >> 16)       
    soma = 0xffff - soma    
    byte2 = soma >> 8
    byte1 = soma & 0xff  
    return byte1, byte2

def checksumValido(quadroInteiro):
    quadroDcd = decode16(quadroInteiro)
    byte1, byte2 = checksum(quadroDcd)
    if (byte1 == 0) & (byte2 == 0):
        return True
    else:
        return False
    
def escreveDados(arquivoS, quadroDcd):    
    tam = len(quadroDcd)
    dados = quadroDcd[5:(tam-1)] 
    dadosB = [dados[i].to_bytes(1, byteorder='big') for i in range(0, len(dados))]  
    with open(arquivoS, "ab") as saida: 
        for byte in dadosB:
            saida.write(byte)  
    print("Fim da escrita do quadro na saida.")

def enviaQuadro(s, quadro):
    quadroEnc = encode16(quadro)
    print(quadroEnc)
    s.send(quadroEnc.encode('ascii'))
    
def leQuadro(s, IDenviado, IDreceptor):
    quadroInteiro = 'cc' # SOF
    flags = '' # Inicializacao
    msg = s.recv(2)
    ID = msg.decode('ascii')
    print("ID:"+str(ID))
    quadroInteiro = quadroInteiro + ID
    checksumAnterior = ''
    #recebe o resto do quadro até EOF
    while True:
        msg = s.recv(2)
        flags = msg.decode('ascii')
        quadroInteiro += flags       
        if flags == '7f': # QUADRO DE DADOS
            if int(ID) == IDenviado: #receptor: # Se for o ID esperado, continua           
                msg = s.recv(4)
                checksum = msg.decode('ascii')                
                quadroInteiro += checksum                
                i = 5     
                while True:
                    msg = s.recv(2)
                    dado = msg.decode('ascii')
                    quadroInteiro += dado
                    if dado == '1b': # se DLE
                        i += 1
                        msg = s.recv(2)
                        dadoEsc = msg.decode('ascii')
                        quadroInteiro += dadoEsc # Le o outro dado ignorando proximo
                    elif dado == 'cd': # Se EOF 
                        print("Final do quadro de dados encontrado.")                   
                        if checksumValido(quadroInteiro):
                            print("Quadro de dados com checksum valido!")
                            checksumAnterior = checksum
                            return quadroInteiro, flags
                        else:
                            print("Checksum invalido! Quadro de dados descartado")
                            return [], flags
                    elif i > 518:
                        print("EOF não encontrado, quadro de dados descartado.")
                        return [], flags
                    i += 1               
            else:
                # DETECTAR RETRANSMISSAO
                msg = s.recv(4)
                checksum = msg.decode('ascii')
                if checksum == checksumAnterior:
                    print("Retransmissão detectada. Enviando outro quadro ack.")
                    quadroAck = constroiQuadroAck(int(ID))
                    enviaQuadro(s, quadroAck)
                    return [], flags                  
                else:                
                    print("Quadro de dados descartado, recebido com ID errado.")
                    return [], flags             
        elif flags == '80': # ACK        
            if int(ID) == IDreceptor: #enviado: 
                msg = s.recv(4)
                checksum = msg.decode('ascii')                
                msg = s.recv(2)
                byte = msg.decode('ascii')                
                if byte == 'cd':
                    quadroInteiro += checksum + byte
                    print("Final do quadro ACK encontrado.")                   
                    if checksumValido(quadroInteiro):
                        print("Quadro ack com checksum valido!")
                        return quadroInteiro, flags
                    else:
                        print("Checksum invalido! Quadro ack descartado")
                        return [], flags                   
                else:
                    print("Erro no quadro ACK.")
                    return [], flags
            else:                
                print("Quadro Ack descartado, recebido com ID errado")
                print(IDenviado)
                return [], flags               
    print("ERRO")
    return [], flags

def iniciaTroca(s, arquivoE, arquivoS):   
    IDenviado = 0
    IDreceptor = 0
    entrada = open(arquivoE, "rb")
    if not entrada:
        print("Arquivo de entrada invalido.")
        return
    primeiroQuadro = constroiQuadroDados(entrada, IDenviado)   
    if primeiroQuadro == []:
        print("Arquivo de entrada vazio. Nao ha quadros para enviar.")
    else:
        print("Enviando quadro.")
        enviaQuadro(s, primeiroQuadro)     
        trocaMensagens(s, primeiroQuadro, entrada, arquivoS, IDenviado, IDreceptor)
    
def trocaMensagens(s, primeiroQuadro, entrada, arquivoS, IDenviado, IDreceptor):   
    quadroAtual = primeiroQuadro   
    while True:
        byte = s.recv(2)
        byteHex = byte.decode('ascii')        
        if byteHex == 'cc': # Inicio de quadro encontrado
            print("Inicio de quadro.")
            quadroLido, flags = leQuadro(s, IDenviado, IDreceptor)            
            if quadroLido != []:
                #print("Quadro invalido. Descartado.")
            #else: # QUadro valido
                if flags == '7f':  # DADOS
                    print("Quadro de dados recebido com sucesso.")
                    quadroDecoded = decode16(quadroLido)
                    unstuff(quadroDecoded)
                    escreveDados(arquivoS, quadroDecoded)
                    
                    print("Enviando quadro ACK.")
                    quadroAck = constroiQuadroAck(IDenviado)
                    enviaQuadro(s, quadroAck)   
                    IDenviado = 1 - IDenviado # Troca o ID de recebimento
                else:  
                    print("Quadro ack recebido com sucesso.")
                    IDreceptor = 1 - IDreceptor # Troca ID de envio
                    novoQuadro = constroiQuadroDados(entrada, IDreceptor)                    
                    if novoQuadro == []:
                        print("Arquivo de entrada vazio. Nao ha quadros para enviar.")
                    else:
                        print("Enviando quadro.")                        
                        quadroAtual = novoQuadro
                        enviaQuadro(s, quadroAtual)
                
def main():    
    if len(sys.argv) < 4:
        print("Erro: número de argumentos insuficiente.")
        return   
    entrada = sys.argv[3]
    saida = sys.argv[4]   
    if entrada == saida:
        print("Erro: não é possível utilizar o mesmo arquivo como entrada e saída.")
        return    
    elif sys.argv[1] == "-s":
        porta = int(sys.argv[2])
        endereco = ("", porta)
        print("Servidor: porta "+str(porta))
        ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    
        endereco = ("", porta)
        ss.bind(endereco)
        ss.listen(1)       
        print("Esperando o cliente...")
        s, cliente = ss.accept()
        s.settimeout(None)
        print("Conectado a {}".format(cliente))  
    elif sys.argv[1] == "-c":
        IP, porta = sys.argv[2].split(':')
        print("Cliente: end IP: "+IP+" e porta: "+porta)      
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
        endServidor = (IP, int(porta))
        s.connect(endServidor)
        s.settimeout(None)             
    else:
        print("Comando invalido.")
        return      
    try:
        iniciaTroca(s, entrada, saida)
    except (KeyboardInterrupt, socket.error):
        print("Finalizando o programa...")
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        if sys.argv[1] == "-s":
            ss.close()    

if __name__ == "__main__":
    main()
