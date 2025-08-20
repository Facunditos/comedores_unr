# Importar librerías
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import date
from time import sleep
import pandas as pd
import os
from datetime import datetime
import csv
import re
import warnings
warnings.filterwarnings(action='ignore')
from dotenv import load_dotenv
import os

load_dotenv()
num_tar = os.getenv("NUMERO_TARJETA")
print(num_tar)


# Configuración del navegador
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)
# Ocultar que es Selenium
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
service = Service('/usr/bin/chromedriver')

# Lectura de comedores y menúes disponibles
comedores_menues_path = "C:/Users/Usuario/Documents/comedores_unr/usuarios/facundo.xlsx"
op_menu_df = pd.read_excel(comedores_menues_path,sheet_name='opciones_menu')
comedores_df = pd.read_excel(comedores_menues_path,sheet_name='comedores')


# Control de habilitacion de reserva para finalizar la ejecución del script
reservas_habilitadas = False
hora_habilitacion = None

# Clase Reserva
class Reserva:
    url_login = 'https://comedores.unr.edu.ar/'
    url_reservas = 'https://comedores.unr.edu.ar/comedor-reserva/reservar'
    url_cuenta = 'https://comedores.unr.edu.ar/comensal/mi-cuenta'
    comedor = None
    menu = None
    u_logueado = False
    # Ni en diciembre ni en enero se van a sacar turno para los meses siguientes
    meses = ['Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    habilitada = False
    
    def __init__(self,u_dni:'str',u_clave:'str',op_eledigas:pd.DataFrame):
        self.driver = webdriver.Chrome(options=chrome_options)
        # Esto corre un script antes de que cargue cualquier página
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        self.wait = WebDriverWait(driver=self.driver, timeout=100)
        self.driver.set_page_load_timeout(400)        
        self.u_dni = str(u_dni)
        self.u_clave = str(u_clave)
        self.op_eledigas = op_eledigas
    def cerrar_navegador(self):
        print('se cierra el navegador\n')
        self.driver.quit()
    
    def loguearse(self):
        # Abrir la página web
        try:
            self.driver.get(self.url_login)
            # Capturar el elemento formulario
            e_form = self.wait.until(
                EC.presence_of_element_located(locator=(By.ID, "form-login"))
            )
            print('Formulario de logeo recibido')
            # Capturar los elementos del formulario
            e_input_dni = e_form.find_element(by=By.NAME,value='form-login[dni]')
            e_input_clave = e_form.find_element(by=By.NAME,value='form-login[clave]')
            # Completar el forumalario
            e_input_dni.send_keys(self.u_dni)
            e_input_clave.send_keys(self.u_clave)
            # Enviar el formulario
            e_boton = e_form.find_element(by=By.NAME,value='botones[botonEnviar]')
            e_boton.click()
            self.wait.until(
                EC.invisibility_of_element_located(locator=(By.ID, "form-login"))
            )
            self.driver.implicitly_wait(200)
            print('Usuario logueado, redireccionando...\n')        
            # Ingresar a la sección de reserva
            self.u_logueado = True
        except Exception as e:
            print(f"Ocurrió un error en el logeo: {e}.")
    def chequear_saldo(self):
        if not self.u_logueado: 
            print('para revisar el saldo primero hay que loguearse\n')
            return
        # Abrir la página web
        try:
            # Revisar crédtio
            #saldo_actual = e_col_md_3.find_element(by=By.CLASS_NAME,value='cc-saldo-actual-valor').text
            saldo = self.driver.find_element(by=By.ID,value='saldo-cabecera-movil').text
            saldo = re.search(r'\d.+',saldo).group(0)
            saldo = saldo.replace('.','').replace(',','.')
            self.saldo = float(saldo)
        except Exception as e:
            print(f"Ocurrió un error ingresando a la cuenta: {e}.")            

    def saldo_suficiente(self,valor_menues):
        return self.saldo>=valor_menues
    
    def cargar_saldo(self):
        if self.saldo is None:
            print('Para cargar saldo primero corresonde chequear el saldo actual')
            return
        self.driver.get(self.url_cuenta)
        e_col_md_3 = self.wait.until(
            EC.presence_of_element_located(locator=(By.CLASS_NAME,'col-md-3'))
        )
        boton_carga_credito = e_col_md_3.find_element(by=By.XPATH,value="//button[@data-toggle='modal']")
        boton_carga_credito.click()
        e_form = self.wait.until(
            EC.visibility_of_element_located(locator=(By.XPATH,"//*/form[@data-bind='submit: cargarCredito']"))
        )
        e_button = e_form.find_element(by=By.XPATH,value=".//*/button[@type='submit']")
        e_button.click()
        self.wait.until(
            EC.url_contains(url='p=')
        )
        self.driver.get(self.driver.current_url)
        print('eligiendo forma de pago')
        e_new_card_row = self.driver.find_element(By.ID,'new_card_row')
        e_button = e_new_card_row.find_element(By.TAG_NAME,'button')
        e_button.click()
        self.wait.until(
            EC.url_contains('card-form')
        )
        print('completando datos de la tarjeta')
        # c/ iframe:
        # cardNumber 
        # expirationDate 
        # securityCode 
        # s/ iframe:
        # cardholderName 
        # cardholderIdentificationNumber 
        # Detecto el elemento iframe
        e_iframe = self.driver.find_element(By.XPATH,"//iframe[@id='iframe-sf-cardNumber']")
        # Cambio de frame y obtengo el input
        self.driver.switch_to.frame(e_iframe)
        e_input_num_tar = self.driver.find_element(By.XPATH,"//input[@id='cardNumber']")
        print('etiqueta',e_input_num_tar.tag_name,'atributo id',e_input_num_tar.get_attribute('id'))
        # retorno al frame original
        self.driver.switch_to.default_content()
        e_input_tit_tar_nombre = self.driver.find_element(By.ID,'cardholderName')
        print('etiqueta',e_input_tit_tar_nombre.tag_name,'atributo id',e_input_tit_tar_nombre.get_attribute('id'))
        # Detecto el elemento iframe
        e_iframe = self.driver.find_element(By.XPATH,"//iframe[@id='iframe-sf-expirationDate']")
        # Cambio de frame y obtengo el input
        self.driver.switch_to.frame(e_iframe)
        e_input_exp_tar = self.driver.find_element(By.XPATH,"//input[@id='expirationDate']")
        print('etiqueta',e_input_exp_tar.tag_name,'atributo id',e_input_exp_tar.get_attribute('id'))
        # retorno al frame original
        self.driver.switch_to.default_content()
        # Detecto el elemento iframe
        e_iframe = self.driver.find_element(By.XPATH,"//iframe[@id='iframe-sf-securityCode']")
        # Cambio de frame y obtengo el input
        self.driver.switch_to.frame(e_iframe)
        e_input_cod_tar = self.driver.find_element(By.XPATH,"//input[@id='securityCode']")
        print('etiqueta',e_input_cod_tar.tag_name,'atributo id',e_input_cod_tar.get_attribute('id'))
        # retorno al frame original
        self.driver.switch_to.default_content()
        e_input_tit_tar_id = self.driver.find_element(By.ID,'cardholderIdentificationNumber')
        print('etiqueta',e_input_tit_tar_id.tag_name,'atributo id',e_input_tit_tar_id.get_attribute('id'))
        # Completar el forumalario
        e_input_num_tar.send_keys('hola')
        e_input_tit_tar_nombre.send_keys('hola')
        e_input_exp_tar.send_keys('hola')
        e_input_cod_tar.send_keys('hola')
        e_input_tit_tar_id.send_keys('hola')
        # Enviar el formulario
        e_span_continuar = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Continuar')]")
        e_button_continuar = e_span_continuar.find_element(By.XPATH,"..")
        print(e_button_continuar.text)
        return 


        
    def ingresar_comedor(self,comedor):
        if not self.u_logueado: 
            print('para elegir un comedor primero hay que loguearse')
            return
        # Abrir la página web
        try:
            self.driver.get(self.url_reservas)
            e_contenedor_comedores = self.wait.until(
                EC.presence_of_element_located(locator=(By.CLASS_NAME,'reservar-comedores-contenedor'))
            )
            e_botones_comedores = e_contenedor_comedores.find_elements(by=By.TAG_NAME,value='button')
            if len(e_botones_comedores) != 7: return  
            n_boton_comedor = comedores_df['comedores'].to_list().index(comedor)
            e_boton_salud = e_botones_comedores[n_boton_comedor]
            # Ingresar al comedor de Salud
            e_boton_salud.click()
            print('Ingreso al comedor',comedor)
            self.comedor = comedor
        except Exception as e:
            print(f"Ocurrió un error al elegir un comedor: {e}.\n")

    def cambiar_mes(self):
        # Se intenta cambiar de mes
        self.wait.until(EC.visibility_of_element_located(locator=(By.XPATH,"//span[@class='calendario-mes-control-mes']")))
        span_mes = self.driver.find_element(by=By.XPATH,value="//span[@class='calendario-mes-control-mes']")
        mes_actual = span_mes.text
        i_mes_actual = self.meses.index(mes_actual)
        buttons_cambios_mes = self.driver.find_elements(by=By.XPATH,value="//button[@class='calendario-mes-control-boton']")
        button_subir_mes = buttons_cambios_mes[1]
        button_subir_mes.click()
        mes_siguiente = self.meses[i_mes_actual+1]
        self.wait.until(EC.text_to_be_present_in_element(locator=(By.XPATH,"//span[@class='calendario-mes-control-mes']"),text_=mes_siguiente))
        print('Cambiamos el calandario al próximo mes')

    def buscar_menu(self,menu,dia,mes):
        if self.comedor is None: 
            print('No se puede avanzar con la reserva del menú porque hay problemas para ingresar al comedor!\n')
            return
        try:
            self.wait.until(EC.visibility_of_all_elements_located(locator=(By.CLASS_NAME,'reservar-servicio')))
            op_reservas = self.driver.find_elements(by=By.CLASS_NAME,value='reservar-servicio')
            if len(op_reservas) != len(op_menu_df[self.comedor][~op_menu_df[self.comedor].isna()]) : 
                print('No están disponibles todas las opciones de menúes para avanzar con la reserva\n')
                return 
            n_op_mer = op_menu_df[self.comedor].to_list().index(menu)
            op_mer = op_reservas[n_op_mer]
            op_mer.click()
            print(f'Avancemos en reservar el menú {menu} el día {dia} del mes {mes}')
            if dia < date.today().day: self.cambiar_mes()
            #self.driver.implicitly_wait(20)
            lote_span_n_dia = self.driver.find_elements(by=By.XPATH,value="//span[@data-bind='text: numero']")
            span_n_dia_reserva = lote_span_n_dia[dia-1]
            div_class_calendario_dia = span_n_dia_reserva.find_element(by=By.XPATH,value="../..")
            div_class_calendario_dia_atributo_clase = div_class_calendario_dia.get_attribute('class')
            if 'calendario-dia-vacio' in div_class_calendario_dia_atributo_clase:
                print('Aún no se habilitaron las reservas o ese día el comedor está cerrado\n')
                return
            # Chequear que en ese día se otorguen turnos, caso contrario, calendario-dia-vacio
            div_class_calendario_dia_turno = div_class_calendario_dia.find_element(by=By.CLASS_NAME,value="calendario-dia-turno")
            info_enlazada = div_class_calendario_dia_turno.get_attribute(name='data-bind')
            if not info_enlazada:
                print(f'El menú no está disponible: día no habilitado o ya se hizo la reserva\n')
                return 
            div_class_calendario_dia_turno.click()
            div_swal2_container = self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "swal2-container")))
            div_swal2_error = self.driver.find_element(By.CLASS_NAME, "swal2-error")
            div_swal2_error_estilo = div_swal2_error.get_attribute('style')
            if div_swal2_error_estilo != 'display: none;': 
                h2_msg_error = div_swal2_container.find_element(by=By.TAG_NAME,value='h2')
                msg_error = h2_msg_error.text
                print(f'Hay problemas con la reserva del menú: {msg_error}\n')
            else:    
                boton_reservar = self.driver.find_element(By.CSS_SELECTOR, ".swal2-confirm")
                boton_reservar.click()
                self.wait.until(EC.staleness_of(div_swal2_container))
                print(f'Menú reservado\n')
                self.habilitada = True
                    
        except Exception as e:
            print(f"Ocurrió un error al elegir un menú: {e}.\n")
    def buscar_menues(self):
        for _,op_elegida in self.op_eledigas.sort_values(by='fecha').iterrows():
            comedor_elegido = op_elegida['comedor']
            menu_elegido = op_elegida['menu']
            dia_elegido = op_elegida['fecha'].day
            mes_elegido = op_elegida['fecha'].month
            if self.u_logueado: self.ingresar_comedor(comedor=comedor_elegido)
            if self.comedor: self.buscar_menu(menu=menu_elegido,dia=dia_elegido,mes=mes_elegido)
        self.cerrar_navegador() 

