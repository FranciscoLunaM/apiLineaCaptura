import datetime
import io
import ssl
from flask import Flask, request,make_response,send_file
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
from fpdf import FPDF, YPos
from flask_cors import CORS
import qrcode
from barcode import Code128
from barcode.writer import SVGWriter
ssl._create_default_https_context = ssl._create_unverified_context
from database import obtenerConexion
conexion= obtenerConexion()

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
rutaRecaudador=os.getenv("RUTA_RECAUDADOR")
rutaConsultaPago=os.getenv("RUTA_CONSULTA_PAGO")


#Get the port and ip from the server
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip_address =s.getsockname()[0]
port=s.getsockname()[1]
s.close()


#consul Config

c = consul.Consul(host=consulIp, port=consulPort)
c.agent.service.register('servicio-linea-captura',
                        service_id='servicio-linea-captura',
                        port=port,
                        address=ip_address,
                        tags=['servicio-linea-captura'])



app = Flask(__name__)
CORS(app)
@app.route("/generarLineaCaptura", methods=["POST"])
def consultar_linea_captura():
    try:
        request_data = request.get_json()
        user = request_data['user']
        email = request_data['email']
        folio=request_data['folio']
        clienteID=request_data['clientId']
        idTramite=request_data['idTramite']
        hora = datetime.datetime.now()

        data=json.dumps({"user":user, "email":email}, separators=(',', ':'))
        
        tokenGenerado=generarToken(data)
        
        lineaDeCaptura=solicitar_linea_captura(tokenGenerado,folio,idTramite)
        
        
        if lineaDeCaptura["resultado"]==True:
            url2="https://enlace-qa.tabasco.gob.mx/api/v1/linea-captura/consulta/documento_linea_captura?folio="+folio
            logging.warning(url2)

            url=lineaDeCaptura["data"]["urlFormatoPago"]["_text"]
            logging.warning(url)         
            today = datetime.date.today()
            logging.warning(today)
            year = today.year
            logging.warning(year)   
            splitLinea= lineaDeCaptura["data"]["lineaCaptura"]["_text"].split("|", 1)
            logging.warning(splitLinea)  
            lineaDeCaptura.update({"urlPdf2":url2})
            logging.warning("linea final antes--------------")  

            conexion= obtenerConexion()
            with conexion.cursor() as cursor:
                
                sql="insert into pagos_finanzas_pagoreferenciado (contribuyente,folio_seguimiento,importe,fecha_registro,folio_control,linea_captura,fecha_vencimiento,linea_captura_oxxo,estatus,tramite_id,user_id,ejercicio,respuesta_finanzas,url_formato,client_id,url_formato2) values ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}','{9}','{10}','{11}','{12}','{13}','{14}','{15}')".format(user,folio,lineaDeCaptura["data"]["importe"]["_text"],hora,lineaDeCaptura["data"]["folioControlEstado"]["_text"],splitLinea[0],lineaDeCaptura["data"]["fechaVencimiento"]["_text"],splitLinea[1],"1",idTramite,"1",year,json.dumps(lineaDeCaptura),url,clienteID,url2)
                logging.warning(sql)  
                logging.warning(sql)
                cursor.execute(sql)
                conexion.commit()
                conexion.close()
                
        
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


@app.route("/consultarPago", methods=["POST"])
def consultarPago():
    data=request.get_json()
    folio=data["folioseguimiento"]
    idtramite=data["idtramite"]
    folioestado=data["foliocontrol"]

    user = data['user']
    email = data['email']

    data=json.dumps({"user":user, "email":email}, separators=(',', ':'))
    tokenGenerado=generarToken(data)
    logging.warning("token: "+tokenGenerado)

    consulta="/?folioSeguimiento="+folio+"&idTramite="+idtramite+"&folioControlEstado="+ folioestado
    dataEncriptada=encriptarData(consulta)
    logging.warning("data: "+dataEncriptada)

    header={
                'Content-Type':'application/json',
                'Access-Control-Allow-Methods':'GET, POST', 
                'X-API-KEY':apiKey,
                'X-CHANNEL-SERVICE':xChannel,
                'X-SISTEMA-KEY':xSistemaKey,
                'X-SESSION-KEY':xSessionKeyTrue,
                'Authorization':'Bearer '+ tokenGenerado
            }
    
    
    response=requests.get(url=rutaConsultaPago+"?query="+dataEncriptada,headers=header)
    desencriptadoLineaCaptura=desencriptado(response.text)
    dataDesencriptado= json.loads(desencriptadoLineaCaptura)

    #Agregar a la base de datos
    """if dataDesencriptado["resultado"]==True:
        conexion= obtenerConexion()

        with conexion.cursor() as cursor:
            number=int(dataDesencriptado["data"]["codigoEstatus"]["_text"])
            sql= "update pagos_finanzas_pagoreferenciado set estatus='"+str(number)+"' where folio_seguimiento like '"+folio +"'"
            cursor.execute(sql)
            conexion.commit()
            conexion.close()"""

    return dataDesencriptado

