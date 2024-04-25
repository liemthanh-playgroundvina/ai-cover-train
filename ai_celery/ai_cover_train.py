import json
import logging
import os
import shutil

import requests
from celery import Task
from ai_celery.celery_app import app
from configs.env import settings
from ai_celery.common import Celery_RedisClient, CommonCeleryService

from train import train_voice


class AICoverTrainTask(Task):
    """
    Abstraction of Celery's Task class to support AI Cover Train
    """
    abstract = True

    def __init__(self):
        super().__init__()

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)


@app.task(
    bind=True,
    base=AICoverTrainTask,
    name="{query}.{task_name}".format(
        query=settings.AI_QUERY_NAME,
        task_name=settings.AI_COVER_TRAIN
    ),
    queue=settings.AI_COVER_TRAIN
)
def ai_cover_train_task(self, task_id: str, data: bytes, task_request: bytes, file: bytes):
    """
    Service AI Cover Train tasks

    task_request example:
        {
          "voice_id": "Random-id-voice-123",
          "youtube_link": [
            "https://www.youtube.com/watch?v=h6RONxjPBf4",
            "https://www.youtube.com/watch?v=V6pLnQdGA_c"
          ]
        }
    file example:
        [
            {'content_type': content_type, 'filename': "a.mp3"}
            {'content_type': content_type, 'filename': "b.wav"}
        ]
    """
    print(f"============= AI Cover Train task {task_id}: Started ===================")
    try:
        # Load data
        data = json.loads(data)
        request = json.loads(task_request)
        files = json.loads(file)
        Celery_RedisClient.started(task_id, data)

        # Check task removed
        Celery_RedisClient.check_task_removed(task_id)

        # Request
        voice_id = request.get('voice_id')
        youtube_link = request.get('youtube_link')
        files = [file['filename'] for file in files]
        # print(request)
        # print(files)
        print(f"============= Check model existed: Processing ===================")
        # 1. Check voice_id is existed in Gen Voice (/ai-cover-gen/rvc_models/models.json)
        check_model_follow_voice_id(voice_id)

        print(f"============= Process audio: Processing ===================")
        # 2. Process audio (youtube_link to audio file & separate voice in audio file)
        audios = process_audio(youtube_link, files)
        # print(audios)
        # Move to dataset folder
        dataset_path = f"./dataset/{voice_id}"
        if os.path.exists(dataset_path):
            shutil.rmtree(dataset_path)
        os.makedirs(dataset_path)
        path_copied = None
        for audio in audios:
            path_copied = copy_audio(audio, dataset_path)
        voice_dir_dataset = os.path.dirname(path_copied)
        print(path_copied)
        print(voice_dir_dataset)

        print(f"============= Traing voice {voice_id}-{voice_dir_dataset}: Processing ===================")
        # 3. Training voice model
        try:
            path_model, path_index = train_voice(voice_id, voice_dir_dataset)
        except Exception as e:
            raise Exception(f"Can train {voice_id} model. Step: 'train_voice', Message: \n{e}")
        print(path_model, path_index)

        print(f"============= Uploading model to s3: Processing ===================")
        # 4. Upload into s3
        url_model = CommonCeleryService.upload_s3_file(
            path_model,
            "application/octet-stream",
            f"ai_model/ai-cover/rvc_pretrained/{voice_id}"
        )
        url_index = CommonCeleryService.upload_s3_file(
            path_index,
            "application/octet-stream",
            f"ai_model/ai-cover/rvc_pretrained/{voice_id}"
        )
        print(url_model, url_index)

        print(f"============= Insert model into AI-Cover-Gen/rvc_models/model.json: Processing ===================")
        # 5. Add model into Gen Voice models
        insert_model_follow_voice_id(voice_id, url_model['url'], url_index['url'])
        
        # Remove dataset/model voice_id
        try:
            os.remove(path_model)
            shutil.rmtree(dataset_path)
            shutil.rmtree(f"./logs/{voice_id}")
        except:
            pass

        # Successful
        metadata = {
            "task": "ai_cover_train",
            "tool": "local",
            "model": "rvc_v2",
            "usage": None,
        }
        response = {"status": "Train model successfully.", "metadata": metadata}
        Celery_RedisClient.success(task_id, data, response)
        return

    except ValueError as e:
        logging.getLogger().error(str(e), exc_info=True)
        err = {'code': "400", 'message': str(e)}
        Celery_RedisClient.failed(task_id, data, err)
        return

    except Exception as e:
        logging.getLogger().error(str(e), exc_info=True)
        err = {'code': "500", 'message': "Internal Server Error"}
        Celery_RedisClient.failed(task_id, data, err)
        return


def check_model_follow_voice_id(voice_id):
    """Check model voice id in repo AI Cover Gen is existed"""
    url = f'{settings.APP_AI_COVER_GEN_DOMAIN}/model/{voice_id}'
    response = requests.get(url)

    if response.status_code == 200:
        model = response.json()['data']
        if model is not None:
            raise ValueError(f"Model voice '{voice_id}' is already existed.")
    else:
        raise Exception(f"Can't connect with API app of ai-cover-gen. Step: 'check_model_follow_voice_id', Message: {response.json()}")

    return


def insert_model_follow_voice_id(voice_id: str, s3_model_url: str, s3_index_url: str):
    url = f'{settings.APP_AI_COVER_GEN_DOMAIN}/model'
    body = {"voice_id": voice_id, "s3_model_url": s3_model_url, "s3_index_url": s3_index_url}
    json_data = json.dumps(body)
    response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        raise Exception(f"Can't connect with API app of ai-cover-gen. Step: 'insert_model_follow_voice_id', Message: {response.json()}")

    return


def process_audio(youtube_link: list, files: list):
    url = f'{settings.APP_AI_COVER_GEN_DOMAIN}/separate-audio'
    body = {"files": files, "youtube_link": youtube_link}
    json_data = json.dumps(body)
    response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        audios = response.json()['data']
    else:
        raise Exception(f"Can't connect with API app of ai-cover-gen. Step: 'process_audio', Message: {response.json()}")

    return audios


def copy_audio(audio_path: str, to_path: str = "./dataset/default_folder"):
    destination_path = os.path.join(to_path, os.path.basename(audio_path))
    shutil.copy(audio_path, destination_path)
    return destination_path

