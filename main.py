from Adafruit_Thermal import *
from machine import Pin
import machine
import time
import network
from microdot import Microdot
import hashlib
import hmac
import urequest
import json
import sys
import ntptime
from microWebCli import MicroWebCli

# Initialize Microdot server
app = Microdot()

# initialize uart interface
printer = Adafruit_Thermal(2, baudrate=9600, tx=Pin(17))
led = machine.Pin(2, machine.Pin.OUT)
printer.println("")


# Import parameters
# open the JSON file
with open("/params.json") as json_file:
    # load the JSON data into a dictionary
    params = json.load(json_file)


wlan_sta = network.WLAN(network.STA_IF)
ssid = params['wifi_ssid']
password = params['wifi_psk']

# Btcpay server url
BTCPAY_INSTANCE=params['btcpay_server_url']
# btcpay server api key
apiKey=params['btcpay_server_api_key']
# btcpay server secret passphrasse for webhook
secret = params['btcpay_server_webhook_secret']


#timezone (Paris)
UTC_OFFSET = 1 * 60 * 60

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



  


if __name__ == "__main__":
    led.value(0)
    # Start Wifi
    do_connect()
    ifconfig = wlan_sta.ifconfig()
    #Print info in debug console and thermal printer
    printer.println('Wifi Connected \r\n IP Address: ' + ifconfig[0])
    printer.println("Server Started")
    printer.feed(2)
    ntptime.settime()
    printer.println(date())
    
    # Start microdot server
    app.run(debug=True)
    