@app.route("/consulta/documento_linea_captura", methods=["GET"])
def documento_linea_captura():
    request_data = request.args.get("folio")
    conexion= obtenerConexion()
    with conexion.cursor() as cursor:
        sql="select pf.folio_seguimiento,pf.importe,pf.folio_control,pf.fecha_registro,pf.fecha_vencimiento,pt.nombre,pf.linea_captura ,pf.linea_captura_oxxo from pagos_finanzas_pagoreferenciado as pf, pagos_finanzas_tramite as pt where folio_seguimiento = '"+request_data+"' and pf.tramite_id=pt.id "
        cursor.execute(sql)
        data=cursor.fetchone()
        folio=str(data[0])
        importe=str(data[1])
        controlEstado=str(data[2])
        fechaEmision=str(data[3])
        fechaVencimiento=str(data[4])
        concepto=str(data[5])
        lineaCaptura=data[6]
        lineaCapturaOxxo=data[7]
        conexion.close()
        
      
    return generarPDF(folio,importe,controlEstado,fechaEmision,fechaVencimiento,concepto,lineaCaptura,lineaCapturaOxxo)
    
    

def generarPDF(folio,importe,controlEstado,fechaEmision,fechaVencimiento,concepto,lineaCaptura,lineaCapturaOxxo):
    
    hora = datetime.datetime.now().time()
    pdf = PDF()
    pdf.set_auto_page_break(auto=True,margin=15)
    pdf.add_page()
    pdf.body(folio,importe,controlEstado,fechaEmision,fechaVencimiento,hora,concepto,lineaCaptura,lineaCapturaOxxo)
    #Creacion del PDF
    stream = pdf.output(dest='S')
    return send_file(io.BytesIO(stream),download_name='logo.pdf')

#Header PDF
class PDF(FPDF):
    def header(self):
        #apilineacaptura/images/tb.png
        self.image("apilineacaptura/images/tb.png",20,15,20)
        self.ln(5)
        self.set_font('helvetica', size=9)
        self.cell(0,5, "GOBIERNO DEL ESTADO DE TABASCO",ln=1,align="C")
        self.cell(0,5, "SECRETARIA DE FINANZAS",ln=1,align="C")
        self.cell(0,5, "ESTADO DE CUENTA",ln=1,align="C")
#Fin del Header
#footer PDF
    def footer(self):
        self.set_y(-10)
        self.set_font('helvetica', size=9)
        self.cell(0,6,"""Ante cualquier duda, favor de comunicarse al Centro de Atención Telefónica de la SF al 01-800-3-10-40-10 donde """ ,ln=1,align="C")
        self.cell(0,2, "con gusto le atenderemos de Lunes a Viernes en horario de 8 a 15 horas, escríbanos al correo safcat@tabasco.gob.mx",align="C")
