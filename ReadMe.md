# Rocketchat 0.74.3 DOCKER 

Rocket.Chat is an Open Source Team Communication and a Real-Time chat which allow you to communicate and collaborate with your team, share files and switch to video/audio conferencing.

## Getting Started

These instructions will get you a copy of the project up and running on your server for development and testing purpose.

### Prerequisites

You will need to install some packages to make everything works.

```
- CentOS 7 clean install
- Internet Connection
- Update CentOS
- Configure SSH connection 
- Docker CE
- Docker COMPOSE
- VIM
- TREE
```

### Installing

This step by step series will help you to get a development env running

**¤~~ STEP 1 : CentOS clean install with SSH ~~¤**

First of all we need an envirnoment to work.

For this project we will install a CentOS 7 on a VirtualMachine or on a real machine as you wish.

Once you get your clean install you will need to update your OS :

```
yum update
```

Then you will need to configure your Internet connection and SSH connexion :

```
example : ping 8.8.8.8
```
```
example : ssh -p 2261 root@127.0.0.1 
```

**¤~~ STEP 2 : Install Docker CE repository and configure it to download the latest stable version ~~¤**

Once you've got a clean install don't forget to create a snapshot if you are in a VM, after that you need ton configure the docker ce repository to install docker ce.

```
sudo yum install -y yum-utils \
  device-mapper-persistent-data \
  lvm2 
```

Now configure the repository to get the latest stable version :

```
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo
```

**¤~~ STEP 3 : Install Docker CE, start and test it ~~¤**

Install Docker CE with the following command :

```
sudo yum install docker-ce docker-ce-cli containerd.io
```

Then start and test it with : 

```
sudo systemctl start docker
```
```
sudo docker run hello-world
```

Enable docker to start docker when you turn on your machine :
```
systemctl enable docker
```

**¤~~ STEP 4 : Install Docker-compose ~~¤**

You can find the latest version of docker compose at : 

https://github.com/docker/compose/releases

Once you get the latest version you can adapt this code to get the latest one : 

```
sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0-rc1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
```

When you get the latest version you now need to add the executable right to the docker compose binary :

```
sudo chmod +x /usr/local/bin/docker-compose
```

Verify that docker-compose is correctly install with the following command :

```
docker-compose --version
```

**¤~~ STEP 5 : Configure work space ~~¤**

Before we create the different work directory we need to install VIM and TREE for verification :

```
yum install vim
yum install tree
```

After that you can create the work space with the following tree or you can create your own tree but ypu will need to adapt the "Dockerfile" :
The README.md is not necessary.

```
[root@localhost home]# tree
.
+-- docker
    +-- Rocket
        +-- Chat
        ¦   +-- Dockerfile
        +-- docker-compose.yaml
        +-- README.md

3 directories, 3 files
```

to create this tree you can copy & past the following sequence order :

```
cd /home
mkdir docker
cd docker/
mkdir Rocket
cd Rocket/
mkdir Chat
vim docker-compose.yaml
cd Chat/
vim Dockerfile
```

Verify with tree :

```
cd /home 
tree
```

**¤~~ STEP 6 : Add content to the "Dockerfile" file ~~¤**

Once the tree is correct you can now add the following content to your "Dockerfile" don't forget that your "Dockerfile" need to had this name in any situation or it won't work ! :

```
FROM alpine:3.8
WORKDIR /tmp
RUN wget -O rocket.chat.tgz https://releases.rocket.chat/0.74.3/ \
	&& apk --no-cache update \
	&& apk --no-cache upgrade \
	&& apk --no-cache add \
		python \
		g++ \
		gcc \
		make \
		nodejs \
		nodejs-npm \
		build-base \
	&& rm -Rf /var/cache/apk \
	&& tar -zxvf rocket.chat.tgz \
	&& rm rocket.chat.tgz \
	&& adduser -D rocket \
	&& mv bundle/ /home/rocket/RocketChat/\
	&& rm -Rf /home/rocket/RocketChat/programs/server/npm/node_modules/sharp/\
	&& chown -R rocket:rocket /home/rocket/RocketChat
USER rocket 
WORKDIR /home/rocket/RocketChat/programs/server
RUN  npm install \
	&& npm audit fix
WORKDIR	/home/rocket/RocketChat
CMD ["node","main.js"]
LABEL maintainer="corentin.gandossi@viacesi.fr"
```

When the configuration as been sucessfully added you can verify it with a build build it in your "Dockerfile" directory ! :
You will get a lot's of warning but don't worry it's normal that doesn't impact rocket.chat or the docker.

```
docker build -t dockertest:latest .
```

**¤~~ STEP 7 : Add content to the "docker-compose.yaml" file ~~¤**

Do the same for the docker compose file, in my case i use a nginx server :

```
version: "3"
services:
  rocketchat:
   build: ./Chat
   restart: unless-stopped
   environment: 
    - ROOT_URL=https://xxxxx.xxxxx.xxxxx 
    - MONGO_URL=mongodb://x.x.x.x:27017/rocketchat 
    - PORT=8080
   ports:
    - 8080
   networks:
    - nginx
    - rocket
networks:
 nginx:
  external: true
 rocket:
  driver: bridge
```

Now we need to create the network interface with :

```
docker network create nginx 
```
We can verify with the classic **ip a** or with **iptables -S**

As we did for the dockerfile we gonna try to build the docker-compose fil to see if there is any error or problem :

```
docker-compose build --no-cache
```

Now that we've the files complete we can now proceed to the test.

## Running the tests

Once we build the docker-compose we get a container name that we can execute, run the docker-compose with the command :

```
docker-compose up
```
If the connection with the database is well configured you will obtained a couple information like this : 

```
rocketchat_1  | ? System ? startup
rocketchat_1  | ? +---------------------------------------------------+
rocketchat_1  | ? |                    SERVER RUNNING                 |
rocketchat_1  | ? +---------------------------------------------------+
rocketchat_1  | ? |                                                   |
rocketchat_1  | ? |  Rocket.Chat Version: 0.74.3                      |
rocketchat_1  | ? |       NodeJS Version: 8.14.0 - x64                |
rocketchat_1  | ? |             Platform: linux                       |
rocketchat_1  | ? |         Process Port: 3000                        |
rocketchat_1  | ? |             Site URL: https://xxxx.xxxx.com       |
rocketchat_1  | ? |     ReplicaSet OpLog: Disabled                    |
rocketchat_1  | ? |          Commit Hash: 202a465f1c                  |
rocketchat_1  | ? |        Commit Branch: HEAD                        |
rocketchat_1  | ? |                                                   |
rocketchat_1  | ? +---------------------------------------------------+
```

## Built With

* [Docker CE guide](https://docs.docker.com/install/linux/docker-ce/centos/) - usefull documentation to learn how to install docker ce
* [Docker COMPOSE guide](https://docs.docker.com/compose/install/) - usefull documentation to learn how to install docker compose
* [Docker guide Rocket.Chat](https://rocket.chat/docs/installation/docker-containers/index.html#) - could help to create your docker our to use a preconfigured docker from recket.chat

## Versioning

We use [RocketChat](https://rocket.chat/) For the versions available, see the [tags on this repository](https://releases.rocket.chat/latest/). 

## Authors

* **Corentin GANDOSSI** - corentin.gandossi@viacesi.fr

* **Loïc STEVENS** - lstevens@yogamicro.com

## License

This project is Open Source.

## Acknowledgments

* Rocket.Chat
* Docker
