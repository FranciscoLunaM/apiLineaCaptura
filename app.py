from flask import Flask,request
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv
import base64
import os
import socket
from waitress import serve
import consul
import logging

#Get all variables from env
load_dotenv()
apiKey=os.getenv("APIKEY")
sessionKeyAbordaje=os.getenv("SESSIONKEY")
canalKey=os.getenv("CANALKEY")
rutaToken=os.getenv("RUTA_TOKEN")
consulIp=os.getenv("CONSUL_IP")
consulPort=os.getenv("CONSUL_PORT")
xChannel=os.getenv("XCHANNELSERVICE")
keyAES=os.getenv("AESKEY")
ivAES=os.getenv("AESIV")
rutaLineaCaptura=os.getenv("RUTA_LINEA_CAPTURA")
xSistemaKey=os.getenv("XSISTEMAKEY")

#Get the port and ip from the server
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip_address =s.getsockname()[0]
port=s.getsockname()[1]
s.close()

#consul Config
"""
c = consul.Consul(host=consul_ip, port=consul_port)
c.agent.service.register('servicio-linea-captura',
                        service_id='servicio-linea-captura',
                        port=port,
                        address=ip_address,
                        tags=['servicio-linea-captura'])
"""


app = Flask(__name__)

@app.route("/consultarLinea", methods=["POST"])
def consultar_linea_captura():
    try:
        data=request.json
        tokenGenerado=generarToken(data)
        return tokenGenerado
    
    except Exception as error:
        print(error)
        return error

#Generacion del Token
def generarToken(datos_usuario):
    try:
        dataEncriptada= encriptarData(datos_usuario)
        #dataEncriptada="gbgSXXxQbx6Q8TgHe4UeX6ApnFWqstT7WwcphR04ld/h0w/JloQZiC7fOj4W8cqnga6v0b6J3avqwlgVy5kqAQsHX5BMeTMHMy6i5czp8S0="
        
        datos_json={
                    'data':dataEncriptada
                    }
        
        header={
                    'Content-Type':'application/json',
                    'Access-Control-Allow-Methods':'GET, POST', 
                    'X-API-KEY':apiKey,
                    'X-SESSION-KEY':sessionKeyAbordaje,
                    'X-CHANNEL-SERVICE':xChannel,
                }

        param={"query":False}

        response = requests.post(url=rutaToken,params=param, headers=header,json=datos_json)
        #response_desencriptado=desencriptar_data(dataEncriptada)
        #dataDesencriptada=desencriptar_data(respuesta)
        
       
        

        return response.text
        #return response.text
    except Exception as error:
        return error
    
def encriptarData(data):

    datos=str(data).encode('utf-8')

    #parametros
    mode = AES.MODE_CBC
    #encriptacion
    encryptor = AES.new(keyAES.encode("utf-8"), mode,ivAES.encode("utf-8"))
    dataEncriptada =encryptor.encrypt(pad(datos,AES.block_size,"pkcs7"))
    dataEncriptadaBase64=base64.b64encode(dataEncriptada).decode("utf-8")
    print(dataEncriptadaBase64)
    return dataEncriptadaBase64

def desencriptar_data(data):
    #parametros
    mode = AES.MODE_CBC
    #---------
    #encriptacion
    base=base64.b64decode(data)
    encryptor = AES.new(keyAES.encode("utf8"), mode,ivAES.encode("utf8"))
    #dataDesencriptada = unpad(encryptor.decrypt(base), AES.block_size)
    dataDesencriptada=""
 
    return dataDesencriptada


def solicitar_linea_captura(token,folio):

    folio_encriptado=encriptarData(folio)
    header={
                'Content-Type':'application/json',
                'Access-Control-Allow-Methods':'GET, POST', 
                'X-API-KEY':apiKey,
                'X-CHANNEL-SERVICE':xChannel,
                'X-SISTEMA-KEY': '',
                'X-SESSION-KEY':sessionKeyAbordaje,
                'Authorization': 'Bearer '+ token
            }
    
    params={
                'query':folio_encriptado
            }
    
    response=requests.get(url=rutaLineaCaptura,headers=header,params=params)
    
    return response


if __name__=="__main__":

    #app.run(debug=True,port="4000")
    serve(app, host=ip_address, port=port)
    #app.run(host=ip_address,port=port)