#FIN footer
#Body
    def body(self,folio,importe,controlEstado,fechaEmision,fechaVencimiento,hora,concepto,lineaCaptura,lineaCapturaOxxo):
        self.set_font('helvetica', size=12)
        self.cell(0,20,"Folio: " + folio,ln=1,align="R")

        qr = qrcode.QRCode(
                version=1,
                box_size=15,
                border=5)
        qr.add_data('Transacción|{}&Importe|{}'.format(folio,importe))
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        self.image(img.get_image(), x=165, y=45,h=40)


        self.set_font('helvetica', size=9)
        self.cell(0,4,"Prueba de pago referenciado" ,align="C",ln=1)
        self.cell(0,4,"Estado de cuenta: "+ controlEstado ,align="C",ln=1)
        self.cell(0,4,"Fecha de emisión: " + fechaEmision,align="C",ln=1)
        self.cell(0,4,"Vencimiento: "+fechaVencimiento,align="C",ln=1)
        self.cell(0,4,"Hora: "+str(hora.hour)+":"+str(hora.minute),align="C",ln=1)
        self.set_font('helvetica',"B", size=13)
        self.cell(0,8,"Total a pagar: $" +importe,align="C",ln=1)
        self.set_font('helvetica', size=7)
        self.ln(5)
        self.multi_cell(0,8,"Concepto: "+concepto,align="C",ln=1)
        self.ln(5)
        self.multi_cell(0,4,"""En caso de que el instrumento de pago sea CHEQUE nominativo distinto al banco donde presentará su pago, el vencimiento de la línea de captura tendrá un día hábil menos del citado en este documento. Lo anterior, se debe a políticas bancarias. Si usted es contribuyente del Impuesto Especial Sobre Producción y Servicios (IEPS), únicamente realice su pago en Instituciones Bancarias.""",align="J")
        self.ln(5)
        self.set_font('helvetica',"B", size=9)
        self.cell(0,10,"**NOTA** " ,ln=1,align="C")
        self.set_font('helvetica', size=7)
        self.multi_cell(0,4,"""ESTIMADO CONTRIBUYENTE, LE RECOMENDAMOS LEER LOS SIGUIENTES COMENTARIOS:
A) Si usted no cuenta con Banca Electrónica, Tarjeta Débito o Crédito, debe utilizar, la opción de "ESTADO DE CUENTA".
B) El ESTADO DE CUENTA tiene vigencia de 2 días naturales, en la hoja se refleja dicha fecha.
C) Si requiere algún cambio en los datos de su vehículo o propietario [RFC, Color, Domicilio] deberá realizar su trámite en las oficinas de atención a contribuyentes.""",ln=1,align="J")
        self.set_font('helvetica', "B",size=8)
        self.cell(0,10,"Los usuarios que deseen pagar sus Estados de Cuenta en el portal de SCOTIABANK, deberán realizar el pago el mismo día de la emisión de la misma." ,ln=1,align="C")
        self.set_font('helvetica', size=13)
        #Lineas de Captura Banco
        self.cell(0,5,"Linea de captura para bancos " ,ln=1,align="C")
        self.cell(0,5,lineaCaptura,ln=1,align="C")
        svg_img_bytes = io.BytesIO()
        Code128(lineaCaptura, writer=SVGWriter()).write(svg_img_bytes)
        self.image(svg_img_bytes,80,166,45)

        #Lineas de captura OXXO
        svg_img_bytes2 = io.BytesIO()
        Code128(lineaCapturaOxxo, writer=SVGWriter()).write(svg_img_bytes2)
        self.image(svg_img_bytes2,10,214,60)
        self.ln(30)
        self.set_font('helvetica', size=8)
        self.cell(0,5,"Línea de captura exclusiva de OXXO:" ,align="L")
        self.set_font('helvetica',"B", size=9)
        self.cell(0,5,"CITIBANAMEX: SERVICIO EST 4630 GOB IMP TABASCO WS" ,ln=1,align="R")
        self.cell(0,5,"HSBC: CLAVE RAP: 2950" ,ln=1,align="R")
        self.cell(0,5,"BANCA AFIRME: PR" ,ln=1,align="R")
        self.cell(0,5,"BANORTE: EMPRESA 48421" ,ln=1,align="R")
        self.cell(0,5,"SCOTIABANK: SERVICIO 1098" ,ln=1,align="R")
        self.cell(0,5,"SANTANDER: CONVENIO =2527" ,ln=1,align="R")
        self.cell(0,5,"BANCOMER: CIE =0672505" ,ln=1,align="R")
        self.cell(0,5,"BANCO DEL BAJIO: SERVICIO 1108" ,ln=1,align="R")
        self.image("apilineacaptura/images/lugares.png",102,223,100)
        self.image("apilineacaptura/images/oxxo.jpg",25,192,20)
        self.set_font('helvetica', size=13)
        
        self.ln(60)
        self.set_font('helvetica',"B", size=9)
        self.cell(0,5,"Su pago puede tardar hasta 72 horas hábiles en verse reflejado." ,ln=1,align="C")
        self.set_font('helvetica', size=9)
        self.multi_cell(0,5,"SOLO TIENE QUE DECIRLE AL CAJERO, DONDE QUIERA QUE ESTÉ PAGANDO: ESTO ES UN PAGO REFERENCIADO A FAVOR DEL GOBIERNO DEL ESTADO DE TABASCO" ,ln=1,align="C")


#FIN Body

@app.route("/pagoRecaudador",methods=["POST"])
def pagoRecaudador():
    try:
               
        data_request=request.get_json()
        
        user = data_request['user']
        email = data_request['email']
        auth=data_request['AuthS701']
        reference=data_request['referenceKey']
        access=data_request['AccessUser']
        establish=data_request['EstablishNum']
        branch=data_request['BranchSource']

        data_recaudador=json.dumps({"AuthS701":auth, "referenceKey":reference, "AccessUser":access, "EstablishNum":establish, "BranchSource":branch}, separators=(',', ':'))
        data=json.dumps({"user":user, "email":email}, separators=(',', ':'))
        
        tokenGenerado=generarToken(data)
        
        dataEncriptadaRecaudador=encriptarData(data_recaudador)
        param=json.dumps({"query":dataEncriptadaRecaudador},separators=(',', ':'))

        

        header={
                        'Content-Type':'application/json',
                        'Access-Control-Allow-Methods':'GET, POST', 
                        'X-API-KEY':apiKey,
                        'X-CHANNEL-SERVICE':xChannel,
                        'X-SISTEMA-KEY':xSistemaKey,
                        'X-SESSION-KEY':xSessionKeyTrue,
                        'Authorization':'Bearer '+ tokenGenerado
                }

        
        response=requests.post(url=rutaRecaudador+"?query="+param,headers=header)
        encriptadoRecaudador=desencriptado(response.text)
        dataDesencriptado= json.loads(encriptadoRecaudador)
        logging.warning(dataDesencriptado)
        
        return dataDesencriptado
    except Exception as error:
     logging.warning(error)


@app.route("/webhookSAIG",methods=["POST"])
def webhook():
    data=request.get_json()
    return data


if __name__=="__main__":

    #app.run(debug=True,port="4000")
    serve(app, host=ip_address, port=port)
    

