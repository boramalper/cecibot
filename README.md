# cecibot

## Installation Instructions
1. Use [StevenBlack's hosts](https://github.com/StevenBlack/hosts) to block
   adware & malware:

       sudo wget https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts -O /etc/hosts
       sudo ifdown --exclude=lo -a && sudo ifup --exclude=lo -a

   * You should update your hosts file regularly (preferably every week, or at
     least once a month), using the same commands.

2. Install the latest version of Python 3:

       sudo add-apt-repository ppa:deadsnakes/ppa
       sudo apt-get update
       sudo apt-get install python3.6 python3.6-dev

3. Install `pip`:

       wget https://bootstrap.pypa.io/get-pip.py -O - | python3.6 - --user

4. Install *redis* using [*chris-lea*s PPA](https://launchpad.net/~chris-lea/+archive/ubuntu/redis-server):

       sudo add-apt-repository ppa:chris-lea/redis-server
       sudo apt-get update
       sudo apt-get install redis-server

### The Backend
1. Install all the dependencies of the backend:

       python3.6 -m pip install --user pyppeteer redis requests


### Frontends

#### Telegram
1. Install all the dependencies of the Telegram frontend:

       python3.6 -m pip install --user redis python-telegram-bot
