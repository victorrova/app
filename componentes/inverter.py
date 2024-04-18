import json
import requests
import xmltodict
import asyncio
import logging


class inverter:

    def __init__(self,construct,config, queue):
        self.ip = config["inverter"]["ip"]
        self.id = config["inverter"]["id"] 
        self.topic = config["inverter"]["topic"]
        self.timer = config["inverter"]["time"]
        self.log = logging.getLogger("inverter")
        self.mqtt_queue = queue
        self.log_level = logging.DEBUG
        self.log.setLevel(self.log_level)
        self.error_id = 0
        self.construct = construct
        self.Internal_config = {"module":"inverter", "task":["_measurement", "events"],"topic": self.topic, "subs_topic": None}
    
    async def Config(self):
        return self.Internal_config
            


    async def _measurement(self):
            self.log.info("Task medidor iniciada")    
            while True:
                try:
                    data = requests.get("http://"+self.ip+"/measurements.xml")
                    if data.ok:
                        buff = xmltodict.parse(data.content)
                        ac_voltage = buff["root"]["Device"]["Measurements"]["Measurement"][0]
                        ac_current = buff["root"]["Device"]["Measurements"]["Measurement"][1]
                        ac_power = buff["root"]["Device"]["Measurements"]["Measurement"][2]
                        #ac_power_fast = buff["root"]["Device"]["Measurements"]["Measurement"][3]
                        ac_frequency =  buff["root"]["Device"]["Measurements"]["Measurement"][4]
                        dc_voltage1 =  buff["root"]["Device"]["Measurements"]["Measurement"][5]
                        dc_voltage2 =  buff["root"]["Device"]["Measurements"]["Measurement"][6]
                        dc_current1 =  buff["root"]["Device"]["Measurements"]["Measurement"][7]
                        dc_current2 =  buff["root"]["Device"]["Measurements"]["Measurement"][8]
                        #link_voltage = buff["root"]["Device"]["Measurements"]["Measurement"][9]
                        grid_power =  buff["root"]["Device"]["Measurements"]["Measurement"][11]
                        injected_power = buff["root"]["Device"]["Measurements"]["Measurement"][12]
                        autoconsum_power = buff["root"]["Device"]["Measurements"]["Measurement"][13]

                        dict = {"ac_voltage": float(ac_voltage[("@Value")]) if "@Value" in ac_voltage else 0,
                                "ac_current":float(ac_current[("@Value")]) if "@Value" in ac_current else 0,
                                "ac_power": float(ac_power[("@Value")])if "@Value" in ac_power else 0,
                                #"ac-power_fast":float(ac_power_fast[("@Value")]) if "@Value" in ac_power_fast else 0,
                                "ac_frequency" :float(ac_frequency[("@Value")]) if "@Value" in ac_frequency else 0,
                                "dc_voltage1" : float(dc_voltage1[("@Value")]) if "@Value" in dc_voltage1 else 0,
                                "dc_voltage2" : float(dc_voltage2[("@Value")])if "@Value" in dc_voltage2 else 0,
                                "dc_curent1" : float(dc_current1[("@Value")]) if "@Value" in dc_current1 else 0,
                                "dc_current2" : float(dc_current2[("@Value")]) if "@Value" in dc_current2 else 0,
                                "link_voltage": (float(grid_power[("@Value")]) if "@Value"  in grid_power else 0) - (float(injected_power[("@Value")]) if "@Value" in injected_power else 0 ),
                                "grid_power" : float(grid_power[("@Value")]) if "@Value"  in grid_power else 0,
                                "injected_power": float(injected_power[("@Value")]) if "@Value" in injected_power else 0,
                                "autoconsum_power": float(autoconsum_power[("@Value")]) if "@Value" in autoconsum_power else 0
                        }
                        self.log.debug("meter: %s", dict)
                        self.mqtt_queue.put_nowait((self.topic[0], json.dumps(dict)))
                        await asyncio.sleep(self.timer)
                        

                    else:
                        self.log.warning("Inversor no disponible")
                        await asyncio.sleep(30)
                    
                except Exception as error:
                    self.log.error(error)
               
    async def events(self):
        self.log.info("Task eventos en inversor iniciado")
        while True:
            try:
                data = requests.get("http://"+self.ip+"/events.xml")
                if data.ok:
                    buff = xmltodict.parse(data.content)
                    if buff["root"]["Device"]["Events"] == None:
                        self.error_id = 0
                    else:
                        try:
                            n = 0
                            for e in buff["root"]["Device"]["Events"]["Event"]:
                                n +=1
                                if n > self.error_id:
                                    self.mqtt_queue.put_nowait((self.topic[1] + "/event", e[("@Message")]))
                                await asyncio.sleep(0.5)
                            self.error_id = n
                            
                        except TypeError as j:
                    
                            if self.error_id == 0:
                                self.mqtt_queue.put_nowait((self.topic[1], buff["root"]["Device"]["Events"]["Event"][("@Message")]))
                                self.error_id = 1
                        
                else:
                    self.log.warning("Inversor no disponible")
                    await asyncio.sleep(30)
                await asyncio.sleep(60)

            except Exception as error:
                self.log.error("Event task: " + str(error))
            
    async def run(self,task = None):
        self.log.info("run inverter meter")
        if task == "_measurement":
            await self.construct.task_launcher(self._measurement(),"_measurement",self.Internal_config)
        elif task == "events":
            await self.construct.task_launcher(self.events(),"events",self.Internal_config)
        else:
           self.log.debug("Ninguna Task creada en Inverter")
    
def main(const,config,queue):
    
    b = inverter(const,config,queue)
    return b

