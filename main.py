from Adafruit_Thermal import *
from machine import Pin
import machine
import time
import network
import uasyncio
from microdot_asyncio import Microdot, send_file
import hashlib
import hmac
import urequest
import json
import sys
import ntptime
import os
import micropython
micropython.mem_info(1)
from microWebCli import MicroWebCli


# Initialize Microdot server
app = Microdot()

# initialize uart interface
printer = Adafruit_Thermal(2, baudrate=9600, tx=Pin(17))
# initialize led
led = machine.Pin(2, machine.Pin.OUT)
printer.println("")


# Import parameters
# open the JSON file
try:
    with open("/params.json") as json_file:
        # load the JSON data into a dictionary
        params = json.load(json_file)
except:
    params = {
        "btcpay_server_url": "",
        "btcpay_server_api_key": "",
        "btcpay_server_webhook_secret": "",
        "wifi_ssid": "",
        "wifi_psk": ""
    }

wlan_sta = network.WLAN(network.STA_IF)
ssid = params['wifi_ssid']
password = params['wifi_psk']


# Btcpay server url
BTCPAY_INSTANCE=params['btcpay_server_url']
# btcpay server api key
apiKey=params['btcpay_server_api_key']
# btcpay server secret passphrasse for webhook
secret = params['btcpay_server_webhook_secret']


#timezone (used for NTP)
UTC_OFFSET = 1 * 60 * 60


## Configure static variable about ap mode management
# Define long press buttcoin
LONG_PRESS_DURATION = 500
# Global variable that store button press duration
button_press_time = None
# Configure button
boot_button = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)
# Global ap_mode variable
ap_mode = False

# if button is pressed during more than 5 seconds, then start wifi in AP mode
def start_ap_mode():
  global ap_mode
  ap_mode = True
  ifconfig = create_AP()
  # give some visual information
  uasyncio.run(main_blink())
  print("AP mode : " + str(ifconfig))
  
############################################
  
boot_button1 = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)


button_down = False
button_down_time = 0
config_mode = False
config_task = ""


async def blink(led, period_ms):
    while True:
        led.on()
        await uasyncio.sleep_ms(period_ms)
        led.off()
        await uasyncio.sleep_ms(period_ms)
        
def handle_button_fall(change):
    global button_down, button_down_time;
    print("button pushed")
    # trigerred next time button is pushed
    boot_button1.irq(trigger=machine.Pin.IRQ_RISING, handler=handle_button_rise)
    
    button_down_time = time.time()
    button_down = True
    
def handle_button_rise(change):
    global button_down_time;
    button_down = False
    # trigerred next time button is pushed
    boot_button1.irq(trigger=machine.Pin.IRQ_FALLING, handler=handle_button_fall)
  



  
################################################





# Used to render date time for printer
def date():
    timestamp = time.localtime(time.time() + UTC_OFFSET)
    if timestamp[3] < 10:
        hour = '0' + str(timestamp[3])
    else:
        hour = str(timestamp[3])
    if timestamp[4] < 10:
        minute = '0' + str(timestamp[4])
    else:
        minute = str(timestamp[4])
    if timestamp[5] < 10:
        second = '0' + str(timestamp[5])
    else:
        second = str(timestamp[5])
    date = hour +':' + minute +':' + second
    print(date)
    return str(date)




# Get Invoice from btcpay server api
def get_invoice(storeId, invoiceId):
    # API call that get order from btcpay server
    retries = 0
    while retries < 5:
        try:
            auth   = MicroWebCli.AuthToken(apiKey)
            print("in retry")
            wCli = MicroWebCli(BTCPAY_INSTANCE + "/api/v1/stores/" + storeId + "/invoices/" + invoiceId, 'GET', auth)
            print('GET %s' % wCli.URL)
            wCli.OpenRequest()
            print("after openRequest")
            resp = wCli.GetResponse()
            print("after response")
            if resp.IsSuccess():
                break
        except Exception as e:
            retries += 1
            if retries == 5:
                raise e
            else:
                print("Cannot connect to btcpay server... try " + str(retries) + "/5")
                time.sleep(5)

    if not resp.IsSuccess():
        print("Cannot connect to btcpay server api")
    else:
        response = resp.ReadContentAsJSON()
        print(response)
        orderId = response['metadata']['orderId']
        receipt = response['checkoutLink'] + '/receipt'
        posData = json.loads(response['metadata']["posData"])
        
        # Print order
        print('Commande: ' + orderId)
        printer.feed(3)
        #Print date center large
        printer.justify('C')
        printer.setSize('L')
        printer.println(date())
        #Printe orderID small left
        printer.setSize('s')
        printer.justify('L')
        printer.feed(1)
        printer.boldOn()
        printer.println('Cmd ' + orderId)
        printer.boldOff()
        printer.feed(1)
        for item in posData['cart']:
            #Printe item
            print(item['title']+ " x" + str(item['count']))
            printer.println(item['title'] + " x" + str(item['count']))
            printer.println("")
        printer.feed(2)

