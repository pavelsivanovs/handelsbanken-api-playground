# Handelsbanken API Playground

This is a repo for storing code for playing with and testing Handelsbanken API Sandbox. \
Documentation: https://developer.handelsbanken.com/

## Setup

Before running the code in `index.py`, please make sure you copy the contents of file `.env.copy` to `.env` and set the 
variable `HANDELSBANKEN_CLIENT_ID` to be equal to the Client ID of your registered application at 
https://developer.handelsbanken.com/application.

It is also important to note that URL's can change depending on what country API you are subscribed too, these may 
need to be updated in ```get_transactions()``` and ```get_accounts```()
