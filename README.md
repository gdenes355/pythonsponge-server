# pythonsponge-server
Result tracking server for PythonSponge

## Setting up your own server
There are numerous options out there to host your own server. In practice, a cheap / free tier server hosted on AWS / Google Cloud / Azure can work perfectly well.

### Google Cloud
Create a new instance on https://console.cloud.google.com/compute/instances

Select a location close to where you plan to use PythonSponge.

Pick a machine size appropriate for your needs. A free tier e2-micro is likely to work (note that the cloud console will quote the VM price around 10USD per month, but if this is your only VM, the free tier machine cost will be deducted later).

Hit `Create`, and wait for the creation to finish.

`Stop` the machine for now using the controls on the top, then hit `edit` using the pencil icon.

Edit the VM name to something friendlier if you wish to. E.g. `my-school-pythonsponge-vm`.

In the `Firewalls` section, tick `Allow HTTPS traffic`. Then `Save`, and once complete, `Start/Resume` the VM.

Use the SSH button to open the VM terminal in the browser.

## Server installation on Linux
Create a  machine and log in via SSH. Your machine could be an AWS/Google Cloud/Azure VM, or any similar Linux box.

1. Make sure that curl is installed
```
sudo apt install curl
```
2. Download and run the machine setup script from this repository. This can be done automatically by running
```
curl -fsSL https://raw.githubusercontent.com/gdenes355/pythonsponge-server/main/tools/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```

### Server scripts
After setting up your server, the following will be available.

#### Redeploy server
Run `sudo /home/pythonsponge/deployed/server/tools/redeploy.sh` to refetch the git repository, install requirements and to (re)launch the servers.

#### Restart nginx
This should only be necessary if the nginx config files were altered. In this case, run `sudo /home/pythonsponge/deployed/server/tools/restart-nginx.sh`.

#### Rerun installation
The installatin script is idempotent and can be rerun at any point to retrigger all setup steps
```
curl -fsSL https://raw.githubusercontent.com/gdenes355/pythonsponge-server/main/tools/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```
