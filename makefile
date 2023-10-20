name=bankconf
scp:
	-pipreqs .
	sshpass -p 784914314a scp -r ../${name} shanghai:/root/docker

build:
	docker build -t ${name} .
	-docker stop ${name} && docker rm ${name}

run:
	docker run --name ${name} --restart=unless-stopped -p 127.0.0.1:8085:8000 -d ${name}
