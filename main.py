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
    # Get the current time including the timezone offset
    timestamp = time.localtime(time.time() + UTC_OFFSET)
    # Format the hour, minute, and second as two-digit strings
    hour = str(timestamp[3]).zfill(2)
    minute = str(timestamp[4]).zfill(2)
    second = str(timestamp[5]).zfill(2)
    # Return the formatted date and time string
    return hour + ':' + minute + ':' + second


# Get Invoice from btcpay server api
def get_invoice(storeId, invoiceId):
    # API call that gets order from btcpay server

    # Retry up to 5 times if the API call fails
    for retries in range(5):
        try:
            # Authenticate with the btcpay server using an API key
            auth   = MicroWebCli.AuthToken(apiKey)

            # Create a new web client and make a GET request to the specified URL
            wCli = MicroWebCli(BTCPAY_INSTANCE + "/api/v1/stores/" + storeId + "/invoices/" + invoiceId, 'GET', auth)
            wCli.OpenRequest()

            # Get the response from the server and check if it was successful
            resp = wCli.GetResponse()
            if resp.IsSuccess():
                # If the response was successful, exit the loop
                break
        except Exception as e:
            # If an exception occurred and this is the last retry, raise the exception
            if retries == 4:
                raise e
            else:
                # Otherwise, print a message and wait 5 seconds before retrying
                print("Cannot connect to btcpay server... try " + str(retries + 1) + "/5")
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
    return "OK"

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

# Wifi connection
def do_connect():
    # Get WiFi interface and credentials
    wlan_sta = network.WLAN(network.STA_IF)
    ssid = params['wifi_ssid']
    password = params['wifi_psk']
    
    # Activate WiFi interface and check if already connected
    wlan_sta.active(True)
    if wlan_sta.isconnected():
        led.value(1)
        return None
    
    # Print message and attempt to connect to WiFi network
    print('Trying to connect to %s...' % ssid)
    wlan_sta.connect(ssid, password)
    
    for retry in range(100):
        # Check if WiFi is connected
        connected = wlan_sta.isconnected()
        if connected:
            led.value(1)
            break
            
        # Blink LED to indicate ongoing connection attempt
        led.value(1)
        time.sleep(1)
        led.value(0)
        time.sleep(1)
        print('.', end='')
    
    # Print success or failure message and return result
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


# Used to configure esp as an access point (used for configuration mode)
def create_AP():
    # Get WiFi access point interface
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(True)

    # Set up access point with specified parameters
    ap_if.config(essid='micropython', password=b"micropython", channel=11, authmode=network.AUTH_WPA_WPA2_PSK)
    
    # Return access point configuration
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




