# -*- coding: utf-8 -*-
"""
Created on Fri Apr 19 18:38:43 2019

@author: Scarlet
"""

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
    hexList = [eval('0x'+quadro[i:i+2]) for i in range(0, len(quadro), 2)]    
    return hexList

def unstuff (frame):
    unstuffingList = []
    i = 5
    shift = 0
    while i < len(frame)-1:
        if frame[i] == DLE:
            unstuffingList.append(i)
            i += 1
        i += 1
    for item in unstuffingList:
        frame.pop(item-shift)
        shift += 1

def checksum(quadro):
    tamanho = len(quadro)
    posicao = 0
    soma = 0   
    while tamanho > 1:
        bh = quadro[posicao]
        bl = quadro[posicao+1]
        posicao = posicao + 2
        tamanho = tamanho - 2
        soma = soma + (bh << 8) + bl    
    if tamanho > 0:
        soma = soma + quadro[posicao]   
    while (soma >> 16):
        soma = (soma & 0xffff) + (soma >> 16)   
    soma = 0xffff - soma    
    byte1 = soma >> 8
    byte2 = soma & 0xff   
    return byte1, byte2

def checksumValido(quadroInteiro):
    
    quadroDcd = decode16(quadroInteiro)
    quadroDcd[3] = 0
    quadroDcd[4] = 0
    b1, b2 = checksum(quadroDcd)
                        
    if (b1 == quadroDcd[3]) & (b2 == quadroDcd[4]):
        return True
    else:
        return False
    
def escreveDados(saida, quadro):    
    quadroDcd = decode16(quadro) 
    tam = len(quadroDcd)
    dados = quadroDcd[5:(tam-1)] 
    dadosB = [dados[i].to_bytes(1, byteorder='big') for i in range(0, len(dados))]

    for byte in dadosB:
        saida.write(byte)
    
    print("Fim da escrita do quadro na saida.")
    

def trocaMensagens(s, arquivoE, arquivoS):
    IDe = 0
    IDr = 0
    entrada = open(arquivoE, "rb")
    saida = open(arquivoS, "wb")
    ack = False
    
    s.settimeout(2)

    quadro = constroiQuadroDados(entrada, IDe)
    quadro16 = encode16(quadro)
    s.send(quadro16.encode('ascii')) # Envia o primeiro quadro
    
    while True:
        while not ack: # Enquanto não receber ack do quadro enviado:
            try:
                byte = s.recv(2) # Recebe um byte
                byteH = byte.decode('ascii')
                if byteH == 'cc': # SOF, inicio de quadro
                    quadro, flags = leQuadro(s, IDr, IDe)
                    if quadro == '': # Quadro descartado
                        print("Quadro descartado")
                        break
                    # Se recebeu um quadro de dados, escrever
                    # no arquivo de saida
                    else:
                        # Recebeu um quadro valido
                        if flags == '7f': # Quadro de dados
                            print("Quadro de dados valido recebido. ")
                            
                            ##### SOMENTE DAZER ISSO DEPOIS
                            ##### DE UNSTUFFING!!!!!!!!!!!!!!!
                            
                            escreveDados(saida, quadro)
                            # Escreve no arquivo de saida
                        else: # Quadro ack
                            print("Quadro ack valido recebido.")
                            #### CRIAR OUTRO QUADRO
                            ### ENVIAR QUADRO
                            ack = True # Sai do loop e entra de novo
                        # Envia mais um quadro
                else:
                    print("") # Continua recebendo bytes ate receber um inicio de quadro
                    
            except socket.timeout as t:
                print(t)    
                #retransmite quadro
                s.send(quadro16.encode('ascii'))
      
        #transmite proximo quadro
    
def leQuadro(s, IDr, IDe):
    quadroInteiro = 'cc'
    flags = '' # Inicializacao
    msg = s.recv(2)
    ID = msg.decode('ascii')
    quadroInteiro = quadroInteiro + ID
    #recebe o resto do quadro até EOF
    while True:
        msg = s.recv(2)
        flags = msg.decode('ascii')
        quadroInteiro += flags
        
        if flags == '7f': # QUADRO DE DADOS
            # continua lendo dados 
            # TESTA ID
            if ID == IDr: # Se for o ID esperado, continua           
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
                    elif dado == 'cd': # EOF CUIDADO COM OS DLE
                        print("Final do quadro de dados encontrado.")
                        if checksumValido(quadroInteiro):
                            print("Quadro de dados com checksum valido!")
                            return quadroInteiro, flags
                        else:
                            print("Checksum invalido! Quadro de dados descartado")
                            return '', flags
                    elif i > 512:
                        print("EOF não encontrado, quadro de dados descartado.")
                        return '', flags
                    i += 1               
            else:
                print("Quadro de dados descartado, recebido com ID errado.")
                return ''  , flags             
        elif flags == '80': # QUADRO ACK          
            if ID == IDe: # Se o ID do quadro for o ID de dados esperado continua
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
                        return '', flags                   
                else:
                    print("Erro no quadro ACK.")
                    return '', flags
            else:
                print("Quadro ACk descartado, recebido com ID errado")
                return '', flags               
    print("ERRO")
    return '', flags

def leBytes1(arquivoE, n):
    with open(arquivoE, "rb") as entrada:
        data = entrada.read(n)
    
    entrada.close()
    return data

def escreveBytes1(arquivoS, data, n):
    with open(arquivoS, "wb") as saida:
        saida.write(data)
    
    saida.close()

def troca(c, arquivoE, arquivoS):
    envia(c, arquivoE)
    recebe(c, arquivoS)

def envia(c, arquivoE): 
    frame = leBytes1(arquivoE, 10)
    c.send(frame)

def recebe(c, arquivoS):
    msg = c.recv(2)
    escreveBytes1(arquivoS, msg, 10)

def main(): 
    if sys.argv[1] == "-s":
        porta = int(sys.argv[2])
        endereco = ("", porta)
        print("Servidor: porta "+str(porta))
        
        ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        endereco = ("", porta)
        ss.bind(endereco)
        ss.listen(1)
        
        print("Esperando um cliente...")

        s, cliente = ss.accept()
        print("Conectado a {}".format(cliente))
        
        entrada = sys.argv[3]
        saida = sys.argv[4]
        
        troca(s, entrada, saida)
        
        s.close()
        ss.close()
        
    elif sys.argv[1] == "-c":
        IP, porta = sys.argv[2].split(':')
        print("Cliente: end IP: "+IP+" e porta: "+porta)
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        endServidor = (IP, int(porta))
        s.connect(endServidor)
        
        entrada = sys.argv[3]
        saida = sys.argv[4]
        
        troca(s, entrada, saida)
        
        s.close()   
    else:
        print("Comando invalido. Utilize '-s <PORT> <INPUT> <OUTPUT>' ou '-c <IP>:<PORT> <INPUT> <OUTPUT>'")
        exit(1)

if __name__ == "__main__":
    main()