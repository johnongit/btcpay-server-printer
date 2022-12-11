# Purpose

This is a ultra mini connector that connect btcpay server and Adafruit thermal printer.

The project itself runs on a esp wroom 32 mini board with MicroPython. The board itself provide a network connection to the thermal printer.

Currently, btcpay server should be configured to send a webhook for each payment to the board.
For each webhook, the board will pull information about the order to print it.


# Prerequisite

The esp32 board and btcpay server must be in the same network (or at least, btcpay server must be able to send a webhook to the board).

# Installation

## board

download the lastest version for the esp wroom 32 board (https://micropython.org/download/esp32/) and follow the installation instructions on micropython.org

Install [Thonny IDE](https://thonny.org/) and [ampy](https://learn.adafruit.com/micropython-basics-load-files-and-run-code/install-ampy) on your PC.

Clone the repository and install all python files with ampy

```bash
git clone https://github.com/johnongit/btcpay-server-printer.git
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put params.json
ampy --port /dev/ttyUSB0 put btcpay.py
ampy --port /dev/ttyUSB0 put thermal_printer.py
ampy --port /dev/ttyUSB0 put hmac.py
ampy --port /dev/ttyUSB0 put micoWebCli.py
ampy --port /dev/ttyUSB0 mkdir /templates
ampy --port /dev/ttyUSB0 put templates/config.html /templates/config.html
```

Import the following library with Thonny IDE
* microdot

## Physical Connection
The connection between the board and the thermal printer use UART2 (labelled as tx2 on the board) and ground (labelled as GND)

## Network
The esp32 needs wifi connection and support WPA-PSK2. params.json file can be openned with Thonny IDE (https://thonny.org/). The wifi connection status is displayed with a fixed blue LED on the board.

## BTCpay server

On the store setting, create and configure a webhook endpoint:
* **Payload URL**: https://espressif.local:5000
* **secret**: A preshared password that need to be configured on the board
* **Events**: Select "Send specific event" and "An invoice has been settled"

:warning: *espressif.local* is the esp32 hostname in the local network. it can be replaced by the IP address (available in Thonny IDE in debug mode during the boot process).

On your btcpay account, create a new API key that can use btcpay.store.canviewinvoices.<your-store-id>.


# Configuration

On the first boot, the board will create a wifi access point named "micropython". Connect to this wifi with the password "btcpay4ever". The configuratoin page will be available on http://192.168.4.1:5000/". Fill the form with the following information:
* **Wi-Fi network SSID**: You wifi ssid
* **Wi-Fi network password**: Your wifi password
* **Btcpay server URL**: Your btcpay server fqdn
* **Btcpay user API key**: Your btcpay server API key
* **Btcpay webhook secret**: Your btcpay server webhook secret

Click on submit. The board is now configured.
To restart the board, press the *boot* on the board.

The board should available at espressif.local.
```
ping espressif.local
```

:warning: *espressif.local* is the esp32 hostname in the local network. it can be replaced by the IP address (available in Thonny IDE in debug mode during the boot process).

## Troubleshooting

When the board is not configured and enter in configuration mode, the blue LED is blinking. When the board is configured, the blue LED is fixed.

## Reconfigure

To reconfigure the board, press and hold (5 seconds) the *boot* button on the board. The board will restart in configuration mode.

# Demo

[Youtube Video](https://youtu.be/AQetGpY0mxo)