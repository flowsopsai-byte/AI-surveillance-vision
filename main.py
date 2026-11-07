import anthropic
import base64
import cv2
import requests
import os
import time
import boto3
from datetime import datetime
from dotenv import load_dotenv
from onvif import ONVIFCamera

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CAM_IP = os.getenv("CAM_IP")
CAM_USER = os.getenv("CAM_USER")
CAM_PASSWORD = os.getenv("CAM_PASSWORD")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

rekognition = boto3.client(
    'rekognition',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION")
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_rtsp_url():
    cam = ONVIFCamera(CAM_IP, 80, CAM_USER, CAM_PASSWORD)
    media = cam.create_media_service()
    profiles = media.GetProfiles()
    token = profiles[0].token
    uri = media.GetStreamUri({
        'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}},
        'ProfileToken': token
    })
    return uri.Uri


def est_employe_autorise(photo_path):
    with open(photo_path, "rb") as f:
        image_bytes = f.read()
    try:
        response = rekognition.search_faces_by_image(
            CollectionId='employes-autorises',
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=80
        )
        if response['FaceMatches']:
            nom = response['FaceMatches'][0]['Face']['ExternalImageId']
            print(f"Employé reconnu : {nom}")
            return True
        return False
    except Exception as e:
        print(f"Rekognition erreur : {e}")
        return False


derniere_alerte = 0

while True:
    heure = datetime.now().hour
    if 9 <= heure < 23:
        print(f"Scan en cours... {datetime.now().strftime('%H:%M:%S')}")

        try:
            rtsp_url = get_rtsp_url()
            cam = cv2.VideoCapture(rtsp_url)
            ret, frame = cam.read()
            cam.release()

            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            photo_name = os.path.join(BASE_DIR, f"photo_{timestamp}.jpg")

            if not ret:
                print("Erreur capture image")
                time.sleep(30)
                continue

            cv2.imwrite(photo_name, frame)

            with open(photo_name, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Y a-t-il un humain sur cette image ? Si oui, décris : genre, âge approximatif, vêtements, ce qu'il fait. Commence par OUI ou NON."
                            }
                        ],
                    }
                ],
            )

            detection = message.content[0].text
            print(detection)

            with open(os.path.join(BASE_DIR, "log_detections.txt"), "a", encoding="utf-8") as log:
                log.write(f"{timestamp} | {detection}\n")

            if detection.startswith("OUI"):
                if est_employe_autorise(photo_name):
                    print("Employé autorisé — pas d'alerte.")
                    os.remove(photo_name)
                elif (time.time() - derniere_alerte) > 300:
                    payload = {
                        "detection": detection,
                        "timestamp": timestamp,
                        "photo": image_data
                    }
                    requests.post(WEBHOOK_URL, json=payload)

                    with open(photo_name, "rb") as photo:
                        resp = requests.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                            data={"chat_id": CHAT_ID},
                            files={"photo": photo}
                        )
                    print("Telegram:", resp.status_code)
                    derniere_alerte = time.time()
                else:
                    os.remove(photo_name)
            else:
                os.remove(photo_name)
                print("Pas d'humain — photo supprimée.")

        except Exception as e:
            print(f"Erreur : {e}")

        time.sleep(30)

    else:
        print("Hors horaires — en attente...")
        time.sleep(60)
