# Purpose

This is a ultra mini connector that connect btcpay server and Adafruit thermal printer.

The project itself runs on a esp wroom 32 mini board with MicroPython.

# Installation

## board

download the lastest version for the esp wroom 32 board (https://micropython.org/download/esp32/) and follow the installation instructions on micropython.org

Install Thonny IDE (https://thonny.org/) and your PC

## Physical Connection
The connection between the board and the thermal printer use UART2 (labelled as tx2 on the board) and ground (labelled as GND)

## Network
The esp32 needs wifi connection and support WPA-PSK2. params.json file can be openned with Thonny IDE (https://thonny.org/). The wifi connection status is displayed with a fixed blue LED on the board.

## BTCpay server

On the store setting, create a webhook endpoint and configure a secret passphrasse. This secret need to be added in params.json (btcpay_server_webhook_secret).

On your btcpay account, create a new API key that can use btcpay.store.canviewinvoices.<your-store-id>. The key need to be added in params.json (btcpay_server_api_key)

In your params.json, add the btcp pay fqdn (eg: https://my-server.my-domain.com)

# Dependencies

Import the following library with Thonny IDE
* microdot

# Demo

[Youtube Video](https://youtu.be/AQetGpY0mxo)