while True:
    # Se corroboró que no siempre se habilitan las reservas todas juntas, por lo cual, se esperan 5 horas desde que se habilita la primera para dejar de buscar menúes
    if reservas_habilitadas is True:
        hora_actual = datetime.now()
        diferencia_s = (hora_actual - hora_habilitacion).total_seconds()
        if diferencia_s > 60*60*5: # equivale a cinco horas 
            break
    dir_usuarios = "C:/Users/Usuario/Documents/comedores_unr/usuarios"
    for usuario in os.listdir(path=dir_usuarios):
        u = usuario.split('.')[0]
        usuario_path = os.path.join(dir_usuarios, usuario)
        menues_elegidos_df = pd.read_excel(usuario_path,sheet_name='menues')
        menues_elegidos_df.sort_values(by='fecha',inplace=True)
        credenciales_df = pd.read_excel(usuario_path,sheet_name='credenciales')
        u_dni = credenciales_df['dni'].loc[0]
        u_clave = credenciales_df['contraseña'].loc[0]
        now_inicio = datetime.now()
        print(f'Hora actual: {now_inicio.hour} hs con {now_inicio.minute} minutos. Avancemos en reservar los menúes de {u} \U0001F4AA!!!\n')
        reserva = Reserva(u_dni=u_dni,u_clave=u_clave,op_eledigas=menues_elegidos_df)
        reserva.loguearse()
        reserva.chequear_saldo()
        if not reserva.saldo_suficiente(valor_menues=3001): reserva.cargar_saldo()
        break
        reserva.buscar_menues()
        if reserva.habilitada is True and reservas_habilitadas is False:
            reservas_habilitadas = True
            hora_habilitacion = datetime.now()
        now_fin = datetime.now()
        demora_s = (now_fin - now_inicio).total_seconds()
        tiempo_ejecucion_path = "C:/Users/Usuario/Documents/comedores_unr/tiempo_ejecucion.csv"
        with open(tiempo_ejecucion_path,'+a',newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow((now_inicio,demora_s))
        print(f'La búsqueda de menúes demoró {demora_s} segundos\n')
    break
    print('En diez minutos volvemos a intertarlo\n')
    diez_min = 60 * 10
    sleep(diez_min)        

print('Fin de la ejecución. Transcurrieron más de 5 horas desde que se habilitó la primer reserva')