# AI COVER TRAIN Using RVC V2

- Required: 6GB RAM GPU (in RTX 3090ti)
- Link: https://github.com/blaise-tk/RVC_CLI
- Queue System using celery(python) + redis + rabbitMQ
- Image information: Ubuntu 20.04 + Python 3.9

1. Clone & download model
```# command
git clone https://github.com/liemthanh-playgroundvina/ai-cover-train
cd ai-cover-train
```

2. Config
```# command
make config
# And add your parameters
```

3.Build Image
```# command
make build
```

4.Download model
```# command
make download_model
```

5.Start
```# command
make start
```