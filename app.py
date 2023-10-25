from flask import Flask, request
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
import json
#from flask_cors import CORS




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
clientID=os.getenv("CLIENT_ID")
clientSecret=os.getenv("CLIENT_SECRET")
urlAuth=os.getenv("URL_AUTH")
xSessionKeyTrue=os.getenv("X_SESSION_KEY_TRUE")

#Get the port and ip from the server
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip_address =s.getsockname()[0]
port=s.getsockname()[1]
s.close()

logging.warning(port)

#consul Config

c = consul.Consul(host=consulIp, port=consulPort)
c.agent.service.register('servicio-linea-captura',
                        service_id='servicio-linea-captura',
                        port=port,
                        address=ip_address,
                        tags=['servicio-linea-captura'])



app = Flask(__name__)

@app.route("/generarLineaCaptura", methods=["POST"])
def consultar_linea_captura():
    try:
        request_data = request.get_json()
        user = request_data['user']
        email = request_data['email']
        folio=request_data['folio']
        idTramite=request_data['idTramite']
   
        data=json.dumps({"user":user, "email":email}, separators=(',', ':'))
        
        tokenGenerado=generarToken(data)
        
        lineaDeCaptura=solicitar_linea_captura(tokenGenerado,folio,idTramite)
        
        return lineaDeCaptura
    
    except Exception as error:
        logging.warning(error)
        return error

#Generacion del Token
def generarToken(datos_usuario):
    try:
        dataEncriptada= encriptarData(datos_usuario)

        datos_json=json.dumps({"data":dataEncriptada},separators=(',', ':'))
             
        header={
                    "Content-Type":"application/json",
                    "Access-Control-Allow-Methods":"GET, POST", 
                    "X-API-KEY":apiKey,
                    "X-SESSION-KEY":sessionKeyAbordaje,
                    "X-CHANNEL-SERVICE":xChannel,
                }

        param={"query":False}
        response = requests.post(url=rutaToken,params=param,headers=header,data=datos_json)
        
        dataResponse= json.loads(response.text)
        tokenDesencriptado=desencriptado(dataResponse["data"])
        
        obteniendoToken=json.loads(tokenDesencriptado)
        token=obteniendoToken["session"]["token_user"]
       
        return token
    except Exception as error:
        logging.warning(error)
        logging.warning(response.status_code)
        logging.warning(response.reason)
        return error
    
def encriptarData(data):
    try:
        datos=str(data).encode('utf-8')
        #parametros
        mode = AES.MODE_CBC
        #encriptacion
        encryptor = AES.new(keyAES.encode("utf-8"), mode,ivAES.encode("utf-8"))
        dataEncriptada =encryptor.encrypt(pad(datos,AES.block_size,"pkcs7"))
        dataEncriptadaBase64=base64.b64encode(dataEncriptada).decode("utf-8")
        return dataEncriptadaBase64
    
    except Exception as error:
            logging.warning(error)
            return error

def desencriptado(data):
    try:
        mode = AES.MODE_CBC
        encryptor = AES.new(keyAES.encode("utf-8"), mode,ivAES.encode("utf-8"))
        #encriptacion
        conversorbytes=base64.b64decode(data)
        desencriptar=unpad(encryptor.decrypt(conversorbytes),AES.block_size,"pkcs7").decode()
        
        return desencriptar
    except Exception as error:
            logging.warning(error)
            return error
    


def solicitar_linea_captura(token,folio,idTramite):

    folio="/?folioSeguimiento="+folio+"&idTramite="+idTramite 
    folio_encriptado=encriptarData(folio)
    header={
                'Content-Type':'application/json',
                'Access-Control-Allow-Methods':'GET, POST', 
                'X-API-KEY':apiKey,
                'X-CHANNEL-SERVICE':xChannel,
                'X-SISTEMA-KEY':xSistemaKey,
                'X-SESSION-KEY':xSessionKeyTrue,
                'Authorization':'Bearer '+ token
            }
    
    
    response=requests.get(url=rutaLineaCaptura+"?query="+folio_encriptado,headers=header)
    desencriptadoLineaCaptura=desencriptado(response.text)
    dataDesencriptado= json.loads(desencriptadoLineaCaptura)
    
    return dataDesencriptado


if __name__=="__main__":

    #app.run(debug=True,port="4000")
    serve(app, host=ip_address, port=port)
    

