
import time

import paho.mqtt.client as mqtt
import logging


class MQTT:

    def __init__(self,config, pila):
      self.id = config["mqtt"]["mqtt_id"]
      self.usuario = config["mqtt"]['mqtt_user']
      self.contraseña = config["mqtt"]['mqtt_passwd']
      self.servidor = config["mqtt"]['mqtt_broker']
      self.puerto = config["mqtt"]['mqtt_port']
      self.topic = ""
      self.payload =""
      self.pila = pila
      self._state = ''
      self.log = logging.getLogger("MQTT")
      self.log_level = logging.DEBUG
      self.log.setLevel(self.log_level)
    
    def version(self):
      return "Version = 1.0"

    def on_connect(self,client,userdata,flags,rc):

      if rc ==0:
        self._state= "Conexión con ip: " + str(self.servidor) + " exitosa..."
      elif rc == 2:
        self._state = "Conexión rechazada; Id de cliente no válida"
      elif rc ==1:
        self._state = "Conexión rechazada; versión de protocolo incorrecto"
      elif rc ==3:
        self._state= "Conexión rechazada; servidor no disponible"
      elif rc == 4:
        self._state = "Conexión rechazada; contraseña o usuario erroneas"
      elif rc == 5:
        self._state = "Conexión rechazada; no autorizada"
      else:
        self._state = "Error de conexión inesperado"
      self.log.info(self._state)
      return self._state

    def on_message(self,client,userdata,msg):
      m = (msg.topic,msg.payload.decode("UTF-8"))
      self.pila.put(m)
      

    def on_subscribe(self, client,userdata, mid, state):
      self._state = "susbcrito a: " + str(mid)
      self.log.debug("subscripción confirmada")

    def on_publish(self,client,userdata,mid):
      self._state = "mid: " + str(mid)

    def on_unsubscribe(self,client, userdata, mid):
      self.log.debug("subscripcion eliminada")

    def sub(self,topic):
      self.client.subscribe(topic,0)
    
    def pub(self,topic,pay):
      self.client.publish(topic,pay)
      self.log.debug('publish: '+ topic)

    def unsub(self,topic):
      self.client.unsubscribe(topic)
 
    def run(self):

      self.client = mqtt.Client(client_id = self.id)
      self.client.on_connect = self.on_connect
      self.client.on_message = self.on_message
      self.client.on_publish = self.on_publish
      self.client.on_subscribe = self.on_subscribe
      self.client.on_unsubscribe = self.on_unsubscribe
      self.client.username_pw_set(self.usuario,self.contraseña)
      while True:
        try:
          self.client.connect(self.servidor,self.puerto)
          break
        except Exception as error:
          self._state = 'Error de conexion.... reintento en 5s'
          self.log.error(self._state)
          time.sleep(5)
      self.client.loop_start()

    def stop(self):
      self.client.disconnect()
      self.client.loop_stop()
      self.log.info('Client stop')

