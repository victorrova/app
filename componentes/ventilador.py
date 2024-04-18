import asyncio
import logging
import psutil
#from pid import PID

class Ventilador:

    def __init__(self,construct,config,queue):
        #self.pid = PID()
        self.pub_topic = config["ventilador"]["topic"]
        self.log = logging.getLogger("ventilador")
        self.mqtt_queue = queue
        self.log_level = logging.DEBUG
        self.log.setLevel(self.log_level)
        self.temp = 0
        self.min_temp = 30
        self.max_temp = 56
        self.min_out = 100
        self.max_out = 255
        self.timer = 60
        self.construct = construct
        self.Internal_config = {"module":"ventilador", "task":["fan"],"topic": self.pub_topic, "subs_topic": None}




    async def Config(self):
        return self.Internal_config




    async def _map(self,x, in_min, in_max, out_min, out_max):
        return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    async def sample_temp(self,temp):
        self.temp = psutil.sensors_temperatures()['cpu_thermal'][0].current


    async def fan(self):
        self.log.debug( "task fan iniciada")
        while True:
            try:
                self.temp = psutil.sensors_temperatures()['cpu_thermal'][0].current
                out = await self._map(self.temp,self.min_temp,self.max_temp,self.min_out,self.max_out)
                await self.mqtt_queue.put_nowait((self.pub_topic, out))
                await asyncio.sleep(self.timer)
            except Exception as error:
                self.log.error(error)
    
    async def run(self,task = None):
        if task == 'fan':
            await self.construct.task_launcher(self.fan(),"fan",self.Internal_config)
        else:
            self.log.debug("No se encuentra la tarea para inicio")



def main(const,config,queue):
    
    b = Ventilador(const,config,queue)
    return b

    



    


    