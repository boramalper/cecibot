# cecibot

## Installation Instructions
1. Use [StevenBlack's hosts](https://github.com/StevenBlack/hosts) to block
   adware & malware:

       sudo wget https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts -O /etc/hosts
       sudo ifdown --exclude=lo -a && sudo ifup --exclude=lo -a

   * You should update your hosts file regularly (preferably every week, or at
     least once a month), using the same commands.

2. Install the latest 8.x LTS version of the *Node.js* as described on their website:

   https://nodejs.org/en/download/package-manager

3. Install *yarn* as described on their website:

   https://yarnpkg.com/en/docs/

4. Install *redis* using [*chris-lea*s PPA](https://launchpad.net/~chris-lea/+archive/ubuntu/redis-server):

       sudo add-apt-repository ppa:chris-lea/redis-server
       sudo apt-get update
       sudo apt-get install redis-server

### The Backend
1. Install all the dependencies of the backend:

       yarn install

   Beware that the [`puppeteer`](https://github.com/GoogleChrome/puppeteer)
   dependency will also download a bundled version of Chromium; to skip it, see
   [*Environment Variables*](https://github.com/GoogleChrome/puppeteer/blob/master/docs/api.md#environment-variables).
