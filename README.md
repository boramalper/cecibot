# cecibot

## Installation Instructions
1. Install Node.js and [PM2](https://pm2.keymetrics.io/):

       # Install Node.js
       curl -sL https://deb.nodesource.com/setup_8.x | sudo -E bash -
       sudo apt-get install -y nodejs build-essential
       
       # Install PM2
       sudo npm install pm2@latest -g
       
2. Configure PM2:

       # Ensure that PM2 will be restarted on reboot
       pm2 startup
       
       # Link PM2 to [Keymetrics]
       pm2 link <KEYMETRICS_SECRET> <KEYMETRICS_PUBLIC>
       
3. Install [redis-stat](https://github.com/junegunn/redis-stat):

       sudo apt-get install -y ruby-all-dev
       sudo gem install redis-stat

1. Ensure that the following directories exist (if not, make them):

       ~/.cecibot/backend
       ~/.cecibot/email
       ~/.cecibot/telegram

2. Use [StevenBlack's hosts](https://github.com/StevenBlack/hosts) to block
   adware & malware:

       sudo wget https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts -O /etc/hosts
       sudo ifdown --exclude=lo -a && sudo ifup --exclude=lo -a

   * You should update your hosts file regularly (preferably every week, or at
     least once a month), using the same commands.

3. Install the latest version of Python 3:

       sudo add-apt-repository ppa:deadsnakes/ppa
       sudo apt-get update
       sudo apt-get install -y python3.6 python3.6-dev

4. Install `pip`:

       wget https://bootstrap.pypa.io/get-pip.py -O - | python3.6 - --user

5. Install *redis* using [*chris-lea*s PPA](https://launchpad.net/~chris-lea/+archive/ubuntu/redis-server):

       sudo add-apt-repository ppa:chris-lea/redis-server
       sudo apt-get update
       sudo apt-get install -y redis-server

### The Backend
1. Install all the dependencies of the backend:

       python3.6 -m pip install --user pyppeteer redis requests

### Frontends

#### E-Mail
1. Install all the dependencies of the E-Mail frontend:

       python3.6 -m pip install --user flask redis boto3
       
2. Save your [AWS](https://aws.amazon.com/) credentials at `~/.aws/credentials`:

       [default]
       aws_access_key_id=YOUR_ACCESS_KEY
       aws_secret_access_key=YOUR_SECRET_KEY

3. Set the default AWS region at `~/.aws/config`:

       [default]
       region=eu-west-1

#### Telegram
1. Install all the dependencies of the Telegram frontend:

       python3.6 -m pip install --user python-telegram-bot redis

### The Web
1. Install nginx:

       sudo apt install nginx

2. Install Certbot for Let's Encrypt and follow all of the instructions on their
   website to get an HTTPS certificate for both `cecibot.com` and
   `www.cecibot.com` with HTTP -> HTTPS redirection enabled for both:

   https://certbot.eff.org/lets-encrypt/ubuntuxenial-nginx