##########################
    
@app.route('/',methods=['GET'])
async def index(request):
    return send_file('/config.html')

@app.route('/config',methods=['POST'])
async def index(request):
    wifi_ssid = request.form.get('wifi_ssid')
    wifi_password = request.form.get('wifi_password')
    url = request.form.get('url')
    api_key = request.form.get('api_key')
    webhook_secret = request.form.get('webhook_secret')
    config = {
      "wifi_ssid": wifi_ssid,
      "wifi_psk": wifi_password,
      "btcpay_server_url": url,
      "btcpay_server_api_key": api_key,
      "btcpay_server_webhook_secret": webhook_secret      
    }
    with open('params.json', 'w') as outfile:
        json.dump(config, outfile)
    print(config)

# Create route that accept POST method
@app.route('/',methods=['POST'])
def index(request):
    headers = request.headers
    post_data_raw = request.body
    post_data_json = request.json
    print(headers)
    print(post_data_raw)
    try:
        # Check webhook signature sent by btcpay server
        sig = headers['btcpay-sig'][7:] 
        print("sig pushed", sig)
        sig_computed = hmac.new(bytes(secret, "utf-8"), msg=post_data_raw, digestmod=hashlib.sha256).hexdigest()
        print("sig computed", sig_computed)
        if sig_computed != sig:
            return 'Unauthorized', 401
        if(post_data_json["type"] == "InvoiceSettled"):
            print("InvoiceSettled")
            invoiceId = post_data_json['invoiceId']
            storeId = post_data_json['storeId']
            get_invoice(storeId, invoiceId)
        return 'OK'
    except Exception as e:
        print("Error: ", e)
        return "Canno Parse request"
    
##########################
    
def do_connect():
    wlan_sta.active(True)
    #wlan_sta.config(hostname='print')
    if wlan_sta.isconnected():
        led.value(1)
        return None
    print('Trying to connect to %s...' % ssid)
    wlan_sta.connect(ssid, password)
    for retry in range(100):
        connected = wlan_sta.isconnected()
        if connected:
            led.value(1)
            break
        led.value(1)
        time.sleep(1)
        led.value(0)
        time.sleep(1)
        print('.', end='')
    if connected:
        print('\nConnected. Network config: ', wlan_sta.ifconfig())
    else:
        print('\nFailed. Not Connected to: ' + ssid)
        while True:
            led.value(1)
            time.sleep(0.2)
            led.value(0)
            time.sleep(0.2)       
    return connected


def create_AP():
    # Définissez les paramètres du point d'accès
    print("in create_AP")
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(True)
    #ap_if.config(essid="printer", authmode=network.AUTH_WPA_WPA2_PSK, password="azertyuiop")
    ap_if.config(essid='micropython',password=b"micropython",channel=11,authmode=network.AUTH_WPA_WPA2_PSK)  #Set up an access point
    return ap_if.ifconfig()





async def start_server():
    app.run(debug=True)
    
    
async def main():
    global config_task, button_down_time, button_down, config_mode
    print("start")
    
    led.value(0)
    
    try:
        # Start Wifi
        do_connect()
        ifconfig = wlan_sta.ifconfig()
        uasyncio.create_task(start_server())               
        #Print info in debug console and thermal printer
        printer.println('Wifi Connected \r\n IP Address: ' + ifconfig[0])
        printer.println("Server Started")
        printer.feed(2)
        ntptime.settime()
        printer.println(date())
    except:
        print("config file not exist")
        uasyncio.create_task(start_server())
        config_mode = True
        
        print(str(create_AP()))
       
        config_task = uasyncio.create_task(blink(led, 500))
        
   
    while True:
        if button_down and ( time.time() - button_down_time >= 5 ):
            print("long press detected")
            # when config mode is turned off, we restart the board
            if config_mode:
                config_mode = False
                machine.reset()
                #stop_blink(config_task, led)
            # when config mode is turned on, we start the led    
            else:
                print("entering configuration mode")
                config_mode = True
                # set the task so that we can cancel it later
                print(str(create_AP()))
                config_task = uasyncio.create_task(blink(led, 500))

            button_down = False

        await uasyncio.sleep(1)

boot_button1.irq(trigger=machine.Pin.IRQ_FALLING, handler=handle_button_fall)
uasyncio.run(main())



