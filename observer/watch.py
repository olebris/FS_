import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from minio import Minio
from minio.error import S3Error
import os
import redis
import json

# Configuration MinIO -
minio_client = Minio(
    "minio:9000",
    access_key="yWyHyc1OxMagrdkJVsfC",
    secret_key="oyBpR3x987VieQ4MbeR0aqD2DmMWCATGIHWIJgFz",
    secure=False  # Passer à True si HTTPS
)
minio_bucket = "mfi-test"

# Configuration Redis
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

# Répertoire à surveiller
directory_to_watch = "../in"

# Extension de fichier temporaire
extension = ".json"

class MinioRedisUploader(PatternMatchingEventHandler):
    patterns = ["*" + extension]
    
    
    def on_created(self, event):
        if event.is_directory:
            return None

        file_path = event.src_path
        object_name = os.path.basename(file_path)
        lines_counter = 0

        # Attente pour s'assurer que le fichier est complètement écrit
        print(f"Traitement de : {object_name}")
        time.sleep((5))
        
        # Afficher la taille du fichier
        file_size = os.path.getsize(file_path)
        print(f"Traitement de : {object_name}, Taille du fichier : {file_size} octets")    
        
        
        try:
            print(file_path)
            with open(file_path, "rb") as file_data:
                
                # Charger le contenu en tant qu'objet JSON
                geojson_data = json.load(file_data)
                
                if "features" not in geojson_data or not geojson_data["features"]:
                    print(f"Skipping file {file_path}: Invalid or empty GeoJSON")
                    return
                

                # Upload vers MinIO
                try: 
                    minio_client.fput_object(minio_bucket,object_name,file_path,)
                    print(f"File {object_name} uploaded to MinIO")
                except Exception as e:
                     print(f"Error processing minio file {file_path}: {e}")

                # Stockage dans Redis
                
                # Effacer toutes les données dans Redis
                redis_client.flushall()
                
                for feature in geojson_data["features"]:
                    try:
                        # Convertir le timestamp en une chaîne pour une utilisation comme clé
                        effective_key = str(int(feature["properties"]["effective"]))
                        layer_key = feature["properties"]["layer"]

                        # Récupérer la valeur actuelle pour la clé "effective" / date
                        existing_value = redis_client.hget('latest', effective_key)
                        if existing_value:
                            existing_feature = json.loads(existing_value)
                            existing_feature["features"].append(feature)
                        else:
                            existing_feature = {"type": "FeatureCollection", "features": [feature]}

                        # Réécrire la valeur mise à jour dans Redis
                        redis_client.hset('latest', effective_key, json.dumps(existing_feature))

                        # Faire de même pour la clé "layer" / risque
                        existing_value = redis_client.hget('latest', layer_key)
                        if existing_value:
                            existing_feature = json.loads(existing_value)
                            existing_feature["features"].append(feature)
                        else:
                            existing_feature = {"type": "FeatureCollection", "features": [feature]}

                        redis_client.hset('latest', layer_key, json.dumps(existing_feature))

                        # Faire de même pour tout le fichier
                        combined_key = "all"
                        existing_value = redis_client.hget('latest', combined_key)
                        if existing_value:
                            existing_feature = json.loads(existing_value)
                            existing_feature["features"].append(feature)
                        else:
                            existing_feature = {"type": "FeatureCollection", "features": [feature]}

                        redis_client.hset('latest', combined_key, json.dumps(existing_feature))
                         
                        # compteur de lignes insérées
                        lines_counter += 1

                    except KeyError as ke:
                        print(f"Error redis processing feature: Missing key {ke}")
                    except Exception as e:
                        print(f"Error redis processing feature: {e}")

            print(f"{lines_counter} features insérées dans Redis")

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")


# Créer un observateur pour surveiller le répertoire
observer = Observer()
observer.schedule(MinioRedisUploader(), path=directory_to_watch, recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()
# Print lignes insérées dans Redis clé "ALL"
print(f"Total lignes insérées dans Redis: {observer.event_handler.inserted_lines_counter}")
